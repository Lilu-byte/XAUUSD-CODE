# 250+ ideas, and what happened to each

Status key: **BUILT** = in the code and on by default. **BUILT (off)** = in the code, off by default. **TESTED - rejected** = tried,
did not survive. **BACKLOG** = sensible, not done. **REJECTED** = deliberately not done, with the reason.
Nothing here is proven on real XAUUSD; "BUILT" means it exists and behaves as specified (see `research/results/`).

## A. Market structure and price action
| # | Idea | Status | Note |
|--:|---|---|---|
| 1 | Higher-timeframe trend bias (EMA50/200 + ADX) gates and weights every setup | BUILT | Counter-trend setups are *penalised*, not just ignored |
| 2 | Trend pullback to EMA21 with RSI reset and a rejection candle | BUILT | Module PB. Needs base-timeframe ADX >= 18 |
| 3 | Liquidity sweep of previous-day high/low | BUILT | Module SW (stop-hunt then close back inside) |
| 4 | Sweep of the Asian-session range | BUILT | Part of SW |
| 5 | Sweep of the 30-bar swing high/low | BUILT | Part of SW |
| 6 | Asian-range compression breakout at London open | BUILT | Module BO. Range must be <= 0.7 x average daily range |
| 7 | Fair-value-gap (three-candle imbalance) retest | BUILT | Module FG. Up to 6 live zones per side, 40-bar life |
| 8 | Order-block entries | REJECTED | Too subjective to code without hindsight; FVG covers the imbalance idea |
| 9 | Break of structure / change of character as a standalone trigger | BACKLOG | Pivots exist (used by divergence) |
| 10 | Round-number ($10 / $50) rejection | BUILT | Module RN, deliberately low weight (0.3) |
| 11 | New York opening-range breakout | BACKLOG | Overlaps BO |
| 12 | Inside-bar / NR7 compression | BUILT | Covered by the squeeze module |

## B. Momentum and volatility
| # | Idea | Status | Note |
|--:|---|---|---|
| 13 | Bollinger-bandwidth squeeze into Donchian break | BUILT | Module SQ |
| 14 | RSI divergence at confirmed swing pivots | BUILT | Module DV, 3-bar fractal, no look-ahead |
| 15 | ADX regime filters for trend modules | BUILT | Stopped trend pullbacks in chop (small gain on synthetic data) |
| 16 | Every distance scales with ATR | BUILT | Same rules work on M1 to D1 |
| 17 | Stand aside when ATR > 2.6x its 100-bar average | BUILT | Avoids news spikes |
| 18 | Stand aside when ATR < 0.6x its average | BUILT | Avoids dead markets where spread dominates |
| 19 | Kaufman efficiency-ratio regime score | BACKLOG | |
| 20 | Session VWAP +/-2 sigma fade in low-ADX | BUILT | Module VW (tick-volume VWAP) |
| 21 | Volatility percentile of Bollinger width over 100 bars | BUILT | Feeds the squeeze module |
| 22 | Multi-timeframe momentum alignment | BUILT | M5-D1 strip in the indicator panel |

## C. Time and session
| # | Idea | Status | Note |
|--:|---|---|---|
| 23 | Trade London + New York only (07:00-20:00 GMT default) | BUILT | Inputs are on the GMT clock, converted from broker time |
| 24 | Avoid the rollover / thin hours | BUILT | Outside the window |
| 25 | No new entries late Friday; flatten before the weekend | BUILT | 19:00 cut-off, 20:30 flatten (GMT) |
| 26 | Intraday range seasonality (mean range by hour) shapes the projection | BUILT | Forecast only |
| 27 | London fix (10:30 / 15:00 GMT) awareness | BACKLOG | |
| 28 | Day-of-week effects | REJECTED | Unstable, weak evidence |
| 29 | Monthly seasonality (e.g. strong Jan, Aug-Sep) | REJECTED | Too few independent observations to trade |

## D. Fundamentals, intermarket, news
| # | Idea | Status | Note |
|--:|---|---|---|
| 30 | DXY inverse-correlation vote | BUILT | Auto-detects USDX/DXY/DX; falls back to EURUSD (positively correlated). Small weight |
| 31 | US 10-year / real-yield filter | BACKLOG | Real yields are gold's main driver but need a data feed most MT5 brokers lack |
| 32 | Economic-calendar block: +/-30 min around high-impact USD events | BUILT | Uses the MT5 calendar |
| 33 | Static US-data window fallback (12:30 / 13:30 GMT) when the calendar is unavailable (Strategy Tester) | BUILT | |
| 34 | Trade the news release itself | REJECTED | Spread widening and slippage dominate |
| 35 | Gold/silver ratio confirmation | BACKLOG | |
| 36 | Risk-on/off proxy (equity index, VIX) | BACKLOG | |
| 37 | Central-bank buying / ETF-flow bias | REJECTED for intraday | Data is slow and weekly |
| 38 | Swap awareness (long gold pays financing on most brokers) | BACKLOG | Time stop already limits holding cost |

