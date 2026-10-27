# Idle-time streams next to the pair (17 Oct 2026)

Family: one small bracket trade a day (TP $5-8, stop $30-50, close 22:45 server) on a second
intraday signal, taken only while the pair is idle (GoldAllAgree flat and GoldAsiaBreak with no
open trade). Each version was also run ungated.

**Verdict: nothing passes. All 3 candidates FAIL.** Each one deepens the pair's drawdown on
the pair window and on m15_test. Two of them lose money on the recent windows. The best, the
H1 EMA20/80 direction at 17:00, adds +$0.60/day on the pair window but is flat on m15_test
(+$0.06/day), loses on 2016-22, and only beats 84% of random-direction versions.

## What was tried (180 versions, all chosen on m15_train only; h1_old not used for choosing)

- `code/idle.py` holds the engine and signals. Fed GoldAsiaBreak's own entries, the bracket
  engine reproduces `H.asia()` trade for trade on M5, M15 and H1: 331 / 1025 / 2416 trades, all
  identical. See `code/check_engine.py`.
- Pair idle: a bar counts as busy for an EA when one of that EA's trades from `H.pair_parts`
  (same timeline) has entry_time <= bar open < exit_time.
  - Gate `entry`: skip the signal if either EA is busy at the fill bar.
  - Gate `strict`: as `entry`, and also close the stream at the open of the first bar where
    either EA is in a position, so the stream never overlaps the pair.
  - Gate `none`: ungated.
- 15 signals x TP {5, 8} x SL {30, 50} x gate {none, entry, strict} = **180 versions on m15_train**. The signals:
  - NY first half hour or first hour (16:30-17:00 / 16:30-17:30), traded with or against the move: 4
  - London session move 10:00-15:30, traded with or against at 15:30, minimum move $0 or $10: 4
  - H1 EMA20/80 direction at 11, 13, 15, 17 or 19:00: 5
  - Pullback to the H1 EMA20 in the H4 EMA20/80 direction (10:00-20:00), H4 alone or H4 + H1 agreeing: 2
- Pick rule, written into `code/grid.py` before it ran:
  - Only gated versions can be candidates.
  - A candidate must make > $0/day alone and >= 0.30 trades/day on m15_train.
  - Pair + stream on m15_train must keep max_dd no deeper than -$323 and max_dd_mtm no deeper than -$344.
  - The best of each family by its own $/day goes forward, top 3 families.
  - 5 versions qualified. The NY family had none.
- `code/evaluate.py` scores the picks once on every window, with H.score. It also runs 200
  random-direction versions on m15_test (same entry bars, TP/SL, gate, exits) and writes
  `results.json`.
- `code/diag.py` is a hindsight diagnostic only, not a selection step. It runs all 180 on the
  pair window and m15_test and writes `grid_all_windows.csv`.

## Training grid (m15_train; baseline pair $1.93/day, dd -313, mtm -334)
- Only 14 of 180 made money alone. NY: 0/48. H1 EMA: 2/60. Pullback: 2/24. London: 10/48.
- Mean stream $/day:
  - ungated: -0.55 at 0.86 trades/day
  - entry-gated: -0.35 at 0.46 trades/day
  - strict: -0.33 at 0.46 trades/day
- Gating halves the trades and so halves the losses, but the loss **per trade** is no better
  on m15_train: -$0.80 gated vs -$0.63 ungated. It is the same on m15_test (-$0.49 vs -$0.50).
  Only on the pair window is the gated loss per trade smaller (-$0.23 vs -$0.46).

## Candidates (one 0.01 lot; M5 fixed $, M15/H1 scaled to price/4000)

