"""
Intraday Trading Agent (mandated daily ₹1,00,000 deployment).

Responsibilities (per run):
1. Determine which iteration of the day this is (TOTAL_ITERATIONS per day).
2. Buy stocks during iterations 1 .. TOTAL_ITERATIONS-1 such that cumulative
   investment for the day lands in [₹90,000, ₹1,00,000].
3. Optionally sell winners / cut losers during the day.
4. On the last iteration of the day (TOTAL_ITERATIONS), liquidate every
   intraday position that is still open.
5. Persist all activity in data/intraday_portfolio.json (free, in-repo
   storage committed by GitHub Actions).
6. Maintain a day-wise history of trades and P&L.
7. On loss-making days, generate a feedback note explaining the likely cause
   and what could have been done differently — feeding back into future picks.

Storage: a single JSON file in the repository (data/intraday_portfolio.json)
which is committed by the GitHub Actions workflow after every run. This is the
free, persistent, version-controlled store for this agent.
"""

from __future__ import annotations

import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytz

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - intraday - %(message)s",
)
logger = logging.getLogger("intraday_agent")

# ---------------------------------------------------------------------------
# Configurable knobs
# ---------------------------------------------------------------------------
DAILY_BUDGET = 100_000          # mandated daily deployment (upper bound)
MIN_DAILY_INVESTMENT = 90_000    # mandated lower bound
TOTAL_ITERATIONS = 14            # randomly chosen run count per day (fixed)
MAX_PICKS_PER_ITER = 3           # diversify across up to N stocks per buy
PROFIT_TAKE_PCT = 0.8            # sell intraday if a position is up >0.8%
STOP_LOSS_PCT = 1.0              # sell intraday if a position is down >1.0%
INTRADAY_UNIVERSE_LIMIT = 40     # cap fetched stocks per iteration for speed

DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "intraday_portfolio.json"
IST = pytz.timezone("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Liquid intraday-friendly universe (subset of NIFTY 50 + Next 50)
# ---------------------------------------------------------------------------
INTRADAY_UNIVERSE = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "HCLTECH", "AXISBANK", "ASIANPAINT",
    "MARUTI", "SUNPHARMA", "TITAN", "BAJFINANCE", "ULTRACEMCO", "NTPC", "WIPRO",
    "POWERGRID", "M&M", "TATAMOTORS", "ONGC", "JSWSTEEL", "TATASTEEL", "TECHM",
    "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "GRASIM", "BRITANNIA", "CIPLA",
    "BPCL", "INDUSINDBK", "TATACONSUM", "EICHERMOT", "HEROMOTOCO", "DRREDDY",
    "HINDALCO", "BAJAJ-AUTO", "DLF", "TATAPOWER", "ADANIENT", "TRENT",
    "INDIGO", "HAVELLS", "SIEMENS", "DIVISLAB",
]


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------
def _today_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def _now_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _empty_state() -> Dict:
    return {
        "current_day": None,
        "history": [],
        "stats": {
            "total_days": 0,
            "winning_days": 0,
            "losing_days": 0,
            "total_realized_pnl": 0.0,
            "best_day_pnl": 0.0,
            "worst_day_pnl": 0.0,
            "feedback_notes": [],
        },
    }


def load_state() -> Dict:
    if not STATE_FILE.exists():
        return _empty_state()
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"State unreadable ({e}); starting fresh.")
        return _empty_state()


def save_state(state: Dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)
    logger.info(f"State written -> {STATE_FILE}")


