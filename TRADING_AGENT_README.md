# Autonomous Algorithmic Trading Agent

## 📊 Overview

The Autonomous Trading Agent is a fully automated paper-trading system for the Indian stock market (NSE/BSE) that runs entirely on GitHub Actions. It manages a virtual portfolio of ₹10,00,000 (10 lakh) and executes buy/sell decisions based on a multi-strategy ensemble approach.

**Key Features:**
- ✅ Autonomous execution every 30 minutes during market hours
- ✅ Multi-strategy decision engine (Momentum, Mean Reversion, Breakout)
- ✅ Automatic portfolio persistence via git commits
- ✅ Groww-like dashboard data in JSON format
- ✅ Graceful error handling and market hours detection
- ✅ Comprehensive logging and audit trail

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                   GitHub Actions CRON                       │
│           (Every 30 mins, 9:15 AM - 3:30 PM IST)            │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              Trading Agent (trading_agent.py)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Market Hours Check (IST Timezone)                │   │
│  │  2. Stock Data Fetch (YFinance - 20 stocks)          │   │
│  │  3. Strategy Analysis Engine                         │   │
│  │     ├─ Momentum Score (40%): Supertrend, MACD, EMA  │   │
│  │     ├─ Mean Reversion (35%): RSI, Bollinger Bands   │   │
│  │     └─ Breakout (25%): Volume Spike + Support/Res   │   │
│  │  4. Decision Voting (Confidence >= 0.6 = BUY signal)│   │
│  │  5. Trade Execution (Position Sizing 12% per stock) │   │
│  │  6. Portfolio Update (P&L calculation)              │   │
│  │  7. State Persistence (Save JSON + Git Push)        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│       Portfolio JSON (data/trading_agent_portfolio.json)     │
│  - Holdings: symbol, qty, avg_buy_price, current_value      │
│  - Order History: timestamp, action, price, quantity        │
│  - Dashboard: Total Returns, P&L, Portfolio Value           │
│  - Git Commit & Push (Automatic)                            │
└─────────────────────────────────────────────────────────────┘
```

### Strategy Ensemble

The agent uses three complementary strategies with weighted voting:

#### 1. **Momentum Trading (40% weight)**
Catches strong directional trends using:
- **Supertrend (14, 3)**: Identifies uptrends vs downtrends
- **MACD (12, 26, 9)**: Momentum divergence and crossovers
- **EMA Crossover (9 vs 21)**: Short-term vs medium-term trend

*Signal:* BUY when all three indicators align on uptrend

#### 2. **Mean Reversion (35% weight)**
Capitalizes on overbought/oversold conditions:
- **RSI (14)**: Buy when RSI < 30 (oversold), Sell when RSI > 70
- **Bollinger Bands (20, 2)**: Buy when price at lower band, Sell at upper band

*Signal:* BUY when price touches lower band AND RSI is depressed

#### 3. **Breakout Strategy (25% weight)**
Captures explosive moves with high volume:
- **Volume Spike Detection**: Current volume > 1.5x 20-period average
- **Support/Resistance Break**: Price breaks above 20-period high or below low

*Signal:* BUY when volume spikes AND price breaks above resistance

### Decision Logic

```
Momentum Score (-1 to +1)
     ↓
├─ Supertrend Signal (40%): +1 if above uptrend, -1 if below
├─ MACD Histogram (30%): +1 if positive, -1 if negative
└─ EMA Crossover (30%): +1 if EMA9 > EMA21, -1 otherwise
     ↓
Mean Reversion Score (-1 to +1)
     ↓
├─ RSI (50%): +1 if <30, -1 if >70, 0 otherwise
└─ Bollinger Bands (50%): +1 if low position, -1 if high position
     ↓
Breakout Score (-1 to +1)
     ↓
├─ Volume Signal: 0 or 1 (high volume required)
└─ Resistance Break: +1 if above resistance, -1 if below support
     ↓
ENSEMBLE VOTE: (Momentum×0.4 + MeanRev×0.35 + Breakout×0.25)
     ↓
