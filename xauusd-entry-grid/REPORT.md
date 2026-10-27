# Entry-grid scalper (David, 20 Oct 2026)

## The idea as tested
A ladder of price levels every $G around the market. When the price touches a level, open one 0.01 lot in the direction of the 1-minute candle at that moment (green = buy, red = sell). Take profit 1-2 pips = **$0.10 or $0.20** (a pip on gold read as $0.10). One open trade per level at a time, no limit on trades. Run with no stop loss and with stops of $0.30, $0.50, $1, $2, $5, $20.

Data: your MT5 M1 export, 26 Jun - 9 Oct 2026, with the broker's spread on each bar (median $0.12 in Jun-Aug, $0.17 in Sep-Oct) plus $0.05 slippage. Tuned on 26 Jun - 31 Aug, tested on 1 Sep - 9 Oct. Swap charged on trades held overnight.

## Result: it loses money in every version
All 140 versions lost on both periods (420 runs including the random and opposite-direction checks). **Zero profitable.**

| Version (test weeks, 1 Sep - 9 Oct) | Trades/day | Win rate | $ per trade | $ per day | Worst drawdown |
|---|---|---|---|---|---|
| Best: levels $5 apart, TP $0.20, stop $0.30 | 649 | 55% | -0.03 | -19 | -$562 |
| Levels $1, TP $0.20, stop $0.30 | 3,283 | 56% | -0.03 | -94 | -$2,725 |
| Levels $1, TP $0.10, stop $1 | 2,806 | 66% | -0.21 | -579 | -$16,782 |
| Levels $1, TP $0.20, **no stop** | 1,868 closed | 100% closed | +0.21 closed | -423 (incl. open losers) | -$29,364 |
| Levels $5, TP $0.20, **no stop** | 367 closed | 100% closed | +0.21 closed | -92 (incl. open losers) | -$6,230 |

For comparison: the GoldAllAgree + GoldAsiaBreak pair makes about **+$4.66/day** (May 2025 - Oct 2026). Holding 0.01 lot of gold made +$9/day in Jun-Aug and -$9/day in Sep-Oct.

## Why
1. **The spread is the size of the target.** A buy opens at the ask, so the price has to rise the whole spread ($0.12-0.20) before the trade is even at zero, and then another $0.10-0.20 to take profit. On a market that moves randomly, a trade with take-profit T and stop S has an expected result of exactly **minus one spread**, whatever T and S are. The tests match: about -$0.20 per trade with a $1 stop.
2. **The candle direction helps a little, not enough.** Compared with coin-flip directions on the same levels, following the candle earns about $0.03-0.08 more per trade. That is a quarter to a half of the spread, so every version still loses, and more trades only lose faster.
3. **Without a stop, it's a grid.** Every closed trade wins (100%), which looks great on the account history, but trades on the wrong side never close. With levels $1 apart, ~180-360 trades were stuck open at the end, worth -$23,000 to -$82,000. A $3,000 account would be margin-called on the first strong move (it can hold roughly 60 open 0.01 lots at 1:100 leverage).
4. **Tighter stops lose less only because of fill modelling.** The near-break-even rows (stop $0.30) are decided inside the same minute. If the far wick of each candle is assumed to come first instead of the near one, the best row goes from -$0.03 to -$0.07 per trade and -$19 to -$81 a day. Only MT5's "every tick based on real ticks" tester can settle the in-minute order, and it can't make the spread go away.

This matches the earlier tests in `xauusd-scalp/` and `xauusd-microscalp/`: $0.10-1 targets on gold lose after the spread, and averaging-down grids look good until one bad move empties the account.

## No EA built
None of the versions makes money after the spread, so no EA was built. If you want to see it in MT5's real-tick tester anyway, I can build it on request.

## Files
- `code/gridsim.py` - the simulator (integer cents, path O-L-H-C / O-H-L-C inside each M1 bar, per-bar spread + $0.05, swap)
- `code/grid.py` - runs all 420 versions
- `grid_m1.csv` - every result (period, spacing G, TP, SL, direction rule, trades, win rate, realized, floating, net per day, drawdown, most trades open)
