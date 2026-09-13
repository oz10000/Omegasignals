# main.py
# ============================================================
# Orquestador principal — pipeline completo + Star Trade Monitor.
# v3.2: manejo robusto de errores en régimen y star trades.
# ============================================================
import logging
from typing import List

from config import (
    SYMBOLS, TIMEFRAME_ENTRY, TIMEFRAME_CONFIRM, TIMEFRAME_TREND,
)
from data_engine import DataEngine
from signal_engine import SignalEngine
from omega_ranker import OmegaRanker, OmegaSignal
from omega_regime_detector import OmegaRegimeDetector
from star_trade_predictor import StarTradePredictor
from report_generator import to_text, star_trade_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def run_scan(symbols: List[str] = None) -> List[OmegaSignal]:
    """Ejecuta el pipeline completo de escaneo."""
    symbols = symbols or SYMBOLS
    de = DataEngine()
    se = SignalEngine()
    ranker = OmegaRanker()

    signals = []
    data_dict = {}

    for sym in symbols:
        try:
            d5 = de.fetch_ohlcv(sym, TIMEFRAME_ENTRY, limit=500)
            d15 = de.fetch_ohlcv(sym, TIMEFRAME_CONFIRM, limit=500)
            d1h = de.fetch_ohlcv(sym, TIMEFRAME_TREND, limit=500)
            if d5 is None or d5.empty:
                continue
            data_dict[sym] = d5
            per_tf = {'5m': d5, '15m': d15, '1h': d1h}
            sig = se.evaluate(sym, per_tf)
            if sig is not None:
                signals.append(se.to_dict(sig))
        except Exception as e:
            logger.warning(f"{sym}: {e}")

    return ranker.rank(signals, data_dict)


def run_full_report():
    """Genera el reporte completo: señales + régimen + star trades."""
    omega_signals = run_scan()
    print(to_text(omega_signals))

    # ---- Régimen ----
    detector = OmegaRegimeDetector()
    de = DataEngine()
    current_regime = 'Chop'
    try:
        btc = de.fetch_ohlcv('BTC/USDT', '1h', limit=500)
        if btc is not None and not btc.empty:
            report = detector.generate_regime_report({'1h': btc})
            current_regime = report.get('current_regime', 'Chop')
            print("\n" + "=" * 70)
            print("  🌊 OMEGA REGIME MONITOR")
            print("=" * 70)
            for k, v in report.items():
                print(f"  {k}: {v}")
            print()
    except Exception as e:
        logger.error(f"Error en régimen: {e}")

    # ---- Star Trade ----
    try:
        predictor = StarTradePredictor()
        pred = predictor.predict(current_regime=current_regime)
        print(star_trade_report(pred))
    except Exception as e:
        logger.error(f"Error en Star Trade: {e}")


if __name__ == '__main__':
    run_full_report()