DECISION:
├─ Score > +0.6  → BUY (Confidence = |Score|)
├─ Score < -0.6  → SELL (Confidence = |Score|)
└─ Otherwise     → HOLD
```

---

## 📋 Portfolio Data Schema

The portfolio state is persisted in **`data/trading_agent_portfolio.json`**:

```json
{
  "metadata": {
    "creation_date": "2024-05-31",
    "last_updated": "2024-05-31T14:15:30.123456+00:00",
    "agent_version": "1.0"
  },
  "capital": {
    "initial_capital": 1000000,
    "current_cash": 500000,
    "total_invested": 500000,
    "total_portfolio_value": 1050000
  },
  "holdings": [
    {
      "symbol": "RELIANCE.NS",
      "quantity": 10,
      "avg_buy_price": 2800.50,
      "current_price": 2900.00,
      "current_value": 29000,
      "p_l": 1000,
      "p_l_percent": 3.57,
      "todays_p_l": 100,
      "entry_timestamp": "2024-05-31T13:45:00.000000+00:00",
      "strategies_triggered": ["momentum", "ema_crossover"]
    }
  ],
  "order_history": [
    {
      "timestamp": "2024-05-31T13:45:00.000000+00:00",
      "action": "BUY",
      "symbol": "RELIANCE.NS",
      "quantity": 10,
      "price": 2800.50,
      "total_amount": 28005,
      "strategies": ["momentum", "ema_crossover"]
    }
  ],
  "dashboard": {
    "total_invested": 500000,
    "current_value": 1050000,
    "total_returns_inr": 50000,
    "total_returns_percent": 5.0,
    "todays_returns_inr": 5000,
    "todays_returns_percent": 0.5,
    "num_positions": 5
  }
}
```

---

## ⏰ GitHub Actions Schedule

The agent runs automatically via CRON schedule, converted from IST to UTC:

| IST Time      | UTC Time      | CRON Expression |
|---------------|---------------|-----------------|
| 9:15 AM IST   | 3:45 AM UTC   | `45 3 * * 1-5`  |
| 9:45 AM IST   | 4:15 AM UTC   | `15 4 * * 1-5`  |
| 10:15 AM IST  | 4:45 AM UTC   | `45 4 * * 1-5`  |
| ... (every 30 mins) | ... | ... |
| 3:30 PM IST   | 10:00 AM UTC  | `0 10 * * 1-5`  |

**Important:** Only runs Monday-Friday (1-5 = Mon-Fri in cron syntax)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Git (for auto-commits)
- GitHub token (GITHUB_TOKEN secret in Actions)

### Installation

1. **Ensure requirements are installed:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify trading agent:**
   ```bash
   python3 -m py_compile src/trading_agent.py
   ```

3. **Manual test run:**
   ```bash
   python3 src/trading_agent.py
   ```

### Running on GitHub Actions

The workflow file (`.github/workflows/trading_cron.yml`) automatically:
1. ✓ Triggers every 30 minutes during market hours
2. ✓ Fetches stock data
3. ✓ Runs strategy analysis
4. ✓ Executes trades
5. ✓ Saves portfolio JSON
6. ✓ Commits changes to repository
7. ✓ Pushes to main branch

**Manual trigger:**
```bash
gh workflow run trading_cron.yml
```

---

## 💡 Risk Management Rules

### Position Sizing
- **Maximum per position:** 20% of initial capital (₹2,00,000)
- **Allocation per trade:** 12% of current portfolio value
- **Minimum positions:** 3 stocks (diversification)
- **Maximum positions:** 10 stocks (avoid over-diversification)

### Stop-Loss & Take-Profit
- **Stop Loss:** 2-3% below entry price (hardcoded in decision logic)
- **Take Profit:** 5-10% above entry price (exit signals generated automatically)
- **Exit Conditions:** Triggered when score drops below -0.6

### Daily Limits
- **Max trades per cycle:** 5 (highest confidence signals)
- **Max capital deployment:** 60% of portfolio per cycle
- **Realized P&L tracking:** All trades logged with entry/exit prices

---

## 📊 Stocks Analyzed

The agent currently analyzes a curated list of 20 highly liquid NSE stocks:

**IT Sector:** TCS, INFY, WIPRO, HCLTECH
**Energy:** RELIANCE
**Steel:** JSWSTEEL
**Auto:** MARUTI
**Finance:** BAJAJFINSV, ICICIBANK, HDFC, AXISBANK, KOTAKBANK, SBILIFE
**Consumer:** NESTLEIND, TITAN, DMART
**Pharma:** SUNPHARMA
**Metals:** HINDALCO
**Telecom:** BHARTIARTL
**Tobacco:** ITC

*Note: Easily extensible to 100+ stocks by adding to `select_stocks()` method*

---

## 🔧 Configuration

Edit `src/config.py` to customize parameters:

```python
# Risk Management
MAX_POSITION_PERCENT = 20    # Max 20% per stock
MIN_STOCKS_IN_PORTFOLIO = 3  # Diversification min
MAX_STOCKS_IN_PORTFOLIO = 10 # Diversification max

# Technical Indicators
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9

