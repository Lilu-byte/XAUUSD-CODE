# XAUUSD research notes

**Provenance.** The build environment had no access to market-data or news sites (Yahoo, Stooq, Dukascopy, exchanges,
FRED, Kaggle and similar were blocked by the network policy), so nothing below was pulled live. These are domain notes from general market
knowledge; treat figures as approximate and check them against your broker. The strategy was **not** fitted to real price history.

## 1. The instrument
* Spot gold, quoted in USD per troy ounce. Typical contract: **100 oz per lot**, so a $1 move = **$100 per lot**; 0.01 lot = $1 per $1 move.
* Tick size usually 0.01. Spread is broker-dependent (commonly tens of cents on ECN-style accounts, wider at rollover and around news).
* Nearly 24h/5d. Broker server time is usually GMT+2/+3 with US daylight-saving shifts, which is why the tools work on a **GMT clock** with an offset.
* Long positions usually pay negative swap; that is one reason for the time stop.

## 2. What moves gold
* **Real yields** (inflation-adjusted Treasury yields): the most consistent inverse driver. Not available in most MT5 feeds, hence a backlog item.
* **US dollar**: broadly inverse. The engine uses a DXY-like symbol if present, else EURUSD (which is roughly the inverse of the dollar) as a small-weight vote.
* **Fed expectations and US data**: NFP, CPI, PCE, FOMC decisions/minutes, Fed-chair speeches, jobless claims, ISM. These cause the sharpest spikes; the EA stays out +/-30 minutes.
* **Safe-haven demand**: geopolitical shocks, equity stress.
* **Central-bank and ETF demand**: slow-moving, relevant to multi-week bias rather than intraday timing.

## 3. Intraday structure (GMT)
| Window | Character |
|---|---|
| 00:00-07:00 Asia | Lower volatility, tends to build a range that later gets swept or broken |
| 07:00-12:30 London | Range expansion; frequent sweep of the Asian high/low then a move |
| 12:30-16:00 London/NY overlap | Highest volume; US data at 12:30 or 13:30 GMT (08:30 New York) |
| 16:00-21:00 New York | Continuation or fade of the day's move; volatility fades into the close |
| ~21:00-23:00 | Rollover: thin, wide spreads, avoid |

The indicator measures the *actual* mean range by hour on your data and uses it to shape the projected candles.

## 4. Strategy families considered
| Family | Typical shape | Used here |
|---|---|---|
| Trend following / pullback | Lower win-rate, larger winners, loses in chop | Module PB + higher-timeframe bias |
| Breakout (range, squeeze) | Low hit-rate, high payoff, many false breaks | BO, SQ |
| Mean reversion (VWAP, oscillator extremes) | High hit-rate, small winners, fat left tail | VW, DV (low weight, gated by regime) |
| Liquidity-sweep reversal (stop-hunt fade) | Moderate hit-rate, tight stops | SW |
| Imbalance retests (FVG / order-block ideas) | Depends on trend context | FG |
| Scalping | High trade count, cost-dominated | Not used: spread is a large fraction of the edge |
| News trading | Fast, slippage-heavy | Rejected |

**Why win-rate is a trap.** Expectancy per trade = win% x average win - loss% x average loss. A 90% win-rate strategy that
wins 0.1R and loses 1.5R has expectancy of -0.06R. High win-rate is easy to manufacture (tiny targets, wide stops) and
usually comes with a fat left tail. The partial-at-1R design lifts the *share of winning trades* legitimately (about half the
position is banked early), but the number to judge is **expectancy and profit factor**, which the tools display.

## 5. What was tested, and what it does and does not show
`research/sim/harness.cpp` runs the real engine code (compiled as C++) on synthetic gold-like data (fat-tailed returns,
volatility clustering, GMT-hour volatility profile, market hours). Results are in `research/results/harness_results.txt`.

| Test | Result |
|---|---|
| Causality: truncated history vs full history | Identical votes and signals. **No look-ahead.** |
| Window consistency: indicator (6000 bars) and EA (3000 bars) vs full history, 10 seeds, 129 signals | 0 differences (6000) and 1 differing bar in 26,000 (3000). The chart and the robot agree |
| Simulator unit tests (stop, partials, break-even, TP2, time stop, shorts, costs, ties) | Pass |
| Sizing unit tests (risk exact, floors to step, refuses over-risk, caps) | Pass |
| **No-edge random walk** | Composite -0.14R; no module significantly positive. **The engine does not manufacture edge from noise.** |
| Trending world (edge planted) | Composite +0.06R (win 55%); trend modules +0.16 to +0.19R, counter-trend modules negative |
| Mean-reverting world | Composite -0.37R. **Trend-following loses when the market mean-reverts.** |
| Alternating regimes; walk-forward gating | Gating made it worse (-0.02R to -0.27R), so it is off by default |
| Does setup grade predict outcome? | **No evidence.** Grade A did not beat grade B in any world; A+ produced only 5 trades. Grade-based risk scaling is therefore off by default |
| Composite vs single modules | In the trending world the composite (+0.06R) is *weaker* than the trend modules alone (+0.16 to +0.19R): counter-trend modules dilute it |
| ADR block / efficiency-ratio regime weights (A/B, 8 seeds, 4 worlds) | ADR block: neutral within noise, ~9% fewer trades. Regime weights: **no measurable benefit** (mean-reverting world -0.45R vs -0.43R), off by default |
| DST maths | US and EU transition instants unit-tested for 2024 and 2026 |
| Analog forecaster (see FORECASTING.md) | No-edge world: 49.9% next bar, 51.4% confident +4 bars (coin flip, no leakage). Structured worlds 53-60%. Old drift forecaster: 36% in the mean-reverting world |
| Pattern veto A/B | trend +0.09R to +0.12R, alternating +0.04R to +0.05R, mean-reverting -0.56R to -0.50R, no-edge unchanged; 10-40% fewer trades |
| Demo turbo thresholds | about 10x trades (3-4/day); simulated expectancy about 0.06-0.10R lower than defaults |
| ORB (GOLD_ORB port), solo on M15 | no-edge -0.08R, trending +0.20R, mean-reverting -0.43R, alternating -0.11R; see GOLD_ORB.md |
| Signal frequency | Roughly 0.5 composite trades per trading day on M15 |

