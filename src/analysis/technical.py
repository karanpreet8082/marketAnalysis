"""
Technical Analysis module.

Calculates various technical indicators for stock analysis:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- SMA/EMA (Simple/Exponential Moving Averages)
- Bollinger Bands
- Volume Analysis
- Support/Resistance Levels
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import ta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, SMAIndicator, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange

from ..config import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    SMA_SHORT, SMA_MEDIUM, SMA_LONG,
    BOLLINGER_PERIOD, BOLLINGER_STD
)


class TechnicalAnalyzer:
    """Technical analysis calculator for stock data."""
    
    def __init__(self):
        self.indicators_cache: Dict[str, pd.DataFrame] = {}
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators for a stock.
        
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            
        Returns:
            DataFrame with all indicators added
        """
        if df is None or df.empty:
            return df
        
        df = df.copy()
        
        # Ensure lowercase column names
        df.columns = [col.lower() for col in df.columns]
        
        # RSI
        df = self._add_rsi(df)
        
        # MACD
        df = self._add_macd(df)
        
        # Moving Averages
        df = self._add_moving_averages(df)
        
        # Bollinger Bands
        df = self._add_bollinger_bands(df)
        
        # Volume indicators
        df = self._add_volume_indicators(df)
        
        # Additional indicators
        df = self._add_additional_indicators(df)
        
        return df
    
    def _add_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add RSI indicator."""
        rsi = RSIIndicator(close=df['close'], window=RSI_PERIOD)
        df['rsi'] = rsi.rsi()
        
        # RSI signals
        df['rsi_oversold'] = df['rsi'] < RSI_OVERSOLD
        df['rsi_overbought'] = df['rsi'] > RSI_OVERBOUGHT
        
        return df
    
    def _add_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add MACD indicator."""
        macd = MACD(
            close=df['close'],
            window_slow=MACD_SLOW,
            window_fast=MACD_FAST,
            window_sign=MACD_SIGNAL
        )
        
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        
        # MACD crossover signals
        df['macd_bullish_cross'] = (
            (df['macd'] > df['macd_signal']) & 
            (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        )
        df['macd_bearish_cross'] = (
            (df['macd'] < df['macd_signal']) & 
            (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        )
        
        return df
    
    def _add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Simple and Exponential Moving Averages."""
        # Simple Moving Averages
        df['sma_20'] = SMAIndicator(close=df['close'], window=SMA_SHORT).sma_indicator()
        df['sma_50'] = SMAIndicator(close=df['close'], window=SMA_MEDIUM).sma_indicator()
        df['sma_200'] = SMAIndicator(close=df['close'], window=SMA_LONG).sma_indicator()
        
        # Exponential Moving Averages
        df['ema_20'] = EMAIndicator(close=df['close'], window=SMA_SHORT).ema_indicator()
        df['ema_50'] = EMAIndicator(close=df['close'], window=SMA_MEDIUM).ema_indicator()
        
        # Moving Average signals
        df['price_above_sma_20'] = df['close'] > df['sma_20']
        df['price_above_sma_50'] = df['close'] > df['sma_50']
        df['price_above_sma_200'] = df['close'] > df['sma_200']
        
        # Golden Cross (SMA 50 crosses above SMA 200)
        df['golden_cross'] = (
            (df['sma_50'] > df['sma_200']) & 
            (df['sma_50'].shift(1) <= df['sma_200'].shift(1))
        )
        
        # Death Cross (SMA 50 crosses below SMA 200)
        df['death_cross'] = (
            (df['sma_50'] < df['sma_200']) & 
            (df['sma_50'].shift(1) >= df['sma_200'].shift(1))
        )
        
        return df
    
    def _add_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands."""
        bb = BollingerBands(
            close=df['close'],
            window=BOLLINGER_PERIOD,
            window_dev=BOLLINGER_STD
        )
        
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()
        df['bb_pband'] = bb.bollinger_pband()  # % position within bands
        
        # Bollinger Band signals
        df['bb_breakout_upper'] = df['close'] > df['bb_upper']
        df['bb_breakout_lower'] = df['close'] < df['bb_lower']
        
        return df
    
    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based indicators."""
        # Average volume (20-day)
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        
        # Volume ratio (current vs average)
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # High volume flag (> 1.5x average)
        df['high_volume'] = df['volume_ratio'] > 1.5
        
        # On-Balance Volume (OBV) simplified
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        
        return df
    
    def _add_additional_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add additional useful indicators."""
        # Average True Range (ATR) for volatility
        atr = AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14
        )
        df['atr'] = atr.average_true_range()
        df['atr_percent'] = (df['atr'] / df['close']) * 100
        
        # ADX for trend strength
        adx = ADXIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14
        )
        df['adx'] = adx.adx()
        df['strong_trend'] = df['adx'] > 25
        
        # Price change metrics
        df['daily_return'] = df['close'].pct_change()
        df['weekly_return'] = df['close'].pct_change(periods=5)
        df['monthly_return'] = df['close'].pct_change(periods=20)
        
        # 52-week high/low proximity
        df['high_52w'] = df['high'].rolling(window=252, min_periods=20).max()
        df['low_52w'] = df['low'].rolling(window=252, min_periods=20).min()
        df['pct_from_52w_high'] = (df['close'] - df['high_52w']) / df['high_52w'] * 100
        df['pct_from_52w_low'] = (df['close'] - df['low_52w']) / df['low_52w'] * 100
        
        return df
    
    def get_technical_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """
        Calculate an overall technical score for a stock.
        
        Returns:
            Tuple of (score from -1 to 1, breakdown dict)
        """
        if df is None or df.empty:
            return 0.0, {}
        
        latest = df.iloc[-1]
        score = 0.0
        breakdown = {}
        
        # RSI Score (-1 to 1)
        rsi = latest.get('rsi', 50)
        if rsi < RSI_OVERSOLD:
            rsi_score = 0.5  # Oversold = bullish
        elif rsi > RSI_OVERBOUGHT:
            rsi_score = -0.5  # Overbought = bearish
        else:
            rsi_score = (50 - rsi) / 50 * 0.3  # Neutral zone
        breakdown['rsi'] = {'value': rsi, 'score': rsi_score}
        score += rsi_score * 0.2
        
        # MACD Score
        macd = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        macd_hist = latest.get('macd_histogram', 0)
        
        if macd > macd_signal and macd_hist > 0:
            macd_score = 0.5
        elif macd < macd_signal and macd_hist < 0:
            macd_score = -0.5
        else:
            macd_score = 0.1 if macd_hist > 0 else -0.1
        breakdown['macd'] = {'value': macd_hist, 'score': macd_score}
        score += macd_score * 0.2
        
        # Moving Average Score
        ma_score = 0.0
        if latest.get('price_above_sma_20', False):
            ma_score += 0.15
        if latest.get('price_above_sma_50', False):
            ma_score += 0.2
        if latest.get('price_above_sma_200', False):
            ma_score += 0.25
        ma_score -= 0.3  # Center the score
        breakdown['moving_averages'] = {'score': ma_score}
        score += ma_score * 0.25
        
        # Bollinger Band Score
        bb_pband = latest.get('bb_pband', 0.5)
        if bb_pband < 0.2:
            bb_score = 0.3  # Near lower band = potential bounce
        elif bb_pband > 0.8:
            bb_score = -0.3  # Near upper band = potential pullback
        else:
            bb_score = 0.0
        breakdown['bollinger'] = {'pband': bb_pband, 'score': bb_score}
        score += bb_score * 0.15
        
        # Volume Score
        volume_ratio = latest.get('volume_ratio', 1.0)
        daily_return = latest.get('daily_return', 0.0)
        
        if volume_ratio > 1.5 and daily_return > 0:
            volume_score = 0.3  # High volume up move = bullish
        elif volume_ratio > 1.5 and daily_return < 0:
            volume_score = -0.3  # High volume down move = bearish
        else:
            volume_score = 0.0
        breakdown['volume'] = {'ratio': volume_ratio, 'score': volume_score}
        score += volume_score * 0.1
        
        # Trend Strength (ADX)
        adx = latest.get('adx', 20)
        trend_score = 0.1 if adx > 25 else 0.0
        breakdown['trend_strength'] = {'adx': adx, 'score': trend_score}
        score += trend_score * 0.1
        
        # Clamp score to [-1, 1]
        score = max(-1.0, min(1.0, score))
        breakdown['total'] = score
        
        return score, breakdown
    
    def get_support_resistance(self, df: pd.DataFrame, lookback: int = 60) -> Dict:
        """
        Identify key support and resistance levels.
        
        Returns:
            Dict with support and resistance levels
        """
        if df is None or len(df) < lookback:
            return {'support': [], 'resistance': []}
        
        recent = df.tail(lookback)
        
        # Find local minima for support
        lows = recent['low'].values
        support_levels = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_levels.append(lows[i])
        
        # Find local maxima for resistance
        highs = recent['high'].values
        resistance_levels = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_levels.append(highs[i])
        
        # Get recent significant levels
        current_price = df['close'].iloc[-1]
        
        return {
            'support': sorted([s for s in support_levels if s < current_price], reverse=True)[:3],
            'resistance': sorted([r for r in resistance_levels if r > current_price])[:3],
            'current_price': current_price
        }
