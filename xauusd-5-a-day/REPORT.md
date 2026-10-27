# Making up to $5 a day on XAUUSD (one 0.01 lot, $3,000)

13 Oct 2026, corrected 15 Oct 2026 (see "Corrections" at the end). Code in `code/` (`engine.py` simulator, `grid.py`, `asia*.py`, `ideas.py`; `asia_ea.py` is a line-by-line copy of the GoldAsiaBreak EA). Full grid: `grid_M15.csv`. To run both EAs on a demo account, see `/mnt/project-files/xauusd-demo-pair/SETUP.md`.

## Bottom line

- **A hard "$5 then stop" rule doesn't make $5 a day.** Hitting $5 is easy: gold moves about $100 a day now, so most setups reach +$5 on 65-80% of days. The problem is the other days. A $5 win needs a stop far enough away to survive normal noise, so one bad day costs $30-50 and wipes out 6-10 good ones.
- I tested 12,600 versions: 15 ways to pick direction (always long, coin flip, D1/H4/H1 trend, the all-agree trend, Asian range breakout), 4 start times, take profit $3/5/8, stop $3-50, 1-3 tries a day, and "recover the loss on the next try". **Only 8% made money in the training years (Jul 2022 to Jun 2024) and 17% in the test years.** The top training picks were coin-flip entries, so most "winners" are luck.
- **One idea held up: the Asian range breakout.** Mark today's high and low from 00:00 to 09:00 server time. From 09:00, take the first M5 close outside that range in its direction, TP $5, stop $50, one trade a day, close anything still open at 22:45. It made money in both training and test years and beat 95-100% of random-direction versions with the same entry times.
- **But it only earns about $0.75-1.05 a day**, not $5, with a worst month of -$125 to -$186. On 2016-2022 hourly data it lost money, and on the M5 data it lost a little from May to December 2025 (-$0.35 a day); all of its M5 profit came in 2026. Like everything else in this project, its edge looks tied to the recent trend.
- **Your current EA already averages $3.61 a day**, but in lumps: it trades on 39% of days, makes $5+ on only 16% of days, its median trade is -$5, and the best 10% of trades make all the profit. January 2026 alone made half of it. Capping it at $5 a day would remove the big days it lives on.
- **Best combination tested: run both side by side.** The all-agree EA plus the Asian breakout averaged **$4.66 a day** (TP $5) or $4.94 a day (TP $8), May 2025 to Oct 2026, with $5+ on 63-66% of days and a worst drawdown of $252-285. The two barely move together (daily correlation 0.03-0.07), which is why the combination is smoother than the EA alone (worst drawdown $358). It still had 6 losing months out of 18, the worst -$119 (TP $5).

## Results (after spread $0.30, slippage $0.10 a side, and swap on the rare trade held overnight)

All figures for one 0.01 lot ($1 per $1 gold move). In the M15 and H1 rows, older years are scaled to today's price so a "$5 target" means the same percentage move. The M5 rows use fixed $5/$50 like the EA, and come from `asia_ea.py`, which copies the EA's code.

| Strategy | Period | $/day | Days ≥ $5 | Losing days | Worst month | Worst drawdown |
|---|---|---|---|---|---|---|
| Buy at 10:00, TP $5, stop $10, every day | M15 2022-26 | -0.10 | 66% | 34% | -$86 | -$253 |
| Same with coin-flip direction | M15 2022-26 | -0.31 | 65% | 35% | -$86 | -$587 |
| Same, all-agree trend direction only | M15 2022-26 | -0.24 | 26% | 16% | -$36 | -$303 |
| **Asian breakout, TP $5, stop $50** | M15 2022-26 | **+0.73** | 80% | 12% | -$186 | -$339 |
| Asian breakout, TP $5, stop $50 (the EA) | M5 2025-26 | +1.05 | 78% | 9% | -$125 | -$259 |
| Asian breakout, TP $5, stop $50 | H1 2016-22 | **-0.60** | 64% | 9% | -$135 | -$1,018 |
| Asian breakout, TP $8, stop $50 (the EA) | M5 2025-26 | +1.33 | 71% | 15% | -$127 | -$232 |
| All-agree EA alone (replay) | M5 2025-26 | +3.61 | 16% | 21% | -$129 | -$358 |
| **EA + Asian breakout TP $5** | M5 2025-26 | **+4.66** | 66% | 24% | -$119 | -$285 |
| EA + Asian breakout TP $8 | M5 2025-26 | +4.94 | 63% | 26% | -$150 | -$252 |

