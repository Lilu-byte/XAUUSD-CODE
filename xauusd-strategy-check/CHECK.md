# Independent check of the gold trend strategy (13 Oct 2026)

Strategy checked (from `xauusd-price-action/STRATEGY.md`): long or flat, never short. Long when the daily close is above its 200-day average. Size = equity × 15% ÷ 20-day annualised volatility, capped at 1.5× equity.

Rebuilt from scratch on raw prices (none of the other thread's code). Data: your MT5 daily export, June 2004 to 9 Oct 2026, cross-checked against OANDA daily prices from QuantConnect (2006-2019; weekly returns correlate 0.999, prices within 0.05%). Tests start April 2005, when the first 200-day average exists. Costs: 0.05% per side, plus overnight swap.

## Verdict
1. **The numbers hold, roughly.** I get 8.9%/yr, -38% worst drawdown, Sharpe 0.70 (claimed 9.4%, -35%, 0.75). Same picture on OANDA data. Trading at the next day's open instead of the close changes nothing.
2. **But its edge over simply holding gold is small and not statistically reliable.** Sharpe 0.70 vs 0.61 for buy-and-hold; a block bootstrap puts the difference at +0.09 with a 90% range of -0.13 to +0.31 (75% chance it's real at all).
3. **The smaller drawdown mostly comes from holding less gold.** Buy-and-hold at 0.75× size (same volatility) has the same -37% drawdown and makes 7.5%/yr. The trend filter adds about 1.4%/yr on top of that.
4. **The filter helped in one era only.** 2005-2015 Sharpe 0.66 vs 0.47 for buy-and-hold (mostly from dodging the 2013 crash). 2016-2026: 0.74 vs 0.79, i.e. slightly worse than holding. In 2019-2026 its drawdown (-33%, Aug 2020 to Mar 2023) was deeper than buy-and-hold's (-27%) due to whipsaws.
5. **Swap matters more than the signal.** With today's swap (~1.1%/yr of price) it makes 8.9%/yr. With a historically realistic CFD financing charge (Fed funds + 1.5%), 6.9%/yr; buy-and-hold drops to 7.4%.
6. **It whipsaws about 7 times a year** (≈3.5 round trips), not 3.

## On a $3,000 account it isn't the same strategy
The 0.01 minimum lot (~$4,200 of gold) is 1.4× equity, so volatility sizing can't be done: the account is either flat or 1.4× long. That version: 10.3%/yr with today's swap (7.5% realistic), **-46% worst drawdown**, worst year -19%. That's buy-and-hold's drawdown, not the advertised -35%.

## Improvements tried (all pre-listed, 2005-2026, today's swap)

| Variant | Return/yr | Sharpe | Worst DD | Losing yrs | Trades/yr |
|---|---|---|---|---|---|
| Proposed (MA200 × vol20) | 8.9% | 0.70 | -38% | 9/22 | 6.9 |
| Check only on Friday close | 8.5% | 0.67 | -40% | 9/22 | 3.7 |
| 2% band around the MA | 8.0% | 0.63 | -44% | 9/22 | 1.9 |
| Keep 1/3 size when below MA | 9.3% | 0.71 | -41% | 9/22 | 0 exits |
| 12-month momentum instead of MA | 8.6% | 0.67 | -40% | 9/22 | 6.2 |
| Average of 1/3/6/12-month momentum | 7.8% | 0.69 | -32% | 9/22 | 5.6 |
| 60-day volatility | 8.9% | 0.71 | -39% | 8/22 | 6.9 |
| **Average of MA 50/100/150/200/250, Friday only, 60-day vol** | 8.7% | **0.73** | -39% | **6/22** | 4.3 |
| Volatility sizing only, no filter | 9.8% | 0.66 | -54% | 7/22 | 0 |
| Buy and hold 1× | 9.8% | 0.61 | -47% | 7/22 | 0 |

- Every variant lands at Sharpe 0.63-0.73. None beats the original by a margin that's distinguishable from luck (best: +0.02, 90% range -0.08 to +0.12).
- The blended version (bold) is the sturdiest, not the most profitable: fewer losing years, ~40% fewer trades, and it stays at Sharpe 0.68-0.73 across every MA set and vol window I tried, so it depends less on "200" being the magic number. It was assembled after seeing the single tests, so treat its small edge as optimistic.

## What actually improves the outcome
1. **Cut financing cost.** A long-biased gold strategy held through a CFD pays swap every night. Holding the same signal through an unleveraged gold ETF or a broker with lower swap keeps 1-3%/yr that the CFD gives away.
2. **Fix position size.** On $3,000, either use a broker/product that allows smaller sizes than 0.01 lot, or fund the account to ~$5,000+ so 0.01 lot is ≤0.85× equity. Otherwise expect buy-and-hold-sized drawdowns.
3. **Check weekly, use a blend of averages.** Same return, half the trades and less reliance on one parameter.

## Current signal
9 Oct close 4,195.20 is below every average tested (20d 4,233, 50d 4,337, 100d 4,261, 200d 4,530, 250d 4,459). Original and blended rules both say **flat**. 20-day volatility 21%.

## Honest limits
22 years of one market contain only ~3 big gold bull/bear cycles. The strategy's profit is gold's long-term rise; the filter is a seat belt that worked in 2013 and cost a little since 2016. Fed funds history is from memory (annual averages), so the "realistic financing" figures are approximate.

Code: `code/` (`check1-3.py`, `improve.py`; run with `python3 -I`). OANDA data re-fetched from QuantConnect/Lean `Data/cfd/oanda/daily/xauusd.zip`.
