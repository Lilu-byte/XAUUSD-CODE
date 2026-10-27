# dns2jtm_xauusd-mean-reversion — "Sawa" multi-TF DeMarker grid (9 sub-strategies)

Files read: `src/strategy.py`, `src/backtest.py`, `src/data_fetcher.py`, `tests/test_strategy.py`, `notebooks/Analysis.ipynb` (incl. saved outputs), `README.md`.

## 1. Claims vs evidence
- README: grid systems "boast high win rates (>80%)"; claims TCA (spread/commission) and walk-forward and a backtrader engine. **Code has none of these** — a plain pandas loop with zero costs and no WFA.
- Saved notebook output (quantstats): period **2026-06-10 → 2026-08-18** (~60 days), cumulative **+7.41%**, Sharpe **12.74**, max drawdown blank, Profit Factor 0.0, Ulcer 0.0. The blank DD / absurd Sharpe come from the equity curve being *realized balance only* (see 5) — so outputs exist but do not measure risk. No win rate is actually computed anywhere.

## 2. Data / timeframe / timezone
- `yfinance` `GC=F` (COMEX gold **futures**, not spot XAUUSD) 5-minute, last 60 days → `data/real_xauusd_5m.csv`. Base loop on 5m bars.
- Timezone: yfinance intraday index for GC=F is exchange time (America/New_York, tz-aware) — the hour filters are copied from an MQL5 EA that used broker server time (typically GMT+2/+3), so session hours are shifted ~7 h vs the original. (Parsing a CSV with mixed −04/−05 offsets may also yield an object index; unverified.)

## 3. Parameters (strategy.py; index = sub-strategy 1..12; active: 1,2,3,5,6,8,9,10,12)
| # | dir | TF1/P1 | TF2/P2 | buy if DM1< / DM2< | sell if DM1> / DM2> | TP pts | grid pts | entry hours |
|---|---|---|---|---|---|---|---|---|
|1|BUY|6m/18|15m/16|0.3/0.3|–|50|150|22,23|
|2|BUY|15/14|20/20|0.3/0.3|–|50|150|3|
|3|BUY|15/26|15/24|0.3/0.3|–|50|150|22|
|5|SELL|5/18|15/18|–|0.7/0.7|50|150|0|
|6|SELL|10/30|30/28|–|0.7/0.7|50|300|23|
|8|BUY|5/12|60/20|0.3/0.3|–|150|150|6-11|
|9|BUY|12/18|15/12|0.3/0.3|–|200|500|10-13|
|10|BUY|10/20|15/10|0.3/0.3|–|200|300|22|
|12|SELL|12/10|15/20|–|0.7/0.7|100|200|8,9|
`POINT_MULTIPLIER=0.01` (100 pts = $1). Lot 0.01 per order (1 oz), contract 100, max 100 orders per basket, balance 10,000.
DeMarker: `DeMax=max(H−H[-1],0)`, `DeMin=max(L[-1]−L,0)`, `SMA(DeMax,n)/(SMA(DeMax,n)+SMA(DeMin,n))`, 0.5 if denominator 0.

## 4. Entry rules
- For each TF: `df.resample('<TF>min')` (pandas default: **left-closed, left-labelled**) → DeMarker → `reindex(5m index).ffill()`.
- On 5m bar i, per active sub-strategy with an empty basket and `hour(i)` in its window: BUY if `DM1<low1 and DM2<low2`; SELL if `DM1>high1 and DM2>high2` → open 1 order at **close[i]**.
- **Look-ahead:** a resampled bar labelled 22:00 contains data to 22:14:59 (15m) or 22:59:59 (60m), but it is aligned to the 5m bar at 22:00 and used at that bar's close (22:05). Signals see up to TF−5 minutes of the future. Biggest bias in the repo.

## 5. Exits / grid mechanics (per bar, per sub-strategy)
- If basket non-empty: `avg = mean(entries)` (equal lots), `last = entries[-1]`.
  - BUY: if `high >= avg + TP` → close all at target; `continue` (no re-entry same bar). Else if `low <= last − grid` → add one order **at the bar low**.
  - SELL mirror (`low <= avg − TP`; add at **bar high** when `high >= last + grid`).
- TP checked before grid add on the same bar (uses pre-add average). Max one add per bar. No stop loss, no time exit; end of data closes everything at the last close.
- "Worst case execution for grid" comment is wrong: buying at the bar low / selling at the bar high is the *best* possible fill and also lower than the grid level → optimistic averages.
- Costs: none. Balance only changes when a basket closes → equity curve ignores floating losses (no drawdown visible until the final forced close).

## 6. Sizing / grid
Equal-lot averaging grid (no lot multiplier), up to 100 × 0.01 lots per sub-strategy, 9 sub-strategies can run concurrently (both directions). Exposure is unbounded in practice.

## 7. Red flags
No credentials/web requests beyond yfinance. Documentation misrepresents the engine (claims backtrader, TCA, WFA). Notebook output path reveals author's local home dir (harmless).

## 8. Reimplementation notes
```
for tf: bars_tf = resample(5m, tf, label='right', closed='left') -> shift so value is available only after tf bar closes  # causal fix
         dm_tf = DeMarker(bars_tf, n).reindex(5m.index, method='ffill')
for i in 5m bars:
  for s in active:
    B = baskets[s]
    if B:
      avg=mean(B); last=B[-1]
      if BUY and high[i]>=avg+TP_s: realize sum(avg+TP_s - e)*1oz; B.clear(); continue
      if BUY and low[i]<=last-G_s and len(B)<100: B.append(last-G_s)  # faithful: B.append(low[i])
      (SELL mirror)
    if not B and hour_ok(s, hour_local[i]) and signal(s,i): B.append(close[i])
mark-to-market equity every bar.
```
Faithful mode: `label='left'` alignment, fills at bar extreme, zero cost, realized-only equity. Honest mode: right-labelled TF bars, grid fills at the level, spread 0.3 per order, MTM equity.

**Inflation:** future-peeking resample alignment; grid fills at bar extremes; no costs; realized-only equity hides all drawdown (hence Sharpe 12.7, no DD); 60-day sample; no stop means baskets almost always close green (high "win rate") until a trend leg.
