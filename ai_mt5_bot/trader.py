"""Script principal para operar con MetaTrader 5 y OpenAI."""
from __future__ import annotations

import argparse
import math
import sys
from typing import Any, Dict

from .ai_decision import DecisionResponse, ask_ai
from .config import Settings, get_settings
from . import indicators, mt5_handler, risk
from .logger import get_logger, log_decision, log_error, log_order
from .utils import save_decision, save_order

LOGGER = get_logger()


def _build_settings(args: argparse.Namespace) -> Settings:
    base = get_settings()
    data = base.to_dict()
    if args.symbol:
        data["symbol"] = args.symbol.upper()
    if args.timeframe:
        data["timeframe"] = args.timeframe.upper()
    if args.live:
        data["live_trading"] = True
    if args.risk is not None:
        data["risk_per_trade"] = args.risk
    if args.bars is not None:
        data["history_bars"] = args.bars
    if args.model:
        data["openai_model"] = args.model
    return Settings(**data)


def _fallback_level(price: float, atr: float, multiplier: float, direction: int) -> float:
    atr = atr if atr and atr > 0 else 0.0
    if atr <= 0:
        # Fallback aproximado de 10 pips si ATR no está disponible
        atr = 0.001 if price < 10 else price * 0.001
    if direction > 0:
        return price + multiplier * atr
    return price - multiplier * atr


def _prepare_snapshot(
    settings: Settings,
    account: Dict[str, Any],
    symbol_info: Any,
    rates,
    tick: Dict[str, float],
    rsi: float,
    atr: float,
) -> Dict[str, Any]:
    price_mid = (tick["bid"] + tick["ask"]) / 2
    spread = tick["ask"] - tick["bid"]
    snapshot = {
        "symbol": settings.symbol,
        "timeframe": settings.timeframe,
        "price": price_mid,
        "spread": spread,
        "rsi": rsi,
        "atr": atr,
        "last_close": float(rates["close"].iloc[-1]),
        "recent_returns": indicators.recent_returns(rates, n=20),
        "balance": account["balance"],
        "free_margin": account["margin_free"],
        "leverage": account["leverage"],
    }
    return snapshot


def run_bot(settings: Settings) -> None:
    LOGGER.info("Iniciando bot para %s en %s (live=%s)", settings.symbol, settings.timeframe, settings.live_trading)
    mt5_handler.initialize(settings)
    try:
        account = mt5_handler.get_account_info()
        symbol_info = mt5_handler.get_symbol_info(settings.symbol)
        rates = mt5_handler.get_rates(settings.symbol, settings.timeframe, settings.history_bars)
        rsi, atr = indicators.compute_indicators(rates)
        tick = mt5_handler.get_tick(settings.symbol)
        snapshot = _prepare_snapshot(settings, account, symbol_info, rates, tick, rsi, atr)
        if snapshot["spread"] > settings.max_spread_points:
            reason = f"Spread {snapshot['spread']:.5f} mayor que límite {settings.max_spread_points:.5f}."
            LOGGER.warning(reason)
            decision = DecisionResponse(action="hold", position_size=0.0, stop_loss=None, take_profit=None, reason=reason)
            log_decision(snapshot, decision.to_dict())
            save_decision(settings.log_dir, snapshot, decision.to_dict())
            print("Spread demasiado amplio, no se opera.")
            return

        decision = ask_ai(snapshot, settings=settings)
        log_decision(snapshot, decision.to_dict())
        save_decision(settings.log_dir, snapshot, decision.to_dict())

        if decision.action == "hold":
            LOGGER.info("La IA sugiere no operar: %s", decision.reason)
            print(f"IA sugiere HOLD: {decision.reason}")
            return

        direction = 1 if decision.action == "buy" else -1
        entry_price = tick["ask"] if direction > 0 else tick["bid"]
        atr_value = atr if atr and math.isfinite(atr) else 0.0

        sl = decision.stop_loss
        tp = decision.take_profit
        if sl is None:
            sl = _fallback_level(entry_price, atr_value, settings.default_sl_atr, -direction)
        if tp is None:
            tp = _fallback_level(entry_price, atr_value, settings.default_tp_atr, direction)

        volume = risk.calc_volume(
            symbol_info,
            balance=account["balance"],
            risk_per_trade=settings.risk_per_trade,
            position_size_frac=float(decision.position_size),
            entry_price=entry_price,
            sl_price=sl,
            atr=atr_value,
            spread=snapshot["spread"],
            settings=settings,
        )
        if volume <= 0:
            msg = "Volumen calculado es 0; operación cancelada."
            LOGGER.info(msg)
            print(msg)
            return

        order_payload = {
            "symbol": settings.symbol,
            "action": decision.action,
            "volume": volume,
            "entry_price": entry_price,
            "stop_loss": sl,
            "take_profit": tp,
            "mode": "live" if settings.live_trading else "paper",
            "reason": decision.reason,
        }

        if not settings.live_trading:
            LOGGER.info("Modo paper trading: %s", order_payload)
            print("Paper trading ->", order_payload)
            save_order(settings.log_dir, {**order_payload, "result": "simulado"})
            return

        result = mt5_handler.send_order(settings.symbol, decision.action, volume, sl, tp)
        log_order(result, order_payload)
        save_order(settings.log_dir, {**order_payload, **result})
        print("Orden enviada:", result)
    finally:
        mt5_handler.shutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bot de trading MT5 asistido por IA")
    parser.add_argument("--symbol", type=str, help="Símbolo a operar", default=None)
    parser.add_argument("--timeframe", type=str, help="Timeframe (M1,M5,M15,H1,H4,D1)", default=None)
    parser.add_argument("--live", action="store_true", help="Activa trading en vivo (por defecto paper)")
    parser.add_argument("--risk", type=float, help="Porcentaje de balance a arriesgar por trade (0-1)", default=None)
    parser.add_argument("--bars", type=int, help="Barras históricas a descargar", default=None)
    parser.add_argument("--model", type=str, help="Modelo de OpenAI a utilizar", default=None)
    args = parser.parse_args(argv)

    try:
        settings = _build_settings(args)
        run_bot(settings)
        return 0
    except Exception as exc:  # pragma: no cover - protección runtime
        log_error(exc)
        print(f"Error en la ejecución: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
