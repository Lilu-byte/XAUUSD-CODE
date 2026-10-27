# n30dyn4m1c / gold-pro-scalper

## 1. Author's claims
No win rate, profit factor, test period or equity curve anywhere. README: "aggressive small-account growth on XM Global-style micro accounts"; CLAUDE.md admits the legacy EAs are "profitable on M1 OHLC modelling only". Symbol "GOLD" (XM name; falls back to XAUUSD). MIT licence.

## 2. Timeframe
All EAs: chart TF = **M1** (`_Period`). TickRobust also uses an **H1 SMA(50)**, read on the closed H1 bar (shift 1).

## 3. TickRobust defaults (magic 777555)
EntryZ 2.2, RequireTurn true, ExitZ 0.2, MaxHoldBars 40, SLPoints 800, SLATRMult 2.5, BreakevenATR 1.0, Start 10, End 20 (exclusive), FridayCloseHour 20, CooldownMins 15 (after a loss), ExtraCostPts 0, MinSDCostMult 3, MinTPCostMult 4, MaxSpread 50 pts, MA/SD period 20, ATR 14, ADX 14, ADXMax 22, H1 SMA 50, ATRAvgPeriod 50, ATR ratio 0.4–2.0, dynamic risk on (fixed 2% when off), news filter on (60 min before / 120 min after, close before news on), daily loss limit on.

## 4. TickRobust entry (evaluated once, on the first tick of each new M1 bar, only when flat)
All values are from the closed bar (shift 1). Z1 = (Close1 − SMA20_1)/StdDev20_1. StdDev is MT5 iStdDev, SMA-based, population (divide by N).
- Long if Z1 ≤ −2.2, short if Z1 ≥ +2.2.
- Turn: a long needs Close1 ≥ Close2, a short needs Close1 ≤ Close2.
- ADX14 main line at bar 1 ≤ 22.
- ATR14_1 / mean(ATR14 over bars 1..50) must be in [0.4, 2.0].
- Spread ≤ 50 pts. cost = spread + ExtraCost. Needs SD20 in points ≥ 3·cost, and |SMA20_1 − fill| in points ≥ 4·cost (fill = ask for a long, bid for a short).
- H1: long needs bid > H1 SMA50[1], short needs bid < it.
- Server hour in [10, 20). Not Friday ≥ 20:00, not Saturday or Sunday.
- News: no USD high-importance MT5 calendar event within (−120 min, +60 min) of now. Loss cooldown must have elapsed. At most 1 position.

## 5. TickRobust exits
- SL = entry ∓ max(800 pts, 2.5·ATR14_1). TP = a limit at SMA20_1 (the mean).
- Each new bar, in this order: (a) close if Z1 ≥ −0.2 (long) or Z1 ≤ 0.2 (short); (b) close if bars held ≥ 40; (c) breakeven: once bid − entry ≥ 1·ATR1, move SL to entry + (spread+2) pts; (d) "gravity" TP: retarget TP to max(SMA1, entry + cost + 5 pts) for a long (mirrored for a short), only when that moves the TP ≥ 20 pts closer.
- Every tick: daily loss limit hit → close all and stop for the day. Friday ≥ 20:00 or weekend → close. A USD red event 0–60 min ahead → close.
- No trailing and no partial closes.

## 6. Sizing
lots = balance·risk% / (SL distance · tickValue/tickSize). Dynamic tiers by equity: <500 → 10%, <2k → 7%, <5k → 5%, <20k → 3%, else 1.5%. Daily loss limit by tier: 25/20/15/10/7% of the day's starting balance, measured on equity. NormalizeLot clamps up to min lot, so a small account can risk more than its tier. No grid, martingale or hedging; 1 position.

## 7. Code vs README
TickRobust matches the README. The news filter needs the live MT5 calendar (in the tester it is empty or absent, so it never fires). The H1 filter fails open.

