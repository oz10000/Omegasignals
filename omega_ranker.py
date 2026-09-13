# omega_ranker.py
# ============================================================
# Omega Ranking Engine — ranking probabilístico 0-100 + tiers.
# v3.2: SL/TP con piso y techo para evitar valores absurdos.
# ============================================================
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List

from config import (
    TIER_THRESHOLDS, OMEGA_WEIGHTS, SCORE_TO_WR,
    ATR_MULT_SL, DEFAULT_ATR_MULT_SL,
    TP_MULT_BY_TIER, TRAILING_DISTANCE, DEFAULT_TRAILING,
    TRAILING_ACTIVATION_BY_TIER, BE_TRIGGER_BY_TIER,
    LEVERAGE_BY_TIER, COST_TOTAL,
    SL_MIN_PCT, SL_MAX_PCT, TP_MIN_PCT,
)
from omega_regime_detector import OmegaRegimeDetector

logger = logging.getLogger(__name__)


@dataclass
class OmegaSignal:
    symbol: str
    direction: str
    omega_score: float
    tier: str
    confidence: float
    estimated_wr: float
    estimated_pf: float
    estimated_dd: float
    entry_price: float
    stop_loss: float
    take_profit: float
    break_even_price: float
    be_trigger_pct: float
    trailing_distance: float
    trailing_activation_pct: float
    leverage_max: int
    regime: str
    conditions: List[str] = field(default_factory=list)
    consensus_score: float = 0.0
    mtf_confirmed: bool = False


