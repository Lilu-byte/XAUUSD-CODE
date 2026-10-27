# Rithick574_XAUUSD-bot-forex — EMA 21/55 cross + ADX + ATR, optional ML veto

Files read: `config.py`, `indicators.py`, `strategy.py`, `backtest.py`, `features.py`, `train_ml.py`, `ml_filter.py`, `bot.py`, `mt5_client.py`, `test_trade.py`, `README.md`.

## 1. Claims vs evidence
- No performance claims. README shows an *illustrative* `train_ml.py` printout (baseline win 41.2%, holdout AUC 0.612, filtered win 49.7% at 0.55). No saved outputs, no model file, no data in repo → nothing is backed up. Author advises PF > 1.3 target and demo first.

## 2. Data / timeframe / timezone
- MT5 `copy_rates_from_pos(SYMBOL, M15, 0, N)`; backtest default last 5000 M15 bars (~2.5 months), ML training last 40000 bars.
- Timestamps = MT5 server time (epoch → naive datetime, no TZ conversion). Hour feature for ML is broker-server hour.

## 3. Parameters (config.py)
EMA_FAST 21, EMA_SLOW 55 (on close, `ewm(span, adjust=False)`), ADX_PERIOD 14, ADX_MIN 20, ATR_PERIOD 14, ATR_SL_MULT 2.0, ATR_TP_MULT 3.0, RISK_PER_TRADE 1%, MAX_OPEN_POSITIONS 1, ML_ENABLED True, ML_MIN_PROBA 0.55, ML_MAX_HOLD_BARS 96 (label horizon only). Backtest: SPREAD_PRICE 0.20, START_EQUITY 10,000.
Indicators: ATR = Wilder (`ewm(alpha=1/14)`) of TR; ADX = Wilder-smoothed +DM/−DM/TR → DX → Wilder; RSI Wilder 14 (features only).

## 4. Entry rules (signal bar = last closed bar t)
- `cross_up = ema_f[t-1] <= ema_s[t-1] and ema_f[t] > ema_s[t]`; `cross_dn` mirror.
- `adx[t] > 20`.
- If ML loaded: `P(win | features[t], dir) >= 0.55` (GradientBoosting, 11 direction-oriented features: adx, adx.diff(3), atr/close, rsi oriented, (emaF-emaS)/atr, (close-emaS)/atr, 5/10-bar pct return, body/atr, hour sin/cos).
- Only when flat. No session filter, no day filter.
- Backtest fill = **close of signal bar t** (docstring says next-bar open; code uses `r.close`). Live: market order at ask/bid right after bar close (≈ next open).

## 5. Exits / mechanics
- SL = entry − dir·2·ATR[t], TP = entry + dir·3·ATR[t], fixed.
- From bar t+1: long: `low <= SL` → SL (checked first), elif `high >= TP` → TP. Short mirror. **Both touched → SL** (conservative). Fills exactly at level (no gap handling).
- Opposite EMA cross on bar j (and no SL/TP that bar) → exit at close[j]. After any exit on bar j, a new entry can be opened on the same bar j's close (so an opposite cross flips the position if ADX > 20).
- No time exit in backtest/live (96-bar cap only used for ML labels). Open position at data end is not closed/counted.
- Costs: flat `0.20 * size` deducted per round trip. No commission/swap.
- Look-ahead: rule path is causal. ML path: `train_ml.py` refits the final model on **all** labeled events (`model.fit(X, y)`) and `backtest.py` then runs on overlapping history → in-sample ML backtest. `dropna()` only removes ~10 warm-up rows; EMA55 is not warmed up (ewm starts at bar 0).

## 6. Sizing
Fixed-fractional compounding: `size = equity*1% / (2*ATR)` units (P&L in price×size). Live: lots = risk$/(ticks·tick_value), clamped to broker min/max/step. No martingale/grid.

## 7. Red flags
None. Credentials default `None`; only MT5 API. `test_trade.py` refuses real accounts unless `--force`.

## 8. Reimplementation notes
```
ema_f, ema_s = EMA(close,21), EMA(close,55); atr = WilderATR(14); adx = WilderADX(14)
for t in 1..N-1:
  if pos:
    if pos.dir>0: hit = SL if low[t]<=SL else TP if high[t]>=TP else None
    else:         hit = SL if high[t]>=SL else TP if low[t]<=TP else None
    if hit is None and opposite_cross(t): hit = close[t]
    if hit: pnl = dir*(hit-entry)*size - 0.20*size; equity+=pnl; pos=None
  if not pos:
    d = +1 if cross_up(t) and adx[t]>20 else -1 if cross_dn(t) and adx[t]>20 else 0
    if d and (no ML or proba>=0.55):
      entry=close[t]; SL=entry-d*2*atr[t]; TP=entry+d*3*atr[t]; size=equity*0.01/(2*atr[t])
```
Skip the ML filter (no model shipped) or train it walk-forward. Rule-only is honest; expect ~35-45% win at 1.5R reward (README's illustrative 41%).

**Inflation risks:** ML backtest is in-sample if you reuse the shipped training flow; entry at signal-bar close with 0.20 spread is mildly optimistic vs real next-open fill + wider spread on M15 crosses; SL-first tie handling is conservative (deflates).
