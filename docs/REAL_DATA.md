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

## 9. Round 9: more precise trades on M5, M15 and M30?
Programs: `research/sim/entries.cpp` (entry methods), `research/sim/shortfc.cpp` (short-term direction), the EA replay on M30 (built
from the M15 export) and on lower costs. Older 60% / newest 40% of each file. Outputs: `research/results/entries_*`, `shortfc_*`,
`real_M30_results.txt`.

### Entry methods (every signal of all 32 combinations, average R per signal, older / newer)
| Entry | M5 | M15 | M30 | H1 |
|---|---|---|---|---|
| **Market (next open, what the EA does)** | **-0.014 / -0.001** | **-0.002 / -0.004** | -0.050 / **+0.017** | **-0.022 / -0.009** |
| Limit 0.10 ATR better | -0.026 / -0.009 | -0.010 / -0.025 | -0.054 / -0.019 | -0.024 / -0.034 |
| Limit 0.25 ATR better | -0.016 / -0.021 | -0.019 / -0.024 | -0.024 / -0.014 | -0.020 / -0.027 |
| Limit 0.40 ATR better | -0.012 / -0.013 | -0.002 / -0.012 | -0.001 / -0.012 | -0.012 / -0.035 |
| Wait for a confirming candle | -0.018 / +0.003 | -0.033 / -0.012 | -0.003 / -0.007 | -0.003 / -0.003 |

A better price **lowered** the result in 18 of 24 comparisons, and in all 12 of the newer halves: the limit orders that fill are the trades
that keep going against you, and the ones that never fill are the winners that left without you (adverse selection). Waiting for a
confirming candle halves the trades; it was slightly better on H1 and M30 and worse on M15. The EA keeps entering at the next open.

### Can the direction of the next 1-6 bars be called? (M5, M15, M30)
Eleven ideas, each "traded" from the next open for 1, 3 and 6 bars at 0.35 cost: a candle over 1.5 ATR then reversal; big candle with
double volume then continuation; volume flow of the last 12 bars; trending/choppy regime from the variance ratio (momentum or reversal);
timeframes agreeing; following the London open's first 30 minutes; following New York's first 30 minutes; rejection of yesterday's
high/low; rejection of a $10 round number; inside-bar breakout; a logistic learning model refitted every day on the last 20,000 bars.

**Result: none beats the cost in both halves on any of the three charts.** Right-call rates 42-56%; the learning model is the most
consistent at 50.5-52.2%. After the 0.35 cost almost every idea loses money per call; the few positive cells appear in one half only,
with standard errors larger than the result. A 52% call on a $4-6 three-bar move is worth about $0.20, less than the spread.

**US jobs report.** On 49 first-Friday reports in the M15 file (2022-2026), following the 08:30-08:45 New York move until 09:45 was right
46.9% of the time and lost $1.90 per trade after cost.

### M30 and cheaper spreads (EA replay, proven picks only)
| Chart | Cost 0.35 (this broker) | Cost 0.25 | Cost 0.15 |
|---|---|---|---|
| M5 | -0.008R, 59% won | +0.017R, 66% | +0.005R, 68% |
| M15 | +0.007R, 61% | -0.005R, 64% | -0.002R, 64% |
| M30 | **-0.112R, 58%** | -0.035R, 64% | +0.009R, 67% |

A cheaper broker gives more trades and more winners (up to 68%) but still about 0R per trade. **M30 is the weakest short chart** at this
broker's cost; M15 is the best of the three, H1 (section 8) better still.

### Plain reading
On M5-M30 gold behaves like a fair coin plus a spread. Nothing tested here (21 entry and prediction ideas, cheaper costs, a learning
model) calls its direction well enough to pay the spread. What *is* predictable on short charts is **how far** price is likely to move
(the calibrated range and candle size of section 8); that is what the indicator shows. The remaining untested idea with a real chance,
markets that move before gold (dollar index, EURUSD, silver, US yields) and surprise in US data, needs data the export did not include:
the export script now saves them (1-minute gold, related markets, the US economic calendar).