| | London 10:00-15:30 fade, TP 5 / SL 30, strict | H1 EMA20/80 at 17:00, TP 5 / SL 50, strict | Pullback to H1 EMA20 in H4 trend, TP 8 / SL 50, entry |
|---|---|---|---|
| m15_train alone $/day (tr/day) | +0.16 (0.50) | +0.03 (0.57) | +0.02 (0.31) |
| m15_train pair+ $/day, dd, mtm | 2.09, -290, -314 | 1.96, -296, -338 | 1.95, -305, -315 |
| **pair** pair+ $/day, tr/day, dd, mtm (base 4.66, 1.59, -284, -245) | **4.00**, 2.26, **-367**, **-400** | 5.26, 2.28, **-343**, **-298** | **3.97**, 2.09, **-387**, **-420** |
| pair alone $/day (tr/day), win rate | -0.66 (0.67), 79% | +0.60 (0.68), 84% | -0.69 (0.50), 76% |
| pair+ worst month (base -119) | -152 | -130 | -159 |
| pair+ $/day without the stream's 3 best days | 3.96 | 5.22 | 3.91 |
| daily corr with pair (pair / m15_test) | 0.04 / -0.01 | -0.08 / -0.04 | -0.09 / -0.06 |
| **m15_test** pair+ $/day, dd, mtm (base 4.06, -298, -407) | **3.26**, **-484**, **-587** | 4.12, **-373**, -404 | **3.35**, **-390**, **-437** |
| m15_test alone $/day | **-0.80** | +0.06 | **-0.71** |
| **h1_old** pair+ $/day, dd (base -0.88, -1,368) | **-1.25**, **-1,931** | **-1.43**, **-2,201** | **-0.97**, **-1,521** |
| h1_old alone $/day | -0.37 | -0.55 | -0.09 |
| random-direction pct, m15_test (200 runs) | **17%** (median -0.52) | **84%** (median -0.27, p95 +0.21) | **34.5%** (median -0.56) |
| tests a / b / c / d / e | no/no/no/no/no | no/no/yes/no/no | no/no/no/no/no |
| verdict | FAIL | FAIL | FAIL |

**Bold** marks a miss of its pass line. The table below gives the ungated twin of each
candidate for reference (these are not candidates):

| ungated twin | pair+ $/day, dd, mtm | m15_test pair+ $/day, dd, mtm | h1_old pair+ $/day, dd |
|---|---|---|---|
| London fade | 3.02, -472, -472 | 2.71, -511, -619 | -1.64, -2,529 |
| H1 EMA at 17:00 | 4.55, -382, -355 | 3.65, -377, -459 | -2.05, -3,163 |
| Pullback | 3.95, -421, -446 | 3.43, -497, -557 | -1.41, -2,205 |

On every window, the gated version did better than its ungated twin.

## Hindsight (`code/diag.py`, not used to choose anything)
- The rank correlation of stream $/day between m15_train and m15_test is -0.15. Between
  m15_train and the pair window it is -0.09. So the training years do not predict which
  version works later.
- 6 of 180 versions meet both (a) and (b) with hindsight: 5 are H1 EMA20/80 at 13:00 (TP 5,
  SL 30/50) and 1 is the NY first hour faded (TP 5, SL 30, entry gate). Every one of them
  lost $0.38-0.78/day on m15_train, so all fail (c). A rule that works only after 2024 is not
  "no compromise".
- Only 1 version made money on all of m15_train, m15_test and the pair window: the 17:00 H1
  EMA candidate above. It still deepens the drawdown on both recent windows.

## Conclusion
Gating by "pair idle" removes half the extra trades. It cuts the damage to the drawdown, but
it does not create an edge. Every second-signal bracket tested here is close to a coin flip
on m15_test. A 0.01-lot stream with a $30-50 stop and a ~80% win rate then adds enough noise
to push the pair's drawdown past the $10 slack, even when its average is slightly positive.
In this family I found no way to trade more often without that compromise.

Files: `code/idle.py`, `code/check_engine.py`, `code/grid.py` (writes `grid_m15_train.csv` and
`candidates.json`), `code/evaluate.py` (writes `results.json`), and `code/diag.py` (writes
`grid_all_windows.csv`). Run each with `python3 -I`.

## Re-check (17 Oct 2026, 15:55 UTC)
I re-ran `check_engine.py`, `grid.py` and `evaluate.py` from scratch:
- `grid_m15_train.csv`, `candidates.json` and `results.json` came out byte for byte the same.
- A separate check found no gated trade that starts while either EA is in a position.
- The two strict candidates never overlap the pair.
- The entry-gated pullback overlaps the pair on 40 of 187 trades on the pair window. That is expected, because its gate only blocks the entry.
- The 17:00 candidate's direction matches a fresh H1 EMA20/80 calculation on every trade.
