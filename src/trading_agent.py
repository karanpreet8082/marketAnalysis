"""
Autonomous Algorithmic Trading Agent for Indian Stock Market (NSE/BSE).

A fully automated paper-trading agent that:
- Runs every 30 minutes during market hours (9:15 AM - 3:30 PM IST)
- Uses multi-strategy ensemble (Momentum, Mean Reversion, Breakout)
- Persists portfolio state via git commits
- Provides Groww-like dashboard data

Author: Trading Agent
Version: 1.0
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
from copy import deepcopy

import pandas as pd
import numpy as np
import pytz
from ta.momentum import RSIIndicator, MACD, SuperTrend
from ta.volatility import BollingerBands
from ta.trend import EMAIndicator, ADXIndicator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data_fetcher import YFinanceFetcher
from config import MAX_POSITION_PERCENT, MIN_STOCKS_IN_PORTFOLIO, MAX_STOCKS_IN_PORTFOLIO


class StrategyEngine:
    """Multi-strategy trading decision engine."""

    def __init__(self, lookback_period: int = 100):
        self.lookback_period = lookback_period
        self.fetcher = YFinanceFetcher()

    def calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """
        Calculate momentum score using Supertrend, MACD, and EMA Crossover.
        Returns a score between -1 and 1.
        """
        try:
            if len(df) < 50:
                return 0.0

            # Supertrend (14, 3) - trend strength
            supertrend = SuperTrend(
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                window=14,
                multiplier=3
            )
            st_trend = supertrend.supertrendl()
            supertrend_signal = 1 if df['Close'].iloc[-1] > st_trend.iloc[-1] else -1

            # MACD - momentum divergence
            macd = MACD(close=df['Close'], window_fast=12, window_slow=26, window_sign=9)
            macd_line = macd.macd()
            macd_signal = macd.macd_signal()
            macd_hist = macd_line.iloc[-1] - macd_signal.iloc[-1] if len(macd_line) > 0 else 0
            macd_signal_value = 1 if macd_hist > 0 else (-1 if macd_hist < 0 else 0)

            # EMA Crossover (9 vs 21)
            ema9 = EMAIndicator(close=df['Close'], window=9).ema_indicator()
            ema21 = EMAIndicator(close=df['Close'], window=21).ema_indicator()
            ema_signal = 1 if ema9.iloc[-1] > ema21.iloc[-1] else -1

            # Combined momentum score
            momentum_score = (supertrend_signal * 0.4 + macd_signal_value * 0.3 + ema_signal * 0.3)

            return momentum_score
        except Exception as e:
            logger.warning(f"Error calculating momentum score: {e}")
            return 0.0

    def calculate_meanreversion_score(self, df: pd.DataFrame) -> float:
        """
        Calculate mean reversion score using RSI and Bollinger Bands.
        Returns a score between -1 and 1.
        """
        try:
            if len(df) < 50:
                return 0.0

            # RSI (14) - overbought/oversold
            rsi = RSIIndicator(close=df['Close'], window=14).rsi()
            rsi_value = rsi.iloc[-1]
            rsi_signal = 1 if rsi_value < 30 else (-1 if rsi_value > 70 else 0)

            # Bollinger Bands (20, 2)
            bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
            bb_lower = bb.bollinger_lband()
            bb_upper = bb.bollinger_uband()
            bb_middle = bb.bollinger_mavg()

            current_price = df['Close'].iloc[-1]
            bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
            bb_signal = 1 if bb_position < 0.2 else (-1 if bb_position > 0.8 else 0)

            # Combined mean reversion score
            meanreversion_score = (rsi_signal * 0.5 + bb_signal * 0.5)

            return meanreversion_score
        except Exception as e:
            logger.warning(f"Error calculating mean reversion score: {e}")
            return 0.0

    def calculate_breakout_score(self, df: pd.DataFrame) -> float:
        """
        Calculate breakout score using volume spike and resistance/support breaks.
        Returns a score between -1 and 1.
        """
        try:
            if len(df) < 20:
                return 0.0

            # Volume spike detection (current volume > 1.5x average)
            avg_volume = df['Volume'].tail(20).mean()
            current_volume = df['Volume'].iloc[-1]
            volume_signal = 1 if current_volume > 1.5 * avg_volume else 0

            # Resistance/Support break (price breaks above 20-period high or below low)
            period_high = df['High'].tail(20).max()
            period_low = df['Low'].tail(20).min()
            current_price = df['Close'].iloc[-1]

            resistance_break = 1 if current_price > period_high else 0
            support_break = -1 if current_price < period_low else 0

            breakout_signal = resistance_break + support_break

            # Combined breakout score (only when volume is high)
            if volume_signal > 0:
                breakout_score = breakout_signal
            else:
                breakout_score = 0.0

            return breakout_score
        except Exception as e:
            logger.warning(f"Error calculating breakout score: {e}")
            return 0.0

    def get_trading_signal(self, symbol: str, df: pd.DataFrame) -> Tuple[str, float, Dict]:
        """
        Generate trading signal using ensemble of strategies.

        Returns:
            (signal, confidence, breakdown) where:
            - signal: "BUY", "SELL", or "HOLD"
            - confidence: confidence score 0-1
            - breakdown: dict with individual strategy scores
        """
        momentum_score = self.calculate_momentum_score(df)
        meanreversion_score = self.calculate_meanreversion_score(df)
        breakout_score = self.calculate_breakout_score(df)

        breakdown = {
            'momentum': momentum_score,
            'meanreversion': meanreversion_score,
            'breakout': breakout_score,
        }

        # Ensemble voting (weighted combination)
        ensemble_score = (
            momentum_score * 0.40 +
            meanreversion_score * 0.35 +
            breakout_score * 0.25
        )

        # Determine signal and confidence
        if ensemble_score > 0.6:
            signal = "BUY"
            confidence = abs(ensemble_score)
        elif ensemble_score < -0.6:
            signal = "SELL"
            confidence = abs(ensemble_score)
        else:
            signal = "HOLD"
            confidence = 0.0

        return signal, confidence, breakdown


class PortfolioManager:
    """Manages trading portfolio, positions, and order book."""

    PORTFOLIO_FILE = PROJECT_ROOT / "data" / "trading_agent_portfolio.json"
    INITIAL_CAPITAL = 1000000  # ₹10 lakh

    def __init__(self):
        self.portfolio = self.load_portfolio()

    def load_portfolio(self) -> Dict:
        """Load portfolio from JSON file, create if not exists."""
        if self.PORTFOLIO_FILE.exists():
            try:
                with open(self.PORTFOLIO_FILE, 'r') as f:
                    portfolio = json.load(f)
                logger.info(f"Loaded portfolio from {self.PORTFOLIO_FILE}")
                return portfolio
            except Exception as e:
                logger.error(f"Error loading portfolio: {e}")
                return self._create_empty_portfolio()
        else:
            logger.info("Creating new portfolio")
            return self._create_empty_portfolio()

    def _create_empty_portfolio(self) -> Dict:
        """Create a new empty portfolio."""
        return {
            "metadata": {
                "creation_date": datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d'),
                "last_updated": datetime.now(pytz.UTC).isoformat(),
                "agent_version": "1.0"
            },
            "capital": {
                "initial_capital": self.INITIAL_CAPITAL,
                "current_cash": self.INITIAL_CAPITAL,
                "total_invested": 0,
                "total_portfolio_value": self.INITIAL_CAPITAL
            },
            "holdings": [],
            "order_history": [],
            "dashboard": self._calculate_dashboard()
        }

    def _calculate_dashboard(self) -> Dict:
        """Calculate dashboard metrics from current holdings."""
        total_value = self.portfolio['capital']['current_cash']
        total_invested = 0
        total_returns_inr = 0
        todays_returns_inr = 0

        for holding in self.portfolio['holdings']:
            holding_value = holding.get('current_value', 0)
            total_value += holding_value
            total_invested += holding.get('quantity', 0) * holding.get('avg_buy_price', 0)
            total_returns_inr += holding.get('p_l', 0)
            todays_returns_inr += holding.get('todays_p_l', 0)

        initial_capital = self.portfolio['capital']['initial_capital']
        total_returns_percent = (total_returns_inr / initial_capital * 100) if initial_capital > 0 else 0

        return {
            "total_invested": total_invested,
            "current_value": total_value,
            "total_returns_inr": total_returns_inr,
            "total_returns_percent": round(total_returns_percent, 2),
            "todays_returns_inr": todays_returns_inr,
            "todays_returns_percent": 0.0,  # Calculate separately if tracking daily
            "num_positions": len([h for h in self.portfolio['holdings'] if h['quantity'] > 0])
        }

    def buy(self, symbol: str, quantity: int, price: float, strategies: List[str]) -> bool:
        """Execute a buy order."""
        total_cost = quantity * price
        current_cash = self.portfolio['capital']['current_cash']

        if total_cost > current_cash:
            logger.warning(f"Insufficient cash for {symbol}: need ₹{total_cost:,.0f}, have ₹{current_cash:,.0f}")
            return False

        # Check position sizing rule (max 20% per stock)
        max_position = self.portfolio['capital']['initial_capital'] * (MAX_POSITION_PERCENT / 100)
        if total_cost > max_position:
            logger.warning(f"Position {symbol} exceeds max position size")
            return False

        # Update holdings
        holding = next((h for h in self.portfolio['holdings'] if h['symbol'] == symbol), None)
        if holding:
            # Add to existing position
            old_quantity = holding['quantity']
            old_avg = holding['avg_buy_price']
            new_quantity = old_quantity + quantity
            new_avg = (old_quantity * old_avg + quantity * price) / new_quantity
            holding['quantity'] = new_quantity
            holding['avg_buy_price'] = new_avg
            holding['entry_timestamp'] = datetime.now(pytz.UTC).isoformat()
        else:
            # New position
            self.portfolio['holdings'].append({
                'symbol': symbol,
                'quantity': quantity,
                'avg_buy_price': price,
                'current_price': price,
                'current_value': total_cost,
                'p_l': 0,
                'p_l_percent': 0,
                'todays_p_l': 0,
                'entry_timestamp': datetime.now(pytz.UTC).isoformat(),
                'strategies_triggered': strategies
            })

        # Update capital
        self.portfolio['capital']['current_cash'] -= total_cost
        self.portfolio['capital']['total_invested'] += total_cost

        # Record order
        self.portfolio['order_history'].append({
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'action': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'total_amount': total_cost,
            'strategies': strategies
        })

        logger.info(f"BUY {quantity} x {symbol} @ ₹{price:.2f} | Cost: ₹{total_cost:,.0f}")
        return True

    def sell(self, symbol: str, quantity: int, price: float) -> bool:
        """Execute a sell order."""
        holding = next((h for h in self.portfolio['holdings'] if h['symbol'] == symbol), None)

        if not holding or holding['quantity'] < quantity:
            logger.warning(f"Cannot sell {quantity} x {symbol}: have {holding['quantity'] if holding else 0}")
            return False

        # Calculate realized P&L
        total_sale = quantity * price
        cost_basis = quantity * holding['avg_buy_price']
        realized_pl = total_sale - cost_basis

        # Update holding
        holding['quantity'] -= quantity
        holding['current_price'] = price
        holding['current_value'] = holding['quantity'] * price

        if holding['quantity'] == 0:
            self.portfolio['holdings'].remove(holding)

        # Update capital
        self.portfolio['capital']['current_cash'] += total_sale
        self.portfolio['capital']['total_invested'] -= cost_basis

        # Record order
        self.portfolio['order_history'].append({
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'action': 'SELL',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'total_amount': total_sale,
            'realized_pl': realized_pl
        })

        logger.info(f"SELL {quantity} x {symbol} @ ₹{price:.2f} | Proceeds: ₹{total_sale:,.0f} | P&L: ₹{realized_pl:,.0f}")
        return True

    def update_prices(self, price_data: Dict[str, float]) -> None:
        """Update current prices for all holdings."""
        for holding in self.portfolio['holdings']:
            symbol = holding['symbol']
            if symbol in price_data:
                new_price = price_data[symbol]
                holding['current_price'] = new_price
                holding['current_value'] = holding['quantity'] * new_price

                # Calculate P&L
                cost_basis = holding['quantity'] * holding['avg_buy_price']
                holding['p_l'] = holding['current_value'] - cost_basis
                holding['p_l_percent'] = (holding['p_l'] / cost_basis * 100) if cost_basis > 0 else 0

    def save_portfolio(self) -> bool:
        """Save portfolio to JSON file and commit to git."""
        try:
            self.portfolio['capital']['total_portfolio_value'] = (
                self.portfolio['capital']['current_cash'] +
                sum(h['current_value'] for h in self.portfolio['holdings'])
            )
            self.portfolio['metadata']['last_updated'] = datetime.now(pytz.UTC).isoformat()
            self.portfolio['dashboard'] = self._calculate_dashboard()

            self.PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.PORTFOLIO_FILE, 'w') as f:
                json.dump(self.portfolio, f, indent=2)

            logger.info(f"Portfolio saved to {self.PORTFOLIO_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error saving portfolio: {e}")
            return False

    def commit_to_git(self) -> bool:
        """Auto-commit portfolio changes to GitHub."""
        try:
            # Check if portfolio file has changed
            result = subprocess.run(
                ['git', 'diff', '--quiet', str(self.PORTFOLIO_FILE)],
                cwd=PROJECT_ROOT,
                capture_output=True
            )

            if result.returncode == 0:
                logger.info("No changes to portfolio, skipping git commit")
                return True

            # Stage file
            subprocess.run(
                ['git', 'add', str(self.PORTFOLIO_FILE)],
                cwd=PROJECT_ROOT,
                check=True
            )

            # Commit
            timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S IST')
            commit_msg = f"Trading Agent: Portfolio update at {timestamp}"

            result = subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"Git commit successful: {commit_msg}")

                # Push to remote
                push_result = subprocess.run(
                    ['git', 'push'],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True
                )

                if push_result.returncode == 0:
                    logger.info("Git push successful")
                    return True
                else:
                    logger.warning(f"Git push failed: {push_result.stderr}")
                    return False
            else:
                logger.warning(f"Git commit failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Git error: {e}")
            return False

    def get_summary(self) -> str:
        """Get a human-readable portfolio summary."""
        portfolio = self.portfolio
        summary = f"""
