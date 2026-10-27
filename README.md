# XAUUSD-CODE

MT5 tools and research for gold (XAUUSD). Every result below was tested on years the rules were not tuned on, after spread and swap, and compared with simply holding gold. **Nothing here guarantees a profit. Run anything that places orders on a demo account first.**

The `.mq5` files are source only. Open each one in MetaEditor and press F7 to compile it.

## MT5 files

| File | What it is | What testing found |
|---|---|---|
| `xauusd-mt5/GoldAllAgree.mq5` (+ `GoldAllAgreeTrend.mq5` indicator) | EA: long 0.01 lot while EMA20 > EMA80 on 5m to 4h, with a $100 emergency stop | Replay May 2025 to Oct 2026: +$1,350 over 265 trades. The edge probably comes from the 2022-2026 trend. |
| `xauusd-5-a-day/GoldAsiaBreak.mq5` | EA: Asian-session range breakout | Run together with GoldAllAgree: about $4.66/day, $5+ on 66% of days, worst drawdown about $285. Setup steps: `xauusd-demo-pair/SETUP.md` |
| `xauusd-microscalp/ea/GoldMicroScalp.mq5` (+ Signals indicator) | M1 micro-scalper v1.30 | Loses after the spread (about -$0.75/day). Only useful in MT5's real-tick tester. |
| `xauusd-candles/GoldCandlePatterns*.mq5` | Candlestick-pattern EA and indicator | Does not make money after the spread. |
| `xauusd-channels/GoldChannels.mq5` | Indicator: up, down and range stretches with channels | Chart tool. Breakouts do not beat holding gold. |
| `xauusd-mt5-patterns/GoldPatterns.mq5` | Indicator: 23 chart patterns, with alerts | Chart tool. Has no direction skill out of sample. |
| `xauusd-pdh-break/indicators/*.mq5` | Indicators: GoldTrendRide, GoldTurtle55, GoldTurtle20, GoldFedDay | Signals only, no orders. See that folder's REPORT. |
| `xauusd-volume-profile/FixedRangeVolumeProfile.mq5` | Fixed-range volume profile (POC, VAH, VAL) | Chart tool. |
| `mt5-tv-navigation/TVNavigation.mq5` | TradingView-style zoom and scroll for MT5 charts | Chart tool. |

## Research folders

Each folder has a `REPORT.md` or `README.md` with its findings, plus the Python code used. Large price CSVs are not included. They came from the MT5 export `XAU_Export.rar` on branch `claude/monke-xau-metatrader-pair-0imt7v`.

- `xauusd-price-action`, `xauusd-strategy-check`, `xauusd-intraday`: daily and intraday trend rules. Holding gold above its 200-day average is about as good as any rule, and it is never worth going short.
- `xauusd-5-a-day`, `xauusd-more-trades`, `xauusd-demo-pair`: the $5-a-day pair and attempts to trade it more often.
- `xauusd-scalp`, `xauusd-microscalp`, `xauusd-candles`, `xauusd-entry-grid`, `xauusd-channel-hedge`, `xauusd-pinterest`: scalping ideas. None makes money after the spread.
- `xauusd-github-eas`, `xauusd-github-bots`: reviews of public GitHub EAs and bots. None beat the pair, and several are traps.
- `xauusd-chart-patterns`: Gold Pattern Trainer, a practice page you open in a browser.

Older toolkits are kept on their own branches: `claude/mt5-xauusd-indicator-ea-zcjthq` (XAU Oracle and XAU Sniper) and `claude/monke-xau-metatrader-pair-0imt7v` (MONKE XAU).
