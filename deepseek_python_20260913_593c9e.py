# consensus_engine.py
"""Motor Ensemble — combina 4 sistemas para emitir un consensus score 0-100."""
import numpy as np
import pandas as pd
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class SystemVote:
    name: str
    direction: str
    confidence: float
    conditions: List[str]


class ConsensusEngine:
    WEIGHTS = {'trend': 0.35, 'momentum': 0.25, 'mean_rev': 0.20, 'volatility': 0.20}
    TF_WEIGHTS = {'5m': 0.40, '15m': 0.35, '1h': 0.25}
    REGIME_FACTORS = {
        'Expansión': 1.20, 'Tendencia Fuerte': 1.15,
        'Tendencia Débil': 1.00, 'Chop': 0.60,
    }

    def compute(self, symbol: str, data: Dict[str, pd.DataFrame]) -> Dict:
        votes_by_tf: Dict[str, List[SystemVote]] = {}
        tf_scores: Dict[str, float] = {}

        for tf, df in data.items():
            if df is None or df.empty or len(df) < 60:
                continue
            votes = [
                self._trend(df),
                self._momentum(df),
                self._mean_rev(df),
                self._volatility(df),
            ]
            votes_by_tf[tf] = votes
            tf_scores[tf] = sum(v.confidence * self.WEIGHTS[v.name] for v in votes)

        if not tf_scores:
            return self._empty(symbol)

        final = sum(tf_scores.get(tf, 0) * w for tf, w in self.TF_WEIGHTS.items())

        regime = self._detect_regime(data.get('1h', pd.DataFrame()))
        final *= self.REGIME_FACTORS.get(regime, 0.80)
        final = float(np.clip(final, 0, 100))

        all_votes = [v for vs in votes_by_tf.values() for v in vs]
        longs = sum(1 for v in all_votes if v.direction == 'LONG')
        shorts = sum(1 for v in all_votes if v.direction == 'SHORT')
        direction = 'LONG' if longs > shorts else 'SHORT' if shorts > longs else None

        mtf_confirmed = all(tf in votes_by_tf for tf in ['5m', '15m', '1h'])

        return {
            'symbol': symbol,
            'consensus_score': final,
            'direction': direction,
            'regime': regime,
            'mtf_confirmed': mtf_confirmed,
            'tf_scores': tf_scores,
            'long_votes': longs,
            'short_votes': shorts,
        }

    def _trend(self, df: pd.DataFrame) -> SystemVote:
        close = df['close']
        ema_f = close.ewm(span=13).mean().iloc[-1]
        ema_s = close.ewm(span=34).mean().iloc[-1]
        slope = (ema_f - ema_s) / ema_s if ema_s > 0 else 0
        direction = 'LONG' if slope > 0 else 'SHORT'
        conf = float(min(abs(slope) * 2000, 100))
        return SystemVote('trend', direction, conf, ['ema_cross'])

    def _momentum(self, df: pd.DataFrame) -> SystemVote:
        close = df['close']
        roc = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100 if len(close) >= 10 else 0
        direction = 'LONG' if roc > 0 else 'SHORT'
        conf = float(min(abs(roc) * 15, 100))
        return SystemVote('momentum', direction, conf, ['roc'])

    def _mean_rev(self, df: pd.DataFrame) -> SystemVote:
        close = df['close']
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()
        if len(close) < 20 or std.iloc[-1] == 0:
            return SystemVote('mean_rev', 'NEUTRAL', 0, [])
        z = (close.iloc[-1] - sma.iloc[-1]) / std.iloc[-1]
        if z > 2:
            return SystemVote('mean_rev', 'SHORT', float(min(abs(z) * 25, 100)), ['z>2'])
        if z < -2:
            return SystemVote('mean_rev', 'LONG', float(min(abs(z) * 25, 100)), ['z<-2'])
        return SystemVote('mean_rev', 'NEUTRAL', 0, [])

    def _volatility(self, df: pd.DataFrame) -> SystemVote:
        high, low, close = df['high'], df['low'], df['close']
        atr = (high - low).rolling(14).mean()
        if atr.iloc[-1] == 0 or len(df) < 20:
            return SystemVote('volatility', 'NEUTRAL', 0, [])
        atr_pct = atr.iloc[-1] / close.iloc[-1]
        breakout_up = close.iloc[-1] > high.iloc[-20:-1].max()
        breakout_down = close.iloc[-1] < low.iloc[-20:-1].min()
        if breakout_up:
            return SystemVote('volatility', 'LONG', float(min(atr_pct * 5000, 100)), ['breakout_up'])
        if breakout_down:
            return SystemVote('volatility', 'SHORT', float(min(atr_pct * 5000, 100)), ['breakout_down'])
        return SystemVote('volatility', 'NEUTRAL', 0, [])

    def _detect_regime(self, df: pd.DataFrame) -> str:
        if df.empty or len(df) < 30:
            return 'Chop'
        high, low, close = df['high'], df['low'], df['close']
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr_pct = tr.rolling(14).mean().iloc[-1] / close.iloc[-1]
        if atr_pct > 0.02:
            return 'Expansión'
        if atr_pct > 0.01:
            return 'Tendencia Fuerte'
        if atr_pct > 0.005:
            return 'Tendencia Débil'
        return 'Chop'

    def _empty(self, symbol: str) -> Dict:
        return {
            'symbol': symbol, 'consensus_score': 0.0, 'direction': None,
            'regime': 'Chop', 'mtf_confirmed': False, 'tf_scores': {},
            'long_votes': 0, 'short_votes': 0,
        }