import pandas as pd
import yfinance as yf
from datetime import timedelta

from tqdm import tqdm
from datetime import datetime
import pytz  # Import for timezone handling

# Set the precise 5-year window ending 2 years ago
# Set the precise 5-year window ending 2 years ago
end_date = datetime.now() - timedelta(days=365*2)
start_date = end_date - timedelta(days=365*5)

# Make both start_date and end_date timezone-aware (UTC)
end_date = end_date.replace(tzinfo=pytz.UTC)
start_date = start_date.replace(tzinfo=pytz.UTC)

def get_biggest_losers(data, date):
    daily_changes = {}
    percentage_changes_average = 0
    counter = 0
    for symbol, df in data.items():
        if date in df.index:
            close_price = df.loc[date, 'Close']
            open_price = df.loc[date, 'Open']
            percentage_change = (close_price - open_price) / open_price * 100
            daily_changes[symbol] = percentage_change
            percentage_changes_average = percentage_changes_average + percentage_change
            counter = counter + 1
    percentage_changes_average = percentage_changes_average/counter
    # print(f"Average Loss Of Biggest Loser On Day of Theoretical Purchase: {percentage_changes_average:.2f}%")
    losers = sorted(daily_changes, key=daily_changes.get)[:1]
    return losers

def calculate_return(data, symbol, start_date):
    try:
        # Get the start price
        start_price = data[symbol].loc[start_date, 'Close']
        
        # Calculate end_date (2 years after start_date, capped at SPY end_date)
        target_end_date = start_date + timedelta(days=365*2)
        max_end_date = data[symbol].index[-1]  # Last available date in the dataset
        end_date = min(target_end_date, max_end_date)

        # Get the end price
        end_price = data[symbol].loc[end_date, 'Close']
        
        # Calculate return
        return (end_price - start_price) / start_price * 100
    except:
        return None  # Handle missing or invalid data

def analyze_results(df_results):
    winners = df_results[df_results['return_2y'] > 0]
    winning_percentage = len(winners) / len(df_results) * 100
    average_return_of_winners = winners['return_2y'].mean()
    average_return_overall = df_results['return_2y'].mean()
    print("Start Date:", start_date )
    print("End Date:", end_date )
    print(f"Winning Percentage: {winning_percentage:.2f}%")
    print(f"Average Return of Winners: {average_return_of_winners:.2f}%")
    print(f"Average Return Overall: {average_return_overall:.2f}%")
    

    # Trend Analysis: Day of the Week
    df_results['day_of_week'] = df_results['date'].dt.day_name()
    day_of_week_trends = df_results.groupby('day_of_week')['return_2y'].mean()
    
    print("Day of the Week Trends:", day_of_week_trends)

    # Market Performance Analysis
    print("\n=== SPY Performance (Last 5 Years) ===")
    try:
        spy = yf.Ticker("SPY")
        spy_data = spy.history(period="5y")
        start_price = spy_data['Close'].iloc[0]
        end_price = spy_data['Close'].iloc[-1]
        spy_return = (end_price - start_price) / start_price * 100

        print(f"SPY Total Return (5 years): {spy_return:.2f}%")
        print(f"Start Price: ${start_price:.2f}, End Price: ${end_price:.2f}")
    except Exception as e:
        print(f"Error fetching SPY data: {e}")