## 10. Round 10: different mechanisms, not new settings
The question this round: every strategy so far predicted a direction from a price pattern and bracketed it with a stop and a target.
Are there **structurally different** ways to trade gold that do better? Audit of all rounds: [AUDIT.md](AUDIT.md).
Programs: `research/sim/mechanisms.cpp` (clock, fixes, gaps, cone, squeeze, overreaction, seasonality) and the EA replay (TREND mode).
Every rule and window was fixed before the run. Older 60% / newer 40% of each file; dollars per 0.01 lot after 0.35 cost and
0.50 / 0.20 swap per night (long / short). Outputs: `research/results/mechanisms_*.txt`, `real_H1_results.txt`, `real_H4_results.txt`.

### A. Mechanisms that hold gold by the clock, by an event or by the calendar
| Mechanism | What it does | Result |
|---|---|---|
| **Clock: long after the daily reopen / through Asia** | Buy at 01:30-02:00 server, sell 2-8 hours later; no pattern | H1 2016-2026: lost money in **9 of 11 years** (-0.2 to -0.4 $/trade); only 2025-2026 positive. Rejected |
| Clock: short New York 16:30-22:00 | "Gold falls in the West" | Lost 2017-2025 every year, won only 2026. Rejected |
| Clock: long or short London 10:00-15:00, long late evening | | Negative in the older half everywhere. Rejected |
| **London fixes** (30 min before/after 10:30 and 15:00 London) | Direction picked on the older half, tested on the newer | M5 (15 months): "short 30 min before the AM fix" positive in both halves (+$0.53 / +$1.18). M15 (4 years): the same window **lost** (-$0.32 / -$1.19). Rejected |
| **Weekend gap fade** | Fade Monday's gap back to Friday's close | Gaps filled within 8 hours only 15-48% of the time; lost in every file. Rejected |
| **Overreaction** (daily, 2004-2026) | Day after a 2-sigma day | After a big up day the next day rose slightly in both halves (+$0.54 / +$2.52, se 1.0 / 3.4): momentum, not reversal, and within noise. After a big down day buying lost. Not adopted |
| **Seasonality** | Months chosen 2004-2015, traded 2015-2026 | "Good" months +5.1 bps/day vs other months +3.5 (se 2.4 / 3.0): no difference. Friday the strongest weekday in both halves (+16.6 / +8.1 bps), but holding only Fridays pays the weekend. Not adopted |

### B. Trading the size forecast (the one prediction that works, section 8)
| Mechanism | What it does | Result |
|---|---|---|
| **Cone fade** | A close outside the 3-bar 20-80% cone: fade back to its median | Lost about the spread in both halves on M5, M15, H1 and H4 (e.g. M15 -$0.38 / -$0.58 per trade, 34,000 trades). Rejected |
| **Cone follow** | Same signal, trade the escape | M5-H1: lost about the spread. **H4, escape over 1 half-width: positive in both halves and both directions** (+$0.55 / +$4.14). In R: about -0.03R per trade in 2016-2019, +0.08R from 2020. The same trending years as TREND mode below: the same edge, not a new one. Promising, not adopted as a separate strategy |
| **Squeeze straddle** | Stop orders on both sides of a quiet 6-bar box, one cancels the other | M5 lost in both halves; M15 and H1 lost in the older half. H4 positive but within noise (+$0.32 / +$1.46, se 0.6 / 1.9). Rejected |

**On M5-H1, fading and following the same signal both lose about the spread.** That is what a fair coin with a spread looks like,
and it confirms section 9: the size of the next move is predictable, its direction is not.

### C. A different payoff shape: TREND mode (built)
Until now every exit took small profits often (60%+ winners) and accepted full-size losses. Round 10 adds two exits that do the
opposite: **Rider** (a third off at 1R, stop to entry, the rest follows a 3-ATR trailing stop for up to 5 days) and **Swing** (held
up to 3 days). Such exits win less often, so the Lab target for them is **50%**. In **TREND mode** every combination that passes trades,
one position each (up to 3, total open risk at most 3%), and on H1/H4 only buys while the daily trend is up. Overnight swap is charged.

