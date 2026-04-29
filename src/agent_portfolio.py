"""
Agent Portfolio Manager

Runs daily at market close (5:30 PM IST) to:
1. Pick top 2 recommendations of the day
2. Add them to agent's portfolio
3. Check existing holdings for target/stop-loss hits
4. Update portfolio performance metrics
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup path BEFORE any local imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pytz

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import BUDGET_MAX, DATA_DIR, REPORTS_DIR
from src.data_fetcher import YFinanceFetcher, get_stock_universe
from src.analysis import TechnicalAnalyzer, FundamentalAnalyzer, SignalGenerator
from src.analysis.signals import Signal
from src.portfolio import PortfolioAllocator

# Agent portfolio settings
AGENT_BUDGET = 100000  # ₹1 Lakh virtual portfolio
DAILY_PICKS = 2        # Top 2 picks per day
MAX_HOLDING_DAYS = 30  # Auto-sell after 30 days if no target/stop hit
PORTFOLIO_FILE = DATA_DIR / "agent_portfolio.json"


def load_agent_portfolio():
    """Load existing agent portfolio from JSON."""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {
        'holdings': [],
        'closed_trades': [],
        'cash': AGENT_BUDGET,
        'total_invested': 0,
        'realized_pnl': 0,
        'stats': {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_return': 0
        }
    }


def save_agent_portfolio(portfolio):
    """Save agent portfolio to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2)
    logger.info(f"Saved agent portfolio to {PORTFOLIO_FILE}")


def get_current_prices(symbols):
    """Fetch current prices for given symbols."""
    fetcher = YFinanceFetcher()
    prices = {}
    
    for symbol in symbols:
        yahoo_symbol = f"{symbol}.NS"
        df = fetcher.fetch_historical_data(yahoo_symbol, period="5d")
        if df is not None and not df.empty:
            prices[symbol] = df['close'].iloc[-1]
    
    return prices


def run_analysis_for_picks():
    """Run analysis and return top picks."""
    logger.info("Running analysis to get today's top picks...")
    
    fetcher = YFinanceFetcher()
    symbols = get_stock_universe(include_suffix=True)[:100]  # Analyze top 100
    
    # Fetch data
    historical_data, stock_info = fetcher.fetch_multiple_stocks(symbols, period="1y")
    
    if not historical_data:
        logger.error("No data fetched")
        return []
    
    # Technical analysis
    tech_analyzer = TechnicalAnalyzer()
    technical_results = {}
    
    for symbol, df in historical_data.items():
        try:
            analyzed_df = tech_analyzer.calculate_all_indicators(df)
            score, breakdown = tech_analyzer.get_technical_score(analyzed_df)
            technical_results[symbol] = (analyzed_df, score, breakdown)
        except Exception as e:
            logger.warning(f"Technical analysis failed for {symbol}: {e}")
    
    # Fundamental analysis
    fund_analyzer = FundamentalAnalyzer()
    fundamental_results = {}
    
    for symbol, info in stock_info.items():
        try:
            analysis = fund_analyzer.analyze_stock(info)
            if analysis:
                fundamental_results[symbol] = analysis
        except:
            pass
    
    # Generate signals
    signal_gen = SignalGenerator()
    signals = signal_gen.generate_signals_batch(technical_results, fundamental_results)
    
    # Filter to strong buys with high confidence
    buy_signals = [
        s for s in signals 
        if s.signal in [Signal.STRONG_BUY, Signal.BUY] and s.confidence >= 0.6
    ]
    
    # Sort by combined score
    buy_signals.sort(key=lambda x: (x.confidence, x.combined_score), reverse=True)
    
    return buy_signals[:DAILY_PICKS]


