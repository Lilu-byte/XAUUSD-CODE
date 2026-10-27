# AhadRasheed_gold-strategy — M5 PDH/PDL break + reversal-candle breakout, 2R

Files read: `strategy.py`, `backtest.py`, `config.py`, `main.py`, `results/backtest_report.txt`, `download_xauusd.py`, `get_xauusd_data.py`, `check_mt5.py`, `README.md`.

## 1. Claims vs evidence
- README: XAUUSD M5, Apr 2025 – Sep 2026, 100,000 candles, **99 trades, 40 W / 59 L, win 40.40%**, $10,000 → **$12,203.47**.
- `results/backtest_report.txt` (saved output of `make_report`) matches: PF **1.342**, avg **+0.212 R**, max DD −$892.77 (−8.68%), max loss streak 7. Internally consistent: 40×2R − 59×1R = 21R = 0.212×99. No trades.csv/equity file or data in repo, so period/data cannot be re-checked.
- Costs were **zero** (`ENTRY_SLIPPAGE=0`, `FIXED_COST_PER_TRADE=0`).

## 2. Data / timeframe / timezone
MT5 `copy_rates_range(XAUUSD, M5)` 2023-09-01 → 2026-09-18 exported as `datetime,open,high,low,close,…`. Converted with `utc=True`, but MT5 epoch is **broker server time**, so "UTC" labels = server time (typically GMT+2/+3). Days = calendar date of that timestamp → broker-day PDH/PDL (Sunday stub is a "day").

## 3. Parameters
RISK_PERCENT 1.0 (of current balance, compounding), RR 2.0, ENTRY_SLIPPAGE 0.0, FIXED_COST 0.0, ONE_POSITION_AT_A_TIME True, CONSERVATIVE_SAME_BAR True. Note `strategy.py` hard-codes `target = entry + 2.0*risk`; backtest recomputes with RR (same).

## 4. Entry rules (setup scan over all bars first, independent of trades)
`PDH/PDL` = max high / min low of previous calendar date in the file. For bar i (skip if no prev day):
- (Dead code: the "reset when back inside range" check compares `state["direction"] == "LONG"/"SHORT"`, which never matches the actual state names → never fires.)
- **Idle:** if `low[i] < PDL` → LONG_WAIT, `ext = low[i]`; elif `high[i] > PDH` → SHORT_WAIT_GREEN, `ext = high[i]`. Then next bar.
- **LONG_WAIT:** if green (`close>open`) and `close < PDL` → LONG_BREAK, `rev = bar i` (ext NOT updated with this bar's low). Else `ext = min(ext, low)`.
- **LONG_BREAK:** if `close >= PDL and high < rev.high` → cancel. Elif `high > rev.high` → **LONG entry at rev.high**, SL = ext, valid only if SL < entry; TP = entry + 2·(entry−SL). Else keep waiting (ext not updated).
- **SHORT_WAIT_GREEN:** green with `close > PDH` → SHORT_WAIT_RED (ext not updated with it); else `ext = max(ext, high)`.
- **SHORT_WAIT_RED:** red (`close<open`) with `close > PDH` → SHORT_BREAK, `rev = bar` (ext not updated); else ext = max(ext, high).
- **SHORT_BREAK:** if `low < rev.low` → **SHORT entry at rev.low**, SL = ext (valid if > entry), TP 2R. No invalidation.
- PDH/PDL are read from the *current* bar's row, so they change at the day roll while a state is pending. No timeouts: a WAIT state can persist for days. No session filter. After an entry, state resets and scanning resumes on the next bar.

## 5. Exits / mechanics
- Trade checked from the bar **after** the entry bar (entry bar's own range ignored). Long: `hit_sl = low<=SL`, `hit_tp = high>=TP`; **both → LOSS (SL)**. Fills exactly at SL/TP (no gap fill modelling). Entry fill exactly at the broken level even if the bar gapped through it.
- No time exit, no day-end exit, no trailing. Unresolved at data end → closed at last close ("OPEN_AT_END").
- One position: setups with `entry_time <= last_exit` are skipped; an OPEN_AT_END trade does not set `last_exit` (minor).
- P&L booked as `risk_money × R` (R = −1 or +2), so units/lot rounding ignored.
- Look-ahead: PDH/PDL are prior-day (fine). Optimistic bits: stop-entry at exact level on gaps; ignoring SL/TP on the entry bar; zero spread (with tight structural stops on M5 — often $2-5 — a 0.3 spread is 6-15% of R).

## 6. Sizing
1% of current balance per trade, compounding. No martingale/grid.

## 7. Red flags
None. MT5 data download only (no credentials, no external web).

## 8. Reimplementation notes
```
PDH,PDL per row = prev broker-date high/low
state=None
for i:
  if state is None:
     if low<PDL: state=LW; ext=low; continue
     if high>PDH: state=SG; ext=high; continue
     continue
  if state==LW:  if green and close<PDL: rev=i; state=LB; continue
                 ext=min(ext,low)
  elif state==LB:
     if close>=PDL and high<rev.high: state=None; continue
     if high>rev.high: if ext<rev.high: emit LONG(entry=rev.high, sl=ext, tp=entry+2R, entry_bar=i); state=None
  elif state==SG: if green and close>PDH: state=SR; continue
                  ext=max(ext,high)
  elif state==SR: if red and close>PDH: rev=i; state=SB; continue
                  ext=max(ext,high)
  elif state==SB: if low<rev.low: if ext>rev.low: emit SHORT(rev.low, ext, 2R, i); state=None
simulate each setup from entry_bar+1, SL-first on ties, skip setups overlapping an open trade.
```
Honest mode: include the reversal/green/red bars in `ext`, fill stop-entries at `max(level, open)` (long), check SL on the entry bar, add 0.3 spread.

**Inflation:** modest. 40% win at 2R needs costs ≈ 0; with 0.3 spread the +0.21R/trade edge likely shrinks by ~0.1-0.2R. Small sample (99 trades). SL-first tie rule is conservative.
