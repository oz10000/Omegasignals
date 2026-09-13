# execution_manager.py
"""Máquina de estados para gestionar cada posición."""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import Enum

from trailing_engine import TrailingState, init_trailing, update_trailing
from config import COST_TOTAL


class PositionState(str, Enum):
    OPEN = 'OPEN'
    PROFIT = 'PROFIT'
    BE_ACTIVE = 'BE_ACTIVE'
    TRAILING_ACTIVE = 'TRAILING_ACTIVE'
    CLOSED = 'CLOSED'


@dataclass
class Position:
    symbol: str
    direction: str
    entry_price: float
    entry_time: datetime
    initial_stop: float
    stop: float
    take_profit: float
    break_even_price: float
    be_trigger_pct: float
    trailing_distance: float
    trailing_activation_pct: float
    leverage: int
    size: float
    state: PositionState = PositionState.OPEN
    best_price: float = 0.0
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl_pct: float = 0.0
    pnl_abs: float = 0.0
    bars_held: int = 0
    trailing: Optional[TrailingState] = None

    def __post_init__(self):
        self.best_price = self.entry_price
        self.trailing = init_trailing(self.entry_price, self.direction)


def process_bar(pos: Position, high: float, low: float, close: float) -> Position:
    if pos.state == PositionState.CLOSED:
        return pos
    pos.bars_held += 1

    if pos.direction == 'LONG' and low <= pos.stop:
        return _close(pos, pos.stop, 'SL')
    if pos.direction == 'SHORT' and high >= pos.stop:
        return _close(pos, pos.stop, 'SL')

    if pos.direction == 'LONG' and high >= pos.take_profit:
        return _close(pos, pos.take_profit, 'TP')
    if pos.direction == 'SHORT' and low <= pos.take_profit:
        return _close(pos, pos.take_profit, 'TP')

    be_trigger = pos.entry_price * (1 + pos.be_trigger_pct) if pos.direction == 'LONG' \
                 else pos.entry_price * (1 - pos.be_trigger_pct)
    if pos.state in (PositionState.OPEN, PositionState.PROFIT):
        if (pos.direction == 'LONG' and high >= be_trigger) or \
           (pos.direction == 'SHORT' and low <= be_trigger):
            pos.stop = pos.break_even_price
            pos.state = PositionState.BE_ACTIVE

    activation = pos.entry_price * (1 + pos.trailing_activation_pct) if pos.direction == 'LONG' \
                 else pos.entry_price * (1 - pos.trailing_activation_pct)
    if pos.state == PositionState.BE_ACTIVE:
        pos.trailing = update_trailing(
            pos.trailing, close, pos.stop, pos.direction,
            pos.trailing_distance, activation,
        )
        if pos.trailing.active:
            pos.state = PositionState.TRAILING_ACTIVE
            pos.stop = pos.trailing.stop

    if pos.state == PositionState.OPEN:
        if (pos.direction == 'LONG' and close > pos.entry_price) or \
           (pos.direction == 'SHORT' and close < pos.entry_price):
            pos.state = PositionState.PROFIT

    return pos


def _close(pos: Position, price: float, reason: str) -> Position:
    pos.exit_price = price
    pos.exit_time = datetime.utcnow()
    pos.exit_reason = reason
    pos.state = PositionState.CLOSED
    if pos.direction == 'LONG':
        pos.pnl_pct = (price - pos.entry_price) / pos.entry_price * 100
    else:
        pos.pnl_pct = (pos.entry_price - price) / pos.entry_price * 100
    pos.pnl_pct -= COST_TOTAL * 100
    pos.pnl_abs = pos.pnl_pct / 100 * pos.entry_price * pos.size
    return pos