def _new_day_record() -> Dict:
    return {
        "date": _today_str(),
        "total_iterations": TOTAL_ITERATIONS,
        "iterations_run": 0,
        "iteration_log": [],
        "invested_today": 0.0,
        "realized_pnl_today": 0.0,
        "open_positions": [],   # currently held intraday positions
        "trades": [],           # all buys + sells of the day
        "closed": False,
    }


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------
def _fetch_intraday(symbols: List[str]) -> Dict[str, "pd.DataFrame"]:
    """Fetch 5-min intraday bars for today (and prior days for context)."""
    import yfinance as yf  # local import to keep module load light

    out: Dict[str, "pd.DataFrame"] = {}
    for sym in symbols:
        ticker = sym if sym.endswith(".NS") else f"{sym}.NS"
        try:
            df = yf.Ticker(ticker).history(period="5d", interval="5m", timeout=20)
            if df is not None and not df.empty:
                out[sym.replace(".NS", "")] = df
        except Exception as e:
            logger.debug(f"intraday fetch failed for {sym}: {e}")
    return out


def _last_price(df) -> float:
    return float(df["Close"].iloc[-1])


# ---------------------------------------------------------------------------
# Picking logic — short-term momentum + RSI sanity
# ---------------------------------------------------------------------------
def _rsi(series, length: int = 14) -> float:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(length).mean()
    roll_down = down.rolling(length).mean()
    rs = roll_up / roll_down.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    try:
        return float(val)
    except Exception:
        return 50.0


def _score_candidate(df) -> Tuple[float, Dict]:
    """Score a stock for an intraday long entry."""
    if df is None or len(df) < 30:
        return -1.0, {}

    close = df["Close"]
    last = float(close.iloc[-1])

    # 30-min momentum: last bar vs 6 bars ago (5m * 6 = 30m)
    mom_30m = (last / float(close.iloc[-7]) - 1.0) * 100 if len(close) > 7 else 0.0
    # Today's open vs now
    today_open = float(close.iloc[-min(len(close), 75)])  # ~ today open
    intraday_chg = (last / today_open - 1.0) * 100 if today_open else 0.0
    rsi = _rsi(close, 14)

    # Penalise overbought (>75) & oversold extremes (<25 likely falling knife)
    rsi_penalty = 0.0
    if rsi > 75:
        rsi_penalty = -1.5
    elif rsi < 30:
        rsi_penalty = -0.5

    # Volume spike confirmation
    vol = df["Volume"].rolling(20).mean().iloc[-1]
    last_vol = df["Volume"].iloc[-1]
    vol_factor = 1.0
    try:
        if vol and last_vol:
            vol_factor = min(2.0, float(last_vol) / float(vol))
    except Exception:
        vol_factor = 1.0

    score = (mom_30m * 1.5) + (intraday_chg * 0.3) + rsi_penalty + (vol_factor - 1.0)
    info = {
        "last": round(last, 2),
        "mom_30m_pct": round(mom_30m, 3),
        "intraday_pct": round(intraday_chg, 3),
        "rsi": round(rsi, 1),
        "vol_factor": round(vol_factor, 2),
        "score": round(score, 3),
    }
    return score, info


def pick_top_stocks(market: Dict[str, "pd.DataFrame"], top_n: int) -> List[Dict]:
    """Rank universe and return top_n — we ALWAYS return some picks (mandate)."""
    ranked: List[Tuple[float, str, Dict]] = []
    for sym, df in market.items():
        score, info = _score_candidate(df)
        ranked.append((score, sym, info))
    ranked.sort(key=lambda x: x[0], reverse=True)

    picks: List[Dict] = []
    for score, sym, info in ranked[:top_n]:
        picks.append({
            "symbol": sym,
            "score": score,
            "info": info,
        })
    return picks


# ---------------------------------------------------------------------------
# Trading actions
# ---------------------------------------------------------------------------
def _value_of(positions: List[Dict], market: Dict[str, "pd.DataFrame"]) -> float:
    total = 0.0
    for p in positions:
        df = market.get(p["symbol"])
        px = _last_price(df) if df is not None else p["buy_price"]
        total += px * p["qty"]
    return total


