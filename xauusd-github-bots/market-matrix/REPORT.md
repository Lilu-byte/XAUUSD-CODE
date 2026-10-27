# Market Matrix (Zeiierman): what it really does, and whether it makes money on gold

17 Oct 2026. David sent the TradingView Pine Script source of "Market Matrix (Zeiierman)" with: "Reverse engineer this and see what's up". I read all of it (about 1,245 lines of Pine), rebuilt every number its panels show in Python (`code/mm.py`; the drawing itself, colours, Fibonacci and regression channel are not ported), turned each panel into the trade a chart reader would take from it, and tested those on David's MT5 gold data (to the 9 Oct 2026 close) and on older OANDA data, after spread, slippage and swap. Independent checks then rebuilt the port, the main backtests and the main figures with separate code, and a last check went through this report number by number (see "Checks").

## Bottom line

- **It is a dashboard, not a trading system.** It draws six small charts of the daily timeframe to the right of your price chart: daily candles with 20/50/200 averages and a "swing VWAP", RSI, MACD, and three of Zeiierman's own oscillators (Relative Trend Index, Absolute Strength Index, Range Oscillator). On the main chart it adds an 89 EMA with a glow band and volume bars. It has no buy or sell signals and no alerts, and the panels are drawn from scratch on the last bar only, so there is no bar-by-bar record of what they said and TradingView's Strategy Tester can't test it (Bar Replay can show what they looked like on a past day). It's Pine Script, so it can't run in MT5 as it is.
- **The code is safe.** It makes no web requests and asks for nothing. Its licence (CC BY-NC-SA 4.0) lets you use and adapt it for yourself with credit to Zeiierman; it can't be sold or used for a paid service, and any shared copy must carry the same licence.
- **The daily data is fetched correctly** (no peeking at future days). The newest point of every panel, including the averages and the swing VWAP's direction, is the still-forming day and moves until the day closes.
- **The swing VWAP and its HH / HL / LH / LL labels rewrite history.** Each turn is drawn at the swing's top or bottom (65 of 67 times exactly), but it only becomes known when price makes a new 50-day extreme the other way. On daily gold since 2004 that came a median 29 trading days and 8.3% after the drawn turn. The 29 Jan 2026 top at 5,598 was only marked on 23 Mar, with gold at 4,406. 36% of past days had their line colour changed afterwards. This is why the panel looks like it catches every turn.
- **The Range Oscillator's ±100 lines don't mark extremes on the daily panel.** They are scaled to a long-run average of the daily range (ATR over 2,000 days, which on TradingView mostly reflects 2016-2023). The oscillator sat beyond ±100 on 21-66% of days in every year from 2005 to 2024, and on 87% of 2026's days, because gold's daily range now is 2.5 times that average.
- **The panels overlap a lot.** Read as bullish or bearish, the seven readings (the first panel gives two) have an average correlation of 0.50; they are all trend or momentum measures.
- **No reading beat simply holding gold in dollars in every period.** I tested 18 readings plus a "panels agree" vote at four thresholds (22 rules), each long+short and long only, on daily, 4-hour and 1-hour bars. Each was picked on earlier years and scored on later ones; the 4-hour and 1-hour rules were also run on OANDA 2007-2016, which nothing was tuned on. In dollars, the rule that did best on the earlier years never beat holding on the later years, and no rule beat holding in every period.
- **Reversal readings win most trades and still don't pay.** RSI 30/70, RTI 20/80, ASI ±8 and Range Oscillator fades win 54-85% of trades. Long+short they lose or roughly break even; long only they make far less than holding, and none held up across periods.
- **Adding shorts lowered the risk-adjusted return** in all 66 MT5 tests and all 42 OANDA tests that traded (in dollars it occasionally added a little).
- **The best of it is a plain long-only trend filter: the 4-hour "MA stack"** (long while close > 20 > 50 > 200 average). In every period it was about level with or better than holding gold on risk (Sharpe 0.42 vs 0.42 on OANDA, 0.45 vs 0.21 on 2014-21, 1.20 vs 0.91 on 2022-26) with a fifth to a half of holding's drawdown, but it made less money than holding on 2022-2026 ($1.45 a day vs $1.74) and on OANDA. It's a similar long-only trend bet to GoldAllAgree (weekly correlation 0.55 with the pair; both went flat on 26 Aug). Added to the pair on May 2025 to Oct 2026 it would have lifted $4.68 to $7.47 a day, with the worst drawdown going from $285 to $441 and losing months from 6 to 7 of 18.
- **The last reading in my data** (9 Oct close, 4,195): read as trend signals, six of seven are bearish. Only the swing VWAP still reads "up", because its last new 50-day extreme was a high on 25 Aug, which shows how slowly it turns. RSI and ASI are above their own signal lines (turning up), and the Range Oscillator at -205 would look "oversold" to someone fading it. Your chart has a week more bars than my data; the VWAP direction flips down on a new 50-day low (below about 4,017 as of 9 Oct).
- **Verdict:** fine as a picture of the daily trend if you like how it looks; don't trade from it. Keep GoldAllAgree + GoldAsiaBreak as the MT5 setup.

