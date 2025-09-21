"""Módulo de interacción con la API de OpenAI para decidir trades."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pydantic import BaseModel, Field, ValidationError, confloat

try:  # Compatibilidad Pydantic v2/v1
    from pydantic import field_validator as _field_validator

    def _validator(*fields, **kwargs):  # type: ignore[misc]
        return _field_validator(*fields, **kwargs)
except ImportError:  # pragma: no cover - fallback Pydantic v1
    from pydantic import validator as _field_validator  # type: ignore

    def _validator(*fields, **kwargs):  # type: ignore[misc]
        kwargs.setdefault("allow_reuse", True)
        return _field_validator(*fields, **kwargs)

from .config import Settings, get_settings

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - permite ejecutar tests sin dependencia real
    from openai import APIError, OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore

    class APIError(Exception):  # type: ignore
        """Excepción genérica cuando openai no está instalado."""

SYSTEM_PROMPT = (
    "Eres un asesor cuantitativo. Devuelve SOLO JSON válido conforme al esquema. "
    "Evita overtrading; si la señal es débil, 'hold'. Considera spread y volatilidad."
)


class DecisionResponse(BaseModel):
    """Esquema estricto que debe cumplir la IA."""

    action: str = Field(..., pattern=r"^(buy|sell|hold)$")
    position_size: confloat(ge=0.0, le=1.0) = Field(...)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = Field(..., min_length=1, max_length=280)

    @_validator("stop_loss", "take_profit")
    def _validate_levels(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value <= 0:
            raise ValueError("SL/TP deben ser positivos en precio absoluto.")
        return value

    def to_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


def _build_json_schema() -> Dict[str, Any]:
    """Obtiene el schema en formato JSON compatible con OpenAI."""

    if hasattr(DecisionResponse, "model_json_schema"):
        schema = DecisionResponse.model_json_schema()
    else:  # pragma: no cover - compatibilidad pydantic v1
        schema = DecisionResponse.schema()
    return {
        "name": "trading_decision",
        "schema": schema,
        "strict": True,
    }


def _get_client(settings: Settings) -> Optional[OpenAI]:
    if OpenAI is None:
        return None
    if not settings.openai_api_key:
        return None
    try:
        return OpenAI(api_key=settings.openai_api_key)
    except TypeError:
        # Versiones antiguas del SDK usan api_key global
        client = OpenAI()
        client.api_key = settings.openai_api_key  # type: ignore[attr-defined]
        return client


def _default_hold(reason: str) -> DecisionResponse:
    return DecisionResponse(action="hold", position_size=0.0, stop_loss=None, take_profit=None, reason=reason[:280])


def ask_ai(snapshot: Dict[str, Any], settings: Optional[Settings] = None) -> DecisionResponse:
    """Solicita una recomendación a OpenAI, validando estrictamente la respuesta."""

    cfg = settings or get_settings()
    client = _get_client(cfg)
    if client is None:
        return _default_hold("API de OpenAI no configurada")

    schema_payload = {"type": "json_schema", "json_schema": _build_json_schema()}

    @retry(
        reraise=True,
        stop=stop_after_attempt(cfg.max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=cfg.decision_timeout_sec),
        retry=retry_if_exception_type(APIError),
    )
    def _call_openai() -> str:
        response = client.chat.completions.create(
            model=cfg.openai_model,
            temperature=0,
            timeout=cfg.decision_timeout_sec,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(snapshot, ensure_ascii=False)},
            ],
            response_format=schema_payload,
        )
        choice = response.choices[0]
        content = getattr(choice.message, "content", None)
        if not content:
            raise APIError("La respuesta de OpenAI no contiene contenido JSON")
        return content

    try:
        raw_content = _call_openai()
    except Exception as exc:  # pragma: no cover - dependiente de API externa
        LOGGER.error("Fallo al consultar OpenAI: %s", exc)
        return _default_hold("Error consultando modelo IA")

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        LOGGER.warning("JSON inválido recibido de OpenAI: %s", exc)
        return _default_hold("Respuesta JSON inválida")

    try:
        decision = DecisionResponse(**parsed)
    except ValidationError as exc:
        LOGGER.warning("Respuesta no válida según esquema: %s", exc)
        return _default_hold("Respuesta fuera de esquema")
    return decision


__all__ = ["DecisionResponse", "ask_ai", "SYSTEM_PROMPT"]
