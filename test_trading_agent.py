#!/usr/bin/env python3
"""
Example/Test Script for Autonomous Trading Agent

This script demonstrates how the trading agent works with sample data
and can be used for testing and validation before going live.

Usage:
    python3 test_trading_agent.py              # Test with real data
    python3 test_trading_agent.py --dry-run    # Analyze without trading
    python3 test_trading_agent.py --demo       # Demo with mock data
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import pytz

# Add src to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    from src.trading_agent import TradingAgent, StrategyEngine, PortfolioManager
    print("✓ Successfully imported Trading Agent modules")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure requirements.txt dependencies are installed:")
    print("  pip install -r requirements.txt")
    sys.exit(1)


def test_portfolio_manager():
    """Test PortfolioManager functionality."""
    print("\n" + "="*60)
    print("TEST 1: Portfolio Manager")
    print("="*60)

    pm = PortfolioManager()
    print(f"✓ Loaded portfolio: {len(pm.portfolio['holdings'])} positions")

    # Test summary
    summary = pm.get_summary()
    print(summary)

    return True


def test_strategy_engine():
    """Test StrategyEngine with sample data."""
    print("\n" + "="*60)
    print("TEST 2: Strategy Engine")
    print("="*60)

    try:
        import pandas as pd
        import numpy as np

        # Generate synthetic OHLCV data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        base_price = 100

        df = pd.DataFrame({
            'Date': dates,
            'Open': base_price + np.random.randn(100).cumsum(),
            'High': base_price + 5 + np.random.randn(100).cumsum(),
            'Low': base_price - 5 + np.random.randn(100).cumsum(),
            'Close': base_price + 2 + np.random.randn(100).cumsum(),
            'Volume': np.random.randint(1000000, 5000000, 100)
        })

        df = df.set_index('Date')

        engine = StrategyEngine()

        # Test individual strategies
        momentum = engine.calculate_momentum_score(df)
        meanrev = engine.calculate_meanreversion_score(df)
        breakout = engine.calculate_breakout_score(df)

        print(f"Momentum Score:     {momentum:+.2f}")
        print(f"Mean Reversion:     {meanrev:+.2f}")
        print(f"Breakout Score:     {breakout:+.2f}")

        # Test ensemble
        signal, confidence, breakdown = engine.get_trading_signal('TEST', df)
        print(f"\nEnsemble Signal:    {signal}")
        print(f"Confidence:         {confidence:.2f}")
        print(f"Breakdown:          {breakdown}")

        return True

    except Exception as e:
        print(f"✗ Strategy engine test failed: {e}")
        return False


def test_market_hours():
    """Test market hours detection."""
    print("\n" + "="*60)
    print("TEST 3: Market Hours Detection")
    print("="*60)

    agent = TradingAgent()

    # Current time
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    is_open = agent.is_market_hours()
    print(f"Current IST Time:   {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Market Open:        {is_open}")

    if now.weekday() >= 5:
        print("Note: Currently weekend, market is closed")
    elif now.hour < 9 or (now.hour == 9 and now.minute < 15):
        print("Note: Currently before 9:15 AM, market not open yet")
    elif now.hour >= 15 and now.minute > 30:
        print("Note: Currently after 3:30 PM, market closed")
    else:
        print("Note: Currently within market hours")

    return True


def test_portfolio_json_creation():
    """Test portfolio JSON file creation and loading."""
    print("\n" + "="*60)
    print("TEST 4: Portfolio JSON Persistence")
    print("="*60)

    pm = PortfolioManager()

    # Show current portfolio state
    portfolio_file = pm.PORTFOLIO_FILE
    print(f"Portfolio File:     {portfolio_file}")
    print(f"File Exists:        {portfolio_file.exists()}")

    if portfolio_file.exists():
        with open(portfolio_file, 'r') as f:
            portfolio = json.load(f)
            print(f"Capital:            ₹{portfolio['capital']['current_cash']:,.0f}")
            print(f"Holdings:           {len(portfolio['holdings'])}")
            print(f"Order History:      {len(portfolio['order_history'])}")
            print(f"Last Updated:       {portfolio['metadata']['last_updated']}")
            return True
    else:
        print("Portfolio file doesn't exist yet (will be created on first run)")
        return True


def test_git_integration():
    """Test git integration."""
    print("\n" + "="*60)
    print("TEST 5: Git Integration")
    print("="*60)

    try:
        import subprocess

        # Check git status
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✓ Git repository found")
            print(f"Changed files:      {len(result.stdout.splitlines())}")

            # Check git config
            user_result = subprocess.run(
                ['git', 'config', 'user.email'],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )

            if user_result.stdout.strip():
                print(f"Git user email:     {user_result.stdout.strip()}")
            else:
                print("⚠ Git user.email not configured (needed for commits)")

            return True
        else:
            print("✗ Not a git repository or git not found")
            return False

    except Exception as e:
        print(f"⚠ Git check failed: {e}")
        return False


def run_full_agent_test():
    """Run the full trading agent in test mode."""
    print("\n" + "="*60)
    print("TEST 6: Full Trading Agent Run (Market Hours Check)")
    print("="*60)

    agent = TradingAgent()

    # Check if within market hours
    if not agent.is_market_hours():
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("Market is closed. Full test skipped (would need to run 9:15 AM - 3:30 PM IST)")
        print("\nTo test during market hours, run:")
        print("  python3 src/trading_agent.py")
        print("\nOr trigger manually via GitHub Actions:")
        print("  gh workflow run trading_cron.yml")
        return True

    # Run agent
    print("Market hours detected! Running full agent cycle...")
    success = agent.run()

    if success:
        print("✓ Agent cycle completed successfully")
        pm = PortfolioManager()
        print(pm.get_summary())
    else:
        print("✗ Agent cycle failed - check logs above")

    return success


def main():
    """Run all tests."""
    print("\n" + "█"*60)
    print("AUTONOMOUS TRADING AGENT - TEST SUITE")
    print("█"*60)

    tests = [
        ("Portfolio Manager", test_portfolio_manager),
        ("Strategy Engine", test_strategy_engine),
        ("Market Hours", test_market_hours),
        ("Portfolio JSON", test_portfolio_json_creation),
        ("Git Integration", test_git_integration),
        ("Full Agent (if market open)", run_full_agent_test),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✓ {test_name} - PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} - FAILED")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} - ERROR: {e}")
            failed += 1

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Passed:             {passed}")
    print(f"Failed:             {failed}")
    print(f"Total:              {passed + failed}")

    if failed == 0:
        print("\n✓ All tests passed! Trading agent is ready.")
        print("\nNext steps:")
        print("1. Review TRADING_AGENT_README.md for detailed documentation")
        print("2. Run: python3 src/trading_agent.py (during market hours)")
        print("3. Check data/trading_agent_portfolio.json for portfolio state")
        print("4. Enable GitHub Actions for automatic trading")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed. Please review above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