def update_agent_portfolio():
    """Main function to update agent portfolio."""
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).strftime('%Y-%m-%d')
    
    logger.info(f"=== Agent Portfolio Update: {today} ===")
    
    portfolio = load_agent_portfolio()
    
    # Step 1: Check existing holdings for exits
    logger.info("Checking existing holdings...")
    
    if portfolio['holdings']:
        symbols = [h['symbol'] for h in portfolio['holdings']]
        current_prices = get_current_prices(symbols)
        
        holdings_to_close = []
        
        for i, holding in enumerate(portfolio['holdings']):
            symbol = holding['symbol']
            current_price = current_prices.get(symbol, holding['current_price'])
            holding['current_price'] = current_price
            
            # Calculate current P&L
            pnl = (current_price - holding['buy_price']) * holding['quantity']
            pnl_pct = ((current_price / holding['buy_price']) - 1) * 100
            holding['unrealized_pnl'] = round(pnl, 2)
            holding['unrealized_pnl_pct'] = round(pnl_pct, 2)
            
            # Check exit conditions
            exit_reason = None
            
            # Target hit
            if current_price >= holding['target_price']:
                exit_reason = 'TARGET_HIT'
            # Stop loss hit
            elif current_price <= holding['stop_loss']:
                exit_reason = 'STOP_LOSS_HIT'
            # Max holding period
            else:
                buy_date = datetime.strptime(holding['buy_date'], '%Y-%m-%d')
                days_held = (datetime.now(ist).replace(tzinfo=None) - buy_date).days
                if days_held >= MAX_HOLDING_DAYS:
                    exit_reason = 'MAX_DAYS_REACHED'
            
            if exit_reason:
                holdings_to_close.append((i, exit_reason, current_price))
        
        # Process exits (in reverse order to maintain indices)
        for i, exit_reason, exit_price in sorted(holdings_to_close, reverse=True):
            holding = portfolio['holdings'].pop(i)
            
            sell_value = exit_price * holding['quantity']
            buy_value = holding['buy_price'] * holding['quantity']
            realized_pnl = sell_value - buy_value
            realized_pnl_pct = ((exit_price / holding['buy_price']) - 1) * 100
            
            closed_trade = {
                'symbol': holding['symbol'],
                'buy_date': holding['buy_date'],
                'sell_date': today,
                'buy_price': holding['buy_price'],
                'sell_price': exit_price,
                'quantity': holding['quantity'],
                'invested': buy_value,
                'returned': sell_value,
                'pnl': round(realized_pnl, 2),
                'pnl_pct': round(realized_pnl_pct, 2),
                'exit_reason': exit_reason,
                'profitable': realized_pnl > 0
            }
            
            portfolio['closed_trades'].append(closed_trade)
            portfolio['cash'] += sell_value
            portfolio['realized_pnl'] += realized_pnl
            
            # Update stats
            portfolio['stats']['total_trades'] += 1
            if realized_pnl > 0:
                portfolio['stats']['winning_trades'] += 1
            else:
                portfolio['stats']['losing_trades'] += 1
            
            if realized_pnl > portfolio['stats']['best_trade']:
                portfolio['stats']['best_trade'] = round(realized_pnl, 2)
            if realized_pnl < portfolio['stats']['worst_trade']:
                portfolio['stats']['worst_trade'] = round(realized_pnl, 2)
            
            logger.info(f"CLOSED: {holding['symbol']} | Reason: {exit_reason} | P&L: ₹{realized_pnl:.0f} ({realized_pnl_pct:.1f}%)")
    
    # Step 2: Get today's top picks
    logger.info("Getting today's top picks...")
    top_picks = run_analysis_for_picks()
    
    if not top_picks:
        logger.warning("No suitable picks found today")
        save_agent_portfolio(portfolio)
        return
    
    # Step 3: Add new holdings (if not already holding)
    existing_symbols = {h['symbol'] for h in portfolio['holdings']}
    
    for pick in top_picks:
        if pick.symbol in existing_symbols:
            logger.info(f"Already holding {pick.symbol}, skipping")
            continue
        
        # Calculate position size (equal weight for simplicity)
        position_size = min(portfolio['cash'] * 0.2, 20000)  # Max 20K per position
        
        if position_size < pick.current_price:
            logger.warning(f"Insufficient cash for {pick.symbol}")
            continue
        
        quantity = int(position_size / pick.current_price)
        if quantity < 1:
            continue
        
        investment = quantity * pick.current_price
        
        new_holding = {
            'symbol': pick.symbol,
            'name': pick.name,
            'buy_date': today,
            'buy_price': round(pick.current_price, 2),
            'quantity': quantity,
            'invested': round(investment, 2),
            'target_price': round(pick.target_price, 2) if pick.target_price else round(pick.current_price * 1.1, 2),
            'stop_loss': round(pick.stop_loss, 2) if pick.stop_loss else round(pick.current_price * 0.95, 2),
            'current_price': round(pick.current_price, 2),
            'unrealized_pnl': 0,
            'unrealized_pnl_pct': 0,
            'confidence': round(pick.confidence * 100),
            'risk_bucket': pick.risk_bucket.value,
            'reasons': pick.reasons[:2] if pick.reasons else []
        }
        
        portfolio['holdings'].append(new_holding)
        portfolio['cash'] -= investment
        portfolio['total_invested'] += investment
        
        logger.info(f"BOUGHT: {pick.symbol} | Qty: {quantity} @ ₹{pick.current_price:.2f} | Investment: ₹{investment:.0f}")
    
    # Step 4: Calculate portfolio metrics
    total_holdings_value = sum(h['current_price'] * h['quantity'] for h in portfolio['holdings'])
    total_invested_current = sum(h['invested'] for h in portfolio['holdings'])
    unrealized_pnl = total_holdings_value - total_invested_current
    
    portfolio['metrics'] = {
        'date': today,
        'cash': round(portfolio['cash'], 2),
        'holdings_value': round(total_holdings_value, 2),
        'total_value': round(portfolio['cash'] + total_holdings_value, 2),
        'unrealized_pnl': round(unrealized_pnl, 2),
        'realized_pnl': round(portfolio['realized_pnl'], 2),
        'total_pnl': round(unrealized_pnl + portfolio['realized_pnl'], 2),
        'total_return_pct': round(((portfolio['cash'] + total_holdings_value) / AGENT_BUDGET - 1) * 100, 2),
        'active_holdings': len(portfolio['holdings']),
        'closed_trades': len(portfolio['closed_trades'])
    }
    
    # Calculate win rate
    if portfolio['stats']['total_trades'] > 0:
        portfolio['stats']['win_rate'] = round(
            portfolio['stats']['winning_trades'] / portfolio['stats']['total_trades'] * 100, 1
        )
        
        # Calculate average return
        if portfolio['closed_trades']:
            avg_return = sum(t['pnl_pct'] for t in portfolio['closed_trades']) / len(portfolio['closed_trades'])
            portfolio['stats']['avg_return'] = round(avg_return, 2)
    
    # Save portfolio
    save_agent_portfolio(portfolio)
    
    # Log summary
    logger.info("=== Portfolio Summary ===")
    logger.info(f"Total Value: ₹{portfolio['metrics']['total_value']:,.0f}")
    logger.info(f"Total Return: {portfolio['metrics']['total_return_pct']}%")
    logger.info(f"Active Holdings: {portfolio['metrics']['active_holdings']}")
    logger.info(f"Closed Trades: {portfolio['metrics']['closed_trades']}")
    if portfolio['stats']['total_trades'] > 0:
        logger.info(f"Win Rate: {portfolio['stats'].get('win_rate', 0)}%")


if __name__ == "__main__":
    update_agent_portfolio()
