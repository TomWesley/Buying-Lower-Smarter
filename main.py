import yfinance as yf
import pandas as pd
from analysis import get_biggest_losers, calculate_return, analyze_results
from datetime import timedelta
from tqdm import tqdm

def main():
    # Step 1: Fetch S&P 500 historical data
    sp500_symbols = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    
    data = {}
    for symbol in sp500_symbols:
        try:
            stock = yf.Ticker(symbol)

            # Fetch max available history for the stock
            hist_data = stock.history(period="max")

            # Limit history to the past 5 years
            hist_data = hist_data[hist_data.index >= (hist_data.index[-1] - pd.DateOffset(years=5))]

            # Store the filtered data
            if not hist_data.empty:
                data[symbol] = hist_data
            else:
                print(f"Skipping {symbol}: No data available")
        
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    
    # Step 2: Analyze each day and store the results
    results = []
    for date in tqdm(data['AAPL'].index):  # Assuming 'AAPL' has data for all days
        losers = get_biggest_losers(data, date)
        for loser in losers:
            return_2y = calculate_return(data, loser, date)
            if return_2y is not None:
                results.append({
                    'date': date,
                    'loser': loser,
                    'return_2y': return_2y
                })
    
    # Step 3: Analyze results
    df_results = pd.DataFrame(results)
    analyze_results(df_results)

if __name__ == "__main__":
    main()

