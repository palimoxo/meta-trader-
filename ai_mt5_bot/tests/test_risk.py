"""Pruebas de cálculo de volumen."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai_mt5_bot.config import Settings
from ai_mt5_bot.risk import calc_volume


@pytest.fixture
def symbol_info() -> SimpleNamespace:
    return SimpleNamespace(
        point=0.0001,
        trade_tick_value=1.0,
        trade_tick_size=0.0001,
        volume_step=0.01,
        volume_min=0.01,
        volume_max=10.0,
        spread=2,
    )


def test_calc_volume_basic(symbol_info: SimpleNamespace) -> None:
    volume = calc_volume(
        symbol_info,
        balance=1000,
        risk_per_trade=0.01,
        position_size_frac=0.5,
        entry_price=1.1000,
        sl_price=1.0950,
        spread=0.0002,
        settings=Settings(),
    )
    assert volume == pytest.approx(0.10, rel=1e-2)


def test_calc_volume_without_sl_uses_atr(symbol_info: SimpleNamespace) -> None:
    volume = calc_volume(
        symbol_info,
        balance=2000,
        risk_per_trade=0.02,
        position_size_frac=0.25,
        entry_price=1.1200,
        sl_price=None,
        atr=0.0010,
        spread=0.0001,
        settings=Settings(),
    )
    assert volume > 0


def test_calc_volume_blocks_high_spread(symbol_info: SimpleNamespace) -> None:
    volume = calc_volume(
        symbol_info,
        balance=1000,
        risk_per_trade=0.02,
        position_size_frac=0.5,
        entry_price=1.1000,
        sl_price=1.0950,
        spread=0.0010,
        settings=Settings(),
    )
    assert volume == 0.0
