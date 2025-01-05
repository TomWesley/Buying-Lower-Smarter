import pandas as pd
import yfinance as yf
from datetime import timedelta

from tqdm import tqdm
from datetime import datetime
import pytz  # Import for timezone handling
import openai

openai.api_key = "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"

def validate_ticker_with_ai(ticker):
    try:
        # Prompt for generative AI
        prompt = f"""
            Provide a quick analysis for the stock ticker {ticker}. I need you to use the following weights and simply output a number between 0 and 100 according to the following: 
            30% - Industry : Is it a technology company(yes/no)
            10% - Growth vs. Blue Chip : Is it a growth oriented company or blue-chip heavy(yes/no)
            30% - Dividends : Is the dividend yield less than 1%(yes/no)
            15% - REIT : Is it not an REIT stock(yes/no)
            15% - Founded date : Was the company founded before 1998(yes, no)

            Answer 'yes' or 'no' for each question and then add the percentages up, counting the number for each yes, output just the number.
            """
        
        # Make a ChatCompletion API call
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial data analyst."},
                {"role": "user", "content": prompt}
            ]
        )

        # Access the result properly
        result = response.choices[0].message.content

        return result
    
    except Exception as e:
        print(f"Error checking criteria for {ticker}: {e}")
        return None



def get_biggest_losers(data, date):
    daily_changes = {}
    percentage_change = 0
    for symbol, df in data.items():
        if date in df.index:
            close_price = df.loc[date, 'Close']
            open_price = df.loc[date, 'Open']
            percentage_change = (close_price - open_price) / open_price * 100
            daily_changes[symbol] = percentage_change
            
            
    # print(f"Average Loss Of Biggest Loser On Day of Theoretical Purchase: {percentage_changes_average:.2f}%")
    losers = sorted(daily_changes, key=daily_changes.get)[:1]

    return losers, percentage_change

def calculate_return(data, symbol, start_date, pc):
    try:
        # Generative AI Section
        
        # Get the start price
        print(symbol)
        print("PERCENTAGE CHANGE FOR THE STOCK WAS")
        # print(pc)

        start_price = data[symbol].loc[start_date, 'Close']
        
        
        # Calculate target end date (2 years after start_date)
        target_end_date = start_date + timedelta(days=365*2)
        
        # Ensure the target end date is within the available data range
        max_end_date = data[symbol].index[-1]  # Last available date in the dataset
        target_end_date = min(target_end_date, max_end_date)
        
        # Find the nearest valid trading day
        valid_dates = data[symbol].index
        if target_end_date not in valid_dates:
            # Use the closest trading day (before the target date)
            target_end_date = valid_dates[valid_dates.get_indexer([target_end_date], method='nearest')[0]]
        
        # Get the end price
        end_price = data[symbol].loc[target_end_date, 'Close']
        
        # Calculate return
        return (end_price - start_price) / start_price * 100
    except Exception as e:
        print(f"Error for {symbol} on {start_date}: {e}")
        return None  # Handle missing or invalid data

def analyze_results(df_results, sd, ed):
    # validation_result = validate_ticker_with_ai('XOM')
    # print(validation_result)
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
    ## As of now SPY working is dependent on 
    try:
        spy = yf.Ticker("SPY")
        spy_data = spy.history(start=sd, end=ed)  # Use the same time window
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
