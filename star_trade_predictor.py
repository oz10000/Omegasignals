# star_trade_predictor.py
# ============================================================
# Detector y predictor de Trades Estrella (horario Argentina UTC-3).
# v3.2: usa STAR_WINDOWS y BEST_DAYS desde config.py.
# ============================================================
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta
from config import TZ_ARGENTINA, STAR_WINDOWS, BEST_DAYS


@dataclass
class StarTradePrediction:
    is_in_window: bool
    current_window_label: str
    minutes_until_next: int
    next_window_label: str
    next_window_start: str
    next_window_quality: int
    star_trades_today: List[dict]
    next_star_time: str
    expected_assets: List[str]
    recommended_leverage: int
    confidence: float
    day_name: str


class StarTradePredictor:
    def __init__(self):
        self.windows = STAR_WINDOWS
        self.best_days = BEST_DAYS
        self.tz = TZ_ARGENTINA

    def _now_ar(self) -> datetime:
        return datetime.now(self.tz)

    def _in_window(self, now: datetime, start: tuple, end: tuple) -> bool:
        h, m = now.hour, now.minute
        sh, sm = start
        eh, em = end
        current = h * 60 + m
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        if start_min <= end_min:
            return start_min <= current <= end_min
        return current >= start_min or current <= end_min

    def _minutes_until(self, now: datetime, start: tuple) -> int:
        sh, sm = start
        target = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return int((target - now).total_seconds() / 60)

    def predict(self, current_regime: str = 'Chop',
                today_trades: List[dict] = None) -> StarTradePrediction:
        now = self._now_ar()
        today_trades = today_trades or []

        # ¿Estamos en una ventana activa?
        current_label = '⏸️ Fuera de ventana'
        current_quality = 0
        for w in self.windows:
            if self._in_window(now, w['start'], w['end']):
                current_label = w['label']
                current_quality = w['quality']
                break

        # Próxima ventana de calidad ≥ 4
        future_windows = []
        for w in self.windows:
            if w['quality'] >= 4:
                mins = self._minutes_until(now, w['start'])
                future_windows.append((mins, w))
        future_windows.sort(key=lambda x: x[0])
        next_mins, next_w = (
            future_windows[0] if future_windows else (9999, self.windows[0])
        )

        # Confianza ajustada
        day_factor = self.best_days.get(now.weekday(), 1.0)
        regime_factor = {'Ω': 1.20, 'S': 1.05, 'Chop': 0.70}.get(
            current_regime, 0.80
        )
        confidence = min(next_w['wr'] * day_factor * regime_factor, 0.98)

        # Activos probables
        assets = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        if next_w['quality'] >= 5:
            assets.append('BNB/USDT')

        day_names = [
            'Lunes', 'Martes', 'Miércoles', 'Jueves',
            'Viernes', 'Sábado', 'Domingo',
        ]

        return StarTradePrediction(
            is_in_window=current_quality >= 4,
            current_window_label=current_label,
            minutes_until_next=next_mins,
            next_window_label=next_w['label'],
            next_window_start=f"{next_w['start'][0]:02d}:{next_w['start'][1]:02d}",
            next_window_quality=next_w['quality'],
            star_trades_today=today_trades,
            next_star_time=(now + timedelta(minutes=next_mins)).strftime("%H:%M"),
            expected_assets=assets,
            recommended_leverage=next_w['lev'],
            confidence=confidence,
            day_name=day_names[now.weekday()],
        )
