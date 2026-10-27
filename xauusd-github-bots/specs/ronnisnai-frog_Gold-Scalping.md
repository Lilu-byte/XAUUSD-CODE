# ronnisnai-frog / Gold-Scalping (GoldReversionGuard.mq5 v1.01)

## 1. Author's claims
No performance figures at all: no win rate, PF, test period or equity curve. It is described as an "Educational project"; the README tells the user to run the tester themselves ("at least 6–12 months, Every tick based on real ticks"). It mentions XM's "GOLD" symbol. The CHANGELOG says v1.00 sized trades "about 8x larger than the intended risk", fixed in 1.01 via OrderCalcProfit. The design (Z-score, turn bar, cost gate, mean TP) is near-identical to n30dyn4m1c TickRobust, but on M5 with SMA50.

## 2. Timeframe
Signals come from `InpTimeframe` = **M5** (independent of the chart). Daily reset uses the D1 bar time. No other HTF.

## 3. Defaults that affect trading
MeanPeriod 50 (SMA and StdDev of close), EntryZ 2.2, ExitZ 0.3, RequireTurn true, ADX 14 with Max 22, ATR 14, ATRAvgBars 50, ATR ratio [0.5, 2.0], MaxSpread 50 pts, ExtraCost 0, StdCostMult 3, DistCostMult 4, Start 10 / End 20 (server time), news on (USD, ±60 min), CloseBeforeNews false, Risk 1% of equity, DailyLoss 3% of day-start equity, MaxTradesDay 8, CooldownBars 6, AllowMinLot false, MinLotRiskCap 3%, SLATRMult 2.5, SLMinPts 500, BreakevenATR 1.0, BEOffset 20 pts, MaxHoldBars 40, CloseFriday true at hour 20, deviation 30, magic 240611.

## 4. Entry (once per new M5 bar, only when no own position)
All values from closed bar 1: m = SMA50[1], s = StdDev50[1] (MT5 population SD), Z = (C1 − m)/s, ADX[1], ATR14[1], ratio = ATR[1] / mean(ATR[1..50]).
Blocked if any of these hold: daily lock; trades today ≥ 8 (counted on DEAL_ENTRY_IN); now < cooldownUntil; Friday hour ≥ 20; hour outside [10, 20); news within ±60 min (**disabled in the tester**); SYMBOL_SPREAD > 50; ADX > 22; ratio < 0.5 or > 2.0.
- Buy if Z ≤ −2.2 and C1 ≥ C2. Sell if Z ≥ +2.2 and C1 ≤ C2.
- Cost gate: cost = (spread + extra)·point. Needs s ≥ 3·cost and |m − fill| ≥ 4·cost.
- SL = fill ∓ max(500 pts, 2.5·ATR). TP = m. Skip if the TP or SL is within (stops/freeze level + 5) pts.
- No day-of-week filter other than Friday ≥ 20:00. Saturday and Sunday are not blocked explicitly, but there are no ticks then.

## 5. Exits (once per new bar, in this order)
1. Optional news close (off by default).
2. Z exit: long closes if Z ≥ −0.3; short closes if Z ≤ +0.3 (closed-bar Z, market close).
3. Time exit: iBarShift(open time) ≥ 40 bars, i.e. about 200 min on M5.
4. Breakeven: when price − open ≥ 1·ATR and the SL is still below entry, move SL to entry + 20 pts (mirrored for shorts). Applied once; there is no trailing.
5. TP retarget: set TP to the current SMA50[1] whenever that mean is still beyond the current price by more than the gap. There is no floor at entry, so the TP can end up below entry for a long (a small-loss limit).
- Server-side SL and TP act intrabar.
- Every tick: equity ≤ day-start equity·(1 − 3%) → close all and lock for the day. Friday ≥ 20:00 → close.
- Loss cooldown: after any closing deal with net P/L < 0, block entries for 6 × 300 s = 30 min.
- No partial closes and no opposite-signal exits.

## 6. Sizing
lots = floor(equity·1% / lossPerLot(entry→SL) / step)·step, using OrderCalcProfit. If that is below the min lot, the EA refuses to trade unless AllowMinLot is set and min-lot risk ≤ 3%. A margin check requires margin ≤ 0.9 × free margin. One position at a time; no grid, martingale or hedging.

## 7. Code vs README
The code matches the README closely. Points to note:
- The README says breakeven goes to "entry"; the code uses entry + 20 pts.
- The news filter is a no-op in backtests, so a Python rebuild without news matches the tester.
- On a small account (< about $2k at a $15–25 stop) with defaults, the EA places **no trades** ("Account too small").
- Look-ahead and repaint: none. Closed-bar values only, decisions at bar open.

## 8. Red flags
None. No WebRequest, no DLL imports, no credential requests, no obfuscation, no paid links. Uses only the standard Trade.mqh.

## 9. Reimplementation (M5 bars; decide at the open of bar t)
```
m=SMA50(C)[t-1]; s=pstd50(C)[t-1]; z=(C[t-1]-m)/s
a=ATR14[t-1]; r=a/mean(ATR14[t-50..t-1]); adx=ADX14[t-1]
if pos:
   if long and z>=-0.3 or short and z<=0.3: exit at O[t]
   elif bars_held>=40: exit
   else:
      if not be and favorable(O[t]) >= a: SL=entry±20pt
      if m beyond O[t]: TP=m
elif allowed(hour∈[10,20), !fri>=20, trades<8, cooldown over, !daylock,
             spread<=50, adx<=22, 0.5<=r<=2):
   long if z<=-2.2 and C[t-1]>=C[t-2]; short if z>=2.2 and C[t-1]<=C[t-2]
   cost=spread(+comm); need s>=3cost and |m-fill|>=4cost
   SL=fill∓max(5.00$, 2.5a); TP=m; size=1%equity/SLdist
intrabar: check SL/TP against H/L (pessimistic: SL first)
after a loss: cooldown 30 min; daily -3% equity → flat + lock
```
