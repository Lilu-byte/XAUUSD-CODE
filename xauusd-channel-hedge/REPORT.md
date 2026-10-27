# Channel-middle hedge (buy + sell at the channel middle) — test report, 22 Oct 2026

**Verdict: it does not make money. No EA built.** Educational test, not investment advice.

## The idea (David, 22 Oct)
Find a definite channel/trend. At the channel middle open a buy and a sell together. Each TP sits a small distance
from the entry (buy TP a little above, sell TP a little below), not at the channel edges. No stop loss until one TP
is hit; then the other leg gets a stop.

## How it was tested
- Channels: the GoldChannels rules (least-squares line through closes, 2 sd + 0.2 ATR break, min 20 candles),
  computed only from candles already closed, so no redraw/look-ahead. "Definite" = live channel at least 20 candles old.
- Entry: a candle touches the channel middle and no other pair has both legs open. 0.01 lot each leg.
- Versions (882 per timeframe): TP $0.50 / $1 / $2 / $3 / $5, or 25% / 50% of the half channel width;
  after the first TP the other leg gets: no stop (your literal rule), closed at once, a stop 1x / 2x / 4x the TP distance
  beyond the hit TP, a stop at the channel edge, or closed when the channel breaks; 1, 5 or 50 pairs open at once;
  minimum channel width $0 / $5 / $10; any channel or ranges only.
- Costs: real bar spread (min $0.10) + $0.05 slippage per fill, swap $0.126 long / $0.046 short per night, triple Wednesday.
  If a stop and a TP fall in the same candle, the stop is assumed.
- M1: 26 Jun - 31 Aug 2026 to choose, 1 Sep - 9 Oct 2026 to check. M5: 5 May 2025 - 9 Oct 2026 (17 months).
- Comparisons: holding 0.01 lot of gold = ~$2.07/day (M1 span), ~$2.43/day (M5 span); GoldAllAgree + GoldAsiaBreak pair ~$4.66/day.

## Results
| | M1 choose | M1 check | M5 17 months |
|---|---|---|---|
| Versions in profit (of 882) | 63 | 90 | **0** |
| Versions in profit on all three | | | **0** |
| Median $/day, with any stop after the first TP | -$34 to -$44 | -$28 to -$43 | -$30 |
| Median $/day, no stop | -$0.30 | -$0.07 | -$9.40 |

**With a stop on the second leg, every version loses.** After the first TP, the leftover leg is a bet that price
comes back; combined, the pair is the same as opening one trade against the move at the first TP, with a stop beyond it.
Without an edge, that bet is a coin flip that pays two spreads per pair. Gold on M1/M5 tends to keep going a little
after leaving the middle, so the stop is hit more often than a coin flip (39-50% wins).

**Without a stop, it looks great on M1 and then fails.** Best M1 version (TP $2, channel at least $10 wide,
one pair at a time): 100% of pairs won, +$9.69/day choose, +$11.68/day check, worst open loss -$256.
But it only works because every pair eventually came back during those 3.5 months, and 46% of the time a leg was stuck.
On M5 over 17 months the same rule won 23 pairs, then on 16 May 2025 a sell got stuck and never came back:
it was still open on 9 Oct 2026 at **-$2,417** (338 days), the account sat at -$2,008 in Feb 2026, and the rule
could not trade for almost a year: **-$2.51/day**. Starting the M5 test on other dates gives -$0.36 to -$3.01/day,
worst stuck leg -$715 to -$2,317; only the last 3.5 months (same as the M1 data) is positive (+$2.60/day).
Allowing more pairs at once makes it bigger, not safer: 50 pairs on M1 shows +$116/day but a $23,325 drawdown
(margin call on $3,000).

A 100% win rate here is the same trap as a no-stop grid or martingale: many small wins, then one loss that does
not close and can be bigger than the account.

## Files
- code/chan.py — live channel per candle (GoldChannels rules, closed candles only); code/seg.py — prototype it reuses
- code/sim2.py — pair simulator; code/grid.py — the 882-version run
- grid_M1.csv, grid_M5.csv — every version's results (pairs, win %, $/day, drawdown incl. floating, worst pair, open at end)
