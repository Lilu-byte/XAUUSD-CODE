# XAUUSD Toolkit for MetaTrader 5 (v2)

An indicator (**XAU Oracle**), an Expert Advisor (**XAU Sniper**) and a data-export script for gold. One shared engine, so the chart and the robot always agree.

## Read this first
**Nothing here can guarantee profit, a fixed win-rate, or a doubled account.** What v2 does is make the tools *earn* the right to trade:
every day a **Strategy Lab** tests 8 strategies x 4 exit styles on your chart's own history and uses only a combination that won
**at least 60% of its trades with a positive average result**, measured walk-forward. When nothing qualifies, the EA stands aside on a live account.

* **Win-rate alone means little.** A target half as far as the stop wins ~67% of trades even in a random market, and still loses money after costs. The tools therefore always show win-rate **and** the average result per trade (R). See [docs/STRATEGY_LAB.md](docs/STRATEGY_LAB.md).
* **Tested on synthetic markets, not yet on real gold.** In a trending test market the full system (daily Lab + trading, replayed day by day) won **66% of trades at +0.31R** each; in a market with no edge it stood aside on 93% of days. Real XAUUSD has to be tested on your data: run `XAU_DataExport.mq5` and follow [docs/TESTING.md](docs/TESTING.md).
* **"Double every month" needs about 10% risk per trade** and fails most months even with a strong edge ([docs/RISK_MATH.md](docs/RISK_MATH.md)). The EA caps risk at 5% per trade.

## What changed in v2 (from your live screenshots)
| Seen on your screen | Fixed |
|---|---|
| "0.01 lot: lose 1.42 if stopped" for a 14.18 stop | Your broker reports the gold tick value 10x too small. Sizing now uses the broker's own profit formula (0.01 lot = 14.18 USD there), so the EA can never open 10x too large |
| Real trial: H1 42% won / -0.23R, H4 39% / -0.25R | One fixed strategy replaced by the daily Strategy Lab; the trial's fill model (which understated results by ~0.1R) replaced by a calibrated one |
| EA and indicator panels on top of each other, text running past the box | Panels size themselves to their text; EA bottom-left, indicator top-left, scoreboard bottom-right |
| Two sells without a stop loss, margin level 64% | Red RISK line in both panels when trades have no stop or the margin level is low |
| Indicator said SELL NOW while the EA said no setup | Both now run the same Lab on the same bars and trade/show the same strategy; the EA panel says which one |

## What you get
### `XAU_Oracle` (indicator)
| Feature | Detail |
|---|---|
| Simple panel | BUY NOW / SELL NOW / HOLD / EXIT NOW / WAIT, entry-stop-target, lot size in money, how long to stay, the strategy in use with its tested record |
| Green/red trade box | Red = risk to the stop, green = profit to the target(s), with labels and a "close by" time |
| Strategy Lab scoreboard | The 6 best combinations on this chart with win-rate, average R, trades and PASS marks |
| Graded history | Past entries of the strategy in use (green = proven, grey = unproven) and where each ended |
| Next candles | Pattern-matching forecast (25 most similar past situations), drawn only when it has proven itself on this chart; plus a one-line call for M15 / H1 / H4 |
| Context | Higher-timeframe trend, day range used, opening range box, yesterday's high/low, Asian range, news countdown |

### `XAU_Sniper_EA` (Expert Advisor)
* Trades exactly the Lab's choice, with its exit style: partial at the first target, break-even, trail, mean-reversion exit, time stop.
* Sizes every trade from the broker's profit formula; refuses trades the minimum lot would over-risk (live accounts).
* Daily and weekly loss limits, drawdown kill-switch, loss-streak pause with paper-trade resume, spread / session / news filters, Friday flatten.
* **Demo mode**: on demo accounts the protections only warn and it can trade the closest strategy even when none passed (labelled UNPROVEN), so you can watch it work.

### `XAU_DataExport` (script)
Saves your broker's XAUUSD history (M5 to D1) and contract details to CSV. Share the folder and every test in `research/` can be re-run on real data.

## Quick start
1. Copy `MQL5/Indicators/XAU_Oracle.mq5`, `MQL5/Experts/XAU_Sniper_EA.mq5` and `MQL5/Scripts/XAU_DataExport.mq5` into your terminal's `MQL5` folder (File > Open Data Folder). Each is one self-contained file. See [docs/INSTALL.md](docs/INSTALL.md).
2. Compile them in MetaEditor (F7).
3. Put the indicator on an XAUUSD chart (M15 or H1). Read the scoreboard: is anything marked PASS?
4. Run the EA on a demo account with `XAU_Sniper_Balanced.set` (or `XAU_Sniper_DemoTurbo.set` to watch many trades).
5. Run `XAU_DataExport` once and send the files, so the Lab can be checked against real gold.

## Repository layout
```
MQL5/Indicators/XAU_Oracle.mq5      the indicator (single file, generated)
MQL5/Experts/XAU_Sniper_EA.mq5      the EA (single file, generated)
MQL5/Scripts/XAU_DataExport.mq5     history export script
MQL5/Presets/*.set                  7 EA profiles, generated from the EA's inputs
src/                                editable sources (engine, platform layer, the three programs)
docs/                               Strategy Lab, ideas (165), research, risk maths, install, testing, reviews
research/                           bundler, preset generator, C++ harness, MT5 mock, Monte Carlo, results
```
Edit `src/`, then run `research/run_checks.sh`: it rebuilds the MT5 files and presets and re-runs every test.

## What was and was not verified
| Verified here (research/results) | Not verified (cannot be, offline) |
|---|---|
| All three programs type-check against a mock of the MT5 API | Compilation in MetaEditor itself |
| Lot sizing correct even when the broker's tick value is 10x wrong | Behaviour on real XAUUSD ticks |
| Fill model within 0.007R of minute-level truth | Profitability or win-rate on real gold |
| No look-ahead in signals, forecasts, the opening range or the Lab | Broker quirks (fills, stops level, clock) |
| EA (3,000 bars) and indicator (10,000 bars) give identical signals: 191,872 comparisons, 0 differences | Any future performance |
| On markets with no edge, the Lab and the forecaster do not invent one | |
| In a trending test market the daily Lab keeps >= 60% winners with positive expectancy | |
