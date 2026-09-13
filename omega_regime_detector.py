# omega_regime_detector.py
# ============================================================
# Detector de Ω-Regime mediante HMM + estacionalidad.
# FIX v3.2: separación correcta de variables Series vs escalares
# para evitar AttributeError: 'numpy.float64' object has no attribute 'shift'
# ============================================================
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

# ============================================================
# MATRIZ DE TRANSICIÓN (entrenada 2024-2026)
# ============================================================
TRANSITION_MATRIX = {
    'Ω': {'Ω': 0.72, 'S': 0.21, 'Chop': 0.07},
    'S': {'Ω': 0.18, 'S': 0.54, 'Chop': 0.28},
    'Chop': {'Ω': 0.06, 'S': 0.31, 'Chop': 0.63},
}

# ============================================================
# PROBABILIDAD MENSUAL DE Ω-REGIME
# ============================================================
MONTHLY_PROB = {
    1: 0.221, 2: 0.187, 3: 0.153, 4: 0.128, 5: 0.104, 6: 0.082,
    7: 0.146, 8: 0.192, 9: 0.284, 10: 0.382, 11: 0.428, 12: 0.354,
}

# ============================================================
# BETA A LIQUIDEZ GLOBAL POR ACTIVO
# ============================================================
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
    """
    Detecta el régimen actual y predice la activación del Ω-Regime.
    """

    def __init__(self):
        self.transition = TRANSITION_MATRIX
        self.monthly_prob = MONTHLY_PROB
        self.liq_beta = LIQUIDITY_BETA

    # --------------------------------------------------------
    # DETECCIÓN DEL RÉGIMEN ACTUAL
    # --------------------------------------------------------
    def detect_current_regime(self, data: Dict[str, pd.DataFrame]) -> str:
        """
        Clasifica el régimen actual usando ADX Wilder y ATR Wilder.
        Retorna: 'Ω', 'S' o 'Chop'.
        """
        df = data.get('1h')
        if df is None or df.empty or len(df) < 60:
            return 'Chop'

        # Sin look-ahead: descartar última vela
        df = df.iloc[:-1]
        if len(df) < 30:
            return 'Chop'

        # ---- Variables correctamente tipadas ----
        high_series = df['high']        # Series
        low_series = df['low']          # Series
        close_series = df['close']      # Series
        close_last = float(close_series.iloc[-1])  # escalar

        if close_last <= 0:
            return 'Chop'

        # ---- True Range (usa Series) ----
        tr = pd.concat([
            high_series - low_series,
            (high_series - close_series.shift()).abs(),
            (low_series - close_series.shift()).abs(),
        ], axis=1).max(axis=1)

        atr = tr.rolling(14).mean().iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return 'Chop'
        atr_pct = atr / close_last

        # ---- ADX Wilder ----
        plus_dm = high_series.diff()
        minus_dm = -low_series.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        alpha = 1 / 14
        atr_s = tr.ewm(alpha=alpha, adjust=False).mean().replace(0, np.nan)
        plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s
        minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s
        di_sum = (plus_di + minus_di).replace(0, np.nan)
        dx = (plus_di - minus_di).abs() / di_sum * 100
        dx = dx.fillna(0).replace([np.inf, -np.inf], 0)
        adx_series = dx.ewm(alpha=alpha, adjust=False).mean()
        adx = float(adx_series.iloc[-1]) if not adx_series.empty else 0.0

        if pd.isna(adx):
            return 'Chop'

        # ---- Clasificación ----
        if adx > 35 and atr_pct > 0.008:
            return 'Ω'
        if adx > 28 and atr_pct > 0.005:
            return 'S'
        return 'Chop'

    # --------------------------------------------------------
    # PREDICCIÓN DEL PRÓXIMO RÉGIMEN
    # --------------------------------------------------------
    def predict_next_window(self, current_regime: str,
                            days_ahead: int = 30) -> OmegaRegimeState:
        """
        Predice la probabilidad de Ω-Regime en la próxima ventana.
        Combina cadena de Markov + estacionalidad mensual.
        """
        # Probabilidad por cadena de Markov (7 días)
        p7 = self.transition.get(current_regime, self.transition['Chop'])['Ω']

        # Probabilidad estacional (mes actual)
        month = datetime.now().month
        p_seasonal = self.monthly_prob.get(month, 0.10)

        # Combinación bayesiana simple
        p30 = 1 - (1 - p7) ** (days_ahead / 7) * (1 - p_seasonal)
        p30 = float(np.clip(p30, 0, 1))

        # Días esperados (8.5% de días son Ω en promedio)
        expected_days = p30 * days_ahead * 0.085

        # Activos con mayor beta a liquidez
        best_assets = sorted(self.liq_beta.items(), key=lambda x: -x[1])[:5]
        best_assets = [a for a, _ in best_assets]

        # Fase del régimen
        phase = self._detect_phase(current_regime, p7)

        return OmegaRegimeState(
            current_regime=current_regime,
            probability_next_7d=float(p7),
            probability_next_30d=float(p30),
            expected_days_omega=float(expected_days),
            best_assets=best_assets,
            best_hours=[2, 3, 4, 13, 14, 15, 16],
            phase=phase,
        )

    def _detect_phase(self, regime: str, p7: float) -> str:
        """Determina la fase del régimen."""
        if regime == 'Ω':
            return 'expansion' if p7 > 0.65 else 'agotamiento'
        if regime == 'S':
            return 'inicio' if p7 > 0.20 else 'preparacion'
        return 'espera'

    # --------------------------------------------------------
    # REPORTE COMPLETO
    # --------------------------------------------------------
    def generate_regime_report(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Genera reporte completo del régimen con manejo de errores."""
        try:
            current = self.detect_current_regime(data)
        except Exception:
            current = 'Chop'

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
        """Genera recomendación operativa."""
        if state.current_regime == 'Ω':
            return "✅ OPERAR PLENO — Régimen Omega activo"
        if state.probability_next_7d > 0.30:
            return "⚠️ PREPARAR — Ω-Regime probable en 7 días"
        if state.probability_next_30d > 0.35:
            return "📊 MONITOREAR — Ω-Regime probable en 30 días"
        return "⏸️ ESPERAR — Sin Ω-Regime en horizonte cercano"
