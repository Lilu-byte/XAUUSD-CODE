# Backtest: merged XAUUSD price action rules

## Update 13 Oct 2026: re-run on David's MT5 export (Aug 2016 to 9 Oct 2026)
Broker candles (GMT+3, D1/H4 as exported, H1 for the outcome walk), with the same scoring as below. **The edge from the OANDA test did not hold.**

| Rule set | Period | Setups | Win at 1R | Win at 2R |
|---|---|---|---|---|
| Baseline: every H4 close in the H4+Daily trend direction | 2019-03 to 2026-10 | 2,304 | 50.1% | 35.1% |
| Rules as written | 2019-03 to 2026-10 | 366 | 51.4% | 36.2% |
| Tuned (engulfing + H1 confirmation) | 2019-03 to 2026-10 | 103 | 50.5% | 33.0% |
|   tuned, grade A only | 2019-03 to 2026-10 | 22 | 59% | 32% |
| Tuned | 2016-08 to 2019-02 (overlaps the OANDA test) | 40 | 55% | 33% |

The tuned rules scored 31% and 25% at 1R in 2020 and 2021, and 55% to 71% in 2023 to 2026. That swing is what noise looks like on about 13 trades a year.

**Why the earlier result didn't carry over:** in the 2016 to 2019 overlap, only 3 of the roughly 30 to 40 setups from each feed fell on the same day. The OANDA H4 candles were built on different hour boundaries from the broker's, so a one-hour shift in where H4 candles start and end changes which candles qualify. A rule whose results depend on that shift has no stable edge.

**Walk-forward check on the MT5 data:** I re-tuned 288 combinations on 2016–2021 and tested them on 2022–2026. The best in-sample version (61% at 1R) scored 52.5% out of sample. Across all combinations, the in-sample and out-of-sample hit rates were slightly negatively correlated (-0.18). Picking a version on past data told me nothing about how it would do later.

**Conclusion:** this rule set, as a mechanical candle-pattern trigger, does not predict XAUUSD direction better than chance on 2019–2026 data, and it does not get near 80%. It still works for describing structure and levels, which is how CURRENT_READ.md uses it.

---

## Original test (OANDA data, 2006 to Feb 2019)

## Data
OANDA XAUUSD hourly bid/ask candles, March 2006 to 25 February 2019 (76,499 H1 candles), from QuantConnect Lean's public sample data. This was the only XAUUSD history reachable from the cloud environment; live feeds (Yahoo, Stooq, brokers) are blocked by its network policy. Mid prices were used; H4 and Daily candles were built from H1 aligned to the New York close (broker-style H4).

## How a setup is scored
Entry is the close of the confirming candle (or the H1 confirmation close in the tuned version). Then H1 candles are walked forward for up to 10 trading days:
- **Win at 1R** = price reaches entry + 1x (entry to invalidation) before touching invalidation.
- **Win at 2R** = same, with a target twice the risk.
- If one H1 candle touches both target and invalidation, it counts as a **loss** (conservative).
- Also reported: whether price was on the right side of entry 1 day and 5 days later (plain direction accuracy).

The tuning was done on 2006-2014 only (288 parameter combinations); 2015-2019 is the out-of-sample check.

## Results

| Rule set | Setups | Win at 1R | Win at 2R | Right side after 1 day |
|---|---|---|---|---|
| Baseline: every H4 close in the H4+Daily trend direction, no candle | 3,743 | 50% | 34% | 49% |
| Merged rules as written in the prompts (any rejection/engulfing, k=2 swings) | 509 | 54% | 37% | 52% |
|   of which grade A (with sweep) | 209 | 58% | 43% | 58% |
| **Tuned: k=3 H4 swings, engulfing only, H1 confirmation** | **122** | **66%** | **47%** | **60%** |
|   tuned, 2006-2014 (in-sample) | 74 | 64% | 46% | 61% |
|   tuned, 2015-2019 (out-of-sample) | 48 | 68% | 48% | 58% |
|   tuned, grade A (with sweep) | 29 | 73% | | |

Win rate vs target for the tuned rules (all years):

| Target | Win rate | Expectancy per trade (before ~0.03R spread) |
|---|---|---|
| 0.5R | 80% | +0.20R |
| 1R | 66% | +0.31R |
| 1.5R | 53% | +0.34R |
| 2R | 47% | +0.41R |
| 3R | 35% | +0.40R |

## What this says about the 80% goal
- The rules carry a real edge: 66% vs a 50% baseline at 1R, and it held on unseen 2015-2019 data (68%).
- 80% is reached only by shrinking the target to half the risk, which lowers profit per trade. Win rate on its own can be pushed to any number by moving the target, so expectancy (R per trade) is the honest score. The best expectancy here is at 2R: 47% wins, about +0.4R per trade.
- Plain direction calls (up/down after 1 day) top out near 60% for the best setups. Nothing in this test came close to 80% on direction.
- Findings that fed back into the rules: engulfing candles beat rejection/pin candles (bullish pins were the weakest, 50% at 1R); a liquidity sweep added roughly 6 to 10 points; requiring Daily agreement barely changed results but cut noise; the H1 confirmation close added the most.

## Caveats
- Small sample: about 9 tuned setups a year, so the 95% range on 66% is roughly 57-74%.
- Picking the best of 288 combinations flatters the in-sample number; the out-of-sample 68% is the figure to trust more.
- Data ends February 2019. Re-running on 2019-2026 data (an MT5 export) is the next check.

## Files
- `backtest/pa_backtest.py`: rules and scoring. `grid.py`: the parameter search. `final.py`: the tables above.
- `backtest/trades_tuned.csv`, `trades_default.csv`: every setup with entry, invalidation, grade and outcome.
