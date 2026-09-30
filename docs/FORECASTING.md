# How the "next candles" work now, and how far to trust them

## What went wrong before
The first version projected candles from the trade-signal score plus a pull back toward the 21 EMA. That is a *trend-following
opinion*, and after a sharp spike it always said "fade it". Measured on the mean-reverting test world its 4-bar direction was right only
**36%** of the time (worse than a coin flip), and on the alternating world it was 51%. Your screenshots show the same thing: a $30 spike
followed by bearish ghost candles while price kept rising.

## The new forecaster: analog pattern matching
Instead of hand-picking candlestick patterns (the research says they mostly do not survive costs, see below), the engine describes the
current situation with **37 numbers** and finds the **25 most similar situations in the loaded history**:

| Group | What is in the description |
|---|---|
| Last three candles | body size, where the close sat in the range, upper and lower wick (engulfing, pin bar, inside bar, doji... all live in these numbers) |
| Trend and location | distance to EMA 21/50/200, EMA slope, RSI, trendiness (efficiency ratio), ADX, Bollinger squeeze, distance to VWAP, distance to yesterday's high/low, share of the day's range used |
| Time and context | hour of day, higher-timeframe trend, DXY/EURUSD proxy, volatility vs normal |
| The eight setup modules | the vote of each (pullback, sweep, breakout, squeeze, VWAP fade, divergence, FVG retest, round level) |

What happened after each of those 25 past situations gives the forecast:
* **Ghost candles** = the real future candles of the most typical neighbour, scaled to today's volatility and anchored on the live price.
* **Cone** = the 20th to 80th percentile of all 25 outcomes.
* **Direction and agreement** = how many of the 25 went up or down over the next 4 bars.

No look-ahead: only situations whose future was fully known *before* the current bar are eligible (tested: forecasts on truncated history are identical).

## The gate: it only shows candles when it has earned it
Every forecast is checked against the past, **walk-forward**: at each of ~250 earlier bars the engine forecasts using only what it knew then,
and the panel compares with what really happened. Directional candles are drawn only if all of these hold:
1. at least 62% of the neighbours agree and the median 4-bar move is at least 0.1 ATR (a "confident call"), **and**
2. confident calls on *this chart's* recent history have been right more often than a coin flip, with a safety margin
   (hit-rate minus half a standard error above 50%, and at least 25 such calls).

Otherwise you see only the grey range cone and a plain sentence: "no clear direction (13 up / 12 down)" or "leaning UP but NOT proven".

## Measured accuracy (synthetic data: shows the mechanism, not real gold)
5 seeds x 14,000 M15 bars per world; calls sampled every 3rd bar. Directional hit-rate:

| World | Next bar, all calls | Next bar, confident | +4 bars, confident | Old forecaster +4 bars |
|---|---:|---:|---:|---:|
| No edge (random walk) | 49.9% | 50.6% | 51.4% | 49.9% |
| Trending | 52.8% | 55.4% | 58.6% | 55.4% |
| Mean-reverting | 53.0% | 56.0% | 60.4% | **36.3%** |
| Alternating regimes | 51.2% | 53.6% | 56.4% | 51.2% |

* On pure noise it correctly scores a coin flip (no leakage).
* Where structure exists it finds it, and it does not depend on the market trending the way the old model did.
* The structure in those worlds is planted, so these numbers are flattering. **On real gold expect roughly 50-53% for the next bar**
  (published k-nearest-neighbour studies on financial series report 50.0-53.2% next-bar accuracy, consistent with efficient markets).
  Expect more from the *confident and proven* subset, and expect the gate to say "no reliable edge" often. That is the honest answer, not a bug.

## The second use: veto for trade setups
If the pattern match is confident and points *against* a setup, the setup is skipped ("pattern match disagrees"). A/B on the synthetic worlds
(composite expectancy per trade): trending +0.09R to **+0.12R**, alternating +0.04R to +0.05R, mean-reverting -0.56R to -0.50R, no-edge unchanged;
10-40% fewer trades. Small but consistent, so it is on by default (`InpPatternVeto`).

## What the research says (read before believing any candle predictor)
* Candlestick patterns on their own: studies on forex, futures and stocks find most patterns have no statistically significant edge and none
  survive realistic transaction costs. See, for example, [Predictive Power of Adaptive Candlestick Patterns in Forex (MDPI Mathematics)](https://www.mdpi.com/2227-7390/8/5/802)
  and [Profitability of Candlestick Charting Patterns (SAGE Open)](https://journals.sagepub.com/doi/10.1177/2158244017736799).
  That is why patterns are used only as *context features*, never as signals.
* k-nearest-neighbour analog forecasting: see [Fast Exact Nearest-Neighbor Learning for High-Frequency Financial Time Series (arXiv)](https://arxiv.org/pdf/2606.10219),
  [Applying k-nearest neighbors to time series forecasting (arXiv)](https://arxiv.org/pdf/2103.14200) and
  [Nearest-Neighbour Predictions in Foreign Exchange Markets](https://www.researchgate.net/publication/5022410_Nearest-Neighbour_Predictions_in_Foreign_Exchange_Markets):
  modest but real gains over random walk on some series; short-horizon direction stays near 50-53%.

## Honest limits
* No method predicts individual candles precisely. The candles are a *typical path*, the cone is the honest uncertainty.
* Accuracy depends on your broker's data and the current regime; the panel's numbers are measured on your chart and change with it.
* A library of ~6,000 bars (about 2 months of M15) is small. More history helps (`Bars analysed`).

## Round 8: measured on your real gold, and what changed
`research/sim/forecast.cpp`, last 3,000 bars of each export, every forecast made only from earlier bars
(output: `research/results/forecast_{M5,M15,H1,H4}.txt`).

**Direction.** The pattern match called the next bar right 48.0% (M5), 50.3% (M15), 50.1% (H1), 50.7% (H4) of the time; 4 bars ahead
49.1-52.8%. "Always up" scored 48-50% intraday and 53-56% on H4 (the bull market), the 21-EMA slope 48-53%. **Nothing here predicts
intraday direction**, so the chart only draws coloured candles where the pattern match has proven itself on that chart, as before.

**The range cone was too narrow.** It should hold the later price 60% of the time; the pattern-match cone held it only 51-55%.
It is replaced by a **calibrated cone**: the 20th-80th percentile of how far price really moved over the same number of bars in the
last 3,000 bars, scaled by ATR and the hour-of-day range profile. Measured on bars it never saw: **59-61% at every step on every timeframe**.

**Candle size.** Next-bar high-low, compared with the real candle:

| Model | M5 error | M15 error | H1 error | H4 error | within +-25% of the real size |
|---|---:|---:|---:|---:|---:|
| Pattern match (typical path) | 2.04 | 4.05 | 9.56 | 14.20 | 34-35% |
| ATR x hour profile | 1.73 | 3.34 | 8.28 | 12.83 | 40-44% |
| Recent ranges x hour profile (HAR-style) | 1.77 | 3.42 | 8.81 | 13.86 | 37-43% |
| **ATR x hour profile, median-corrected (now used)** | **1.66** | **3.11** | **7.73** | **12.21** | **43-48%** |

The error falls 14-19% against the old candles. On the chart, when there is no proven direction, each coming bar is drawn as a grey outline
exactly as tall as that bar is expected to be, inside the calibrated cone. The panel says, for example, "Next 3 candles: about 4.1 high each;
price 60% likely between 4180.2 and 4191.5", and "Next candle size: M15 ~7.9 H1 ~17.4 H4 ~39.4" replaces the "-- -- --" line.
