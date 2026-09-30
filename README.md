# XAUUSD Toolkit for MetaTrader 5 (v2)

An indicator (**XAU Oracle**), an Expert Advisor (**XAU Sniper**) and a data-export script for gold. One shared engine, so the chart and the robot always agree.

## Read this first
**Nothing here can guarantee profit, a fixed win-rate, or a doubled account.** What v2 does is make the tools *earn* the right to trade:
every day a **Strategy Lab** tests 8 strategies x 4 exit styles on your chart's own history and uses only a combination that won
**at least 60% of its trades with a positive average result**, measured walk-forward. When nothing qualifies, the EA stands aside on a live account.

* **Win-rate alone means little.** A target half as far as the stop wins ~67% of trades even in a random market, and still loses money after costs. The tools therefore always show win-rate **and** the average result per trade (R). See [docs/STRATEGY_LAB.md](docs/STRATEGY_LAB.md).
* **Tested on your real XAUUSD history (M5 to D1, up to 22 years).** Replayed day by day exactly as the EA trades, it wins **58-65% of trades
  at about break-even** (within +-0.05R per trade) on every timeframe, at this broker's cost. The 60% win-rate goal is met; a reliable profit
  is not, and no filter tested so far supplies one. Details: [docs/REAL_DATA.md](docs/REAL_DATA.md).
