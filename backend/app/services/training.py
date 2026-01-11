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


def suggest_optimal_weights(df: pd.DataFrame, return_col: str) -> Dict[str, Any]:
    """
    Discover optimal weights by comparing TOP performers vs BOTTOM performers.

    Approach:
    1. Split picks into winners (top 25% by return) and losers (bottom 25%)
    2. Test MANY potential factors - both directions (e.g., high AND low dividend)
    3. Use ABSOLUTE difference - if losers have more of something, flip the indicator
    4. Keep only the BEST factor from each category (no double-counting)
    5. Weight by differentiation strength
    """
    returns = df[return_col]

    # Define winners (top 25%) and losers (bottom 25%)
    top_threshold = returns.quantile(0.75)
    bottom_threshold = returns.quantile(0.25)

    winners = df[returns >= top_threshold]
    losers = df[returns <= bottom_threshold]

    # Define factors GROUPED BY CATEGORY
    # We'll only keep the best factor from each category
    factor_categories = {
        'dividend': {
            'no_dividend': lambda x: x['dividend_yield'] == 0,
            'low_dividend': lambda x: (x['dividend_yield'] > 0) & (x['dividend_yield'] < 1),
            'medium_dividend': lambda x: (x['dividend_yield'] >= 1) & (x['dividend_yield'] < 3),
            'high_dividend': lambda x: x['dividend_yield'] >= 3,
        },
        'volume': {
            'very_high_volume': lambda x: x['volume'] > 50_000_000,
            'high_volume': lambda x: (x['volume'] > 20_000_000) & (x['volume'] <= 50_000_000),
            'medium_volume': lambda x: (x['volume'] > 5_000_000) & (x['volume'] <= 20_000_000),
            'low_volume': lambda x: x['volume'] <= 5_000_000,
        },
        'loss_severity': {
            'extreme_loss': lambda x: x['daily_loss_pct'] < -10,
            'severe_loss': lambda x: (x['daily_loss_pct'] < -5) & (x['daily_loss_pct'] >= -10),
            'moderate_loss': lambda x: (x['daily_loss_pct'] < -3) & (x['daily_loss_pct'] >= -5),
            'mild_loss': lambda x: x['daily_loss_pct'] >= -3,
        },
        'ranking': {
            'rank_1': lambda x: x['ranking'] == 1,
            'rank_2': lambda x: x['ranking'] == 2,
            'rank_3': lambda x: x['ranking'] == 3,
            'rank_4': lambda x: x['ranking'] == 4,
            'rank_5': lambda x: x['ranking'] == 5,
            'top_2_loser': lambda x: x['ranking'] <= 2,
            'bottom_2_loser': lambda x: x['ranking'] >= 4,
        },
        # Industries are independent - each can be in the formula
        'tech_sector': {
            'tech_sector': lambda x: x['industry'].str.contains('technology|software|semiconductor', case=False, na=False),
        },
        'healthcare_sector': {
            'healthcare_sector': lambda x: x['industry'].str.contains('healthcare|pharmaceutical|biotech', case=False, na=False),
        },
        'financial_sector': {
            'financial_sector': lambda x: x['industry'].str.contains('financial|bank|insurance', case=False, na=False),
        },
        'consumer_sector': {
            'consumer_sector': lambda x: x['industry'].str.contains('consumer|retail', case=False, na=False),
        },
        'energy_sector': {
            'energy_sector': lambda x: x['industry'].str.contains('energy|oil|gas', case=False, na=False),
        },
        'industrial_sector': {
            'industrial_sector': lambda x: x['industry'].str.contains('industrial|manufacturing', case=False, na=False),
        },
        'reit': {
            'is_reit': lambda x: x['industry'].str.contains('reit|real estate', case=False, na=False),
        },
        'communications': {
            'communications': lambda x: x['industry'].str.contains('communication|telecom|media', case=False, na=False),
        },
        'utilities': {
            'utilities': lambda x: x['industry'].str.contains('utilities|utility', case=False, na=False),
        },
    }

    # Calculate differentiation for ALL factors
    all_factors = {}

    for category, factors in factor_categories.items():
        for name, condition in factors.items():
            try:
                winners_with = condition(winners).mean() * 100
                losers_with = condition(losers).mean() * 100

                # Raw difference (positive = more common in winners)
                raw_diff = winners_with - losers_with

                # Absolute difference for ranking importance
                abs_diff = abs(raw_diff)

                all_factors[name] = {
                    'category': category,
                    'winners_pct': round(winners_with, 1),
                    'losers_pct': round(losers_with, 1),
                    'raw_difference': round(raw_diff, 1),
                    'abs_difference': round(abs_diff, 1),
                    'favors_winners': raw_diff > 0,
                    'indicator': 'POSITIVE' if raw_diff > 0 else 'NEGATIVE'
                }
            except Exception:
                pass

    # For each category, keep only the factor with the HIGHEST absolute difference
    best_per_category = {}
    for name, data in all_factors.items():
        category = data['category']
        if category not in best_per_category or data['abs_difference'] > best_per_category[category]['abs_difference']:
            best_per_category[category] = {**data, 'name': name}

    # Filter to significant factors (>5% difference)
    significant_factors = {
        v['name']: v for k, v in best_per_category.items()
        if v['abs_difference'] >= 5
    }

    # Sort by absolute difference descending
    sorted_factors = dict(sorted(
        significant_factors.items(),
        key=lambda x: x[1]['abs_difference'],
        reverse=True
    ))

    # Build the formula from significant factors
    formula_factors = {}
    for name, data in sorted_factors.items():
        formula_factors[name] = {
            'weight_score': data['abs_difference'],
            'condition': 'HAS' if data['favors_winners'] else 'NOT',
            'category': data['category'],
            'winners_pct': data['winners_pct'],
            'losers_pct': data['losers_pct'],
            'difference': data['raw_difference'],
        }

    # Normalize weights to sum to 100
    total_score = sum(f['weight_score'] for f in formula_factors.values())

    final_weights = {}
    for name, data in formula_factors.items():
        weight = round(data['weight_score'] / total_score * 100, 1) if total_score > 0 else 0
        final_weights[name] = {
            'weight': weight,
            'condition': data['condition'],
            'category': data['category'],
            'description': f"{'Has' if data['condition'] == 'HAS' else 'Does NOT have'} {name.replace('_', ' ')}",
            'winners_pct': data['winners_pct'],
            'losers_pct': data['losers_pct'],
            'difference': data['difference'],
        }

    return {
        'formula': final_weights,
        'all_factors_tested': all_factors,
        'best_per_category': {k: v['name'] for k, v in best_per_category.items()},
        'significant_factors_count': len(sorted_factors),
        'total_factors_tested': len(all_factors),
        'categories_count': len(best_per_category),
        'thresholds': {
            'top_25_pct_return': round(float(top_threshold), 1),
            'bottom_25_pct_return': round(float(bottom_threshold), 1),
            'winners_count': len(winners),
            'losers_count': len(losers),
            'min_difference_threshold': 5.0
        }
    }


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