EA replay, real data, daily walk-forward Lab exactly as the EA runs it (MULTI = TREND mode):
| Chart, Lab window | Mode | Trades | Won | Avg R (se) | Profit factor | Random-entry control (same exits and filter) |
|---|---|---|---|---|---|---|
| H1, 25,000 bars (EA AUTO), Oct 2020 - Sep 2026 | STEADY (60%, one pick) | 114 | 64% | -0.029 (0.066) | 0.91 | |
| H1, 25,000 bars | **TREND** | **676** | **57%** | **+0.107 (0.049)** | **1.25** | +0.064 (0.154), 114 trades |
| H1, 25,000 bars, at most 1 position | TREND | 298 | 54% | +0.054 (0.077) | 1.12 | |
| H1, 25,000 bars, at most 5 positions | TREND | 866 | 57% | +0.107 (0.042) | 1.25 | |
| H1, 10,000 bars | TREND | 654 | 58% | +0.118 (0.045) | 1.32 | -0.014 (0.120), 139 trades |
| H1, 25,000 bars, both directions with the daily trend | TREND | 872 | 57% | +0.082 (0.040) | 1.20 | |
| H1, 10,000 bars, no daily filter | TREND | 1,339 | 54% | +0.026 (0.031) | 1.06 | +0.024 (0.108) |
| H4, 6,000 bars | **TREND** | **529** | **57%** | **+0.140 (0.053)** | **1.34** | -0.060 (0.069), 369 trades |
| H4, 10,000 bars (EA AUTO) | TREND | 459 | 50% | +0.013 (0.053) | 1.03 | |
| H4, 10,000 bars | STEADY | 21 | 48% | -0.302 (0.173) | 0.44 | |
| M15, 10,000 bars | TREND | 1,837 | 57% | -0.040 (0.022) | 0.89 | |
| M5, 10,000 bars | TREND | 947 | 59% | +0.006 (0.028) | 1.02 | |

TREND mode, average R per trade by year (trades):
| Chart | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| H1, 25,000 bars | | | -0.09 (22) | -0.23 (31) | +0.08 (66) | **+0.20 (321)** | +0.04 (236) |
| H4, 6,000 bars | **+0.45 (55)** | -0.65 (12) | +0.04 (43) | -0.30 (11) | -0.29 (29) | **+0.13 (294)** | **+0.35 (85)** |

### Plain reading
* **TREND mode is the strongest result of the project**: about +0.1R per trade over 500-900 trades, t-statistic 2.2-2.6,
  on H1 robust to the Lab window (10,000 or 25,000 bars) and better with the daily filter than without.
* **It is a trend follower and earns in trending years.** H1's profit came from 2025; H4's from 2020 and 2025-2026. In quiet or falling
  years it trades little and loses a little. Expect long flat or slightly losing stretches.
