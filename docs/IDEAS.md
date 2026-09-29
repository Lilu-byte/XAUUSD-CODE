# 75+ ideas, and what happened to each

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
