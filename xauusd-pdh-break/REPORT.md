# XAUUSD_PDH_Break.rar review (18 Oct 2026)

David posted `XAUUSD_PDH_Break.rar` with no message. This is what it contains, what each EA does, and whether it would make money, scored the project's way: after spread $0.30 + slippage $0.10 + swap, against holding gold and against the GoldAllAgree + GoldAsiaBreak pair over the same window.

## What is in the archive

Four plain-text MQL5 source files, copied to `source/`. Nothing compiled (.ex5/.ex4/.exe/.dll), no DLL imports, no web requests, no file writes, no login or password handling. They look safe to compile. All four are by "El Gigante de Hierro", and three of them only send alerts unless you set `AllowDemoTrading = true`; even then they refuse to trade on a real account.

| EA | What it does |
|---|---|
| **XAUUSD_PDH_Break** (the file the archive is named after) | M15 or H1. Buys once a day when a bar closes above yesterday's high for the first time. Stop 1 x ATR, target 2 x ATR, closes after 32 bars (M15) or 24 (H1). Long only. |
| XAUUSD_Turtle_D1 | Daily Turtle: buy stop at the 55-day high, stop 2 x ATR(20), then trails at the 20-day low. Long only. |
| XAUUSD_EWMAC_H1 | Hourly trend score (EMA16 - EMA64, divided by volatility). Holds 0 to 4 units of 0.01 lot depending on how strong the uptrend is. No stop loss. Long only. |
| XAUUSD_FOMC_Follow | On Fed statement days, follows the direction of the 14:00-15:00 New York hour, trailing stop, out by 18:00 New York. |

## Bottom line

- **PDH Break doesn't make money worth having.** About break-even after costs: +$0.23 a day over 2022-2026 on M15, -$0.07 a day on H1 2016-2022. All its profit is from 2025-2026.
- **Adding it to the pair fails the project's "no compromise" test.** It lifts the pair from $4.66 to $5.15 a day (May 2025 - Oct 2026), but days with $5+ fall from 66% to 55% and the worst drop deepens from $245 to $279. In 2022-2024 it adds nothing.
- **The author's "+0.15R per trade over 508 trades" is a before-costs figure.** I get 510 trades and +0.22R without costs, but only +0.05R after $0.40 of spread and slippage per trade.
- **Of the other three, only EWMAC is worth a look, and it's too risky on $3,000.** It made $11.64 a day May 2025 - Oct 2026, but fell $1,570 (half the account) from 28 Jan to 4 Aug 2026 and lost money in 5 of 11 years. Turtle roughly ties holding gold and at its 0.5% risk setting can't trade on $3,000 at all. FOMC is break-even.
- **Advice: keep the pair. Don't add PDH Break.**

## PDH Break results (one 0.01 lot, after costs)

| Window | Data | Trades | $/day | Win rate | Worst drop | Pair $/day (same window) |
|---|---|---|---|---|---|---|
| Jul 2022 - Jun 2024 | M15 | 228 | 0.00 | 35% | -$46 | 1.93 |
| Jul 2024 - Oct 2026 | M15 | 282 | +0.41 | 39% | -$109 | 4.06 |
| May 2025 - Oct 2026 (pair window) | M15 | 165 | +0.49 | 39% | -$109 | 4.66 |
| Aug 2016 - Jun 2022 | H1 | 600 | -0.07 | 34% | -$179 | -0.88 |

Holding 0.01 lot of gold over the same windows: $0.97, $2.96, $1.87 and $0.12 a day.

By year at 0.01 lot (M15): 2022 -$5, 2023 +$15, 2024 -$74, 2025 +$198, 2026 +$109. H1 2016-2024 by year: -5, +10, -57, +35, +70, -120, -63, +40, +9; 2025 +$337, 2026 +$344.

Average win $9.02, average loss $4.55 (M15). Stops are 63% of exits.

Pair + PDH Break:

