# Running GoldAllAgree and GoldAsiaBreak side by side (demo first)

15 Oct 2026. These are the two EAs from this project that made money in testing on data they weren't tuned on. Run together on one 0.01 lot each, they averaged **$4.66 a day** from May 2025 to Oct 2026, in lumps: $5 or more on about 2 days in 3, and 6 losing months out of 18. Expect less live. Run them on a demo account for at least a month before any real money.

## 1. Account

- **MT5 demo, hedging mode, $3,000.** When you open the demo account, tick "Use hedge in trading". The MT5 window title then says *Hedge*, not *Netting*. Both EAs refuse to trade on a netting account and show an alert, because there the two EAs' orders would merge into one position.
- Leverage 1:100 or more. Margin is about $42 per 0.01 lot at 1:100, and both EAs together hold at most 0.02 lot.
- Same kind of server clock as your export: GMT+2 in winter and GMT+3 in summer, so the trading day ends at 23:00 server time. Most MT5 brokers use this. If yours doesn't, the Asian range hours would need shifting; ask in the thread.

## 2. Install and compile

| File | Copy to | Path in this project |
|---|---|---|
| `GoldAllAgree.mq5` (EA, v1.10) | MQL5/Experts | `/mnt/project-files/xauusd-mt5/GoldAllAgree.mq5` |
| `GoldAsiaBreak.mq5` (EA, v1.10) | MQL5/Experts | `/mnt/project-files/xauusd-5-a-day/GoldAsiaBreak.mq5` |
| `GoldAllAgreeTrend.mq5` (indicator, optional) | MQL5/Indicators | `/mnt/project-files/xauusd-mt5/GoldAllAgreeTrend.mq5` |

In MT5: File > Open Data Folder, copy the files, then open each one in MetaEditor (F4) and press **F7**. Each should say 0 errors. They haven't been compiled yet because MetaEditor isn't available here, so paste any errors in the thread and I'll fix them.

## 3. Check each EA in the Strategy Tester

The tester runs one EA at a time. Settings for both: XAUUSD, M5, model **"Every tick based on real ticks"**, 2025-05-05 to 2026-10-09, deposit 3000, default inputs.

| EA | Compare with | What the replay expects |
|---|---|---|
| GoldAllAgree | `/mnt/project-files/xauusd-mt5/expected_trades_M5.csv` | 265 trades, about +$1,350, wins 1 in 3 |
| GoldAsiaBreak | `/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv` | 331 trades, about +$390 at a $0.30 spread (+$640 at the recorded spread), wins about 89% |

Entry times and directions should mostly match. Totals will differ with your broker's spread and commission.

## 4. Attach them

1. Open two XAUUSD **M5** charts.
2. Chart 1: drag **GoldAllAgree** onto it, and the GoldAllAgreeTrend indicator if you want to see its signal.
3. Chart 2: drag **GoldAsiaBreak** onto it.
4. In each EA's settings, tick *Allow Algo Trading* and keep the default inputs. Turn on the **Algo Trading** button in the toolbar.
5. Keep MT5 running and connected, ideally on a VPS. Both EAs keep their stops and take-profits on the broker's server, and they pick up where they left off after a restart.

Magic numbers: GoldAllAgree 20261013, GoldAsiaBreak 20261014. Each only touches its own trades, so you can also trade by hand on the same account.

## 5. What each one does

**GoldAsiaBreak**: at most one trade a day.
- Marks the high and low from 00:00 to 09:00 server time. From 09:00, the first M5 candle that closes outside that range opens a trade in its direction: take profit $5, stop $50.
- If that first break can't be traded (the spread is too wide, or MT5 was off), it sits the day out.
- No new trades after 22:29. Anything still open is closed at 22:45.
- Most days: +$5 within a few hours. About 1 day in 10: a loss, about -$30 on average and -$50 at worst.

**GoldAllAgree**: long only, holds for days to weeks.
- Buys when EMA20 is above EMA80 on all of M5, M15, M30, H1 and H4. Sells when any one of them turns down.
- Wins about 1 trade in 3. The profit comes from a few long trends, so long runs of small losses are normal.
- Has a $100 emergency stop. After a stop-out or a manual close, it waits for the signal to go flat before buying again.
- At the 9 Oct close it was **flat**, because H4 had been down since late August, so it may not trade for a while.

## 6. Expected results (replay, May 2025 to Oct 2026, one 0.01 lot each)

| | $ a day | Days ≥ $5 | Losing months | Worst month | Worst drawdown |
|---|---|---|---|---|---|
| GoldAllAgree | 3.61 | 16% | 7 of 18 (3 with no trade) | -$129 | -$358 |
| GoldAsiaBreak | 1.05 | 78% | 6 of 18 | -$125 | -$259 |
| **Both** | **4.66** | **66%** | **6 of 18** | **-$119** | **-$285** |

Costs: a $0.30 spread plus $0.10 slippage on GoldAsiaBreak, the recorded spread on GoldAllAgree, and swap on positions held overnight. Details are in `/mnt/project-files/xauusd-5-a-day/REPORT.md` and `/mnt/project-files/xauusd-mt5/README.md`.

Read these numbers with care:
- **Most of the profit is from 2026.** The pair made $3.38 a day from May to December 2025 and $5.75 a day in 2026. GoldAsiaBreak lost $0.35 a day in May-Dec 2025. On 2016-2022 hourly data it lost money, and GoldAllAgree's idea did no better than just holding gold on 2006-2024.
- **GoldAllAgree is lumpy.** January 2026 alone made half its profit.
- **GoldAsiaBreak lives on a thin margin.** Its break-even win rate is about 86% and it won 89%. If its demo win rate stays under 86% after 40 or so trades, switch it off.

## 7. Calendar

- **Early closes:** in your export the session ended early (19:55-21:45) on US holidays: the day after Thanksgiving, Christmas Eve, and Mondays such as Martin Luther King Day. Next ones: Fri 27 Nov and Thu 24 Dec 2026, then Mon 18 Jan 2027. The broker's session table doesn't show these. On those days, set GoldAsiaBreak's close time to 19:30 or take it off the chart for the day. Otherwise a trade still open at the early close is held to the next open and closed there.
- **Clock changes** (US daylight saving ends 1 Nov 2026): nothing to do, as long as your broker's server clock moves with New York like the export's did.

## 8. Not part of this setup

GoldMicroScalp and GoldCandlePatterns lost money in testing. If you run either one on the same demo for comparison anyway, their magic numbers don't clash with these two.
