# The Strategy Lab: how the tools reach a 60% win-rate honestly

## The problem your screenshots showed
Your own terminal ran the old fixed strategy on real XAUUSD and reported it plainly:

| Chart | Trades | Won | Average per trade |
|---|---:|---:|---:|
| H1 (363 days) | 50 | 42% | -0.23R |
| H4 (1,356 days) | 28 | 39% | -0.25R |
| D1 (21 years) | 48 | 58% | +0.10R |

One fixed rule set does not suit every timeframe or every year of gold. So instead of shipping one strategy and hoping, the tools now **test many strategies on your chart's own history every day and use only the one that proved itself**.

## Two facts that shape everything
1. **Win-rate is mostly set by where the exits are, not by how clever the entry is.** In a market with no edge at all, a target half as far away as the stop wins about 67% of the time; a target as far as the stop wins 50%; a target 2.5x as far wins about 29%. The average result is the same in all three cases: zero minus costs. Measured here on pure noise (minute-level truth, 8,500 trades each):

   | Exit style | Won (no edge) | Won (trending market) |
   |---|---:|---:|
   | Classic: half at 1R, runner to 2.5R | 50.6% | 58.4% |
   | High-hit: 70% at 0.5R, runner to 1.5R | **66.7%** | **71.4%** |
   | Quick: everything at 0.6R | **62.7%** | **68.2%** |
   | Mean-revert: exit on the close back over the 5-bar mean | 52.0% | 53.3% |

2. **So a 60% win-rate is easy; a 60% win-rate that also makes money is not.** It needs a real edge in the entries. The Lab therefore demands both, every time: at least the target share of winners (default 60%) **and** a positive average result that survives a statistical margin.

## What is on trial (8 strategies x 4 exits = 32 combinations)
| Strategy | Entry rule (closed bar, never repaints) | Source |
|---|---|---|
| Confluence | Nine-module score (pullback, sweep, Asian breakout, squeeze, VWAP fade, divergence, FVG, round level, opening range) | Rounds 1-4 |
| Opening-range breakout | GOLD_ORB rules: settled first-hour range, close outside it, with the trend | GOLD_ORB port |
| RSI-2 dip in trend | Price on the trend side of the 200 EMA, higher timeframe not against it, RSI(2) below 10 (above 90 for shorts) | Connors RSI-2 |
| Double-7 dip in trend | Same trend rule, close below the lowest close of the last 7 bars | Connors Double 7s |
| Weak-close dip in trend | Same trend rule, close in the bottom 15% of a full-size bar and lower than the previous close | Internal bar strength (IBS) research |
| Stop-hunt reversal | Sweep of yesterday's / Asian / swing level that closes back inside, with the trend | ICT/SMC "Judas swing" |
| EMA pullback | Trend pullback to the 21 EMA with an RSI reset and a rejection candle | Classic trend following |
| Squeeze breakout | Bollinger squeeze or Asian-range breakout, not against the trend | Volatility breakout |

Each is combined with each exit style above. Every combination is traded through the history one trade at a time, with spread and slippage charged.

## How the Lab chooses (and why you can trust its record)
* **Every day** (server midnight) the Lab re-tests all 32 combinations on the last 10,000 closed bars before today. The indicator and the EA use exactly the same bars, so they always choose the same strategy.
* A combination **qualifies** when, over the whole window, it has at least 50 trades, won at least 63% (the 60% target plus a 3-point allowance for the drop-off that always happens out of sample), keeps a positive average even after subtracting one standard error, **and** was still profitable in the most recent fifth of the window.
* The best qualifying combination is used. If none qualifies, the EA **stands aside** on a live account (on a demo account it can trade the closest one, clearly labelled UNPROVEN).
* The record the panel quotes in AUTO mode is **walk-forward**: for each later fifth of the history, the choice is made using only the data before it, and only the trades after it are counted. That is the honest estimate of "let the Lab choose", not the flattering record of the best combination.

The selection rule itself was chosen by experiment (research/results/harness_results.txt), comparing five rules by a **live replay** that re-runs the Lab every simulated day exactly as the EA does:

| Rule (fresh seeds, 4 x 30,000 M15 bars per world) | Bull world | Trend world | No-edge world | Alternating world |
|---|---|---|---|---|
| First version (lenient) | 61% won, -0.01R | 61% won, +0.03R | traded 60% of days, -0.06R | traded 52% of days, -0.02R |
| **Strict (default now)** | **67% won, +0.05R** | **65% won, +0.10R** | traded 26% of days, -0.06R | traded 8% of days |

## What the live replay shows (synthetic markets: mechanics, not real gold)
3 seeds x 30,000 M15 bars per world, daily Lab on a 10,000-bar window, target 60%:

| World | Days a proven strategy existed | Trades/day | Won | Average | Profit factor |
|---|---:|---:|---:|---:|---:|
| Trending (clear edge) | 89% | 0.56 | **66.0%** | **+0.31R** | 1.88 |
| Steady bull (small edge) | 32% | 0.31 | **63.8%** | -0.02R | 0.94 |
| No edge | 7% | 0.05 | 74% (39 trades) | +0.10R, not significant | - |
| Mean-reverting | 5% | 0.04 | 55% (29 trades) | -0.18R | - |
| Alternating regimes | 4% | 0.04 | 64% (28 trades) | -0.05R | - |

Reading it:
* **When an edge exists, the system finds it and keeps above 60% winners with a real profit** (trend world).
* **When the edge is too small to pay the costs of quick exits** (steady bull), win-rate stays above 60% but profit is about zero. That is the price of the 60% requirement: in the same world the classic exit earned +0.10 to +0.15R per trade at about 55% winners. Lower *Strategy Lab: minimum % of winning trades* to 50-55 if you prefer profit per trade over win-rate.
* **When there is no edge, it mostly stands aside** (4-7% of days) instead of forcing trades. That is the most important property for an account.

## What the numbers on your screen mean
* **Scoreboard** (bottom right): the six best combinations on this chart, their win-rate, average result in R, number of trades, and PASS when they qualify. The arrow marks the one in use.
* **Main panel**: "Strategy: ... [PROVEN]" and "Tested here (walk-forward): 64% won, avg +0.08R, 120 trades".
* **Arrows on the chart** are the past entries of the strategy in use (green = proven, grey = unproven), with a tick or cross where each trade ended, so you can see its history at a glance.

## Limits (read before trusting any of it)
* The Lab measures the past. A strategy that passed can stop working; the daily re-test, the "still profitable recently" rule and the EA's loss limits exist for that day.
* The window is 10,000 bars: about 104 trading days on M15, 1.4 years on H1. Short windows mean fewer trades and wider uncertainty; the 50-trade minimum is the floor.
* Choosing the best of 32 combinations flatters in-sample numbers. That is why the walk-forward record, not the best cell's record, is what the panel quotes.
* Only real data can say whether real gold, on your broker and timeframe, contains an edge these strategies catch. See TESTING.md, and use `MQL5/Scripts/XAU_DataExport.mq5` to export your data so every test here can be re-run on it.
