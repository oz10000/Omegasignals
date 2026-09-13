# omega_regime_detector.py
"""Detector de Ω-Regime mediante HMM + estacionalidad."""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, timedelta

TRANSITION_MATRIX = {
    'Ω': {'Ω': 0.72, 'S': 0.21, 'Chop': 0.07},
    'S': {'Ω': 0.18, 'S': 0.54, 'Chop': 0.28},
    'Chop': {'Ω': 0.06, 'S': 0.31, 'Chop': 0.63},
}

MONTHLY_PROB = {
    1: 0.221, 2: 0.187, 3: 0.153, 4: 0.128, 5: 0.104, 6: 0.082,
    7: 0.146, 8: 0.192, 9: 0.284, 10: 0.382, 11: 0.428, 12: 0.354,
}

LIQUIDITY_BETA = {
    'BTC/USDT': 0.92, 'ETH/USDT': 0.88, 'SOL/USDT': 1.15,
    'BNB/USDT': 0.78, 'LINK/USDT': 0.95, 'AVAX/USDT': 1.08,
    'XRP/USDT': 0.72, 'ADA/USDT': 0.68, 'DOGE/USDT': 1.24,
    'PEPE/USDT': 1.68,
}


@dataclass
class OmegaRegimeState:
    current_regime: str
    probability_next_7d: float
    probability_next_30d: float
    expected_days_omega: float
    best_assets: List[str]
    best_hours: List[int]
    phase: str


class OmegaRegimeDetector:
    def __init__(self):
        self.transition = TRANSITION_MATRIX
        self.monthly_prob = MONTHLY_PROB
        self.liq_beta = LIQUIDITY_BETA

    def detect_current_regime(self, data: Dict[str, pd.DataFrame]) -> str:
        df = data.get('1h')
        if df is None or df.empty or len(df) < 60:
            return 'Chop'
        df = df.iloc[:-1]
        close = df['close'].iloc[-1]
        high, low = df['high'], df['low']

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = atr / close

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        alpha = 1 / 14
        atr_s = tr.ewm(alpha=alpha, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s
        minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9) * 100
        adx = dx.ewm(alpha=alpha, adjust=False).mean().iloc[-1]

        if adx > 35 and atr_pct > 0.008:
            return 'Ω'
        if adx > 28 and atr_pct > 0.005:
            return 'S'
        return 'Chop'

    def predict_next_window(self, current_regime: str, days_ahead: int = 30) -> OmegaRegimeState:
        p7 = self.transition[current_regime]['Ω']
        month = datetime.now().month
        p_seasonal = self.monthly_prob.get(month, 0.10)
        p30 = 1 - (1 - p7) ** (days_ahead / 7) * (1 - p_seasonal)
        expected_days = p30 * days_ahead * 0.085

        best_assets = sorted(self.liq_beta.items(), key=lambda x: -x[1])[:5]
        best_assets = [a for a, _ in best_assets]

        phase = self._detect_phase(current_regime, p7)

        return OmegaRegimeState(
            current_regime=current_regime,
            probability_next_7d=p7,
            probability_next_30d=p30,
            expected_days_omega=expected_days,
            best_assets=best_assets,
            best_hours=[2, 3, 4, 13, 14, 15, 16],
            phase=phase,
        )

    def _detect_phase(self, regime: str, p7: float) -> str:
        if regime == 'Ω':
            return 'expansion' if p7 > 0.65 else 'agotamiento'
        if regime == 'S':
            return 'inicio' if p7 > 0.20 else 'preparacion'
        return 'espera'

    def generate_regime_report(self, data: Dict[str, pd.DataFrame]) -> Dict:
        current = self.detect_current_regime(data)
        prediction = self.predict_next_window(current)
        return {
            'current_regime': current,
            'probability_7d': prediction.probability_next_7d,
            'probability_30d': prediction.probability_next_30d,
            'expected_days': prediction.expected_days_omega,
            'best_assets': prediction.best_assets,
            'best_hours': prediction.best_hours,
            'phase': prediction.phase,
            'recommendation': self._recommendation(prediction),
        }

    def _recommendation(self, state: OmegaRegimeState) -> str:
        if state.current_regime == 'Ω':
            return "✅ OPERAR PLENO — Régimen Omega activo"
        if state.probability_next_7d > 0.30:
            return "⚠️ PREPARAR — Ω-Regime probable en 7 días"
        if state.probability_next_30d > 0.35:
            return "📊 MONITOREAR — Ω-Regime probable en 30 días"
        return "⏸️ ESPERAR — Sin Ω-Regime en horizonte cercano"
