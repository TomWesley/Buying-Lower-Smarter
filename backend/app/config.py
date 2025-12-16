import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECT_ROOT = BASE_DIR.parent

# Database
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/stocks.db"
SYNC_DATABASE_URL = f"sqlite:///{DATA_DIR}/stocks.db"

# Data files from original project
SP500_TICKERS_FILE = PROJECT_ROOT / "SANDPNoRepeats.csv"
STOCK_METADATA_FILE = PROJECT_ROOT / "fixedUp.csv"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)
