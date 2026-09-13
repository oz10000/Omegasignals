# data_engine.py
"""Motor de datos con CCXT (Binance/OKX/Bybit) y caché UTC-aware."""
import os
import time
import logging
from typing import Optional, Dict, List
import pandas as pd
import ccxt
from config import EXCHANGE_PRIORITY, CACHE_DIR

logger = logging.getLogger(__name__)
CACHE_TTL = 3600


class DataEngine:
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._connect()

    def _connect(self):
        for ex_id in EXCHANGE_PRIORITY:
            try:
                ex = getattr(ccxt, ex_id)({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'},
                    'timeout': 30000,
                })
                ex.load_markets()
                self.exchanges[ex_id] = ex
                logger.info(f"✅ Conectado a {ex_id}")
                if len(self.exchanges) >= 3:
                    break
            except Exception as e:
                logger.warning(f"⚠️ {ex_id}: {e}")

    def fetch_ohlcv(self, symbol: str, timeframe: str = '5m',
                    limit: int = 500, use_cache: bool = True) -> Optional[pd.DataFrame]:
        cache_file = os.path.join(
            self.cache_dir, f"{symbol.replace('/', '_')}_{timeframe}_{limit}.parquet"
        )

        if use_cache and os.path.exists(cache_file):
            try:
                df = pd.read_parquet(cache_file)
                if not df.empty and self._cache_fresh(df):
                    return df
            except Exception:
                pass

        for ex_id, exchange in self.exchanges.items():
            for attempt in range(3):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    if not ohlcv:
                        continue
                    df = pd.DataFrame(
                        ohlcv,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'],
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                    df = df.set_index('timestamp').sort_index()
                    df = df[~df.index.duplicated(keep='last')]
                    if use_cache:
                        try:
                            df.to_parquet(cache_file)
                        except Exception:
                            pass
                    return df
                except Exception as e:
                    logger.warning(f"Intento {attempt+1}/3 {symbol}@{ex_id}: {e}")
                    time.sleep(1)
        return None

    def _cache_fresh(self, df: pd.DataFrame) -> bool:
        try:
            last = df.index[-1]
            if last.tzinfo is None:
                last = last.tz_localize('UTC')
            return (pd.Timestamp.now(tz='UTC') - last).total_seconds() < CACHE_TTL
        except Exception:
            return False

    def get_symbols(self) -> List[str]:
        from config import SYMBOLS
        return SYMBOLS
