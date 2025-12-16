import json
from typing import Dict, Optional


# Default weights based on original analysis
DEFAULT_WEIGHTS = {
    "industry": 15,      # Tech/Healthcare bonus
    "dividends": 15,     # Low dividend yield bonus
    "reit": 10,          # Non-REIT bonus
    "severity_of_loss": 30,  # Bigger loss = higher score
    "ranking": 10,       # Position among top 5 losers
    "volume": 20         # High volume bonus
}

DEFAULT_THRESHOLD = 65.0


def calculate_confidence_score(
    ticker: str,
    daily_loss_pct: float,
    ranking: int,
    industry: str,
    dividend_yield: float,
    volume: int,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate confidence score for a stock pick based on various factors.

    Args:
        ticker: Stock ticker symbol
        daily_loss_pct: Percentage loss for the day (negative value)
        ranking: Position among biggest losers (1-5)
        industry: Stock industry category
        dividend_yield: Dividend yield percentage
        volume: Trading volume
        weights: Custom weights dict, uses defaults if None

    Returns:
        Confidence score between 0 and 100
    """
    w = weights or DEFAULT_WEIGHTS
    score = 0.0
    industry_lower = industry.lower() if industry else ""

    # Industry: Technology or Healthcare bonus
    if "technology" in industry_lower or "healthcare" in industry_lower or "software" in industry_lower:
        score += w.get("industry", 15)

    # Dividend Yield: Low dividend yield is positive (growth stock indicator)
    if dividend_yield < 1:
        score += w.get("dividends", 15)

    # REIT: Non-REIT stocks get bonus
    if "reit" not in industry_lower:
        score += w.get("reit", 10)

    # Severity of Loss: Bigger losses may indicate oversold conditions
    severity_weight = w.get("severity_of_loss", 30)
    if daily_loss_pct < -5:
        score += severity_weight
    else:
        # Partial credit based on how close to -5%
        partial = severity_weight * ((100 - (5 + daily_loss_pct) * 20) / 100)
        score += max(0, partial)

    # Volume: High volume indicates institutional interest
    if volume > 30_000_000:
        score += w.get("volume", 20)

    # Ranking: Favor bigger losers
    ranking_weight = w.get("ranking", 10)
    ranking_score = max(ranking_weight - (ranking - 1) * (ranking_weight / 5), 0)
    score += ranking_score

    return min(100, max(0, score))


def filter_by_threshold(
    picks: list,
    threshold: float = DEFAULT_THRESHOLD
) -> list:
    """Filter picks by confidence score threshold"""
    return [p for p in picks if p.get('confidence_score', 0) >= threshold]


def weights_to_json(weights: Dict[str, float]) -> str:
    """Convert weights dict to JSON string for storage"""
    return json.dumps(weights)


def weights_from_json(weights_json: str) -> Dict[str, float]:
    """Parse weights from JSON string"""
    if not weights_json:
        return DEFAULT_WEIGHTS.copy()
    return json.loads(weights_json)


def suggest_weights_from_training(picks: list) -> Dict[str, float]:
    """
    Analyze training picks and suggest optimal weights.
    Uses correlation analysis to determine which factors best predict positive returns.
    """
    import numpy as np
    from scipy import stats

    if not picks:
        return DEFAULT_WEIGHTS.copy()

    # Extract features and outcomes
    returns = []
    industries_tech_healthcare = []
    low_dividends = []
    non_reits = []
    high_volumes = []
    loss_severities = []
    rankings = []

    for pick in picks:
        ret = pick.get('return_2y') or pick.get('return_5y')
        if ret is None:
            continue

        returns.append(ret)

        industry = (pick.get('industry') or '').lower()
        industries_tech_healthcare.append(
            1 if 'technology' in industry or 'healthcare' in industry or 'software' in industry else 0
        )

        low_dividends.append(1 if (pick.get('dividend_yield') or 0) < 1 else 0)
        non_reits.append(0 if 'reit' in industry else 1)
        high_volumes.append(1 if (pick.get('volume') or 0) > 30_000_000 else 0)
        loss_severities.append(1 if (pick.get('daily_loss_pct') or 0) < -5 else 0)
        rankings.append(6 - (pick.get('ranking') or 3))  # Invert so rank 1 = 5 points

    if len(returns) < 10:
        return DEFAULT_WEIGHTS.copy()

    returns = np.array(returns)

    # Calculate correlations with returns
    correlations = {}

    factors = {
        'industry': industries_tech_healthcare,
        'dividends': low_dividends,
        'reit': non_reits,
        'volume': high_volumes,
        'severity_of_loss': loss_severities,
        'ranking': rankings
    }

    total_correlation = 0
    for name, values in factors.items():
        if len(set(values)) > 1:  # Need variation
            corr, _ = stats.pearsonr(values, returns)
            correlations[name] = max(0, corr)  # Only positive correlations
        else:
            correlations[name] = 0
        total_correlation += correlations[name]

    # Normalize to sum to 100
    if total_correlation > 0:
        suggested = {
            name: round(corr / total_correlation * 100, 1)
            for name, corr in correlations.items()
        }
    else:
        suggested = DEFAULT_WEIGHTS.copy()

    return suggested
