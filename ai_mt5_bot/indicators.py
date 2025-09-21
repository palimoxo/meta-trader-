"""Cálculo de indicadores técnicos auxiliares."""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange


def compute_indicators(df: pd.DataFrame) -> Tuple[float, float]:
    """Añade RSI y ATR al DataFrame y devuelve sus últimos valores."""

    if df.empty:
        raise ValueError("El DataFrame de precios está vacío.")
    if not {"high", "low", "close"}.issubset(df.columns):
        raise ValueError("El DataFrame debe contener las columnas high, low y close.")

    rsi_indicator = RSIIndicator(close=df["close"], window=14)
    df["rsi"] = rsi_indicator.rsi()

    atr_indicator = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14)
    df["atr"] = atr_indicator.average_true_range()

    rsi_last = float(df["rsi"].iloc[-1])
    atr_last = float(df["atr"].iloc[-1])
    return rsi_last, atr_last


def recent_returns(df: pd.DataFrame, n: int = 50) -> List[float]:
    """Calcula los últimos rendimientos logarítmicos."""

    if "close" not in df.columns:
        raise ValueError("Se requiere la columna close para calcular retornos.")
    closes = df["close"].astype(float)
    log_returns = np.log(closes / closes.shift(1)).dropna()
    tail = log_returns.tail(n)
    return tail.astype(float).tolist()


__all__ = ["compute_indicators", "recent_returns"]
