# More trades from GoldAllAgree's trend rule (17 Oct 2026)

Family: change GoldAllAgree's rule, or add a sibling stream next to it, so the pair trades more often.

**Verdict: nothing passes. All 3 candidates FAIL.** Every candidate misses test (b) on m15_test:

- The re-entry change drops $/day to 3.54 and deepens the mark-to-market drawdown to -$544.
- The short mirror and the faster sibling push max_dd to -$380 and -$660.

On m15_train, no version of the trend rule added trades without also deepening the pair's
drawdown or cutting its $/day, with one exception. That one version (the re-entry change below)
was flat on the pair window and lost $0.51/day on m15_test.

## Method

- **Code**: `code/aa_more.py` is a cached copy of `harness.allagree()` with extensions: k-of-n
  agreement, per-timeframe EMAs, re-entry while "armed", cool-down, sibling stream, and
  random-direction runs. Run `code/verify.py` to check it.
  - With every extension off it matches `H.pair_parts` on pair, m15_train and h1_old (265 / 339
    / 301 trades).
  - It also matches `H.allagree(side=-1 / need=k / fast,slow)` on M5, M15 and H1. All runs show
    0 differences.
- **Versions** are written in M15 terms (M15, M30, H1, H4), as GoldAllAgree's "Use M5 = off"
  version runs on m15_train. `code/specs.py` maps each one to the other windows:
  - Pair window: M5 is added to every timeframe set.
  - h1_old: only the H1 and H4 members are kept.
- **Costs**:
  - A change to GoldAllAgree is priced like the EA replay: the bar's recorded spread. Its numbers
    are also given at the flat $0.30 + $0.10 a fill.
  - Added streams pay the flat $0.30 spread + $0.10 slippage a fill. That is scaled by
    price/4000 on M15 and H1.
  - Swap is as in the harness.
- **Selection**: `code/train_grid.py` scores 243 versions on m15_train only. The pick rule is
  written in the script's docstring, before the run. A version is eligible on m15_train when all
  of these hold:
  - E1: combined trades/day >= 1.36 (the +0.3 on M5, scaled to M15).
  - E2: combined $/day >= 1.93, and for a change also at flat cost.
  - E3: max_dd >= -323 and max_dd_mtm >= -344.
  - E4: own P&L > 0. For a change, "own" means the changed EA minus the EA.

  The pick in each family (change / short / sibling) is the eligible version with the best
  $/day. A family with no eligible version falls back to the rule stated in the script.
- **Diagnostics run after the picks were fixed** (they choose nothing):
  - `code/neighbours.py` scores 14 neighbours of the change pick on m15_train. 13 of them are new.
  - `code/mapping_check.py` covers the M5 and H1 mappings of the change pick. It scores 1 new
    version on m15_train.
  - `code/hindsight.py` runs all 243 versions on pair, m15_test and h1_old.
- **Versions scored on m15_train: 257** (243 grid + 13 neighbours + 1 H1 analogue).
- **Picks**: `code/evaluate.py` scores the 3 picks once on each window and writes `results.json`.
  For the 200 random-direction runs on m15_test, entry and exit times and costs are unchanged.
  Each run picks every trade's direction at random.
- I re-ran `verify.py`, `train_grid.py` and `evaluate.py` from scratch on 17 Oct 2026.
  `train_grid.csv` and `picks.json` came out byte-identical to the first run, and `results.json`
  value-identical.
- h1_old was not used for choosing.

## What the m15_train grid showed (baseline pair $1.93/day, 1.24 trades/day, dd -313, mtm -334)

| kind | versions | own $/day > 0 | held dd (E3) | median combined $/day, dd |
|---|---|---|---|---|
| faster EMAs / fewer timeframes / k-of-n (change/agree) | 106 | 6 | 9 | 1.24, -479 |
| re-entry while slow frames hold (change/armed) | 12 | 7 | 7 | 1.97, -309 |
| cool-down after exit (change/cool) | 4 | 1 | 4 | 1.90, -292 |
| short mirror, added stream | 49 | **0** | **0** | 0.73, -458 |
| long sibling stream (hold / handoff / free) | 57 | 23 | **0** | 1.79, -573 |
| short sibling while the EA is flat | 15 | **0** | **0** | 0.39, -475 |

**Faster EMAs on all four timeframes** (5/20 ... 15/60):
- Combined $/day fell to $0.99-1.46 and dd deepened to about -$400.
- 5/20 doubled trades/day (2.17) and lost $0.94/day.

