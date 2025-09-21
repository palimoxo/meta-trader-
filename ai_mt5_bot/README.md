# ai-mt5-bot

Asistente de trading automático para MetaTrader 5 guiado por una señal de IA.

## Requisitos previos
1. **MetaTrader 5** instalado en Windows 11 con una cuenta demo (ej. Admiral Markets) y el terminal abierto. Activa la casilla **"Permitir automatización Algo trading"**.
2. Python 3.10 o superior instalado y accesible desde la terminal.
3. Cuenta de OpenAI con acceso al modelo configurado.
4. Este repositorio clonado localmente.
5. Conexión estable a Internet para descargar históricos y consultar la IA.

## Instalación
1. Crea un entorno virtual:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate  # En PowerShell
   ```
2. Instala dependencias:
   ```bash
   pip install -r ai_mt5_bot/requirements.txt
   ```
3. Copia el archivo de ejemplo y completa la configuración:
   ```bash
   copy ai_mt5_bot\\.env.example ai_mt5_bot\\.env
   ```
   Edita `.env` para añadir tu `OPENAI_API_KEY` y ajustar parámetros.

## Uso
- **Modo Paper (por defecto)**:
  ```bash
  python -m ai_mt5_bot.trader --symbol EURUSD --timeframe M5
  ```
- **Modo Live (bajo tu responsabilidad)**:
  ```bash
  python -m ai_mt5_bot.trader --symbol EURUSD --timeframe M5 --live
  ```
- Cambia el riesgo por operación:
  ```bash
  python -m ai_mt5_bot.trader --risk 0.02
  ```

Los registros de decisiones y órdenes se guardan en `ai_mt5_bot/data/` (`decisions.csv`, `orders.csv`, `trades.log`).

## Backtesting
Coloca un CSV con columnas `time,open,high,low,close` dentro de `ai_mt5_bot/data/` y ejecuta:
```bash
python -m ai_mt5_bot.backtester --file ai_mt5_bot/data/tu_archivo.csv
```
El informe se generará en `ai_mt5_bot/data/backtest_report.txt`. El backtest es educativo: ajusta comisiones, spreads y horarios a tu bróker real.

## Estructura del proyecto
- `config.py`: carga y valida parámetros desde `.env`.
- `mt5_handler.py`: conexión con MetaTrader 5.
- `indicators.py`: RSI, ATR y retornos.
- `ai_decision.py`: consulta y validación de la IA.
- `risk.py`: cálculo de volumen según riesgo.
- `trader.py`: orquestador principal (paper/live).
- `logger.py`: logging en consola y archivo.
- `utils.py`: utilidades y guardado de CSV.
- `backtester.py`: ejemplo sencillo de backtesting.
- `tests/`: pruebas unitarias básicas.

## Consejos operativos
- Prueba el bot varios días en demo antes de operar en real.
- Ajusta `MAX_SPREAD_POINTS` al comportamiento típico de tu bróker y símbolo.
- Evita operar durante noticias económicas de alto impacto.
- Establece límites diarios/semanales de pérdida y pausa el bot si se alcanzan.

## Aviso legal
Este proyecto tiene fines educativos. Operar en mercados financieros conlleva un **alto riesgo** y puedes perder parte o la totalidad de tu capital. No se ofrecen garantías de rentabilidad ni se asume responsabilidad por su uso.
