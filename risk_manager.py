# risk_manager.py
"""Gestión de Stop Loss dinámico basado en ATR."""
from config import ATR_MULT_SL, DEFAULT_ATR_MULT_SL


def compute_stop_loss(entry: float, atr_pct: float,
                      direction: str, symbol: str) -> float:
    mult = ATR_MULT_SL.get(symbol, DEFAULT_ATR_MULT_SL)
    dist = mult * atr_pct
    if direction == 'LONG':
        return entry * (1 - dist)
    return entry * (1 + dist)


def compute_position_size(capital: float, risk_pct: float,
                          entry: float, stop: float, leverage: int = 1) -> float:
    risk_amount = capital * risk_pct
    per_unit = abs(entry - stop)
    if per_unit <= 0:
        return 0.0
    qty = risk_amount / per_unit
    max_notional = capital * leverage
    return min(qty, max_notional / entry)