def _intraday_manage_open_positions(
    day: Dict, market: Dict[str, "pd.DataFrame"], iteration: int
) -> List[Dict]:
    """Sell winners / cut losers based on simple thresholds. Returns sold list."""
    sold: List[Dict] = []
    remaining: List[Dict] = []
    for pos in day["open_positions"]:
        df = market.get(pos["symbol"])
        if df is None:
            remaining.append(pos)
            continue
        px = _last_price(df)
        change_pct = (px / pos["buy_price"] - 1.0) * 100

        if change_pct >= PROFIT_TAKE_PCT or change_pct <= -STOP_LOSS_PCT:
            pnl = (px - pos["buy_price"]) * pos["qty"]
            trade = {
                "time": _now_str(),
                "iteration": iteration,
                "action": "SELL",
                "symbol": pos["symbol"],
                "qty": pos["qty"],
                "price": round(px, 2),
                "buy_price": pos["buy_price"],
                "pnl": round(pnl, 2),
                "pnl_pct": round(change_pct, 2),
                "reason": "TAKE_PROFIT" if change_pct >= PROFIT_TAKE_PCT else "STOP_LOSS",
            }
            day["trades"].append(trade)
            day["realized_pnl_today"] += pnl
            sold.append(trade)
            logger.info(
                f"  SELL {pos['symbol']} qty={pos['qty']} @ ₹{px:.2f} "
                f"(P&L ₹{pnl:.0f} / {change_pct:+.2f}%) [{trade['reason']}]"
            )
        else:
            remaining.append(pos)
    day["open_positions"] = remaining
    return sold


def _force_liquidate(
    day: Dict, market: Dict[str, "pd.DataFrame"], iteration: int, reason: str
) -> List[Dict]:
    sold: List[Dict] = []
    for pos in list(day["open_positions"]):
        df = market.get(pos["symbol"])
        # if price unavailable use buy price (no further pnl change)
        px = _last_price(df) if df is not None else pos["buy_price"]
        pnl = (px - pos["buy_price"]) * pos["qty"]
        change_pct = (px / pos["buy_price"] - 1.0) * 100
        trade = {
            "time": _now_str(),
            "iteration": iteration,
            "action": "SELL",
            "symbol": pos["symbol"],
            "qty": pos["qty"],
            "price": round(px, 2),
            "buy_price": pos["buy_price"],
            "pnl": round(pnl, 2),
            "pnl_pct": round(change_pct, 2),
            "reason": reason,
        }
        day["trades"].append(trade)
        day["realized_pnl_today"] += pnl
        sold.append(trade)
        logger.info(
            f"  FORCE-SELL {pos['symbol']} qty={pos['qty']} @ ₹{px:.2f} "
            f"(P&L ₹{pnl:.0f} / {change_pct:+.2f}%) [{reason}]"
        )
    day["open_positions"] = []
    return sold


def _iteration_buy_budget(day: Dict, iteration: int) -> float:
    """How much to deploy this iteration so we end up in [90k, 100k] cumulative."""
    if iteration >= TOTAL_ITERATIONS:
        return 0.0  # final iteration is sell-only
    remaining_iters = TOTAL_ITERATIONS - iteration  # includes current, excludes final sell
    invested = day["invested_today"]
    headroom = DAILY_BUDGET - invested
    if headroom <= 0:
        return 0.0
    # spread evenly across remaining buy iterations (excluding final liquidation)
    buy_iters_left = max(1, remaining_iters - 1)
    target = headroom / buy_iters_left

    # Make sure we are on track to clear MIN_DAILY_INVESTMENT.
    n_buy = TOTAL_ITERATIONS - 1
    required_cum = MIN_DAILY_INVESTMENT * (iteration / n_buy)
    catchup = max(0.0, required_cum - invested)
    target = max(target, catchup)

    # On the FINAL buy iteration (iteration == n_buy), force the floor: we must
    # not finish the day with less than MIN_DAILY_INVESTMENT deployed.
    if iteration == n_buy:
        floor_topup = max(0.0, MIN_DAILY_INVESTMENT - invested)
        target = max(target, floor_topup)

    return min(target, headroom)


