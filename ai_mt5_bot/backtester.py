"""Backtest educativo basado en RSI/ATR."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .config import get_settings
from .indicators import compute_indicators
from .utils import ensure_dir


def _load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected = {"time", "open", "high", "low", "close"}
    if not expected.issubset(df.columns):
        raise ValueError(f"El CSV debe contener las columnas: {expected}")
    df["time"] = pd.to_datetime(df["time"])
    return df


def _simulate_trades(df: pd.DataFrame, risk_per_trade: float, default_sl: float, default_tp: float) -> Tuple[List[float], List[float]]:
    equity = 1.0
    highs: List[float] = [equity]
    lows: List[float] = [equity]
    trade_returns: List[float] = []

    position = None
    entry_idx = None
    direction = 0
    entry_price = 0.0
    sl = 0.0
    tp = 0.0

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        price = float(df.iloc[i]["close"])
        atr = float(prev.get("atr", 0.0))
        rsi = float(prev.get("rsi", 50.0))

        if position is None:
            if rsi < 30 and atr > 0:
                position = "long"
                direction = 1
                entry_price = price
                sl = entry_price - default_sl * atr
                tp = entry_price + default_tp * atr
                entry_idx = i
            elif rsi > 70 and atr > 0:
                position = "short"
                direction = -1
                entry_price = price
                sl = entry_price + default_sl * atr
                tp = entry_price - default_tp * atr
                entry_idx = i
        else:
            hit = None
            if direction == 1 and price <= sl:
                hit = sl
            elif direction == 1 and price >= tp:
                hit = tp
            elif direction == -1 and price >= sl:
                hit = sl
            elif direction == -1 and price <= tp:
                hit = tp

            if hit is not None or i == len(df) - 1:
                exit_price = hit if hit is not None else price
                trade_return = direction * (exit_price - entry_price) / entry_price
                risk_adjusted = trade_return * risk_per_trade
                equity *= 1 + risk_adjusted
                trade_returns.append(risk_adjusted)
                highs.append(max(highs[-1], equity))
                lows.append(min(lows[-1], equity))
                position = None
                direction = 0
                entry_idx = None

    return trade_returns, lows


def _metrics(trade_returns: List[float], equity_curve: List[float]) -> Dict[str, float]:
    if not trade_returns:
        return {"winrate": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "retorno": 0.0}

    profits = [r for r in trade_returns if r > 0]
    losses = [abs(r) for r in trade_returns if r < 0]
    winrate = len(profits) / len(trade_returns)
    profit_factor = (np.sum(profits) / np.sum(losses)) if losses else float("inf")
    max_drawdown = 0.0
    peak = equity_curve[0]
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
    retorno = np.prod([1 + r for r in trade_returns]) - 1
    return {
        "winrate": float(winrate),
        "profit_factor": float(profit_factor),
        "max_drawdown": float(max_drawdown),
        "retorno": float(retorno),
    }


def run_backtest(data_path: Path) -> Dict[str, float]:
    settings = get_settings()
    df = _load_data(data_path)
    compute_indicators(df)
    trades, equity_curve = _simulate_trades(
        df,
        risk_per_trade=settings.risk_per_trade,
        default_sl=settings.default_sl_atr,
        default_tp=settings.default_tp_atr,
    )
    return _metrics(trades, equity_curve)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest educativo con RSI/ATR")
    parser.add_argument(
        "--file",
        type=str,
        help="Ruta al CSV de precios (time,open,high,low,close). Si no se especifica se usará el primero en data/",
        default=None,
    )
    args = parser.parse_args()

    settings = get_settings()
    data_dir = Path(settings.log_dir)
    if args.file:
        csv_path = Path(args.file)
    else:
        csv_files = sorted(data_dir.glob("*.csv"))
        if not csv_files:
            print(
                "No se encontró ningún CSV en data/. Coloca un archivo con columnas time,open,high,low,close para ejecutar el backtest."
            )
            return
        csv_path = csv_files[0]

    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo {csv_path}")

    metrics = run_backtest(csv_path)
    report_lines = [
        f"Archivo analizado: {csv_path}",
        "Estrategia: RSI<30 compra / RSI>70 venta, SL/TP basados en ATR",
        f"Winrate: {metrics['winrate']:.2%}",
        f"Profit Factor: {metrics['profit_factor']:.2f}",
        f"Max Drawdown: {metrics['max_drawdown']:.2%}",
        f"Retorno acumulado: {metrics['retorno']:.2%}",
        "Nota: este backtest es didáctico. Ajusta datos, costes y ejecución a tu bróker real.",
    ]

    ensure_dir(data_dir)
    report_path = data_dir / "backtest_report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Informe guardado en {report_path}")


if __name__ == "__main__":  # pragma: no cover - ejecución manual
    main()
