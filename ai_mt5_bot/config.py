"""Configuración central del bot de trading."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from pydantic import BaseModel, Field

try:  # Compatibilidad con Pydantic v2 y v1
    from pydantic import ConfigDict, field_validator as _field_validator

    def _validator(*fields, **kwargs):  # type: ignore[misc]
        return _field_validator(*fields, **kwargs)

    MODEL_CONFIG = ConfigDict(populate_by_name=True, str_strip_whitespace=True, validate_assignment=True)
except ImportError:  # pragma: no cover - fallback Pydantic v1
    from pydantic import validator as _field_validator  # type: ignore

    def _validator(*fields, **kwargs):  # type: ignore[misc]
        kwargs.setdefault("allow_reuse", True)
        return _field_validator(*fields, **kwargs)

    MODEL_CONFIG = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

_ALLOWED_TIMEFRAMES = {"M1", "M5", "M15", "H1", "H4", "D1"}


class Settings(BaseModel):
    """Valores de configuración obtenidos desde variables de entorno."""

    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-5-codex", alias="OPENAI_MODEL")
    symbol: str = Field("EURUSD", alias="SYMBOL")
    timeframe: str = Field("M5", alias="TIMEFRAME")
    history_bars: int = Field(1000, alias="HISTORY_BARS")
    risk_per_trade: float = Field(0.01, alias="RISK_PER_TRADE")
    default_sl_atr: float = Field(2.0, alias="DEFAULT_SL_ATR")
    default_tp_atr: float = Field(3.0, alias="DEFAULT_TP_ATR")
    live_trading: bool = Field(False, alias="LIVE_TRADING")
    max_spread_points: float = Field(0.00020, alias="MAX_SPREAD_POINTS")
    log_dir: str = Field("data", alias="LOG_DIR")
    decision_timeout_sec: int = Field(30, alias="DECISION_TIMEOUT_SEC")
    max_retries: int = Field(3, alias="MAX_RETRIES")
    min_balance: float = Field(0.0, alias="MIN_BALANCE")

    if MODEL_CONFIG is not None:  # pragma: no branch
        model_config = MODEL_CONFIG
    else:  # pragma: no cover - soporte Pydantic v1
        class Config:
            allow_population_by_field_name = True
            validate_assignment = True
            anystr_strip_whitespace = True

    @_validator("timeframe")
    def _validate_timeframe(cls, value: str) -> str:
        value = value.upper()
        if value not in _ALLOWED_TIMEFRAMES:
            raise ValueError(f"TIMEFRAME inválido: {value}. Debe ser uno de {_ALLOWED_TIMEFRAMES}.")
        return value

    @_validator("history_bars")
    def _validate_bars(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("HISTORY_BARS debe ser mayor que 0.")
        return value

    @_validator("risk_per_trade")
    def _validate_risk(cls, value: float) -> float:
        if value <= 0 or value > 1:
            raise ValueError("RISK_PER_TRADE debe estar en (0, 1].")
        return value

    @_validator("max_spread_points")
    def _validate_spread(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("MAX_SPREAD_POINTS debe ser positivo.")
        return value

    @_validator("decision_timeout_sec")
    def _validate_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("DECISION_TIMEOUT_SEC debe ser positivo.")
        return value

    @_validator("max_retries")
    def _validate_retries(cls, value: int) -> int:
        if value < 1:
            raise ValueError("MAX_RETRIES debe ser al menos 1.")
        return value

    @classmethod
    def from_env(cls) -> "Settings":
        """Construye la configuración leyendo las variables de entorno cargadas."""

        raw: Dict[str, Any] = {}
        fields = getattr(cls, "model_fields", None) or getattr(cls, "__fields__")  # compatibilidad pydantic v1/v2
        for name, field in fields.items():
            alias = getattr(field, "alias", None) or name
            value = os.getenv(alias)
            if value is not None:
                raw[name] = value
        return cls(**raw)

    def to_dict(self) -> Dict[str, Any]:
        """Devuelve la configuración como diccionario estándar."""

        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


@lru_cache()
def get_settings() -> Settings:
    """Devuelve la configuración cacheada."""

    return Settings.from_env()


__all__ = ["Settings", "get_settings"]