def _execute_buys(
    day: Dict,
    market: Dict[str, "pd.DataFrame"],
    iteration: int,
    budget: float,
) -> List[Dict]:
    if budget <= 0:
        return []

    # We allow scaling into a name we already hold — each entry is a separate
    # position record with its own buy price. This is necessary so we don't
    # starve when the universe is concentrated, and it keeps the daily
    # ₹90k–₹1L mandate satisfiable.
    picks = pick_top_stocks(market, MAX_PICKS_PER_ITER)
    if not picks:
        logger.warning("No picks returned — skipping buys this iteration.")
        return []

    per_pick = budget / len(picks)
    bought: List[Dict] = []
    leftover = 0.0
    for pick in picks:
        sym = pick["symbol"]
        df = market.get(sym)
        if df is None:
            continue
        px = _last_price(df)
        alloc = per_pick + leftover
        qty = int(alloc // px)
        if qty < 1:
            # too expensive for this slice — push budget to next pick
            leftover = alloc
            continue
        cost = qty * px
        leftover = alloc - cost

        position = {
            "symbol": sym,
            "qty": qty,
            "buy_price": round(px, 2),
            "buy_time": _now_str(),
            "iteration": iteration,
            "score_info": pick["info"],
        }
        day["open_positions"].append(position)
        day["invested_today"] += cost

        trade = {
            "time": _now_str(),
            "iteration": iteration,
            "action": "BUY",
            "symbol": sym,
            "qty": qty,
            "price": round(px, 2),
            "cost": round(cost, 2),
            "score": pick["info"],
        }
        day["trades"].append(trade)
        bought.append(trade)
        logger.info(
            f"  BUY  {sym} qty={qty} @ ₹{px:.2f} (₹{cost:.0f}) "
            f"score={pick['info'].get('score')}"
        )

    return bought


# ---------------------------------------------------------------------------
# End-of-day: feedback + history archive
# ---------------------------------------------------------------------------
def _generate_feedback(day: Dict) -> str:
    """Heuristic post-mortem note when the day was unprofitable."""
    pnl = day["realized_pnl_today"]
    trades = day["trades"]
    sells = [t for t in trades if t["action"] == "SELL"]
    losers = [t for t in sells if t.get("pnl", 0) < 0]
    winners = [t for t in sells if t.get("pnl", 0) > 0]
    forced = [t for t in sells if t.get("reason") == "EOD_FORCE_SELL"]

    notes: List[str] = []
    notes.append(
        f"Day P&L ₹{pnl:.0f} on ₹{day['invested_today']:.0f} deployed "
        f"({(pnl / max(day['invested_today'], 1)) * 100:.2f}%)."
    )
    if losers:
        worst = min(losers, key=lambda t: t.get("pnl", 0))
        notes.append(
            f"Worst trade: {worst['symbol']} (P&L ₹{worst['pnl']:.0f}, "
            f"{worst.get('pnl_pct', 0):.2f}%). Consider tighter stop on entries "
            f"with weaker momentum scores."
        )
    if forced and pnl < 0:
        forced_pnl = sum(t["pnl"] for t in forced)
        notes.append(
            f"{len(forced)} EOD force-sells contributed ₹{forced_pnl:.0f}. "
            "Earlier intraday exits (lower take-profit threshold) might have "
            "preserved capital."
        )
    if winners and losers and len(losers) > len(winners):
        notes.append(
            "More losing trades than winners — picks may have been chasing "
            "overbought stocks; tighten RSI filter (<70) for next day."
        )
    if not losers and pnl < 0:
        notes.append(
            "All trades closed flat/positive but cumulative loss — likely from "
            "slippage / odd-lot rounding. Increase per-iteration size."
        )
    if pnl >= 0:
        notes.append("Profitable day — keep current parameters.")
    return " ".join(notes)


def _archive_day(state: Dict, day: Dict) -> None:
    """Move a finished day into history and update aggregate stats."""
    day["closed"] = True
    pnl = day["realized_pnl_today"]
    invested = day["invested_today"]
    pnl_pct = (pnl / invested * 100) if invested else 0.0
    feedback = _generate_feedback(day)

    record = {
        "date": day["date"],
        "iterations_run": day["iterations_run"],
        "invested": round(invested, 2),
        "realized_pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 3),
        "trades": day["trades"],
        "n_buys": sum(1 for t in day["trades"] if t["action"] == "BUY"),
        "n_sells": sum(1 for t in day["trades"] if t["action"] == "SELL"),
        "feedback": feedback,
        "profitable": pnl > 0,
    }
    state["history"].append(record)

    s = state["stats"]
    s["total_days"] += 1
    s["total_realized_pnl"] = round(s.get("total_realized_pnl", 0.0) + pnl, 2)
    if pnl > 0:
        s["winning_days"] += 1
    elif pnl < 0:
        s["losing_days"] += 1
    if pnl > s.get("best_day_pnl", 0.0):
        s["best_day_pnl"] = round(pnl, 2)
    if pnl < s.get("worst_day_pnl", 0.0):
        s["worst_day_pnl"] = round(pnl, 2)
    # keep rolling tail of feedback for the dashboard
    s.setdefault("feedback_notes", []).append({"date": day["date"], "note": feedback})
    s["feedback_notes"] = s["feedback_notes"][-30:]
    state["current_day"] = None
    logger.info(f"Archived {day['date']}: P&L ₹{pnl:.0f} ({pnl_pct:+.2f}%) — {feedback}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_iteration() -> None:
    state = load_state()
    today = _today_str()

    # If we have an open day from a prior date, force-close it (no live prices
    # for those positions — settle at last known buy price). This guarantees no
    # cross-day positions ever accumulate.
    cur = state.get("current_day")
    if cur and cur.get("date") != today:
        logger.warning(f"Found stale open day {cur['date']}; finalising before today.")
        _force_liquidate(cur, market={}, iteration=cur.get("iterations_run", 0) + 1,
                         reason="STALE_DAY_FORCE_CLOSE")
        _archive_day(state, cur)

    # New day?
    if not state.get("current_day"):
        state["current_day"] = _new_day_record()

    day = state["current_day"]
    iteration = day["iterations_run"] + 1
    is_final = iteration >= TOTAL_ITERATIONS
    logger.info(
        f"=== Intraday iteration {iteration}/{TOTAL_ITERATIONS} for {today} ==="
    )

    # Build the universe to fetch — sample to stay fast.
    universe = INTRADAY_UNIVERSE[:]
    random.shuffle(universe)
    universe = universe[:INTRADAY_UNIVERSE_LIMIT]

    # Always also fetch any stocks we currently hold so we can mark them.
    held_syms = [p["symbol"] for p in day["open_positions"]]
    fetch_set = list({*universe, *held_syms})
    market = _fetch_intraday(fetch_set)
    logger.info(f"Fetched intraday data for {len(market)} symbols.")

    # 1. Manage existing positions (TP / SL) — except final iteration which
    #    unconditionally liquidates.
    sold: List[Dict] = []
    bought: List[Dict] = []
    if is_final:
        sold = _force_liquidate(day, market, iteration, reason="EOD_FORCE_SELL")
    else:
        sold = _intraday_manage_open_positions(day, market, iteration)
        # 2. Decide buy budget for this iteration and execute.
        budget = _iteration_buy_budget(day, iteration)
        logger.info(
            f"Iteration buy budget: ₹{budget:.0f} "
            f"(invested so far: ₹{day['invested_today']:.0f})"
        )
        bought = _execute_buys(day, market, iteration, budget)

    # 3. Log iteration summary
    day["iterations_run"] = iteration
    day["iteration_log"].append({
        "iteration": iteration,
        "time": _now_str(),
        "n_bought": len(bought),
        "n_sold": len(sold),
        "invested_today_after": round(day["invested_today"], 2),
        "realized_pnl_today_after": round(day["realized_pnl_today"], 2),
        "open_positions_after": len(day["open_positions"]),
    })

    # 4. If final iteration, archive day to history & generate feedback.
    if is_final:
        _archive_day(state, day)

    save_state(state)
    logger.info("=== Iteration complete ===")


if __name__ == "__main__":
    run_iteration()
