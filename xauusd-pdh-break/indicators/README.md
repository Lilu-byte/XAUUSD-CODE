# Four chart indicators from the XAUUSD_PDH_Break archive (21 Oct 2026)

Each one draws an EA's rules from David's archive on the chart: where it would buy or sell, where its stop sits, and where it would exit. A panel in the top right shows what it is doing now. They are indicators only and place no orders.

**As strategies, none of them beats the GoldAllAgree + GoldAsiaBreak pair or simply holding gold** (results below, and in `../REPORT.md`). Treat them as chart reading aids, not as a reason to trade more.

| File | Name in your list | From EA | Chart |
|---|---|---|---|
| `GoldTrendRide.mq5` | Hourly trend ride | XAUUSD_EWMAC_H1 | H1 |
| `GoldTurtle55.mq5` | Turtle 55/20 breakout | XAUUSD_Turtle_D1 | D1 |
| `GoldFedDay.mq5` | Fed-day follow | XAUUSD_FOMC_Follow | H1 |
| `GoldTurtle20.mq5` | Fast Turtle 20/10 | XAUUSD_Turtle_D1 with 20/10 lookbacks | D1 |

## Install

1. In MT5: File > Open Data Folder > `MQL5\Indicators`. Copy the four `.mq5` files there.
2. Open each one in MetaEditor and press F7. If anything fails to compile, paste the errors in this thread.
3. Drag the indicator onto an XAUUSD chart **on the timeframe in the table**. On any other timeframe it shows an alert and won't load.

## What you see

**GoldTrendRide (H1)**
- Aqua line = EMA16, gold line = EMA64.
- Green up arrow = add a unit, orange down arrow = cut a unit, red X = back to flat. Each arrow sits on the hour where the EA would trade at the open.
- Panel: units held now and the lots that equals (`UnitLots` x units, 0.01 by default), the trend score, the last change, and the score that would add or cut the next unit.
- `Cap = 2.0` allows up to 4 units, as in the EA. `Cap = 0.5` limits it to 0 or 1 unit.

**GoldTurtle55 / GoldTurtle20 (D1)**
- Blue dotted line = the buy level (55-day or 20-day high). Orange dotted line = the exit level (20-day or 10-day low).
- Green arrow = buy, red line = the stop while in a trade (2 x ATR below the entry, raised to the exit level, never lowered), red X = exit.
- Panel: in a trade or flat, the buy level and how far away it is, the stop, and the open result per 0.01 lot.
- Both files are the same code with different defaults, so you can run them side by side.

**GoldFedDay (H1)**
- On each Fed statement day in the built-in list (2016 to Dec 2026): green up arrow = buy, red down arrow = sell, red line = the trailing stop, yellow X = exit.
- Panel: an open Fed-day trade if there is one, the last Fed day's result, and the next Fed day.
- `ServerMinusNY = 7` fits your broker all year (its trading day opens at 01:00 server time, which is 18:00 New York). Change it only on a broker with a different clock.
- For Fed days after December 2026, add them in `ExtraFomcDates` as `YYYYMMDD,YYYYMMDD`.

**Alerts:** `AlertsOn` pops up an alert when a new arrow appears on the current bar. `PushAlerts` also sends it to the MT5 phone app.

The lines and arrows use the chart's bid prices with no spread, so a real fill would be a little worse. Past arrows don't move once a bar has closed. The Turtle's buy and exit arrows can appear during the day, because the EA uses stop orders.

## How they tested (0.01 lot per unit, after spread $0.30, slippage $0.10 and swap)

| | Period | $ a day | Holding 0.01 lot of gold | Notes |
|---|---|---|---|---|
| Hourly trend ride, 0-4 units | May 2025 - Oct 2026 | 11.64 | 1.87 | Fell $1,570 between 28 Jan and 4 Aug 2026 (half the account). Lost money in 5 of 11 years. No stop. |
| Hourly trend ride, 0-1 unit (`Cap = 0.5`) | May 2025 - Oct 2026 | 3.14 | 1.87 | Fell $735 |
| Turtle 55/20 | 2004 - 2026 | 0.44 | 0.48 | 57 trades. At the EA's 0.5% risk it can't trade on $3,000: the stop is about $187 away per 0.01 lot now |
| Fast Turtle 20/10 | 2004 - 2026 | 0.21 | 0.48 | 129 trades, worst drop $526 on closed trades, 2026 so far -$17 |
| Fed-day follow | 2016 - 2026 | 0.04 | 0.93 | 80 trades, about $12 a year |
| **The pair (GoldAllAgree + GoldAsiaBreak)** | May 2025 - Oct 2026 | **4.66** | 1.87 | Worst drop $285 |

The trend ride's big number comes from holding up to 0.04 lot of gold through the 2025 rally. Its drop in 2026 is more than five times the pair's worst. Next to the pair, the combined worst drop was about $1,600 at 0-4 units, or $800 at 0-1 unit.

Code for these numbers: `../code/others.py`, `../code/ewmac_check2.py`, `../code/fast_turtle.py`.
