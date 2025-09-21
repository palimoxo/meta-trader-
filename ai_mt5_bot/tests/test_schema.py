"""Tests del esquema de respuesta de la IA."""
from __future__ import annotations

import pytest

from ai_mt5_bot.ai_decision import DecisionResponse


def test_decision_response_valid() -> None:
    payload = {
        "action": "buy",
        "position_size": 0.5,
        "stop_loss": 1.0750,
        "take_profit": 1.0800,
        "reason": "Cruce alcista confirmado",
    }
    decision = DecisionResponse(**payload)
    assert decision.action == "buy"
    assert decision.position_size == pytest.approx(0.5)


def test_decision_response_invalid_action() -> None:
    payload = {
        "action": "invalid",
        "position_size": 0.5,
        "reason": "Texto",
    }
    with pytest.raises(Exception):
        DecisionResponse(**payload)


def test_decision_response_invalid_position_size() -> None:
    payload = {
        "action": "sell",
        "position_size": 1.5,
        "reason": "Muy alto",
    }
    with pytest.raises(Exception):
        DecisionResponse(**payload)