## Breakout EA (`XAU_Quant_Reversion_Breakout.mq5`, header says "Gemini Quant Lab")
Decides **on every tick** from **current-bar (shift 0)** values. Z = (bid − SMA20[0])/SD20[0]. This repaints intrabar and cannot be reproduced exactly with OHLC bars.
- **MR (magic 777333):** entry when hour in [10, 20), ADX[0] < 20, spread ≤ 50, ATR14[0]/ATR50[0] in [0.5, 2.0], not near news, and |Z| > 2.4. Z < 0 → buy at ask, else sell at bid. SL 800 pts, TP 1500 pts. Management every tick: if |Z| < 0.2 and not yet partial, close 50% and move SL to entry ± spread; full close when Z ≥ −0.3 (long) / Z ≤ 0.3 (short). Bug: a long reaches Z = −0.3 before |Z| < 0.2, so the full close fires first and the 50% scale-out is effectively dead. Trailing on each new bar: SL = bid − 1.5·ATR[0] (ask + for shorts), moved only if it improves the SL by > 0.2·ATR. It has no activation threshold, so on the first bar it usually tightens the 800-pt SL to about 1.5 ATR.
- **TB (magic 777444):** evaluated on new bars only, when flat. Donchian = max High / min Low of bars 1..30. Long if ask > DonchHigh, ADX[0] ≥ 30, DI+ > DI−, |DI+ − DI−| ≥ 5, bid > EMA50[0], and ATR14/ATR50 ≥ 0.5. Short is the mirror (bid < DonchLow, DI− > DI+, ask < EMA). SL 1000 pts, TP 2000 pts, trail 2.0·ATR on each new bar (same 0.2·ATR step rule). Cooldown: 10 flat new bars after **any** TB close; the README says "after loss".
- Risk: MR uses the tier; TB uses 0.3 × tier. Separate magics, so 1 MR and 1 TB position can be open at once (both may be long). Daily loss limit by tier. News window 60/60.
- **README mismatch:** Breakout has **no Friday/weekend close**, although the README says it is shared.

## Other EAs
- **m1_OLHC** (magic 777333): Z from the closed bar, recomputed on each new bar. EntryZ 2.0 (+0.5 when ATR/avg100ATR > 1.5), and live Z must also be ≥ 90% of the threshold. Entry on ticks after a 3-tick or 2-second confirmation, plus a velocity block. Spread ≤ 12% of ATR and ≤ 1.5× the 20-tick average. ADX ≤ 25, H1 SMA50 filter. SL 800 / TP 1500. "Gravity" Z exit: 0.5 decaying by 0.1 every 5 min, reaching 0 after 15 min. Time exit at 30 min. Breakeven at 1.5·ATR + 50 pts → entry + 10 pts. Trail 2·ATR on each new bar (halved after 15 min). Writes a local trade-log file (FileOpen only, no network).
- **m1_EveryTick** and **IdealEA_1mOHLC.txt** are near-identical simpler copies: EntryZ 2.0, ExitZ 0.5, SL 800 / TP 1500, trail 2·ATR, max hold 30 min, H1 filter, no ADX.

## 8. Red flags
None found: no WebRequest, DLL, credential requests, obfuscation or paid links. The only concern is the very high default risk (10% per trade under $500).

## 9. Reimplementation (TickRobust, M1 bars; fills at the next bar's open)
```
at open of bar t (use bars ≤ t-1):
  m=SMA20(C)[t-1]; s=pstd20(C)[t-1]; z=(C[t-1]-m)/s; a=ATR14[t-1]
  if pos: if (long and z>=-0.2) or (short and z<=0.2) or held>=40: exit at open
          BE: if favorable excursion at open >= a: SL=entry±(spread+2pt)
          TP=max(m, entry+cost+5pt) (long) if closer by >=20pt
  elif 10<=hour<20 and not fri>=20/weekend:
     long if z<=-2.2 and C[t-1]>=C[t-2]; short mirror
     require ADX14[t-1]<=22, 0.4<=a/mean(ATR[t-50..t-1])<=2,
       s/pt>=3*cost, |m-fill|/pt>=4*cost, fill vs H1SMA50(prev closed H1)
     SL=max(800pt,2.5a); TP=m
  intrabar: SL/TP hit-check on H/L (SL first if both are hit)
```
