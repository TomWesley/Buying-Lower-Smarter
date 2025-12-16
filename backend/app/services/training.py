"""
Training service for analyzing biggest loser patterns and discovering optimal scoring weights.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from scipy import stats
import json

from app.services.stock_data import (
    sp500_historical,
    load_stock_metadata,
    fetch_stock_data,
    fetch_spy_data,
    get_biggest_losers,
    calculate_return,
    calculate_spy_return,
    get_all_historical_tickers
)
from app.services.scoring import calculate_confidence_score, DEFAULT_WEIGHTS


def run_training_analysis(
    start_date: datetime,
    end_date: datetime,
    hold_years: List[int] = [2, 5],
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Run training analysis on a date range.
    Collects all biggest losers, their characteristics, and outcomes.
    Returns analysis results including factor correlations and suggested weights.
    """
    # Load metadata for scoring
    metadata = load_stock_metadata()

    # Get tickers that were in S&P 500 during our date range
    # We collect from start of each year in our range to cover the period
    relevant_tickers = set()
    current_year = start_date.year
    while current_year <= end_date.year:
        year_start = datetime(current_year, 1, 1)
        tickers_for_year = sp500_historical.get_tickers_for_date(year_start)
        relevant_tickers.update(tickers_for_year)
        current_year += 1

    print(f"Relevant tickers for {start_date.year}-{end_date.year}: {len(relevant_tickers)}")

    # Extend end date to allow for return calculations
    max_hold = max(hold_years)
    data_end_date = end_date + timedelta(days=365 * max_hold + 30)

    # Fetch stock data only for relevant tickers
    if progress_callback:
        progress_callback(0, "Fetching stock data...")

    stock_data = fetch_stock_data(
        list(relevant_tickers),
        start_date - timedelta(days=7),  # Buffer for finding trading days
        data_end_date,
        lambda p: progress_callback(p * 0.4, "Fetching stock data...") if progress_callback else None
    )

    if progress_callback:
        progress_callback(40, "Fetching SPY data...")

    spy_data = fetch_spy_data(start_date - timedelta(days=7), data_end_date)

    # Get trading days from SPY
    trading_days = [d for d in spy_data.index if start_date <= d <= end_date]
    total_days = len(trading_days)

    if progress_callback:
        progress_callback(45, f"Analyzing {total_days} trading days...")

    # Collect all picks
    picks = []

    for i, date in enumerate(trading_days):
        # Get S&P 500 constituents for this date
        eligible_tickers = sp500_historical.get_tickers_for_date(date.to_pydatetime())

        # Find biggest losers
        losers = get_biggest_losers(stock_data, date, eligible_tickers, top_n=5)

        for loser in losers:
            ticker = loser['ticker']
            meta = metadata.get(ticker, {'industry': 'unknown', 'dividend_yield': 0.0, 'volume': 0})

            pick = {
                'loser_date': date.strftime('%Y-%m-%d'),  # Day stock was identified as loser
                'ticker': ticker,
                'daily_loss_pct': round(loser['daily_loss_pct'], 4),
                'ranking': loser['ranking'],
                'industry': meta['industry'],
                'dividend_yield': meta['dividend_yield'],
                'volume': meta['volume'],
            }

            # Calculate returns for each hold period
            # Note: calculate_return now returns (return_pct, purchase_date, purchase_price)
            # Purchase happens at OPEN the day AFTER the loser was identified
            for years in hold_years:
                ret, purchase_date, purchase_price = calculate_return(stock_data, ticker, date, years)
                spy_ret = calculate_spy_return(spy_data, date, years)
                pick[f'return_{years}y'] = round(ret, 4) if ret is not None else None
                pick[f'spy_return_{years}y'] = round(spy_ret, 4) if spy_ret is not None else None

            # Store purchase date (same for all hold periods since it's the day after loser_date)
            if purchase_date is not None:
                pick['purchase_date'] = purchase_date.strftime('%Y-%m-%d')
                pick['purchase_price'] = round(purchase_price, 4) if purchase_price else None

            # Calculate confidence score using default weights
            pick['confidence_score'] = calculate_confidence_score(
                ticker,
                loser['daily_loss_pct'],
                loser['ranking'],
                meta['industry'],
                meta['dividend_yield'],
                meta['volume']
            )

            picks.append(pick)

        if progress_callback and i % 50 == 0:
            progress = 45 + (i / total_days * 45)
            progress_callback(progress, f"Processing day {i+1}/{total_days}")

    if progress_callback:
        progress_callback(90, "Analyzing patterns...")

    # Analyze the results
    analysis = analyze_training_results(picks, hold_years)

    if progress_callback:
        progress_callback(100, "Complete")

    return {
        'picks': picks,
        'analysis': analysis,
        'summary': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_trading_days': total_days,
            'total_picks': len(picks),
            'hold_periods': hold_years
        }
    }


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def analyze_training_results(picks: List[Dict], hold_years: List[int]) -> Dict[str, Any]:
    """
    Analyze training results to find patterns and suggest optimal weights.
    """
    if not picks:
        return {}

    df = pd.DataFrame(picks)
    analysis = {}

    for years in hold_years:
        return_col = f'return_{years}y'
        spy_col = f'spy_return_{years}y'

        # Filter to picks with valid returns
        valid = df[df[return_col].notna()].copy()

        if len(valid) < 10:
            continue

        # Basic stats
        returns = valid[return_col]
        spy_returns = valid[spy_col].dropna()

        analysis[f'{years}y'] = {
            'total_picks': len(valid),
            'win_rate': round((returns > 0).mean() * 100, 2),
            'avg_return': round(returns.mean(), 2),
            'median_return': round(returns.median(), 2),
            'std_return': round(returns.std(), 2),
            'min_return': round(returns.min(), 2),
            'max_return': round(returns.max(), 2),
            'spy_avg_return': round(spy_returns.mean(), 2) if len(spy_returns) > 0 else None,
            'spy_win_rate': round((spy_returns > 0).mean() * 100, 2) if len(spy_returns) > 0 else None,
            'beat_spy_rate': round((returns.values > spy_returns.values).mean() * 100, 2) if len(spy_returns) == len(returns) else None,
        }

        # Factor analysis
        analysis[f'{years}y']['factor_analysis'] = analyze_factors(valid, return_col)

        # Industry breakdown
        analysis[f'{years}y']['by_industry'] = (
            valid.groupby('industry')[return_col]
            .agg(['mean', 'count', lambda x: (x > 0).mean() * 100])
            .rename(columns={'mean': 'avg_return', 'count': 'picks', '<lambda_0>': 'win_rate'})
            .round(2)
            .sort_values('avg_return', ascending=False)
            .head(20)
            .to_dict('index')
        )

        # Day of week analysis
        valid['day_of_week'] = pd.to_datetime(valid['loser_date']).dt.day_name()
        analysis[f'{years}y']['by_day'] = (
            valid.groupby('day_of_week')[return_col]
            .agg(['mean', 'count'])
            .rename(columns={'mean': 'avg_return', 'count': 'picks'})
            .round(2)
            .to_dict('index')
        )

        # Ranking analysis
        analysis[f'{years}y']['by_ranking'] = (
            valid.groupby('ranking')[return_col]
            .agg(['mean', 'count', lambda x: (x > 0).mean() * 100])
            .rename(columns={'mean': 'avg_return', 'count': 'picks', '<lambda_0>': 'win_rate'})
            .round(2)
            .to_dict('index')
        )

        # Loss severity buckets
        valid['loss_bucket'] = pd.cut(
            valid['daily_loss_pct'],
            bins=[-float('inf'), -10, -7, -5, -3, 0],
            labels=['<-10%', '-10 to -7%', '-7 to -5%', '-5 to -3%', '-3 to 0%']
        )
        analysis[f'{years}y']['by_loss_severity'] = (
            valid.groupby('loss_bucket', observed=True)[return_col]
            .agg(['mean', 'count', lambda x: (x > 0).mean() * 100])
            .rename(columns={'mean': 'avg_return', 'count': 'picks', '<lambda_0>': 'win_rate'})
            .round(2)
            .to_dict('index')
        )

        # Suggest optimal weights based on correlations
        analysis[f'{years}y']['suggested_weights'] = suggest_optimal_weights(valid, return_col)

    return convert_numpy_types(analysis)