=== TRADING AGENT PORTFOLIO SUMMARY ===
Timestamp: {portfolio['metadata']['last_updated']}

CAPITAL:
  Initial: ₹{portfolio['capital']['initial_capital']:,.0f}
  Cash: ₹{portfolio['capital']['current_cash']:,.0f}
  Invested: ₹{portfolio['capital']['total_invested']:,.0f}
  Total Value: ₹{portfolio['capital']['total_portfolio_value']:,.0f}

RETURNS:
  Total P&L: ₹{portfolio['dashboard']['total_returns_inr']:,.0f} ({portfolio['dashboard']['total_returns_percent']:.2f}%)
  Today's P&L: ₹{portfolio['dashboard']['todays_returns_inr']:,.0f}

HOLDINGS ({portfolio['dashboard']['num_positions']} positions):
"""
        for holding in portfolio['holdings']:
            if holding['quantity'] > 0:
                summary += f"\n  {holding['symbol']:12} | Qty: {holding['quantity']:>4} | Avg: ₹{holding['avg_buy_price']:>8.2f} | Current: ₹{holding['current_price']:>8.2f} | P&L: ₹{holding['p_l']:>10,.0f} ({holding['p_l_percent']:>6.2f}%)"

        return summary


class TradingAgent:
    """Main autonomous trading agent."""

    def __init__(self):
        self.strategy_engine = StrategyEngine()
        self.portfolio_manager = PortfolioManager()
        self.ist = pytz.timezone('Asia/Kolkata')
        self.fetcher = YFinanceFetcher()

    def is_market_hours(self) -> bool:
        """Check if current time is within market hours (9:15 AM - 3:30 PM IST, Mon-Fri)."""
        now = datetime.now(self.ist)

        # Check day of week (0=Monday, 6=Sunday)
        if now.weekday() >= 5:  # Saturday or Sunday
            logger.info("Market closed: Weekend")
            return False

        # Check time (9:15 AM to 3:30 PM IST)
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

        if now < market_open or now > market_close:
            logger.info(f"Market closed: Current time {now.strftime('%H:%M:%S IST')} is outside 9:15 AM - 3:30 PM")
            return False

        return True

    def select_stocks(self) -> List[str]:
        """Select stocks to analyze based on liquidity and volatility."""
        stocks = [
            'TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS',
            'RELIANCE.NS', 'JSWSTEEL.NS', 'MARUTI.NS', 'BAJAJFINSV.NS',
            'ICICIBANK.NS', 'HDFC.NS', 'AXISBANK.NS', 'KOTAKBANK.NS',
            'NESTLEIND.NS', 'TITAN.NS', 'DMART.NS', 'SUNPHARMA.NS',
            'HINDALCO.NS', 'BHARTIARTL.NS', 'SBILIFE.NS', 'ITC.NS'
        ]
        return stocks

    def run(self) -> bool:
        """Run the trading agent for one cycle."""
        logger.info("=" * 60)
        logger.info("TRADING AGENT CYCLE START")
        logger.info("=" * 60)

        # Check market hours
        if not self.is_market_hours():
            logger.warning("Market is closed, exiting")
            return False

        try:
            # Select stocks to trade
            stocks = self.select_stocks()
            logger.info(f"Selected {len(stocks)} stocks for analysis")

            # Fetch data
            logger.info("Fetching stock data...")
            historical_data = self.fetcher.fetch_multiple_stocks(
                stocks,
                period="1mo",
                progress_callback=lambda c, t, s: None
            )[0]

            if not historical_data:
                logger.error("Failed to fetch stock data")
                return False

            logger.info(f"Fetched data for {len(historical_data)} stocks")

            # Analyze and generate signals
            logger.info("Running strategy analysis...")
            buy_signals = []

            for symbol, df in historical_data.items():
                if len(df) < 50:
                    continue

                signal, confidence, breakdown = self.strategy_engine.get_trading_signal(symbol, df)

                if signal == "BUY" and confidence >= 0.6:
                    buy_signals.append({
                        'symbol': symbol,
                        'signal': signal,
                        'confidence': confidence,
                        'breakdown': breakdown,
                        'current_price': float(df['Close'].iloc[-1])
                    })

            logger.info(f"Generated {len(buy_signals)} BUY signals (confidence >= 0.6)")

            # Execute trades
            logger.info("Executing trades...")
            trades_executed = 0

            # Sort by confidence (highest first)
            buy_signals.sort(key=lambda x: x['confidence'], reverse=True)

            for signal in buy_signals[:5]:  # Limit to top 5 signals
                symbol = signal['symbol']
                price = signal['current_price']
                confidence = signal['confidence']

                # Position sizing: allocate 10-15% of portfolio per trade
                portfolio_value = (
                    self.portfolio_manager.portfolio['capital']['current_cash'] +
                    sum(h['current_value'] for h in self.portfolio_manager.portfolio['holdings'])
                )
                allocation = portfolio_value * 0.12  # 12% per position

                quantity = int(allocation / price)
                if quantity < 1:
                    continue

                strategies = [k for k, v in signal['breakdown'].items() if abs(v) > 0.5]

                if self.portfolio_manager.buy(symbol, quantity, price, strategies):
                    trades_executed += 1

            logger.info(f"Executed {trades_executed} trades")

            # Update current prices
            current_prices = {
                symbol: float(df['Close'].iloc[-1])
                for symbol, df in historical_data.items()
            }
            self.portfolio_manager.update_prices(current_prices)

            # Save and commit
            self.portfolio_manager.save_portfolio()
            self.portfolio_manager.commit_to_git()

            # Print summary
            print(self.portfolio_manager.get_summary())

            logger.info("=" * 60)
            logger.info("TRADING AGENT CYCLE COMPLETE")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"Trading agent error: {e}", exc_info=True)
            return False


def main():
    """Main entry point."""
    try:
        agent = TradingAgent()
        success = agent.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
