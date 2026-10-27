# Scalping XAUUSD for $0.10-$1 per trade (14 Oct 2026)

One 0.01 lot per trade ($1 per $1 gold move). Data: M5 candles from the MT5 export, May 2025 to Oct 2026 (train May-Dec 2025, test Jan-Oct 2026). The export's M1 candles are inside the .rar, which can't be unpacked in this environment; a plain CSV export of M1 would let me repeat this on 1m. Code: `code/edge.py`, `code/brackets.py`. Tables: `edge.csv`, `brackets.csv`.

## Bottom line

- **No version made money.** 2,592 setups (6 entry signals, take profit $0.10/0.25/0.50/1.00, stops 1x to 30x the target, spread $0.05/0.15/0.30, 1, 5 or unlimited trades open at once): **zero were profitable** in either period with realistic fills.
- **Why:** each trade starts behind by the spread. With a target and a stop, the spread is what you lose on average unless the entry signal really predicts the next few candles. The best candle signals moved price only $0.00-0.30 in your favour over the next 5-30 minutes, about the size of the spread, and the ones that looked good in 2025 flipped in 2026.
- **High win rates are easy and meaningless.** A $1 target with a $30 stop won 91-93% of trades and still lost $4-12 a day, because one stop wipes out 30 wins.
- **More trades at once makes it worse, not better.** Every extra position pays the spread again and they all move together, so they win and lose at the same time.
- **Beware backtests that look perfect.** If the test assumes the target is hit before the stop whenever both fall inside one candle, even coin-flip entries "make" $107-119 a day. MT5's Strategy Tester in "1 minute OHLC" or "Open prices only" mode can show the same illusion. Only "Every tick based on real ticks" is trustworthy for $0.10-$1 targets.

## What moves after each signal (next 1, 3, 6 M5 candles, $ per 0.01 lot)

| Signal | Signals/day | Avg move after 6 candles (2025 / 2026) | Win rate (2025 / 2026) |
|---|---|---|---|
| All 4 timeframes agree (trend side) | 96 | +0.23 / +0.30 | 52% / 51% |
| All agree + pullback candle | 47 | +0.29 / +0.28 | 53% / 51% |
| RSI(2) extreme, fade it | 36 | +0.02 / +0.09 | 51% / 52% |
| Fade 3 same-colour candles | 62 | +0.02 / +0.11 | 51% / 51% |
| Engulfing candle | 14-28 | +0.10 / +0.45 | 50% / 50% |
| Pin bar (wick rejection) | 48 | -0.12 / -0.08 | 49% / 49% |
| Follow last candle | 266 | +0.01 / -0.03 | 50% / 50% |

Spread: the bar data's minimum spread is about $0.04-0.06, but the quote at export time was $0.32, and raw-spread accounts add about $0.07 commission per 0.01 lot. Assume $0.15-0.35 per trade.

The only signal that is consistently positive is the multi-timeframe trend, which is the existing all-agree EA. It needs to hold for a while to earn more than the spread, which is what that EA already does.

## Best result per signal (test 2026, random-walk odds when target and stop share a candle)

| Spread | Best signal | Target / stop | Trades/day | Win rate | $/day |
|---|---|---|---|---|---|
| $0.05 | RSI(2) fade | $1 / $1 | 35 | 24% | -0.94 |
| $0.15 | All agree + pullback | $1 / $30 | 26 | 91% | -8.13 |
| $0.30 | RSI(2) fade | $0.10 / $0.10 | 35 | 0% | -3.51 |

A $0.10 stop is narrower than a $0.15-0.30 spread, so it is hit the moment the trade opens.
