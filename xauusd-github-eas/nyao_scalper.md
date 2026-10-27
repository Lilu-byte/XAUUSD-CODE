# Nyao Scalper MT5 (github.com/elrizwiraswara/nyao_scalper_mt5)

Read 2026-10-14 (v46.0, last commit 9a98af2, 14 Oct 2026). BSD-3 licence, one 8,200-line .mq5 file, no DLLs; the only network call is an opt-in Discord webhook.

## What it does (default profile, XAUUSDm M5, 0.01 lot)
- Despite the name, not a $0.10 scalper: a trend follower with $20 stops.
- Entry: a 0-10 "trend score" from the last ~8-17 hours of M5 bars (position in 200-bar range, distance from EMA200 in ATRs, efficiency ratio over 100 bars, 192-bar momentum). Buys when buy score >= 5 and D1 close is >= 0.5% above a rising EMA50; sells mirror that. Decided on closed bars.
- Exit: fixed $20 stop. At +$20 a "checkpoint": keep the trade if the trend still agrees (lock 50%, next checkpoint $20 further), else close. $20 trailing stop from +$10. Closes a loser early if the opposite score reaches 6.
- After 4 losses in a row it paper-trades until a paper win.
- Optional martingale "hedge chain" recovery, off by default (README itself warns of ruin risk).
- Needs a hedging account. Points assume 3-digit gold quotes (Exness XAUUSDm); divide by 10 on 2-digit symbols.

## Author's own real-tick test (reports/default-2026-real-ticks, $2,000 fresh each month, 0.01 lot)
| Months (2026) | M5 net | M1 net |
|---|---|---|
| Jan-Jun (used while designing it) | +$1,701 | +$532 |
| Jul-Sep (out of sample) | -$49 | -$400 |
- M5: 1,107 trades, 44% win, avg win $20.73 / loss $13.62, PF 1.20, worst monthly drawdown 20%.
- Jan + Jun alone = +$1,499 of the M5 profit; other 7 months net about +$154.
- The .set file header quotes an older run (M5 Jan-Sep +44%, Jul-Sep -10.6%), so results shift between versions.

## Fit with the project
- Same idea as GoldAllAgree (ride multi-hour trend, D1 filter), plus shorting and tighter stops. The project's tests found shorting and small stops lost money over 2006-2024.
- Does not deliver a steady $5/day: profit came in two strong-trend months, and the only unseen months were flat to negative.
- If trying it: demo, M5, hedge chain off, MT5 tester on "Every tick based on real ticks" with the broker's spread.