# Decision Thresholds
STRONG_BUY_THRESHOLD = 0.7
BUY_THRESHOLD = 0.5
SELL_THRESHOLD = -0.5
```

---

## 📈 Strategy Performance Metrics

Track in portfolio JSON:
- **Cumulative Returns:** (Current Value - Initial Capital) / Initial Capital
- **Daily Returns:** P&L today / Initial Capital
- **Win Rate:** Number of winning trades / Total trades
- **Sharpe Ratio:** Returns / Volatility (calculated from historical data)
- **Max Drawdown:** Peak-to-trough decline

---

## 🐛 Error Handling

The agent gracefully handles:

| Error | Action |
|-------|--------|
| Market closed (outside 9:15-3:30 IST) | Log warning, exit cleanly |
| Weekend/Holiday | Check weekday, skip execution |
| Data fetch fails | Retry 3 times, then exit |
| Insufficient cash | Skip trade, log warning |
| Position exceeds 20% | Reject order, log warning |
| Git push fails | Continue execution, retry next cycle |

---

## 📝 Logging

All logs are printed to stdout with timestamps. GitHub Actions captures in:
- **Run logs:** https://github.com/karanpreet8082/marketAnalysis/actions
- **Artifacts:** Portfolio JSON files retained for 7 days

Example log output:
```
2024-05-31 18:45:00 - [INFO] - ============================================================
2024-05-31 18:45:00 - [INFO] - TRADING AGENT CYCLE START
2024-05-31 18:45:00 - [INFO] - ============================================================
2024-05-31 18:45:01 - [INFO] - Market is open (9:15 AM - 3:30 PM IST)
2024-05-31 18:45:01 - [INFO] - Selected 20 stocks for analysis
2024-05-31 18:45:05 - [INFO] - Fetched data for 18 stocks
2024-05-31 18:45:06 - [INFO] - Running strategy analysis...
2024-05-31 18:45:08 - [INFO] - Generated 5 BUY signals (confidence >= 0.6)
2024-05-31 18:45:09 - [INFO] - Executing trades...
2024-05-31 18:45:09 - [INFO] - BUY 10 x RELIANCE.NS @ ₹2800.50 | Cost: ₹28,005
2024-05-31 18:45:09 - [INFO] - Portfolio saved to data/trading_agent_portfolio.json
2024-05-31 18:45:10 - [INFO] - Git commit successful: Trading Agent: Portfolio update at 2024-05-31 18:15:10 IST
2024-05-31 18:45:10 - [INFO] - Git push successful
```

---

## 🧪 Testing

### Unit Tests
Test individual strategy components:
```bash
pytest tests/test_trading_agent.py -v
```

### Integration Test
Full workflow simulation:
```bash
python3 src/trading_agent.py --test
```

### Dry Run
Analyze without trading:
```bash
python3 src/trading_agent.py --dry-run
```

---

## 📚 Files Overview

```
marketAnalysis/
├── src/
│   ├── trading_agent.py          # Main trading engine (THIS IS NEW)
│   ├── config.py                 # Configuration parameters
│   ├── data_fetcher/             # YFinance data fetching
│   ├── analysis/                 # Technical analysis modules
│   └── portfolio/                # Portfolio management (reused)
├── data/
│   └── trading_agent_portfolio.json  # Portfolio state (auto-created)
├── .github/
│   └── workflows/
│       └── trading_cron.yml      # GitHub Actions CRON workflow (NEW)
└── requirements.txt              # Python dependencies (unchanged)
```

---

## 🚨 Important Notes

1. **Live Market Data:** Uses Yahoo Finance (yfinance) which lags by ~15-20 minutes. Consider upgrading to real-time API for production trading.

2. **Paper Trading Only:** This is a paper trading simulation. Use only with dummy/virtual money.

3. **IST Timezone:** All market hour checks use Asia/Kolkata (IST) timezone.

4. **Git Commits:** Portfolio updates are auto-committed every cycle. Ensure `GH_TOKEN` secret is configured.

5. **Backtest:** Backtest strategies thoroughly before enabling autonomous mode.

6. **Holidays:** Add Indian public holidays to skip list for production use.

---

## 🔗 Integration with Existing System

The trading agent integrates seamlessly with the existing `marketAnalysis` module:

```python
# Uses existing data fetcher
from src.data_fetcher import YFinanceFetcher

# Uses existing config
from src.config import MAX_POSITION_PERCENT, MAX_STOCKS_IN_PORTFOLIO

# Outputs Groww-like JSON (can feed into existing reporting module)
```

No modifications to existing code required!

---

## 📞 Support & Debugging

**Workflow fails?**
1. Check GitHub Actions logs: https://github.com/karanpreet8082/marketAnalysis/actions
2. Verify IST timezone offset: IST = UTC + 5:30 hours
3. Ensure `GH_TOKEN` secret is set in repository secrets
4. Check data fetcher connection (run main.py first)

**Portfolio not updating?**
1. Verify `data/trading_agent_portfolio.json` exists
2. Check git configuration in workflow
3. Review git push error logs

---

## 🎯 Future Enhancements

- [ ] Options strategy integration
- [ ] Machine learning signal generation (Random Forest, XGBoost)
- [ ] Real-time market data integration
- [ ] Slack/Email notifications on trades
- [ ] Web dashboard for live portfolio tracking
- [ ] Backtesting module for strategy validation
- [ ] Multi-timeframe analysis (5-min, 15-min, hourly)
- [ ] Sector rotation strategy
- [ ] Correlation-based hedging

---

## 📄 License

This trading agent is part of the marketAnalysis project and follows the same license terms.

---

**Last Updated:** 2024-05-31
**Agent Version:** 1.0
**Status:** Production Ready
