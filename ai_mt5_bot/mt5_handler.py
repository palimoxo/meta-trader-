"""Abstracciones sobre la API de MetaTrader 5."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings, get_settings

try:  # pragma: no cover - la librería solo está disponible en entornos MT5
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - permite ejecutar los tests sin MT5
    mt5 = None  # type: ignore

LOGGER = logging.getLogger(__name__)

_TIMEFRAME_MAP = {
    "M1": getattr(mt5, "TIMEFRAME_M1", 1) if mt5 else 1,
    "M5": getattr(mt5, "TIMEFRAME_M5", 5) if mt5 else 5,
    "M15": getattr(mt5, "TIMEFRAME_M15", 15) if mt5 else 15,
    "H1": getattr(mt5, "TIMEFRAME_H1", 60) if mt5 else 60,
    "H4": getattr(mt5, "TIMEFRAME_H4", 240) if mt5 else 240,
    "D1": getattr(mt5, "TIMEFRAME_D1", 1440) if mt5 else 1440,
}


def _ensure_mt5_available() -> None:
    if mt5 is None:
        raise RuntimeError(
            "La librería MetaTrader5 no está disponible. Instale MetaTrader 5 Python API en este entorno."
        )


def initialize(settings: Optional[Settings] = None) -> None:
    """Inicializa MetaTrader5 con reintentos exponenciales."""

    cfg = settings or get_settings()
    _ensure_mt5_available()

    @retry(reraise=True, stop=stop_after_attempt(cfg.max_retries), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _do_initialize() -> None:
        if mt5.initialize():
            return
        code, message = mt5.last_error()
        LOGGER.error("Error al inicializar MT5 (%s): %s", code, message)
        raise RuntimeError(f"No se pudo inicializar MetaTrader5: {message}")

    _do_initialize()


def reconnect(settings: Optional[Settings] = None) -> None:
    """Fuerza un reinicio de la conexión."""

    shutdown()
    initialize(settings=settings)


def shutdown() -> None:
    """Cierra la conexión con MetaTrader5."""

    if mt5 is None:
        return
    mt5.shutdown()


def ensure_symbol(symbol: str) -> None:
    """Asegura que el símbolo esté visible en el Market Watch."""

    _ensure_mt5_available()
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"No fue posible seleccionar el símbolo {symbol} en MT5.")


def timeframe_to_mt5(timeframe: str) -> int:
    """Mapea la cadena de timeframe a la constante de MT5."""

    tf = timeframe.upper()
    if tf not in _TIMEFRAME_MAP:
        raise ValueError(f"Timeframe no soportado: {timeframe}")
    return _TIMEFRAME_MAP[tf]


def get_account_info() -> Dict[str, Any]:
    """Obtiene información resumida de la cuenta actual."""

    _ensure_mt5_available()
    info = mt5.account_info()
    if info is None:
        code, message = mt5.last_error()
        raise RuntimeError(f"No se pudo obtener account_info: {code} {message}")
    return {
        "balance": float(info.balance),
        "equity": float(info.equity),
        "margin_free": float(info.margin_free),
        "leverage": float(info.leverage),
        "currency": info.currency,
    }


def get_symbol_info(symbol: str) -> Any:
    """Devuelve el objeto de información del símbolo."""

    _ensure_mt5_available()
    ensure_symbol(symbol)
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"No se pudo obtener información del símbolo {symbol}.")
    return info


def get_rates(symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
    """Obtiene barras históricas como DataFrame de pandas."""

    _ensure_mt5_available()
    ensure_symbol(symbol)
    if bars <= 0:
        raise ValueError("El número de barras debe ser positivo.")
    mt5_timeframe = timeframe_to_mt5(timeframe)
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        code, message = mt5.last_error()
        raise RuntimeError(
            f"copy_rates_from_pos devolvió sin datos para {symbol} {timeframe} ({code} {message})."
        )
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df[["time", "open", "high", "low", "close", "tick_volume"]]


def get_tick(symbol: str) -> Dict[str, float]:
    """Obtiene el último tick del símbolo."""

    _ensure_mt5_available()
    ensure_symbol(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        code, message = mt5.last_error()
        raise RuntimeError(f"No se pudo obtener symbol_info_tick: {code} {message}")
    return {
        "bid": float(tick.bid),
        "ask": float(tick.ask),
        "last": float(getattr(tick, "last", float("nan"))),
    }


def send_order(symbol: str, action: str, volume: float, sl: Optional[float], tp: Optional[float]) -> Dict[str, Any]:
    """Envía una orden a mercado BUY/SELL con SL/TP opcionales."""

    _ensure_mt5_available()
    ensure_symbol(symbol)
    action_lower = action.lower()
    if action_lower not in {"buy", "sell"}:
        raise ValueError(f"Acción inválida: {action}.")
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        code, message = mt5.last_error()
        raise RuntimeError(f"No se pudo obtener el tick para enviar la orden: {code} {message}")
    order_type = mt5.ORDER_TYPE_BUY if action_lower == "buy" else mt5.ORDER_TYPE_SELL
    price = float(tick.ask if action_lower == "buy" else tick.bid)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": price,
        "deviation": 20,
        "type_filling": getattr(mt5, "ORDER_FILLING_IOC", 2),
        "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
        "comment": "ai-mt5-bot",
    }
    if sl is not None:
        request["sl"] = float(sl)
    if tp is not None:
        request["tp"] = float(tp)
    result = mt5.order_send(request)
    if result is None:
        code, message = mt5.last_error()
        raise RuntimeError(f"order_send devolvió None: {code} {message}")
    return {
        "retcode": getattr(result, "retcode", None),
        "comment": getattr(result, "comment", ""),
        "order": getattr(result, "order", None),
        "price": getattr(result, "price", price),
        "volume": getattr(result, "volume", volume),
    }


__all__ = [
    "initialize",
    "reconnect",
    "shutdown",
    "ensure_symbol",
    "timeframe_to_mt5",
    "get_account_info",
    "get_symbol_info",
    "get_rates",
    "get_tick",
    "send_order",
]
