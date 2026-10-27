# ilahuerta-IA_backtrader-pullback-window-xauusd — "Sunrise Ogle" 5m pullback-window (Backtrader)

Files read: `src/strategy/sunrise_ogle_xauusd.py` (3450 lines; all `tests/*.py` and `entry_validation_analysis.py` are 0-byte), `PERFORMANCE_METRICS.md`, `README.md`.

## 1. Claims vs evidence
- Claimed (5m, 2020-07-10 → 2025-07-25, $100k): return +44.75%, Sharpe 0.892, **PF 1.64**, **win 55.43% (97W/78L, 175 trades)**, max DD 5.81%, expectancy $251.
- **No saved outputs, no data, no images, no trade reports in repo.** The metrics doc is internally inconsistent: gross loss listed as $71,233.45 but PF computed with $70,233.45; 115,166.76 − 71,233.45 = 43,933 ≠ 44,747; "5 large losses (<−$2,000)" total only −$5,987; "525,600 5-minute bars" is the number of *minutes* in a year. Treat the numbers as unverified/likely generated text.
- README contradicts code (README: SL 2.5×ATR, TP 12×ATR, EMAs 14/18/24, 7-17 UTC filter; code: long SL 4.5, TP 6.5, EMAs 14/14/24, time filter OFF).

## 2. Data / timeframe / timezone
`XAUUSD_5m_5Yea.csv` (not included), GenericCSV `YYYYMMDD,HH:MM:SS,O,H,L,C,V`, 5-minute. Comments label hours "UTC"; source unknown.

## 3. Default parameters that trade (code, not README)
- **LONG only** (`ENABLE_SHORT_TRADES=False`).
- EMA_confirm = EMA(1) = close; EMA_fast 14, EMA_medium 14, EMA_slow 24, EMA_filter 100 (Backtrader EMA, SMA-seeded). ATR(10) Backtrader (Wilder). `ema_exit` 25 computed but unused.
- Long: price-filter EMA ON; ATR filter ON with `0 <= ATR <= 2.00` (price units); candle-direction, EMA-order, angle, EMA-below-price filters OFF. ATR-increment filter is ON in params but only referenced in dead code (`_handle_pullback_entry`, never called from `next()`).
- Pullback: `LONG_PULLBACK_MAX_CANDLES=3`, `LONG_ENTRY_WINDOW_PERIODS=1`, `WINDOW_PRICE_OFFSET_MULTIPLIER=0.001`, time offset OFF.
- SL = 4.5×ATR, TP = 6.5×ATR (measured from signal-bar low/high). Risk 1%. Cash 100k, `setcommission(leverage=30)` → **zero commission, zero spread, no slippage**.
- (Short params if enabled: EMA-order, price filter, prev-bearish candle, angle in [−90,−20] with scale 10, ATR in [0.0004,0.00075] — EURUSD-scale values that would block every gold short; SL 2.5, TP 6.5, 2 green candles, window 7.)

## 4. Entry rules (state machine, evaluated in `next()` on bar close; skipped entirely while a position or entry order exists)
1. **SCANNING** at bar s: `cross_above(close, EMA14)` or `cross_above(close, EMA24)` (cross = `a[0]>b[0] and a[-1]<=b[-1]`), and `close[s] > EMA100[s]`, and `ATR10[s] <= 2.0` → ARMED_LONG, count=0.
2. **ARMED_LONG** from bar s+1: if bar is red (`close<open`) → count += 1; when count reaches 3 → store that bar's high/low → WINDOW_OPEN. Any non-red bar → full reset to SCANNING. (Opposing check while armed: close crosses *below* EMA14/24 with previous bar bearish → reset.)
3. **WINDOW_OPEN** set on 3rd red bar p: `top = high[p] + 0.001*(high[p]-low[p])`, `bottom = low[p] − same`, `expiry = p+1`.
4. Bar p+1 only: if `high >= top` → SUCCESS (checked first; both touched → SUCCESS); elif `low <= bottom` → back to ARMED_LONG (count=0, need 3 new consecutive reds). Bar p+2 → expired → ARMED_LONG.
5. On SUCCESS at bar j: re-check `close[j] > EMA100[j]`; `ATR[j] > 0`. Submit **market buy** → fills at **open of j+1**.
   SL = `low[j] − 4.5·ATR[j]`, TP = `high[j] + 6.5·ATR[j]`. State resets to SCANNING.

## 5. Exits / mechanics
- Stop + Limit orders (OCO) created in `notify_order` when the entry fills at j+1's open → Backtrader evaluates them from bar **j+2** (bar j+1's range is unprotected). Stop created first → if both touched in one bar the **stop fills first** (Backtrader processes in submission order). Gaps: stop fills at open if gapped through; limit fills at open if better.
- No trailing, no time/day-end exit, no EMA exit. One position at a time. Can hold over weekends.
- Look-ahead: none found. Decision on close, fill at next open. Missing costs is the main optimism (5m gold, average SL ≈ 5-10 points means 0.3 spread ≈ 3-6% of R per trade).

## 6. Sizing
`contracts = max(1, int(equity*1% / ((entry_close_j − SL)*100)))`, order size = contracts×100 oz (risk computed from close[j], not the actual fill). Integer lots → most trades are 1 lot (100 oz) with risk ≤1% (could exceed 1% when the min-1 clamp applies). No martingale/grid.

## 7. Red flags
None (no network, no credentials). Placeholder `YOUR_USERNAME` URLs; heavy LLM-style docs with numbers not produced by any artifact in the repo.

## 8. Reimplementation notes
```
ema14, ema24, ema100 = EMA(close,14|24|100); atr = WilderATR(10)
state=SCAN
for t:
  if in_pos: check SL/TP from entry_bar+1 (SL first); continue
  if pending_entry: fill at open[t]; set SL/TP; in_pos; continue
  if state==SCAN:
     if (xup(close,ema14) or xup(close,ema24)) and close[t]>ema100[t] and atr[t]<=2.0: state=ARMED; n=0
  elif state==ARMED:
     if close[t]<open[t]: n+=1; if n==3: top=high[t]+.001*rng; bot=low[t]-.001*rng; win_bar=t+1; state=WIN
     else: state=SCAN
  elif state==WIN:
     if t>win_bar: state=ARMED; n=0
     elif high[t]>=top:
        if close[t]>ema100[t]: pending_entry; SL=low[t]-4.5*atr[t]; TP=high[t]+6.5*atr[t]
        state=SCAN
     elif low[t]<=bot: state=ARMED; n=0
```
(For strict Backtrader parity, start SL/TP checks at fill_bar+1.) Add 0.3 spread to test.

**Inflation:** no spread/commission; claimed metrics unsupported and inconsistent; parameters visibly hand-tuned ("OPTIMIZED"/"EXPANDED" comments) on the same 5-year sample (in-sample). The `ATR<=2.0` cap means almost no trades in 2024-25 high-volatility gold, so results depend heavily on period.
