# 20 ways to improve the code (round 2)

Status: **DONE** = implemented and tested in this round. **TESTED-OFF** = implemented, measured, no benefit, off by default.
**PROPOSED** = worth doing, not done yet (what it needs is stated). None is proven on real XAUUSD; see TESTING.md.

| # | Improvement | Status | Notes |
|--:|---|---|---|
| 1 | **Single-file build**: each program is one self-contained file generated from shared sources (`research/bundle.py`) | DONE | Fixes the `Include\XAU\XAU_Platform.mqh not found` compile error. Nothing to copy but two files |
| 2 | **ADR-used block**: no trend-continuation votes once 90% of the average daily range is used | DONE | Neutral within noise on synthetic worlds; removes late-day trades |
| 3 | **London-local session windows** (follow UK daylight saving) | DONE | Trade window 07:00-20:00 London time |
| 4 | **DST-aware server clock** (US-DST "New York close" servers, EU-DST, or fixed) | DONE | Boundaries unit-tested; removes the old "one offset for all history" limitation |
| 5 | **Self-calibrating forecast cone**: width from the model's realised one-step error | DONE | Replaces a hard-coded 0.63 x ATR assumption |
| 6 | **"No map" state**: no candles when efficiency ratio is low or volatility is spiking | DONE | Only the range cone is drawn, and the panel says why |
| 7 | **Bar-1 and bar-4 direction audits** shown separately | DONE | Trust the short horizon for entries, the longer for holds |
| 8 | **One position per symbol (any magic, manual too) + instance lock** | DONE | Prevents stacked trades from a second chart or EA |
| 9 | **Never-naked orders**: if a broker rejects stops on the market request, open, attach, and close at once if attaching fails | DONE | |
| 10 | **D1-against-trade halves the risk** | DONE | Needs 260+ D1 bars |
| 11 | **Realised-only daily loss option** | DONE | Off by default; the equity-based limit is stricter |
| 12 | **Efficiency-ratio regime weighting** (trend modules down in chop, mean-reversion down in strong trend) | TESTED-OFF | A/B on 4 synthetic worlds: no measurable benefit (e.g. mean-reverting world -0.45R to -0.43R), so it stays off |
| 13 | **Empirical probability per score bucket** from the trial, shown instead of a bare grade | PROPOSED | Needs a few hundred real trades per bucket to mean anything |
| 14 | **Real-yield (TIPS) filter** via an allowed `WebRequest` data source | PROPOSED | Gold's most consistent macro driver; needs a data feed and a URL allow-list |
| 15 | **Volatility-targeted sizing** (risk shrinks when ATR is in its top percentile) | PROPOSED | Smooths the equity curve; test on real data |
| 16 | **Walk-forward optimiser harness** on Strategy Tester XML output, choosing plateaus not peaks | PROPOSED | Needs real tester exports |
| 17 | **Live risk-of-ruin panel**: Monte Carlo of the EA's own closed trades | PROPOSED | `research/sim/montecarlo.cpp` is the core; needs 30+ live trades |
| 18 | **Anchored VWAP** from the London open, NY open and last swing | PROPOSED | Better mean-reversion anchors than a day-reset VWAP |
| 19 | **Trimmed-mean bar range** (ignore crash bars) as the stop scale after news spikes | PROPOSED | Idea from the reference; ATR inflates for hours after a spike |
| 20 | **Liquidity-pool targets**: equal highs/lows and PDH/PDL as take-profit targets instead of a fixed R | PROPOSED | Needs pool detection and a target-selection test |

Further candidates: M1 sub-bar simulation in the trial (removes the pessimistic tie-break bias), trade journal CSV with a weekly R report,
protect-profit move to break-even before red-folder news, an XAGUSD correlation vote, prop-firm rule pack (trailing drawdown, consistency).

