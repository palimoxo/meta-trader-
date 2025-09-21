"""Gestión de riesgo y tamaño de posición."""
from __future__ import annotations

import logging
import math
from typing import Any, Optional

from .config import Settings, get_settings

LOGGER = logging.getLogger(__name__)


def _precision_from_step(step: float) -> int:
    step = abs(step)
    if step <= 0:
        return 2
    text = f"{step:.10f}".rstrip("0")
    if "." not in text:
        return 0
    return max(0, len(text.split(".")[1]))


def _get_attr(symbol_info: Any, names: tuple[str, ...], default: float = 0.0) -> float:
    for name in names:
        value = getattr(symbol_info, name, None)
        if value is not None and float(value) != 0.0:
            return float(value)
    return float(default)


def calc_volume(
    symbol_info: Any,
    balance: float,
    risk_per_trade: float,
    position_size_frac: float,
    entry_price: float,
    sl_price: Optional[float],
    *,
    atr: Optional[float] = None,
    spread: Optional[float] = None,
    settings: Optional[Settings] = None,
) -> float:
    """Calcula el volumen óptimo según el riesgo y las restricciones del símbolo."""

    cfg = settings or get_settings()
    if balance < cfg.min_balance:
        LOGGER.info("Balance por debajo de MIN_BALANCE: %.2f", balance)
        return 0.0
    if risk_per_trade <= 0 or position_size_frac <= 0:
        return 0.0
    if entry_price is None:
        return 0.0

    # Verificación de spread
    point = _get_attr(symbol_info, ("point",), 0.0)
    spread_value = spread
    if spread_value is None:
        spread_float = getattr(symbol_info, "spread_float", None)
        if spread_float:
            spread_value = float(spread_float)
        else:
            spread_points = getattr(symbol_info, "spread", None)
            if spread_points is not None and point:
                spread_value = float(spread_points) * point
    if spread_value is not None and spread_value > cfg.max_spread_points:
        LOGGER.info("Spread %.5f mayor que máximo permitido %.5f", spread_value, cfg.max_spread_points)
        return 0.0

    risk_amount = balance * risk_per_trade * position_size_frac
    if risk_amount <= 0:
        return 0.0

    if sl_price is not None:
        distance_stop = abs(entry_price - sl_price)
    else:
        atr_value = atr if atr is not None else getattr(symbol_info, "atr", None)
        if atr_value is None or float(atr_value) <= 0:
            atr_value = point or 0.0
        distance_stop = cfg.default_sl_atr * float(atr_value)
    if distance_stop <= 0:
        return 0.0

    tick_value = _get_attr(symbol_info, ("trade_tick_value", "tick_value"), 0.0)
    tick_size = _get_attr(symbol_info, ("trade_tick_size", "tick_size", "point"), 0.0)
    value_per_unit = tick_value / tick_size if tick_size else 0.0
    if value_per_unit <= 0:
        value_per_unit = 1.0  # fallback conservador

    raw_volume = risk_amount / (distance_stop * value_per_unit)
    if raw_volume <= 0 or math.isinf(raw_volume) or math.isnan(raw_volume):
        return 0.0

    volume_step = _get_attr(symbol_info, ("volume_step",), 0.01)
    if volume_step <= 0:
        volume_step = 0.01
    min_volume = _get_attr(symbol_info, ("volume_min",), volume_step)
    max_volume = getattr(symbol_info, "volume_max", None)

    steps = math.floor((raw_volume + 1e-12) / volume_step)
    volume = steps * volume_step
    if volume < min_volume:
        return 0.0
    if max_volume is not None:
        volume = min(float(max_volume), volume)

    precision = _precision_from_step(volume_step)
    volume = round(volume, precision)
    return float(volume)


__all__ = ["calc_volume"]
