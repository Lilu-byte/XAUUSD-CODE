# Results on your real XAUUSD data

Data: your broker's XAUUSD D1 history exported with `XAU_DataExport.mq5` on 30 Sep 2026: **5,730 daily bars, June 2004 to 29 Sep 2026**
(`research/data/XAUUSD_D1.csv`). Contract details from the same export: `research/data/XAUUSD_info.txt`.
Reproduce: `research/run_checks.sh` (writes `research/results/real_D1_results.txt`).

## 1. The sizing bug is confirmed by the broker's own numbers
The export reports `tick_value = 0.10` but `loss_1lot_10usd_move = -1000`. A 10 USD move on 1 lot loses 1,000 USD, so the true value of one
0.01 tick is 1.00 per lot: the broker's tick value is **10x too small**. v1 sized from the tick value (the "0.01 lot: lose 1.42" on your
screenshot was really 14.18). v2 sizes from the broker's profit formula, which gives the correct 1,000.

## 2. The Strategy Lab on 22 years of daily gold
Whole history, all 32 combinations, spread + slippage 0.30 per trade (today's level, so older years are charged more than they paid):

| Result | Won | Avg per trade | Trades |
|---|---:|---:|---:|
| **5 combinations pass** (>= 63% won, profit after 1 standard error, still profitable recently) | | | |
| RSI-2 dip in trend + Quick exit (today's pick) | 67.5% | +0.065R | 252 |
| RSI-2 dip in trend + High-hit exit | 71.3% | +0.051R | 251 |
| Confluence + Quick exit | 70.2% | +0.106R | 57 |
| Confluence + Classic exit | 61.5% | +0.336R | 52 |
| Double-7 dip + Mean-revert exit | 60.5% | +0.041R | 392 |
| Pattern-match forecast, walk-forward: next bar | 53.1% right | | 1,975 calls |
| Pattern-match forecast, confident 4-bar calls | 55.3% right | | 676 calls |

The forecast figures match the research (about 50-53% for the next bar): a real but small edge, strongest when the forecaster is confident.

## 3. Is it stable? Five-year blocks
| Strategy + exit | 2005-09 | 2010-14 | 2015-19 | 2020-24 | 2025-26 |
|---|---|---|---|---|---|
| RSI-2 dip + Quick | 74%, +0.16R | 73%, +0.15R | 65%, +0.01R | 62%, -0.03R | 58%, -0.03R |
| Weak-close dip + Classic | 49%, +0.05R | 53%, +0.05R | 54%, +0.01R | 56%, +0.13R | 56%, +0.27R |
| Double-7 dip + High-hit | 68%, +0.05R | 65%, -0.01R | 70%, +0.03R | 67%, +0.03R | 74%, +0.10R |
| Confluence + Classic | (2 trades) | 53%, +0.17R | 56%, +0.24R | 67%, +0.42R | 67%, +0.32R |

* The famous RSI-2 dip worked very well on gold until 2014 and has faded since. **Edges change**: that is why the Lab re-tests every day and
  insists that a strategy is still profitable in the most recent fifth of its window.
* The weak-close dip with the classic exit and the confluence strategy were positive in every block, at around 53-67% winners.
* High-winner exits (High-hit, Quick) give 60-75% winners in every block but only small profits per trade.

## 4. Live replay: choosing day by day as the EA would
Daily Lab on the previous N daily bars, then trading its pick (target 60% winners):

| Lab window | Period traded | Days a proven pick existed | Trades | Won | Avg per trade |
|---|---|---:|---:|---:|---:|
| 1,500 bars (6 years) | 2010-2026 | 58% | 161 | 57.8% | -0.05R (se 0.06) |
| 2,500 bars (10 years) | 2014-2026 | 48% | 103 | 62.1% | -0.04R (se 0.08) |
| 3,500 bars (14 years) | 2018-2026 | 27% | 28 | 64.3% | 0.00R (se 0.15) |

On daily bars the automatic choice is **about break-even with ~60% winners**. With only a few trades a month the samples are small and the
result is not significant either way. The main reason it is not better: the strategy that looked best on the whole window (RSI-2 dip) was
exactly the one that faded after 2014.

## 5. What this means for you
* **Daily charts:** no strong automatic edge. If you trade D1 by hand, the confluence signal and the weak-close dip were the most stable.
* **Intraday (where you actually trade, M5 to H1):** not tested on real data yet. That needs the M15 and H1 files from the same export folder.
* Nothing here changes the risk rules: the edges found are small, so risk per trade should stay small.

## 6. Intraday results (M5, M15, H1, H4 export of 30 Sep 2026)
Data: M5 Apr 2025 - Sep 2026 (100,148 bars), M15 Jun 2022 - Sep 2026 (100,000), H1 Jul 2016 - Sep 2026 (60,000), H4 Oct 2013 - Sep 2026 (20,000).
Full output: `research/results/real_{M5,M15,H1,H4}_results.txt`.

### Live replay: what the EA would have done, day by day
| Chart | Period traded | Days a strategy passed | Trades | Won | Avg per trade |
|---|---|---:|---:|---:|---:|
| M5 | Jun 2025 - Sep 2026 | 12% | 120 | 63.3% | -0.09R (se 0.07) |
| M15 | Nov 2022 - Sep 2026 | 15% | 371 | 58.2% | -0.02R (se 0.04) |
| **H1** | Apr 2018 - Sep 2026 | 33% | **514** | **64.4%** | **0.00R** (se 0.03) |
| H4 | Sep 2017 - Sep 2026 | 4% | 20 | 60.0% | -0.07R |
| "Always trade the closest" (demo option) | all four | - | 827 - 2,398 | 63-64% | **-0.04 to -0.06R** |

### Plain reading
* **The 60% win-rate target is met on real gold** (58-64% winners). **Profit is not:** the best case, H1, is exactly break-even over 514 trades.
* **Standing aside works:** trading only proven picks cut the loss from about -0.05R to about 0.00R per trade. The demo option that trades the
  closest strategy anyway lost on every timeframe, so it is now **off by default** (`InpDemoTradeUnproven = false`, renamed `InpDemoUnproven` in round 7; still on in `DemoTurbo`).
* **The next-candle forecast has no edge intraday:** 48.7-51.0% right on M5, M15 and H1 (a coin flip). The indicator's audit gate already hides
  the ghost candles when the forecast has not proven itself, which on intraday charts will be most of the time.
* **The most stable intraday rule on 10 years of H1:** the opening-range breakout with the classic exit, **+0.05R per trade over 1,146 trades,
  positive in 5 of 6 two-year blocks, but only 52% winners.** Its high-winner versions (67% winners) are break-even (+0.01R).
  The weak-close dip with the mean-revert exit was also positive in 5 of 6 blocks but only +0.005R.
* **On real gold, high win-rate and profit pull in opposite directions** for every strategy tested here. The tools can deliver either a 60%+
  win-rate at about break-even, or a small profit at about 52% winners (set *Strategy Lab: minimum % of winning trades* to 50).

## 7. Round 7: the demo screenshot of 30 Sep 2026, and ten more ideas tested on this data
### What the screenshot showed
| On screen | What it means |
|---|---|
| Balance 98.19, equity 66.15, open P/L -32.04 | The loss is two **manual** 0.01-lot sells at 4168.17 **without a stop loss** (price 4184). The EA's own record: 3 trades, 67% won, -2.94: the High-hit exit wins small and loses in full, and 3 trades say nothing yet |
| Margin level 79%, free margin -17.21 | No new trade can open (EA or manual) and the broker closes positions at its stop-out level. On 98 USD at 1:100, 0.01 lot of gold ties up about 42 USD of margin |
| EA panel "[DEMO - free run]", trading an **UNPROVEN** strategy | The attached copy still carried the old input values: MT5 keeps an attached EA's inputs when it is recompiled |
| Weekly chart "BUY NOW": 0.01 lot risks 246.65 USD = 514% of the account | The indicator only warned. It now says **TOO BIG, SKIP** and shows the balance the trade needs |
| Text cut off at the panel's right edge | MT5 cuts every text label after 63 characters. Panel lines now wrap |

**The account is too small for gold on any timeframe at a sane risk.** 0.01 lot of XAUUSD moves 1 USD per 1 USD of price. Typical stops at the
end of September 2026 (1.2-1.5 ATR over the last 200 bars):

| Chart | ATR | Typical stop | 0.01 lot risks, on 98 USD | Balance for 1% risk at 0.01 lot |
|---|---:|---:|---:|---:|
| M5 | 4.1 | 4.9 - 6.2 | 5.6% | about 550 USD |
| M15 | 7.9 | 9.5 - 11.9 | 11% | about 1,070 USD |
| H1 | 17.4 | 21 - 26 | 24% | about 2,350 USD |
| H4 | 39 | 47 - 59 | 54% | about 5,300 USD |
| D1 | 127 | 152 - 191 | 175% | about 17,000 USD |

### Ten ideas, screened on the older 60% of every file and checked on the newest 40%
`research/sim/ideas.cpp` (output: `research/results/ideas_{M5,M15,H1,H4}.txt`). Every signal of all 32 strategy/exit combinations is
simulated on its own (cost 0.30, cost guard off), then each filter keeps a subset. The ideas were written down before the first run.
Cells: change in average R per trade versus all signals, **older 60% / newest 40%**. All-signal averages were -0.084/-0.027 (M5),
-0.116/-0.017 (M15), -0.060/-0.018 (H1), -0.052/-0.011 (H4).

| Idea | M5 | M15 | H1 | H4 | Verdict |
|---|---|---|---|---|---|
| **Stop at least 20 round-trip costs** (cost <= 5% of the stop) | **+0.069 / +0.022** | **+0.086 / +0.010** | **+0.041 / +0.013** | -0.005 / +0.003 | **Adopted** (see below) |
| Buys only (gold's long drift) | +0.009 / -0.037 | +0.012 / +0.011 | +0.003 / +0.015 | -0.018 / +0.030 | Rejected: small, flips sign |
| Higher timeframe must agree (not just be neutral) | +0.003 / +0.021 | +0.015 / +0.003 | -0.007 / -0.004 | +0.002 / +0.027 | Not adopted: tiny, negative on H1 |
| Calm or busy market (ATR vs its reference) | +-0.02 | +-0.03 | +-0.01 | +-0.02 | Rejected: no effect |
| Day range used < 60% / >= 60% | -0.063 / +0.003 | -0.019 / -0.021 | +0.001 / -0.017 | +0.015 / -0.024 | Rejected (late-day dips slightly better on M5/M15 only) |
| Trending market (efficiency ratio >= 0.3) | +0.024 / -0.034 | +0.024 / +0.005 | +0.040 / +0.028 | +0.019 / -0.001 | Rejected: holds on H1 only |
| Entry 07-12 GMT (London) | -0.025 / +0.002 | -0.033 / +0.013 | +0.020 / -0.004 | -0.007 / +0.001 | Rejected |
| Entry 12-17 GMT (London/New York overlap) | +0.022 / -0.013 | +0.030 / -0.022 | -0.031 / -0.013 | -0.020 / -0.027 | Rejected |
| Entry 17-21 GMT (New York afternoon) | +0.017 / -0.001 | +0.040 / +0.008 | +0.026 / +0.070 | +0.011 / +0.081 | Promising on the dips, **not confirmed** by the replay (below) |
| Volume spike on the signal bar | +0.026 / +0.055 | +0.000 / +0.040 | -0.030 / -0.011 | -0.013 / +0.024 | Rejected: flips sign |
| Not Monday / not Friday | +-0.02 | +-0.01 | +-0.01 | +-0.01 | Rejected: no effect |
| 5-day / 20-day move agrees with the trade | +-0.02 | +-0.01 | +-0.01 | -0.02 / +0.05 | Rejected |

**Eight new entry rules**, traded one at a time through the same simulator (previous-day high/low breakout, previous-day low sweep, three lower
closes in an uptrend, close below the lower Bollinger band, 20-bar Donchian breakout, 50-EMA touch, RSI-2 dip with the higher timeframe agreeing,
weak close with less than 60% of the day's range used), each with all four exits on H1 and H4: **none was positive in both halves.**

**Asian-open drift.** On H1 the GMT hours 22 and 23 rose in both halves (t = 2.0 / 6.2 and 4.0 / 3.9). These are the first hours after the
daily break, when the spread is at its widest; the exported prices are bids, so part of the "rise" is the spread narrowing, which is exactly
what a buyer pays. Rejected as untradeable from this data.

### The cost guard inside the full EA process (daily Lab + trading, cost 0.35 = this broker's spread plus slippage)
| Chart | Proven picks only: before -> after | Won (after) | Every day, closest pick: before -> after |
|---|---|---:|---|
| M5 | -0.169R (59 trades) -> **-0.008R** (451) | 59% | -0.063R -> -0.017R |
| M15 | -0.023R (321) -> **+0.007R** (563) | 61% | -0.070R -> **+0.014R** |
| H1 | -0.063R (233) -> -0.049R (189) | 58% | -0.003R -> +0.005R |
| H4 | -0.060R (12) -> **+0.004R** (186) | 63% | -0.048R -> -0.023R |
| D1 | unchanged (daily stops are far above the guard) | | |

H4 uses a 6,000-bar Lab window, as in section 6; with 10,000 bars only 39 trades were left (43.6% won, -0.33R, se 0.13).

It helps on every timeframe because it stops paying 5-15% of every trade in spread. **It does not create an edge:** everything is now within
about +-0.05R of zero, with 58-63% winners. On 10 years of H1 the weak-close dip was the clearest beneficiary: with the High-hit and Quick exits
it now wins 64-68% of trades at +0.03R, positive in 4-5 of 5 two-year blocks (before: about -0.01R to -0.04R).

**New York afternoon window for the dips (second stage).** Combined with the guard, dips entered 17-21 GMT were positive in both halves on
M5 (+0.03R, 63% won) and H1 (+0.06/+0.08R, 65-66% won) when every signal is simulated on its own. Traded the way the EA trades (daily Lab, one
trade at a time) it did not hold: M5 -0.10R (73 trades), M15 +0.04R (100), H1 -0.01R (205). The window stays **off**; it remains available to
the research harness (`XAU_DIPWIN=17-21`).

**Win-rate target.** Raising the Lab target to 65% or 70% did not raise the live win-rate (61-67%) and did not improve the average.
The real-data win-rate is already 58-67% on every timeframe; what is missing is profit, and no filter tested here supplies it.

### Plain reading
* The files now stop the avoidable losses: spread (cost guard), oversized trades (account-fit check), margin calls (margin guard), trades
  without a stop (optional protection), and trading unproven strategies on demo (rehearsal mode).
* On real gold the result is still **about break-even with 58-65% winners**. A demo account cannot turn that into a guarantee: 45 days and
  3 trades carry no information, and even 200 trades have a standard error of about 0.07R per trade, larger than any edge measured here.

## 8. Round 8: "one perfect strategy", an EA that trades, better predictions
### What the screenshots of 30 Sep 2026 showed
| On screen | Cause | Fixed |
|---|---|---|
| The EA on H1 showed exactly the M5 result ("63% won, +0.06R, 350 trades") | MT5 keeps an EA's variables when the chart's timeframe changes; the EA kept the M5 Lab result | The EA and the indicator reset everything on (re)start |
| Scoreboard "PASS" but the panel said UNPROVEN | PASS used the plain 60% rule, the pick needs 63% and a profitable last fold | PASS now means exactly "can be picked" |
| Green box under a buy entry | The mean-revert exit's moving 5-bar mean was drawn as the target after price had fallen | The box ends at the strategy's typical winning exit; the moving exit level is a dotted line with its own label |
| Top lines of the indicator panel hidden | MT5's One Click Trading buttons cover the top-left corner | The panel starts below them when they are shown |
| EA idle | A manual trade was open (the EA did not trade while any position existed on the symbol); news pauses; nothing passed the Lab on 66-76% of days | Your trades no longer block the EA; see below for the rest |

### Mixing every strategy into one: a walk-forward meta-model
`research/sim/meta.cpp`: every signal of all 32 combinations becomes a candidate; a ridge regression on 22 situation features (per strategy
family) plus a term per combination, refitted daily on candidates that had already closed, takes the best candidate if its predicted result
beats a threshold. Cost 0.35, cost guard on. Average R per trade, older 60% / newer 40% (full tables: `research/results/meta_*.txt`):

| | M5 | M15 | H1 | H4 | Trades per day |
|---|---|---|---|---|---|
| Every signal, no model | | | -0.004 / -0.008 | | 1-2 (H1) |
| Combination average (a continuous Lab) | -0.042 / -0.025 | -0.002 / -0.010 | -0.035 / -0.001 | +0.001 / +0.016 | 0.3-5 |
| Ridge model, threshold +0.03R | -0.045 / -0.003 | -0.013 / -0.018 | -0.014 / -0.001 | -0.067 / -0.019 | 0.3-4 |
| Ridge model, 3 positions at once | | -0.009 / -0.009 | -0.015 / +0.005 | | up to 10 (M15) |

The model makes the EA trade often (1-10 times a day) at 52-60% winners and **about zero per trade**. The strategies' results cannot be
predicted from the situation at entry any better than by their own average. Not adopted.

### Well-documented gold effects, tested here
| Effect | Result | Verdict |
|---|---|---|
| First 30 minutes of New York predict the last 30 / the rest of the day (intraday momentum) | same direction 47.8-51.9% (M5 and M15) | none |
| Turn of the month | first 3 days: +0.02%/day vs +0.05% (2004-15), +0.13% vs +0.04% (2015-26) | flips, rejected |
| Daily trend, long/flat (close vs 200-day mean) | 9.0%/yr (Sharpe 0.59) 2004-15, 10.2%/yr (0.72) 2015-26 | real, but it is gold's drift: buy-and-hold made 10.5% / 13.5% |
| Daily trend, long/short (50 or 100-day mean) | -0.9% to -1.5%/yr 2004-15, +8%/yr 2015-26 | shorts cost money |

### Trading with the daily trend (`research/sim/drift.cpp`)
Every strategy with six exits (the four standard ones, a slow "rider" and a 3-day "swing") in three modes: no filter, only in the daily trend's
direction, buys only while the daily trend is up. The honest test of any selection: **choose the three best on the older half, then look at
the newer half**:

| Chart | No daily filter | With the daily trend | Buys only in a daily uptrend |
|---|---:|---:|---:|
| M5 | +0.083R | +0.033R | -0.025R |
| M15 | +0.016R | -0.009R | +0.012R |
| **H1** | +0.028R | +0.123R | **+0.163R** |
| **H4** | -0.030R | +0.066R | **+0.109R** |

On H1 and H4 buying only in a daily uptrend held up (H1 example: weak-close dip with the High-hit exit, 76% won +0.09R older, **71% won
+0.085R newer**, 279 trades). Caveat: the newer half (2021/22-2026) was a strong bull market, which flatters buying.

### The EA process with the new defaults (daily Lab, as the EA trades, cost 0.35)
| Chart | Defaults | Proven picks only | Won | Before this round |
|---|---|---:|---:|---:|
| M5 | no daily filter, 10,000-bar Lab | -0.008R (451 trades) | 59% | same |
| M15 | no daily filter, 10,000-bar Lab | +0.007R (563) | 61% | same |
| **H1** | **buys only in a daily uptrend, 25,000-bar Lab** | **+0.025R (164)** | **67%** | -0.049R (189), 58% |
| **H4** | **buys only in a daily uptrend, 10,000-bar Lab** | **+0.020R (151)** | **65%** | +0.004R (186), 63% |

With the longer Lab window a proven strategy existed on 57-58% of days on H1/H4 (before: 29-34%). Everything is still within about one
standard error of zero: better, not proven. Other combinations tried (daily filter on M5/M15, both-sides filter, 25,000 bars on M5/M15) were
no better or worse; they are listed in the research log, not adopted.

### Plain reading
* No mix of these strategies, no model and no filter found an intraday edge on real gold that survives costs.
* The one thing that held for 22 years is gold's upward drift. The files now lean on it where holding times are long enough to matter
  (H1 and above: buy only in a daily uptrend), which moved H1/H4 from slightly negative to slightly positive at 65-67% winners.
* The EA trades more because your trades no longer block it, the H1 Lab has a proven pick on more days, and three copies can run on M15,
  H1 and H4 at once (presets `XAU_Sniper_Multi_*`). It does not trade more by lowering its standards: every way of doing that tested here
  gave about zero per trade.
