"""
Fundamental Analysis module.

Analyzes fundamental metrics of stocks:
- Valuation ratios (P/E, P/B, EV/EBITDA)
- Financial health indicators
- Growth metrics
- Dividend analysis
"""

from typing import Dict, Optional, Tuple, List
import pandas as pd
import numpy as np

from ..config import (
    MAX_PE_RATIO, MIN_VOLUME_AVG, MIN_MARKET_CAP,
    LARGE_CAP_THRESHOLD, MID_CAP_THRESHOLD
)


class FundamentalAnalyzer:
    """Fundamental analysis for stock evaluation."""
    
    def __init__(self):
        self.sector_pe_averages: Dict[str, float] = {}
    
    def analyze_stock(self, stock_info: Dict) -> Dict:
        """
        Perform comprehensive fundamental analysis on a stock.
        
        Args:
            stock_info: Dictionary with stock fundamentals from data fetcher
            
        Returns:
            Analysis results with scores and flags
        """
        if not stock_info:
            return {}
        
        analysis = {
            'symbol': stock_info.get('symbol', ''),
            'name': stock_info.get('name', ''),
            'sector': stock_info.get('sector', 'Unknown'),
            'industry': stock_info.get('industry', 'Unknown'),
        }
        
        # Market Cap Category
        market_cap_cr = stock_info.get('market_cap_cr', 0)
        analysis['market_cap_cr'] = market_cap_cr
        analysis['cap_category'] = self._get_cap_category(market_cap_cr)
        
        # Valuation Analysis
        analysis['valuation'] = self._analyze_valuation(stock_info)
        
        # Quality Score
        analysis['quality'] = self._analyze_quality(stock_info)
        
        # Dividend Analysis
        analysis['dividend'] = self._analyze_dividend(stock_info)
        
        # Price Analysis
        analysis['price_analysis'] = self._analyze_price(stock_info)
        
        # Overall fundamental score
        analysis['fundamental_score'] = self._calculate_overall_score(analysis)
        
        return analysis
    
    def _get_cap_category(self, market_cap_cr: float) -> str:
        """Classify stock by market capitalization."""
        if market_cap_cr >= LARGE_CAP_THRESHOLD:
            return 'large_cap'
        elif market_cap_cr >= MID_CAP_THRESHOLD:
            return 'mid_cap'
        else:
            return 'small_cap'
    
    def _analyze_valuation(self, info: Dict) -> Dict:
        """Analyze valuation metrics."""
        pe_ratio = info.get('pe_ratio')
        pb_ratio = info.get('pb_ratio')
        forward_pe = info.get('forward_pe')
        
        valuation = {
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'forward_pe': forward_pe,
            'score': 0.0,
            'flags': []
        }
        
        # P/E Analysis
        if pe_ratio is not None:
            if pe_ratio < 0:
                valuation['flags'].append('negative_earnings')
                valuation['score'] -= 0.3
            elif pe_ratio < 15:
                valuation['flags'].append('undervalued_pe')
                valuation['score'] += 0.4
            elif pe_ratio < 25:
                valuation['flags'].append('fairly_valued')
                valuation['score'] += 0.2
            elif pe_ratio < MAX_PE_RATIO:
                valuation['flags'].append('premium_valuation')
                valuation['score'] -= 0.1
            else:
                valuation['flags'].append('overvalued')
                valuation['score'] -= 0.3
        
        # P/B Analysis
        if pb_ratio is not None:
            if pb_ratio < 1:
                valuation['flags'].append('below_book_value')
                valuation['score'] += 0.2
            elif pb_ratio < 3:
                valuation['flags'].append('reasonable_pb')
                valuation['score'] += 0.1
            elif pb_ratio > 5:
                valuation['flags'].append('high_pb')
                valuation['score'] -= 0.1
        
        # Forward P/E vs Trailing P/E
        if forward_pe and pe_ratio and forward_pe > 0 and pe_ratio > 0:
            if forward_pe < pe_ratio * 0.85:
                valuation['flags'].append('earnings_growth_expected')
                valuation['score'] += 0.2
            elif forward_pe > pe_ratio * 1.15:
                valuation['flags'].append('earnings_decline_expected')
                valuation['score'] -= 0.2
        
        # Clamp score
        valuation['score'] = max(-1.0, min(1.0, valuation['score']))
        
        return valuation
    
    def _analyze_quality(self, info: Dict) -> Dict:
        """Analyze quality metrics."""
        quality = {
            'score': 0.0,
            'flags': []
        }
        
        # Beta analysis
        beta = info.get('beta', 1.0)
        quality['beta'] = beta
        
        if beta and beta < 0.8:
            quality['flags'].append('low_volatility')
            quality['score'] += 0.2
        elif beta and beta > 1.5:
            quality['flags'].append('high_volatility')
            quality['score'] -= 0.1
        
        # Volume liquidity
        avg_volume = info.get('avg_volume', 0)
        quality['avg_volume'] = avg_volume
        
        if avg_volume > 1000000:
            quality['flags'].append('highly_liquid')
            quality['score'] += 0.2
        elif avg_volume > MIN_VOLUME_AVG:
            quality['flags'].append('adequate_liquidity')
            quality['score'] += 0.1
        else:
            quality['flags'].append('low_liquidity')
            quality['score'] -= 0.2
        
        # Market cap (size factor)
        market_cap_cr = info.get('market_cap_cr', 0)
        if market_cap_cr > LARGE_CAP_THRESHOLD:
            quality['flags'].append('large_cap')
            quality['score'] += 0.15
        elif market_cap_cr > MID_CAP_THRESHOLD:
            quality['flags'].append('mid_cap')
        
        # Clamp score
        quality['score'] = max(-1.0, min(1.0, quality['score']))
        
        return quality
    
    def _analyze_dividend(self, info: Dict) -> Dict:
        """Analyze dividend metrics."""
        dividend = {
            'yield': info.get('dividend_yield', 0) or 0,
            'score': 0.0,
            'flags': []
        }
        
        div_yield = dividend['yield']
        
        if div_yield > 0.05:  # > 5%
            dividend['flags'].append('high_dividend')
            dividend['score'] += 0.3
        elif div_yield > 0.02:  # > 2%
            dividend['flags'].append('moderate_dividend')
            dividend['score'] += 0.15
        elif div_yield > 0:
            dividend['flags'].append('low_dividend')
            dividend['score'] += 0.05
        else:
            dividend['flags'].append('no_dividend')
        
        return dividend
    
    def _analyze_price(self, info: Dict) -> Dict:
        """Analyze current price position."""
        price_analysis = {
            'current_price': info.get('current_price', 0),
            'previous_close': info.get('previous_close', 0),
            'fifty_two_week_high': info.get('fifty_two_week_high', 0),
            'fifty_two_week_low': info.get('fifty_two_week_low', 0),
            'score': 0.0,
            'flags': []
        }
        
        current = price_analysis['current_price'] or 0
        high_52w = price_analysis['fifty_two_week_high'] or 0
        low_52w = price_analysis['fifty_two_week_low'] or 0
        
        if current and high_52w and low_52w and high_52w > low_52w:
            # Calculate position in 52-week range
            range_52w = high_52w - low_52w
            position = (current - low_52w) / range_52w
            price_analysis['position_in_52w_range'] = position
            
            if position < 0.3:
                price_analysis['flags'].append('near_52w_low')
                price_analysis['score'] += 0.3  # Potential value
            elif position > 0.9:
                price_analysis['flags'].append('near_52w_high')
                price_analysis['score'] -= 0.2  # Caution
            elif position > 0.7:
                price_analysis['flags'].append('trending_up')
                price_analysis['score'] += 0.1
            
            # Calculate % from 52-week high
            pct_from_high = ((current - high_52w) / high_52w) * 100
            price_analysis['pct_from_52w_high'] = pct_from_high
            
            if pct_from_high < -30:
                price_analysis['flags'].append('significant_correction')
                price_analysis['score'] += 0.2
        
        return price_analysis
    
    def _calculate_overall_score(self, analysis: Dict) -> float:
        """Calculate overall fundamental score."""
        score = 0.0
        weights = {
            'valuation': 0.35,
            'quality': 0.30,
            'dividend': 0.15,
            'price_analysis': 0.20
        }
        
        for component, weight in weights.items():
            if component in analysis and 'score' in analysis[component]:
                score += analysis[component]['score'] * weight
        
        return max(-1.0, min(1.0, score))
    
    def filter_stocks(
        self, 
        stocks_info: Dict[str, Dict],
        min_market_cap: float = MIN_MARKET_CAP,
        max_pe: float = MAX_PE_RATIO,
        min_volume: int = MIN_VOLUME_AVG
    ) -> List[Dict]:
        """
        Filter stocks based on fundamental criteria.
        
        Args:
            stocks_info: Dictionary of symbol -> stock info
            min_market_cap: Minimum market cap in Crores
            max_pe: Maximum P/E ratio
            min_volume: Minimum average daily volume
            
        Returns:
            List of stocks that pass all filters
        """
        filtered = []
        
        for symbol, info in stocks_info.items():
            # Market cap filter
            if info.get('market_cap_cr', 0) < min_market_cap:
                continue
            
            # Volume filter
            if info.get('avg_volume', 0) < min_volume:
                continue
            
            # P/E filter (exclude extremely high or negative)
            pe = info.get('pe_ratio')
            if pe is not None and (pe < 0 or pe > max_pe):
                continue
            
            # Must have valid price
            if not info.get('current_price'):
                continue
            
            filtered.append(info)
        
        return filtered
    
    def get_sector_comparison(
        self, 
        stock_info: Dict, 
        sector_stocks: List[Dict]
    ) -> Dict:
        """Compare stock to sector peers."""
        if not sector_stocks:
            return {}
        
        sector_pe_values = [s['pe_ratio'] for s in sector_stocks if s.get('pe_ratio') and s['pe_ratio'] > 0]
        sector_pb_values = [s['pb_ratio'] for s in sector_stocks if s.get('pb_ratio') and s['pb_ratio'] > 0]
        
        comparison = {
            'sector_avg_pe': np.mean(sector_pe_values) if sector_pe_values else None,
            'sector_avg_pb': np.mean(sector_pb_values) if sector_pb_values else None,
            'peer_count': len(sector_stocks)
        }
        
        stock_pe = stock_info.get('pe_ratio')
        if stock_pe and comparison['sector_avg_pe']:
            comparison['pe_vs_sector'] = (stock_pe / comparison['sector_avg_pe'] - 1) * 100
        
        return comparison
