import csv
import time
import yfinance as yf
import pandas as pd

def fetch_stock_info(tickers, output_file, delay=2):
    # Create a list to store stock data
    stock_data = []

    # Loop through each ticker and fetch data with a delay
    for ticker in tickers:
        try:
            # Fetch data for the current ticker
            ticker_obj = yf.Ticker(ticker)
            
            # Get the info dictionary
            info = ticker_obj.info
            
            # Extract relevant fields
            industry = info.get('industry', 'N/A')
            dividend_yield = info.get('dividendYield', 'N/A')
            if dividend_yield != 'N/A':
                dividend_yield = round(dividend_yield * 100, 2)  # Convert to percentage
            volume = info.get('volume', 'N/A')
            
            # Add the stock's data to the list
            stock_data.append({
                'Ticker': ticker,
                'Industry': industry,
                'Dividend Yield': dividend_yield,
                'Volume': volume
            })

            print(f"Fetched data for {ticker}")

        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            stock_data.append({
                'Ticker': ticker,
                'Industry': 'Error',
                'Dividend Yield': 'Error',
                'Volume': 'Error'
            })

        # Wait for the specified delay to avoid hitting rate limits
        time.sleep(delay)

    # Write the data to a CSV file
    with open(output_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Ticker', 'Industry', 'Dividend Yield', 'Volume'])
        writer.writeheader()
        writer.writerows(stock_data)

    print(f"Data written to {output_file}")

# Read tickers from input CSV (single row)
input_file = 'SANDPNoRepeats.csv'
output_file = 'fixedUp.csv'

tickers = []
with open(input_file, mode='r') as file:
    reader = csv.reader(file)
    for row in reader:
        tickers = row  # Read all tickers from the single row

# Fetch stock info with a 2-second delay between requests
fetch_stock_info(tickers, output_file, delay=2)