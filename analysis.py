import pandas as pd
import yfinance as yf
from datetime import timedelta

from tqdm import tqdm
from datetime import datetime
import pytz  # Import for timezone handling


def get_biggest_losers(data, date):
    daily_changes = {}
    for symbol, df in data.items():
        if date in df.index:
            close_price = df.loc[date, 'Close']
            open_price = df.loc[date, 'Open']
            percentage_change = (close_price - open_price) / open_price * 100
            daily_changes[symbol] = percentage_change
            
            
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

def analyze_results(df_results, sd, ed):
    winners = df_results[df_results['return_2y'] > 0]
    winning_percentage = len(winners) / len(df_results) * 100
    average_return_of_winners = winners['return_2y'].mean()
    average_return_overall = df_results['return_2y'].mean()
    print("Start Date:", sd )
    print("End Date:", ed)
    print(f"Winning Percentage: {winning_percentage:.2f}%")
    print(f"Average Return of Winners: {average_return_of_winners:.2f}%")
    print(f"Average Return Overall: {average_return_overall:.2f}%")
    

    # Trend Analysis: Day of the Week
    df_results['day_of_week'] = df_results['date'].dt.day_name()
    day_of_week_trends = df_results.groupby('day_of_week')['return_2y'].mean()
    
    print("Day of the Week Trends:", day_of_week_trends)

    # Market Performance Analysis
    print("\n=== SPY Rolling 2-Year Returns ===")
    try:
        spy = yf.Ticker("SPY")
        spy_data = spy.history(start=sd, end=ed)  # Use the same fixed 5-year window
        spy_data['2y_return'] = None  # Initialize column

        # Calculate 2-year returns for each day
        for i in range(len(spy_data)):
            start_price = spy_data['Close'].iloc[i]
            start_date = spy_data.index[i]
            end_date = start_date + timedelta(days=365*2)

            # Find the closest available date within the 2-year window
            end_prices = spy_data[spy_data.index >= end_date]['Close']
            if not end_prices.empty:
                end_price = end_prices.iloc[0]
                spy_data.at[start_date, '2y_return'] = (end_price - start_price) / start_price * 100

        # Filter out any days without a valid 2-year return
        valid_returns = spy_data['2y_return'].dropna()
        avg_2y_return = valid_returns.mean()
        winning_percentage_spy = (valid_returns > 0).sum() / len(valid_returns) * 100

        print(f"SPY Average 2-Year Return: {avg_2y_return:.2f}%")
        print(f"SPY Winning Percentage (2-Year Windows): {winning_percentage_spy:.2f}%")
    except Exception as e:
        print(f"Error calculating SPY rolling returns: {e}")