class OmegaRanker:
    def __init__(self):
        self.tier_thresholds = TIER_THRESHOLDS
        self.regime_detector = OmegaRegimeDetector()

    # --------------------------------------------------------
    # RANKING PRINCIPAL
    # --------------------------------------------------------
    def rank(self, signals: List[dict],
             data_dict: Dict[str, pd.DataFrame]) -> List[OmegaSignal]:
        omega_signals: List[OmegaSignal] = []
        for sig in signals:
            if not sig.get('is_valid'):
                continue
            sym = sig['symbol']
            df = data_dict.get(sym)
            if df is None or df.empty:
                continue
            try:
                osig = self._build_omega(sig, df)
                omega_signals.append(osig)
            except Exception as e:
                logger.warning(f"Error ranking {sym}: {e}")

        omega_signals.sort(key=lambda x: -x.omega_score)
        return omega_signals

    # --------------------------------------------------------
    # CONSTRUCCIÓN DEL OMEGA SIGNAL
    # --------------------------------------------------------
    def _build_omega(self, sig: dict, df: pd.DataFrame) -> OmegaSignal:
        sym = sig['symbol']
        close = float(df['close'].iloc[-1])

        consensus = float(sig.get('consensus_score', 50.0))
        mtf_confirmed = bool(sig.get('mtf_confirmed', False))
        mtf_score = 100.0 if mtf_confirmed else 50.0

        regime = sig.get('regime', 'Chop')
        regime_scores = {
            'Expansión': 100, 'Tendencia Fuerte': 90,
            'Tendencia Débil': 60, 'Chop': 20,
        }
        regime_score = regime_scores.get(regime, 30)

        atr_pct = float(sig.get('atr_pct', 0.01))
        if 0.005 <= atr_pct <= 0.015:
            vol_score = 100.0
        elif 0.003 <= atr_pct <= 0.025:
            vol_score = 70.0
        else:
            vol_score = 30.0

        hist_wr, hist_pf, hist_dd = self._stats_from_score(consensus)
        hist_wr_score = hist_wr * 100
        liquidity_score = 80.0

        omega = (
            OMEGA_WEIGHTS['consensus'] * consensus +
            OMEGA_WEIGHTS['mtf'] * mtf_score +
            OMEGA_WEIGHTS['regime'] * regime_score +
            OMEGA_WEIGHTS['volatility'] * vol_score +
            OMEGA_WEIGHTS['historical_wr'] * hist_wr_score +
            OMEGA_WEIGHTS['liquidity'] * liquidity_score
        )

        # Bonus/penalización por régimen detectado en vivo
        try:
            live_regime = self.regime_detector.detect_current_regime({'1h': df})
            if live_regime == 'Ω':
                omega = min(omega * 1.10, 100)
            elif live_regime == 'S':
                omega = min(omega * 1.03, 100)
            elif live_regime == 'Chop':
                omega = omega * 0.85
        except Exception:
            pass

        # Ajuste por hora (UTC)
        try:
            hour = df.index[-1].hour
        except Exception:
            hour = 12
        if hour in [2, 3, 4, 13, 14, 15, 16]:
            omega = min(omega * 1.05, 100)
        elif hour in [8, 9, 20, 21]:
            omega = omega * 0.92

        omega = float(np.clip(omega, 0, 100))
        tier = self._classify_tier(omega)

        # ---- SL con piso y techo ----
        atr_mult = ATR_MULT_SL.get(sym, DEFAULT_ATR_MULT_SL)
        sl_distance = atr_mult * atr_pct
        sl_distance = max(min(sl_distance, SL_MAX_PCT), SL_MIN_PCT)

        # ---- TP con piso mínimo ----
        tp_mult = TP_MULT_BY_TIER.get(tier, 1.0)
        tp_distance = max(tp_mult * atr_pct, TP_MIN_PCT)

        # ---- BE trigger ----
        be_trigger = BE_TRIGGER_BY_TIER.get(tier, 0.5)
        be_trigger_pct = be_trigger * atr_pct

        # ---- Precios ----
        direction = sig['direction']
        if direction == 'LONG':
            sl = close * (1 - sl_distance)
            tp = close * (1 + tp_distance)
            be = close * (1 + COST_TOTAL)
        else:
            sl = close * (1 + sl_distance)
            tp = close * (1 - tp_distance)
            be = close * (1 - COST_TOTAL)

        trailing = TRAILING_DISTANCE.get(sym, DEFAULT_TRAILING)
        trailing_act = TRAILING_ACTIVATION_BY_TIER.get(tier, 0.5) * atr_pct

        leverage = LEVERAGE_BY_TIER.get(tier, 1)
        conditions = self._conditions(sig, regime, mtf_confirmed)

        return OmegaSignal(
            symbol=sym,
            direction=direction,
            omega_score=omega,
            tier=tier,
            confidence=omega / 100.0,
            estimated_wr=hist_wr,
            estimated_pf=hist_pf,
            estimated_dd=hist_dd,
            entry_price=close,
            stop_loss=sl,
            take_profit=tp,
            break_even_price=be,
            be_trigger_pct=be_trigger_pct,
            trailing_distance=trailing,
            trailing_activation_pct=trailing_act,
            leverage_max=leverage,
            regime=regime,
            conditions=conditions,
            consensus_score=consensus,
            mtf_confirmed=mtf_confirmed,
        )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------
    def _classify_tier(self, score: float) -> str:
        for tier, thr in self.tier_thresholds.items():
            if score >= thr:
                return tier
        return 'NO-TIER'

    def _stats_from_score(self, score_0_100: float):
        for bin_str, s in SCORE_TO_WR.items():
            low, high = bin_str.split('-')
            if float(low) <= score_0_100 <= float(high):
                return s['wr'], s['pf'], s['dd']
        return 0.50, 1.0, -0.15

    def _conditions(self, sig: dict, regime: str, mtf: bool) -> List[str]:
        c = []
        if sig.get('adx', 0) >= 30:
            c.append('ADX≥30')
        if sig.get('ker', 0) >= 0.55:
            c.append('KER≥0.55')
        if mtf:
            c.append('Multi-TF✓')
        if regime in ('Expansión', 'Tendencia Fuerte'):
            c.append(f'Régimen:{regime}')
        return c
