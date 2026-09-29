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