* **A demo account cannot guarantee a real one.** Treat the demo as a rehearsal: same balance you would really deposit, same rules
  (the EA's default *Demo mode = Rehearsal*), and judge it after 100+ trades, not after 3.
* **"Double every month" needs about 10% risk per trade** and fails most months even with a strong edge ([docs/RISK_MATH.md](docs/RISK_MATH.md)). The EA caps risk at 5% per trade.

## What changed in round 8 (screenshots of the 3,000 USD demo)
| Seen on your screen | Changed |
|---|---|
| EA on H1 showing the M5 result, and not trading | MT5 kept the EA's M5 memory after the timeframe switch; the EA now resets on every start. Your manual trades no longer block it |
| Indicator: PASS on the scoreboard but UNPROVEN in the panel | PASS now uses exactly the rule that makes a strategy PROVEN |
| Green box drawn below a buy | The box ends at the strategy's typical winning exit; the moving exit level is a separate dotted line |
| Top of the panel hidden behind the SELL/BUY buttons | The panel starts below MT5's One Click Trading buttons |
| "Improve the predictions" | Calibrated cone (holds the price 59-61% of the time, as intended; before 51-55%) and candle sizes 14-19% more accurate, measured on your data |
| "Make the EA trade on its own" | H1 and above buy only while the daily trend is up, with a 4-year Lab on H1: proven picks on 57% of days instead of 34%, replay +0.025R at 67% won (before -0.049R). Three copies can run on M15, H1 and H4 (`XAU_Sniper_Multi_*` presets) |
| "Mix every strategy into one" | Tested as a walk-forward model over all 32 combinations: it trades 1-10 times a day at about 0R. Not adopted ([docs/REAL_DATA.md](docs/REAL_DATA.md), section 8) |

## What changed in round 7 (demo screenshot of 30 Sep 2026)
| Seen on your screen | Changed |
|---|---|
| Equity 66 of 98: two manual sells with **no stop loss**, margin level 79% | EA: no entry while free margin <= 0 or margin level < 300% (every mode). Optional *InpProtectManual* puts a stop on positions that have none |
| Weekly chart "BUY NOW", 0.01 lot = 514% of the account | Indicator: **TOO BIG, SKIP** with the balance that trade needs; no alert for trades the account cannot carry |
| EA "[DEMO - free run]" trading an UNPROVEN strategy | New *Demo mode* input, default **Rehearsal** = real-account rules. The old inputs were renamed, so the attached EA cannot keep the old values |
| Panel lines cut off | MT5 cuts labels at 63 characters; lines now wrap |
| Losses from spread on short stops (real data) | **Cost guard**: no setup with a stop shorter than 20 round-trip costs. EA replay at this broker's cost: M5 -0.17R -> -0.01R, M15 -0.02R -> +0.01R per trade |

**Account size.** 0.01 lot of gold moves 1 USD per 1 USD. For 1% risk at 0.01 lot you need roughly 550 USD on M5, 1,100 on M15,
2,400 on H1 and 5,300 on H4 (Sep 2026 volatility). On about 100 USD every trade risks 5-25% of the account. Open a demo with the balance you
would really deposit, or use a cent account.

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
| Next candles | Calibrated 60% range cone and the expected size of each coming candle (measured on your data); a predicted direction only where the pattern match has proven itself on this chart; expected next-candle size for M15 / H1 / H4 |
| Context | Higher-timeframe and daily trend, day range used, opening range box, yesterday's high/low, Asian range, news countdown |

### `XAU_Sniper_EA` (Expert Advisor)
* Trades exactly the Lab's choice, with its exit style: partial at the first target, break-even, trail, mean-reversion exit, time stop.
* Sizes every trade from the broker's profit formula; refuses trades the minimum lot would over-risk (live accounts).
* Daily and weekly loss limits, drawdown kill-switch, loss-streak pause with paper-trade resume, spread / session / news filters, Friday flatten.
* **Demo mode**: *Rehearsal* (default) runs a demo exactly like a real account. *Free run* (or the DemoTurbo preset) turns the protections into warnings and can trade the closest strategy when none passed (labelled UNPROVEN), capped at 10% of equity per trade, so you can watch it work.
* Cost guard, margin and spread checks before every entry; optional stops for your own trades that have none.

### `XAU_DataExport` (script)
Saves your broker's XAUUSD history (M5 to D1) and contract details to CSV. Share the folder and every test in `research/` can be re-run on real data.

## Quick start
1. Copy `MQL5/Indicators/XAU_Oracle.mq5`, `MQL5/Experts/XAU_Sniper_EA.mq5` and `MQL5/Scripts/XAU_DataExport.mq5` into your terminal's `MQL5` folder (File > Open Data Folder). Each is one self-contained file. See [docs/INSTALL.md](docs/INSTALL.md).
2. Compile them in MetaEditor (F7).
3. Put the indicator on an XAUUSD chart (M15 or H1). Read the scoreboard: is anything marked PASS?
4. **Remove the old EA from the chart and attach it again** (MT5 keeps an attached EA's old inputs after a recompile), then load `XAU_Sniper_Balanced.set` on a demo account (or `XAU_Sniper_DemoTurbo.set` to watch many trades).
   For more trades, attach it to three XAUUSD charts, M15, H1 and H4, with `XAU_Sniper_Multi_M15.set`, `_H1.set` and `_H4.set`.
5. Run `XAU_DataExport` once and send the files, so the Lab can be checked against real gold.

## Repository layout
```
MQL5/Indicators/XAU_Oracle.mq5      the indicator (single file, generated)
MQL5/Experts/XAU_Sniper_EA.mq5      the EA (single file, generated)
MQL5/Scripts/XAU_DataExport.mq5     history export script
MQL5/Presets/*.set                  7 EA profiles, generated from the EA's inputs
src/                                editable sources (engine, platform layer, the three programs)
docs/                               Strategy Lab, ideas (226), real-data results, research, risk maths, install, testing, reviews
research/                           bundler, preset generator, C++ harness, MT5 mock, Monte Carlo, results
```
Edit `src/`, then run `research/run_checks.sh`: it rebuilds the MT5 files and presets and re-runs every test.

## What was and was not verified
| Verified here (research/results) | Not verified (cannot be, offline) |
|---|---|
| All three programs type-check against a mock of the MT5 API | Compilation in MetaEditor itself |
| Lot sizing correct even when the broker's tick value is 10x wrong | Behaviour on real XAUUSD ticks |
| Fill model within 0.007R of minute-level truth | Future profitability on real gold (the past, replayed: about break-even, 58-65% winners) |
| No look-ahead in signals, forecasts, the opening range or the Lab | Broker quirks (fills, stops level, clock) |
| EA (3,000 bars) and indicator (10,000 bars) give identical signals: 191,872 comparisons, 0 differences | Any future performance |
| On markets with no edge, the Lab and the forecaster do not invent one | |
| In a trending test market the daily Lab keeps >= 60% winners with positive expectancy | |
