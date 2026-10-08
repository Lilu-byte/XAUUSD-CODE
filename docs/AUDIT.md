# Audit: what has been tried, what moved the needle, what was never explored

Written in round 10, after nine rounds of work. The question asked: *are the hypotheses tweaks to the seed, or different
mechanisms?* This page answers it honestly, using only results measured on the real XAUUSD export (2004-2026).

## 1. Every trading system is a choice on ten axes
| Axis | What the project did (rounds 1-9) | Never explored before round 10 |
|---|---|---|
| **Information** (what the decision is based on) | Gold's own candles: 9 pattern modules, 8 entry families, higher-timeframe trend, daily trend, hour of day, tick volume, a pattern matcher (kNN), two learning models | Other markets (dollar index, silver, yields, stock indexes), the size of news surprises, positioning (COT), options, order book, physical demand |
| **What is predicted** | Direction of the next bars; which of stop/target is hit first | **Size of the move** (round 8: worked); probability of touching a level |
| **Entry** | Market order at the next open | Limit and confirmation entries (round 9: worse) |
| **Exit / payoff shape** | Fixed brackets with partial profits: many small wins, full-size losses | **Trend riding: few big wins, held for days** (round 10) |
| **Holding period** | Minutes to 8 hours | **Days** (round 10); weeks to months (tested, not built: account size) |
| **Exposure structure** | One position at a time, one strategy | **A portfolio: every strategy that passes trades at once** (round 10) |
| **Timing structure** | Signal-driven | **Clock-driven**: fixed hours, fixes, weekend gaps (round 10: rejected) |
| **Selection** | Daily walk-forward Strategy Lab; a meta-model | (kept) |
| **Market** | XAUUSD only | FX pairs and indexes with finer lot sizes (needs data) |
| **Costs** | Spread and slippage, cost guard | **Overnight swap** (round 10) |

Rounds 1-9 moved along the first four rows only, and mostly along the first: new ways to read gold's own candles to call
direction. That is the "seed". Every variation of it (more patterns, filters, thresholds, learning models, better entries)
ended at the same place: 58-67% winners and about zero per trade after costs.

## 2. What actually moved the needle (real data, EA replay)
| Change | Kind | Effect |
|---|---|---|
| Cost guard: no stop shorter than 20 round-trip costs | Cost structure | M5 -0.17R to -0.01R, M15 -0.02R to +0.01R per trade |
| Daily trend filter, buys only in a daily uptrend (H1+) | Information (daily drift) | H1 -0.05R to +0.03R, H4 0.00R to +0.02R |
| **TREND mode: portfolio of all passing strategies + multi-day trend-riding exits + swap charged** | **Payoff shape, holding period, exposure** | **H1 +0.11 to +0.12R per trade (t 2.2-2.6, 650-680 trades, either Lab window), 57% winners. H4 +0.14R with a 6,000-bar Lab, but +0.01R with 10,000** |
| Account-fit, margin and spread gates | Risk | Stops the avoidable losses (oversized trades, margin calls) |

Everything else (about 250 ideas) was a tweak: no measurable effect, or an effect that did not survive the newer half of the data.

## 3. What round 10 tested: structurally different mechanisms
| Mechanism | Different because | Result |
|---|---|---|
| **Clock**: hold gold at fixed hours (after the daily reopen, Asian hours, New York, London) | No pattern at all: exposure by time of day. Documented as "gold rises in Asia, falls in the West" | Buying after the daily reopen lost money in every year 2016-2024 after costs and won only in 2025-2026; other hours no better. Rejected |
| **Benchmark fixes**: 30 minutes around the London AM/PM fixes | Flow-driven, not pattern-driven | One window positive in both halves of the 15-month M5 file, not on 4 years of M15. Rejected |
| **Weekend gaps**: fade Monday's gap toward Friday's close | Event-driven | Gaps filled within 8 hours only 15-48% of the time; fading lost in every file. Rejected |
| **Overreaction**: the day after a 2-sigma day | Daily, event-driven | Slight momentum in both halves (follow the big day), about 100 trades per half, within noise. Not adopted |
| **Seasonality**: month of year, weekday | Calendar | Months chosen on 2004-2015 did not beat the rest in 2015-2026. Fridays strongest in both halves; needs overnight holds. Not adopted |
| **Size forecast, traded**: fade or follow a close outside the calibrated cone | Uses the one prediction that works | Fade and follow both lose about the spread on M5-H1 (a coin with a spread). H4 follow positive in both halves, but only in the trending years 2020-2026: the same edge as TREND mode. Not adopted |
| **Squeeze straddle**: stop orders both sides of a quiet box | Direction-free | Lost on M5-H1; H4 within noise. Rejected |
| **Payoff shape**: trend-riding and 3-day exits | Positive skew instead of high win-rate | Strongest result in the project (above) |
| **Portfolio**: all passing strategies at once (1 to 5 positions tested) | Diversification across strategies | H1: 1 position 298 trades +0.05R; 3 positions 676 trades +0.11R; 5 positions 866 trades +0.11R. More trades at the same quality |

## 4. Honest limits of the one thing that works
* Its profit is concentrated in gold's strongest bull runs: **2025** on H1, **2020 and 2025-2026** on H4. 2021-2024 lost a little (few
  trades, the Lab stood aside most days). It is a **trend-following** system: it earns when gold trends and pays small amounts when it doesn't.
* On H4 the result depends on the Lab window (6,000 bars +0.14R, 10,000 bars +0.01R), so H1 is the chart to trust.
* A random-entry control with the same exits and the same daily filter made about zero (-0.06R to +0.06R), so the
  Lab's choice adds something beyond "being long gold". But the control samples are small (114-369 trades) and on H1 with
  the 25,000-bar Lab the gap (+0.107 vs +0.064) is within noise.
* The stops on H1/H4 are $20-60. At 1% risk per trade that needs roughly $2,000-6,000. **It cannot run safely on $50-100.**
* Swap was modelled at $0.50 per oz per night for longs. The EA and the indicator use the broker's real swap.

## 5. What is still unexplored, and what it needs
| Idea | Why it could matter | Needs |
|---|---|---|
| Dollar index / EURUSD / silver / US yields moving before gold | The only new *information* left for short timeframes | Run the export script (round 9 version) |
| Size of US data surprises (actual vs forecast) | Documented drift after surprises | The export's calendar file |
| FX pairs or a cent account | Lot granularity: a $100 account can risk 1-2% per trade | Broker details and data |
| Volatility-targeted sizing, equity-curve pauses | Smoother account curve (does not add edge) | Can be built now |

## 6. Round 11 addendum
* **Moved the needle:** size forecasts (HAR candle size 2-10% better; today's range 12-43% better once the day is under way)
  and a stricter definition of the daily uptrend (200-day mean must be rising): TREND mode H4 went from +0.01R to +0.10R at
  the EA's Lab window, H1 from +0.11R to +0.12R.
* **Did not:** supply/demand zones (three entry styles), the volume-profile point of control, a self-correcting cone, a cone
  leaning with the trend, a regime switch to STEADY in non-uptrends, Lab breadth as confidence.
* **What the controls say:** buying every London open while the trend is up, with the same exit, made +0.01 to +0.06R; the
  Lab's picks +0.10 to +0.12R. Most of the edge is the trend plus the exit; the Lab adds a little on top.
