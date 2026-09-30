# What "double the account every month" actually requires

This is arithmetic, not opinion. `research/sim/montecarlo.cpp` simulates one month of trading (40,000
simulated months per cell) with the same trade shape as the EA: stop-loss = -1R, half closed at 1R then
break-even = +0.5R, runner to 2.5R = +1.75R. Risk per trade is a fixed percentage of *current* equity
(compounding). Full tables: [`research/results/montecarlo_results.md`](../research/results/montecarlo_results.md).

Scenarios (expectancy E in R per trade; "win rate" = trades with positive net R):

| Scenario | E | Win rate | How plausible on real gold? |
|---|---:|---:|---|
| No edge after costs | -0.10R | 45% | What a random strategy earns after spread. The default assumption until proven otherwise. |
| Modest edge | +0.10R | 55% | A good, robust intraday system. |
| Good edge | +0.25R | 62% | Rare, and fragile. |
| Exceptional edge | +0.50R | 75% | Almost certainly overfitted if you see it in a backtest. |

## One month, 24 trades (about one per trading day)

Probability of **doubling** (P2x), of a month ending **20% or more down** (P-20), and of a **30%+ peak-to-trough drawdown** (PDD30):

| Risk per trade | No edge: P2x / P-20 / PDD30 | Modest: P2x / P-20 / PDD30 | Good: P2x / P-20 / PDD30 | Exceptional: P2x / P-20 / PDD30 |
|---:|---|---|---|---|
| 1% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% |
| 2% | 0% / 5.5% / 0.1% | 0% / 0.5% / 0% | 0% / 0% / 0% | 0% / 0% / 0% |
| 5% | 0.1% / 40.4% / 44.4% | 1.2% / 11.9% / 16.6% | 4.9% / 3.0% / 5.5% | 29.4% / 0.1% / 0.3% |
| 10% | 2.0% / 63.7% / 91.7% | 12.5% / 28.4% / 71.7% | 32.2% / 9.9% / 49.6% | 77.9% / 0.5% / 15.0% |
| 20% | 4.9% / 77.6% / 99.9% | 22.9% / 43.8% / 98.7% | 47.8% / 19.6% / 94.9% | 88.2% / 1.6% / 74.0% |

## What this means

1. **To double a month you need to risk roughly 10% of the account on every trade.** At the 1-2% risk professionals use,
   even a *good* edge grows an account 6-12% in a typical month, and a modest edge 2-4%.
2. **Even at 10% risk the outcome is mostly luck.** With a genuinely good edge you double 32% of months and suffer a
   30%+ drawdown in about half of them. With a modest edge you double 12% of months and lose 20%+ in 28%.
3. **If the edge is zero (the default until you prove otherwise), high risk is a fast way to lose the account:**
   at 10% risk, 64% of months end 20%+ down and 92% contain a 30%+ drawdown.
4. **Win-rate does not rescue you.** A 75% win-rate strategy with a fat left tail can still have negative expectancy.
   The tools therefore report expectancy and profit factor next to win-rate.
5. Small accounts have an additional floor: XAUUSD is 100 oz per lot, so 0.01 lot loses $1 per $1 move.
   With a $10 stop, one minimum lot risks $10; on a $100 account that is 10% per trade.
   On a live account (and on a demo in the default *Rehearsal* mode) the EA **refuses** such a trade rather than silently over-risking,
   and the indicator shows **TOO BIG, SKIP** with the balance the trade needs. Use a cent/micro account, or a larger balance.
   Rough minimums for 1% risk at 0.01 lot with Sep 2026 volatility: M5 550 USD, M15 1,100, H1 2,400, H4 5,300, D1 17,000.

## Win-rate is set by the exits
In a market with no edge the chance of reaching a target T before a stop S is about S / (S + T):

| Target (x stop) | Winners (no edge) | Measured here | Average result |
|---:|---:|---:|---|
| 0.5 | 67% | 66.7% | zero minus costs |
| 0.6 | 62.5% | 62.7% | zero minus costs |
| 1.0 | 50% | 50.6% | zero minus costs |
| 2.5 | 29% | - | zero minus costs |

So a 60%+ win-rate is a design choice of the exit. Profit comes only from entries with a real edge; the Strategy Lab requires both (docs/STRATEGY_LAB.md).

## What the EA does about it

* Risk per trade is capped at 5% (`XS_MAX_RISK_PCT` at the top of `XAU_Sniper_EA.mq5`). Raising it is your decision; read the table above first.
* Daily loss limit (default 3%), weekly (6%), drawdown kill-switch from peak equity (15%): the EA stops and, optionally, flattens.
* Risk falls after two consecutive losses; trading pauses after three in a row.
* The presets range from 0.5% (Conservative) to 4% (Aggressive). None is a promise; Aggressive is the closest to a "double it" attempt and is labelled as such.

## Reproduce

```
g++ -std=c++17 -O2 -o montecarlo research/sim/montecarlo.cpp && ./montecarlo
```
Edit the scenario list in `main()` to test your own measured win-rate and expectancy (from the indicator's Trial block or the Strategy Tester).
