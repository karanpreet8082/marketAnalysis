"""
Configuration settings for the Stock Market Analysis Agent.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
HISTORICAL_DIR = DATA_DIR / "historical"

# API Configuration
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"

# Email Configuration
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Investment Budget
BUDGET_MIN = int(os.getenv("INVESTMENT_BUDGET_MIN", 10000))
BUDGET_MAX = int(os.getenv("INVESTMENT_BUDGET_MAX", 50000))

# Technical Analysis Parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

SMA_SHORT = 20
SMA_MEDIUM = 50
SMA_LONG = 200

BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

# Risk Categorization Thresholds (Market Cap in Crores)
LARGE_CAP_THRESHOLD = 50000  # > ₹50,000 Cr = Large Cap
MID_CAP_THRESHOLD = 10000    # ₹10,000-50,000 Cr = Mid Cap
                              # < ₹10,000 Cr = Small Cap

# Beta thresholds for risk classification
CONSERVATIVE_BETA_MAX = 1.0
MODERATE_BETA_MAX = 1.3

# Fundamental Filters
MAX_PE_RATIO = 50           # Exclude stocks with P/E > 50
MIN_VOLUME_AVG = 100000     # Minimum average daily volume
MIN_MARKET_CAP = 500        # Minimum market cap in Crores

# Position Sizing
MAX_POSITION_PERCENT = 20   # Max 20% of budget in single stock
MIN_STOCKS_IN_PORTFOLIO = 3 # Diversification minimum
MAX_STOCKS_IN_PORTFOLIO = 10

# Signal Thresholds
STRONG_BUY_THRESHOLD = 0.7
BUY_THRESHOLD = 0.5
SELL_THRESHOLD = -0.5
STRONG_SELL_THRESHOLD = -0.7

# Data Fetching
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 30  # seconds
RATE_LIMIT_DELAY = 0.5  # seconds between API calls