Asian breakout by year ($/day, TP $5 / stop $50): M15 2022 -0.52, 2023 +0.64, 2024 +0.42, 2025 +0.71, 2026 +2.06. M5 (the EA): May-Dec 2025 -0.35, 2026 +2.24.

Both side by side by year ($/day, TP $5): May-Dec 2025 $3.38, Jan-Oct 2026 $5.75.

The EA copy against random directions on the same entry bars (200 runs): median -$0.40 a day, 95th percentile +$0.64, so the breakout's +$1.05 beat all of them. With the bar's recorded spread instead of a flat $0.30, the breakout makes $1.71 a day and the pair $5.32; the recorded spread is the lowest in each bar, so real fills will be closer to the flat $0.30.

## Things that did not help

- Adding a trend filter to the breakout (only trade breaks in the H4, D1 or H4+H1 trend direction): $/day fell to about zero on M15.
- Stops tighter than $20: every version lost, because normal noise hits them before $5.
- A second try that aims to win back the first loss: no better than one try, and worst days double.
- Long-only breakout: positive but about half the profit of trading both directions.

## Caveats

- The breakout was picked after looking at 12,600 combinations. Its random-direction check helps, but treat the edge as optimistic.
- M5 data covers only May 2025 onward. The 2016-2022 check used hourly bars (entries up to an hour late), so it is weaker evidence, but it was negative.
- Running both EAs means up to 0.02 lot open at once (about 2.8x the account). On a netting account the two would merge into one position, so both EAs now refuse to trade on a netting account.
- Thin margin: trades won 85% (M15) and 89% (M5) of the time, at +$5 each; losers averaged about -$30 (many are 22:45 closes, not full stops). Break-even is about 86% wins, so a few points' drop in win rate turns it negative. It is also sensitive to small details: setting the $5/$50 from the quote rather than from a fill $0.10 worse (what the EA does when an order slips) turns 4 of 331 trades from losses into wins and gives $1.47 a day instead of $1.05. The report keeps the cautious figure.
- Holiday early closes (the day after US Thanksgiving, Christmas Eve, US Monday holidays; 19:55-21:45 in the export) end the session before 22:45, and the broker's session table doesn't show it. A trade still open then is held to the next open and closed there. On those days, set the close time to 19:30 or switch GoldAsiaBreak off.

## Files

- `GoldAsiaBreak.mq5` (v1.10): the breakout EA (goes in MQL5/Experts, attach to an XAUUSD chart, any timeframe; works on M5 closes). Defaults: 0.01 lot, range 00:00-09:00 server, TP $5, stop $50, one trade a day, close at 22:45 (or 10 minutes before the session ends), magic 20261014 so it runs next to GoldAllAgree. Needs a hedging account. Not compiled yet (MetaEditor isn't available here).
- `expected_trades_AsiaBreak.csv`: every trade the EA should take from May 2025 to Oct 2026 (TP $5, flat $0.30 spread), to compare with MT5's Strategy Tester.
- Server times assume the same broker as the export (GMT+3 in summer).

## Corrections (15 Oct 2026)

A review of both EAs against their backtests found these problems, now fixed:
- **Close time.** Since March 2026 this broker's session ends at 23:00, so the old 23:30 close never fired and trades could run overnight or over a weekend. The EA now closes at 22:45, or 10 minutes before the session's end, and closes any trade left from an earlier day at the next open.
- **First break only.** The rule trades only the first close outside the range. The old EA would take a later break if it missed the first one (EA restarted, spread too wide, order rejected). It now skips the day instead.
- **One trade a day after a restart.** The EA now checks the account's deal history, so a restart can't lead to a second trade the same day or to a wrongly skipped day. It also waits for a complete Asian range before trading.
- **Numbers.** The old M5 figures scaled the $5/$50 to the price of gold, which the EA doesn't do, and a trade carried in from the day before wrongly used up the next day's trade. Corrected: the breakout on M5 makes $1.05 a day at TP $5 (was $0.97) and $1.33 at TP $8 (was $1.73). The pair makes $4.66 (was $4.57) and $4.94 (was $5.34). The M15 row moved from +0.66 to +0.73 and the H1 row from -0.72 to -0.60.
