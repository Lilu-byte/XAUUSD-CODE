# How to find out whether this works on *your* broker's XAUUSD

No number in this repository proves profitability. This protocol does. Do the steps in order and stop at the first failure.

## Step 0: read the indicator's Trial block
Attach `XAU_Oracle` to XAUUSD M15 (and try M5, H1). The **TRIAL** lines run the same signal rules, one trade at a time, over
the loaded history (default 6000 bars, about 2-3 months of M15).

| You see | Meaning |
|---|---|
| Fewer than ~30 trades | Too few to conclude anything. Raise *Bars analysed* or use a lower timeframe |
| Expectancy (Exp) <= 0 | On this data, the strategy loses. Do not automate it here |
| Exp positive but PF < 1.2 | Marginal; costs and slippage will likely erase it |
| Win% high but Exp small | Classic small-wins/large-losses shape; judge by Exp and PF |
| Module list: mostly negative | The market is not behaving the way these setups assume right now |
| "Direction call ... right" near 50% | The projection has no directional skill on this chart; treat ghost candles as range only |

The trial uses a pessimistic simulator (a bar touching both stop and target counts as stopped; measured bias roughly -0.1R
in a no-edge world), so a small positive number here is a better sign than it looks. Tick volume is used for VWAP and spikes.

## Step 1: Strategy Tester on real ticks
* Symbol XAUUSD, period M15, **Modelling: Every tick based on real ticks**, at least **2 years**, your real deposit and leverage.
* Inputs: `XAU_Sniper_Balanced.set`. Set the broker clock **manually** (*InpManualGmt* on, winter offset, and the daylight-saving mode that matches your broker).
* The calendar is unavailable in the tester, so the static 12:30/13:30 GMT window is used instead.
* Split the period: **first 70% in-sample, last 30% out-of-sample.** Look at the out-of-sample part last, once.

## Step 2: pass criteria (suggested minimums, on out-of-sample real ticks)
| Metric | Minimum | Why |
|---|---|---|
| Trades | >= 150 | Fewer means the result is mostly luck |
| Profit factor | >= 1.3 | Room for costs and drift |
| Expectancy | >= +0.15R per trade after costs | Below this, slippage and regime change decide |
| Max equity drawdown | <= 15% at 1% risk | Kill-switch default is 15% |
| Profitable months | >= 60% | Steady beats lucky |
| Largest single trade | < 20% of net profit | Not one lucky runner |
| Worst losing streak | Survivable at your risk | Use the Monte Carlo (RISK_MATH.md) with your measured win-rate |

## Step 3: robustness (a real edge degrades gracefully)
Re-run with:
1. Spread +50% (use the tester's fixed-spread override).
2. Different start dates (shift by 1, 2, 3 months).
3. `InpScoreMin` +/-0.2, `InpSLMinATR` +/-0.2, `InpTP1_R` 0.8/1.2.
4. Each module switched off in turn.

If profit exists only in a narrow band of settings or only in one period, it is overfit. Discard it.

## Step 4: optimisation, if you must
* Optimise at most 2-3 parameters at once, on the in-sample block only. Use the custom criterion (`OnTester`).
* Choose the middle of a broad **plateau**, not the highest peak.
* Verify the chosen set on the out-of-sample block. If it fails, the optimisation found noise.
* Re-optimising every few weeks is curve-fitting with extra steps. Don't.

## Step 5: demo forward test
At least **4 weeks and 30+ trades**. Compare with the tester: win-rate, expectancy, average slippage, spread paid. Live results
noticeably worse than the tester usually mean fills or spread the tester did not model.

## Step 6: going live
* Start at **0.25-0.5%** risk. Keep the daily/weekly limits and the kill-switch on.
* Scale up only after 100+ live trades with expectancy >= +0.1R after costs.
* Never raise risk to "catch up". The drawdown kill-switch exists for the day that the market stops behaving like your test period.

## Known limits of this toolkit
* Trend-following losses in mean-reverting markets are real (see IDEAS.md, stress worlds). Expect stretches of weeks that lose.
* Gating modules off from trailing results can make things worse (tested); it is off by default.
* Grade-based risk scaling has no supporting evidence; it is off by default.
* Tick volume is not real volume; VWAP and volume spikes are approximations.
* Daylight saving is modelled with the US or EU rule you select. If your broker's server clock follows neither, set *fixed* or the sessions can be an hour off for part of the year.
