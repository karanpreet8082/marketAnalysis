# Indian Stock Market Analysis Dashboard 📊

An automated **hourly** stock analysis agent for Indian markets (NSE/BSE) with a web dashboard featuring:
- Real-time recommendations during market hours
- Portfolio tracking with P&L
- Sell transaction history with profit/loss analysis

**100% Free** - Runs on GitHub Actions, hosted on GitHub Pages, no servers needed!

## Features

- 📈 **Hourly Analysis**: Updates every hour during market hours (9:15 AM - 3:30 PM IST)
- 📊 **Technical Analysis**: RSI, MACD, Moving Averages, Bollinger Bands, Volume
- 💼 **Portfolio Tracking**: Add your holdings, track current value and P&L
- 💰 **Sell History**: Track all sells with profit/loss based on average buy price
- 🎯 **Risk Buckets**: Conservative, Moderate, Aggressive categorization
- 🌐 **Web Dashboard**: Beautiful responsive UI hosted on GitHub Pages

## Quick Start

### 1. Fork this Repository

Click the **Fork** button on GitHub to create your own copy.

### 2. Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Set Source to **GitHub Actions**
3. Your dashboard will be available at: `https://YOUR_USERNAME.github.io/marketAnalysis/`

### 3. Enable GitHub Actions

1. Go to **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. The analysis runs automatically every hour during market hours (Mon-Fri)

### 4. (Optional) Add Twelve Data API

If you want backup data source:
1. Sign up at [twelvedata.com](https://twelvedata.com) (free tier: 800 calls/day)
2. Go to **Settings** → **Secrets** → **Actions**
3. Add secret: `TWELVE_DATA_API_KEY`

> **Note:** The agent works perfectly with just Yahoo Finance (no signup needed)!

## How It Works

### Market Hours Schedule

The agent runs every hour during Indian market hours:
- 9:15 AM, 10:15 AM, 11:15 AM, 12:15 PM, 1:15 PM, 2:15 PM, 3:15 PM IST
- Monday to Friday only

### Dashboard Tabs

| Tab | Description |
|-----|-------------|
| 📈 **Recommendations** | Current hour's buy recommendations by risk bucket |
| 📋 **All Signals** | Complete list of analyzed stocks with scores |
| 💼 **My Portfolio** | Your holdings with live P&L tracking |
| 💰 **Sell History** | All sell transactions with profit/loss |
| 🤖 **Agent Portfolio** | Agent's auto-traded portfolio performance |

### Agent Portfolio (New!)

The agent automatically trades its own recommendations to prove they work:

- **Daily at 5:30 PM IST**: Picks top 2 high-confidence stocks
- **Virtual Budget**: ₹1,00,000 starting capital
- **Auto-exits**: When target hit 🎯, stop-loss hit 🛑, or 30 days elapsed ⏱️
- **Track Record**: See win rate, total return, all trades

This lets you see how well the agent's recommendations actually perform over time!

### Portfolio Tracking

1. **Add Holdings**: Search for a stock, enter buy price and quantity
2. **Track P&L**: See current value, profit/loss, and return %
3. **Sell Stocks**: Record sells to track realized gains/losses
4. **Average Price**: Multiple buys calculate weighted average automatically

### Profit/Loss Calculation

For sells, profit is calculated using **weighted average buy price**:

```
Avg Buy Price = Total Cost of All Buys / Total Quantity Bought
Profit/Loss = (Sell Price - Avg Buy Price) × Quantity Sold
```

## Technical Details

### Analysis Indicators

| Indicator | Purpose |
|-----------|---------|
| RSI (14) | Overbought/Oversold detection |
| MACD | Trend and momentum |
| SMA (20, 50, 200) | Trend direction |
| Bollinger Bands | Volatility and price levels |
| Volume | Trade confirmation |

### Risk Buckets

| Bucket | Criteria | Allocation |
|--------|----------|------------|
| 🟢 Conservative | Large cap, Beta < 1.0 | 50% |
| 🟡 Moderate | Mid cap, Beta 0.8-1.3 | 35% |
| 🔴 Aggressive | Small cap, Beta > 1.3 | 15% |

### Data Storage

- **Recommendations**: Generated fresh each hour by GitHub Actions
- **Portfolio & Sells**: Stored in your browser's localStorage (private to you)

## Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/marketAnalysis.git
cd marketAnalysis

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run analysis (test mode - 10 stocks)
cd src
python main.py --test

# Open the generated report
open ../reports/index.html  # or just open in browser
```

### Run Options

```bash
# Full analysis (100 stocks)
python main.py

# Custom budget
python main.py --budget 30000

# Analyze more/fewer stocks
python main.py --max-stocks 50
```

## Project Structure

```
marketAnalysis/
├── src/
│   ├── main.py                # Entry point
│   ├── config.py              # Settings
│   ├── data_fetcher/          # Stock data fetching
│   │   ├── yfinance_fetcher.py
│   │   └── stock_list.py      # 500 Indian stocks
│   ├── analysis/              # Analysis modules
│   │   ├── technical.py
│   │   ├── fundamental.py
│   │   └── signals.py
│   ├── portfolio/             # Portfolio management
│   │   ├── allocator.py
│   │   └── risk_manager.py
│   └── reporting/             # Dashboard generation
│       └── html_generator.py
├── reports/                   # Generated dashboard
├── .github/workflows/         # GitHub Actions
└── requirements.txt
```

## Manual Trigger

You can manually run the analysis anytime:

1. Go to **Actions** tab
2. Select **"Hourly Stock Analysis"**
3. Click **"Run workflow"**
4. Optionally adjust budget and max stocks
5. Click **"Run workflow"** button

## FAQ

**Q: Is my portfolio data safe?**
A: Yes! Portfolio data is stored only in YOUR browser's localStorage. It never leaves your device.

**Q: Why hourly updates?**
A: Stock prices change throughout the day. Hourly analysis catches intraday opportunities.

**Q: Can I use this for real trading?**
A: This is for educational/analysis purposes. Always do your own research before investing.

**Q: Will GitHub Actions cost money?**
A: No! GitHub Actions is free for public repositories (2000 minutes/month for private).

## ⚠️ Disclaimer

- This tool provides **algorithmic analysis**, NOT financial advice
- Past performance does NOT guarantee future results
- Always do your own research before investing
- Consult a SEBI-registered advisor for investment decisions
- Stock market investments carry risk of capital loss

## Contributing

Pull requests welcome! Ideas:
- Add more technical indicators
- Improve signal algorithm
- Add backtesting
- Support more markets

## License

MIT License - Use freely, but remember the disclaimers!

---

**Happy Investing! 📈**

*Built with ❤️ for the Indian investor community*
