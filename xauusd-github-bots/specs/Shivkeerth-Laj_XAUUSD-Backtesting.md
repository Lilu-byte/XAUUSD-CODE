# Shivkeerth-Laj_XAUUSD-Backtesting — "4-candle run" breakout, 2R (Instagram strategy)

Files read: `XAUUSD BACKTEST V2.ipynb` (parsed as JSON text incl. saved outputs; 3 code cells, last one empty), `README.md`.

## 1. Claims vs evidence
- README makes no performance claim (strategy "from a short Instagram clip"); describes 50,000 M5 bars Feb-Oct 2025.
- **Saved output (cell 2, "Unedited strategy"):** 50,000 candles 2025-02-13 22:30 → 2025-10-28 17:20; start $50,000, **final −$171,200**, total P&L **−$221,200**, **5,939 trades, 1,611 W / 4,328 L, win 27.13%**. Check: 1611×$400 − 4328×$200 = −$221,200 ✓. So the repo's own output shows the strategy losing heavily (PF ≈ 0.74 at fixed $200 risk), even with optimistic fills.

## 2. Data / timeframe / timezone
MT5 `copy_rates_from_pos("XAUUSD.sd", M5, 0, 50000)` (falls back to XAUUSD/GOLD/…), epoch → naive datetime = **broker server time**. CSV saved to the author's Downloads folder (not in repo). No session filter.

## 3. Parameters
`initial_balance=50000`, `risk_per_trade=200` ($, fixed, not compounding), RR 2 (hard-coded), look-forward horizon 50 bars, run length 4 candles. No spread, commission, or slippage.

## 4. Entry rules (for every bar i ≥ 4)
- `last4 = bars[i-4 .. i-1]` (the four bars before i).
- `bullish = all(close > open)` over last4; `bearish = all(close < open)`.
- Bullish → **Buy**, entry = `high[i-1]`, SL = `low[i-1]`, TP = entry + 2·(entry−SL).
- Bearish → **Sell**, entry = `low[i-1]`, SL = `high[i-1]`, TP = entry − 2·(SL−entry).
- Skip if entry == SL. Trade time stamped at bar i.
- **No position limit and no dedup:** every bar whose prior 4 candles qualify opens a new, overlapping trade (a 6-candle green run yields 3 trades). That's why 5,939 trades in 8 months.
- **Fill assumption:** filled at `high[i-1]` (long) unconditionally — even if bar i and later never trade that high. This is a "price already passed / not yet reached" bias: trades are assumed filled whether or not the breakout happened.

## 5. Exits / mechanics
- Scan bars `i+1 … i+50` (**bar i itself is skipped**). Long: `high >= TP` → win (checked **first**), elif `low <= SL` → loss. Short mirror (`low <= TP` first). **Both touched in one bar → WIN** (optimistic).
- Fills exactly at SL/TP; no gap modelling.
- If neither within 50 bars → outcome "open", P&L 0, excluded from win %, balance unchanged (no mark-to-market exit).
- P&L = `(exit − entry) × lot`, `lot = 200 / |entry − SL|` → exactly +$400 or −$200 per resolved trade.
- Look-ahead summary: (a) unconditional fill at the breakout level, (b) ignoring bar i, (c) TP-first tie rule, (d) zero costs. All inflate; result is still negative.

## 6. Sizing
Fixed $200 risk per trade, units = 200/|entry−SL| (no lot rounding, no compounding; balance can go negative). No martingale/grid, but unlimited concurrent overlapping trades.

## 7. Red flags
None in code (no credentials, no web). Cell 0 runs `pip install`; contributor LinkedIn links in README only.

## 8. Reimplementation notes
```
for i in 4..N-1:
  b = bars[i-4:i]
  if all(b.close>b.open): d=+1; entry=high[i-1]; sl=low[i-1]
  elif all(b.close<b.open): d=-1; entry=low[i-1]; sl=high[i-1]
  else: continue
  R=abs(entry-sl); if R==0: continue
  tp = entry + d*2*R
  for j in i+1 .. min(i+50, N-1):
     if d>0: if high[j]>=tp: win; break  elif low[j]<=sl: loss; break
     else:   if low[j]<=tp: win; break   elif high[j]>=sl: loss; break
  pnl = +400 / -200 / 0(open)
```
Honest variant: require an actual stop-entry trigger (`high[k] > entry` for some k ≥ i, fill at `max(entry, open[k])`), check SL/TP from the fill bar, SL-first on ties, one position at a time, 0.3 spread, and close "open" trades at bar i+50 close.

**Inflation:** every bias here favours the strategy (assumed fills, TP-first ties, no costs), and the saved result is still −$221k at 27% win; a faithful honest rebuild should be worse. Overlapping trades make the trade count and DD meaningless as risk measures.
