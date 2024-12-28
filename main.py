import yfinance as yf
import pandas as pd
from analysis import get_biggest_losers, calculate_return, analyze_results
from datetime import timedelta
from tqdm import tqdm
from datetime import datetime
import pytz  # Import for timezone handling

# Set the precise 5-year window ending 2 years ago
# Set the precise 5-year window ending 2 years ago
end_date = datetime.now() - timedelta(days=365*7)
start_date = end_date - timedelta(days=365*20)

# Make both start_date and end_date timezone-aware (UTC)
end_date = end_date.replace(tzinfo=pytz.UTC)
start_date = start_date.replace(tzinfo=pytz.UTC)



def main():
    #CHECK The below if things go wrong
    
    # Step 1: Fetch S&P 500 historical data
    sp500_symbols = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    
    data = {}
    for symbol in sp500_symbols:
        try:
            stock = yf.Ticker(symbol)
            
            # Fetch historical data within the specific 5-year window
            hist_data = stock.history(start=start_date, end=end_date)
            
            # Store the filtered data
            if not hist_data.empty:
                data[symbol] = hist_data
            else:
                print(f"Skipping {symbol}: No data available in 5-year window")
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    
    # Step 2: Analyze each day and store the results
    results = []
    # Ensure we analyze dates within the 5-year window
    analysis_start_date = max(start_date, data['AAPL'].index[0])  # Use AAPL or another reliable stock
    analysis_dates = data['AAPL'].loc[analysis_start_date:].index

    for date in tqdm(analysis_dates):
 # Assuming 'AAPL' has data for all days
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
    analyze_results(df_results, start_date, end_date)

if __name__ == "__main__":
    main()

