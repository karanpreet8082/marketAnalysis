"""
Risk Manager module.

Categorizes stocks and signals into risk buckets:
- Conservative: Large cap, low beta, stable dividend
- Moderate: Mid cap, moderate beta, growth stocks
- Aggressive: Small cap, high beta, momentum plays
"""

from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

from ..config import (
    CONSERVATIVE_BETA_MAX, MODERATE_BETA_MAX,
    LARGE_CAP_THRESHOLD, MID_CAP_THRESHOLD
)
from ..analysis.signals import StockSignal, RiskBucket, Signal


@dataclass
class RiskProfile:
    """Risk profile for allocation purposes."""
    bucket: RiskBucket
    allocation_percent: float  # Target % of portfolio
    max_position_percent: float  # Max single position
    position_count: int  # Target number of positions
    description: str


class RiskManager:
    """Manages risk categorization and allocation limits."""
    
    # Default risk profiles
    DEFAULT_PROFILES = {
        RiskBucket.CONSERVATIVE: RiskProfile(
            bucket=RiskBucket.CONSERVATIVE,
            allocation_percent=50.0,
            max_position_percent=20.0,
            position_count=3,
            description="Large cap, stable companies with lower volatility"
        ),
        RiskBucket.MODERATE: RiskProfile(
            bucket=RiskBucket.MODERATE,
            allocation_percent=35.0,
            max_position_percent=15.0,
            position_count=3,
            description="Mid cap growth companies with moderate risk"
        ),
        RiskBucket.AGGRESSIVE: RiskProfile(
            bucket=RiskBucket.AGGRESSIVE,
            allocation_percent=15.0,
            max_position_percent=10.0,
            position_count=2,
            description="Small cap, high growth potential with higher volatility"
        )
    }
    
    def __init__(self, profiles: Dict[RiskBucket, RiskProfile] = None):
        self.profiles = profiles or self.DEFAULT_PROFILES
    
    def categorize_signals(
        self,
        signals: List[StockSignal]
    ) -> Dict[RiskBucket, List[StockSignal]]:
        """
        Group signals by risk bucket.
        
        Args:
            signals: List of stock signals
            
        Returns:
            Dict mapping risk bucket to signals
        """
        categorized = {
            RiskBucket.CONSERVATIVE: [],
            RiskBucket.MODERATE: [],
            RiskBucket.AGGRESSIVE: []
        }
        
        for signal in signals:
            categorized[signal.risk_bucket].append(signal)
        
        # Sort each bucket by combined score
        for bucket in categorized:
            categorized[bucket].sort(
                key=lambda x: (x.confidence, x.combined_score),
                reverse=True
            )
        
        return categorized
    
    def get_top_picks_by_bucket(
        self,
        categorized_signals: Dict[RiskBucket, List[StockSignal]],
        action: str = 'buy'
    ) -> Dict[RiskBucket, List[StockSignal]]:
        """
        Get top picks for each risk bucket.
        
        Args:
            categorized_signals: Signals grouped by risk bucket
            action: 'buy' or 'sell'
            
        Returns:
            Top picks per bucket
        """
        top_picks = {}
        
        for bucket, signals in categorized_signals.items():
            profile = self.profiles[bucket]
            
            # Filter by action
            if action == 'buy':
                filtered = [s for s in signals if s.signal in [Signal.STRONG_BUY, Signal.BUY]]
            elif action == 'sell':
                filtered = [s for s in signals if s.signal in [Signal.STRONG_SELL, Signal.SELL]]
            else:
                filtered = signals
            
            # Take top N based on profile position count
            top_picks[bucket] = filtered[:profile.position_count]
        
        return top_picks
    
    def calculate_risk_metrics(
        self,
        signals: List[StockSignal]
    ) -> Dict:
        """
        Calculate portfolio risk metrics from selected signals.
        
        Returns:
            Risk metrics dict
        """
        if not signals:
            return {
                'avg_beta': 0,
                'bucket_distribution': {},
                'sector_concentration': {},
                'diversification_score': 0
            }
        
        # Calculate average beta
        betas = []
        for signal in signals:
            beta = signal.fundamental_breakdown.get('quality', {}).get('beta')
            if beta:
                betas.append(beta)
        avg_beta = sum(betas) / len(betas) if betas else 1.0
        
        # Bucket distribution
        bucket_dist = {}
        for bucket in RiskBucket:
            count = sum(1 for s in signals if s.risk_bucket == bucket)
            bucket_dist[bucket.value] = count
        
        # Sector concentration
        sectors = {}
        for signal in signals:
            sector = signal.sector
            sectors[sector] = sectors.get(sector, 0) + 1
        
        # Diversification score (0-1, higher is better)
        unique_sectors = len(set(s.sector for s in signals))
        unique_buckets = len(set(s.risk_bucket for s in signals))
        diversification = (unique_sectors / max(len(signals), 1)) * 0.7 + \
                         (unique_buckets / 3) * 0.3
        
        return {
            'avg_beta': round(avg_beta, 2),
            'bucket_distribution': bucket_dist,
            'sector_concentration': sectors,
            'diversification_score': round(diversification, 2)
        }
    
    def validate_portfolio_risk(
        self,
        signals: List[StockSignal],
        budget: float
    ) -> Dict:
        """
        Validate if selected portfolio meets risk guidelines.
        
        Returns:
            Validation results with warnings
        """
        warnings = []
        
        # Check bucket allocation
        bucket_counts = {}
        for bucket in RiskBucket:
            bucket_counts[bucket] = sum(1 for s in signals if s.risk_bucket == bucket)
        
        # Check if aggressive is too high
        total = len(signals)
        if total > 0:
            aggressive_pct = bucket_counts[RiskBucket.AGGRESSIVE] / total * 100
            if aggressive_pct > 30:
                warnings.append(
                    f"High aggressive allocation ({aggressive_pct:.0f}%) - consider reducing"
                )
        
        # Check diversification
        sectors = set(s.sector for s in signals)
        if len(sectors) < 3 and len(signals) >= 5:
            warnings.append("Low sector diversification - concentrated in few sectors")
        
        # Check for sector overconcentration
        sector_counts = {}
        for signal in signals:
            sector_counts[signal.sector] = sector_counts.get(signal.sector, 0) + 1
        
        for sector, count in sector_counts.items():
            if count > len(signals) * 0.4:
                warnings.append(f"High concentration in {sector} sector ({count} stocks)")
        
        return {
            'is_valid': len(warnings) == 0,
            'warnings': warnings,
            'bucket_distribution': {b.value: c for b, c in bucket_counts.items()},
            'sector_count': len(sectors)
        }
    
    def adjust_profile_for_market_conditions(
        self,
        market_sentiment: str  # 'bullish', 'bearish', 'neutral'
    ) -> Dict[RiskBucket, RiskProfile]:
        """
        Adjust risk profiles based on market conditions.
        """
        adjusted = {}
        
        for bucket, profile in self.profiles.items():
            adjusted_profile = RiskProfile(
                bucket=profile.bucket,
                allocation_percent=profile.allocation_percent,
                max_position_percent=profile.max_position_percent,
                position_count=profile.position_count,
                description=profile.description
            )
            
            if market_sentiment == 'bullish':
                # In bullish market, slightly increase moderate/aggressive
                if bucket == RiskBucket.MODERATE:
                    adjusted_profile.allocation_percent = min(45, profile.allocation_percent + 5)
                elif bucket == RiskBucket.AGGRESSIVE:
                    adjusted_profile.allocation_percent = min(25, profile.allocation_percent + 5)
                elif bucket == RiskBucket.CONSERVATIVE:
                    adjusted_profile.allocation_percent = max(40, profile.allocation_percent - 10)
                    
            elif market_sentiment == 'bearish':
                # In bearish market, increase conservative allocation
                if bucket == RiskBucket.CONSERVATIVE:
                    adjusted_profile.allocation_percent = min(70, profile.allocation_percent + 15)
                elif bucket == RiskBucket.AGGRESSIVE:
                    adjusted_profile.allocation_percent = max(5, profile.allocation_percent - 10)
                elif bucket == RiskBucket.MODERATE:
                    adjusted_profile.allocation_percent = max(25, profile.allocation_percent - 5)
            
            adjusted[bucket] = adjusted_profile
        
        return adjusted
