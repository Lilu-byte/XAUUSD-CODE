# GOLD_ORB: what it is, what was ported, what was not

Source studied: `GOLD_ORB-main.zip` (an MQL5 EA, "GOLD_ORB", by Ulysses O. Andulte; README, `GOLD_ORB.mq5`, `price_action.mqh`, risk/money/trailing
includes, a default input set and a test-case deck). The Alglib, Fuzzy and Stat folders are unmodified MetaQuotes standard-library copies.

## The strategy
An **opening range breakout** on XAUUSD H1:
1. At the daily open (broker server hour 1) the **first H1 candle** is the initial range (high and low).
2. On each following candle a side of the range is *extended* if the candle sets a new high (or low) with its body also beyond the range body; the extension restarts that side's counter.
3. A side is **final** once it has been quiet for 3 candles ("candle composition"). Only a final side can break.
4. Signal: a closed candle in the breakout direction whose **close is beyond the final level** (bullish above the high = buy, bearish below the low = sell).
5. At most one long and one short per day. Fixed stop 400 points, fixed target 1,200 points (3R), a trail that only engages near the target, 1% risk sizing.
6. **Spike guard**: if a candle's wick is more than 500 points ($5), the range uses the body edge instead of the wick.
7. **Virtual environment**: every signal is also simulated on paper; if real trading is paused (drawdown / loss streak) the paper trades keep running, and real trading can resume when the paper equity recovers.

## Evidence in the package
One backtest: XAUUSD H1, **2019-02-21 to 2020-01-01**, $1,000, 1:100, "Every tick based on real ticks", **zero-latency** execution.
Balance ends near $1,500 (+50%) but falls from about $1,150 to about $830 (roughly -28% peak to trough) between February and May, and most of its gains arrive in two bursts (June and December).
Its own readme says "Profitable on Bull Market". One strong year, ideal fills, no out-of-sample period: that is an illustration, not proof.

## Faults found in the original (so they were not copied)
| Fault | Effect |
|---|---|
| Drawdown block has no braces: `if(dd > limit) printf(...); execute_trade = false;` | With a non-zero drawdown input (the source file's default is 10) `execute_trade` is set false on every tick, so **real orders are never sent**; only the virtual ones run |
| `int OnInit()` returns the string `"Initialization Success"` | Wrong type; should return `INIT_SUCCEEDED` |
| Input `LossStreakCounter` and a function `LossStreakCounter(...)` share a name | Ambiguous / fragile |
| Fixed 400-point stop, 1,200-point target | 400 points was about 0.3% of a $1,300 gold price; today's ATR is several times larger, so the stop would be noise. Not portable |
| Trail 700 points behind price but SL only 400 points away | The trail cannot engage until price is almost at the 1,200-point target, so it does nothing useful |
| `MoneyManagement`: `tradeSize = (margin / stopPoints) / tickValue` | Ignores tick size; only correct when tick size = point |
| Range lines created with fixed names (`"My Line"`) every candle | Duplicate objects / clutter |
| Server-hour open hardcoded to 1 | Only right for New-York-close servers |

## What was implemented here
| From GOLD_ORB | In this project |
|---|---|
| Opening range: first candle(s) after the daily open | `ComputeOrb()` in the core: the first `orb_range_min` minutes (60) after `orb_start_hour` on the server clock; works on any timeframe up to H4 |
| Range extension + "candle composition" settle rule | Ported rule for rule: `orb_settle_min` minutes (180 = 3 H1 candles, scaled to the chart's timeframe); high and low sides settle independently; extension needs a new wick extreme **and** a new body extreme (0.10 tolerance) |
| Close-beyond-range breakout, 1 long + 1 short per day | Ported: bullish/bearish candle, close beyond the final wick level, first per side per session |
| Spike-wick guard | Ported, but relative to volatility (`orb_wick_atr` = 0.5 ATR) instead of a fixed 500 points |
| ORB alone as the strategy | **Solo mode** (`InpOrbSolo`): the ORB vote alone is a signal. Optional `InpOrbNeedBias` restricts it to the higher-timeframe trend |
| ORB as a module | Also the **9th module** of the composite score (weight 0.9), so it can combine with the other eight |
| Fixed points stop/target | Replaced by the project's ATR-scaled structural stop and R-multiple targets; preset `XAU_Sniper_GoldORB.set` uses a single 3R target and no partials to mirror the original |
| Range drawn as horizontal lines | One **opening-range box** on the chart with high/low labels, coloured by state (building / settling / FINAL) and a line in the panel |
| Virtual (paper) equity monitoring and resume | `CXPaper` ledger in the core: while a loss-streak pause is active the EA paper-trades the signals bar by bar (using the same simulator) and resumes when the last three paper trades are net positive and not all losses, or at the end of the day |
| 1% risk sizing, max drawdown stop | Already present (and stricter: kill-switch, daily/weekly limits) |
| Not copied | Alglib/Fuzzy/Stat libraries, hedging assumptions, fixed-point stops, the MA100 filter (computed but never used in the original) |

## A bug in *this* project found while porting the paper-trade idea
The loss-streak pause counted consecutive losses over 45 days of history. Once paused the EA takes no trades, so it could never win one to end the streak;
it stayed paused until the streak aged out. Fixed: the pause now ends at the end of the day, or as soon as the paper trades recover.

## Tests (research/sim/harness.cpp, scripted H1 days)
Range forms on the first candle; no signal while settling; long on a settled close above the high; second same-day long ignored; short allowed the same day;
an early breakout extends the range instead of signalling; the extended range must settle again; the spike wick is ignored; solo mode gives a full plan and the bias option rejects it
when the trend is neutral; the paper ledger resolves a winner and reports recovery correctly. On the no-edge world ORB solo is not profitable (no look-ahead).

## Simulated behaviour (synthetic worlds: mechanics, not real gold)
ORB solo on M15, 8 seeds x 30,000 bars, about 0.8-1.1 trades a day:

| World | Expectancy per trade | Reading |
|---|---:|---|
| No edge | -0.08R | Baseline (costs plus the simulator's pessimism); nothing leaks |
| Trending | **+0.20R** (win 58%) | Breakouts follow through |
| Mean-reverting | **-0.43R** (win 33%) | Breakouts are faded; the strategy's real risk |
| Alternating | -0.11R | Wins and losses cancel |

This is the same picture as the source's own "profitable on bull market": a breakout system needs the market to follow through.

## How to use it
* **Indicator:** leave *Module: opening range breakout* on. The blue box is today's range (grey building, light blue settling, bright blue final). Set *Daily open on the SERVER clock* to your broker's gold open (1 for New-York-close brokers).
* **EA, GOLD_ORB only:** attach to an XAUUSD **H1** chart and load `XAU_Sniper_GoldORB.set` (demo first).
* **EA, combined:** keep the ORB module on in the normal presets; it then votes together with the other eight.
* Check the broker's open hour: gold on most New-York-close servers reopens at 01:00 server time; if your chart shows the first candle of the day at another hour, change *Daily open*.
