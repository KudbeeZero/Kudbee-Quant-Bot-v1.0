"""Kudbee Quant — an honest quantitative trading research toolkit.

Design contract (the "honesty layer"):
  1. No hardcoded performance numbers. If we cannot compute it from real
     data, it does not render.
  2. Paper-trading is the default. Live capital is an explicit opt-in.
  3. Every signal is a hypothesis to be measured, never a guarantee.
  4. Risk (drawdown, risk-of-ruin, CVaR) is reported as loudly as return.

See docs/PHILOSOPHY.md for the full rationale.
"""

__version__ = "0.1.0"
