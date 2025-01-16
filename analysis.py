import pandas as pd
import yfinance as yf
from datetime import timedelta

from tqdm import tqdm
from datetime import datetime
import pytz  # Import for timezone handling


from yahooquery import Ticker


# Set timeout globally (e.g., 10 seconds)


def calculate_confidence_score(ticker: str, percentage_change: float, ranking: int) -> float:
    """
    Calculate a confidence score for a stock based on various factors.
    
    Parameters:
        ticker (str): The stock ticker.
        percentage_change (float): The percentage change of the stock's price.
        ranking (int): The rank of the stock in the biggest loser list (1 for biggest loser, etc.).
    
    Returns:
        float: The confidence score between 0 and 100.
    """
    try:
        # Fetch data from Yahoo Finance
        stock = Ticker(ticker, asynchronous=True, timeout=5)
        summary = stock.summary_detail.get(ticker, {})
        asset_profile = stock.asset_profile.get(ticker, {})
        key_stats = stock.key_stats
        
        # Extract data
        industry = asset_profile.get("industry", "").lower()
        dividend_yield = summary.get("dividendYield", 0) * 100  # Convert to percentage
        ipo_year = key_stats[ticker].get('ipoYear')        
        # Define weights
        weights = {
            "industry": 25,
            "growth_vs_blue_chip": 10,
            "dividends": 15,
            "reit": 15,
            "severity_of_loss": 25,
            "ranking": 10,
        }
        
        # Calculate score components
        score = 0

        # Industry: Is it a technology or innovative healthcare company?
        if "technology" in industry or "healthcare" in industry:
            score += weights["industry"]

        if ipo_year and ipo_year > 2004:
            score += weights["growth_vs_blue_chip"]
        # Dividend Yield: Is the dividend yield less than 1%?
        if dividend_yield < 1:
            score += weights["dividends"]

        # REIT: Is it not a REIT stock?
        if "reit" not in industry:
            score += weights["reit"]

        # Severity of Loss: Did the stock lose more than 5%?
        if percentage_change < -5:  # Assuming percentage_change is negative for losses
            score += weights["severity_of_loss"]

        # Ranking: Based on position in biggest loser hierarchy
        ranking_score = max(10 - (ranking - 1) * 2, 0)  # 10% for #1, 8% for #2, etc.
        score += ranking_score

        # Return the confidence score
        return score
    
    except Exception as e:
        print(f"Error calculating confidence score for {ticker}: {e}")
        return 0.0

def get_biggest_losers(data, date):
    daily_changes = {}
    percentage_change = 0
    for symbol, df in data.items():
        if date in df.index:
            close_price = df.loc[date, 'Close']
            open_price = df.loc[date, 'Open']
            percentage_change = (close_price - open_price) / open_price * 100
            daily_changes[symbol] = percentage_change
            
            
    losers = sorted(daily_changes, key=daily_changes.get)[:5]
    rank = 1
    
    temp = losers
    storevalues = []
    for loser in temp:
        
        confidence_score = calculate_confidence_score(loser, daily_changes[loser], rank)
        rank = rank + 1
        if(confidence_score < 70):
            storevalues.append(loser)
                
        
    for s in storevalues:
        losers.remove(s)
    # print(losers)
    return losers, percentage_change

def calculate_return(data, symbol, start_date, pc):
    try:
    
        
        # Get the start price

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
    # 
    # 
    winners = df_results[df_results['return_2y'] > 0]
    winning_percentage = len(winners) / len(df_results) * 100
    average_return_of_winners = winners['return_2y'].mean()
    average_return_overall = df_results['return_2y'].mean()
    print("Start Date:", sd )
    print("End Date:", ed)
    print("Number of Stocks to Meet Criteria:", len(df_results))
    print(f"Winning Percentage: {winning_percentage:.2f}%")
    print(f"Average Return of Winners: {average_return_of_winners:.2f}%")
    print(f"Average Return Overall: {average_return_overall:.2f}%")
    

    # Trend Analysis: Day of the Week
    # df_results['day_of_week'] = df_results['date'].dt.day_name()
    # day_of_week_trends = df_results.groupby('day_of_week')['return_2y'].mean()
    
    # print("Day of the Week Trends:", day_of_week_trends)

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
