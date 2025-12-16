"""
Data API endpoints for stock metadata and S&P 500 information.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, date
from typing import List, Optional

from app.services.stock_data import (
    sp500_historical,
    load_stock_metadata,
    get_sp500_tickers_for_date,
    get_all_historical_tickers
)

router = APIRouter()


@router.get("/sp500/tickers")
async def get_sp500_tickers(for_date: Optional[date] = None):
    """
    Get S&P 500 constituents.
    If date is provided, returns the historical composition for that date.
    Otherwise returns all tickers that have ever been in the S&P 500.
    """
    if for_date:
        tickers = get_sp500_tickers_for_date(datetime.combine(for_date, datetime.min.time()))
        return {
            'date': for_date.isoformat(),
            'count': len(tickers),
            'tickers': sorted(tickers)
        }
    else:
        tickers = get_all_historical_tickers()
        return {
            'description': 'All tickers that have ever been in the S&P 500',
            'count': len(tickers),
            'tickers': sorted(tickers)
        }


@router.get("/sp500/date-range")
async def get_historical_date_range():
    """Get the date range of historical S&P 500 data"""
    start, end = sp500_historical.get_date_range()
    return {
        'start_date': start.date().isoformat() if start else None,
        'end_date': end.date().isoformat() if end else None
    }


@router.get("/metadata")
async def get_stock_metadata(ticker: Optional[str] = None):
    """
    Get stock metadata (industry, dividend yield, volume).
    If ticker is provided, returns metadata for that stock.
    Otherwise returns metadata for all stocks.
    """
    metadata = load_stock_metadata()

    if ticker:
        if ticker not in metadata:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        return {
            'ticker': ticker,
            **metadata[ticker]
        }

    return {
        'count': len(metadata),
        'stocks': metadata
    }


@router.get("/industries")
async def get_industries():
    """Get a list of all unique industries"""
    metadata = load_stock_metadata()
    industries = {}
    for data in metadata.values():
        industry = data['industry']
        industries[industry] = industries.get(industry, 0) + 1

    sorted_industries = sorted(industries.items(), key=lambda x: -x[1])
    return {
        'count': len(industries),
        'industries': [{'name': k, 'stock_count': v} for k, v in sorted_industries]
    }
