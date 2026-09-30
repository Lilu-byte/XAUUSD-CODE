# Installation

The code was checked by translating it to C++ against a mock of the MT5 API (see `research/run_checks.sh`). It has **not**
been compiled in MetaEditor, so treat the first compile as part of testing. If MetaEditor reports an error, the message and
line number are enough to fix it quickly.

## 1. Copy the files
Each program is **one self-contained file**; there is no include folder to install.

In MetaTrader 5: **File > Open Data Folder**, then open `MQL5`.

| From this repo | To |
|---|---|
| `MQL5/Indicators/XAU_Oracle.mq5` | `MQL5/Indicators/` |
| `MQL5/Experts/XAU_Sniper_EA.mq5` | `MQL5/Experts/` |
| `MQL5/Scripts/XAU_DataExport.mq5` | `MQL5/Scripts/` |
| `MQL5/Presets/*.set` (optional) | anywhere; load from the EA inputs dialog |

Replace the old versions: v2 inputs changed, and old `.set` files will not load correctly.

(An earlier version needed `MQL5/Include/XAU/`; that caused the error `file 'Include\XAU\XAU_Platform.mqh' not found`. It is gone.
The editable sources live in `src/`; `python3 research/bundle.py` regenerates the two files.)

## 2. Compile
Open MetaEditor (F4), open each `.mq5`, press **F7**. Expect 0 errors.

## 3. Indicator
1. Open an **XAUUSD** chart (any timeframe; M15 is the reference). The symbol name can be `XAUUSD`, `GOLD`, `XAUUSD.m`, etc. Everything uses the chart symbol.
2. Navigator > Indicators > XAU_Oracle, drag onto the chart.
3. Inputs to check first:
   * **Broker clock.** Most MT5 gold brokers run a "New York close" server: GMT+2 in winter, GMT+3 in summer (follows US daylight saving).
     That is the default (*Server clock daylight saving = US*). The offset is auto-detected and the daylight-saving rule is applied to *all* history.
     If your broker's clock never changes, choose *fixed*; if it follows EU time, choose *EU*. If the Asian box or session names look shifted, tick
     *Set broker GMT offset by hand* and enter the **winter** offset.
   * **Risk % and Balance override** (used only for the position-size line; 0 = your account equity).
   * **Strategy / Exit style**: leave both on AUTO to let the Strategy Lab choose. **Strategy Lab: minimum % of winning trades** is 60 by default.
4. The first load runs the Strategy Lab (a few seconds). It re-runs once a day. The scoreboard (bottom right) shows the result.
5. Leave the chart scrolled to the latest bar. *Leave room on the right for projections* shifts the chart so the ghost candles fit.
6. Give it a minute to load history. Rebuilds happen on every new bar; the dashboard refreshes every second.
   For a longer test window raise Tools > Options > Charts > *Max bars in chart* (e.g. 500000) and scroll back once to load history.

## 4. Expert Advisor
1. Tools > Options > Expert Advisors: tick **Allow algorithmic trading**. Press the **AutoTrading** toolbar button.
2. Attach `XAU_Sniper_EA` to an XAUUSD **M15** chart (one chart per symbol per magic number).
3. Load a preset: inputs dialog > **Load**:
   | Preset | Use |
   |---|---|
   | `XAU_Sniper_Balanced.set` | Default: Lab choice, 1% risk |
   | `XAU_Sniper_Conservative.set` | 0.5% risk, Lab must see 65% winners |
   | `XAU_Sniper_HighWin.set` | Every trade uses the High-hit exit, Lab target 65% |
   | `XAU_Sniper_Growth.set` / `XAU_Sniper_Aggressive.set` | 2% / 4% risk |
   | `XAU_Sniper_DemoTurbo.set` | Demo only: all day, several positions, trades the closest strategy even when none passed |
   | `XAU_Sniper_GoldORB.set` | The GOLD_ORB opening-range strategy alone (H1 chart) |
4. **Start on a demo account.** See [TESTING.md](TESTING.md).
5. Optional: add a DXY-like symbol (`USDX`, `DXY`, ...) to Market Watch. Without it the EA uses EURUSD as a proxy.

## 5. Notes
* **Calendar.** News filtering uses MT5's built-in economic calendar and needs a connected terminal. It is not available in the Strategy Tester; the EA then falls back to a fixed 12:30 and 13:30 GMT window on weekdays.
* **Hedging vs netting.** On netting accounts the EA will not enter while any position exists on the symbol.
* **Tiny accounts.** One minimum lot (0.01) of XAUUSD risks about $1 per $1 of stop distance. If that exceeds your risk budget the EA skips the trade and logs why. Use a cent/micro account or a bigger balance.
* **State.** The EA keeps its peak equity, kill-switch flag and per-position management state in terminal global variables. To clear a kill-switch, start the EA once with *InpResetKill = true*, then turn it off again.
* Only one instance of the EA per symbol/magic number; change `InpMagic` if you run several.

