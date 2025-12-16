"""
Script to fetch and update S&P 500 ticker metadata.
Fetches current industry, dividend yield, and average volume for each ticker.
"""
import csv
import time
from typing import List, Dict
import yfinance as yf
from yahooquery import Ticker
import pandas as pd

from app.config import SP500_TICKERS_FILE, STOCK_METADATA_FILE, PROJECT_ROOT


def get_current_sp500_tickers() -> List[str]:
    """
    Get current S&P 500 constituents from Wikipedia.
    Falls back to existing file if fetch fails.
    """
    try:
        # Fetch from Wikipedia
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df['Symbol'].tolist()
        # Clean up any formatting issues (e.g., BRK.B vs BRK-B)
        tickers = [t.replace('.', '-') if '.' in t else t for t in tickers]
        # Also keep the dot version for compatibility
        tickers_with_dots = [t.replace('-', '.') for t in tickers if '-' in t]
        all_tickers = list(set(tickers + tickers_with_dots))
        return sorted(all_tickers)
    except Exception as e:
        print(f"Could not fetch from Wikipedia: {e}")
        # Fall back to existing file
        with open(SP500_TICKERS_FILE, 'r') as f:
            content = f.read().strip()
            return [t.strip() for t in content.split(',') if t.strip()]


def fetch_ticker_metadata(tickers: List[str]) -> Dict[str, Dict]:
    """
    Fetch metadata for each ticker using yfinance.
    Returns dict of {ticker: {industry, dividend_yield, volume}}
    """
    metadata = {}
    failed_tickers = []

    print(f"Fetching metadata for {len(tickers)} tickers...")

    # Process in batches to avoid rate limiting
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(tickers)-1)//batch_size + 1}")

        for ticker in batch:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                # Extract relevant fields
                industry = info.get('industry', info.get('sector', 'Unknown'))
                dividend_yield = info.get('dividendYield', 0) or 0
                # Convert to percentage if it's a decimal
                if dividend_yield < 1 and dividend_yield > 0:
                    dividend_yield = dividend_yield * 100
                volume = info.get('averageVolume', info.get('volume', 0)) or 0

                metadata[ticker] = {
                    'industry': industry,
                    'dividend_yield': round(dividend_yield, 2),
                    'volume': int(volume)
                }

            except Exception as e:
                print(f"Error fetching {ticker}: {e}")
                failed_tickers.append(ticker)
                # Default values for failed tickers
                metadata[ticker] = {
                    'industry': 'Unknown',
                    'dividend_yield': 0.0,
                    'volume': 0
                }

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        # Longer delay between batches
        time.sleep(1)

    if failed_tickers:
        print(f"\nFailed to fetch data for {len(failed_tickers)} tickers: {failed_tickers[:10]}...")

    return metadata


def save_tickers_csv(tickers: List[str], filepath: str):
    """Save tickers as comma-separated list"""
    # Exclude TSLA per original methodology
    tickers = [t for t in tickers if t != 'TSLA']
    with open(filepath, 'w') as f:
        f.write(','.join(tickers))
    print(f"Saved {len(tickers)} tickers to {filepath}")


def save_metadata_csv(metadata: Dict[str, Dict], filepath: str):
    """Save metadata to CSV file"""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Ticker', 'Industry', 'Dividend Yield', 'Volume'])
        for ticker, data in sorted(metadata.items()):
            writer.writerow([
                ticker,
                data['industry'],
                data['dividend_yield'],
                data['volume']
            ])
    print(f"Saved metadata for {len(metadata)} tickers to {filepath}")


def update_all():
    """Main function to update all ticker data"""
    print("=" * 50)
    print("Updating S&P 500 Ticker Data")
    print("=" * 50)

    # Get current S&P 500 list
    print("\n1. Fetching current S&P 500 constituents...")
    tickers = get_current_sp500_tickers()
    print(f"   Found {len(tickers)} tickers")

    # Fetch metadata for each ticker
    print("\n2. Fetching metadata from Yahoo Finance...")
    metadata = fetch_ticker_metadata(tickers)

    # Save updated files
    print("\n3. Saving updated files...")
    output_tickers = PROJECT_ROOT / "sp500_tickers.csv"
    output_metadata = PROJECT_ROOT / "sp500_metadata.csv"

    save_tickers_csv(tickers, str(output_tickers))
    save_metadata_csv(metadata, str(output_metadata))

    # Print summary stats
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)

    industries = {}
    for data in metadata.values():
        ind = data['industry']
        industries[ind] = industries.get(ind, 0) + 1

    print(f"Total tickers: {len(metadata)}")
    print(f"Unique industries: {len(industries)}")
    print("\nTop 10 industries:")
    for ind, count in sorted(industries.items(), key=lambda x: -x[1])[:10]:
        print(f"  {ind}: {count}")

    high_volume = sum(1 for d in metadata.values() if d['volume'] > 30_000_000)
    print(f"\nHigh volume (>30M): {high_volume} stocks")

    low_dividend = sum(1 for d in metadata.values() if d['dividend_yield'] < 1)
    print(f"Low dividend (<1%): {low_dividend} stocks")

    return tickers, metadata


if __name__ == "__main__":
    update_all()
