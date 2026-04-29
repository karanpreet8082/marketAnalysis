"""
Stock universe for Indian markets - NSE/BSE listed stocks.

This module contains a curated list of ~500 stocks from:
- NIFTY 50 (Large Cap index constituents)
- NIFTY Next 50 
- NIFTY Midcap 150
- NIFTY Smallcap 250
- Additional high-volume BSE stocks
"""

from typing import List, Dict
import pandas as pd
from pathlib import Path

# Nifty 50 - Large Cap Blue Chips
NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "HCLTECH", "AXISBANK", "ASIANPAINT",
    "MARUTI", "SUNPHARMA", "TITAN", "BAJFINANCE", "DMART", "ULTRACEMCO",
    "NTPC", "WIPRO", "ADANIENT", "POWERGRID", "M&M", "NESTLEIND", "TATAMOTORS",
    "ONGC", "JSWSTEEL", "TATASTEEL", "TECHM", "HDFCLIFE", "ADANIPORTS",
    "COALINDIA", "BAJAJFINSV", "GRASIM", "BRITANNIA", "SBILIFE", "DIVISLAB",
    "CIPLA", "BPCL", "APOLLOHOSP", "INDUSINDBK", "TATACONSUM", "EICHERMOT",
    "HEROMOTOCO", "DRREDDY", "HINDALCO", "UPL", "BAJAJ-AUTO"
]

# Nifty Next 50 - Large/Mid Cap
NIFTY_NEXT_50 = [
    "ADANIGREEN", "BANKBARODA", "VEDL", "HAVELLS", "GODREJCP", "DLF", "DABUR",
    "PIDILITIND", "SIEMENS", "ICICIPRULI", "INDUSTOWER", "PNB", "AMBUJACEM",
    "NAUKRI", "MARICO", "BOSCHLTD", "CHOLAFIN", "ABB", "SRF", "ICICIGI",
    "COLPAL", "BERGEPAINT", "INDIGO", "TATAPOWER", "MUTHOOTFIN", "JINDALSTEL",
    "TORNTPHARM", "ACC", "GAIL", "IOC", "IRCTC", "PIIND", "CANBK", "PEL",
    "LUPIN", "ZOMATO", "YESBANK", "OFSS", "MCDOWELL-N", "PETRONET", "AUROPHARMA",
    "TRENT", "MAXHEALTH", "PAGEIND", "POLICYBZR", "ALKEM", "SOLARINDS", "BIOCON",
    "LICI", "MOTHERSON"
]

# Nifty Midcap 150 - Sample (key stocks)
NIFTY_MIDCAP_150_SAMPLE = [
    "PERSISTENT", "COFORGE", "DIXON", "LTIM", "PHOENIXLTD", "FEDERALBNK",
    "TVSMOTOR", "CROMPTON", "VOLTAS", "IDFCFIRSTB", "LTTS", "MRF", "SONACOMS",
    "OBEROIRLTY", "ASTRAL", "SCHAEFFLER", "SKFINDIA", "TIMKEN", "ESCORTS",
    "BHARATFORG", "SUNDARMFIN", "CUMMINSIND", "TATACHEM", "HONAUT", "NHPC",
    "NMDC", "BEL", "BHEL", "HAL", "IRFC", "RECLTD", "PFC", "SJVN", "RVNL",
    "CONCOR", "GMRINFRA", "SUZLON", "IREDA", "IDEAFORGE", "ZEEL", "TV18BRDCST",
    "NETWORK18", "ABFRL", "RAYMOND", "VGUARD", "BLUESTARCO", "WHIRLPOOL",
    "CENTURYTEX", "TRIDENT", "WELSPUNIND", "RATNAMANI", "JINDALSAW", "APLAPOLLO",
    "NAVINFLUOR", "DEEPAKNTR", "AARTIIND", "CLEAN", "ATUL", "FLUOROCHEM",
    "ALKYLAMINE", "FINEORG", "GALAXYSURF", "VINATIORGA", "ANURAS", "LXCHEM",
    "AETHER", "BALRAMCHIN", "EIDPARRY", "TRIVENI", "SHREECEM", "JKCEMENT",
    "RAMCOCEM", "STARCEMENT", "HEIDELBERG", "INDIACEM", "ORIENTCEM", "PRSMJOHNSN",
    "RAIN", "GRAPHITE", "HIMADRI", "CARBONTOOL", "INOXWIND", "RITES", "IRCON"
]

