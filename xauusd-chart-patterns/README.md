# Gold Pattern Trainer

Open `gold-pattern-trainer.html` in any browser (double-click it). It works offline. Progress is saved in that browser only.

## What's inside

- **Learn**: 31 chart patterns, each with a drawing, a plain explanation, how to spot it, how traders use it (entry, stop, target), the common mistake, and how it did on real gold. 23 of them open a real gold example with "Another real one" and "Practise finding it". The other 8 are learn only: diamond top and bottom, high tight flag, island reversal, measured move, bump and run, dead cat bounce and VCP. They are rare on gold or need gaps.
- **Practice**, on 880 random windows of real XAUUSD history (MT5 export: D1 2004-2026, H4, H1, M15, M5):
  - *Find it*: drag across the candles where the named pattern sits, or tap its first and last candle. You get "Found it" when your selection overlaps the real one by 60% or more, and "Close" from 35%. Then the real pattern is drawn with labels, and "Show what happened next" plays the rest of the chart with the entry, stop and target.
  - *Name it*: a shaded area, four answers. The wrong answers are look-alikes.
  - *Will it work?*: the pattern has just broken out. Guess whether the target or the stop gets hit first.
  - Options: choose a pattern or let the app pick (weak patterns come up more often), choose timeframes, hide dates until you answer, and sometimes flip charts upside down so you don't learn a direction bias. The flip idea came from investingoal.com's learning tips.
- **Progress**: your tries and accuracy per pattern. A pattern counts as Mastered after 8 or more tries at 80% or better.
- **Do they work?**: the results of trading every pattern found the textbook way.

## Added 25 Oct (better visuals and teaching)

- **Learning path** in 7 stages: Basics, Tops and bottoms, Triangles and ranges, Wedges and channels, Flags and pennants, Cups and curves, Rare patterns. "Continue" opens the next unfinished stage, and each stage has its own practice button.
- **Basics**: seven idea cards with drawings: trend, support and resistance, waiting for the close, drawing lines, entry/stop/target and R, why patterns fail, and timeframes (with the gold results per timeframe). Each card ends with a quick check.
- **Step-by-step lessons**: each drawing builds one swing at a time with a caption ("First peak and pullback: the left shoulder"…). The last step shows the measured move: a height bracket and the same distance projected from the breakout. The breakout leg is green for up and red for down. The lesson shows a checklist, entry/stop/target tags, "Don't confuse it with" comparisons, and previous/next lesson buttons.
- **Look-alikes side by side**: 12 pairs that often get mixed up, with the one difference between them.
- **Practice**: three hints (the drawing, then where to look, then the breakout candle). Each hint lowers the score. After you answer, the real chart marks the breakout candle and draws a measured-move arrow, and a legend explains the marks. The textbook drawing sits next to the real chart, with the pattern's numbers (length, stop, target, reward : risk) and a "what makes it one" checklist. A wrong Name it answer shows your pick and the right one side by side.
- **Review queue**: each right answer pushes that pattern's next review further away (1, 3, 7, then 21 days). A wrong answer brings it back now. Use "Review due" on the Learn page or in the pattern menu.

## How the patterns were found

`src/detect.py` finds swing highs and lows (zigzag at 1.5, 2, 3 and 4.5 ATR), then applies fixed geometric rules: equal tops within 12% of the height, neckline breaks, fitted trendlines for triangles, wedges and channels, a pole of at least 5 ATR for flags, and a parabola fit for cups. Every instance needs a confirmed close beyond its line. It found 2,625 instances. I checked samples of each pattern by eye and tightened the rules where they looked wrong. The rules were never tuned on trade outcomes.

## Results on gold (after a $0.40 cost per trade)

- The target was hit before the stop 39% of the time.
- The average trade made +0.07R, where R is the amount risked. Random entries with the same direction, stop and target made −0.04R.
- The gap was largest on daily and 1-hour charts and close to zero on 5-minute charts.
- Bull flags reached their target first only 15% of the time. Web pages often quote 75-80%.
- Triple tops, triple bottoms, cups and rounding patterns have too few cases to judge.
- None of the pattern or candle rules tested earlier in this project beat simply holding gold.

Educational only, not investment advice.

## Rebuild

From `src/`: `python3 detect.py patterns.json`, then `python3 stats.py`, `python3 pack.py` and `python3 build.py`. `gold-pattern-trainer-publish-source.html` is the same app without the document wrapper, ready to publish as a web page if David approves.
