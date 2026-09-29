# Installation

The code was checked by translating it to C++ against a mock of the MT5 API (see `research/run_checks.sh`). It has **not**
been compiled in MetaEditor, so treat the first compile as part of testing. If MetaEditor reports an error, the message and
line number are enough to fix it quickly.

## 1. Copy the files
In MetaTrader 5: **File > Open Data Folder**, then open `MQL5`.

| From this repo | To |
|---|---|
| `MQL5/Include/XAU/` (whole folder) | `MQL5/Include/XAU/` |
| `MQL5/Indicators/XAU_Oracle.mq5` | `MQL5/Indicators/` |
| `MQL5/Experts/XAU_Sniper_EA.mq5` | `MQL5/Experts/` |
| `MQL5/Presets/*.set` | `MQL5/Presets/` (or anywhere; you load them from the inputs dialog) |

The include folder **must** be `MQL5/Include/XAU/` because both programs use `#include <XAU/XAU_Platform.mqh>`.

## 2. Compile
Open MetaEditor (F4), open each `.mq5`, press **F7**. Expect 0 errors.

## 3. Indicator
1. Open an **XAUUSD** chart (any timeframe; M15 is the reference). The symbol name can be `XAUUSD`, `GOLD`, `XAUUSD.m`, etc. Everything uses the chart symbol.
2. Navigator > Indicators > XAU_Oracle, drag onto the chart.
3. Inputs to check first:
   * **Broker GMT offset.** Sessions, the Asian range and the news fallback run on the GMT clock. Auto-detection is on by default.
     If the shaded Asian box or session names look shifted, tick *Set broker GMT offset by hand* and enter your broker's offset (commonly 2 in winter, 3 in summer).
   * **Risk % and Balance override** (used only for the position-size line; 0 = your account equity).
4. Leave the chart scrolled to the latest bar. *Leave room on the right for projections* shifts the chart so the ghost candles fit.
5. Give it a minute to load history. Rebuilds happen on every new bar; the dashboard refreshes every second.

## 4. Expert Advisor
1. Tools > Options > Expert Advisors: tick **Allow algorithmic trading**. Press the **AutoTrading** toolbar button.
2. Attach `XAU_Sniper_EA` to an XAUUSD **M15** chart (one chart per symbol per magic number).
3. Load a preset: inputs dialog > **Load** > `XAU_Sniper_Balanced.set`.
4. **Start on a demo account.** See [TESTING.md](TESTING.md).
5. Optional: add a DXY-like symbol (`USDX`, `DXY`, ...) to Market Watch. Without it the EA uses EURUSD as a proxy.

## 5. Notes
* **Calendar.** News filtering uses MT5's built-in economic calendar and needs a connected terminal. It is not available in the Strategy Tester; the EA then falls back to a fixed 12:30 and 13:30 GMT window on weekdays.
* **Hedging vs netting.** On netting accounts the EA will not enter while any position exists on the symbol.
* **Tiny accounts.** One minimum lot (0.01) of XAUUSD risks about $1 per $1 of stop distance. If that exceeds your risk budget the EA skips the trade and logs why. Use a cent/micro account or a bigger balance.
* **State.** The EA keeps its peak equity, kill-switch flag and per-position management state in terminal global variables. To clear a kill-switch, start the EA once with *InpResetKill = true*, then turn it off again.
* Only one instance of the EA per symbol/magic number; change `InpMagic` if you run several.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Panel says "loading history" | Not enough bars yet; scroll back or wait for the terminal to download history |
| No projections visible | Chart shift is off or the chart is scrolled away from the newest bar |
| EA logs "signal skipped: ..." | Working as designed; the reason is in the message (spread, news, daily limit, ...) |
| EA never trades | Check AutoTrading is on, the panel status line, and the Experts tab of the Toolbox |
| Signals appear at odd hours | GMT offset wrong; set it manually |
