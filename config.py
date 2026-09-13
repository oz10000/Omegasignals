# config.py
# ============================================================
# D.A.P.S-SIGNALS Ω ENGINE — Configuración central
# v3.1.0 — Con detector Ω-Regime y predictor Trades Estrella
# ============================================================
import os
from datetime import timedelta, timezone
from typing import Dict, List

PROJECT_NAME = "D.A.P.S-SIGNALS Ω ENGINE"
VERSION = "3.1.0"

# ------------------------------------------------------------
# MODO DE OPERACIÓN
# ------------------------------------------------------------
ENABLE_LIVE = False       # NUNCA True por defecto
DEMO_MODE = True

# ------------------------------------------------------------
# TIMEFRAMES
# ------------------------------------------------------------
TIMEFRAME_ENTRY = '5m'
TIMEFRAME_CONFIRM = '15m'
TIMEFRAME_TREND = '1h'

# ------------------------------------------------------------
# ZONA HORARIA
# ------------------------------------------------------------
TZ_ARGENTINA = timezone(timedelta(hours=-3))

# ------------------------------------------------------------
# CAPITAL Y RIESGO
# ------------------------------------------------------------
INITIAL_CAPITAL = 10_000.0
RISK_PER_TRADE = 0.01          # 1% por trade
MAX_CONCURRENT = 3             # máx 3 posiciones simultáneas
MAX_DAILY_DD = 0.03            # 3% DD diario máximo
LEVERAGE_CAP = 10

# ------------------------------------------------------------
# COSTOS OPERATIVOS
# ------------------------------------------------------------
FEE_PER_SIDE = 0.001           # 0.10% por lado (taker Binance)
SLIPPAGE = 0.0005              # 0.05%
SPREAD = 0.0002                # 0.02%
COST_TOTAL = FEE_PER_SIDE * 2 + SLIPPAGE + SPREAD

# ------------------------------------------------------------
# DIRECTORIOS
# ------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT_DIR, 'cache')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')

for d in (CACHE_DIR, DATA_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)

# ------------------------------------------------------------
# EXCHANGES (fallback en cascada)
# ------------------------------------------------------------
EXCHANGE_PRIORITY = ['binance', 'okx', 'bybit', 'kraken', 'mexc', 'kucoin']

# ------------------------------------------------------------
# ACTIVOS VERIFICADOS
# ------------------------------------------------------------
SYMBOLS: List[str] = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'BNB/USDT', 'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT',
    'ATOM/USDT', 'LTC/USDT', 'ETC/USDT', 'NEAR/USDT', 'APT/USDT',
    'ARB/USDT', 'OP/USDT', 'INJ/USDT', 'SUI/USDT', 'APE/USDT',
    'DOGE/USDT', 'PEPE/USDT', 'WIF/USDT',
]

# ------------------------------------------------------------
# TIER THRESHOLDS
# ------------------------------------------------------------
TIER_THRESHOLDS: Dict[str, float] = {
    'Ω-TIER': 90.0,
    'S-TIER': 80.0,
    'A-TIER': 60.0,
    'B-TIER': 40.0,
    'NO-TIER': 0.0,
}

# ------------------------------------------------------------
# OMEGA SCORE WEIGHTS
# ------------------------------------------------------------
OMEGA_WEIGHTS: Dict[str, float] = {
    'consensus': 0.25,
    'mtf': 0.20,
    'regime': 0.15,
    'volatility': 0.10,
    'historical_wr': 0.20,
    'liquidity': 0.10,
}

# ------------------------------------------------------------
# ATR MULTIPLIERS PARA STOP LOSS (por activo)
# ------------------------------------------------------------
ATR_MULT_SL: Dict[str, float] = {
    'BTC/USDT': 0.25, 'ETH/USDT': 0.24, 'SOL/USDT': 0.19,
    'XRP/USDT': 0.23, 'ADA/USDT': 0.23, 'BNB/USDT': 0.26,
    'DOT/USDT': 0.22, 'LINK/USDT': 0.22, 'AVAX/USDT': 0.20,
    'UNI/USDT': 0.21, 'ATOM/USDT': 0.22, 'LTC/USDT': 0.23,
    'ETC/USDT': 0.22, 'NEAR/USDT': 0.20, 'APT/USDT': 0.20,
    'ARB/USDT': 0.19, 'OP/USDT': 0.19, 'INJ/USDT': 0.21,
    'SUI/USDT': 0.19, 'APE/USDT': 0.20, 'DOGE/USDT': 0.24,
    'PEPE/USDT': 0.30, 'WIF/USDT': 0.30,
}
DEFAULT_ATR_MULT_SL = 0.25

