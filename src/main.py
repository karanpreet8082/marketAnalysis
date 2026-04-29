"""
Main entry point for the Stock Market Analysis Agent.

Orchestrates data fetching, analysis, and reporting.
Generates hourly reports during market hours for GitHub Pages.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import BUDGET_MAX, REPORTS_DIR, DATA_DIR
from data_fetcher import YFinanceFetcher, get_stock_universe, NIFTY_500_SYMBOLS
from analysis import TechnicalAnalyzer, FundamentalAnalyzer, SignalGenerator
from portfolio import PortfolioAllocator, RiskManager
from reporting import HTMLReportGenerator


def run_analysis(
    budget: float = BUDGET_MAX,
    max_stocks: int = 100,  # Limit for faster execution
    save_report: bool = True
) -> Dict:
    """
    Run the complete stock analysis pipeline.
    
    Args:
        budget: Investment budget
        max_stocks: Maximum number of stocks to analyze
        save_report: Whether to save HTML report to disk
        
    Returns:
        Results dictionary
    """
    from datetime import datetime
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    
    logger.info("=" * 60)
    logger.info("STOCK MARKET ANALYSIS AGENT - Starting analysis")
    logger.info(f"Date/Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info(f"Budget: ₹{budget:,.0f}")
    logger.info("=" * 60)
    
    results = {
        'status': 'running',
        'date': now_ist.strftime('%Y-%m-%d'),
        'time': now_ist.strftime('%H:%M'),
        'timestamp': now_ist.strftime('%Y-%m-%d %H:%M IST'),
        'stocks_analyzed': 0,
        'signals_generated': 0,
        'report_saved': False,
        'errors': []
    }
    
    try:
        # Step 1: Get stock universe
        logger.info("Step 1: Loading stock universe...")
        symbols = get_stock_universe(include_suffix=True)[:max_stocks]
        logger.info(f"Loaded {len(symbols)} stocks for analysis")
        
        # Step 2: Fetch data
        logger.info("Step 2: Fetching stock data...")
        fetcher = YFinanceFetcher()
        
        def progress_callback(current, total, symbol):
            if current % 20 == 0 or current == total:
                logger.info(f"Progress: {current}/{total} - {symbol}")
        
        historical_data, stock_info = fetcher.fetch_multiple_stocks(
            symbols,
            period="1y",
            progress_callback=progress_callback
        )
        
        logger.info(f"Fetched data for {len(historical_data)} stocks")
        results['stocks_analyzed'] = len(historical_data)
        
        if len(historical_data) == 0:
            raise ValueError("No stock data fetched - check internet connection")
        
        # Step 3: Technical Analysis
        logger.info("Step 3: Running technical analysis...")
        tech_analyzer = TechnicalAnalyzer()
        technical_results: Dict[str, Tuple] = {}
        
        for symbol, df in historical_data.items():
            try:
                analyzed_df = tech_analyzer.calculate_all_indicators(df)
                score, breakdown = tech_analyzer.get_technical_score(analyzed_df)
                technical_results[symbol] = (analyzed_df, score, breakdown)
            except Exception as e:
                logger.warning(f"Technical analysis failed for {symbol}: {e}")
        
        logger.info(f"Technical analysis completed for {len(technical_results)} stocks")
        
        # Step 4: Fundamental Analysis
        logger.info("Step 4: Running fundamental analysis...")
        fund_analyzer = FundamentalAnalyzer()
        fundamental_results: Dict[str, Dict] = {}
        
        for symbol, info in stock_info.items():
            try:
                analysis = fund_analyzer.analyze_stock(info)
                if analysis:
                    fundamental_results[symbol] = analysis
            except Exception as e:
                logger.warning(f"Fundamental analysis failed for {symbol}: {e}")
        
        logger.info(f"Fundamental analysis completed for {len(fundamental_results)} stocks")
        
        # Step 5: Generate Signals
        logger.info("Step 5: Generating trading signals...")
        signal_gen = SignalGenerator()
        signals = signal_gen.generate_signals_batch(technical_results, fundamental_results)
        
        # Filter to actionable signals
        actionable = signal_gen.filter_actionable_signals(signals, min_confidence=0.5)
        buy_signals = actionable['buy']
        
        logger.info(f"Generated {len(signals)} total signals")
        logger.info(f"Actionable buy signals: {len(buy_signals)}")
        results['signals_generated'] = len(signals)
        
        # Step 6: Portfolio Allocation
        logger.info("Step 6: Creating portfolio allocation...")
        allocator = PortfolioAllocator(budget_max=budget)
        recommendation = allocator.allocate_portfolio(
            signals=buy_signals,
            budget=budget,
            date_str=results['date']
        )
        
        logger.info(f"Allocated {len(recommendation.positions)} positions")
        logger.info(f"Total investment: ₹{recommendation.allocated_amount:,.0f}")
        
        # Print summary
        print("\n" + allocator.format_for_display(recommendation))
        
        # Step 7: Generate Report
        logger.info("Step 7: Generating HTML report...")
        report_gen = HTMLReportGenerator()
        
        # Save report with timestamp info
        if save_report:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate the web dashboard (main index.html)
            html_report = report_gen.generate_web_dashboard(
                recommendation=recommendation,
                timestamp=results['timestamp'],
                all_signals=signals
            )
            
            report_path = REPORTS_DIR / "index.html"
            report_gen.save_report(html_report, str(report_path))
            
            # Save hourly report data as JSON for history
            hourly_data_path = DATA_DIR / "hourly_reports.json"
            save_hourly_data(hourly_data_path, recommendation, results['timestamp'])
            
            # Save stock universe for portfolio search
            save_stock_universe_json(DATA_DIR / "stocks.json")
            
            logger.info(f"Report saved to {report_path}")
            results['report_saved'] = True
        
        results['status'] = 'completed'
        logger.info("=" * 60)
        logger.info("Analysis completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        results['status'] = 'failed'
        results['errors'].append(str(e))
    
    return results


def save_hourly_data(filepath, recommendation, timestamp):
    """Save hourly report data to JSON for history tracking."""
    import json
    
    # Load existing data
    data = []
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except:
            data = []
    
    # Add new entry
    entry = {
        'timestamp': timestamp,
        'budget': recommendation.total_budget,
        'allocated': recommendation.allocated_amount,
        'positions': len(recommendation.positions),
        'summary': recommendation.summary
    }
    
    data.append(entry)
    
    # Keep only last 7 days of hourly data (7 * 7 hours = 49 entries max)
    data = data[-50:]
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def save_stock_universe_json(filepath):
    """Save stock universe to JSON for portfolio search."""
    from data_fetcher.stock_list import get_stock_info
    
    stock_info = get_stock_info()
    stocks = []
    
    for symbol, info in stock_info.items():
        stocks.append({
            'symbol': symbol,
            'category': info['category'],
            'risk_bucket': info['risk_bucket']
        })
    
    with open(filepath, 'w') as f:
        json.dump(stocks, f, indent=2)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stock Market Analysis Agent')
    parser.add_argument(
        '--budget', 
        type=float, 
        default=BUDGET_MAX,
        help='Investment budget in INR'
    )
    parser.add_argument(
        '--max-stocks',
        type=int,
        default=100,
        help='Maximum stocks to analyze (reduce for faster testing)'
    )
    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Skip sending email (deprecated, emails removed)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Skip saving report to disk'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (10 stocks)'
    )
    
    args = parser.parse_args()
    
    if args.test:
        results = run_analysis(
            budget=args.budget,
            max_stocks=10,
            save_report=True
        )
    else:
        results = run_analysis(
            budget=args.budget,
            max_stocks=args.max_stocks,
            save_report=not args.no_save
        )
    
    # Exit with appropriate code
    sys.exit(0 if results['status'] == 'completed' else 1)


if __name__ == "__main__":
    main()