| Window | Pair $/day | Pair + PDH $/day | $5+ days | Worst drop (marked daily) |
|---|---|---|---|---|
| May 2025 - Oct 2026 | 4.66 | 5.15 | 66% -> 55% | -$245 -> -$279 |
| Jul 2024 - Oct 2026 | 4.06 | 4.46 | 68% -> 52% | -$407 -> -$364 (closed: -$298 -> -$331) |
| Jul 2022 - Jun 2024 | 1.93 | 1.94 | 69% -> 52% | -$334 -> -$348 |
| Aug 2016 - Jun 2022 (H1) | -0.88 | -0.95 | 63% -> 48% | -$1,394 -> -$1,502 |

Daily correlation with the pair is only 0.03-0.11, so it doesn't hurt much, but it barely helps outside 2025-2026.

### Things in the PDH code to know before running it

- `AllowDemoTrading` is false by default: it only pops up alerts. Set to true it trades, but only on a demo account; on a real account it never places an order.
- It risks 0.5% of balance ($15) per trade, sized by ATR. **On H1 it has skipped every trade since December 2025**, because the hourly ATR (about $20 now) means even 0.01 lot risks more than $15. On M15 it trades 0.01 lot at today's prices, but in the calm years 2022-2024 it would have traded 0.02-0.17 lot, which made 2024 lose $272 instead of $74.
- Its magic number (551515) differs from the pair's, so on a hedging account it could run next to them.
- A signal that gets skipped (spread too wide, balance too small) still uses up the day.

## The other three EAs (one 0.01 lot per unit, after costs)

| EA | Window | $/day | Worst drop | Holding gold (same size) |
|---|---|---|---|---|
| Turtle D1 | 2004-2026 | 0.44 | -$240 (closed trades) | 0.48 |
| Turtle D1 | May 2025 - Oct 2026 | 4.24 (3 trades) | -$219 | 1.87 |
| EWMAC H1, 0-4 units | Aug 2016 - Jun 2021 | 0.64 | -$535 | 0.15 |
| EWMAC H1, 0-4 units | Jul 2021 - Oct 2026 | 4.64 | -$1,570 | 1.76 |
| EWMAC H1, 0-4 units | May 2025 - Oct 2026 | 11.64 | -$1,570 | 2.13 |
| EWMAC H1, `Cap = 0.5` (max 0.01 lot) | May 2025 - Oct 2026 | 3.14 | -$735 | |
| FOMC follow | 2016-2026, 80 trades | 0.04 | -$80 | |

- **Turtle**: at the default 0.5% risk, the 2 x ATR stop is so wide that 0.01 lot already risks far more than $15. It would have placed no trade since 2005 on a $3,000 account (at 1% risk, none since 2019). At a forced 0.01 lot it only ties holding gold.
- **EWMAC**: it does better than holding the same average amount of gold, in both halves of the data (the half after the author's fitted divisor too), because it is flat 55% of the time and steps out of falls. But that's a rally-driven result. It holds up to 0.04 lot (about 5x the account), has no stop, lost money in 2016, 2018, 2019, 2021 and 2022, and its worst drop is half the account. The author's own header says the same ("lost money in 5 of 11 years. Promising only"). With the pair alongside it, the worst drop is about $1,600 at defaults or $800 at `Cap = 0.5`, against $284 for the pair alone.
- **FOMC**: 80 trades in 10 years, 45% winners, about $12 a year. At 0.5% risk it also skips a third of trades on $3,000.

## Caveats

- Everything here is replayed from bar data (M15 2022-2026, H1 2016-2026, D1 2004-2026 from David's MT5 export), not ticks. The M15 window is the only one with M15 data, so the author may well have tuned PDH on it; the 2016-2022 H1 check is the cleanest out-of-sample test, and it was slightly negative.
- New York times assume this broker's server clock is New York + 7 hours, which the export shows (the session opens at 01:00 server = 18:00 New York all year).
- The EWMAC replay uses the full history for its averages; the EA uses the last 2,000 hourly bars, which gives the same values in practice.

## Files

- `source/`: the four .mq5 files from the archive, unchanged.
- `code/pdh.py`: line-by-line replay of PDH Break; `code/score.py`: scoring against the pair and holding gold (output `results_pdh.txt`).
- `code/others.py`, `code/ewmac_check.py`, `code/ewmac_check2.py`: the other three EAs (output `results_others.txt`).
- `trades_M15.csv`, `trades_H1.csv`: every PDH Break trade at 0.01 lot.
