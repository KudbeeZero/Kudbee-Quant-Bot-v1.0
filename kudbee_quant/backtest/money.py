"""Dollar-and-cents account simulation on top of the R-based bracket engine.

R-expectancy is the honest metric, but it's abstract. This converts a sequence
of bracket trades into an actual EQUITY CURVE in dollars, so we can answer "if I
put $100 in at 10x, what happens?" — and, more importantly, show what PROPER
position sizing looks like next to the reckless full-notional version.

Two sizing modes:
  full_notional   : each trade uses notional = leverage x equity (the naive
                    "I have $100 and 10x, so I trade $1000" — risk per trade is
                    NOT controlled; it equals leverage x stop%, often 20-30%).
  fixed_fractional: risk a fixed fraction of CURRENT equity per trade (e.g. 2%).
                    The position size is solved from the stop distance; leverage
                    is just a cap. THIS is how you survive 300 trades.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .bracket import _resolve_full


def trade_log(
    df: pd.DataFrame,
    signal: pd.Series,
    stop_atr: float = 1.5,
    target_r: float = 3.0,
    max_bars: int = 24,
    fee_pct: float = 0.0004,
    limit_retrace_atr: float | None = 0.25,
    entry_window: int = 6,
) -> pd.DataFrame:
    """Per-trade log with the fields a dollar sim needs: entry timestamp, entry
    price, stop distance as a fraction of price (stop_pct), and net R outcome
    (already net of the ``fee_pct`` round-trip). Same entry/resolution logic as
    ``bracket_backtest`` (limit-retrace maker entry, conservative stop-first).
    """
    need = {"high", "low", "close", "atr"}
    if not need <= set(df.columns):
        raise ValueError(f"trade_log needs columns {sorted(need)}")
    close = df["close"].to_numpy(); high = df["high"].to_numpy()
    low = df["low"].to_numpy(); atr = df["atr"].to_numpy()
    ts = (pd.to_datetime(df["timestamp"], utc=True).to_numpy()
          if "timestamp" in df.columns else np.arange(len(df)))
    sig = pd.Series(signal, index=df.index).fillna(0.0).to_numpy()
    n = len(df)
    rows = []
    busy_until = -1
    for t in range(n - 1):
        if sig[t] == 0 or t <= busy_until:
            continue
        direction = 1.0 if sig[t] > 0 else -1.0
        sd = stop_atr * atr[t]
        if not np.isfinite(sd) or sd <= 0:
            continue
        if limit_retrace_atr is None:
            entry, entry_bar = close[t], t
        else:
            limit = close[t] - direction * limit_retrace_atr * atr[t]
            ewin = min(t + entry_window, n - 1)
            entry_bar = None
            for j in range(t + 1, ewin + 1):
                if (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit):
                    entry_bar = j; break
            if entry_bar is None:
                continue
            entry = limit
        stop = entry - direction * sd
        target = entry + direction * sd * target_r
        end = min(entry_bar + max_bars, n - 1)
        outcome, exit_j = _resolve_full(direction, entry, stop, target, sd, target_r,
                                        high, low, close, entry_bar, end)
        stop_pct = sd / entry
        net_r = outcome - fee_pct / stop_pct      # fee in R = fee_pct / stop_pct
        rows.append({"timestamp": ts[entry_bar], "direction": direction,
                     "entry": float(entry), "stop_pct": float(stop_pct),
                     "outcome_r": float(outcome), "net_r": float(net_r)})
        busy_until = exit_j
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class AccountResult:
    mode: str
    equity0: float
    equity_final: float
    n_trades: int
    ret_pct: float
    max_drawdown_pct: float
    ruined: bool                 # equity hit the wipeout floor
    worst_trade_pct: float
    avg_risk_pct: float          # mean $ risked per trade as % of equity
    equity_curve: list

    def summary(self) -> dict:
        return {"mode": self.mode, "equity_final": round(self.equity_final, 2),
                "ret_pct": round(self.ret_pct, 1), "max_dd_pct": round(self.max_drawdown_pct, 1),
                "ruined": self.ruined, "avg_risk_pct": round(self.avg_risk_pct, 1),
                "n_trades": self.n_trades}


def simulate_account(
    trades: pd.DataFrame,
    equity0: float = 100.0,
    mode: str = "fixed_fractional",
    risk_frac: float = 0.02,
    leverage: float = 10.0,
    ruin_floor: float = 0.10,
) -> AccountResult:
    """Walk a trade log into a dollar equity curve (compounding on current equity).

    Args:
        trades: output of ``trade_log`` (needs ``net_r`` and ``stop_pct``).
        equity0: starting account in $.
        mode: 'full_notional' (notional = leverage x equity, risk uncontrolled)
              or 'fixed_fractional' (risk ``risk_frac`` of equity per trade).
        risk_frac: fraction of equity risked per trade in fixed_fractional mode.
        leverage: max leverage (a hard cap on notional in BOTH modes).
        ruin_floor: equity fraction below which the account is "blown" and stops.
    """
    eq = equity0
    curve = [eq]
    risks = []
    peak = eq
    max_dd = 0.0
    worst = 0.0
    ruined = False
    floor = equity0 * ruin_floor
    for _, tr in trades.iterrows():
        stop_pct = tr["stop_pct"]
        if not np.isfinite(stop_pct) or stop_pct <= 0:
            continue
        if mode == "full_notional":
            notional = leverage * eq
        else:  # fixed_fractional: notional solved from the stop, capped by leverage
            notional = min((risk_frac * eq) / stop_pct, leverage * eq)
        dollar_per_r = notional * stop_pct            # $ value of 1R for this size
        pnl = tr["net_r"] * dollar_per_r
        risks.append(100.0 * dollar_per_r / eq)       # risk as % of equity
        worst = min(worst, 100.0 * pnl / eq)
        eq = eq + pnl
        curve.append(eq)
        peak = max(peak, eq)
        max_dd = min(max_dd, 100.0 * (eq - peak) / peak)
        if eq <= floor:
            ruined = True
            break
    return AccountResult(
        mode=mode, equity0=equity0, equity_final=eq, n_trades=len(curve) - 1,
        ret_pct=100.0 * (eq - equity0) / equity0, max_drawdown_pct=max_dd,
        ruined=ruined, worst_trade_pct=worst,
        avg_risk_pct=float(np.mean(risks)) if risks else 0.0, equity_curve=curve)