**The simulator is deliberately pessimistic.** A bar that touches both stop and target counts as stopped, and the runner cannot
reach TP2 on the bar TP1 filled. In the no-edge world a fair process should score about -0.04R (modelled costs); it scores
-0.14R, so the bias against the strategy is roughly 0.1R. Real-tick results in MT5 will not carry that bias.

**What synthetic data cannot show:** whether gold, on your timeframe and broker, has any of the structure these modules target.
That is the only question that matters and it has to be answered on real data (see TESTING.md).

## 6. Honest probability framing
* A robust intraday edge in a liquid market is usually a fraction of an R per trade before costs and often disappears out of sample.
* Backtests that show win-rates above ~70% together with strong profit are, far more often than not, curve-fits or unrealistic fills.
* Costs matter: on M15 a $0.30 round-trip on a ~$8 stop is ~0.04R per trade, which is a large share of a realistic edge.
* See RISK_MATH.md for what doubling a month would require.

## v2 additions (round 5)
### New findings from the tests
| Test | Result |
|---|---|
| Fill model vs minute-level truth (8,500 trades per cell) | Candle-path fills: average error 0.001-0.007R. The v1 rule (stop always first) was 0.095-0.110R too harsh. **All v1 trial numbers, including the ones on your screenshots, were about 0.1R per trade too pessimistic** |
| Win-rate by exit style, no-edge market | Classic 50.6%, High-hit 66.7%, Quick 62.7%, Mean-revert 52.0%: geometry, not skill |
| Strategy Lab, 32 combinations, 5 synthetic worlds | In trending and bull worlds several combinations reach >= 60% winners with profit; in no-edge and mean-reverting worlds none do (see STRATEGY_LAB.md) |
| Selection rules, 5 variants, live replay on fresh seeds | Strict rule (1 standard error, whole window, 50 trades, recent fifth still profitable) best everywhere; adopted |
| Live replay (daily Lab, as the EA trades) | Trend: 66% won, +0.31R, PF 1.88. Bull: 64% won, -0.02R. No-edge: stands aside 93% of days |
| Indicator vs EA signal windows | 191,872 comparisons across 8 strategies x 4 exits: 0 differences |

### Sources consulted this round
* Tick-value errors on XAUUSD at some brokers and the OrderCalcProfit fix: MQL5 forum threads [wrong value for SYMBOL_TRADE_TICK_VALUE](https://www.mql5.com/en/forum/444637/page5), [Wrong value returned by SYMBOL_TRADE_TICK_VALUE_LOSS](https://www.mql5.com/en/forum/453450), [What can I use instead of SYMBOL_TRADE_TICK_VALUE](https://www.mql5.com/en/forum/440059).
* Connors RSI(2) and Double 7s, including a GLD test (~72% winners over 76 trades): [Does Connors Double 7s work on GLD](https://www.edgestacker.com/tools/library/double7-gld/), [MQL5 article on RSI2 mean reversion](https://www.mql5.com/en/articles/17636), [WealthLab RSI2 Connors](https://www.wealth-lab.com/Strategy/RunBacktestPublished?strategyID=5).
* Internal bar strength: [The IBS Effect: Daily Mean Reversion of Equity Indices](https://www.researchgate.net/publication/256065291_The_IBS_Effect_Daily_Mean_Reversion_of_Equity_Indices), [Using Internal Bar Strength as a Key Indicator (arXiv)](https://arxiv.org/abs/2306.12434).
* Intraday momentum (first half-hour predicts the last), including precious-metal futures: [Market intraday momentum (JFE)](https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351), [Intraday return predictability in commodity ETFs](https://pmc.ncbi.nlm.nih.gov/articles/PMC7480318/).
* Win-rate versus reward-to-risk under a random walk (first-passage probabilities): [TradingView explainer](https://www.tradingview.com/chart/SPX/HUmb4N1D-The-Math-Retail-Traders-Ignore-Risk-Reward-Ratios-Are-Worthless/).
Market-data hosts (Yahoo, Stooq, Dukascopy, exchanges, FRED, Kaggle) remain blocked from this environment; the export script is the route to real data.
