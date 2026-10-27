# Pinterest 1m-5m strategies, tested on XAUUSD

23 Oct 2026. The ask: search Pinterest for 1-minute to 5-minute strategies and see what the images show.

## What I could and could not see

Pinterest is blocked from this cloud machine (pinterest.com and its image host i.pinimg.com are both refused, and the pin pages don't allow automated reading). So **I could not look at the images themselves.** What I could do:

- find the pins through web search (titles and links, about 30 pins), and
- read the strategy pages those pins usually link to, which spell out the rules the infographics show.

If you want the images read directly, I can do it on your PC (the remote session we used for the Khosravani videos), or you can screenshot a few pins into the thread.

## What the pins are

Almost every 1m-5m pin is one of a handful of moving-average recipes, repackaged with hype titles:

| Pin family (example titles) | Rule as published | Hype in the title |
|---|---|---|
| "The Easiest 1-Minute Scalping Strategy: 3-EMA" | EMA 25/50/100 stacked, buy the pullback into EMA 25-50, stop past EMA 100, target 1.5x the stop | "beat the market", "BEST" |
| "1 Minute Trend Momentum Scalping" | EMA 50 over EMA 100 = buy-only; Stochastic(5,3,3) dips under 20 and crosses back up | "classic system" |
| "5 Min Scalping with EMA Channel and MACD", "5-Minute Momentum (Momo)" | Price crosses EMA 20 with MACD on the same side; stop at the swing, exit when MACD flips | |
| "Crazy 5 Minute Strategy", EMA 9/55/200 + RSI | EMA 9 crosses EMA 55 on the side of EMA 200, RSI over 52 / under 48 | "Crazy" |
| EMA 5/20 + MACD + Bollinger | EMA 5/20 cross, MACD histogram agrees, price not stretched from the Bollinger middle | |
| "EMA 15 / EMA 20 crossover" | Always in, flip on every cross | |
| "Profitable Simple Scalping Gold EMA 800", "Best Scalping XAU/USD M1" | Trade only on the EMA 800 side, enter on a fast cross (I used EMA 9/21) | "Profitable" |
| "Heikin-Ashi EMA Trading Strategy" | Heikin-Ashi turns green above EMA 50 (red below), exit on colour flip | |
| Hull + ADX (1-minute lists) | +DI/-DI cross in the direction of the Hull MA, target 1x the stop | |
| "No Loss Gold Scalping", "90% win rate", binary-option 5-minute pins, "XAUUSD Arrow Indicator M1" | No codeable rules; arrow indicators repaint; binary options aren't MT5 trades | **Impossible claims.** No strategy has no losses. |

## How I tested

- One 0.01 lot ($1 per $1 move), signal on a closed bar, fill at the next bar's open.
- Cost: the project's usual $0.30 spread + $0.10 slippage per trade, and a lighter $0.15 + $0.05 to be generous.
- Published default settings, nothing tuned by me. So every period counts as unseen data.
- Data: M1 26 Jun-9 Oct 2026 (76 days), M5 5 May 2025-9 Oct 2026 (372 days), and M15 Jul 2022-May 2025 as a check on years before the M5 data (no 1m/5m data exists for those years).
- Compared with the same entries in random directions, holding gold, and the GoldAllAgree + GoldAsiaBreak pair ($4.66/day).

## Results (full $0.40 cost, $ per day)

| Strategy | M1 2026 | M5 2025-26 | M15 2022-25 (unseen years) | Trades/day on M5 | Worst drawdown on M5 |
|---|---|---|---|---|---|
| 3-EMA 25/50/100 pullback | -12.24 | -1.89 | -0.25 | 5.0 | -$1,397 |
| EMA 50/100 + Stochastic | -28.95 | -4.33 | -2.11 | 10.3 | -$1,696 |
| Momo EMA 20 + MACD | -19.49 | +0.87 | -0.19 | 7.0 | -$682 |
| EMA 9/55/200 + RSI | -6.12 | **+2.69** | +0.13 | 2.6 | -$620 |
| EMA 5/20 + MACD + Bollinger | -8.54 | +0.26 | -0.44 | 4.4 | -$591 |
| EMA 15/20 crossover | -24.07 | **+2.52** | -1.34 | 9.5 | -$1,042 |
| Gold EMA 800 + 9/21 cross | +0.75 | +1.27 | -0.27 | 3.2 | -$937 |
| Heikin-Ashi + EMA 50 | -83.18 | -14.05 | -4.96 | 34.1 | -$5,268 |
| Hull + ADX DI cross | -13.27 | -5.23 | -1.16 | 7.3 | -$2,108 |
| *Hold gold (0.01 lot)* | *+2.19* | *+2.55* | *+2.06* | | |
| *The pair you already have* | | *+4.66* | | | *-$285* |

With the lighter $0.20 cost every number improves, but the picture stays the same: all M1 versions except EMA 800 still lose, and the best M5 version (EMA 15/20, +$4.90/day) is still below the pair and ran -$914 deep. Full table with both costs, win rates, monthly counts, long vs short and the random-direction check: `results.csv`.

## What this means

1. **On 1-minute, everything loses** except the EMA 800 version, which is break-even (+$0.75/day, 1 of 5 months up). Same reason as our earlier scalping work: the spread is about the size of the move these rules catch.
2. **On 5-minute, three look positive (EMA 9/55/200 + RSI, EMA 15/20, Momo), but it's the 2026 gold rally, not the rule.** Almost all their profit is in the second half of the period (EMA 15/20: -$3.20/day in the first half, +$8.24 in the second). On 2022-2025 they make about $0. Even in the good stretch none beats simply holding gold ($2.55/day) by much, and all of them sit far below the pair, with 2-4x its drawdown.
3. **Win rates are 20-45%**, not the 70-90% the pins suggest. Several do beat random directions, so there's a small trend-following effect, just not enough to pay costs reliably.
4. **"No loss" and "90% win rate" pins can't be tested** because they show no rules, and the claims themselves are a red flag.

**Advice: don't add any of these. Keep the GoldAllAgree + GoldAsiaBreak pair.** Educational test, not investment advice.

## Files

- `code/pins.py`: the nine rules and the test (uses the shared engine `xauusd-github-bots/code/gbt.py`).
- `results.csv`: every number above, both cost levels.

## Sources (pins found through search; pages not readable from here)

- 3-EMA 1-minute: pinterest.com/pin/978829300257425869, kr.pinterest.com/pin/189291990580689398, uk.pinterest.com/pin/1119074207402257697
- 1 Minute Trend Momentum: pinterest.com/pin/448178600411254110, de.pinterest.com/pin/410320216043674761
- 5 Min EMA Channel + MACD: pinterest.com/pin/806214770773985406; 5-Minute Momentum: pinterest.com/pin/389139224049554739
- EMA 15/20 crossover: pinterest.com/pin/1072841942466856981; Heikin-Ashi EMA: ca.pinterest.com/pin/757027018651245588
- Gold: pinterest.com/pin/984810643516138750 (No Loss), za.pinterest.com/pin/558587160039385292 (EMA 800), pinterest.com/pin/558587160038395997 (M1), es.pinterest.com/pin/627196685636534518 (Arrow M1)
- Rule pages: binance.com/en/square/post/709861 (EMA 50/100 + Stochastic), fxopen.com/blog/en/three-working-5-minute-trading-strategies (Momo, EMA 9/55/200 + RSI, EMA 5/20 + MACD + BB), axiory.com/trading-resources/strategies/one-minute-strategy (Hull + ADX and others)
