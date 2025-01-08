import pandas as pd
import yfinance as yf
from datetime import timedelta

from tqdm import tqdm
from datetime import datetime
import pytz  # Import for timezone handling
import openai
from pydantic import BaseModel, Field


openai.api_key = ""

class TicketResolution(BaseModel):
    # class Step(BaseModel):
    #     description: str = Field(description="Description of the step taken.")
    #     action: str = Field(description="Action taken to resolve the issue.")

    # steps: list[Step]
    # final_resolution: str = Field(
    #     description="The final message that will be send to the customer."
    # )
    confidence: float = Field(description="Confidence Score based on the Analysis (0-100)")


def get_ticket_response_pydantic(ticker, rank, sol):
    query = f"""
            Provide a quick analysis for the company with the stock ticker: {ticker}. Follow these **exact rules** to calculate a confidence score (0–100) based on weighted criteria. **Output only the final number.**

            1. **Industry (20%)**: Is it a technology or innovative healthcare company?  
            - Assign 20% if "Yes"; 0% otherwise.

            2. **International Presence (5%)**: Does the company have significant international revenue?  
            - Assign 5% if "Yes"; 0% otherwise.

            3. **Growth vs. Blue Chip (15%)**: Is it a growth-oriented company rather than a blue-chip traditional one?  
            - Assign 15% if "Yes"; 0% otherwise.

            4. **Dividends (20%)**: Is the dividend yield less than 1%?  
            - Assign 20% if "Yes"; 0% otherwise.

            5. **REIT (15%)**: Is it not an REIT stock?  
            - Assign 15% if "Yes"; 0% otherwise.

            6. **Severity of Loss (15%)**: Based on {sol}, did the stock lose more than 5% on the day?  
            - Assign 15% if "Yes"; 0% otherwise.

            7. **Ranking Among Biggest Losers (10%)**: Based on the {rank} variable:
            - Assign 10% if it is the biggest loser.
            - Assign 8% if it is the 2nd biggest loser.
            - Assign 6% if it is the 3rd biggest loser.
            - Assign 4% if it is the 4th biggest loser.
            - Assign 2% if it is the 5th biggest loser.

            ---

            **Instructions for Output**: 
            1. Evaluate each criterion above and calculate its percentage contribution.
            2. Add all contributions to produce a total confidence score (0–100).
            3. Output **only the final number** (e.g., "85").

            ---
            """

    system_prompt = """
        You are a stock analyzer producing a confidence score. 
        """
    completion = openai.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        response_format=TicketResolution,
    )

    return completion.choices[0].message.parsed

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
    losers = sorted(daily_changes, key=daily_changes.get)[:5]
    #AI SECTION
    rank = 1
    for loser in losers:
        response_pydantic = get_ticket_response_pydantic(loser, rank, daily_changes[loser])
        print(loser)
        print(daily_changes[loser])
        print(response_pydantic.model_dump())
        
        # validation_result = validate_ticker_with_ai(loser, rank)
        rank = rank + 1
        # print(loser)
        # print(validation_result)
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