## Export your data (optional, recommended)
Navigator > Scripts > **XAU_DataExport**, drag onto the XAUUSD chart, OK. Files appear in `<Data Folder>\MQL5\Files\XAU_Export\`. Zip that folder and share it: the whole Strategy Lab and the live replay can then be run on your real broker data.

## Demo accounts
*Demo accounts > Demo mode*:
* **Rehearsal** (default): the demo runs exactly the rules of a real account, so what you see is what a real account would do.
* **Free run** (also set by `XAU_Sniper_DemoTurbo.set`): every protection only warns (no kill-switch, no daily limits), up to 5 EA trades at once,
  and the smallest lot is allowed even above your risk, up to *InpDemoMaxRiskPct* (10%) of equity per trade. With *InpDemoUnproven* it also
  trades the closest strategy when none passed the Lab (marked UNPROVEN). Not a preview of a real account.

On a real account the demo inputs are ignored. In every mode the EA will not enter while free margin is <= 0, the margin level is below 300%,
or the spread is above 1.5x the tested cost (*InpCostPrice*, 0.35). 0.01 lot of gold needs roughly 42 USD of margin at 1:100 and 4,200 USD price.

**After updating the EA, remove it from the chart and attach it again** (or load a preset): MT5 keeps the input values of an attached EA
when it is recompiled. The demo inputs were renamed in round 7 so that old free-run values cannot carry over.

**Your own trades.** *Your own trades > InpProtectManual* (off by default) lets the EA put a stop on any position on the symbol that has none,
where it would lose *InpProtectPct* (5%) of equity; a position already losing more gets its stop 5% of equity beyond the current price.

**More trades: three copies.** Attach the EA to three XAUUSD charts, M15, H1 and H4, and load `XAU_Sniper_Multi_M15.set`,
`XAU_Sniper_Multi_H1.set` and `XAU_Sniper_Multi_H4.set` (each has its own magic number, so the copies do not block each other).
Each runs its own daily Strategy Lab. On a netting account only one position per symbol is possible; use a hedging account.

**Daily trend filter** (*InpDailyTrend*, both programs): AUTO = on H1 and above buy only while the last daily close is above its 200-day
mean; on M5-M30 no filter. OFF, WITH (only in the daily trend's direction) and LONG (buys only, every timeframe) are the other choices.
**Lab window** (*InpHistoryBars*): 0 = AUTO, 25,000 bars on H1 (about 4 years), 10,000 elsewhere. Keep both settings equal in the EA and
the indicator so they choose the same strategy. The H1 window needs *Tools > Options > Charts > Max bars in chart* of at least 30,000.

**Account size.** The indicator shows "TOO BIG, SKIP" when even 0.01 lot risks more than 1.5x your *Risk per trade*, and the balance the
trade would need. Rough minimums for 1% risk at 0.01 lot (Sep 2026): M5 550 USD, M15 1,100, H1 2,400, H4 5,300.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Panel says "loading history" | Not enough bars yet; scroll back or wait for the terminal to download history |
| No projections visible | Chart shift is off or the chart is scrolled away from the newest bar |
| EA logs "signal skipped: ..." | Working as designed; the reason is in the message (spread, news, daily limit, ...) |
| Panel says STOPPED - loss limit hit (old version) | Update the EA; on a demo account it now clears the stale kill-switch at start. On a real account set *InpResetKill* for one start |
| EA never trades | Check AutoTrading is on, the panel status line, and the Experts tab of the Toolbox |
| Signals appear at odd hours | Broker clock setting wrong (fixed / US / EU DST) or winter offset wrong; set it manually |
| Panel says LEARNING for a long time | Not enough history yet; scroll the chart back or raise *Max bars in chart* |
| Scoreboard shows no PASS | Nothing reached the win-rate target with profit on this chart. The EA stands aside (live and demo rehearsal) or trades UNPROVEN (demo free run). Try another timeframe, or lower the target |
| Indicator says "TOO BIG, SKIP" / EA says "ACCOUNT TOO SMALL HERE" | Even 0.01 lot risks more than 1.5x your risk setting on this timeframe. Use a lower timeframe, a larger (demo) balance, or a cent account |
| EA status line mentions margin | Open trades (manual ones too) use the margin; close or protect them first |
| EA panel still says "[DEMO - free run]" after an update | Remove the EA from the chart and attach it again |
| EA shows another timeframe's strategy after you switched the chart (old version) | Update: the EA now resets itself on a timeframe change |
| "setup skipped: against the daily trend" | H1 and above buy only in a daily uptrend (AUTO); set *InpDailyTrend* = OFF to trade both ways |
| EA logs "sizing note - broker tick value is off" | Expected on some brokers; the EA already uses the correct figure |
| EA logs "another instance is already running" | A second chart with the same magic (or a crashed run; wait 15 seconds and reattach) |
