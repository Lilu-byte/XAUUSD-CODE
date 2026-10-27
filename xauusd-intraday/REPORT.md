# XAUUSD: 5m / 15m / 30m / 1h / 4h strategies (13 Oct 2026)

## Bottom line

- **Best rule found:** be long gold only while the trend is up on *every* timeframe (fast EMA20 above slow EMA80 on M5, M15, M30, H1 and H4). Otherwise stay flat. Never short.
- On years it was not tuned on it beat holding gold on risk: 2024-07 to 2026-10, **21%/yr, worst drawdown 17%, Sharpe 1.57** vs holding **27%/yr, drawdown 28%, Sharpe 1.16**. In 2026 alone (when gold fell) it made **+19%** while holding lost 5%.
- **Big caveat:** this edge shows up only in 2022-2026. Tested the same way on 2006-2019 (OANDA) and 2016-2024 (MT5) with the timeframes that exist that far back (H1 + H4), it was no better than holding gold (Sharpe 0.21 vs 0.25, and 0.11 vs 0.35). Recent gold has trended unusually cleanly; a choppy market would likely erase the advantage.
- Bootstrap: about an 85-89% chance the Sharpe advantage over holding is real in 2022-2026, not proof.
- **Today (9 Oct close): FLAT.** M5, M15, M30 and H1 are up, H4 is still down.

## How it was tested

- Data: the MT5 export (bid candles, server time). Coverage limits everything: M5 only from May 2025, M15 from Jul 2022, H1 from 2016, H4 from 2013. M30 was built from M15.
- Costs: half the quoted spread plus $0.10 slippage per side, plus the broker's swap (long -12.6 pts/night, triple Wednesday). Doubling costs barely changes any result below.
- Rules were picked on training years and scored on later "test" years: test from 2024-07 for M15/M30/H1/H4, from 2026-01 for M5 (its history is too short for anything longer).
- Position sizes are 1x gold (long 1 = fully invested), so results compare directly to holding gold.
- Grid per timeframe: 15 rules (price vs EMA, EMA crosses, channel breakouts, z-score and RSI(2) reversion) x long+short / long only = 30.

## Part 1: each timeframe alone

| Timeframe | Rule picked on training years | Test Sharpe | Test return/yr | Test drawdown | Trades/yr | Holding gold (Sharpe / ret / dd) |
|---|---|---|---|---|---|---|
| M5 (test 2026) | EMA20/80 cross, long only | 0.87 | 16% | -16% | 516 | -0.02 / -5% / -27% |
| M15 | 100-bar breakout, long only | 1.61 | 23% | -14% | 77 | 1.16 / 27% / -28% |
| M30 | EMA50/200 cross, long only | 1.47 | 26% | -20% | 30 | 1.13 / 27% / -28% |
| H1 | EMA20/80 cross, long only | 1.38 | 24% | -14% | 39 | 1.11 / 27% / -29% |
| H4 | EMA10/40 cross, long only | 1.29 | 24% | -22% | 20 | 1.14 / 27% / -29% |

- Every winner was a **long-only trend** rule. All mean-reversion rules and nearly all long+short rules lost to holding.
- Each pick ranked 2nd-3rd of 30 in the test years (10th on M5), so training choices carried over, but only 4-7 of 30 rules per timeframe beat holding.
- M5 is the weakest: 500+ trades a year, very sensitive to costs and to the short sample.

## Part 2: all timeframes together

| Rule (M15 timeline, test 2024-07+) | Test Sharpe | Return/yr | Drawdown | Trades/yr | Time in market |
|---|---|---|---|---|---|
| **All 4 agree up, long only** | **1.57** | 21% | -17% | 84 | 35% |
| Vote-weighted, long only | 1.57 | 22% | -16% | 83 | 43% |
| All agree, long and short | 0.80 | 12% | -16% | 140 | 49% |
| H4+H1 up, buy M15 dips, exit on trend end | 1.01 | 14% | -18% | 29 | 45% |
| H4+H1 up, buy dips, exit on bounce | -0.08 | -1% | -17% | 225 | 18% |
| Holding gold | 1.16 | 27% | -28% | 0 | 100% |

On the M5 timeline (all five timeframes, test 2026): all-agree-up long only scored Sharpe 1.59, +19%, drawdown -8%; holding lost 5%. Shorting when all agree down helped in 2026 (+24%), but shorting lost in every longer test the project has run.

## Part 3: merging Part 1 and Part 2

| Merge (M15 timeline, test 2024-07+) | Test Sharpe | Return/yr | Drawdown | Time in market |
|---|---|---|---|---|
| **Single-timeframe picks, only while all timeframes agree up** | **1.78** | 23% | -14% | 33% |
| Majority vote of picks (3+ of 4 long) | 1.63 | 27% | -13% | 56% |
| 50/50 picks average + all-agree-up | 1.67 | 23% | -16% | 45% |
| Plain average of picks | 1.57 | 25% | -15% | 56% |

On the M5 timeline (test 2026) the first merge scored 1.60 and +19%; the majority vote and plain average dropped to 0.66-0.81.

- The merge with the all-agree filter is the top scorer, but it only adds a little over "all agree up" alone and was chosen after seeing 9 variants. Treat them as the same strategy.
- It is fractional (holds 0-100%), which a $3,000 account cannot do. The plain **all-agree-up** rule is all-or-nothing and can be traded with one 0.01 lot.

## On a $3,000 account

- One 0.01 lot is ~1 oz, about $4,200 of gold, so 1.4x the account. Results scale by about 1.4: roughly 29%/yr with a 24% worst drawdown on the 2024-26 test, and proportionally worse in a bad stretch.
- About 84 entries a year (1-2 a week), in the market ~35% of the time.
- Check the five trends at every 5-minute close (or M15 close if M5 is too frequent; the M15-based version scored about the same).

## What I'd do

1. Run **all-agree-up, long only, one 0.01 lot** on demo for a few months.
2. Keep the daily 200-day filter from STRATEGY.md in mind: both rules are trend following, and over 20 years trend following on gold has only roughly matched holding.
3. Don't trade M5 rules alone, mean reversion, or shorts: none held up.

## Files

- code/lib.py (data, rules, backtester), per_tf.py (Part 1), combo.py (Parts 2-3; `python3 combo.py 2` doubles costs), long_history.py (2006-2026 check), detail.py (quarters, bootstrap, today's state).
- per_tf_all.csv (all 150 single-timeframe results), combo_*.csv, long_history.csv.
- data/XAUUSD_M5.csv, data/XAUUSD_M15.csv copied from the MT5 export.
