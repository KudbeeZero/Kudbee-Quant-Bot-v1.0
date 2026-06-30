"""Position sizing, leverage & risk-of-ruin — the math that turns a loss
distribution into a SAFE LEVERAGE number.

Built from two research passes (sources in docs/MEMORY §22). Everything works from
a list of per-trade R outcomes (and per-trade adverse moves for the perp map), so
it plugs straight into the journal / backtest trade record.

The throughline: every safe-size method scales roughly as 1/variance or
1/|worst loss| — so cutting the loss tail (KudbeeX's fast-fail rule, §21) directly
RAISES the safe leverage ceiling. These functions quantify that.

HONESTY CAVEATS (do not skip):
- Kelly / optimal-f assume the edge is KNOWN and STATIONARY. A backtest estimates
  it with error, so full Kelly is an overbet → always trade a FRACTION (¼–½).
- Optimal-f is a CEILING you stay well below, never a target (it implies
  max-loss-sized drawdowns).
- Liquidation is driven by intra-trade MAX ADVERSE EXCURSION (and mark price),
  NOT the closing R — feed actual MAE, not final R, into the leverage map.
"""
from __future__ import annotations

import numpy as np


def kelly_gaussian(R) -> float:
    """f* ≈ mean/variance (Thorp) — fraction of equity to risk per 1R. 0 if no edge."""
    R = np.asarray(R, float)
    if R.size == 0 or R.var() == 0:
        return 0.0
    return max(0.0, float(R.mean() / R.var()))


def kelly_empirical(R) -> float:
    """Exact Kelly for an R-multiple distribution: solve E[R/(1+fR)] = 0 for f,
    using the whole distribution (not the win/loss binary). numpy bisection, no
    scipy dependency. Returns 0 if there is no positive-growth edge."""
    R = np.asarray(R, float)
    if R.size == 0:
        return 0.0
    g = lambda f: np.mean(R / (1.0 + f * R))
    if g(1e-9) <= 0:
        return 0.0
    lo, hi = 1e-9, 1.0 / (abs(R.min()) + 1e-9) - 1e-6   # 1+fR>0 keeps log defined
    if hi <= lo:
        return 0.0
    for _ in range(100):                                 # bisection
        mid = 0.5 * (lo + hi)
        if g(mid) > 0:
            lo = mid
        else:
            hi = mid
    return float(0.5 * (lo + hi))


def optimal_f(R) -> float:
    """Ralph Vince empirical optimal f (maximises geometric growth on the trade
    list). A CEILING, not a target — trade a fraction of it."""
    R = np.asarray(R, float)
    if R.size == 0 or R.min() >= 0:
        return 0.0
    worst = abs(R.min())
    fs = np.linspace(0.001, 0.999, 999)
    ghpr = [np.exp(np.mean(np.log(np.clip(1 + f * (R / worst), 1e-9, None)))) for f in fs]
    return float(fs[int(np.argmax(ghpr))])


def risk_of_ruin_closed(R, units: float) -> float:
    """Closed-form gambler's-ruin: ((1-edge)/(1+edge))^units, edge = mean R.
    ``units`` = account / risk-per-trade (number of 1R losses to zero)."""
    R = np.asarray(R, float)
    edge = R.mean()
    if edge <= 0:
        return 1.0
    return float(((1 - edge) / (1 + edge)) ** units)


def ror_montecarlo(R, risk_frac: float, n_trades: int = 500, n_sims: int = 20000,
                   ruin_dd: float = 0.5, seed: int = 0) -> float:
    """Monte-Carlo probability of a ``ruin_dd`` peak-to-trough drawdown when risking
    ``risk_frac`` of equity per 1R, resampling the actual R-list. The honest RoR —
    closed forms assume fixed bets + i.i.d.; this uses your real distribution."""
    R = np.asarray(R, float)
    if R.size == 0:
        return 0.0
    rng = np.random.default_rng(seed)
    ruined = 0
    for _ in range(n_sims):
        eq = peak = 1.0
        for r in rng.choice(R, n_trades):
            eq *= (1 + risk_frac * r)
            peak = max(peak, eq)
            if eq <= peak * (1 - ruin_dd):
                ruined += 1
                break
    return ruined / n_sims


def liq_distance(leverage: float, mmr: float = 0.005) -> float:
    """Adverse price move (fraction) to liquidation for isolated margin:
    1/leverage − maintenance-margin-rate. (20x ≈ 5%, 40x ≈ 2.5%.)"""
    return 1.0 / leverage - mmr


def max_safe_leverage(adverse_moves, n_trades: int, alpha: float = 0.01,
                      mmr: float = 0.005, levs=None) -> float:
    """Highest leverage whose per-horizon liquidation probability stays ≤ ``alpha``.

    ``adverse_moves``: per-trade WORST adverse excursion as a fraction of entry
    (use real MAE, not closing R). ``n_trades``: trades over the horizon. Scans
    leverage down until P(any liquidation over n_trades) ≤ alpha."""
    am = np.asarray(adverse_moves, float)
    if am.size == 0:
        return 0.0
    levs = levs if levs is not None else np.arange(50, 0.5, -0.5)
    for lev in levs:
        d = liq_distance(lev, mmr)
        if d <= 0:
            continue
        p_liq = float(np.mean(am > d))
        if 1 - (1 - p_liq) ** n_trades <= alpha:
            return float(lev)
    return 0.5


def vol_target_multiplier(realized_vol: float, target_vol: float = 0.40) -> float:
    """Position multiplier for constant-volatility sizing: target/realized
    (Moskowitz-Ooi-Pedersen; Barroso-Santa-Clara). De-levers when vol spikes."""
    if realized_vol <= 0:
        return 0.0
    return target_vol / realized_vol


def summary(R, adverse_moves=None, n_trades: int = 500, alpha: float = 0.01,
            mmr: float = 0.005, kelly_frac: float = 0.25) -> dict:
    """One-call risk report from a list of per-trade R outcomes."""
    R = np.asarray(R, float)
    fk = kelly_empirical(R)
    out = {
        "n_trades": int(R.size),
        "mean_r": round(float(R.mean()), 4) if R.size else 0.0,
        "std_r": round(float(R.std()), 4) if R.size else 0.0,
        "kelly_full": round(fk, 4),
        "kelly_gaussian": round(kelly_gaussian(R), 4),
        "kelly_fraction_used": kelly_frac,
        "risk_per_trade_frac": round(fk * kelly_frac, 4),       # ¼-Kelly default
        "optimal_f": round(optimal_f(R), 4),
        "ror_quarter_kelly": round(ror_montecarlo(R, fk * kelly_frac, n_trades), 4),
    }
    if adverse_moves is not None and len(adverse_moves):
        out["max_safe_leverage"] = max_safe_leverage(adverse_moves, n_trades, alpha, mmr)
        out["alpha_liq"] = alpha
    return out


# --- additive default-off experiment gates/sizers (Improvements 3-5) ---------
# These live as submodules of this package; the position-sizing math above is the
# original module's content, preserved verbatim when risk.py became a package.
from .correlation_guard import CorrelationGuard  # noqa: E402,F401
from .drawdown_guard import DrawdownGuard  # noqa: E402,F401
from .session_sizer import session_risk_multiplier, sized_risk  # noqa: E402,F401
