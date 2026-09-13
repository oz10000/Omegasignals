# indicator_engine.py
"""Indicadores con fórmulas Wilder correctas (ADX, ATR, KER, EMA)."""
import pandas as pd
import numpy as np


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close'].shift(1)
    return pd.concat([
        high - low,
        (high - close).abs(),
        (low - close).abs(),
    ], axis=1).max(axis=1)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR con suavizado Wilder (RMA)."""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)
    tr = _true_range(df)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    return atr.fillna(0).replace([np.inf, -np.inf], 0)


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX Wilder correcto (DM condicional)."""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    high, low = df['high'], df['low']
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    alpha = 1.0 / period
    tr = _true_range(df)
    atr_s = tr.ewm(alpha=alpha, adjust=False).mean().replace(0, np.nan)

    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s

    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = (plus_di - minus_di).abs() / di_sum * 100
    dx = dx.fillna(0).replace([np.inf, -np.inf], 0)
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    return adx.fillna(0).replace([np.inf, -np.inf], 0)


def compute_ker(df: pd.DataFrame, period: int = 10) -> pd.Series:
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)
    close = df['close']
    change = abs(close.diff(period))
    volatility = close.diff().abs().rolling(period).sum()
    ker = change / (volatility + 1e-9)
    return ker.fillna(0).replace([np.inf, -np.inf], 0)


def compute_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    if df.empty:
        return pd.Series(0.0, index=df.index)
    return df['close'].ewm(span=period, adjust=False).mean()


def compute_regime(df: pd.DataFrame, adx_val: float, atr_pct: float) -> str:
    if df.empty or len(df) < 30:
        return 'Chop'
    if adx_val > 40 and atr_pct > 0.02:
        return 'Expansión'
    if adx_val > 30:
        return 'Tendencia Fuerte'
    if adx_val > 20:
        return 'Tendencia Débil'
    return 'Chop'