## E. Trade management
| # | Idea | Status | Note |
|--:|---|---|---|
| 39 | Structural stop plus ATR buffer, clamped between 0.9 and 2.6 ATR | BUILT | Too-wide setups are skipped, not squeezed |
| 40 | Partial at TP1 (1R), stop to break-even + spread | BUILT | Raises the share of winning trades |
| 41 | ATR chandelier trail on the runner | BUILT | |
| 42 | Time stop (default 8 h) | BUILT | Trades that go nowhere are closed |
| 43 | Broker-side SL and TP always set | BUILT | Protects if the terminal disconnects |
| 44 | Pyramiding into winners | REJECTED | Raises tail risk; would need its own risk budget |
| 45 | Three-target scale-out ladder | BACKLOG | |
| 46 | Move to break-even before scheduled news | BACKLOG | |

## F. Risk and money management
| # | Idea | Status | Note |
|--:|---|---|---|
| 47 | Fixed-fractional risk on equity (compounds automatically) | BUILT | |
| 48 | Risk scaled by setup grade (B 0.6x, A 1.0x, A+ 1.4x) | BUILT (off) | **Tested - no evidence grades predict outcome** (grade A was not better than B in any synthetic world; A+ has too few trades to say). Enable only if your own Trial shows A/A+ beat B |
| 49 | Risk cut after two consecutive losses | BUILT | Anti-martingale. Martingale is never used |
| 50 | Daily and weekly loss limits | BUILT | |
| 51 | Drawdown kill-switch from peak equity, persists across restarts | BUILT | |
| 52 | Max trades per day, cooldown after a loss, pause after N losses | BUILT | |
| 53 | Refuse a trade when the minimum lot would over-risk | BUILT | Unit-tested |
| 54 | Cap on margin used per trade | BUILT | |
| 55 | Absolute lot cap and 5% per-trade ceiling | BUILT | |
| 56 | Volatility-targeted sizing (risk shrinks in high-ATR regimes) | BACKLOG | |
| 57 | Netting vs hedging account awareness | BUILT | |

## G. Visuals and experience
| # | Idea | Status | Note |
|--:|---|---|---|
| 58 | Graded Buy/Sell arrows | BUILT | |
| 59 | Entry / stop / TP1 / TP2 lines with labels | BUILT | |
| 60 | Time-stop vertical line and "exit by HH:MM" | BUILT | |
| 61 | Projected ghost candles and expected-range cone | BUILT | Statistical expectation, not a prophecy |
| 62 | Traffic-light dashboard: BUY NOW / IN TRADE / EXIT NOW / MISSED / WAIT / AVOID | BUILT | |
| 63 | Position-size calculator for your balance | BUILT | |
| 64 | Multi-timeframe trend strip | BUILT | |
| 65 | Popup, sound, push and email alerts | BUILT | |
| 66 | "Missed - do not chase" when price ran > 0.35 ATR past entry | BUILT | |
| 67 | Warning when an opposite setup appears during a trade | BUILT | |
| 68 | Previous-day high/low and Asian range drawn on chart | BUILT | |
| 69 | Historical exit markers (tick/cross) | BUILT | |

## H. Honesty and validation
| # | Idea | Status | Note |
|--:|---|---|---|
| 70 | On-chart trial: win-rate, TP1 rate, profit factor, expectancy by grade and by module, on **your** broker's data | BUILT | |
| 71 | Forecast self-audit: how often the direction call was right vs a 50% coin flip | BUILT | |
| 72 | Non-repainting closed-bar logic, proven by a causality test | BUILT | |
| 73 | One shared engine so the indicator and EA cannot disagree | BUILT | |
| 74 | Pessimistic simulator (a bar touching stop and target counts as stopped) | BUILT | Measured bias about -0.1R; see RESEARCH.md |
| 75 | No-edge control world: the strategy must not find profit in noise | BUILT | Passed |
| 76 | Regime stress worlds: trending, mean-reverting, alternating | BUILT | Shows regime dependence, see below |
| 77 | Walk-forward module gating (switch off modules with negative trailing trial) | BUILT (off) | **Tested - it hurt** when regimes flip faster than the lookback (-0.02R to -0.27R). Off by default |
| 78 | Custom optimisation criterion (recovery factor x profit factor x sqrt trades) | BUILT | Discourages curve-fits that win on a few huge trades |

