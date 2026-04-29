"""
Twelve Data API fetcher - backup data source.

Used when Yahoo Finance fails or for additional data points.
Free tier: 800 API calls/day
"""

import time
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import logging

from ..config import (
    TWELVE_DATA_API_KEY, TWELVE_DATA_BASE_URL,
    MAX_RETRIES, RETRY_DELAY, REQUEST_TIMEOUT, RATE_LIMIT_DELAY
)

logger = logging.getLogger(__name__)


class TwelveDataFetcher:
    """Backup data fetcher using Twelve Data API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or TWELVE_DATA_API_KEY
        self.base_url = TWELVE_DATA_BASE_URL
        self.api_calls_made = 0
        self.daily_limit = 800
        
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API request with retry logic."""
        if not self.api_key:
            logger.warning("Twelve Data API key not configured")
            return None
        
        if self.api_calls_made >= self.daily_limit:
            logger.error("Daily API limit reached")
            return None
        
        params['apikey'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                self.api_calls_made += 1
                
                if response.status_code == 200:
                    data = response.json()
                    if 'code' in data and data['code'] != 200:
                        logger.error(f"API error: {data.get('message', 'Unknown error')}")
                        return None
                    return data
                elif response.status_code == 429:
                    logger.warning("Rate limited, waiting...")
                    time.sleep(60)
                else:
                    logger.error(f"HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.error(f"Request timeout for {endpoint}")
            except Exception as e:
                logger.error(f"Request failed: {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
        
        return None
    
    def fetch_time_series(
        self, 
        symbol: str, 
        interval: str = "1day",
        outputsize: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical time series data.
        
        Args:
            symbol: Stock symbol (without .NS suffix)
            interval: Time interval ('1min', '5min', '1day', '1week')
            outputsize: Number of data points to return
            
        Returns:
            DataFrame with OHLCV data
        """
        # Convert to Twelve Data format (add :NSE suffix for NSE stocks)
        td_symbol = f"{symbol}:NSE"
        
        params = {
            'symbol': td_symbol,
            'interval': interval,
            'outputsize': outputsize,
            'format': 'JSON'
        }
        
        data = self._make_request('time_series', params)
        
        if not data or 'values' not in data:
            return None
        
        try:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            
            # Convert to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.sort_index()
            df['symbol'] = symbol
            
            time.sleep(RATE_LIMIT_DELAY)
            return df
            
        except Exception as e:
            logger.error(f"Failed to parse data for {symbol}: {e}")
            return None
    
    def fetch_quote(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time quote for a symbol."""
        td_symbol = f"{symbol}:NSE"
        
        params = {'symbol': td_symbol}
        data = self._make_request('quote', params)
        
        if not data:
            return None
        
        time.sleep(RATE_LIMIT_DELAY)
        
        return {
            'symbol': symbol,
            'name': data.get('name'),
            'price': float(data.get('close', 0)),
            'open': float(data.get('open', 0)),
            'high': float(data.get('high', 0)),
            'low': float(data.get('low', 0)),
            'volume': int(data.get('volume', 0)),
            'change': float(data.get('change', 0)),
            'change_percent': float(data.get('percent_change', 0)),
            'previous_close': float(data.get('previous_close', 0)),
            'fifty_two_week_high': float(data.get('fifty_two_week', {}).get('high', 0)),
            'fifty_two_week_low': float(data.get('fifty_two_week', {}).get('low', 0)),
        }
    
    def fetch_technical_indicator(
        self, 
        symbol: str, 
        indicator: str,
        interval: str = "1day",
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Fetch pre-calculated technical indicator.
        
        Args:
            symbol: Stock symbol
            indicator: Indicator name ('rsi', 'macd', 'sma', 'ema', 'bbands')
            interval: Time interval
            **kwargs: Additional indicator parameters
            
        Returns:
            DataFrame with indicator values
        """
        td_symbol = f"{symbol}:NSE"
        
        params = {
            'symbol': td_symbol,
            'interval': interval,
            'outputsize': 100,
            **kwargs
        }
        
        data = self._make_request(indicator, params)
        
        if not data or 'values' not in data:
            return None
        
        try:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.sort_index()
            
            # Convert to numeric
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            time.sleep(RATE_LIMIT_DELAY)
            return df
            
        except Exception as e:
            logger.error(f"Failed to parse {indicator} for {symbol}: {e}")
            return None
    
    def get_api_usage(self) -> Dict:
        """Get current API usage stats."""
        return {
            'calls_made': self.api_calls_made,
            'daily_limit': self.daily_limit,
            'remaining': self.daily_limit - self.api_calls_made
        }
    
    def reset_usage_counter(self):
        """Reset the API usage counter (call at start of new day)."""
        self.api_calls_made = 0
