import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from bisect import bisect_right
import csv

from app.config import PROJECT_ROOT


# Historical S&P 500 constituents file (from fja05680/sp500 GitHub)
SP500_HISTORICAL_FILE = PROJECT_ROOT / "sp500_historical.csv"
# Current stock metadata (industry, dividend, volume)
STOCK_METADATA_FILE = PROJECT_ROOT / "sp500_metadata.csv"


class SP500Historical:
    """
    Manages historical S&P 500 constituents.
    Provides the correct list of tickers for any given date.
    """

    def __init__(self):
        self._data: Dict[datetime, Set[str]] = {}
        self._sorted_dates: List[datetime] = []
        self._loaded = False

    def load(self):
        """Load historical constituents from CSV"""
        if self._loaded:
            return

        try:
            df = pd.read_csv(SP500_HISTORICAL_FILE)
            for _, row in df.iterrows():
                date = pd.to_datetime(row['date']).to_pydatetime()
                tickers_str = row['tickers']
                tickers = set(t.strip() for t in tickers_str.split(',') if t.strip())
                # Exclude TSLA per original methodology
                tickers.discard('TSLA')
                self._data[date] = tickers

            self._sorted_dates = sorted(self._data.keys())
            self._loaded = True
            print(f"Loaded historical S&P 500 data: {len(self._sorted_dates)} dates from {self._sorted_dates[0].date()} to {self._sorted_dates[-1].date()}")

        except Exception as e:
            print(f"Error loading historical S&P 500 data: {e}")
            self._loaded = False

    def get_tickers_for_date(self, date: datetime) -> Set[str]:
        """
        Get the S&P 500 constituents for a specific date.
        Uses the most recent data point on or before the given date.
        """
        if not self._loaded:
            self.load()

        if not self._sorted_dates:
            return set()

        # Find the most recent date on or before the target date
        date_only = datetime(date.year, date.month, date.day)
        idx = bisect_right(self._sorted_dates, date_only)

        if idx == 0:
            # Before our data starts, use earliest available
            return self._data[self._sorted_dates[0]]

        return self._data[self._sorted_dates[idx - 1]]

    def get_all_tickers(self) -> Set[str]:
        """Get all unique tickers that have ever been in the S&P 500"""
        if not self._loaded:
            self.load()

        all_tickers = set()
        for tickers in self._data.values():
            all_tickers.update(tickers)
        return all_tickers

    def get_date_range(self) -> tuple:
        """Get the date range of historical data"""
        if not self._loaded:
            self.load()

        if self._sorted_dates:
            return (self._sorted_dates[0], self._sorted_dates[-1])
        return (None, None)


# Global instance
sp500_historical = SP500Historical()