# Nifty Smallcap 250 - Sample (high volume small caps)
NIFTY_SMALLCAP_250_SAMPLE = [
    "RBLBANK", "MANAPPURAM", "L&TFH", "UJJIVANSFB", "EQUITASBNK", "KARURVYSYA",
    "CENTRALBK", "DCBBANK", "SOUTHBANK", "TMBANK", "LAKSHVILAS", "DHANI",
    "JMFINANCIL", "IIFL", "MOTILALOFS", "ANGELONE", "CDSL", "BSE", "CAMS",
    "KPITTECH", "BIRLASOFT", "MPHASIS", "ZENSAR", "NIITLTD", "CYIENT",
    "TATAELXSI", "HAPPSTMNDS", "ROUTE", "MASTEK", "NEWGEN", "INTELLECT",
    "TANLA", "AFFLE", "LATENTVIEW", "DATAPATTNS", "MAPLETREE", "DELHIVERY",
    "XPRESSBEES", "ECOM", "MAHLIFE", "EMAMILTD", "JYOTHYLAB", "TCNSBRANDS",
    "VMART", "SHOPERSTOP", "RELAXO", "BATAINDIA", "METROBRAND", "CAMPUS",
    "GOCOLORS", "KALYANKJIL", "SENCO", "TITAN", "RAJESHEXPO", "APLLTD",
    "GRANULES", "LAURUSLABS", "NATCOPHARM", "IPCALAB", "AJANTPHARM", "GLENMARK",
    "ABBOTINDIA", "PFIZER", "GLAXO", "SANOFI", "JBCHEPHARM", "SOLARA",
    "SYNGENE", "SEQUENT", "HIKAL", "DIVIS", "NEULANDLAB", "SHILPAMED",
    "ADVENZYMES", "ENZENE", "STARHEALTH", "NIACL", "GICRE", "ICICI_LOMBARD",
    "HDFCAMC", "NAM_INDIA", "UTIAMC", "KFINTECH", "SBICARDS", "PAYTM",
    "ZOMATO", "NYKAA", "CARTRADE", "EASEMYTRIP", "IXIGO", "YATRA", "THOMASCOOK"
]

# Additional high-volume BSE stocks not in above indices
BSE_ADDITIONAL = [
    "ADANIPOWER", "ADANITRANS", "ADANIENSOL", "ATGL", "AWL", "WOCKPHARMA",
    "CYPCHEM", "INDIABULLS", "IBULHSGFIN", "OBEROIRLTY", "PRESTIGE", "BRIGADE",
    "SOBHA", "GODREJPROP", "SUNTV", "PVRINOX", "SAREGAMA", "TIPS", "NAZARA",
    "DBREALTY", "ANANTRAJ", "MAHINDCIE", "ARVINDFASH", "KPRMILL", "TNPETRO",
    "COCHINSHIP", "GRSE", "MAZDA", "BDL", "BEML", "ITI", "MIDHANI", "NLCINDIA"
]

# Combined list of all stocks with NSE suffix
NIFTY_500_SYMBOLS = list(set(
    NIFTY_50 + NIFTY_NEXT_50 + NIFTY_MIDCAP_150_SAMPLE + 
    NIFTY_SMALLCAP_250_SAMPLE + BSE_ADDITIONAL
))

def get_stock_universe(include_suffix: bool = True) -> List[str]:
    """
    Get the complete stock universe for analysis.
    
    Args:
        include_suffix: If True, append '.NS' suffix for Yahoo Finance compatibility
        
    Returns:
        List of stock symbols
    """
    if include_suffix:
        return [f"{symbol}.NS" for symbol in NIFTY_500_SYMBOLS]
    return NIFTY_500_SYMBOLS


def get_stock_info() -> Dict[str, Dict]:
    """
    Get stock metadata including sector and market cap category.
    
    Returns:
        Dictionary mapping symbol to metadata
    """
    stock_info = {}
    
    # Large cap (Nifty 50)
    for symbol in NIFTY_50:
        stock_info[symbol] = {
            "category": "large_cap",
            "index": "NIFTY50",
            "risk_bucket": "conservative"
        }
    
    # Large/Mid cap (Nifty Next 50)
    for symbol in NIFTY_NEXT_50:
        if symbol not in stock_info:
            stock_info[symbol] = {
                "category": "large_mid_cap",
                "index": "NIFTYNEXT50",
                "risk_bucket": "moderate"
            }
    
    # Mid cap
    for symbol in NIFTY_MIDCAP_150_SAMPLE:
        if symbol not in stock_info:
            stock_info[symbol] = {
                "category": "mid_cap",
                "index": "NIFTYMIDCAP150",
                "risk_bucket": "moderate"
            }
    
    # Small cap
    for symbol in NIFTY_SMALLCAP_250_SAMPLE + BSE_ADDITIONAL:
        if symbol not in stock_info:
            stock_info[symbol] = {
                "category": "small_cap",
                "index": "SMALLCAP",
                "risk_bucket": "aggressive"
            }
    
    return stock_info


def save_stock_universe_csv(output_path: Path = None):
    """Save stock universe to CSV file."""
    if output_path is None:
        output_path = Path(__file__).parent.parent.parent / "data" / "stock_universe.csv"
    
    stock_info = get_stock_info()
    data = []
    
    for symbol, info in stock_info.items():
        data.append({
            "symbol": symbol,
            "yahoo_symbol": f"{symbol}.NS",
            "category": info["category"],
            "index": info["index"],
            "risk_bucket": info["risk_bucket"]
        })
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} stocks to {output_path}")
    return df


if __name__ == "__main__":
    # Generate CSV when run directly
    df = save_stock_universe_csv()
    print(f"\nStock distribution:")
    print(df["category"].value_counts())
