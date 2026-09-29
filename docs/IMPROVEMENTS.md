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
