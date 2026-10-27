# Can the pair trade more often without giving anything up? (17 Oct 2026)

David asked: "any way to have it trade more often without compromise?" I read "it" as the pair he is running, GoldAllAgree v1.10 plus GoldAsiaBreak v1.10, one 0.01 lot each. "Without compromise" here means more trades a day, with the pair's $ a day no lower and its worst drop no deeper. That has to hold on the recent data and on years the change wasn't tuned on.

## Short answer

**No.** I tested 1,332 ways to add trades. Every one either lowered the pair's $ a day, deepened its worst drop, or fell apart on the years it wasn't tuned on. Keep the pair as it is.

The pair already trades about 1.6 times a day on average. The reason it sometimes goes quiet is the reason it makes money. GoldAsiaBreak's edge is the day's **first** break of the Asian range, and later breaks don't carry it. GoldAllAgree makes its money from long holds while every timeframe points up, and it has been flat since 26 Aug because the H4 trend turned down. Extra trades built from the same price data come out close to a coin flip after costs. With $30-50 stops, each one adds more swing to the account than profit.

## The pair today (one 0.01 lot each)

| Window | $ a day | Trades a day | Worst drop (closed) | Worst drop (open trades counted) |
|---|---|---|---|---|
| **6 May 2025 - 9 Oct 2026, M5 (the numbers you've seen)** | **4.66** | **1.59** | **-$284** | **-$245** |
| Jul 2022 - Jun 2024, M15 (where every change was tuned) | 1.93 | 1.24 | -$313 | -$334 |
| Jul 2024 - Oct 2026, M15 (scored once) | 4.06 | 1.22 | -$298 | -$407 |
| Aug 2016 - Jun 2022, H1 (older check) | -0.88 | 1.04 | -$1,368 | -$1,394 |

A change passed only if it added at least 0.3 trades a day and kept all of these:
- at least $4.66 a day, with neither worst drop more than $10 deeper, on your window;
- at least $4.06 a day, with neither worst drop more than $10 deeper, on Jul 2024 - Oct 2026;
- positive on its own in both 2022-24 and 2024-26;
- not worse on 2016-22;
- direction better than 95% of random coin flips.

## What was tested

| Idea | Versions | Best result | Why it fails |
|---|---|---|---|
| More trades from GoldAsiaBreak: re-trade after a win, flip after a stop, a second range (00:00-06/07:00, 03:00-09:00, later ranges) | 127 | Second break after a win: 2.1 trades a day | The extra trades lose $0.68 a day on your window. Later breaks lost in 45 of 48 versions on 2022-24, and every range starting at 09:00 or later lost |
| New one-a-day breakouts from other sessions: London range broken in New York, New York opening range, US data release range, previous day's high/low, and fades of each | 768 | Fade of a failed break after the 15:30 US data: $4.95 a day, 2.4 trades a day | Worst drop -$303 (limit -$294); 2016-22 worse; direction no better than 90% of coin flips. Only 8% of versions made money even on 2022-24 |
| Trades only while both EAs are idle: New York first hour, London move at 15:30, H1 trend at a fixed hour, pullbacks | 180 | H1 trend at 17:00: $5.26 a day, 2.3 trades a day | Worst drop -$343; on 2024-26 the drop is -$373 and the stream makes $0.06 a day on its own; loses on 2016-22 |
| More trades from GoldAllAgree: faster averages, fewer timeframes, 3 or 4 of 5 agreeing, re-entry, a short-side copy, a faster long sibling | 257 | Re-entry while H1 and H4 stay up: same $4.66 a day, 2.1 trades a day, smaller drop on your window | On 2024-26 it lowers the pair to $3.54 a day and the open-trade drop to -$544. The short copy lost in all 49 versions on 2022-24. Every sibling that made money was long at the same time as the EA, the same bet doubled |

All four groups also scored every version on the later years afterwards, as a check and not to choose anything. The 2022-24 ranking didn't predict 2024-26 (rank correlations between -0.35 and +0.10). The handful of versions that would have passed on later years had all lost money on 2022-24.

## The closest trade-off, if you accept a deeper drop

**A second copy of GoldAsiaBreak with an $8 target**, on the same daily break, is the only extra stream that made money on every window from 2022 to 2026. It beat 99.5% of coin-flip directions on 2024-26:

| Window | Pair now | Pair + second copy (TP $8) |
|---|---|---|
| Your window, $ a day / trades a day | 4.66 / 1.59 | 5.99 / 2.48 (2025: 4.02, 2026: 7.67) |
| Your window, worst drop (closed / open trades) | -$284 / -$245 | -$487 / -$442 |
| Jul 2024 - Oct 2026, $ a day / worst drop | 4.06 / -$298 | 5.31 / -$386 |
| Jul 2022 - Jun 2024, $ a day / worst drop | 1.93 / -$313 | 2.95 / -$545 |
| Aug 2016 - Jun 2022, $ a day / worst drop | -0.88 / -$1,368 | -1.40 / -$2,381 |

It is the same bet twice: its daily result moves with GoldAsiaBreak's (correlation 0.79-0.87). The extra profit comes with a proportionally deeper drop, and on 2016-22 it loses more. It is a compromise, not a way around one. If you want it anyway, no new code is needed. Attach GoldAsiaBreak to a second XAUUSD chart with Take profit 8 and Magic number 20261016. The EA tracks its trades by magic number, so the two copies don't interfere. Demo first.

## If you meant the micro-scalper (GoldMicroScalp v1.30)

Its trade count is set by the spread limit and the session window. Loosening either adds trades at about the same loss each: every version in the 216-version v1.30 grid lost money. More trades there means losing faster.

## Files

- `code/harness.py`: copies of both EAs (checked trade for trade against their replays), the windows, and the scoring. `code/baseline.out` holds the pair's numbers.
- `asia-more/`, `sessions/`, `idle-time/`, `allagree-more/`: each group's code, grids, picks, results and `NOTES.md`.