## Round 3 (from live screenshots)
| # | Change | Status | Why |
|--:|---|---|---|
| 21 | **Analog pattern-matching forecaster** (37 features, 25 neighbours, medoid ghost candles, 20-80% cone) replacing the trend-score drift | DONE | Old model was 36% right in a mean-reverting world and faded every spike |
| 22 | **Walk-forward audit + confidence gate**: candles drawn only if confident calls have beaten a coin flip on this chart | DONE | Honest about when it has no edge |
| 23 | **Pattern-match veto** on trade setups | DONE (on) | A/B: small consistent gain, no harm on noise |
| 24 | **Green/red trade box** (risk zone red, profit zones green, labels, exit-by time) | DONE | Requested |
| 25 | **Simple panel** (5-7 lines) and optional detailed panel; EA panel likewise | DONE | Requested; the old panel was 25 lines of jargon |
| 26 | **Solid line styles**; removed the dotted vertical time-stop line | DONE | Dotted lines rendered as chains of diamonds |
| 27 | **Small accounts: show minimum-lot risk instead of refusing** in the indicator (still refuses in a live EA) | DONE | Manual traders need the number, with a warning |
| 28 | **Demo-unlocked EA**: guardrails only warn on demo accounts; stale kill-switch and equity peak cleared at start; up to 5 concurrent trades | DONE | The persisted kill-switch (tripped by floating loss on manual trades) locked the EA out |
| 29 | **DemoTurbo preset**: about 10x the trades at lower quality (simulated -0.06R to -0.10R vs default) | DONE | Lets you watch a live test flow |
| 31 | **Opening range breakout module + solo mode + range box** (ported from GOLD_ORB, ATR-scaled) | DONE | See GOLD_ORB.md; +0.20R trending / -0.43R mean-reverting in simulation |
| 32 | **Paper-trade ledger** that resumes trading after a loss-streak pause | DONE | Idea from GOLD_ORB's virtual environment |
| 33 | **Loss-streak deadlock fixed** (pause now ends at end of day or on paper recovery) | DONE | Bug in this project's earlier pause |
| 30 | **Analog-only trade signals** (a proven, confident pattern match as its own setup source) | PROPOSED | Needs an incremental analog cache: per-bar queries over the full history are too slow to backtest inside the indicator |

## Round 5 (screenshots of the live demo, and the 60% goal)
| # | Change | Status | Why |
|--:|---|---|---|
| 34 | **Lot sizing from the broker's profit formula** (OrderCalcProfit), tick value only as a fallback | DONE | The demo broker reports the XAUUSD tick value 10x too small: "0.01 lot, lose 1.42" was really 14.18. A live account would have been sized 10x too big |
| 35 | **Candle-path fills** in every trial | DONE | The old pessimistic rule understated results by ~0.1R per trade |
| 36 | **Four exit styles** (Classic, High-hit, Quick, Mean-revert) | DONE | Win-rate is mostly set by the exit |
| 37 | **Four new entry families** (RSI-2 dip, Double-7, weak close, trend-filtered ORB) | DONE | Documented high-win-rate methods |
| 38 | **Strategy Lab** with walk-forward record and strict qualification | DONE | Chooses per chart, per day |
| 39 | **Live replay** of the daily Lab | DONE | The faithful estimate of the whole system |
| 40 | **Scoreboard**, PROVEN badge, hold-time, money-based size | DONE | |
| 41 | **Panels that fit their text**, EA panel bottom-left | DONE | The screenshots showed both panels on top of each other and text running past the box |
| 42 | **Account-health warning** (no-stop trades, margin level) | DONE | |
| 43 | **Multi-timeframe next-candle line** | DONE | |
| 44 | **Data export script** and real-data mode in the harness | DONE | So real XAUUSD can be tested next |
| 45 | **Presets generated from the EA's own inputs** | DONE | They can no longer drift out of date |

