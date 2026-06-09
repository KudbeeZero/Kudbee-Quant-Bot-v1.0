"""Prediction journal — how the system learns alongside the trader.

Discretionary chart reads (e.g. "this red vector at the daily open gets
recovered this week") are falsifiable predictions. We log each one with its
level, direction, and deadline, then verify it against real price data once
the deadline passes. Over time this builds an HONEST, measured track record of
the trader's calls by setup type — turning discretionary skill into a number
instead of a vibe. No cherry-picking: every logged call is scored, hit or miss.
"""

from .journal import Prediction, TradeJournal

__all__ = ["Prediction", "TradeJournal"]
