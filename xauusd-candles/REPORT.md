# Candlestick pattern EA and indicator for XAUUSD (14 Oct 2026)

Files:
- `GoldCandlePatterns.mq5` is the EA. It goes in MQL5/Experts; attach it to an XAUUSD chart with Algo Trading on.
- `GoldCandlePatternsInd.mq5` is the indicator. It goes in MQL5/Indicators and marks the same patterns the EA trades.
- `code/patterns.py` holds the pattern definitions, `code/grid.py` the test and `code/defaults.py` the default-settings check. Full table: `grid.csv`.

Neither file is compiled yet, because MetaEditor isn't available here. Press F7 in MetaEditor and paste any errors in the thread.

The Investopedia page is blocked from this environment, so I used the standard textbook definitions of the patterns that primer covers.

## Patterns (16)

| Buy | Sell | Definition used |
|---|---|---|
| Hammer | Hanging man | Lower wick at least 2x the body, small upper wick, body at most 35% of the range. Hammer after a fall, hanging man after a rise |
| Inverted hammer | Shooting star | Upper wick at least 2x the body, small lower wick. Inverted hammer after a fall, shooting star after a rise |
| Bullish engulfing | Bearish engulfing | Body opposite to and fully covering the previous body, against the prior move |
| Bullish harami | Bearish harami | Small body (under half) inside a previous long body of the opposite colour |
| Piercing line | Dark cloud cover | After a long opposite candle, opens beyond its close and closes past its midpoint |
| Morning star | Evening star | Long candle, then a small "star" candle, then a candle closing past the first one's midpoint |
| Three white soldiers | Three black crows | Three long same-colour candles, each opening inside the previous body and closing further on |
| Doji after a fall | Doji after a rise | Body at most 10% of the range |

"Long" means a body bigger than the average of the last 20 candles. "After a fall" means the previous close is below the close 6 candles earlier.

## How it trades (defaults)

- At each closed M5 candle, the enabled patterns vote buy or sell.
- With the trend filter on (default), it only trades in the direction of the H1 trend (EMA20 vs EMA80).
- One 0.01 lot, take profit $5, stop $12, one trade open at a time.
- It stops for the day once today's closed profit reaches +$5, or the loss reaches -$20.
- Trading runs from 01:15 server time; anything still open is closed at 23:30. Magic number 20261015.
- All of this can be changed in the inputs, including turning each pattern on or off.

## Test results (after spread $0.30, slippage $0.10, one 0.01 lot)

Train/test split: 5m trained on May-Dec 2025 and tested on Jan-Oct 2026; 15m trained on Jul 2022-Jun 2024 and tested on Jul 2024-Oct 2026. Each pattern was tested alone and with the H1 filter, under 28 target/stop settings ($1-5 target, $1-20 stop): 952 versions per timeframe.

- **Only 4-5% of versions made money in the training years, and 3-4% in the test years.** The ones that did made $0.10-0.20 a day and traded rarely (three soldiers, three crows, evening star with the trend).
- **Patterns do only somewhat better than coin flips.** Random-direction trades on the same candles lost $1.30 a day (15m) and $3.12 a day (5m) in the test years. The best pattern picks lost about $0.30-1.00 a day.
- **The default settings hit +$5 on about 78% of days, but still lose money overall.** The losing days are bigger than the winning ones:

| Defaults, test years | $/day | Days at +$5 | Losing days | Worst month | Worst drawdown |
|---|---|---|---|---|---|
| 5m, 2026, no daily loss limit | -3.89 | 79% | 20% | -$192 | -$745 |
| **5m, 2026, -$20 daily loss limit (default)** | **-1.35** | 78% | 23% | -$125 | -$315 |
| 5m, 2026, -$10 daily loss limit | -0.81 | 66% | 34% | -$56 | -$185 |
| 15m, 2024-26, -$20 daily loss limit | -0.39 | 77% | 21% | -$127 | -$393 |

- Why: a $5 target needs a stop far enough away to survive normal noise. On the bad days (about 1 in 5) the stop costs $12-20, which erases 3-4 good days. Patterns choose the direction only slightly better than chance, which doesn't cover the spread and those bad days.
- Earlier work in this project found the same thing: engulfing and rejection candles at key levels scored 66-68% on 2006-2019 data but 50.5% on 2019-2026, against a 50.1% baseline (`xauusd-price-action/BACKTEST.md`).

## How to use it safely

- Demo only. Run MT5's Strategy Tester in **"Every tick based on real ticks"** mode. "1 minute OHLC" and "Open prices only" can show profits that aren't real when the target and stop are close together.
- The indicator is the useful part for reading charts by hand. A bright arrow means the pattern agrees with the H1 trend, and the EA would take it. A grey arrow means it's against the trend, and the EA skips it.