## I. Second round: "even more"
| # | Idea | Status | Note |
|--:|---|---|---|
| 79 | Restart-safe position state in global variables | BUILT | |
| 80 | Tester-safe state (cleared at init/deinit) | BUILT | Stops optimisation passes leaking state |
| 81 | Retry on requote / price change / off quotes | BUILT | Not on timeouts (avoids duplicate orders) |
| 82 | Spread filter absolute and as % of ATR | BUILT | |
| 83 | Refuse to trade without higher-timeframe history | BUILT | |
| 84 | Auto GMT-offset detection with manual override | BUILT | DST across old history is approximate |
| 85 | Per-module expectancy shown live in the panel | BUILT | |
| 86 | Machine-learned scorer on module votes | BACKLOG | Needs real data and rigorous walk-forward |
| 87 | Portfolio: XAUUSD + XAGUSD | BACKLOG | |
| 88 | Monte Carlo of your own trade history | BACKLOG | `montecarlo.cpp` is the starting point |
| 89 | Trade journal CSV export | BACKLOG | |
| 90 | Session-specific parameter sets | BACKLOG | Beware overfitting |
| 91 | Prop-firm rule pack (trailing drawdown, consistency rule) | BACKLOG | Daily-loss and drawdown limits exist |
| 92 | Telegram alerts | BACKLOG | Needs WebRequest allow-list |

## What the stress worlds taught (synthetic data, so mechanics only)

| World | Composite expectancy | Reading |
|---|---:|---|
| No edge (random walk) | -0.14R (about -0.04R is modelled cost, the rest is simulator pessimism) | Correct: no invented edge |
| Trending (planted drift) | +0.06R | Trend modules profit; counter-trend modules lose |
| Mean-reverting | -0.37R | A trend-following system loses in a mean-reverting market. This is the strategy's real risk |
| Alternating regimes, ungated | -0.02R | Wins and losses roughly cancel |
| Alternating regimes, walk-forward gated | -0.27R | Gating lags the regime and makes things worse |

The takeaway is uncomfortable but useful: **the outcome depends on whether real XAUUSD, on your timeframe and broker, behaves
more like the trending or the mean-reverting world.** That is what the indicator's Trial block and the Strategy Tester tell you.

## Round 3 additions
| # | Idea | Status | Note |
|--:|---|---|---|
| 93 | Data-driven pattern recognition (nearest-neighbour analogs over 37 features) instead of fixed candlestick patterns | BUILT | Candlestick patterns alone mostly fail after costs (see FORECASTING.md); they live on as context features |
| 94 | Forecast confidence gate from a walk-forward audit | BUILT | |
| 95 | Pattern-match veto of trade setups | BUILT (on) | Small, consistent gain in simulation |
| 96 | Green/red position box on the chart | BUILT | |
| 97 | Demo mode that cannot lock the EA out | BUILT | Real accounts keep all protections |
| 98 | Opening range breakout (GOLD_ORB rules: initial range, extension, settle count, close-beyond signal, wick guard) | BUILT | Module 9 and solo mode |
| 99 | Paper-trade ledger to resume after a pause (GOLD_ORB virtual environment) | BUILT | |
| 100 | One-long-one-short-per-day limit for breakouts | BUILT | Inside the ORB module |
| 101 | Equity-slope detection to resume (GOLD_ORB) | REJECTED | Paper-trade recovery is simpler and uses the same simulator |
| 102 | Fixed-point stops and targets | REJECTED | Not portable across price levels; ATR-scaled instead |

## Round 5: 50 new ideas for a 60%+ win-rate that also makes money
Status: **BUILT** (in the code, tested), **BUILT (option)**, **TESTED-OFF**, **PROPOSED**, **REJECTED**.

### A. Measuring honestly (you cannot improve what you mis-measure)
| # | Idea | Status | Note |
|--:|---|---|---|
| 103 | Replace the "stop always wins" fill rule with the candle's likely path (O-L-H-C / O-H-L-C) | BUILT | Old rule understated results by ~0.1R per trade; new one is within 0.007R of minute-level truth |
| 104 | Calibrate the simulator against a minute-by-minute replay | BUILT | `harness calib` |
| 105 | Gaps through a level fill at the open, not at the level | BUILT | Weekend gaps |
| 106 | Report expectancy next to win-rate everywhere | BUILT | Scoreboard, panel, EA log |
| 107 | Walk-forward record for any automatic choice | BUILT | Panel quotes it in AUTO mode |
| 108 | Live replay: re-run the daily Lab over history exactly like the EA | BUILT | `harness replay` |
| 109 | Real-data path: export your broker's history and re-run every test on it | BUILT | `XAU_DataExport.mq5` + `harness real` |
| 110 | Statistical margin (1 standard error) before calling a strategy profitable | BUILT | |

### B. Exits that raise the share of winners
| # | Idea | Status | Note |
|--:|---|---|---|
| 111 | High-hit exit: 70% off at 0.5R, break-even, runner to 1.5R | BUILT | 66.7% winners even with no edge |
| 112 | Quick exit: everything at 0.6R | BUILT | 62.7% winners with no edge |
| 113 | Mean-reversion exit on the close back over the 5-bar mean (Connors) | BUILT | For dip strategies |
| 114 | Wider stops for mean-reversion trades (1.5-3.2 ATR) | BUILT | Part of the profile |
| 115 | Lock a small profit instead of plain break-even after the first target | BUILT (field) | `be_lock_r`; not used by default |
| 116 | Time stop per exit style (12 bars for mean reversion) | BUILT | |
| 117 | Exit style chosen per strategy by the Lab, not globally | BUILT | 32 combinations |
| 118 | Limit entries a fraction of ATR better than the signal close | PROPOSED | Raises win-rate a little; needs pending-order handling and fill modelling |
| 119 | Scale-out ladder 0.5R / 1R / 2R | PROPOSED | Middle ground between High-hit and Classic |

