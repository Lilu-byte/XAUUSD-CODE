# GoldAllAgree: MT5 Expert Advisor (13 Oct 2026, v1.10 on 15 Oct)

Runs the "all agree" rule from xauusd-intraday/REPORT.md: **hold one long XAUUSD position while EMA20 is above EMA80 on M5, M15, M30, H1 and H4 (closed bars only). Flat otherwise. Never short.** Re-checked at every M5 close.

## Install (5 minutes)

1. In MT5: **File > Open Data Folder**, then go to `MQL5/Experts/` and copy `GoldAllAgree.mq5` there.
2. Open MetaEditor (F4), open the file, press **Compile** (F7). It should report 0 errors. If it shows any, paste them in the thread.
3. Back in MT5, open an **XAUUSD M5 chart** (any timeframe works, M5 is the natural one). Drag *GoldAllAgree* from Navigator > Expert Advisors onto it.
4. Tick **Allow Algo Trading** in the EA's settings and turn on the **Algo Trading** button in the toolbar.
5. The chart's top-left corner shows each timeframe's trend, the signal (LONG/FLAT) and what it holds.

Start on a **demo account** with **hedging** (the default for most MT5 demo accounts). Leave the terminal running (or use a VPS); the EA only acts while MT5 is open and connected. To run it beside GoldAsiaBreak, follow `/mnt/project-files/xauusd-demo-pair/SETUP.md`.

## Chart indicator: GoldAllAgreeTrend

Shows exactly what the EA sees, so the chart and the EA always agree.

- **Ribbon** between the chart's EMA20 and EMA80: green shade when EMA20 is on top, red when below.
- **EMA20 line colour:** green = the EA's signal is LONG (all five timeframes up), grey = this chart's timeframe is up but at least one other isn't, red = this timeframe is down.
- **Arrows:** green up-arrow where the EA would buy, orange down-arrow where it would exit.
- **Panel** (top right): each timeframe UP/DOWN with its EMA gap in $ (how far from flipping), then the signal (LONG/FLAT) and since when.
- Optional pop-up or phone alert when the signal changes (off by default).

Install it like the EA, but into `MQL5/Indicators/`, compile, and drag it onto the XAUUSD chart. On an M5 chart the arrows match the EA bar for bar; on other timeframes they're checked at that chart's closes, so they can be a few minutes off.

## Settings

| Setting | Default | What it does |
|---|---|---|
| Fast / Slow EMA | 20 / 80 | The tested values. Don't change them without retesting. |
| Use M5 ... H4 | all on | Timeframes that must all agree. The M15-timeline test (M5 off) scored about the same and trades less. |
| Fixed lots | 0.01 | One 0.01 lot = 1 oz, about $4,200 of gold, about 1.4x a $3,000 account. |
| Equity per 0.01 lot | 0 (off) | Auto-size: e.g. 3000 means 0.01 lot per $3,000 of equity. |
| Max lots | 1.0 | Hard cap. |
| Max spread (points) | 80 | Waits to enter while the spread is wider than $0.80 (e.g. at the daily rollover). Exits are never delayed. |
| Emergency stop ($) | 100 | Hard stop placed on the broker's server, in case your terminal disconnects. No replay trade went more than $94 against, so it changes nothing in the backtest. 0 turns it off. After a stop-out or a manual close the EA waits for a FLAT signal before buying again, also after a restart. |
| Close Friday | off | Optional: flatten before the weekend. Not part of the backtest. |
| Need hedging | on | Refuses to trade on a netting account, where another gold EA's orders would merge with this position. Set it off only if GoldAllAgree runs alone. |
| Magic number | 20261013 | The EA only touches its own positions. |

## Check it in the Strategy Tester first

Strategy Tester (Ctrl+R): Expert *GoldAllAgree*, XAUUSD, M5, model **"Every tick based on real ticks"** (or "1 minute OHLC"), dates 2025-05-05 to 2026-10-09, deposit 3000, leverage your broker's.

`expected_trades_M5.csv` lists the 265 trades the rule should take over that period (from the MT5 export, 0.01 lot, after spread and swap). Your tester should show about the same entries and a similar total; small differences come from tick timing and spread.

What the replay shows for one 0.01 lot on $3,000:

| | Trades | Win rate | Profit |
|---|---|---|---|
| May-Dec 2025 | 162 | 34% | +$642 |
| Jan-Oct 2026 | 103 | 28% | +$709 |
| Total | 265 | 32% | +$1,350 (+45%), worst closed-trade drawdown 8% |

That is about 3.5 trades a week, more than the "1-2 a week" in the intraday report: that figure is for the version without M5 (84 a year). With M5 included the study itself counted 130 a year in 2026, the same as this replay (103 by 9 Oct); 2025 was busier. Turn *Use M5* off for the calmer version, which scored about the same.

It loses on two trades out of three. The profit comes from a few long trends (biggest win $243, biggest loss $77). Expect long runs of small losses.

## Honest limits

- The edge showed up only in 2022-2026, when gold trended cleanly. On 2006-2024 data the same idea (H1+H4) did no better than just holding gold. A choppy market will likely erase it.
- 0.01 lot on $3,000 is 1.4x leverage: gains and drops are ~1.4x the gold move while in the trade.
- Today (9 Oct close) the signal is **FLAT**: H4 has been down since early September; the EA will not buy until H4 turns up too.

## Files

- `GoldAllAgree.mq5`: the Expert Advisor.
- `GoldAllAgreeTrend.mq5`: the matching chart indicator.
- `expected_trades_M5.csv`: trades the rule should take, May 2025 to Oct 2026.
- `code/expected_trades.py`: rebuilds that list from the MT5 export using the intraday study's code.

## Changes in v1.10 (15 Oct 2026)

- Emergency stop on by default at $100 (was off).
- Stops with an alert on a netting account (switch: *Need hedging*).
- The pause after a stop-out or manual close now survives a restart: it reads the last trade from the account history, and ends the pause at once if a FLAT signal came while the EA was off.
- At each new M5 bar it waits up to a minute from the bar's first tick for the M15-H4 averages to include their newest bar, so entries and exits at those timeframes' flips aren't one bar late. It also needs 320 bars of history per timeframe before trading.
- The indicator waits the same way before redrawing, so its arrows and alerts don't flicker at a higher-timeframe flip.
