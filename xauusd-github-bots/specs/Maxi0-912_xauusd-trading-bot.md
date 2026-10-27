# Maxi0-912_xauusd-trading-bot — H1 Donchian breakout + RSI + EMA200 + ATR (walk-forward)

Files read: `bot_xauusd.py`, `walk_forward.py`, `optimizar_breakout.py`, `backtest_xauusd.py` (actually the breakout backtest), `backtest_regimen.py`, `filtro_noticias.py`, `notificaciones.py`, `dashboard.py` (grep), `README.md`.

## 1. Claims vs evidence
- README (walk-forward, H1, ~4 yrs): PF **1.22**, win **38.1%**, max DD **10.6%**, **84** OOS trades, **3/5** profitable steps. Live params chosen from it: RANGO 40, RSI 75/25, ATR_SL 2.0.
- No saved outputs/logs/data in repo; numbers unverifiable. Arithmetic is self-consistent: with fixed +2R/−1R, PF = 2·W/L → 38.1% win gives PF ≈ 1.23.
- Author's own regime/optimizer scripts print that earlier variants failed out of sample.

## 2. Data / timeframe / timezone
MT5 `copy_rates_range(XAUUSD, H1)` from IC Markets / MetaQuotes-Demo. WF range 2022-01-01 → 2026-06-28; optimizer 2025-01-01→2026-06-28 with "validation" 2022-2024. Times = MT5 server time (naive, typically GMT+2/+3). No session filter.

## 3. Parameters
Live (`bot_xauusd.py`): RANGO_VELAS 40, RSI_PERIOD 14, RSI OB/OS 75/25, EMA 200, ATR 14, ATR_SL_MULT 2.0, ATR_MIN_PERCENTIL 30, RR 2.0, RISK 1%.
Backtests: spread 30 points × 0.01 = **0.30** price, balance 100k, risk 1%. WF grid: RANGO {15,20,30,40} × RSI {(65,35),(70,30),(75,25)} × ATR_SL {1.0,1.5,2.0}; select by max PF in train with ≥15 trades. Train 270 d, validate 90 d.
Indicators: EMA `ewm(span=200, adjust=False)`; RSI = **SMA-based** (rolling mean of gains / losses, 14); ATR = **SMA** of TR(14).

## 4. Entry rules (evaluated on closed bar t)
- `hh = max(high[t-N..t-1])`, `ll = min(low[t-N..t-1])` (N = RANGO, excludes bar t).
- Long: `close[t] > hh` and `close[t] > EMA200[t]` and `RSI[t] < 75` and `ATR[t] >= q30`.
- Short: `close[t] < ll` and `close[t] < EMA200[t]` and `RSI[t] > 25` and `ATR[t] >= q30`.
- `q30` = 30th percentile of ATR over the **entire downloaded dataset** (backtests) / last 500 bars (live).
- Only when flat (one position, magic filter). Live also blocks new entries ±30 min around High-impact USD events (Forex Factory weekly JSON) — not in backtests.

## 5. Exits / mechanics
- Backtest fill: long `entry = close[t] + 0.30`, short `entry = close[t] − 0.30`. SL = entry ∓ ATR·mult, TP = entry ± 2·SL distance. Live: market at ask/bid.
- From bar t+1: long `low<=SL` → SL first, elif `high>=TP` → TP; short mirror. **Both touched → SL.** New entry allowed on the same bar that closed the prior trade.
- No trailing, no time/day exit, no opposite-signal exit. Open trade at window end is dropped (not counted).
- P&L: not price-based — each trade is booked as +2R or −1R of compounding 1% risk.
- WF: each window is simulated from scratch (no carry-over); next step starts at `fin_train`, so validation windows cover 90 of every 270 days (5 steps: OOS ≈ 2022-10, 2023-07, 2024-04, 2025-01, 2025-10, 90 d each).
- **Look-ahead:** ATR q30/q90 percentile is computed over the full 2022-2026 history before slicing → future vol regime leaks into every window (mild). Indicators computed on full history then sliced (fine, causal). Otherwise causal; entering at signal-bar close is an optimistic but achievable fill.

## 6. Sizing
Fixed 1% of balance per trade (compounding). Live lots = risk$ / (SL points × point value), min 0.01. No martingale/grid.

## 7. Red flags
- **Hardcoded MT5 demo login + two different passwords** in `backtest_xauusd.py`, `walk_forward.py`, `optimizar_breakout.py`.
- **Hardcoded Telegram bot token and chat_id** in `notificaciones.py` (posts trade notifications to api.telegram.org). Leaked secrets, not malware; remove before any use.
- `filtro_noticias.py` uses `cloudscraper` against nfs.faireconomy.media (anti-bot bypass). Flask dashboard on localhost:5000. No lures.

## 8. Reimplementation notes
```
ema=EMA(close,200); rsi=SMA_RSI(close,14); atr=SMA(TR,14); q=quantile(atr,0.30)  # causal: use expanding/rolling quantile
hh=rolling_max(high.shift(1),N); ll=rolling_min(low.shift(1),N)
for t from max(200,N,14)+5:
  if pos: (long) if low[t]<=SL: lose elif high[t]>=TP: win; (short mirror) -> R += -1 / +RR
  if not pos and atr[t]>=q:
    if close[t]>hh[t] and close[t]>ema[t] and rsi[t]<OB: entry=close[t]+0.30; SL=entry-k*atr[t]; TP=entry+RR*k*atr[t]
    elif close[t]<ll[t] and close[t]<ema[t] and rsi[t]>OS: entry=close[t]-0.30; SL=entry+k*atr[t]; TP=entry-RR*k*atr[t]
```
Live defaults: N=40, OB/OS 75/25, k=2.0, RR=2. Also implement `backtest_regimen.py` variant if wanted (ADX(SMA-smoothed)≥25 → breakout with EMA200; ADX≤20 → fade: buy if close in bottom 15% of 20-bar range, sell top 15%; skip if ATR > full-sample q90; k=1.5, RR=1.5).

**Inflation:** small sample (84 trades) and per-window re-optimisation over 36 combos; full-sample ATR percentile; fixed R booking ignores gaps through SL. SL-first tie rule deflates. PF 1.22 on 84 trades is within noise of 1.0.
