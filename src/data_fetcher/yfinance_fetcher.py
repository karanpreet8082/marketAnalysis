"""
Yahoo Finance data fetcher for Indian stocks.

Primary data source using the yfinance library.
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import logging

from ..config import (
    MAX_RETRIES, RETRY_DELAY, REQUEST_TIMEOUT, RATE_LIMIT_DELAY,
    MIN_VOLUME_AVG, MIN_MARKET_CAP
)

logger = logging.getLogger(__name__)


class YFinanceFetcher:
    """Fetches stock data from Yahoo Finance."""
    
    def __init__(self):
        self.cache: Dict[str, pd.DataFrame] = {}
        self.info_cache: Dict[str, Dict] = {}
        self.failed_symbols: List[str] = []
    
    def fetch_historical_data(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data for a stock.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            period: Data period ('1mo', '3mo', '6mo', '1y', '2y', '5y')
            interval: Data interval ('1d', '1wk', '1mo')
            
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        cache_key = f"{symbol}_{period}_{interval}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        for attempt in range(MAX_RETRIES):
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval, timeout=REQUEST_TIMEOUT)
                
                if df.empty:
                    logger.warning(f"No data returned for {symbol}")
                    return None
                
                # Standardize column names
                df.columns = [col.lower() for col in df.columns]
                
                # Add symbol column
                df['symbol'] = symbol.replace('.NS', '')
                
                self.cache[cache_key] = df
                time.sleep(RATE_LIMIT_DELAY)
                
                return df
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {symbol}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
        
        self.failed_symbols.append(symbol)
        return None
    
    def fetch_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        Fetch fundamental stock information.
        
        Returns dict with:
        - marketCap
        - forwardPE / trailingPE
        - priceToBook
        - beta
        - sector
        - industry
        - dividendYield
        - etc.
        """
        if symbol in self.info_cache:
            return self.info_cache[symbol]
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'symbol' not in info:
                return None
            
            # Extract relevant fields with defaults
            stock_info = {
                'symbol': symbol.replace('.NS', ''),
                'name': info.get('longName', info.get('shortName', symbol)),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'market_cap_cr': info.get('marketCap', 0) / 10000000,  # Convert to Crores
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'beta': info.get('beta', 1.0),
                'dividend_yield': info.get('dividendYield', 0),
                'eps': info.get('trailingEps'),
                'book_value': info.get('bookValue'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume', 0),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'previous_close': info.get('previousClose'),
            }
            
            self.info_cache[symbol] = stock_info
            time.sleep(RATE_LIMIT_DELAY)
            
            return stock_info
            
        except Exception as e:
            logger.error(f"Failed to fetch info for {symbol}: {e}")
            return None
    
    def fetch_multiple_stocks(
        self, 
        symbols: List[str], 
        period: str = "1y",
        progress_callback=None
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Dict]]:
        """
        Fetch data for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            period: Data period
            progress_callback: Optional callback(current, total, symbol)
            
        Returns:
            Tuple of (historical_data_dict, stock_info_dict)
        """
        historical_data = {}
        stock_info = {}
        total = len(symbols)
        
        for i, symbol in enumerate(symbols):
            if progress_callback:
                progress_callback(i + 1, total, symbol)
            
            # Fetch historical data
            hist_df = self.fetch_historical_data(symbol, period=period)
            if hist_df is not None and not hist_df.empty:
                historical_data[symbol] = hist_df
            
            # Fetch fundamental info
            info = self.fetch_stock_info(symbol)
            if info:
                # Apply basic filters
                if self._passes_basic_filters(info):
                    stock_info[symbol] = info
        
        logger.info(f"Fetched {len(historical_data)} stocks with historical data")
        logger.info(f"Fetched {len(stock_info)} stocks with fundamental info")
        logger.info(f"Failed symbols: {len(self.failed_symbols)}")
        
        return historical_data, stock_info
    
    def _passes_basic_filters(self, info: Dict) -> bool:
        """Check if stock passes basic fundamental filters."""
        # Filter by minimum volume
        if info.get('avg_volume', 0) < MIN_VOLUME_AVG:
            return False
        
        # Filter by minimum market cap (in Crores)
        if info.get('market_cap_cr', 0) < MIN_MARKET_CAP:
            return False
        
        # Must have a valid price
        if not info.get('current_price'):
            return False
        
        return True
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for a list of symbols."""
        prices = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d")
                if not data.empty:
                    prices[symbol] = data['Close'].iloc[-1]
                time.sleep(RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Failed to get price for {symbol}: {e}")
        
        return prices
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        self.info_cache.clear()
        self.failed_symbols.clear()
