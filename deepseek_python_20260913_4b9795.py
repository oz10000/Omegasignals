# signal_engine.py
"""Genera señales base a partir de indicadores + consensus."""
import pandas as pd
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from indicator_engine import compute_adx, compute_atr, compute_ker, compute_ema, compute_regime
from consensus_engine import ConsensusEngine

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    symbol: str
    direction: str
    is_valid: bool
    reason: str
    entry_price: float
    score: float
    adx: float
    ker: float
    atr_pct: float
    atr_abs: float
    regime: str
    ema15: float
    ema50: float
    volume_ratio: float
    consensus_score: float
    mtf_confirmed: bool
    tf_scores: Dict = field(default_factory=dict)


class SignalEngine:
    def __init__(self):
        self.consensus = ConsensusEngine()

    def evaluate(self, symbol: str, data: Dict[str, pd.DataFrame]) -> Optional[Signal]:
        df = data.get('5m')
        if df is None or df.empty or len(df) < 30:
            return None

        df = df.iloc[:-1]
        if len(df) < 30:
            return None

        close = float(df['close'].iloc[-1])
        adx_s = compute_adx(df, 14)
        atr_s = compute_atr(df, 14)
        ker_s = compute_ker(df, 10)
        ema15 = float(compute_ema(df, 15).iloc[-1])
        ema50 = float(compute_ema(df, 50).iloc[-1])

        adx = float(adx_s.iloc[-1]) if not adx_s.empty else 0
        atr = float(atr_s.iloc[-1]) if not atr_s.empty else 0
        atr_pct = atr / close if close > 0 else 0
        ker = float(ker_s.iloc[-1]) if not ker_s.empty else 0
        regime = compute_regime(df, adx, atr_pct)

        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = float(df['volume'].iloc[-1] / avg_vol) if avg_vol > 0 else 0

        cons = self.consensus.compute(symbol, data)
        direction = cons.get('direction') or ('LONG' if close > ema15 else 'SHORT')

        is_valid = True
        reason = "OK"
        if regime == 'Chop':
            is_valid, reason = False, "Régimen Chop"
        elif direction == 'LONG' and close < ema15:
            is_valid, reason = False, "Precio < EMA15"
        elif direction == 'SHORT' and close > ema15:
            is_valid, reason = False, "Precio > EMA15"

        return Signal(
            symbol=symbol, direction=direction, is_valid=is_valid, reason=reason,
            entry_price=close, score=cons.get('consensus_score', 0) / 100.0,
            adx=adx, ker=ker, atr_pct=atr_pct, atr_abs=atr, regime=regime,
            ema15=ema15, ema50=ema50, volume_ratio=vol_ratio,
            consensus_score=cons.get('consensus_score', 0),
            mtf_confirmed=cons.get('mtf_confirmed', False),
            tf_scores=cons.get('tf_scores', {}),
        )

    def to_dict(self, sig: Signal) -> dict:
        return {
            'symbol': sig.symbol, 'direction': sig.direction,
            'is_valid': sig.is_valid, 'reason': sig.reason,
            'entry_price': sig.entry_price, 'score': sig.score,
            'adx': sig.adx, 'ker': sig.ker, 'atr_pct': sig.atr_pct,
            'atr_abs': sig.atr_abs, 'regime': sig.regime,
            'ema15': sig.ema15, 'ema50': sig.ema50,
            'volume_ratio': sig.volume_ratio,
            'consensus_score': sig.consensus_score,
            'mtf_confirmed': sig.mtf_confirmed,
        }