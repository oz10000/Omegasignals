# trailing_engine.py
"""Trailing Stop dinámico — sigue máximos/mínimos."""
from dataclasses import dataclass


@dataclass
class TrailingState:
    active: bool
    best_price: float
    stop: float


def init_trailing(entry: float, direction: str) -> TrailingState:
    return TrailingState(active=False, best_price=entry, stop=0.0)


def update_trailing(state: TrailingState, current_price: float,
                    current_stop: float, direction: str,
                    trailing_distance: float, activation_price: float) -> TrailingState:
    if not state.active:
        if direction == 'LONG' and current_price >= activation_price:
            state.active = True
            state.best_price = current_price
        elif direction == 'SHORT' and current_price <= activation_price:
            state.active = True
            state.best_price = current_price
        return state

    if direction == 'LONG':
        if current_price > state.best_price:
            state.best_price = current_price
        new_stop = state.best_price * (1 - trailing_distance)
        state.stop = max(current_stop, new_stop)
    else:
        if current_price < state.best_price:
            state.best_price = current_price
        new_stop = state.best_price * (1 + trailing_distance)
        state.stop = min(current_stop, new_stop)
    return state
