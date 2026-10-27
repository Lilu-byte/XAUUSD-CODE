# SiyabongaDlamini / SmartMoney.MQ5 (SmartMoney_MTF_EA_v2.mq5)

## 1. Author's claims (README, "CHOZEN TRADING SYSTEMS")
"Backtest Performance Highlights (XAUUSD - M1)":
- Deposit $10,000, net profit $4,330.13 (+43.3%), PF 1.20, recovery factor 1.70, 434 trades, "Win Rate: ~50%", expected payoff 9.98.
- **No test period stated.**
- The referenced `equity_curve.png`, `backtest_stats.png` and `correlation.png` are **not in the repo**. The badge "Performance-Proven" is a static shields.io image. The claims cannot be verified.

## 2. Timeframes
Runs on **M1** (entry TF), with M15 (middle) and H4 (higher). Its OnTick does not depend on the chart TF, but the README says attach to M1.

## 3. Defaults that matter
- Swings: SwingBars 5, MaxSwingLookback 150.
- Premium/discount: DiscountThreshold 0.5, Fib 0.618–0.786, RequireFibZone false.
- Sweep: lookback 20, confirm 1, wickRatio 0.5, closeRatio 0.4.
- Consolidation: 6 bars, 3.0 "pips" (pip = 10·point = $0.10, so $0.30).
- StructureLookback 15, RequireStructureShift false.
- Targets: Risk 1% of balance, MinRR 2, MaxRR 10, SL buffer 3 pips ($0.30), ExtendedTarget true.
- Trade management: Breakeven at 1R, Trailing from 2R with step 0.5 (× "initial risk").
- Limits: MaxSpread 30 pts, MaxDailyTrades 10, MaxOpenPositions 3, cooldown 5 M1 bars.
- Sessions on: London 08:00–17:00 and NY 13:00–22:00 (server time, end inclusive); Asia off.
- No news filter, no day-of-week rule, no Friday close.

## 4. Entry (once per new M1 bar, on its first tick)
Gates: spread ≤ 30; daily trades < 10; server time in [08:00, 22:00]; open positions < 3; ≥ 5 bars since the last entry.

**Swings (H4 and M15):** a 5/5 fractal over bars i = 5…149. A high is a swing high if it is ≥ the highs of the 5 older bars (strict >) and > the highs of the 5 newer bars. Element [0] is the most recent swing. The right side includes the forming bar 0, so the newest swing can repaint.

**HTF trend (H4):** compare the last two swing highs and lows. Priority order:
1. HH & HL → +1
2. LH & LL → −1
3. HH (low not higher) → +1
4. LH (low not lower) → −1
5. HL → +1
6. LL → −1
7. otherwise 0. Almost always nonzero.

**PD zone (M15):** Hi = max of all M15 swing highs in the window, Lo = min of all swing lows, mid = Lo + 0.5·(Hi − Lo).

**Uptrend (+1), needs mid-price ≤ mid**, then at least 2 of these 4 confirmations:
- **fib:** Hi − 0.786R ≤ price ≤ Hi − 0.618R.
- **sweep:** liqLow = min Low of M1 bars 2..21. Bar 1 has Low1 < liqLow and C1 > liqLow, and either (C1 − L1)/range1 > 0.4 or lowerWick/body ≥ 0.5. Bar 2 can never qualify, because it is inside the lookback.
- **breakout:** the 6-bar range of bars 1..6 ≤ $0.30, and the *bar-0* close > that range's high and > bar-0 open. At the first tick of a bar, close = open, so this is **effectively never true**.
- **structure:** the lowest low in bars 2..16 is more recent than the 2nd-lowest, Low0 and Low1 are both > that lowest low, and Low0 < mid.

**Downtrend (−1):** the mirror, with price ≥ mid. The sell fib zone is **asymmetric**: midpoint + [0.214, 0.382] × (Hi − mid), i.e. half the range.

**SL (buy):**
1. min(lowest Low of M1 bars 1..20, most recent M15 swing low).
2. If ask − M15low > 3·(ask − M1low), use the M1 low instead.
3. Subtract $0.30.
4. Cap the distance at 1.5% of price.

**TP:** entry + 2R. If a sweep was found and the 2nd-most-recent H4 swing high gives RR between 2 and 10, use that level instead.
Then require RR ≥ 2 and place a market order.

## 5. Exits (ManageOpenPositions runs **every tick**)
- `initialRisk = |open − currentSL|` uses the **current** SL, not the original one.
- BE: when profit ≥ 1·risk, move SL to open ± 2 pts.
- Trail: when profit ≥ 2·risk, set SL = price ∓ 0.5·risk, moving it only if it improves by > 5 pts.
- **Bug that drives results:** after BE, risk ≈ 2 pts, so currentRR is huge. The trailing stop then sits about 1 pt behind price and steps every 5 pts. In effect, once +1R is touched the trade is closed on the next small pullback, near +1R. Exits are therefore mostly −1R, about +1R, or a TP if it is hit in one move. That is consistent with "~50% WR, PF 1.2".
- Time exit: close losers after 48 h. There is no other time, EOD or Friday exit and no opposite-signal exit.

## 6. Sizing
lots = 1%·balance / (ticksAtRisk·tickValue), floored to step and clamped to the min lot. Up to **3 concurrent positions**, possibly in the same direction (pyramiding by repeated signals). No martingale or grid.

## 7. Code vs README
- The "Consolidation breakouts" feature is dead code (bar-0 close = open, and $0.30 is too tight for gold).
- "Max RR / extended targets" works only on sweep setups.
- README "Trailing ... once a specified RR is hit": implemented, but with the BE/initial-risk bug above.
- The newest swing can repaint because fractals use bar 0.
- Effective signals: sweep + structure, sweep + fib, or fib + structure, inside the discount half.
- No look-ahead in the backtest otherwise.
- The README's headline numbers and images are unverifiable.

## 8. Red flags
- No WebRequest, DLL, obfuscation or credential requests.
- Marketing tone: "Performance-Proven" badge, "institutional", "sniper entries", "© All Rights Reserved" with no LICENSE file, and missing report images. No paid links found.

## 9. Reimplementation (M1 bars + resampled M15/H4)
```
on open of M1 bar t (bar0 = O[t]; H0=L0=C0=O[t]):
  gates: spread<=30, trades_today<10, 8:00<=time<=22:00, npos<3, t-last_entry>=5
  H4sw = fractal5(H4 bars 5..149 back); trend = rule(H4sw[0],H4sw[1])
  M15sw = fractal5(M15 ...); Hi=max(highs), Lo=min(lows), mid=(Hi+Lo)/2
  long if trend==1 and px<=mid and count(fib,sweep,struct)>=2   # breakout≈0
  SL = min(minLow(1..20), M15sw.low[0]) (rule above) - 0.30$, cap 1.5% px
  TP = entry+2R or H4 prevSwingHigh if sweep and 2<=RR<=10
manage per bar (approximation of the tick logic):
  if H >= entry+1R: SL→entry (+2pt); then treat as exit ≈ entry+1R (or TP if it is in the same bar)
  losers open >48h: close
```
