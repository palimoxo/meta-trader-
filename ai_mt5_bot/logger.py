"""Configuración básica de logging para el bot."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from .config import get_settings
from .utils import ensure_dir

LOGGER_NAME = "ai_mt5_bot"
LOGGER = logging.getLogger(LOGGER_NAME)

if not LOGGER.handlers:
    LOGGER.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(stream_handler)

    log_dir = Path(get_settings().log_dir)
    ensure_dir(log_dir)
    file_handler = logging.FileHandler(log_dir / "trades.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)


def get_logger() -> logging.Logger:
    """Devuelve la instancia de logger global."""

    return LOGGER


def log_decision(snapshot: Dict[str, Any], decision: Dict[str, Any]) -> None:
    """Registra la decisión de la IA junto al snapshot del mercado."""

    LOGGER.info("Decisión IA: %s | Snapshot: %s", decision, snapshot)


def log_order(result: Dict[str, Any], extra: Dict[str, Any]) -> None:
    """Registra el resultado del envío de una orden."""

    LOGGER.info("Resultado orden: %s | Datos adicionales: %s", result, extra)


def log_error(error: Any) -> None:
    """Registra un error capturado."""

    LOGGER.error("Error en ejecución: %s", error)


__all__ = ["get_logger", "log_decision", "log_order", "log_error", "LOGGER"]
