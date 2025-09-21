"""Tests de indicadores técnicos."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ai_mt5_bot.indicators import compute_indicators, recent_returns


def test_compute_indicators_and_returns() -> None:
    rows = 100
    base = np.linspace(1.10, 1.20, rows)
    df = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=rows, freq="min"),
            "open": base + 0.0001,
            "high": base + 0.0005,
            "low": base - 0.0005,
            "close": base,
            "tick_volume": np.random.randint(50, 200, size=rows),
        }
    )

    rsi_last, atr_last = compute_indicators(df)
    assert "rsi" in df.columns
    assert "atr" in df.columns
    assert np.isfinite(rsi_last)
    assert np.isfinite(atr_last)

    returns = recent_returns(df, n=10)
    assert len(returns) == 10
    assert all(isinstance(val, float) for val in returns)