## What each panel actually computes

| Panel | What the code does | In plain terms |
|---|---|---|
| Daily candles + 20/50/200 averages | Simple averages of daily closes (including the forming day) | Standard trend picture |
| Swing anchored "VWAP" | Finds the latest new 50-bar high and low; direction = whichever came last. On each flip it restarts a volume-weighted average with a 20-bar half-life from that extreme and **redraws** the line back to it | A slow trend line that looks perfect in hindsight. Volume on gold CFDs is tick count; with no volume (e.g. TVC:GOLD) the line isn't drawn |
| RSI | RSI(14) with a 9-bar average, 70/30 lines | Standard |
| MACD | 12/26/9, histogram coloured by rising or falling | Standard |
| Relative Trend Index | Where the close sits between the 95th-percentile high and 5th-percentile low of the last 100 bars (of close ± half the last bar's move), with a 20-bar EMA | A 100-bar stochastic with outliers cut (correlation 0.997); outside 0-100 about 21% of the time |
| Absolute Strength Index | The 15-bar return placed between the 3rd-largest and 3rd-smallest of the previous 15 one-bar returns, scaled so those map to +1 and -1; 14-bar average; ±8 lines | 15-day momentum divided by daily volatility (correlation 0.97); ±8 is about a 2-sigma 15-day move |
| Range Oscillator | Distance of the close from a 50-bar average where each bar is weighted by how far it moved, in units of 2 × ATR(2000); colours from how often it visited that level in the last 100 bars | Price vs a move-weighted average, scaled to a long-run daily range |
| Main chart | 89 EMA with a ±0.1 ATR band, last 135 bars of volume, optional Fibonacci and regression channel | Cosmetic |

## Test results

Each reading becomes a position (long, short or flat) decided on a closed bar and taken at the next bar's open, one 0.01 lot, no stops (the indicator has none). Costs: spread $0.30, slippage $0.10 on entry and on exit ($0.50 a round trip), swap $0.126 long / $0.046 short a night (triple on Wednesday; scaled to the gold price before 2016). Periods: daily rules picked on 2005-2015 and scored on 2016-2026; 4-hour rules on 2014-2021 and 1-hour on 2017-2021, both scored on 2022-2026 and also run on OANDA 2007 to mid-2016. Sharpe is on gold-price returns (on the dollar P&L of a fixed 0.01 lot, holding's Sharpe drops more than most rules', so a few more rules come out level with it). Full tables: `results.csv`, `oanda_2007_2016.csv`.

| | Daily (scored 2016-26) | 4-hour (scored 2022-26) | 1-hour (scored 2022-26) | OANDA 2007-16 (4-hour / 1-hour) |
|---|---|---|---|---|
| Holding 0.01 lot long | $0.95/day, Sharpe 0.70, drawdown $1,458 | $1.74/day, Sharpe 0.91, drawdown $1,458 | same as 4-hour | $0.22/day, Sharpe 0.42, drawdown $916 |
| Rules that beat holding in $ | 0 of 44 | 0 of 44 | 5 of 44, none of them in every period | 9 / 3 of 42 that traded |
| Best rule on the earlier years, then scored | ASI vs its signal, long only: $0.28/day, Sharpe 0.38 | MA stack, long only: $1.45/day, Sharpe 1.20, drawdown $452 | Range Osc breakout, long only: $1.24/day, Sharpe 0.95, drawdown $716 | |
| Reversal readings: win rate, $/day | 54-85%, -$0.81 to +$0.13 | 57-78%, -$1.84 to +$0.84 | 55-74%, -$2.50 to +$0.43 | |
| Median Sharpe, long+short vs long only | 0.14 vs 0.48 | 0.06 vs 0.73 | 0.12 vs 0.79 | |

The three long-only rules that were level with or better than holding's Sharpe in all three periods, at two decimals ($/day, Sharpe, worst drawdown; holding in brackets):

| Rule | OANDA 2007-16 | MT5 earlier years | 2022-26 | Beats the same trades shifted in time (earlier / 2022-26) |
|---|---|---|---|---|
| 4-hour MA stack 20/50/200 | $0.18, 0.42, $183 ($0.22, 0.42, $916) | 2014-21: $0.18, 0.45, $215 ($0.13, 0.21, $407) | $1.45, 1.20, $452 ($1.74, 0.91, $1,458) | 96% / 100% |
| 4-hour MACD line above zero | $0.24, 0.57, $547 | 2014-21: $0.09, 0.21, $296 | $1.48, 0.97, $1,130 | 75% / 89% |
| 1-hour Range Osc +100 breakout, exit at 0 | $0.19, 0.49, $291 | 2017-21: $0.35, 0.72, $163 ($0.30, 0.42, $407) | $1.24, 0.95, $716 | 98% / 90% |

Unrounded, only the 1-hour breakout is strictly above holding in all three periods; the MA stack is a hair below on OANDA (0.417 vs 0.422) and the MACD line on 2014-21 (0.206 vs 0.208). All three are long-only trend filters: they earn mainly by being out of gold while it falls, so they made less than holding in the strong 2022-26 rise, though some made a little more in flatter periods. The MA stack had the smallest drawdowns on OANDA and 2022-26 and still works if filled one bar later ($1.31/day, Sharpe 1.02 on 2022-26). The MACD line's drawdowns were 60-78% of holding's. The shifted-timing figures move by a few points from run to run.

Rules that look good on recent data alone are not to be trusted: the 1-hour "5 of 7 panels agree" made $1.93 a day on 2022-26, but $0.39 on 2022-24 (holding $0.85), about $0 on 2017-21 and -$0.30 on OANDA, and it halves if filled one bar later.

## Files

- `code/mm.py`: Python port of the panel series (defaults as in the script).
- `code/test_rules.py`: the rules, the cost model and scoring; `results.csv`.
- `code/diagnostics.py`: redraw, Range Oscillator bounds, panel correlation, last reading, timing tests, pair combination; `diagnostics.json`, `swing_anchors_D1.csv`, `panel_vote_correlation_D1.csv`.
- `code/oanda_check.py`: OANDA 2007-2016 run, reading the OANDA file cloned to /tmp/claude-0/portfolio-oanda; `oanda_2007_2016.csv` (OANDA has no volume, so the "VWAP + price side" rows have no trades there).
- `code/extra_checks.py`: 200-copy timing tests for the table above; `extra_checks.json`.
- `verify-port/`, `verify-backtest/` (includes the one-bar-later fills and the 2022-24 split in `lookahead_results.json` and `extras_results.json`), `verify-claims/`, `verify-final/`: the independent checks.

## Checks

- **Port** (`verify-port/`): every series rewritten from the Pine code alone, with Pine's own seeding rules. After warm-up they agree with `mm.py` (largest gap 0.09 on the 89 EMA in 2005, under 0.0005 for the rest apart from the ATR point below; the sign differs on 1 daily and 4 intraday bars out of tens of thousands), and the swing VWAP and all 67 turns are identical. The data requests can't see the future; only the 89 EMA band is plotted bar by bar. One real difference: TradingView computes ATR(2000) inside a 2,700-bar window while `mm.py` uses all history, so the Range Oscillator's size differs by 0-14% on daily bars (its sign never changes). The ±100 rules move by up to $0.83 a day on May 2025-Oct 2026 (the 1-hour long+short breakout falls from $1.28 to $0.45); the 1-hour long-only breakout above is unchanged ($1.90 on that window, $1.24 to $1.25 on 2022-26).
- **Backtests** (`verify-backtest/`): four of the rules plus holding, rebuilt with the other engine (`../code/gbt.py`) and separately written rule code, match day by day from 2016 (apart from $0.10 on the last day for rules still open). Cutting or changing future bars leaves every position unchanged, so there is no look-ahead. The pair figures reproduce exactly on the same booking; booking the pair mark-to-market instead gives a pair drawdown of $245 and pair + MA stack $432. The daily earlier-years Sharpes depend on scaling the swap to the gold price before 2016 (daily MACD line 0.45 scaled vs 0.30 with today's fixed swap). `gbt.simulate` leaves out a trade still open on the last bar; it doesn't affect anything here, because `test_rules.py` uses its own loop.
- **Claims** (`verify-claims/`): the redraw, Range Oscillator, ASI/RTI, panel correlation, last-bar and MA stack figures reproduced with separate code. The checker corrected my first draft: some 1-hour rules beat holding on OANDA, more than one rule held up on risk, the MA stack made more than holding on 2014-21, and some long-only reversal rules made money on 2022-26.
- **Final read-through** (`verify-final/`): every figure in this report checked against the files; its corrections (rule counts, rounding, the dollar-based Sharpe, wording) are included above.
