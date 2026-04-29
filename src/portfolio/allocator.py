"""
Portfolio Allocator module.

Handles position sizing and capital allocation across recommended stocks.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import math

from ..config import (
    BUDGET_MIN, BUDGET_MAX,
    MAX_POSITION_PERCENT, MIN_STOCKS_IN_PORTFOLIO, MAX_STOCKS_IN_PORTFOLIO
)
from ..analysis.signals import StockSignal, RiskBucket, Signal
from .risk_manager import RiskManager, RiskProfile


@dataclass
class PositionRecommendation:
    """Recommended position for a stock."""
    symbol: str
    name: str
    signal: Signal
    risk_bucket: RiskBucket
    current_price: float
    quantity: int
    investment_amount: float
    allocation_percent: float
    target_price: float
    stop_loss: float
    potential_gain_percent: float
    potential_loss_percent: float
    confidence: float
    reasons: List[str]


@dataclass 
class PortfolioRecommendation:
    """Complete portfolio recommendation."""
    date: str
    total_budget: float
    allocated_amount: float
    cash_reserve: float
    positions: List[PositionRecommendation]
    by_risk_bucket: Dict[str, List[PositionRecommendation]]
    risk_metrics: Dict
    summary: Dict


class PortfolioAllocator:
    """Allocates capital across recommended stocks."""
    
    def __init__(
        self,
        budget_min: float = BUDGET_MIN,
        budget_max: float = BUDGET_MAX,
        risk_manager: RiskManager = None
    ):
        self.budget_min = budget_min
        self.budget_max = budget_max
        self.risk_manager = risk_manager or RiskManager()
    
    def allocate_portfolio(
        self,
        signals: List[StockSignal],
        budget: float = None,
        date_str: str = None
    ) -> PortfolioRecommendation:
        """
        Create a complete portfolio allocation from signals.
        
        Args:
            signals: List of stock signals (should be filtered to buys only)
            budget: Investment budget (defaults to max budget)
            date_str: Date string for the recommendation
            
        Returns:
            PortfolioRecommendation with all positions
        """
        from datetime import datetime
        
        budget = budget or self.budget_max
        date_str = date_str or datetime.now().strftime('%Y-%m-%d')
        
        # Filter to buy signals only
        buy_signals = [s for s in signals if s.signal in [Signal.STRONG_BUY, Signal.BUY]]
        
        if not buy_signals:
            return self._empty_recommendation(date_str, budget)
        
        # Categorize by risk bucket
        categorized = self.risk_manager.categorize_signals(buy_signals)
        
        # Get top picks for each bucket
        top_picks = self.risk_manager.get_top_picks_by_bucket(categorized, action='buy')
        
        # Flatten top picks and allocate
        all_picks = []
        for bucket in [RiskBucket.CONSERVATIVE, RiskBucket.MODERATE, RiskBucket.AGGRESSIVE]:
            all_picks.extend(top_picks[bucket])
        
        # Calculate positions
        positions = self._calculate_positions(all_picks, budget)
        
        # Group by risk bucket
        by_bucket = {
            'conservative': [],
            'moderate': [],
            'aggressive': []
        }
        
        for pos in positions:
            by_bucket[pos.risk_bucket.value].append(pos)
        
        # Calculate metrics
        total_allocated = sum(p.investment_amount for p in positions)
        cash_reserve = budget - total_allocated
        
        risk_metrics = self.risk_manager.calculate_risk_metrics(
            [s for s in buy_signals if s.symbol in [p.symbol for p in positions]]
        )
        
        summary = self._generate_summary(positions, budget, by_bucket)
        
        return PortfolioRecommendation(
            date=date_str,
            total_budget=budget,
            allocated_amount=total_allocated,
            cash_reserve=cash_reserve,
            positions=positions,
            by_risk_bucket=by_bucket,
            risk_metrics=risk_metrics,
            summary=summary
        )
    
    def _calculate_positions(
        self,
        signals: List[StockSignal],
        budget: float
    ) -> List[PositionRecommendation]:
        """Calculate position sizes for each signal."""
        positions = []
        
        if not signals:
            return positions
        
        # Get allocation by bucket
        bucket_allocations = {
            RiskBucket.CONSERVATIVE: 0.50,  # 50%
            RiskBucket.MODERATE: 0.35,      # 35%
            RiskBucket.AGGRESSIVE: 0.15    # 15%
        }
        
        # Count signals per bucket
        bucket_counts = {bucket: 0 for bucket in RiskBucket}
        for signal in signals:
            bucket_counts[signal.risk_bucket] += 1
        
        # Calculate per-stock allocation
        for signal in signals:
            bucket = signal.risk_bucket
            bucket_budget = budget * bucket_allocations[bucket]
            stocks_in_bucket = bucket_counts[bucket]
            
            if stocks_in_bucket == 0:
                continue
            
            # Base allocation per stock in bucket
            base_allocation = bucket_budget / stocks_in_bucket
            
            # Adjust by confidence (higher confidence = larger position)
            confidence_multiplier = 0.8 + (signal.confidence * 0.4)  # 0.8 to 1.2
            adjusted_allocation = base_allocation * confidence_multiplier
            
            # Apply max position limit
            max_position = budget * (MAX_POSITION_PERCENT / 100)
            final_allocation = min(adjusted_allocation, max_position)
            
            # Calculate quantity
            price = signal.current_price
            if price <= 0:
                continue
            
            quantity = math.floor(final_allocation / price)
            
            if quantity <= 0:
                continue
            
            actual_investment = quantity * price
            
            # Calculate potential gains/losses
            potential_gain = 0
            potential_loss = 0
            
            if signal.target_price and signal.target_price > price:
                potential_gain = ((signal.target_price - price) / price) * 100
            
            if signal.stop_loss and signal.stop_loss < price:
                potential_loss = ((price - signal.stop_loss) / price) * 100
            
            positions.append(PositionRecommendation(
                symbol=signal.symbol,
                name=signal.name,
                signal=signal.signal,
                risk_bucket=signal.risk_bucket,
                current_price=price,
                quantity=quantity,
                investment_amount=round(actual_investment, 2),
                allocation_percent=round((actual_investment / budget) * 100, 1),
                target_price=signal.target_price or 0,
                stop_loss=signal.stop_loss or 0,
                potential_gain_percent=round(potential_gain, 1),
                potential_loss_percent=round(potential_loss, 1),
                confidence=signal.confidence,
                reasons=signal.reasons
            ))
        
        # Sort by allocation amount (largest first)
        positions.sort(key=lambda x: x.investment_amount, reverse=True)
        
        return positions
    
    def _generate_summary(
        self,
        positions: List[PositionRecommendation],
        budget: float,
        by_bucket: Dict[str, List[PositionRecommendation]]
    ) -> Dict:
        """Generate portfolio summary."""
        if not positions:
            return {
                'total_positions': 0,
                'avg_confidence': 0,
                'bucket_allocation': {},
                'expected_return_range': (0, 0)
            }
        
        total_invested = sum(p.investment_amount for p in positions)
        
        # Bucket allocation
        bucket_alloc = {}
        for bucket_name, bucket_positions in by_bucket.items():
            bucket_total = sum(p.investment_amount for p in bucket_positions)
            bucket_alloc[bucket_name] = {
                'amount': bucket_total,
                'percent': round((bucket_total / budget) * 100, 1) if budget > 0 else 0,
                'positions': len(bucket_positions)
            }
        
        # Average confidence
        avg_confidence = sum(p.confidence for p in positions) / len(positions)
        
        # Expected return range (weighted average)
        weighted_gain = sum(
            p.potential_gain_percent * p.investment_amount 
            for p in positions
        ) / total_invested if total_invested > 0 else 0
        
        weighted_loss = sum(
            p.potential_loss_percent * p.investment_amount 
            for p in positions
        ) / total_invested if total_invested > 0 else 0
        
        # Sector distribution
        sectors = {}
        for p in positions:
            # Get sector from signal
            sector = 'Unknown'
            for signal in positions:
                if signal.symbol == p.symbol:
                    # We don't have direct access to sector here, 
                    # but it's in the reasons usually
                    for reason in p.reasons:
                        if reason.startswith('Sector:'):
                            sector = reason.replace('Sector:', '').strip()
                            break
            sectors[sector] = sectors.get(sector, 0) + 1
        
        return {
            'total_positions': len(positions),
            'total_invested': round(total_invested, 2),
            'cash_reserve': round(budget - total_invested, 2),
            'avg_confidence': round(avg_confidence, 2),
            'bucket_allocation': bucket_alloc,
            'expected_gain_percent': round(weighted_gain, 1),
            'max_loss_percent': round(weighted_loss, 1),
            'sector_distribution': sectors
        }
    
    def _empty_recommendation(
        self,
        date_str: str,
        budget: float
    ) -> PortfolioRecommendation:
        """Create empty recommendation when no buys available."""
        return PortfolioRecommendation(
            date=date_str,
            total_budget=budget,
            allocated_amount=0,
            cash_reserve=budget,
            positions=[],
            by_risk_bucket={
                'conservative': [],
                'moderate': [],
                'aggressive': []
            },
            risk_metrics={
                'avg_beta': 0,
                'bucket_distribution': {},
                'sector_concentration': {},
                'diversification_score': 0
            },
            summary={
                'total_positions': 0,
                'message': 'No actionable buy signals found for today. Recommend staying in cash.'
            }
        )
    
    def format_for_display(
        self,
        recommendation: PortfolioRecommendation
    ) -> str:
        """Format recommendation for text display."""
        lines = [
            f"📊 PORTFOLIO RECOMMENDATION - {recommendation.date}",
            f"{'=' * 50}",
            f"Budget: ₹{recommendation.total_budget:,.0f}",
            f"Allocated: ₹{recommendation.allocated_amount:,.0f}",
            f"Cash Reserve: ₹{recommendation.cash_reserve:,.0f}",
            ""
        ]
        
        for bucket_name in ['conservative', 'moderate', 'aggressive']:
            positions = recommendation.by_risk_bucket[bucket_name]
            emoji = {'conservative': '🟢', 'moderate': '🟡', 'aggressive': '🔴'}[bucket_name]
            
            lines.append(f"{emoji} {bucket_name.upper()} ({len(positions)} stocks)")
            lines.append("-" * 40)
            
            for pos in positions:
                signal_icon = '🔼' if pos.signal == Signal.STRONG_BUY else '△'
                lines.append(
                    f"  {signal_icon} {pos.symbol} ({pos.name[:20]})"
                )
                lines.append(
                    f"     Buy: {pos.quantity} shares @ ₹{pos.current_price:.2f}"
                )
                lines.append(
                    f"     Investment: ₹{pos.investment_amount:,.0f} ({pos.allocation_percent}%)"
                )
                lines.append(
                    f"     Target: ₹{pos.target_price:.2f} | Stop Loss: ₹{pos.stop_loss:.2f}"
                )
                lines.append(
                    f"     Potential: +{pos.potential_gain_percent}% / -{pos.potential_loss_percent}%"
                )
                lines.append(
                    f"     Confidence: {pos.confidence * 100:.0f}%"
                )
                lines.append("")
        
        # Summary
        summary = recommendation.summary
        lines.extend([
            "=" * 50,
            "SUMMARY",
            f"Total Positions: {summary.get('total_positions', 0)}",
            f"Avg Confidence: {summary.get('avg_confidence', 0) * 100:.0f}%",
            f"Expected Gain: +{summary.get('expected_gain_percent', 0)}%",
            f"Max Loss (if stop hit): -{summary.get('max_loss_percent', 0)}%",
        ])
        
        return '\n'.join(lines)
