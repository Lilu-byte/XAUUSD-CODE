# ikeawesom_xauusd-backtest — PDH/PDL sweep "70% win rate"

Files read: `TradeSimulation.py`, `ExtractTrades.py`, `main.ipynb` (with outputs), `README.md`.

## 1. Claims vs evidence
- README: ~70% win rate on every intraday TF, 2004-2024 Kaggle data: 1m 69.31% (7181 trades), 5m 70.85% (5619), **15m 71.17% (4547)**, 30m 70.57% (3704), 1h 69.21% (2761), 4h 61.44% (1097). No PF, no P&L, no return, no drawdown reported anywhere.
- `main.ipynb` saved outputs match the README table exactly, so the numbers are real outputs of this code. But they are **win counts under a broken win definition** (see 5/8): "WIN" is not "profitable", and no P&L is ever computed.

## 2. Data / timeframe / timezone
- Kaggle `novandraanugrah/xauusd-gold-price-historical-data-2004-2024`, `;`-separated `Date;Open;High;Low;Close;Volume`. Notebook runs on `./data/XAU_<tf>_data.csv` for 1m…1M.
- Timezone: not stated anywhere; days are grouped by the date string of the CSV timestamp (so whatever TZ the dataset uses, likely broker/UTC-ish; Sunday stubs become their own "day").
- **Ordering assumption:** each date's bars are `insert(0, …)`-ed and then the date dict is reversed. That only yields chronological order if the CSV is **newest-first**. If the file is oldest-first, the whole sim runs backwards in time (prev day = next calendar day, bars walked from close to open). Verify file order before trusting anything.

## 3. Parameters
None. No SL distance, no TP distance, no costs, one instrument, 1 unit implied.

## 4. Entry rules (only bar **open** prices are used inside the day)
- For each day D (skip the first): `PDH = max(high)`, `PDL = min(low)` of previous day in the dict (D-1 trading day, all bars).
- Bias: `change = open - close` per bar (note sign); `bullish = sum(change over D-1 bars) >= 0`. Since sum(open-close) ≈ −(day's net move), **"bullish" flag ≈ previous day closed DOWN** (inverted vs README). Ties → bullish.
- State machine over bars of day D, `p = bar.open`:
  - bullish (long): not swept: if `p <= PDL` → `swept=True, sweep=p`, next bar. Swept, not in trade: if `p >= sweep` → **enter long at p**; else `sweep = p` (trail the low).
  - bearish (short): mirror with `p >= PDH`, entry when `p <= sweep`, else `sweep = p`.
- Multiple trades per day allowed; after a WIN all state resets and a new sweep of the same PDH/PDL is required.

## 5. Exit rules / backtest mechanics
- In trade, each subsequent bar open `p` (long; short mirrored):
  - `p > sweep` → **"WIN"**, exit at p, reset. (Compared with the *sweep price*, not entry. Entry was already `>= sweep`, so a WIN can be a loss in price terms.)
  - `p == sweep` → flag BE, keep holding; the next resolution is then recorded as "BE" (counts as a trade, not a win).
  - `p < sweep` → "LOSE", exit at p, stop processing the day (no more trades).
- Day end with no resolution (entry on last bar) → compares last open vs entry → recorded BE (equal). No overnight holding.
- High/low intrabar never used for exits → no SL/TP-same-bar question. No spread, no commission, no slippage.
- Look-ahead: none intrabar if file order is right (decision on bar open, fill at same open is achievable). The edge is fake for a different reason: the "TP" is the swept extreme which is *behind* entry.

## 6. Sizing
None (win count only). No martingale/grid.

## 7. Red flags
None in code (no credentials, no network except `kagglehub` download in notebook).

## 8. Reimplementation notes
```
for day D (chronological), prev = D-1:
  PDH,PDL = max(prev.high), min(prev.low)
  long_mode = sum(prev.open - prev.close) >= 0      # faithful (inverted) bias
  state=FLAT; swept=False
  for bar in D:  p = bar.open
    if state==IN:
      if (long_mode and p>sweep) or (!long_mode and p<sweep): record(WIN or BE if be_flag, entry, p); reset (swept=False, be_flag=False)
      elif p==sweep: be_flag=True
      else: record(LOSE, entry, p); break
    elif not swept:
      if (long_mode and p<=PDL) or (!long_mode and p>=PDH): swept=True; sweep=p
    else:
      if (long_mode and p>=sweep) or (!long_mode and p<=sweep): state=IN; entry=p
      else: sweep=p
  if state==IN at day end: record(BE if last_open==entry else WIN/LOSE vs entry)
```
Add a P&L column = `dir*(exit-entry)` and report it; also run a "fixed" variant with bias sign corrected and real SL/TP.

**Why ~70% is inflated:** a "win" only requires the next bar's open to stay on the right side of the swept extreme, which the entry bar already sits on (entry `>= sweep`). That is a near-coin-flip skewed to the "win" side by construction, and wins are scored without reference to entry price, so many "wins" lose money. No P&L, no costs (a 1-bar hold on 1m/5m gold is dominated by a ~0.2-0.3 spread). Expect win-rate-by-P&L near or below 50% and negative expectancy after spread.
