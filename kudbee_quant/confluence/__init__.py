"""Confluence scoring and the studies that TEST whether confluence pays.

The thesis — "the more levels stack at a zone, the higher the probability" — is
itself a falsifiable hypothesis. We score how many distinct reference levels
cluster within a tolerance band, then measure whether higher confluence
actually produces a bigger or more reliable reaction than a low-confluence
zone (and than a null). We do not assume it does.
"""

from .scorer import (
    add_confluence,
    confluence_reaction_study,
    range_exhaustion_study,
)
from .stack import (
    confluence_directional_study,
    confluence_position,
    confluence_score,
    factor_votes,
)

__all__ = [
    "add_confluence", "confluence_reaction_study", "range_exhaustion_study",
    "confluence_directional_study", "confluence_position", "confluence_score",
    "factor_votes",
]