* **On H4 it depends on the Lab window** (+0.14R with 6,000 bars, +0.01R with the EA's 10,000), so H4 is the less reliable of the two;
  H1 is the recommended chart. On M5 and M15 trend exits do not help: AUTO keeps those charts in STEADY mode.
* **Part of it is simply being long gold in a bull market.** The random-entry control with the same exits made -0.06 to +0.06R,
  so the Lab's choices add something, but the control samples are small and, on H1 with 25,000 bars, the gap is within noise.
* **Account size.** Trend exits use H1/H4 stops of about $20-60 per 0.01 lot. At 1% risk that needs about $2,000-6,000 per position,
  and TREND mode may hold three. On a $50-100 account each position would risk 20-100% of the account; the EA refuses such trades.

## 11. Round 11: supply/demand zones, sharper size forecasts, a stronger trend filter
Programs: `research/sim/zones.cpp`, `sizefc.cpp`, `enginefc.cpp` (the engine's own forecast code, new vs old) and the EA
replay with new options (`XAU_D1DEF`, `XAU_DAYS`, `XAU_DIAG`). Outputs: `research/results/zones_*`, `sizefc_*`, `enginefc_*`.
All rules fixed before the runs; older 60% / newer 40% of each file.

### A. Supply and demand zones (the popular "different types of entries" picture)
Zone = 1-3 quiet bars followed by a 2-ATR impulse; traded at its first return; stop beyond the zone, target 2R (a coin
flip wins about 33% at 2R). Net R per trade after 0.35 cost, older / newer:
| Entry | M5 | M15 | H1 | H4 |
|---|---|---|---|---|
| Limit order at the zone (most fills) | -0.22 / -0.17 | -0.22 / -0.07 | -0.20 / -0.19 | -0.15 / +0.04 |
| Engulfing candle in the zone | -0.04 / -0.16 | -0.19 / -0.01 | +0.07 / -0.03 | +0.09 / -0.15 |
| Retest after a break of structure | +0.07 / +0.12 | -0.10 / +0.02 | -0.21 / -0.08 | +0.24 / -0.19 |
| Point of control of yesterday's volume profile (1:1 back to it) | win 51% / 54% | 51% / 50% | 50% / 49% | |

The classic entry, a limit order at the zone, **lost on every chart**: the orders that fill are the zones that break.
Before costs every entry is within a few hundredths of R of zero: the zone does not tell where price goes. The retest
looked good on M5 only (15 months) and failed on M15 and H1. The point of control is not a magnet (49-54% to reach it first).

### B. Size forecasts (built)
| Forecast | Old method | New method | Error vs old (newer part, every year better?) |
|---|---|---|---|
| Next candle's high-low | ATR x hour profile x median | **HAR**: regression on the last 1, 6, 48 and 480 candles | M5 -9.6%, M15 -10.1%, H1 -5.2%, H4 -1.9% (every year) |
| Today's high-low, 2 hours into the day | 14-day mean | **14-day mean + range made so far, fitted** | M5 -4%, M15 -12%, H1 -12%, H4 -28% |
| same, 8 hours in | 14-day mean | same model | M5 -18%, M15 -26%, H1 -25%, H4 -43% |
| same, 14 hours in | 14-day mean | same model | -34% to -70% |
| Day range from yesterday / 5 / 22 days (HAR) | 14-day mean | | -7% (22 years of daily bars, better in 10 of 10 years); the intraday model above beats it |
| Weekday x hour profile (jobs Fridays, Fed Wednesdays) | hour profile | | -0% to -1%: not worth it |
| Self-correcting (conformal) cone | fixed 20/80% | | H4 coverage per year steadier (59-61%), but M15 fell to 58%: not adopted |
| Cone leaning with the daily trend | | | pinball loss unchanged (+-0.1%): the trend does not move the next 3 bars |
(Measured on the engine's own code by `enginefc.cpp`, with the history a chart really loads: 10,000 bars on M5/M15.)

### C. TREND mode structure (EA replay, 50% target, all passing combinations, swap charged)
What "daily trend up" means (buys only while it is true), MULTI = TREND mode, average R per trade (trades):
| Definition | H1, 25,000-bar Lab | H1, 10,000 | H4, 10,000 (EA AUTO) | H4, 6,000 |
|---|---|---|---|---|
| Close above its 200-day mean (rounds 8-10) | +0.107 (676) | +0.118 (654) | +0.013 (459) | +0.140 (529) |
| **Close above a RISING 200-day mean (new default)** | **+0.122 (722)** | **+0.119 (684)** | **+0.097 (714)** | **+0.105 (815)** |
| Close above the close of 12 months ago | +0.120 (776) | | +0.047 (680) | |
| Both of the first and the third | +0.132 (682) | | +0.069 (610) | |

The rising-mean rule wins where it was meant to: it stands aside in the choppy years (H1 2023: -0.23R became -0.07R;
H4 2021-2023 losses shrank) and makes H4 independent of the Lab window. By year with the new rule, H1:
2022 -0.09 (12), 2023 -0.07 (30), 2024 +0.10 (109), 2025 +0.19 (345), 2026 +0.06 (226).

Other structure tests (H1, 25,000-bar Lab unless noted):
| Test | Result |
|---|---|
| Lab target 40 / 45 / 50 / 55% | +0.051 (747) / +0.081 (727) / +0.107 (676) / +0.139 (506): a higher target trades less and a little better; kept at 50 (differences within noise) |
| STEADY both directions on days the trend is not up (regime switch) | -0.140R (72 trades). Rejected |
| More strategies passing = better trades? | H1: 1-2 passing -0.07R, 6-10 +0.17R; H4: 1-2 +0.05R, 3-5 -0.05R. No consistent pattern. Rejected |
| Lab's quoted win-rate vs the real one | H1: quoted 55-60% came true at 54-55%, 65%+ at 65-66%. **H4: quoted 55-65% came true at 43-54%.** Treat H4 win-rates on the scoreboard as 5-15 points too high |
| Random buys with the same exit and filter | H1 +0.04 / +0.01R, H4 +0.06R over 414-498 trades (deterministic: every London open while the trend is up). The Lab's picks: +0.10 to +0.12R. The Lab adds about 0.06-0.10R over simply being long, within about 1.5 standard errors |

### Plain reading
* The one thing that predicts gold better than before is **size**: the next candle's high-low (2-10% better) and today's
  range once the day is under way (12-43% better). The indicator and the EA panel use both now.
* Direction still cannot be called from patterns, zones or volume profiles: supply/demand zones lost like everything else.
* TREND mode's edge is mostly **being long gold while its 200-day mean is rising, and letting winners run for days**.
  The stricter definition of "rising" made it steadier (H1 +0.12R, H4 +0.10R, either Lab window). It is still a trend
  follower that earns in years like 2024-2025 and stands aside or loses a little in years like 2022-2023.

## 12. Round 12: the "Adaptive ST [FXC]" Supertrend indicator
The TradingView indicator from the user's screenshot, rebuilt from its panel: line = (high + low) / 2 -+ factor x ATR(10),
factor = 1.5 + 3.5 x the ATR's percentile rank over the last 100 bars (volatility 98 -> factor 4.93); flips on a close through
the line. Programs: `research/sim/supertrend.cpp` (traded on its own) and the EA replay with `XAU_STTRAIL` / `XAU_STFILTER`.
Rules fixed before the runs; cost 0.35, swap charged; older 60% / newer 40%.

### Traded on its own (R per trade, older / newer)
| Way of trading it | M5 | M15 | H1 | H4 |
|---|---|---|---|---|
| Buy and Sell labels, always in (stop and reverse) | +0.02 / -0.00 | -0.12 / +0.06 | -0.09 / -0.04 | -0.06 / -0.05 |
| Buy labels only | +0.16 / -0.11 | -0.04 / +0.16 | -0.05 / +0.14 | +0.00 / +0.17 |
| Buy labels only, daily uptrend (the EA's filter) | +0.16 / -0.23 | -0.02 / +0.18 | +0.06 / +0.10 (0.21 trades a day) | +0.05 / +0.11 |
| Classic Supertrend (10, 3), buys in a daily uptrend | +0.05 / -0.17 | +0.02 / +0.20 | +0.12 / +0.15 (0.16 a day) | -0.12 / +0.48 |
Flipping long and short as the labels suggest loses on H1 and H4 and is flat on M5. Buys only earn in the newer half (the
2025-26 bull market) and lose in the older half: the market's rise, not the indicator. The adaptive factor is no better than
the classic fixed one. TREND mode on H1 makes +0.12R at 0.47 trades a day, more than any of these.

### Inside the EA (TREND mode replay, 50% target, rising-mean filter)
| | H1 25,000 / 10,000-bar Lab | H4 10,000 / 6,000-bar Lab | M15 STEADY |
|---|---|---|---|
| Current EA | +0.122 (722) / +0.119 (684) | +0.097 (714) / +0.105 (815) | +0.009 (545) |
| Rider exit trails on the Supertrend line instead of 3 ATR | +0.116 (726) / +0.105 (700) | +0.050 (686) / +0.101 (808) | |
| Entries only while the line points the trade's way | +0.123 (487) | +0.139 (500) | -0.076 (226) |
As a trailing stop it is worse on every chart. As a filter it keeps the per-trade result on H1 with a third fewer trades
(2024 and 2026 turned negative), lifts H4 per trade with the same total profit, and hurts M15. **Not adopted**: nothing
improved everywhere. The code stays in the engine switched off (`st_trail`, `st_filter`), not exposed as an input, so the
test can be re-run.
