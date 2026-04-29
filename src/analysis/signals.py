"""
Signal Generator module.

Combines technical and fundamental analysis to generate
BUY/SELL/HOLD signals with confidence scores.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd

from ..config import (
    STRONG_BUY_THRESHOLD, BUY_THRESHOLD,
    SELL_THRESHOLD, STRONG_SELL_THRESHOLD,
    CONSERVATIVE_BETA_MAX, MODERATE_BETA_MAX,
    LARGE_CAP_THRESHOLD, MID_CAP_THRESHOLD
)


class Signal(Enum):
    """Trading signal types."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class RiskBucket(Enum):
    """Risk categorization for portfolio allocation."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class StockSignal:
    """Complete signal data for a stock."""
    symbol: str
    name: str
    sector: str
    signal: Signal
    confidence: float  # 0 to 1
    technical_score: float  # -1 to 1
    fundamental_score: float  # -1 to 1
    combined_score: float  # -1 to 1
    risk_bucket: RiskBucket
    current_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    reasons: List[str]
    technical_breakdown: Dict
    fundamental_breakdown: Dict


class SignalGenerator:
    """Generates trading signals by combining technical and fundamental analysis."""
    
    def __init__(
        self,
        technical_weight: float = 0.5,
        fundamental_weight: float = 0.5
    ):
        self.technical_weight = technical_weight
        self.fundamental_weight = fundamental_weight
    
    def generate_signal(
        self,
        symbol: str,
        technical_df: pd.DataFrame,
        technical_score: float,
        technical_breakdown: Dict,
        fundamental_analysis: Dict
    ) -> Optional[StockSignal]:
        """
        Generate a trading signal for a stock.
        
        Args:
            symbol: Stock symbol
            technical_df: DataFrame with technical indicators
            technical_score: Technical analysis score (-1 to 1)
            technical_breakdown: Breakdown of technical scores
            fundamental_analysis: Fundamental analysis results
            
        Returns:
            StockSignal object or None if insufficient data
        """
        if technical_df is None or technical_df.empty or not fundamental_analysis:
            return None
        
        # Get latest data
        latest = technical_df.iloc[-1]
        
        # Extract scores
        fundamental_score = fundamental_analysis.get('fundamental_score', 0)
        
        # Combined score
        combined_score = (
            technical_score * self.technical_weight +
            fundamental_score * self.fundamental_weight
        )
        
        # Determine signal
        signal, confidence = self._determine_signal(combined_score, technical_score, fundamental_score)
        
        # Determine risk bucket
        risk_bucket = self._determine_risk_bucket(fundamental_analysis)
        
        # Calculate target price and stop loss
        current_price = fundamental_analysis.get('price_analysis', {}).get('current_price', 0)
        target_price, stop_loss = self._calculate_targets(
            current_price, signal, latest, risk_bucket
        )
        
        # Generate reasons
        reasons = self._generate_reasons(
            signal, technical_breakdown, fundamental_analysis
        )
        
        return StockSignal(
            symbol=symbol,
            name=fundamental_analysis.get('name', symbol),
            sector=fundamental_analysis.get('sector', 'Unknown'),
            signal=signal,
            confidence=confidence,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            combined_score=combined_score,
            risk_bucket=risk_bucket,
            current_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            reasons=reasons,
            technical_breakdown=technical_breakdown,
            fundamental_breakdown=fundamental_analysis
        )
    
    def _determine_signal(
        self,
        combined_score: float,
        technical_score: float,
        fundamental_score: float
    ) -> Tuple[Signal, float]:
        """Determine signal and confidence from scores."""
        # Base signal from combined score
        if combined_score >= STRONG_BUY_THRESHOLD:
            signal = Signal.STRONG_BUY
            confidence = min(1.0, 0.7 + (combined_score - STRONG_BUY_THRESHOLD))
        elif combined_score >= BUY_THRESHOLD:
            signal = Signal.BUY
            confidence = 0.5 + (combined_score - BUY_THRESHOLD) * 0.5
        elif combined_score <= STRONG_SELL_THRESHOLD:
            signal = Signal.STRONG_SELL
            confidence = min(1.0, 0.7 + abs(combined_score - STRONG_SELL_THRESHOLD))
        elif combined_score <= SELL_THRESHOLD:
            signal = Signal.SELL
            confidence = 0.5 + abs(combined_score - SELL_THRESHOLD) * 0.5
        else:
            signal = Signal.HOLD
            confidence = 0.4 + (1 - abs(combined_score)) * 0.3
        
        # Reduce confidence if technical and fundamental disagree
        if (technical_score > 0 and fundamental_score < 0) or \
           (technical_score < 0 and fundamental_score > 0):
            confidence *= 0.8
        
        # Boost confidence if both agree strongly
        if abs(technical_score) > 0.5 and abs(fundamental_score) > 0.5:
            if (technical_score > 0 and fundamental_score > 0) or \
               (technical_score < 0 and fundamental_score < 0):
                confidence = min(1.0, confidence * 1.15)
        
        return signal, round(confidence, 2)
    
    def _determine_risk_bucket(self, fundamental_analysis: Dict) -> RiskBucket:
        """Determine risk bucket based on fundamental characteristics."""
        market_cap_cr = fundamental_analysis.get('market_cap_cr', 0)
        beta = fundamental_analysis.get('quality', {}).get('beta', 1.0)
        
        # Market cap based classification
        if market_cap_cr >= LARGE_CAP_THRESHOLD:
            cap_risk = RiskBucket.CONSERVATIVE
        elif market_cap_cr >= MID_CAP_THRESHOLD:
            cap_risk = RiskBucket.MODERATE
        else:
            cap_risk = RiskBucket.AGGRESSIVE
        
        # Beta based adjustment
        if beta is None:
            beta = 1.0
        
        if beta <= CONSERVATIVE_BETA_MAX:
            beta_risk = RiskBucket.CONSERVATIVE
        elif beta <= MODERATE_BETA_MAX:
            beta_risk = RiskBucket.MODERATE
        else:
            beta_risk = RiskBucket.AGGRESSIVE
        
        # Combined - take the higher risk
        risk_order = [RiskBucket.CONSERVATIVE, RiskBucket.MODERATE, RiskBucket.AGGRESSIVE]
        return risk_order[max(risk_order.index(cap_risk), risk_order.index(beta_risk))]
    
    def _calculate_targets(
        self,
        current_price: float,
        signal: Signal,
        latest_data: pd.Series,
        risk_bucket: RiskBucket
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate target price and stop loss."""
        if not current_price or current_price <= 0:
            return None, None
        
        # Get ATR for volatility-based targets
        atr = latest_data.get('atr', current_price * 0.02)
        atr_percent = latest_data.get('atr_percent', 2.0)
        
        # Risk multipliers by bucket
        risk_multipliers = {
            RiskBucket.CONSERVATIVE: {'target': 1.5, 'stop': 1.0},
            RiskBucket.MODERATE: {'target': 2.0, 'stop': 1.5},
            RiskBucket.AGGRESSIVE: {'target': 3.0, 'stop': 2.0}
        }
        
        multiplier = risk_multipliers[risk_bucket]
        
        if signal in [Signal.STRONG_BUY, Signal.BUY]:
            # Target above current price
            target_price = current_price * (1 + (atr_percent / 100) * multiplier['target'])
            stop_loss = current_price * (1 - (atr_percent / 100) * multiplier['stop'])
        elif signal in [Signal.STRONG_SELL, Signal.SELL]:
            # For shorts or exit signals
            target_price = current_price * (1 - (atr_percent / 100) * multiplier['target'])
            stop_loss = current_price * (1 + (atr_percent / 100) * multiplier['stop'])
        else:
            target_price = None
            stop_loss = None
        
        return (
            round(target_price, 2) if target_price else None,
            round(stop_loss, 2) if stop_loss else None
        )
    
    def _generate_reasons(
        self,
        signal: Signal,
        technical_breakdown: Dict,
        fundamental_analysis: Dict
    ) -> List[str]:
        """Generate human-readable reasons for the signal."""
        reasons = []
        
        # Technical reasons
        if 'rsi' in technical_breakdown:
            rsi_val = technical_breakdown['rsi'].get('value', 50)
            if rsi_val < 30:
                reasons.append(f"RSI ({rsi_val:.1f}) indicates oversold condition")
            elif rsi_val > 70:
                reasons.append(f"RSI ({rsi_val:.1f}) indicates overbought condition")
        
        if 'macd' in technical_breakdown:
            macd_score = technical_breakdown['macd'].get('score', 0)
            if macd_score > 0.3:
                reasons.append("MACD shows bullish momentum")
            elif macd_score < -0.3:
                reasons.append("MACD shows bearish momentum")
        
        if 'moving_averages' in technical_breakdown:
            ma_score = technical_breakdown['moving_averages'].get('score', 0)
            if ma_score > 0.2:
                reasons.append("Price trading above key moving averages")
            elif ma_score < -0.2:
                reasons.append("Price trading below key moving averages")
        
        # Fundamental reasons
        valuation = fundamental_analysis.get('valuation', {})
        if 'undervalued_pe' in valuation.get('flags', []):
            reasons.append(f"Attractive P/E ratio ({valuation.get('pe_ratio', 'N/A')})")
        if 'overvalued' in valuation.get('flags', []):
            reasons.append(f"High P/E ratio ({valuation.get('pe_ratio', 'N/A')}) suggests overvaluation")
        
        price_analysis = fundamental_analysis.get('price_analysis', {})
        if 'near_52w_low' in price_analysis.get('flags', []):
            reasons.append("Trading near 52-week low - potential value")
        if 'near_52w_high' in price_analysis.get('flags', []):
            reasons.append("Trading near 52-week high - momentum play")
        if 'significant_correction' in price_analysis.get('flags', []):
            reasons.append("Significant correction from highs - potential recovery")
        
        quality = fundamental_analysis.get('quality', {})
        if 'highly_liquid' in quality.get('flags', []):
            reasons.append("High liquidity ensures easy entry/exit")
        
        # Add sector info
        sector = fundamental_analysis.get('sector', '')
        if sector and sector != 'Unknown':
            reasons.append(f"Sector: {sector}")
        
        return reasons[:5]  # Limit to 5 reasons
    
    def generate_signals_batch(
        self,
        technical_results: Dict[str, Tuple[pd.DataFrame, float, Dict]],
        fundamental_results: Dict[str, Dict]
    ) -> List[StockSignal]:
        """
        Generate signals for multiple stocks.
        
        Args:
            technical_results: Dict of symbol -> (df, score, breakdown)
            fundamental_results: Dict of symbol -> analysis
            
        Returns:
            List of StockSignal objects, sorted by combined score
        """
        signals = []
        
        for symbol in technical_results:
            if symbol not in fundamental_results:
                continue
            
            df, tech_score, tech_breakdown = technical_results[symbol]
            fund_analysis = fundamental_results[symbol]
            
            signal = self.generate_signal(
                symbol=symbol.replace('.NS', ''),
                technical_df=df,
                technical_score=tech_score,
                technical_breakdown=tech_breakdown,
                fundamental_analysis=fund_analysis
            )
            
            if signal:
                signals.append(signal)
        
        # Sort by combined score (highest first for buys)
        signals.sort(key=lambda x: x.combined_score, reverse=True)
        
        return signals
    
    def filter_actionable_signals(
        self,
        signals: List[StockSignal],
        min_confidence: float = 0.5
    ) -> Dict[str, List[StockSignal]]:
        """
        Filter signals to only actionable ones and group by action.
        
        Returns:
            Dict with 'buy', 'sell', 'hold' lists
        """
        result = {
            'buy': [],
            'sell': [],
            'hold': []
        }
        
        for signal in signals:
            if signal.confidence < min_confidence:
                continue
            
            if signal.signal in [Signal.STRONG_BUY, Signal.BUY]:
                result['buy'].append(signal)
            elif signal.signal in [Signal.STRONG_SELL, Signal.SELL]:
                result['sell'].append(signal)
            else:
                result['hold'].append(signal)
        
        # Sort buys by confidence (highest first)
        result['buy'].sort(key=lambda x: (x.confidence, x.combined_score), reverse=True)
        result['sell'].sort(key=lambda x: (x.confidence, abs(x.combined_score)), reverse=True)
        
        return result
