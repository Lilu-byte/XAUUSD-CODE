# Fixed Range Volume Profile for MT5

`FixedRangeVolumeProfile.mq5`: an MT5 indicator that shows how much volume traded at each price between two points in time that you choose.

## Install

1. In MT5: File > Open Data Folder > MQL5 > Indicators. Copy `FixedRangeVolumeProfile.mq5` there.
2. Open it in MetaEditor and press F7 (compile). It hasn't been compiled yet: MetaEditor isn't available where it was written, so paste any errors in the thread.
3. In MT5, drag "FixedRangeVolumeProfile" from the Navigator onto an XAUUSD chart. It works on any symbol and timeframe.

## Use

- Two blue dashed vertical lines appear. At first they sit 120 candles back and on the newest candle. Drag either line and the profile is rebuilt for the candles between them. A line includes the whole candle it sits on.
- **Rows:** volume at each price level. The teal part is volume from candles that closed up, and the red part is from candles that closed down. Rows inside the value area are bright, rows outside it are dim.
- **POC** (gold line): the price row with the most volume.
- **VAH / VAL** (dotted lines): the top and bottom of the value area. It is built outward from the POC, one row at a time, always taking the busier neighbouring row, until it holds 70% of the range's volume.
- **Summary:** the bottom-right corner shows the range, how many candles built the profile, the POC and the value area.
- **More than one profile:** add the indicator again and give it a different "Name of this profile", e.g. FRVP2, and set "Summary position" to 1 so its summary sits above the first one. Each gets its own pair of lines. Renaming a profile later leaves its old lines on the chart; delete them by hand.
- **Always up to date:** set "Range always ends at the newest candle" to true. There is then only a start line, and the profile updates every few seconds as new volume comes in.

## Settings worth knowing

| Setting | Default | What it does |
|---|---|---|
| Number of price rows | 60 | How many horizontal rows the range is cut into |
| Row size in price | 0 | Set e.g. 0.50 for $0.50 rows on gold, lined up on round prices; 0 uses the number of rows. A range that would need more than 2,000 rows uses a whole multiple instead ($1, $1.50...), shown in the summary |
| Value area | 70% | Share of the volume inside VAH-VAL |
| Candles used to build the profile | M1 | Each M1 candle's volume is spread over its own high-low, which is far more precise than using H1 or H4 candles. Very long ranges switch to M5, M15 and so on, keeping to 200,000 candles or fewer |
| Volume | Tick | Gold CFDs have no exchange volume, so MT5 counts price updates (tick volume). Real volume is used only if your broker supplies it |
| Placement / width | Left, 30%, 20 candles | Rows grow from the range start (or end at the range end). The longest row is 30% of the range's width, and at least 20 candles so short ranges stay readable |
| Extend POC, VAH and VAL | On | The three lines continue to the right of the range |

## Good to know

- Changing timeframe keeps the lines where they were. Removing the indicator removes them.
- The first time a range needs M1 history MT5 may still be downloading it, and the corner shows "loading M1 history...". If M1 data doesn't reach back far enough, the indicator moves to M5 or coarser after about 10 seconds, and tries M1 again once a minute.
- M1 matters most for ranges shorter than a day: built from M5, M15 or H1 candles, the POC and value area of a few hours can be dollars off. For a week or longer, M5 and M15 come close to M1.
- This is a picture of where volume traded. It hasn't been tested as a trading signal in this project.
