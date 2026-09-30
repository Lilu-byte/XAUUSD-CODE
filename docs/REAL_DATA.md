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
  closest strategy anyway lost on every timeframe, so it is now **off by default** (`InpDemoTradeUnproven = false`; still on in `DemoTurbo`).
* **The next-candle forecast has no edge intraday:** 48.7-51.0% right on M5, M15 and H1 (a coin flip). The indicator's audit gate already hides
  the ghost candles when the forecast has not proven itself, which on intraday charts will be most of the time.
* **The most stable intraday rule on 10 years of H1:** the opening-range breakout with the classic exit, **+0.05R per trade over 1,146 trades,
  positive in 5 of 6 two-year blocks, but only 52% winners.** Its high-winner versions (67% winners) are break-even (+0.01R).
  The weak-close dip with the mean-revert exit was also positive in 5 of 6 blocks but only +0.005R.
* **On real gold, high win-rate and profit pull in opposite directions** for every strategy tested here. The tools can deliver either a 60%+
  win-rate at about break-even, or a small profit at about 52% winners (set *Strategy Lab: minimum % of winning trades* to 50).