## Round 7 (demo screenshot of 30 Sep 2026: "make the demo profitable")
| # | Change | Status | Why |
|--:|---|---|---|
| 46 | **Cost guard** in the engine (`min_stop_cost`, EA/indicator input *InpMinStopCosts* = 20) with its own reason "stop too short for the spread" | DONE | Real data: the spread took 5-15% of every short-stop trade; the guard lifted the EA replay on every timeframe |
| 47 | **Fixed tested cost** (*InpCostPrice* = 0.35) instead of 1.5x the spread of the moment | DONE | The Lab ran at server midnight, when the spread is widest, and the indicator and EA could test different costs and choose differently |
| 48 | **Account-fit status** in the indicator (TOO BIG, SKIP / NO FREE MARGIN) and no alert for trades the account cannot carry | DONE | Weekly chart: BUY NOW at 514% risk |
| 49 | **Demo rehearsal mode** (*InpDemoMode*), free run capped at *InpDemoMaxRiskPct* | DONE | The demo must behave like the real account it is meant to preview |
| 50 | **Margin level and spread checks** before every entry, in every mode | DONE | Margin level 79% on the screenshot |
| 51 | **Lot planning refuses a trade when free margin is <= 0** (it used to skip the margin check) | DONE | Bug: a negative free margin bypassed the margin cap |
| 52 | **"ACCOUNT TOO SMALL HERE"** status in the EA with the balance the trade needs | DONE | |
| 53 | **Optional stop for positions without one** (*InpProtectManual*) | DONE (off) | |
| 54 | **Panel text wraps** at MT5's 63-character label limit | DONE | Lines were cut off on the screenshot |
| 55 | **D1/W1 display**: hold time in days/weeks, "close by" as a date, no "day range used" | DONE | |
| 56 | **Idea screen** `research/sim/ideas.cpp` (discovery/holdout split, filters, new rules, session drift) wired into `run_checks.sh` | DONE | |

## Round 8 (screenshots of 30 Sep 2026: "trade on its own", "more precise", "one perfect strategy")
| # | Change | Status | Why |
|--:|---|---|---|
| 57 | EA and indicator reset their state on every (re)start | DONE | The EA kept the M5 Lab result after the chart was switched to H1 |
| 58 | Scoreboard PASS = eligible for the pick | DONE | PASS and UNPROVEN on the same screen |
| 59 | Mean-revert trade box redrawn (typical exit + moving exit line) | DONE | Green box under a buy |
| 60 | Panel below the One Click Trading buttons | DONE | Status lines hidden |
| 61 | `InpOneTradePerSymbol` default false | DONE | Manual trades kept the EA idle |
| 62 | Daily trend filter in the engine (`d1_mode`), `InpDailyTrend` = AUTO in both programs | DONE | H1/H4 improved in both the chosen-on-older test and the EA replay |
| 63 | Lab window AUTO (H1 25,000 bars) | DONE | More proven days, better H1 replay |
| 64 | Calibrated forecast cone and candle size (`CalibrateForecast`, `ForecastRange`) | DONE | Cone 59-61% instead of 51-55%; size error -14 to -19% |
| 65 | Presets for three EA copies (M15, H1, H4) | DONE | More trades from independent Labs |
| 66 | Research programs `meta.cpp`, `drift.cpp`, `forecast.cpp` in `run_checks.sh` | DONE | |

## Round 9
| # | Change | Status | Why |
|--:|---|---|---|
| 67 | Engine member `dn` renamed `d1n` | DONE | MetaEditor warning "declaration of 'dn' hides member" (1 warning in each program) |
| 68 | Offline checker uses -Wshadow and handles local string arrays | DONE | Catches that class of MetaEditor warning here |
| 69 | `SimulateTradeAt`: entry at any bar and price, limit fills handled | DONE | Needed to test precision entries honestly |
| 70 | Export script: 1-minute gold, related markets, US economic calendar | DONE | The only short-timeframe ideas left need that data |
| 71 | M30 replay, entries and short-term direction programs in `run_checks.sh` | DONE | |
