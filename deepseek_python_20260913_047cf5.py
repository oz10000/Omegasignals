# main.py
"""Orquestador principal — ejecuta el pipeline completo + Star Trade Monitor."""
import logging
from typing import List

from config import SYMBOLS, TIMEFRAME_ENTRY, TIMEFRAME_CONFIRM, TIMEFRAME_TREND
from data_engine import DataEngine
from signal_engine import SignalEngine
from omega_ranker import OmegaRanker, OmegaSignal
from omega_regime_detector import OmegaRegimeDetector
from star_trade_predictor import StarTradePredictor
from report_generator import to_text, star_trade_report

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_scan(symbols: List[str] = None) -> List[OmegaSignal]:
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
    omega_signals = run_scan()
    print(to_text(omega_signals))

    # Régimen
    detector = OmegaRegimeDetector()
    de = DataEngine()
    btc = de.fetch_ohlcv('BTC/USDT', '1h', limit=500)
    if btc is not None:
        report = detector.generate_regime_report({'1h': btc})
        print("\n" + "=" * 70)
        print("  🌊 OMEGA REGIME MONITOR")
        print("=" * 70)
        for k, v in report.items():
            print(f"  {k}: {v}")
        print()

    # Star Trade
    predictor = StarTradePredictor()
    pred = predictor.predict(
        current_regime=report.get('current_regime', 'Chop') if btc is not None else 'Chop',
    )
    print(star_trade_report(pred))


if __name__ == '__main__':
    run_full_report()