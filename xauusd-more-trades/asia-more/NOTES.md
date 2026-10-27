# More trades from GoldAsiaBreak's own rule (17 Oct 2026)

**Verdict: nothing passes. All 3 candidates FAIL.** None of the 127 versions met the pair-window
test (a), even when I looked back at all of them afterwards. One extra 0.01 lot with a $30-50
stop always pushed the pair's worst drawdown past the $10 slack the test allows. The only
extra trades that earned money on every recent window were a second position on the same
break (candidate D), and that just doubles the bet.

## Method
- `code/asia_more.py`: a copy of `harness.asia()` with extensions added (second range, re-arm,
  stop-and-reverse, separate TP/SL for the extra trades), plus `sim_fixed()` for the random-direction runs.
  `code/verify.py` shows that with every extension off it matches H.asia('M5'), H.asia('M15', scale=True) and
  H.asia('H1', scale=True) trade for trade (331 / 1025 / 2416 trades), and that sim_fixed matches the engine.
- `code/train_grid.py`: **127 versions scored on m15_train only** (`train_grid.csv`). Families:
  A re-arm (48), A2 re-arm with every trade's TP/SL changed (10), B stop-and-reverse (8), B+A SAR + re-arm (4),
  C second range as its own stream (54: 9 ranges x TP 3/5/8 x SL 30/50), D second position, same break,
  bigger TP (3). The selection rule was written in the script before it ran: best combined $/day per group,
  taking versions that held the drawdown first. Only 3 versions held it, all in family A.
- `code/evaluate.py`: the 3 picks scored once on pair, m15_test and h1_old (`results.json`). The 200
  random-direction runs on m15_test use the same entry times and TP/SL/exits.
- `code/hindsight.py`: a diagnostic only, not a selection step. It runs all 127 versions on pair and m15_test
  (`hindsight.csv`).
- I did not look at h1_old when choosing.

## What the training grid showed (m15_train, baseline pair $1.93/day, dd -$313 / mtm -$334)
- Re-arm, taking a fresh break after the first trade closes: the extra trades lost money in 45 of 48 versions.
  The "new day high/low" re-arm lost $0.05-1.82/day. The "back inside, then out again" re-arm was about break-even
  at best (+$0.05).
- Stop-and-reverse: about 0.03 trades/day, and the extra trades lost in all 8 versions.
- Second range: only ranges that end at 06:00-09:00 earned money. Ranges that start at 09:00 or later (09-12,
  09-13, 12-15, 13-16, 00-12) lost in all 30 versions. Best was 00:00-07:00 at TP $8 / SL $30 (+$1.48/day alone), but
  the combined drawdown was -$491.
- A second position at TP $8: +$1.01/day alone, combined drawdown -$545.

## Candidates (one 0.01 lot each; "combined" = the pair plus or with the candidate, H.score)

| | pair $/day | trades/day | max_dd | mtm dd | m15_train $/day (dd) | m15_test $/day (dd / mtm) | h1_old $/day (dd) |
|---|---|---|---|---|---|---|---|
| Baseline pair | 4.66 | 1.59 | -284 | -245 | 1.93 (-313) | 4.06 (-298 / -407) | -0.88 (-1368) |
| A re-arm once after TP, back-inside then out, TP3/SL30 | **3.98** | 2.09 | -289 | **-268** | 1.98 (-260) | 4.20 (-301 / -407) | **-1.03 (-1598)** |
| C 00:00-07:00 range from 07:00, TP8/SL30 | **4.51** | 2.52 | **-574** | **-529** | 3.41 (-491) | 4.77 (**-498 / -537**) | **-1.47 (-2385)** |
| D second lot on the same break, TP8/SL50 | 5.99 | 2.48 | **-487** | **-442** | 2.95 (-545) | 5.31 (**-386** / -416) | **-1.40 (-2381)** |

Candidate alone ($/day; A = the extra trades only):

| | pair | m15_train | m15_test | h1_old | random pct (m15_test) | corr with pair | pair $/day w/o its 3 best days |
|---|---|---|---|---|---|---|---|
| A | -0.68 (0.50 tr/day) | +0.05 | +0.14 | -0.15 | 97% | -0.05 | 3.95 |
| C | -0.14 (0.93) | +1.48 | +0.72 | -0.59 | 99% | 0.18 | 4.45 |
| D | +1.33 (0.89) | +1.01 | +1.26 | -0.52 | 99.5% | 0.35 (0.79 with GoldAsiaBreak) | 5.93 |

Checks (a pair / b m15_test / c alone > 0 on train and test / d h1_old / e random >= 95%):
- A: fails a ($/day 3.98, mtm dd -268) and d. Passes b, c, e. **FAIL**
- C: fails a, b and d. **FAIL**
- D: fails a (drawdown -487) and b (drawdown -386). Fails d. **FAIL**

## What looking back at all 127 versions showed (diagnostic only)
- On the pair window, 0 of 127 meet (a), and none meet both (a) and (b).
- 39 versions reach $4.66/day with +0.3 trades/day, but every one of them has a mark-to-market drawdown
  of -$273 or worse (the limit is -$255).
- Only 3 versions keep the drawdown within the limit, and their best is $4.35/day.
- The closest misses all lost money on m15_train. For example, the "new day high/low" re-arm makes +$0.73/day on the pair
  window but -$0.58/day on m15_train.

## Conclusion
GoldAsiaBreak's edge is its first break of the day. Later breaks the same day (re-arm), reversing after
a stop, and later-day ranges do not carry it. Earlier ranges and a bigger second target do carry it, but they
trade the same move with more size, so the drawdown grows about as fast as the profit. Within this family I
found no way to trade more often without that cost.
