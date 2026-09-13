# leverage_manager.py
"""Apalancamiento dinámico según tier y WR."""
from config import LEVERAGE_BY_TIER, LEVERAGE_CAP


def compute_max_leverage(tier: str, estimated_wr: float, estimated_dd: float) -> int:
    base = LEVERAGE_BY_TIER.get(tier, 1)
    if abs(estimated_dd) > 0.15:
        base = max(1, base - 3)
    elif abs(estimated_dd) > 0.08:
        base = max(1, base - 1)
    if estimated_wr >= 0.94:
        base = min(base + 2, LEVERAGE_CAP)
    elif estimated_wr >= 0.90:
        base = min(base + 1, LEVERAGE_CAP)
    return min(base, LEVERAGE_CAP)