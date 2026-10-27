# foeed/FvgGold-EA — FvgGold.mq5 v2.01

Source read: `FvgGold.mq5` (953 lines), `FvgGold.set`, `README.md`, `mql5_description.md`, `docs/robots.txt`.

## 1. Author's claims
- "XAUUSD.m, M15 timeframe, 0.01 lot, starting balance $10,000": 3-month (Apr-Jul 2026) +5.2%, WR 40.0%, 35 trades; **6-month (Jan-Jul 2026) +48.7% ($10,000 -> $14,874), WR 45.3%, 64 trades**. "R:R = 1.5 is optimal".
- **Arithmetically impossible at 0.01 lot**: a win is ~$6.75 (1.5 x $4.50 SL x 1 oz), so 64 trades cannot make +$4,874 (max ~ $430). Also inconsistent with "Min balance $10,000 for 0.01 lot". Treat numbers as unreliable.

## 2. Timeframes
- Execution/FVG/OB TF: `FVGTimeframe` = M15. ATR(14) on M15.
- HTF `HTF_Period` = H1: EMA(50) and EMA(200) on close; ATR(14,H1) only checked > 0.

## 3. Inputs (defaults = .set file)
MinGapSize 25 pts; MaxAgeBars 20; MinAgeBars 2; FVGBuffer 3.0 (price $); MinScoreFVG 50; weights Gap 30 / Disp 30 / HTF 20 / Fresh 10 / PD 10; UseOBFilter true; OB_ImpulseATR 1.5; OB_LookbackBars 50; OB_MinSize 10 pts; OB_ConfluenceBonus 20; OB_MaxDistance 200 pts; EMA 50/200; FixedLot 0.01; RiskPercent 0.5 (only if FixedLot=0); MaxTrades 1 (positions + pending); DailyLossLimit $5; ATR_TP_Mult 2.0 (unused while UseFixedRR); RiskRewardRatio 1.5; UseFixedRR true; UseKillzone true; KZ 7-10, 12-16, NY end 21; KZ_PreferOverlap false; CloseAtEOD false; Magic 7777; Slippage 20.

## 4. Entry rules (every tick)
Order per tick: daily P/L refresh -> manage BE -> EOD close -> if daily realized P/L <= -$5 stop -> detect OBs -> detect FVGs -> bias -> killzone -> place limits.
- **Bias**: H1 EMA50[0] vs EMA200[0] (forming H1 bar). +1 / -1; equal -> no trade.
- **Killzone**: `TimeGMT()` hour in [7,10) or [12,21) (the [12,16) overlap is a subset of NY [12,21)). NOTE: in the MT5 Strategy Tester `TimeGMT()` equals simulated server time, so the author's backtests used **server-time hours**. No day-of-week filter, no spread filter (only stop-level check).
- **FVG detection** (scan i = 3..29 on M15): c1 = bar i, c3 = bar i-2, middle = bar i-1. Bullish: low[i-2] > high[i] -> zone [high[i], low[i-2]]. Bearish: high[i-2] < low[i] -> zone [high[i-2], low[i]]. Gap >= 25 points ($0.25). Age = index of middle bar, must be 2..20 (so c3 is a closed bar; no look-ahead). Score computed **once, when first detected** (i.e. first tick after c3 closes):
  - gap: min(gap/ATR_M15[0], 1) x 30
  - displacement: |close-open|/(high-low) of the middle candle x 30
  - HTF: +20 if FVG type == bias
  - freshness: (1 - age/20) x 10 (age 2 -> 9)
  - PD: +10 if bullish and Bid < H1 EMA50[0], or bearish and Bid > H1 EMA50[0]
  - OB bonus +20 if any unmitigated same-type OB overlaps the zone or lies within 200 pts (bull: fvg.bottom - ob.top in [0,$2]; bear: ob.bottom - fvg.top in [0,$2]). "UseOBFilter = Require" is misleading: it is only a bonus.
  - keep if score >= 50.
