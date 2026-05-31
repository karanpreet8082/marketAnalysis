# Autonomous Trading Agent - Architecture Document

## Executive Summary

The Autonomous Trading Agent is a production-grade algorithmic trading system designed to run entirely within GitHub Actions. It automates the entire process of:
1. Market data acquisition (NSE/BSE stocks)
2. Technical analysis using three complementary strategies
3. Trade decision-making via ensemble voting
4. Portfolio management and risk control
5. State persistence and audit trail
6. Scheduled execution every 30 minutes during market hours

This document provides detailed technical specifications for implementation, integration, and maintenance.

---

## 1. System Architecture

### 1.1 High-Level Flow

```
GitHub Actions CRON → Market Check → Data Fetch → Strategy Analysis 
→ Signal Generation → Trade Execution → Portfolio Update → Git Commit
```

### Key Components:
- **StrategyEngine**: Three-strategy ensemble (Momentum, MeanRev, Breakout)
- **PortfolioManager**: Holdings, orders, P&L tracking
- **TradingAgent**: Main orchestrator and market-hours validator
- **GitHub Actions**: Cron-based trigger every 30 minutes

---

## 2. Strategy Ensemble Details

### Momentum (40% weight)
- **Supertrend(14,3)**: Identifies uptrend/downtrend
- **MACD(12,26,9)**: Momentum divergence signals
- **EMA Crossover (9vs21)**: Trend confirmation

Score Range: -1.0 to +1.0

### Mean Reversion (35% weight)
- **RSI(14)**: Oversold < 30, Overbought > 70
- **Bollinger Bands(20,2)**: Price extremes

Score Range: -1.0 to +1.0

### Breakout (25% weight)
- **Volume Spike**: Current > 1.5x 20-period average
- **Support/Resistance**: 20-period High/Low breaks

Score Range: -1.0 to +1.0

### Ensemble Decision
```
Ensemble = Momentum×0.4 + MeanRev×0.35 + Breakout×0.25
BUY if Score > 0.6
SELL if Score < -0.6
HOLD otherwise
```

---

## 3. Position Sizing & Risk Management

```
Initial Capital: ₹10,00,000

Per Position:
├─ Max: 20% (₹2,00,000)
├─ Allocation: 12% per trade
└─ Qty = Allocation / Current Price

Portfolio:
├─ Min positions: 3 (diversification)
├─ Max positions: 10
└─ Max daily deployment: 60%
```

---

## 4. Data Persistence

Portfolio saved as JSON with:
- **Capital**: Initial, current cash, invested, portfolio value
- **Holdings**: Symbol, quantity, avg price, current price, P&L
- **Orders**: BUY/SELL history with timestamp, price, strategies
- **Dashboard**: Total returns, daily P&L, position count

Persisted via:
1. Save to `data/trading_agent_portfolio.json`
2. Git add + commit
3. Git push to origin/main

---

## 5. GitHub Actions Schedule

IST 9:15 AM to 3:30 PM = UTC 3:45 AM to 10:00 AM

Every 30 minutes:
```yaml
schedule:
  - cron: '45 3 * * 1-5'   # 9:15 AM IST
  - cron: '15 4 * * 1-5'   # 9:45 AM IST
  - cron: '45 4 * * 1-5'   # 10:15 AM IST
  # ... (13 more for every 30 mins)
  - cron: '0 10 * * 1-5'   # 3:30 PM IST
```

---

## 6. Error Handling

| Error | Action |
|-------|--------|
| Market closed | Exit cleanly (code 0) |
| Weekend/Holiday | Skip execution |
| Data fetch fail | Retry 3×, then exit (code 1) |
| Insufficient cash | Skip trade, continue |
| Position exceeds 20% | Reject order |
| Git push fails | Log, continue |

---

## 7. Key Files

```
src/trading_agent.py          # Main trading engine
.github/workflows/trading_cron.yml  # GitHub Actions workflow
data/trading_agent_portfolio.json   # Portfolio state
TRADING_AGENT_README.md       # User guide
TRADING_AGENT_ARCHITECTURE.md # This document
```

---

## 8. Monitoring & Debugging

Monitor via:
- GitHub Actions tab: All execution logs
- Portfolio JSON: Complete audit trail in git
- Artifacts: Saved for 7 days

Debug checklist:
- [ ] Python syntax: `python3 -m py_compile src/trading_agent.py`
- [ ] Market hours: IST 9:15 AM - 3:30 PM, Mon-Fri
- [ ] Data fetch: yfinance working, rate limits OK
- [ ] Strategy scores: Verify ensemble calculation
- [ ] Git config: user.email and user.name set
- [ ] GH_TOKEN: Secret configured in repo settings

---

## 9. Performance Expectations

- **Execution time**: ~5-8 seconds per cycle
- **Data fetch**: 1-2 seconds for 20 stocks
- **Strategy analysis**: 2-3 seconds
- **Git operations**: 1-2 seconds

- **Signal frequency**: 1-5 BUY signals per cycle (varies)
- **Trade execution**: 0-5 trades per cycle
- **Return expectations**: Varied (simulation depends on strategies)

---

## 10. Production Deployment

Before going live:
- [x] Syntax validation
- [x] Dependencies verified
- [x] Error handling complete
- [x] Market hours logic correct
- [x] Git integration working
- [ ] Backtest on historical data (user responsibility)
- [ ] Paper trading validated (recommended)
- [ ] Risk limits reviewed (user responsibility)
- [ ] Monitoring alerts set (optional)

---

## Next Steps

1. **Deploy**: Push trading_cron.yml to .github/workflows/
2. **Test**: Trigger manual workflow run (workflow_dispatch)
3. **Monitor**: Check Actions tab for logs
4. **Review**: Check data/trading_agent_portfolio.json updates
5. **Iterate**: Adjust strategies as needed per performance

For detailed information, see TRADING_AGENT_README.md

---

**Version:** 1.0  
**Last Updated:** 2024-05-31  
**Status:** Production Ready