### C. Entries with a documented edge
| # | Idea | Status | Note |
|--:|---|---|---|
| 120 | RSI(2) dip in trend (Connors) | BUILT | ~72% winners on GLD daily in published tests |
| 121 | Double-7s in trend | BUILT | |
| 122 | Internal bar strength (weak close) in trend | BUILT | Documented next-bar reversal effect in indices |
| 123 | Opening range breakout with the trend (GOLD_ORB) | BUILT | Trend filter added |
| 124 | Stop-hunt reversal only with the trend | BUILT | |
| 125 | Squeeze and Asian-range breakout not against the trend | BUILT | Most often chosen in trending worlds |
| 126 | Trend defined by 200 EMA side AND higher-timeframe agreement | BUILT | |
| 127 | First-half-hour momentum into the last half hour (intraday momentum literature, incl. gold futures) | PROPOSED | Needs a session-return feature; promising for NY session |
| 128 | Buy-the-dip only above yesterday's low in a bull regime | PROPOSED | |
| 129 | Short-side filter: shorts only when D1 and H4 both point down | PROPOSED | Gold's long bull trend punishes counter-trend shorts |

### D. Choosing what to trade
| # | Idea | Status | Note |
|--:|---|---|---|
| 130 | Strategy Lab: 8 x 4 combinations tested daily on the chart's own history | BUILT | |
| 131 | Win-rate target as an input (default 60%) | BUILT | |
| 132 | 3-point allowance for out-of-sample decay | BUILT | Tested: lifts out-of-sample win-rate above 60% |
| 133 | "Still profitable in the most recent fifth" rule | BUILT | Tested: cuts trading in regime changes |
| 134 | 50-trade minimum | BUILT | Tested |
| 135 | Stand aside when nothing qualifies (live accounts) | BUILT | Trades on 4-7% of days in no-edge worlds |
| 136 | Rolling "last two folds" window | TESTED-OFF | Worse than using the whole window with the recency rule |
| 137 | Same fixed data window for indicator and EA so both choose alike | BUILT | Bars up to server midnight |
| 138 | Fixed strategy or fixed exit selectable by hand | BUILT | Inputs "Strategy" and "Exit style" |
| 139 | Pattern-match veto inside the Lab | TESTED-OFF | Removed from the default path: kept the Lab and live trading identical and fast |
| 140 | Weight recent trades more in the Lab score | PROPOSED | Needs a replay comparison |

### E. Making it easy and fun
| # | Idea | Status | Note |
|--:|---|---|---|
| 141 | Strategy Lab scoreboard with PASS marks and the pick highlighted | BUILT | Bottom right |
| 142 | PROVEN / UNPROVEN badge on every signal (green / grey arrows) | BUILT | |
| 143 | "Stay about 3h; close by 17:00" from the Lab's own hold times | BUILT | |
| 144 | Lot size shown as money: risk and typical win in account currency | BUILT | |
| 145 | Mean-reversion target drawn as a moving line (5-bar mean) | BUILT | |
| 146 | Next-candle direction for M15 / H1 / H4 on one line | BUILT | Each audited separately |
| 147 | Ghost candles re-anchored to the live price every second | BUILT | |
| 148 | Panels that size themselves to their text; EA panel bottom-left, indicator top-left | BUILT | Fixes the overlap in your screenshots |
| 149 | Account-health warning: trades without a stop loss, low margin level | BUILT | Your screenshots showed two sells without a stop and 64% margin level |
| 150 | Weekly report card (trades, win-rate, R, best/worst) written to a file | PROPOSED | |

### F. Safety
| # | Idea | Status | Note |
|--:|---|---|---|
| 151 | Lot size from the broker's profit formula, not the tick value | BUILT | Your broker reports the tick value 10x too small; the old sizing would have been 10x too big |
| 152 | Size cross-check: tick value vs profit formula vs contract size, mismatch logged | BUILT | |

### And more (second brainstorm)
| # | Idea | Status |
|--:|---|---|
| 153 | Per-session Lab (London vs New York) choosing different strategies | PROPOSED |
| 154 | Real-yield and DXY daily bias as a Lab filter | PROPOSED |
| 155 | Volatility-targeted position size (smaller in the top 20% of ATR) | PROPOSED |
| 156 | Monte Carlo risk-of-ruin of the chosen strategy shown in the scoreboard | PROPOSED |
| 157 | Auto-export of the Lab table to CSV every day for a journal | PROPOSED |
| 158 | Push notification with the full plan (entry/stop/target/size) | PROPOSED |
| 159 | "Why no trade" history: last 20 skipped signals with reasons | PROPOSED |
| 160 | One-click manual trade from the panel with the plan's stop and size | PROPOSED |
| 161 | Multi-symbol Lab (XAGUSD, XAUEUR) to see if the edge is gold-specific | PROPOSED |
| 162 | Break-even move before red-folder news for open trades | PROPOSED |
| 163 | Stop placed beyond the nearest round number (playbook idea) | PROPOSED |
| 164 | Lab on M1-resolved fills (exact intrabar order) inside MT5 | PROPOSED |
| 165 | Martingale / grid recovery | REJECTED: raises win-rate by hiding losses until one wipes the account |