- **OB detection** (i = 2..54): impulse = bar i with |body| >= 1.5 x ATR_M15[0]; OB = bar i+1 of opposite colour; zone = its body (min/max of open,close), size >= 10 pts. Bull OB invalidated when Bid < bottom; bear when Ask > top; pruned after 50 bars.
- **FVG invalidation**: bull zone removed when Bid < midpoint, bear when Ask > midpoint; removed when middle-bar time older than 20 x 15 min. Removed zones are **re-detected** on the next tick if still inside the scan window, so a zone can come back (and be re-traded once its previous order is gone).
- **Order**: only zones with type == bias, not yet ordered, and (positions + pending of magic) < 1, and no order/position whose comment contains "FVG_<middle-bar time>".
  - Buy limit: entry = bottom + 1.5, SL = bottom - 3.0, TP = entry + 1.5 x 4.5 = entry + 6.75. Requires Ask - entry >= stops_level*point + spread.
  - Sell limit: entry = top - 1.5, SL = top + 3.0, TP = entry - 6.75. Requires entry - Bid >= minDist.
  - SL distance therefore **always $4.50 (450 pts)**, independent of gap size. If gap < $3 the buy entry is above the midpoint (can be above the zone top).
  - Pending is GTC, **never cancelled** when the zone is mitigated/expired/bias flips (CloseAtEOD=false). A stale pending blocks all new trades (MaxTrades counts pendings).

## 5. Exits
- Fixed SL/TP as above (1.5R).
- Break-even: when Bid - open >= 0.5 x ATR_M15[0] (buy) and SL < open -> SL = open + 2 pts ($0.02); mirrored for sells. No trailing, no partials.
- CloseAtEOD (off by default): at GMT hour 21, minute 55 closes positions and deletes pendings.
- No opposite-signal exit, no Friday close.

## 6. Sizing
Fixed 0.01 lot. If FixedLot=0: risk 0.5% of balance over SL distance via tick value, capped at min(0.10, balance x 0.01) lots. One trade at a time; no hedge/grid/martingale.
Daily loss limit: realized deal profit+swap+commission since server midnight <= -$5 -> no new orders that day (with 0.01 lot ~2 losses).

## 7. Code vs README
- Largely matches README (scoring, killzone, 1.5R, BE 0.5 ATR, $5 daily limit). Differences: OB is a bonus not a requirement; README "Buy limit... entry = bottom + half buffer" correct; README says killzones in GMT but tester uses server time; pending orders not cancelled; FVG re-detection quirk.
- `OnTester` optimizes for win rate (profitable runs only) -> parameter set is WR-fitted.
- No look-ahead in detection. Uses forming-bar ATR/EMA values at detection time (approximate with previous closed bar in a bar backtest).
- Claimed returns inconsistent with 0.01-lot sizing (see 1).

## 8. Red flags
- No WebRequest, DLL, credentials or obfuscation.
- Heavy SEO / marketing: MQL5 Market listing (free, product 186778), YouTube clickbait "FREE ENTRY SIGNAL", landing page, keyword-stuffed README, contact@cybox.uk. Implausible return claims. Not a paid lure by itself.

## 9. Reimplementation notes
```
on each new M15 bar t (bar 1 = just closed):
  for i in 3..21 (middle age 2..20) detect FVG(c1=i, c3=i-2); if new & gap>=0.25: score once (ATR/EMA of last closed bar); keep if >=50
  intrabar (use H/L path): remove bull zone if bid<mid, bear if ask>mid; expire after 20 bars
  bias = sign(EMA50_H1 - EMA200_H1)
  if hour(server) in [7,10)∪[12,21) and realized_today > -5 and no position/pending:
     for zone with type==bias (oldest first): place limit at edge±1.5, SL edge∓3.0, TP 1.5R
  pending stays until filled (no expiry)
  on fill: BE to entry±0.02 when MFE >= 0.5*ATR14_M15
```
