# Session streams next to the pair (17 Oct 2026)

Family: new one-trade-a-day streams from other parts of the day, built like GoldAsiaBreak (fixed $
TP/SL, close at 22:45, one trade per stream per day), added next to GoldAllAgree + GoldAsiaBreak.

**Verdict: nothing passes. All 3 candidates FAIL.** The closest, a fade of a failed break of the
15:30 data-release range, adds 0.8 trades a day and +$0.30 a day on the pair window, but it
deepens the drawdown on the pair window (-$303 vs -$284) and on m15_test (-$326 vs -$298), and it
loses on 2016-22.

## What was tried (768 versions, all chosen on m15_train only)

- Engine `code/sessions.py`. With the Asian range (00:00-09:00, break, TP 5, SL 50) it reproduces
  `harness.asia()` trade for trade on M5, M15 and H1 (`code/check_engine.py`: 331 / 1025 / 2416
  trades, 0 differences).
- 16 setups:
  - London range 09:00 or 10:00 to 15:00, watched from 15:30 or 16:30; 09:00-15:30 watched from 15:30; 09:00-16:30 watched from 16:30.
  - New York opening range 16:30 + 15 / 30 / 60 minutes.
  - US data range 15:30 + 15 / 30 / 60 minutes.
  - Previous day's high/low, watched from 01:00, 09:00, 15:30 or 16:30.
- Each setup was run with 3 direction rules: break, fade (the opposite way at the first break), and fail (after the first break, wait for a close back inside the range, then trade against the break).
- Each of those was run with TP {3, 5, 8, 10} x SL {15, 25, 35, 50}, which makes 16 x 3 x 16 = **768 versions on m15_train**.
- Pre-registered pick (`code/grid.py`):
  - A version is eligible when it makes at least 0.30 trades a day and the pair plus the stream on m15_train has max_dd no deeper than -$323 and max_dd_mtm no deeper than -$344.
  - Versions are ranked by the stream's own $/day on m15_train, and the best of each family is kept.
  - The 3 best families go forward.
- h1_old was not used to choose anything. On H1, range starts round down to the hour, and range ends and start times round up.
- Only 58 of 768 versions (8%) made money on m15_train. That is the same base rate as the 12,600-version 5-a-day grid, so most of the "winners" are noise.

## Candidates (one 0.01 lot; M5 fixed $, M15/H1 scaled to price/4000)

| | PDHL >01:00 break, TP 10 / SL 25 | NY open 30m break, TP 5 / SL 35 | US data 15m fail-fade, TP 10 / SL 15 |
|---|---|---|---|
| m15_train alone $/day (trades/day) | +0.35 (0.78) | +0.35 (0.94) | +0.18 (0.69) |
| m15_train pair+ $/day, dd, dd_mtm | 2.29, -294, -321 | 2.29, -246, -250 | 2.11, -288, -315 |
| m15_test alone $/day | +0.01 | **-0.72** | +0.05 |
| m15_test pair+ $/day, dd, dd_mtm (base 4.06, -298, -407) | 4.07, **-424**, **-451** | **3.34**, **-468**, **-499** | 4.10, **-326**, -409 |
| pair alone $/day (trades/day) | **-0.33** (0.82) | **-1.19** (0.95) | +0.30 (0.80) |
| pair pair+ $/day, trades, dd, dd_mtm (base 4.66, 1.59, -284, -245) | **4.33**, 2.41, **-481**, **-497** | **3.47**, 2.55, **-335**, **-307** | 4.95, 2.40, **-303**, **-258** |
| pair+ worst month (base -119) | -234 | -176 | -143 |
| pair+ $/day without the stream's 3 best days | 4.25 | 3.43 | 4.87 |
| daily corr with the pair (pair window / m15_test) | 0.12 / 0.04 | -0.09 / -0.08 | 0.07 / -0.07 |
| h1_old alone $/day | -0.89 | -0.33 | -0.10 |
| h1_old pair+ $/day, dd (base -0.88, -1,368) | **-1.77**, **-2,769** | **-1.21**, **-1,871** | **-0.98**, **-1,586** |
| random-direction percentile, m15_test (200 runs) | 97.5% | **3%** | **90%** |
| tests a / b / c / d / e | no / no / yes / no / yes | no / no / no / no / no | no / no / yes / no / no |
| verdict | FAIL | FAIL | FAIL |

Bold marks a value that misses its pass line.

## Hindsight check (`code/diag.py`, not used to choose anything)

The same 768 versions were also run on m15_test and on the pair window, only to see whether the
training picks carry over.

- They don't. The rank correlation of $/day between train and m15_test is 0.08, and between train and the pair window it is 0.10.
- Of the 58 versions that made money on train, 16 stayed positive on m15_test, 9 on the pair window, and 2 on both.
- Even picking with hindsight, 7 versions meet (a) and (b). All 7 lost money on m15_train, so none could pass (c).
  - Most are fades of a failed 15:30 US-data break and London 10-15 fades at TP $3-8.
- The "fail" direction rule was the least bad on average: -$0.29, -$0.20 and -$0.15 a day on train, m15_test and the pair window. Break averaged -$0.45, -$0.44 and -$0.34; fade averaged -$0.62, -$0.48 and -$0.69.

## Files

- `code/sessions.py`: the engine and the setups.
- `code/check_engine.py`: checks the engine against the harness.
- `code/grid.py`: the train grid, which writes `grid_m15_train.csv` and `candidates.json`.
- `code/evaluate.py`: scores the candidates on all windows, writes `results.json`.
- `code/diag.py`: the hindsight check, writes `grid_all_windows.csv`.

Run any of them with `python3 -I`.
