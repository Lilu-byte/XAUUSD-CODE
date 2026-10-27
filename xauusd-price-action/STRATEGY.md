# A profitable XAUUSD plan, based on what the data showed (13 Oct 2026)

## What the tests established
- **Short-term direction is close to a coin flip.** Price action setups, ML models, time of day, news surprises and EURUSD signals all landed at 49–57% on unseen years, roughly the same as guessing "up" ([RESULTS.md](research/RESULTS.md), [BACKTEST.md](BACKTEST.md)).
- **Gold's money came from being long over months and years.** Buy and hold from June 2004 made about 10% a year after spread and swap. Every rule that included shorting lost money.
- **A simple trend filter cuts the damage in gold's bear markets.** Its cost is giving up some upside.

## Daily strategies, June 2004 to October 2026, after spread and swap

Costs use today's 0.35 spread and the -0.126/-0.046 per-ounce overnight swap from the export, scaled to the price at the time.

| Strategy | Return / yr | Worst drawdown | Return per unit of risk (Sharpe) | 2013–2018 (gold bear market) |
|---|---|---|---|---|
| Buy and hold | 10.2% | -46% | 0.64 | -5.0% / yr |
| Long only when the daily close is above the 200-day average | 8.0% | -34% | 0.60 | -2.5% / yr |
| **Same, with position size scaled to 15% annual volatility** | **9.4%** | **-35%** | **0.75** | -3.5% / yr |
| Long when price breaks the 50-day high, exit at the 20-day low | 4.3% | -29% | 0.42 | -2.5% / yr |
| Buy 5-day-low pullbacks above the 200-day average | 3.6% | -30% | 0.39 | -3.8% / yr |
| Long only when Daily price structure is bullish | 3.8% | -33% | 0.35 | -3.6% / yr |
| Long and short with Daily price structure | -3.9% | -77% | -0.14 | -3.9% / yr |

These rules were fixed in advance, not tuned on this data. The recommended rule still lost money in 9 of 22 years, and most of its profit came from a few strong trend years (2005–2011, 2019–2020, 2024–2025: +76% in 2025).

## The plan

1. **Core rule: long or flat, never short.** At each daily close:
   - Close above its 200-day average: hold a long position.
   - Close below it: be flat.
   - Expect about 3 changes a year.
2. **Position size from volatility, not conviction.**
   - Notional = equity × 15% ÷ gold's 20-day annualised volatility, capped at 1.5× equity.
   - Re-size about once a week.
   - With gold's volatility at 21% today, that is about 0.7× equity.
   - One lot is 100 oz, about $420,000 at 4,200. On a $3,000 account, the 0.01 minimum lot is already 1.4× equity, so 0.01 is the most that account should hold.
3. **What it says right now: flat.** Gold closed at 4,195.20 on 9 Oct, below its 200-day average of 4,530. It is about 25% under the January high of 5,598. The rule goes long again on a daily close back above the 200-day average.
4. **Use the price action read for context only.** It maps structure and levels well, but it showed no edge as a trade trigger. If you use it to time an entry once the core rule is long, don't expect it to add return.
5. **Stop doing what the data says doesn't pay:**
   - Shorting gold.
   - M5/M15 scalping: intraday direction was about 50%, and the spread takes the rest. The two trades in the EA journal were both M5 losses, though two trades prove nothing either way.
   - Trading news releases.
   - Chasing a high win rate with small targets.
6. **Prove it before scaling.**
   - Run the rule on demo, or with the minimum lot, for at least 3 months.
   - Keep a journal.
   - Compare the result with simply holding gold.

## Honest limits
This plan makes money only if gold keeps rising over the long run, as it has since 2004. During 2013–2018 every version lost money for six years. It is a disciplined way to own gold with smaller drawdowns, not a forecasting edge. Past results don't guarantee future ones, and leveraged CFDs can lose more than expected.

Code: [research/strat.py](research/strat.py).