def analyze_factors(df: pd.DataFrame, return_col: str) -> Dict[str, Any]:
    """
    Analyze how different factors correlate with returns.
    """
    factors = {}
    returns = df[return_col].values

    # Industry (tech/healthcare vs others)
    df['is_tech_health'] = df['industry'].str.contains('technology|healthcare|software', case=False, na=False).astype(int)
    if df['is_tech_health'].nunique() > 1:
        corr, pval = stats.pointbiserialr(df['is_tech_health'], returns)
        factors['industry_tech_health'] = {
            'correlation': round(corr, 4),
            'p_value': round(pval, 4),
            'significant': pval < 0.05
        }

    # Low dividend
    df['is_low_dividend'] = (df['dividend_yield'] < 1).astype(int)
    if df['is_low_dividend'].nunique() > 1:
        corr, pval = stats.pointbiserialr(df['is_low_dividend'], returns)
        factors['low_dividend'] = {
            'correlation': round(corr, 4),
            'p_value': round(pval, 4),
            'significant': pval < 0.05
        }

    # Non-REIT
    df['is_non_reit'] = (~df['industry'].str.contains('reit', case=False, na=False)).astype(int)
    if df['is_non_reit'].nunique() > 1:
        corr, pval = stats.pointbiserialr(df['is_non_reit'], returns)
        factors['non_reit'] = {
            'correlation': round(corr, 4),
            'p_value': round(pval, 4),
            'significant': pval < 0.05
        }

    # High volume
    df['is_high_volume'] = (df['volume'] > 30_000_000).astype(int)
    if df['is_high_volume'].nunique() > 1:
        corr, pval = stats.pointbiserialr(df['is_high_volume'], returns)
        factors['high_volume'] = {
            'correlation': round(corr, 4),
            'p_value': round(pval, 4),
            'significant': pval < 0.05
        }

    # Loss severity (continuous)
    corr, pval = stats.pearsonr(df['daily_loss_pct'], returns)
    factors['loss_severity'] = {
        'correlation': round(corr, 4),
        'p_value': round(pval, 4),
        'significant': pval < 0.05,
        'note': 'Negative correlation means bigger losses lead to better returns'
    }

    # Ranking
    corr, pval = stats.spearmanr(df['ranking'], returns)
    factors['ranking'] = {
        'correlation': round(corr, 4),
        'p_value': round(pval, 4),
        'significant': pval < 0.05,
        'note': 'Negative correlation means lower rank (bigger loser) leads to better returns'
    }

    return factors