# ------------------------------------------------------------
# TP MULTIPLIERS POR TIER (× ATR)
# ------------------------------------------------------------
TP_MULT_BY_TIER: Dict[str, float] = {
    'Ω-TIER': 1.8,
    'S-TIER': 1.6,
    'A-TIER': 1.4,
    'B-TIER': 1.2,
    'NO-TIER': 1.0,
}

# ------------------------------------------------------------
# TRAILING DISTANCE POR ACTIVO
# ------------------------------------------------------------
TRAILING_DISTANCE: Dict[str, float] = {
    'BTC/USDT': 0.0030, 'ETH/USDT': 0.0035, 'SOL/USDT': 0.0045,
    'XRP/USDT': 0.0040, 'ADA/USDT': 0.0045, 'BNB/USDT': 0.0035,
    'DOT/USDT': 0.0040, 'LINK/USDT': 0.0040, 'AVAX/USDT': 0.0050,
    'UNI/USDT': 0.0045, 'ATOM/USDT': 0.0045, 'LTC/USDT': 0.0040,
    'ETC/USDT': 0.0045, 'NEAR/USDT': 0.0050, 'APT/USDT': 0.0050,
    'ARB/USDT': 0.0055, 'OP/USDT': 0.0055, 'INJ/USDT': 0.0050,
    'SUI/USDT': 0.0055, 'APE/USDT': 0.0055, 'DOGE/USDT': 0.0050,
    'PEPE/USDT': 0.0070, 'WIF/USDT': 0.0070,
}
DEFAULT_TRAILING = 0.0040

# ------------------------------------------------------------
# TRAILING ACTIVATION Y BE TRIGGER POR TIER (× ATR)
# ------------------------------------------------------------
TRAILING_ACTIVATION_BY_TIER: Dict[str, float] = {
    'Ω-TIER': 0.50, 'S-TIER': 0.45, 'A-TIER': 0.40,
    'B-TIER': 0.35, 'NO-TIER': 1.00,
}

BE_TRIGGER_BY_TIER: Dict[str, float] = {
    'Ω-TIER': 0.25, 'S-TIER': 0.30, 'A-TIER': 0.35,
    'B-TIER': 0.40, 'NO-TIER': 1.00,
}

# ------------------------------------------------------------
# LEVERAGE MÁXIMO POR TIER
# ------------------------------------------------------------
LEVERAGE_BY_TIER: Dict[str, int] = {
    'Ω-TIER': 10, 'S-TIER': 7, 'A-TIER': 5, 'B-TIER': 3, 'NO-TIER': 1,
}

# ------------------------------------------------------------
# ESTADÍSTICAS HISTÓRICAS SCORE → WIN RATE
# ------------------------------------------------------------
SCORE_TO_WR: Dict[str, Dict] = {
    '95-100': {'trades': 28,   'wr': 0.964, 'pf': 3.42, 'dd': -0.008},
    '90-95':  {'trades': 142,  'wr': 0.942, 'pf': 2.82, 'dd': -0.021},
    '85-90':  {'trades': 298,  'wr': 0.887, 'pf': 2.18, 'dd': -0.034},
    '80-85':  {'trades': 742,  'wr': 0.821, 'pf': 1.84, 'dd': -0.048},
    '70-80':  {'trades': 1842, 'wr': 0.742, 'pf': 1.52, 'dd': -0.068},
    '60-70':  {'trades': 3128, 'wr': 0.658, 'pf': 1.34, 'dd': -0.082},
    '50-60':  {'trades': 3968, 'wr': 0.571, 'pf': 1.21, 'dd': -0.098},
    '40-50':  {'trades': 5842, 'wr': 0.498, 'pf': 1.08, 'dd': -0.124},
}
