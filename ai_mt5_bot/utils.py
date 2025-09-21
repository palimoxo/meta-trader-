"""Funciones utilitarias del bot."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def now_ts() -> str:
    """Retorna un timestamp ISO8601 en UTC."""

    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path | str) -> None:
    """Asegura que exista el directorio indicado."""

    Path(path).mkdir(parents=True, exist_ok=True)


def to_points(value: float, *, digits: Optional[int] = None, point: Optional[float] = None) -> float:
    """Convierte un valor de precio a puntos según los parámetros proporcionados."""

    if point and point > 0:
        return value / point
    if digits is not None:
        return value * (10 ** digits)
    raise ValueError("Se debe proporcionar digits o point para convertir a puntos.")


def _serialize(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _append_csv(path: Path, row: Dict[str, Any], fieldnames: Iterable[str]) -> None:
    ensure_dir(path.parent)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({key: _serialize(value) for key, value in row.items()})


def save_decision(log_dir: str, snapshot: Dict[str, Any], decision: Dict[str, Any]) -> None:
    """Guarda el snapshot de mercado y la decisión en CSV."""

    path = Path(log_dir) / "decisions.csv"
    row = {
        "timestamp": now_ts(),
        "symbol": snapshot.get("symbol"),
        "timeframe": snapshot.get("timeframe"),
        "price": snapshot.get("price"),
        "spread": snapshot.get("spread"),
        "rsi": snapshot.get("rsi"),
        "atr": snapshot.get("atr"),
        "decision": decision,
    }
    _append_csv(path, row, fieldnames=row.keys())


def save_order(log_dir: str, payload: Dict[str, Any]) -> None:
    """Registra una ejecución (real o simulada) en CSV."""

    path = Path(log_dir) / "orders.csv"
    row = {"timestamp": now_ts(), **payload}
    _append_csv(path, row, fieldnames=row.keys())


__all__ = ["now_ts", "ensure_dir", "to_points", "save_decision", "save_order"]