def suggest_optimal_weights(df: pd.DataFrame, return_col: str) -> Dict[str, float]:
    """
    Suggest optimal weights based on factor importance.
    Uses absolute correlation values to determine relative importance.
    """
    returns = df[return_col].values

    # Calculate feature values
    features = {}

    # Tech/Healthcare
    features['industry'] = df['industry'].str.contains('technology|healthcare|software', case=False, na=False).astype(float).values

    # Low dividend
    features['dividends'] = (df['dividend_yield'] < 1).astype(float).values

    # Non-REIT
    features['reit'] = (~df['industry'].str.contains('reit', case=False, na=False)).astype(float).values

    # Severe loss (>5%)
    features['severity_of_loss'] = (df['daily_loss_pct'] < -5).astype(float).values

    # High volume
    features['volume'] = (df['volume'] > 30_000_000).astype(float).values

    # Ranking (inverted: rank 1 = 5, rank 5 = 1)
    features['ranking'] = (6 - df['ranking']).values / 5

    # Calculate correlations
    correlations = {}
    for name, values in features.items():
        if len(np.unique(values)) > 1:
            corr, _ = stats.pearsonr(values, returns)
            # Use positive correlation (we want factors that predict higher returns)
            correlations[name] = max(0, corr)
        else:
            correlations[name] = 0

    # Normalize to sum to 100
    total = sum(correlations.values())
    if total > 0:
        weights = {name: round(corr / total * 100, 1) for name, corr in correlations.items()}
    else:
        # Fall back to defaults
        weights = DEFAULT_WEIGHTS.copy()

    return weights


def evaluate_model(
    picks: List[Dict],
    weights: Dict[str, float],
    threshold: float,
    hold_years: int = 2
) -> Dict[str, Any]:
    """
    Evaluate a scoring model against training data.
    Returns performance metrics.
    """
    return_col = f'return_{hold_years}y'
    spy_col = f'spy_return_{hold_years}y'

    # Recalculate scores with new weights
    scored_picks = []
    for pick in picks:
        if pick.get(return_col) is None:
            continue

        score = calculate_confidence_score(
            pick['ticker'],
            pick['daily_loss_pct'],
            pick['ranking'],
            pick['industry'],
            pick['dividend_yield'],
            pick['volume'],
            weights
        )
        pick_copy = pick.copy()
        pick_copy['new_score'] = score
        scored_picks.append(pick_copy)

    if not scored_picks:
        return {'error': 'No valid picks'}

    df = pd.DataFrame(scored_picks)

    # All picks
    all_returns = df[return_col]
    all_spy = df[spy_col].dropna()

    # Filtered picks
    filtered = df[df['new_score'] >= threshold]

    results = {
        'all_picks': {
            'count': len(df),
            'avg_return': round(all_returns.mean(), 2),
            'win_rate': round((all_returns > 0).mean() * 100, 2),
            'spy_avg_return': round(all_spy.mean(), 2) if len(all_spy) > 0 else None,
        },
        'filtered_picks': {
            'count': len(filtered),
            'avg_return': round(filtered[return_col].mean(), 2) if len(filtered) > 0 else None,
            'win_rate': round((filtered[return_col] > 0).mean() * 100, 2) if len(filtered) > 0 else None,
        },
        'filter_rate': round(len(filtered) / len(df) * 100, 2) if len(df) > 0 else 0,
        'weights': weights,
        'threshold': threshold
    }

    if len(filtered) > 0:
        # Estimate picks per week
        dates = pd.to_datetime(filtered['loser_date']).unique()
        weeks = (dates.max() - dates.min()).days / 7
        results['filtered_picks']['picks_per_week'] = round(len(filtered) / weeks, 2) if weeks > 0 else 0

    return results