def load_stock_metadata() -> Dict[str, Dict]:
    """Load stock metadata (industry, dividend yield, volume) from CSV"""
    metadata = {}
    try:
        with open(STOCK_METADATA_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row['Ticker']
                try:
                    metadata[ticker] = {
                        'industry': row['Industry'].lower() if row['Industry'] else 'unknown',
                        'dividend_yield': float(row['Dividend Yield']) if row['Dividend Yield'] and row['Dividend Yield'] != 'N/A' else 0.0,
                        'volume': int(float(row['Volume'])) if row['Volume'] and row['Volume'] != '0.0' else 0
                    }
                except (ValueError, KeyError):
                    metadata[ticker] = {
                        'industry': 'unknown',
                        'dividend_yield': 0.0,
                        'volume': 0
                    }
    except FileNotFoundError:
        print(f"Metadata file not found: {STOCK_METADATA_FILE}")
    return metadata


def get_sp500_tickers_for_date(date: datetime) -> List[str]:
    """Get the S&P 500 constituents for a specific date"""
    return list(sp500_historical.get_tickers_for_date(date))


def get_all_historical_tickers() -> List[str]:
    """Get all tickers that have ever been in the S&P 500"""
    return list(sp500_historical.get_all_tickers())


def fetch_stock_data(
    tickers: List[str],
    start_date: datetime,
    end_date: datetime,
    progress_callback: Optional[callable] = None
) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical OHLC data for multiple tickers.
    Returns dict of {ticker: DataFrame with OHLC data}
    """
    data = {}
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            if not hist.empty:
                # Remove timezone info from index for consistent comparisons
                hist.index = hist.index.tz_localize(None)
                data[ticker] = hist
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

        if progress_callback and i % 10 == 0:
            progress_callback(i / total * 100)

    return data


def fetch_spy_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Fetch SPY data for comparison"""
    spy = yf.Ticker("SPY")
    hist = spy.history(start=start_date, end=end_date)
    # Remove timezone info from index for consistent comparisons
    hist.index = hist.index.tz_localize(None)
    return hist


def get_biggest_losers(
    data: Dict[str, pd.DataFrame],
    date: datetime,
    eligible_tickers: Optional[Set[str]] = None,
    top_n: int = 5
) -> List[Dict]:
    """
    Find the top N biggest losers (by intraday % change) for a given date.
    Only considers tickers in the eligible_tickers set (if provided).
    Returns list of dicts with ticker and percentage change.
    """
    daily_changes = []
    target_date = date.date() if hasattr(date, 'date') else date

    for symbol, df in data.items():
        # Skip if not in eligible tickers for this date
        if eligible_tickers and symbol not in eligible_tickers:
            continue

        # Find matching date in index
        for idx in df.index:
            if idx.date() == target_date:
                try:
                    open_price = df.loc[idx, 'Open']
                    close_price = df.loc[idx, 'Close']
                    if pd.notna(open_price) and pd.notna(close_price) and open_price > 0:
                        pct_change = (close_price - open_price) / open_price * 100
                        daily_changes.append({
                            'ticker': symbol,
                            'pct_change': pct_change
                        })
                except (KeyError, TypeError):
                    pass
                break  # Found the date, move to next symbol

    # Sort by percentage change (ascending = biggest losses first)
    daily_changes.sort(key=lambda x: x['pct_change'])

    # Return top N with ranking
    result = []
    for i, item in enumerate(daily_changes[:top_n]):
        result.append({
            'ticker': item['ticker'],
            'daily_loss_pct': item['pct_change'],
            'ranking': i + 1
        })

    return result


def get_next_trading_day(df: pd.DataFrame, date: datetime) -> Optional[datetime]:
    """Find the next trading day after the given date"""
    target_date = date.date() if hasattr(date, 'date') else date
    for idx in df.index:
        if idx.date() > target_date:
            return idx
    return None


def calculate_return(
    data: Dict[str, pd.DataFrame],
    ticker: str,
    loser_date: datetime,
    hold_years: int
) -> tuple:
    """
    Calculate the return for a stock purchased the day AFTER it was identified as a loser.

    The strategy is:
    1. Stock is identified as biggest loser on Day X (loser_date)
    2. Purchase at market OPEN on Day X+1 (next trading day)
    3. Sell at market CLOSE N years later

    Returns:
        tuple: (return_percentage, purchase_date, purchase_price) or (None, None, None)
    """
    if ticker not in data:
        return None, None, None

    df = data[ticker]

    try:
        # Find the next trading day after the loser was identified
        purchase_date = get_next_trading_day(df, loser_date)
        if purchase_date is None:
            return None, None, None

        # Purchase at OPEN price on the day after the loss
        purchase_price = df.loc[purchase_date, 'Open']

        if pd.isna(purchase_price) or purchase_price <= 0:
            return None, None, None

        # Calculate target sell date (N years from purchase)
        target_end_date = purchase_date + timedelta(days=365 * hold_years)

        # Check if we have enough data
        if target_end_date > df.index[-1]:
            return None, None, None

        # Find the closest date in the index to our target
        best_idx = None
        best_diff = None
        for idx in df.index:
            diff = abs((idx - target_end_date).days)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_idx = idx

        if best_idx is None:
            return None, None, None

        # Sell at CLOSE price
        sell_price = df.loc[best_idx, 'Close']

        if pd.notna(sell_price) and sell_price > 0:
            return_pct = (sell_price - purchase_price) / purchase_price * 100
            return return_pct, purchase_date, purchase_price
        return None, None, None

    except Exception as e:
        print(f"Error calculating return for {ticker}: {e}")
        return None, None, None


def calculate_spy_return(
    spy_data: pd.DataFrame,
    loser_date: datetime,
    hold_years: int
) -> Optional[float]:
    """
    Calculate SPY return for the same hold period as the stock pick.

    Uses the same logic: buy at OPEN the day after the loser was identified,
    sell at CLOSE N years later.
    """
    try:
        # Find the next trading day after the loser was identified
        purchase_date = get_next_trading_day(spy_data, loser_date)
        if purchase_date is None:
            return None

        # Purchase at OPEN price
        purchase_price = spy_data.loc[purchase_date, 'Open']

        if pd.isna(purchase_price) or purchase_price <= 0:
            return None

        # Calculate target sell date
        target_end_date = purchase_date + timedelta(days=365 * hold_years)

        # Find the first available date on or after target
        sell_idx = None
        for idx in spy_data.index:
            if idx >= target_end_date:
                sell_idx = idx
                break

        if sell_idx is None:
            return None

        # Sell at CLOSE price
        sell_price = spy_data.loc[sell_idx, 'Close']

        if pd.notna(sell_price) and sell_price > 0:
            return (sell_price - purchase_price) / purchase_price * 100
        return None

    except Exception as e:
        print(f"Error calculating SPY return: {e}")
        return None