**k-of-n** (letting 1 or 2 timeframes disagree): dd went to -$510 to -$700. That is the same
"more of the same bet" problem the coordinator found.

**Faster EMAs on M15/M30 only** (H1/H4 kept at 20/80):
- dd held at about -$290, but they lost $0.22-0.27/day net.
- Trades went up to 1.47-1.88 a day.

**Cool-down**: cuts trades, as expected (1.21-1.23/day), so it cannot meet E1.

**Short mirror**: lost in all 49 versions (-$0.49 to -$1.99 a day of its own on m15_train).

**Long sibling streams**: earned money in 18 of 19 "free" versions and 5 of 19 "hold" versions.
In both modes the sibling can be long at the same time as GoldAllAgree, so it doubles the trend
bet. dd ran -$408 to -$730 across all 57.

The "handoff" mode is the one that trades only while GoldAllAgree is flat: it exits when the EA
enters. It lost in all 19 versions. The hours when GoldAllAgree is flat are hours when a faster
long trend rule does not pay.

**Only one version met E1-E4**: the re-entry change, anchors H1+H4, fast M15 EMA5/20.
Its 13 neighbours on m15_train (fast EMA 3/12 ... 8/32, anchors H1+H4 or M30+H1+H4) gave
$1.83-2.23/day. Most held dd within about $10 of baseline, so it was not a lone spike on train.

## Candidates (one 0.01 lot; pair window fixed $, M15/H1 scaled to price/4000)

**A. Re-entry change to GoldAllAgree** (anchors H1+H4, fast M15 EMA5/20).

- **Pair window**: the re-entry needs M5 + M15 EMA5/20.
  - Change own $/day: -0.00 (2025 +0.65, 2026 -0.55).
  - Changed EA alone: 3.61 $/day, 1.23 trades/day.
  - At flat $0.30 + $0.10 costs the changed pair makes 4.17/day vs 4.38 for the base pair.
- **h1_old**: the change does nothing there, because H1+H4 are the whole rule. The trades are
  identical.

**B. Short mirror stream** (M15+M30+H1+H4, EMA8/32).

- Picked by the fallback: no short version was eligible.
- The pair window gain comes from 3 days in March and June 2026.

**C. Faster long sibling, "hold"** (M15+M30+H1+H4 EMA15/60, enters only while GoldAllAgree is flat).

- Picked by the fallback: no sibling version was eligible.

| | Baseline pair | A. Re-entry change | B. Short mirror stream | C. Faster long sibling, "hold" |
|---|---|---|---|---|
| **pair** combined $/day, tr/day, dd, mtm | 4.66, 1.59, -284, -245 | 4.66, 2.11, -262, -225 | 5.41, 2.93, **-376**, **-342** | 5.96, 1.94, **-335**, **-366** |
| pair worst month | -119 | -129 | -219 | -154 |
| pair $/day without the candidate's 3 best days | | 4.23 | 3.41 | 4.69 |
| daily corr with pair (pair window) | | -0.02 | 0.02 | 0.40 |
| pair alone $/day, tr/day, dd | | 3.61, 1.23, -356 (own -0.00) | 0.76, 1.34, -470 | 1.30, 0.35, -164 |
| **m15_train** combined $/day, tr/day, dd, mtm | 1.93, 1.24, -313, -334 | 2.06, 1.47, -297, -287 | 1.38, 1.90, -383, -394 | 2.25, 1.37, -425, -429 |
| m15_train alone $/day (own) | | 1.78 (own +0.12) | **-0.55** | +0.32 |
| **m15_test** combined $/day, tr/day, dd, mtm | 4.06, 1.22, -298, -407 | **3.54**, 1.51, **-316**, **-544** | 4.55, 1.75, **-380**, **-486** | 4.28, 1.37, **-660**, **-744** |
| m15_test alone $/day (own) | | 2.71 (own **-0.51**) | +0.50 | +0.23 |
| m15_test flat-cost changed vs base pair | | 3.33 vs 3.94 | | |
| **h1_old** combined $/day, dd | -0.88, -1,368 | -0.88, -1,368 (no change on H1 data) | **-1.02**, **-1,759** | **-1.28**, **-2,129** |
| h1_old alone $/day | | (own 0.00) | -0.14 | -0.40 |
| random-direction pct, m15_test (200) | | 97.5% (long-only, info) | **78.5%** (median -0.27, p95 +1.39) | 67.5% (long-only, info) |
| tests a / b / c / d / e | | yes / **no** / **no** / yes / n.a. | no / no / no / no / no | no / no / yes / no / n.a. |
| verdict | | **FAIL** | **FAIL** | **FAIL** |