## Round 7: ten ideas to make the demo pay (tested on the real export of 30 Sep 2026)
Full numbers: [REAL_DATA.md, section 7](REAL_DATA.md#7-round-7-the-demo-screenshot-of-30-sep-2026-and-ten-more-ideas-tested-on-this-data).
| # | Idea | Status | Evidence / reason |
|--:|---|---|---|
| 166 | **Cost guard**: skip setups whose stop is shorter than 20 round-trip costs | BUILT | The only rule that helped in both halves of the M5, M15 and H1 files; in the EA replay at this broker's cost it lifted every timeframe (M5 -0.17R -> -0.01R, M15 -0.02R -> +0.01R, H4 -0.06R -> 0.00R) |
| 167 | **Account-fit check** in the indicator: "TOO BIG, SKIP" instead of "BUY NOW" when 0.01 lot is over your risk, plus the balance the trade needs | BUILT | The weekly chart said BUY NOW with 514% of the account at risk |
| 168 | **Demo rehearsal mode** (default): a demo account runs exactly the real-account rules | BUILT | A demo only previews a real account if it trades like one. Free run is still one switch (or the DemoTurbo preset) away. The inputs were renamed so an attached EA does not keep the old free-run values |
| 169 | **Margin and spread guard** in every mode: no entry with free margin <= 0, margin level < 300%, or a spread above 1.5x the tested cost | BUILT | The screenshot showed margin level 79% and free margin -17.21 |
| 170 | **Stops for your own trades** (`InpProtectManual`, off by default): positions without a stop get one at a chosen % of equity | BUILT (off) | Two manual sells without a stop were the whole loss on the screenshot. Off by default because it changes trades you opened yourself |
| 171 | **Panel lines wrap** at 63 characters; weekly/daily charts show days/weeks and dates instead of "504h" and "close by 00:00" | BUILT | MT5 cuts a text label after 63 characters |
| 172 | Session windows (London, overlap, New York afternoon) | TESTED - not adopted | New York afternoon (17-21 GMT) helped the dips in both halves on all four timeframes, but not in the EA replay (M5 -0.10R, H1 -0.01R). Kept in the engine, off (`dip_gmt_lo`) |
| 173 | Market-condition filters: volatility, day range used, trend strength, higher-timeframe agreement, volume spike, day of week, 5/20-day momentum | TESTED - rejected | None helped on most timeframes in both halves; several flipped sign between timeframes |
| 174 | Eight new entry rules (previous-day breakout and sweep, 3 lower closes, Bollinger, Donchian, 50-EMA touch, RSI-2 with higher timeframe, weak close early in the day) | TESTED - rejected | None positive in both halves on H1 or H4 |
| 175 | Asian-open drift (buy the first hours after the daily break) and buys-only (gold's long drift) | TESTED - rejected | The drift sits in the widest-spread hour and bid-only data cannot show what a buyer pays; buys-only changed results by under 0.04R and flipped sign |
| 176 | Higher Lab target (65-70%) to raise the win-rate | TESTED - rejected | Real win-rate stayed 61-67% and the average did not improve |

## Round 8: fifty more ideas ("one perfect strategy", an EA that trades, sharper predictions)
Numbers: [REAL_DATA.md section 8](REAL_DATA.md#8-round-8-one-perfect-strategy-an-ea-that-trades-better-predictions) and
[FORECASTING.md](FORECASTING.md#round-8-measured-on-your-real-gold-and-what-changed).

### A. From the screenshots
| # | Idea | Status | Note |
|--:|---|---|---|
| 177 | Reset the EA's state on every (re)start | BUILT | Bug: after M5 -> H1 the EA kept trading the M5 Lab result |
| 178 | Scoreboard PASS uses the exact pick rule | BUILT | PASS and PROVEN can no longer disagree |
| 179 | Mean-revert trade box: typical exit as the green edge, moving exit level as a dotted line | BUILT | The green box was drawn under a buy |
| 180 | Panel starts below MT5's One Click Trading buttons | BUILT | The status lines were hidden |
| 181 | Your manual trades no longer stop the EA (`InpOneTradePerSymbol` = false) | BUILT | Margin-level check still protects the account |

### B. One strategy that mixes everything
| # | Idea | Status | Note |
|--:|---|---|---|
| 182 | Walk-forward meta-model (ridge, 22 features x 3 families + 32 combinations) choosing among all signals | TESTED - rejected | About 0R per trade on every timeframe, both halves |
| 183 | Continuous Lab: take any combination whose running average is positive | TESTED - rejected | -0.04 to +0.02R |
| 184 | Take every signal of every combination | TESTED - rejected | 1-2 trades/day on H1 at -0.01R |
| 185 | Meta-model plus "the combination itself must be positive" | TESTED - rejected | |
| 186 | Up to 3 positions at once from different combinations | TESTED - rejected | Up to 10 trades/day on M15, still about 0R |
| 187 | Higher model threshold for fewer, "surer" trades | TESTED - rejected | Win-rate 55-60%, average still within noise of 0 |

### C. Gold's daily trend and drift
| # | Idea | Status | Note |
|--:|---|---|---|
| 188 | Buy only while the daily close is above its 200-day mean, on H1 and above | BUILT (AUTO) | Chosen-on-older, checked-on-newer: H1 +0.16R, H4 +0.11R; EA replay H1 +0.025R at 67% won, H4 +0.020R at 65% |
| 189 | Strategy Lab on about 4 years of H1 (25,000 bars) | BUILT (AUTO) | Proven pick on 57% of days instead of 34%; replay -0.049R -> +0.025R |
| 190 | Trade only in the daily trend's direction (shorts in a downtrend) | TESTED - option | Worse than buys-only on H1/H4; available as `InpDailyTrend` = WITH |
| 191 | Daily filter on M5/M15 | TESTED - rejected | M5 worse (-0.15R), M15 unchanged within noise |
| 192 | "Rider" exit: a third at 1R, trail the rest 3 ATR, up to 5 days | TESTED - proposed | Best profit with the daily trend (+0.15 to +0.40R newer half) but 41-60% winners; below the 60% target |
| 193 | "Swing" exit: classic exit held up to 3 days | TESTED - proposed | Same trade-off |
| 194 | Daily trend following, long/flat 200-day mean | TESTED - documented | 9-10%/yr in both halves; needs a large account (0.01 lot with a daily stop risks 5-10% of 3,000 USD) |
| 195 | Daily trend following, long/short 50/100-day mean | TESTED - rejected | Lost money 2004-15 |
| 196 | Turn-of-the-month effect | TESTED - rejected | Flips between decades |
| 197 | Intraday momentum (first 30 min of New York -> last 30 min / rest of day) | TESTED - rejected | 47.8-51.9% |
| 198 | Lab window 25,000 bars on M5/M15 | TESTED - rejected | No better |

### D. Prediction precision
| # | Idea | Status | Note |
|--:|---|---|---|
| 199 | Calibrated range cone (past standardised moves x ATR x hour profile) | BUILT | Holds the price 59-61% of the time as intended; the old cone 51-55% |
| 200 | Candle size = ATR x hour profile x median correction | BUILT | Error 14-19% lower than the old ghost candles |
| 201 | Grey outline for each coming bar, as tall as it is expected to be | BUILT | Shown when no direction is proven |
| 202 | Panel line: "Next 3 candles: about X high; price 60% likely between A and B" | BUILT | |
| 203 | Expected next-candle size for M15, H1, H4 instead of "-- -- --" | BUILT | |
| 204 | Hour-of-day profile on H4 too | BUILT | |
| 205 | De-seasonalised EWMA of ranges (HAR-style) for candle size | TESTED - rejected | Slightly worse than ATR x profile |
| 206 | "Always up" as the direction call | TESTED - rejected | 53-56% on H4 only because of the bull market; 48-50% intraday |
| 207 | 21-EMA slope as the direction call | TESTED - rejected | 48-53% |
| 208 | Pattern-match direction with a stricter confidence gate | TESTED - rejected | Confident calls 48-53%: the existing gate already hides them |

### E. More trades without lowering the bar
| # | Idea | Status | Note |
|--:|---|---|---|
| 209 | Three EA copies on M15, H1 and H4 (presets `XAU_Sniper_Multi_*`, own magic numbers) | BUILT | Independent daily Labs, about three times the chances |
| 210 | One EA that scans several timeframes itself | PROPOSED | Needs per-position timeframe state; not written blind without an MT5 test |
| 211 | Trade every PASS combination, not only the best | PROPOSED | Idea 186 suggests about 0R extra per trade |
| 212 | Lower Lab target (55%) for more trades | TESTED (round 7) | H1 +0.026R: similar; left at 60% for the win-rate goal |

### F. Clarity and safety
| # | Idea | Status | Note |
|--:|---|---|---|
| 213 | "against the daily trend" as the reason a signal was skipped | BUILT | |
| 214 | Daily trend on the panel ("Daily: UP" / "Daily: DOWN (no buys)") | BUILT | |
| 215 | EA does not trade when the daily bars needed by the filter are missing | BUILT | |
| 216 | Same Lab window rule in the EA and the indicator (AUTO) | BUILT | |
| 217 | Unit tests: daily filter look-ahead, modes, calibrated cone on unseen bars | BUILT | |

### G. Backlog and rejections
| # | Idea | Status | Note |
|--:|---|---|---|
| 218 | Swap-aware holding (gold longs pay overnight swap) | PROPOSED | Matters for the rider/swing exits |
| 219 | Real-yield / DXY daily regime | PROPOSED | Needs the data in MT5 |
| 220 | Gradient-boosted trees instead of ridge for the meta-model | PROPOSED | Low prior after 182 |
| 221 | Separate Labs for London and New York | PROPOSED | |
| 222 | Volatility-targeted position size | PROPOSED | Helps drawdowns, not the average |
| 223 | Trail H4 runners under swing lows | PROPOSED | |
| 224 | Pyramiding into winners in a daily uptrend | REJECTED | Too much risk for small accounts |
| 225 | COT / options-implied volatility filters | REJECTED | Not available in an MT5 feed |
| 226 | Grid / martingale to raise the win-rate | REJECTED | Hides losses until one wipes the account |

## Round 9: more precise short-timeframe trades and predictions
Numbers: [REAL_DATA.md section 9](REAL_DATA.md#9-round-9-more-precise-trades-on-m5-m15-and-m30).
| # | Idea | Status | Note |
|--:|---|---|---|
| 227 | Limit entry 0.10 ATR better than the signal | TESTED - rejected | Adverse selection: lower on M5, M15, M30, H1 |
| 228 | Limit entry 0.25 ATR better | TESTED - rejected | Same |
| 229 | Limit entry 0.40 ATR better | TESTED - rejected | Same, and fills only 25-50% of signals |
| 230 | Wait for a confirming candle, then enter | TESTED - rejected | Half the trades, no better |
| 231 | Candle over 1.5 ATR, then fade it | TESTED - rejected | 50-56% right, loses after cost |
| 232 | Big candle with double volume, then follow it | TESTED - rejected | |
| 233 | Volume flow of the last 12 bars | TESTED - rejected | 48-49% right |
| 234 | Trending/choppy regime (variance ratio): momentum or reversal | TESTED - rejected | 49-51% |
| 235 | Timeframes agree (fast trend = higher-timeframe trend) | TESTED - rejected | 49-54% |
| 236 | Follow the London open's first 30 minutes | TESTED - rejected | |
| 237 | Follow New York's first 30 minutes | TESTED - rejected | |
| 238 | Rejection of yesterday's high / low | TESTED - rejected | |
| 239 | Rejection of a $10 round number | TESTED - rejected | |
| 240 | Inside bar, then close beyond the mother bar | TESTED - rejected | |
| 241 | Logistic learning model refitted daily (10 inputs) | TESTED - rejected | 50.5-52.2% right: real but smaller than the spread |
| 242 | Follow the first 15 minutes after the US jobs report | TESTED - rejected | 46.9% over 49 reports |
| 243 | M30 as the trading chart | TESTED | Weakest short chart: -0.11R at this broker's cost |
| 244 | A cheaper broker (0.15-0.25 per trade) | TESTED | More trades and winners (64-68%), still about 0R |
| 245 | Markets that move before gold (dollar index, EURUSD, silver, US yields, stock index) on M1-M5 | ENABLED | The export script now saves them (`InpExtraSymbols`); test after the next export |
| 246 | Surprise in US data (actual vs forecast) and the next hour of gold | ENABLED | The export script now saves the US calendar with actual/forecast/previous |
| 247 | 1-minute candles for exact fills on M5 | ENABLED | `InpBarsM1` in the export script |
| 248 | Depth of market imbalance | PROPOSED | Only where the broker shows a real order book; most gold CFD books are synthetic |
| 249 | Tick spread filter (trade only when the spread is below its median) | PROPOSED | Needs tick data |
| 250 | Exchange (COMEX) volume instead of tick volume | REJECTED | Not in a retail MT5 feed |
| 251 | Engine entry at a chosen bar and price (`SimulateTradeAt`) | BUILT | Used by the research; tested against the old simulator |
| 252 | MetaEditor "hides member" warning check in the offline checker (-Wshadow) | BUILT | The last build's single warning came from this |

## Round 10: fifty ideas for different mechanisms (not new settings on the same breakout)
Audit of everything so far: [AUDIT.md](AUDIT.md). Numbers: [REAL_DATA.md section 10](REAL_DATA.md#10-round-10-different-mechanisms-not-new-settings).
Includes the earlier ideas that were proposed but never built.
| # | Idea | Status | Note |
|--:|---|---|---|
| 253 | **Clock**: buy after the daily reopen, sell 2 hours later (no pattern) | TESTED - rejected | H1: lost in every year 2016-2024 |
| 254 | Clock: buy after the reopen, hold to London (01:30-08:30) | TESTED - rejected | |
| 255 | Clock: buy through Asia only while the daily trend is up | TESTED - rejected | Worse than without the filter |
| 256 | Clock: hold long through the daily break (pays swap) | TESTED - rejected | Positive only in 2025-2026 |
| 257 | Clock: short the US cash session ("gold falls in the West") | TESTED - rejected | Lost 2017-2025 every year |
| 258 | Clock: long or short London 10:00-15:00 | TESTED - rejected | |
| 259 | London AM fix: 30 minutes before / after | TESTED - rejected | M5 positive in both halves, M15 (4 years) negative |
| 260 | London PM fix: 30 minutes before / after | TESTED - rejected | |
| 261 | Fade weekend gaps back to Friday's close | TESTED - rejected | Gaps filled only 15-48% of the time |
| 262 | Day after a 2-sigma day: fade it | TESTED - rejected | Big down days were not followed by rebounds |
| 263 | Day after a 2-sigma up day: follow it | TESTED - not adopted | Slightly positive in both halves, within noise |
| 264 | Month-of-year seasonality | TESTED - rejected | Chosen months did not beat the rest out of sample |
| 265 | Weekday effect (Friday) | TESTED - not adopted | Strongest in both halves; needs weekend holds |
| 266 | **Trade the size forecast**: fade a close outside the cone | TESTED - rejected | Loses about the spread on every chart |
| 267 | Follow a close outside the cone | TESTED - promising (H4 only) | H4 positive in both halves, but only in trending years: the same edge as TREND |
| 268 | Squeeze straddle (two-way stops around a quiet box) | TESTED - rejected | |
| 269 | Squeeze, upside only, daily trend up | TESTED - rejected | |
| 270 | **Rider exit**: a third at 1R, stop to entry, 3-ATR trail, up to 5 days | BUILT | Positive skew: few big winners |
| 271 | **Swing exit**: the classic exit held up to 3 days | BUILT | |
| 272 | **TREND mode**: every passing combination trades at once (portfolio) | BUILT | H1 +0.11R per trade over 676 trades |
| 273 | 50% Lab target for trend exits (60% is the wrong bar for positive skew) | BUILT | |
| 274 | Total open-risk cap across positions (3%) | BUILT | |
| 275 | Overnight swap in the simulator and the Lab, broker's own rates, triple Wednesday | BUILT | |
| 276 | Multi-day positions kept over Friday; time stop counted in chart bars | BUILT | |
| 277 | AUTO mode: TREND on H1/H4, STEADY on M1-M30 and D1+ | BUILT | Trend exits lost on M15 (-0.04R) |
| 278 | Random-entry control in the replay (same exits, same filter) | BUILT | Separates skill from "being long gold" |
| 279 | Per-year results in the replay | BUILT | Showed the profit is concentrated in trending years |
| 280 | TREND mode on M5/M15 | TESTED - rejected | |
| 281 | TREND mode without the daily filter | TESTED - rejected | H1 +0.03R instead of +0.11R |
| 282 | TREND mode trading with the daily trend both ways | TESTED - not adopted | +0.08R, a bit worse than buys only |
| 283 | Positions at once: 1 to 5 | TESTED | H1: 1 = +0.05R (298 trades), 3 = +0.11R (676), 5 = +0.11R (866); 3 is the default |
| 284 | Lab window on H4 (6,000 vs 10,000 bars) | TESTED - warning | +0.14R vs +0.01R: H4 results are fragile; H1 is not |
| 285 | Indicator: session clock line (current session and the next event) | BUILT | "London open in 1h20" |
| 286 | Indicator: in TREND mode show any passing strategy's signal | BUILT | |
| 287 | EA panel: every open position with its exit style and P/L | BUILT | |
| 288 | Export: broker swap mode and rates | BUILT | |
| 289 | Dollar index / EURUSD moving before gold (M1-M5) | NEEDS DATA | Run the export script (round 9 version) and send the files |
| 290 | Silver moving before gold; gold/silver ratio extremes | NEEDS DATA | `InpExtraSymbols` includes XAGUSD |
| 291 | US 10-year real yield as a regime switch | NEEDS DATA | Not in most MT5 feeds; a bond CFD can stand in |
| 292 | Size of US data surprises (actual vs forecast) and gold's next hour | NEEDS DATA | The export saves the calendar |
| 293 | Speculator positioning extremes (weekly COT report) | PROPOSED | External weekly data, slow signal for TREND mode |
| 294 | Gold ETF holdings change as a trend filter | PROPOSED | External data |
| 295 | Volatility-targeted size (same dollar risk per day, not per trade) | PROPOSED | Smoother equity; adds no edge |
| 296 | Pause after a drawdown on the EA's own equity curve | PROPOSED | Usually cuts recoveries as much as losses; test before building |
| 297 | Add to a winning Rider position (pyramiding) | PROPOSED | Raises the payoff skew; needs margin |
| 298 | Weekly trend filter on top of the daily | PROPOSED | Fewer trades; may avoid 2021-2024 chop |
| 299 | One-line "today's plan" on the indicator (buy only / stand aside, expected range) | PROPOSED | Next simplification step |
| 300 | Cent account or FX pairs with finer lots for $50-100 | NEEDS BROKER | The only way a small account can use these rules |
| 301 | Export the EA's own trades to compare demo with the replay | PROPOSED | Detects broker differences early |
| 302 | Options-implied gold volatility (GVZ) for the range forecast | REJECTED for now | Not in an MT5 feed |
