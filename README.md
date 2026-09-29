# XAUUSD Toolkit for MetaTrader 5

An indicator (**XAU Oracle**) and an Expert Advisor (**XAU Sniper**) for gold, built on one shared
signal engine so the chart and the robot always agree.

## Read this first

**Nothing here can guarantee profit, a fixed win-rate, or a doubled account.** No strategy can, and this
one has not been proven on real XAUUSD data (the environment it was built in had no market-data access).
What it *does* give you is a disciplined system, honest self-measurement on your own broker's data, and
risk controls that stop a bad month from becoming a blown account.

* **Win-rate is not the goal, expectancy is.** Any strategy can show a "high win-rate" by taking tiny profits
  and risking large losses. The tools report win-rate *and* expectancy (average R per trade) and profit factor.
* **"Double every month" needs about 10% risk per trade** even with a genuinely strong edge, and even then it
  fails most months and suffers 30%+ drawdowns about half the time. With no edge it destroys the account.
  The numbers are in [docs/RISK_MATH.md](docs/RISK_MATH.md). The EA caps risk per trade at 5% on purpose.
* **Validate before you trust it.** Follow [docs/TESTING.md](docs/TESTING.md): read the indicator's on-chart
  trial, then run the Strategy Tester on real ticks, then forward-test on demo.

## What you get

### `XAU_Oracle` (indicator)
| Feature | Detail |
|---|---|
| Graded entries | Buy/Sell arrows graded **B / A / A+** by confluence score. Closed-bar logic: **never repaints**. |
| Full trade plan | Entry, stop, TP1, TP2 drawn on the chart, plus a **time-stop line** ("exit by 14:30"). |
| Position size | Lots, money at risk and margin for *your* balance and risk %. Refuses to over-risk tiny accounts. |
| Hold guidance | Typical time to first target (measured from the indicator's own trial), status: BUY NOW / IN TRADE / EXIT NOW / MISSED / WAIT / AVOID. |
| Projected candles | Next N candles as ghost candles with an expected-range cone (statistical expectation, with its own hit-rate audit shown). |
| Trial on your data | Win-rate, TP1 hit-rate, profit factor, expectancy by grade and by strategy module, over the loaded history. |
| Context | Higher-timeframe bias, M5-D1 trend strip, session, ATR, spread, prev-day high/low, Asian range, VWAP, news countdown. |
| Alerts | Popup, sound, push, email. |

### `XAU_Sniper_EA` (Expert Advisor)
* Same engine and rules as the indicator. One trade at a time by default.
* Fixed-fractional sizing on equity, reduced after loss streaks (optional scaling by setup grade, off by default). Refuses trades when the minimum lot would over-risk.
* Account protection: daily loss limit, weekly loss limit, **drawdown kill-switch**, max trades/day, pause after N losses, cooldown.
* Filters: spread (absolute and vs ATR), session window, high-impact USD news (MT5 calendar), Friday cut-off and weekend flatten.
* Management: partial close at TP1, stop to break-even, ATR chandelier trail, time stop, retry on requotes.
* Restart-safe (state kept in terminal global variables); Strategy Tester custom criterion for optimisation.

### The strategy in one paragraph
Eight independent modules vote each closed bar: trend pullback, liquidity sweep, Asian-range breakout,
volatility squeeze break, VWAP-extreme fade, RSI divergence, fair-value-gap retest, round-number
rejection. The higher-timeframe trend and a DXY/EURUSD proxy add or subtract weight. A signal needs a
minimum score **and** at least two agreeing modules, plus session, volatility and spread filters.
The stop is structural (with ATR floor/ceiling); targets are multiples of that risk.
Details: [docs/RESEARCH.md](docs/RESEARCH.md), [docs/IDEAS.md](docs/IDEAS.md) (90+ ideas, built/rejected and why), [docs/IMPROVEMENTS.md](docs/IMPROVEMENTS.md) (20 further improvements) and [docs/REFERENCE_REVIEW.md](docs/REFERENCE_REVIEW.md).

## Quick start
1. Copy the two files `MQL5/Indicators/XAU_Oracle.mq5` and `MQL5/Experts/XAU_Sniper_EA.mq5` into your terminal's data folder (File > Open Data Folder > MQL5). Nothing else to install. See [docs/INSTALL.md](docs/INSTALL.md).
2. Compile `XAU_Oracle.mq5` and `XAU_Sniper_EA.mq5` in MetaEditor (F7).
3. Attach the indicator to an XAUUSD M15 chart. Read the **TRIAL** block first.
4. Run the EA in the Strategy Tester (Every tick based on real ticks) with `Presets/XAU_Sniper_Balanced.set`.
5. Demo-trade for at least four weeks before risking real money, starting at 0.25-0.5% risk.

## Repository layout
```
MQL5/Indicators/XAU_Oracle.mq5      the indicator (single self-contained file, generated)
MQL5/Experts/XAU_Sniper_EA.mq5      the EA (single self-contained file, generated)
MQL5/Presets/*.set                  five EA risk profiles
src/                                editable sources: XAU_Core.mqh (engine), XAU_Platform.mqh (MT5 glue), the two mains
docs/                               ideas, research notes, risk maths, install/testing, reference review, improvements
research/                           bundler, C++ harness, mock MT5 API, Monte Carlo, saved results
```
Edit `src/`, then `python3 research/bundle.py` (or `research/run_checks.sh`) regenerates the two MT5 files.

## What was and was not verified
| Verified here | Not verified (cannot be, offline) |
|---|---|
| Sources type-check as C++ against a mock of the MT5 API (`research/run_checks.sh`) | Compilation in MetaEditor itself |
| Engine has **no look-ahead** (signals on truncated history are identical); indicator and EA windows give the same signals | Behaviour on real XAUUSD ticks |
| Trade simulator and lot sizing unit-tested, incl. refusal to over-risk | Profitability, win-rate, drawdown on real data |
| No-edge control: strategy does **not** invent an edge from noise | Broker-specific quirks (fills, stops level, GMT offset) |
| Regime stress tests show where it wins and loses (trending vs mean-reverting) | Any future performance |

`research/run_checks.sh` regenerates everything in `research/results/`.
