# JoelPasapera_ExpertAdvisory — Polars "time-of-day bracket" backtester (strategy_1)

Files read: `ExpertAdvisory.py` (947 lines, all of it), `README.md`, `requirements.txt`.

## 1. Claims vs evidence
- README claims speed only ("14-year backtesting in 30 seconds" with Polars/PyTorch); **no win rate, PF, or return claims**. No outputs, CSVs, or charts in repo.
- **The file does not parse**: line 548 `df_1m_limits = df1_1m.select(["Date_max])` is an unterminated string (SyntaxError; also an undefined name). Further bugs: `_run_back_test` swaps `max`/`min` and reads `parameters["Date"]` instead of `Date_max`; the CSV rename maps `column_0` (which doesn't exist) etc. So nothing in this repo could have produced results as committed. Spec below is the **intended** logic.
- PyTorch is imported but never used; GPU tester, strategy_2 (SMC), news scraping, evaluator, PDF report are empty stubs.

## 2. Data / timeframe / timezone
- Raw `XAUUSD.csv` from a **Google Drive link** in README (unknown provenance), MT4-style no-header rows `YYYY.MM.DD,HH:MM,O,H,L,C,V`, 1-minute.
- Timestamps are declared as `America/Lima` (UTC−5, no DST), then converted to `America/New_York` (DST-aware) and written to `XAUUSD_1m.csv` as naive NY-local strings. So the 09:00 / 13:00 rules are **New York local time**, assuming the raw file truly is UTC−5. Resampled 5m…1d files are created but unused.

## 3. Parameters (strategy_1 defaults)
`entry_time="9:00"`, `tp=4` (price units, $4), `sl=2` ($2), `limit_time="13:00:00"`, `order="buy"` (ignored), `lot_size=0.05` (ignored). No spread/commission.

## 4. Entry rules
- Every day, take the 1-minute bar stamped exactly **09:00** NY (bar 09:00:00-09:00:59).
- Direction: computed later as `buy if tp > sl` → `(High+4) > (Low−2)` is always true → **always long**.
- Entry price = **Open of the 09:00 bar**.
- TP = `High(09:00 bar) + 4`, SL = `Low(09:00 bar) − 2`. **Look-ahead:** the levels use the high/low of the same bar whose open is the fill, so the entry bar can never stop you out and SL distance is set with knowledge of that minute's range.
- One trade per day, no filters.

## 5. Exit rules / mechanics (intended)
- Scan 1m bars from 09:00 (inclusive) to 13:00:00 same day: first bar with `High >= TP` **or** `Low <= SL`.
- `close_price = TP if High >= TP else SL` → **if both touched in one bar → TP (optimistic)**.
- If neither is hit by 13:00 → takes the last bar of the window, then `close_price = TP if its High >= TP else SL` → a time-exit is **booked as a full SL loss**, not at the 13:00 price (pessimistic, and wrong).
- Profit: `+|Open − TP|` if close_price > Open, else `−|Open − SL|` (price units, per 1 oz; no lot math). Cumulative sum is the equity curve. Win ≥ $4, loss ≥ $2 by construction.
- As committed (with the swapped max/min bug, if the syntax error were fixed) the first bar (09:00 itself) always matches, `close_price = SL` → every trade a loss.

## 6. Sizing
None (P&L in price units). No martingale/grid.

## 7. Red flags
- External **Google Drive download** for the data file and a YouTube link (not malicious in code, but unverifiable data; only fetch as data, never execute).
- No credentials, no network calls in code. `setup_file_paths()` does `os.chdir` to the script dir (harmless). Mostly scaffold/stub code.

## 8. Reimplementation notes
```
bars: 1m, tz = America/New_York (convert from UTC-5 fixed if using their file)
for each date d:
  b0 = bar at d 09:00; if missing: skip
  entry = b0.open; tp = b0.high + 4; sl = b0.low - 2
  win = None
  for b in bars[d 09:00 .. d 13:00]:          # inclusive of b0 (cannot trigger)
     if b.high >= tp: exit=tp; break           # TP checked first
     if b.low  <= sl: exit=sl; break
  else: exit = sl                               # faithful: time-out booked as SL
        # honest: exit = last bar close (<=13:00)
  pnl = exit - entry
```
Honest mode: decide levels after the 09:00 bar closes and enter at 09:01 open (or use the prior bar's range), SL-first on ties, exit at 13:00 close, 0.3 spread.

**Bias notes:** TP-first tie handling and same-bar range look-ahead inflate win rate; booking timeouts as full SL deflates it. Long-only on gold over 14 years carries strong drift tailwind (gold ~+150% over the period) — compare against a "buy 09:00, sell 13:00" baseline.