**Bold** marks a miss of its pass line. Test (c) for a change asks that both the changed EA
alone and the change's own P&L are positive on m15_train and on m15_test.

Test (e) applies to the short stream, which picks a direction against the long-only pair. A and
C are long-only, so their percentiles are shown for information only.

### The change pick's mappings (`code/mapping_check.py`, diagnostic, chooses nothing)

- **Pair window, re-entry on M15 EMA5/20 alone**, exactly as tuned instead of M5 + M15: $4.05/day,
  1.90 trades/day, dd -319, mtm -292. That fails (a).
  - So candidate A's pass of (a) depends on the M5 mapping.
  - Either way it fails (b) on m15_test, which has no M5.
- **Nearest version testable on H1 data** (anchor H4 only, re-enter on H1 EMA5/20):

  | window | $/day | dd | mtm | own $/day |
  |---|---|---|---|---|
  | h1_old | -0.70 | -1,129 | | +0.18 |
  | m15_train | 2.07 | -344 | | |
  | m15_test | 3.69 | -500 | -539 | -0.37 |

  On older data the idea is not harmful, but it fails on recent data.

## Hindsight: all 243 versions on every window (`code/hindsight.py`, `hindsight.csv`; not a selection step)

### Even with hindsight, no version of this family passes

- 5 versions meet (a) on the pair window and 34 meet (b) on m15_test. **None meets both.**
- The 5 that meet (a) all give m15_test dd -316 to -604 or mtm -482 to -755.

### Train results do not carry over for the changes

This is rank correlation of the change's own $/day, across the 122 change versions:

| m15_train vs | rank corr |
|---|---|
| m15_test | -0.35 |
| pair | +0.13 |
| h1_old | -0.59 |

The faster-EMA changes:
- lost on 2022-24;
- did well on 2024-26 (the strong gold uptrend);
- were mixed on 2016-22.

So the EMA choice is a bet on the regime, not a setting that can be tuned. No change version
earned its own money on train, m15_test and pair together.

### Short mirror

| window | median own $/day | best | share > 0 |
|---|---|---|---|
| m15_train | -1.20 | -0.49 | 0% |
| h1_old (2016-22) | -0.33 | -0.06 | 0% |
| m15_test | -0.33 | +0.60 | 22% |
| pair | +0.58 | +1.76 | 86% |

It lost in every one of the 49 versions on m15_train and on h1_old. Its pair-window gain is the
2026 sell-offs, and the pick's best day was +$407 on 23 Mar 2026. This confirms the project's
earlier finding that shorting loses long term.

### Long sibling

The ordering carries over (train vs m15_test rank corr 0.82), but none of the 57 kept the
drawdown on m15_train, and none meets (a).

### Closest hindsight version (not a candidate)

The closest version is a change: GoldAllAgree with EMA15/60 on M5/M15/M30 and EMA10/40 on
H1/H4, all five still agreeing. It is not a candidate because it lost $0.73/day vs the EA on
m15_train. Taking it now would mean choosing on the test windows.

| window | combined $/day | trades/day | max_dd | mtm | own $/day |
|---|---|---|---|---|---|
| pair | 5.55 | 1.86 | -228 | -182 | +0.89 |
| m15_test | 4.64 | | -233 | -274 | +0.59 |
| h1_old | -0.58 | | -1,139 | | +0.29 |
| m15_train | 1.20 | | -407 | -386 | -0.73 |

- On the pair window it adds only +0.27 trades/day, so it would still miss (a)'s +0.3 trades
  line.
- On m15_train it lost in 2022 and 2023 (-$0.85, -$1.16 a day of its own).

It is a regime-dependent lead, not a pass. If David wants it tried, it should be forward-tested
as its own question.

## Files

- `code/aa_more.py`: the rule engine.
- `code/verify.py`: checks the engine against the harness.
- `code/specs.py`: the versions and their window mapping.
- `code/train_grid.py`: m15_train grid and picks. Writes `train_grid.csv` and `picks.json`.
- `code/evaluate.py`: scores the picks on every window. Writes `results.json`.
- `code/neighbours.py`: writes `train_neighbours.csv`.
- `code/mapping_check.py`: the change pick's M5 and H1 mappings.
- `code/hindsight.py`: writes `hindsight.csv`.

All scripts run with `python3 -I code/<name>.py`.
