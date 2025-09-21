"""Herramientas para el bot de trading asistido por IA en MT5."""

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - metadatos opcionales
    __version__ = version("ai-mt5-bot")
except PackageNotFoundError:  # pragma: no cover - durante desarrollo
    __version__ = "0.1.0"

__all__ = ["__version__"]
