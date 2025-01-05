import pandas as pd
import yfinance as yf
import numpy as py
from datetime import timedelta

sp500_symbols = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
print(sp500_symbols)