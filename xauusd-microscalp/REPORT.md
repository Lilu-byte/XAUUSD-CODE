# Many small targets from 1-5 minute candles, XAUUSD (14 Oct 2026)

## Short answer

I tested about 830,000 versions of the idea: read the 1-5 minute candles (finished or still forming), take a $0.10-$1 profit, repeat with no limit on trades. **None made money on the weeks they were not tuned on.** The EA below trades the three best signals I found. It loses about **$3.90 a day** on the test weeks (Sep 1 to Oct 9, 2026). It is delivered so you can see it on a demo account, not to run with real money.

Latest version (v1.30, 15 Oct): $0.25 targets with a trailing stop, a spread limit and a session window. It trades about 7 times a day and still loses, about $0.11 a trade and $0.75 a day on the test weeks; see "the selective version (v1.30)" below.

The reason is arithmetic, not a missing pattern. Each trade pays the spread, about $0.18-0.24 on one 0.01 lot. Over the 1-3 minutes a candle signal covers, the best signals moved price only $0.00-0.30 in their favour. A $0.10 target is smaller than the spread, so the price has to move $0.30-0.35 your way just to collect $0.10. More trades and more open positions multiply the spread you pay; they don't add profit.

Two more approaches were tested after that and also failed:
- **A machine-learning model reading the candles** (287 LightGBM and logistic models, 714,000 settings, trained on candle shapes, forming candles, trends on five timeframes, time of day and volume). Its three best versions lost $2.00-4.10 a day on the test weeks, worse than random buy/sell on the same minutes. Its "skill" was 1-3 cents a trade, against a 20-24 cent spread.
- **Averaging down (a "grid")**, where each new position adds on a $2 move against you and the whole basket closes at +$0.30. This is the only thing that made $5+ a day on the test weeks: +$9.42 a day, no losing day. It is not an edge. Random directions earned the same +$9.10, and the profit comes from rare, huge losses that simply didn't happen in those 29 days. On the 14 months before them (rebuilt from your M5 data) the same rule lost about $18 a day. One failed basket there cost $2,700-4,700, enough to wipe out the $3,000 account. I did not build it.

## Update, 15 Oct: the spike-fade lead, tested properly

David asked for another try at a version that makes money. I tested the one effect that kept showing up, the snap-back after a sharp move, with about 110,000 more versions (`families/snapback-*`, checks in `verify/snapback-*`). Every promising pick went to two independent skeptics, and all of them were refuted.

| Pick | Rule | Tuning weeks | Test weeks | Why it doesn't hold |
|---|---|---|---|---|
| Fade a $7+ three-minute move, close after 3 minutes, $10 stop | no take-profit | +$9.20 a day | +$4.37 a day | Three US-news days made all of the test profit; without them it's -$0.02 a day. One minute of delay drops it to +$0.90. Lost money since mid-September. No sign of it on 17 months of older M5 data |
| Fade a sharp move back toward the day's VWAP, close after 15 minutes, $25 stop | no take-profit | +$18.44 a day | +$3.22 a day | Statistically zero (one day made $169). Worst test day -$95. Simply selling every one of those minutes made more |
| Same snap-back as a ladder of $1 take-profits, re-entering while the price stays stretched | within your $0.10-$1 rule | +$1.70 a day | -$0.52 a day | Each rung pays the spread again |
| Other "overstretched" signals (RSI, z-score, runs of candles, range expansion) | various | +$4.90 to +6.90 a day | -$1.90 to -4.80 a day | All lost on the test weeks |
| Fade big 15-minute bars, 2022-2026 | no take-profit | +$0.21 a day | +$0.83 a day | Under one trade a day; came from a few crash rebounds in gold's 2025-26 rally; made nothing or lost since late June |

The snap-back is real but short: most of it happens in the first minute, mostly around news, when real spreads and slippage are worst. Capping it at a $1 target removes it; holding it longer makes it a news lottery. With this broker's spread, I found no way for $0.10-$1 targets from candle patterns to add up to $5 a day.

## Update, 15 Oct: small targets with a trailing stop (v1.20)

David asked for $0.05-0.10 targets on the same four signals, a first stop wider than the target, and a stop that follows price once a trade is in profit. GoldMicroScalp v1.20 does that:
- **Target** $0.10 per 0.01 lot, measured from the entry price (one input per module).
- **First stop** $0.30, measured from the price that triggers it (the bid for a buy, the ask for a sell), so the spread alone can't hit it. A full stop costs about $0.30 plus the spread. The EA refuses a first stop of $0.05 or less.
- **Trailing stop** for buys and sells: once a trade is +$0.03, its stop stays $0.02 behind the best price, and moves only when it improves by $0.01 or more. A trade that reaches +$0.07 and falls back exits at about +$0.05 ($0.06 with a $0.01 distance). If the broker refuses to move the stop, or its minimum stop distance is wider than the trail, the EA keeps the stop itself and closes at market.
- CP is on, the caps are higher (SF and QB 3, CP 5, total 12). Signals, entry timing, the hedging check, the $15 daily loss stop, the 22:58 close-all and the spread filter are unchanged. The indicator only changed its CP default to on.

**What to expect.** A $0.02 trailing stop can't be tested on 1-minute candles, because what happens inside the minute decides every trade. The average per trade can still be estimated: unless the signals move price in their direction within those first seconds (on the test weeks they moved it less than the spread even over 1-3 minutes), any exit rule, trailing or fixed, leaves each trade about the spread worse off on average. The trailing stop changes the mix, many small wins and fewer larger losses, not the average. The same test as above, with the $0.10 target and a stop $0.30 beyond the spread (Sep 1 to Oct 9, 2026):

| v1.20 defaults (bracket, no trail) | $ a trade | Trades a day | $ a day |
|---|---|---|---|
| All four modules, no daily stop | -0.23 | 232 | -53 |
| All four, recorded spread only, no daily stop | -0.19 | 232 | -43 |
| **All four, $15 daily stop (as the EA runs)** | -0.29 | 53 | **-15.2** (the stop was reached every day) |
| PB alone | -0.21 | 16 | -3.3 |
| SF alone / QB alone | -0.20 / -0.18 | 4 / 2 | -0.8 / -0.4 |

CP makes up nine trades in ten. To see the trailing stop's real effect, run the EA in MT5's Strategy Tester with "Every tick based on real ticks"; `ea/expected_trades.csv` still lists the v1.10 trades and no longer matches the defaults.

## Update, 15 Oct: the selective version (v1.30)

David asked for fewer, better trades: targets of $0.15-0.30, a first stop 2-3 times the target, a trailing stop, a spread limit tied to the target, a session window, stricter signals and only the strongest candle patterns. GoldMicroScalp v1.30 does that, and the indicator marks the same filtered signals.

| Setting | v1.30 default |
|---|---|
| Take profit, every module | $0.25 from the entry price |
| First stop | $0.60 beyond the spread. The EA refuses to start if a stop is under $0.20 or not wider than its take profit |
| Trailing stop | starts at +$0.08, stays $0.04 behind the best price, moves in steps of $0.01 or more. Unchanged logic from v1.20, including the fallback to closing at market if the broker refuses the move |
| Session window | 15:00-19:00 server time, checked on the signal candle (the 18:59 candle's trade opens in the 19:00 minute). This server runs on GMT+3, so that is 12:00-16:00 GMT, the London/New York overlap; 13:00-17:00 here would be 10:00-14:00 GMT. It also has the lowest spreads of the day on this data |
| Spread limit | the live spread when the trade would open must be at most 50% of that module's take profit ($0.125 at the defaults: 12 points pass, 13 don't), and at most 50 points as before. The EA reads the quote again for each module and before each retry |
| PB body | the signal candle's body at least 0.8 times the average range of the 20 candles before it |
| CP body | at least 0.5 times that average range |
| CP patterns | engulfing, morning/evening star, three white soldiers/black crows. Hammer/hanging man, inverted hammer/shooting star, harami, piercing/dark cloud and doji can each be switched back on |
| M5 alignment | optional, off by default: the last finished M5 candle, or the M5 EMA(9), must point the trade's way |
| Caps, daily stop, close-all | unchanged: PB 3, SF 3, QB 3, CP 5, 12 in total; $15 daily loss; entries 01:05-22:29, close-all 22:58 |

**What to expect.** Same test as before: fair fills, spread plus $0.05 slippage, the trade entered on the next minute's open and filtered on the spread recorded for that minute. The trailing stop can't be shown on 1-minute candles, so these are the take profit and first stop alone.

| v1.30 defaults | $ a trade | Trades a day | $ a day |
|---|---|---|---|
| Tuning weeks, Jun 26 to Aug 31 | -0.10 | 9.2 | -0.96 |
| **Test weeks, Sep 1 to Oct 9** | **-0.11** | **6.7** | **-0.75** |
| Test weeks, recorded spread, no slippage | -0.06 | 6.7 | -0.42 |
| Test weeks, live spread $0.05 above the recorded one | | 0 | 0 (no trade passes the limit) |
| Test weeks, random directions on the same minutes (200 runs) | | | -1.02 median, -0.64 best |

By module on the test weeks: CP 3.9 trades a day at -$0.10 each, PB 1.1 at -$0.09, SF 0.9 at -$0.13, QB 0.8 at -$0.17.

**Almost every trade is decided inside its first minute.** With a $0.25 target and a $0.60 stop, nearly every trade reaches one of them, often both, within the minute it opens, and 1-minute candles can't show which came first. The answer swings the result:

| A minute that touches both is settled by | $ a trade | $ a day |
|---|---|---|
| Stop first | -0.47 | -3.17 |
| The candle's path (open, high, low, close) | -0.18 | -1.19 |
| **Fair odds (used above)** | **-0.11** | **-0.75** |
| Target first | +0.13 | +0.89 |

Only MT5's Strategy Tester on "Every tick based on real ticks" can settle it. "1 minute OHLC" uses the candle's path, and the "target first" row is what an over-optimistic tester shows.

What the tests showed:
- **The filters cut the cost, not the problem.** About 7 trades a day instead of 230. The signals do carry a little direction: they beat 96% of random runs on the test weeks (all 200 on the tuning weeks). But that is worth about +$0.04 a trade before costs, against about $0.15 of spread and slippage each trade pays.
- **The trade count falls when spreads widen.** 8.4, 8.6 and 7.4 trades a day in the first three test weeks, then 4.8, 5.4 and 4.2 as the typical recorded spread rose from 13 to 19 points. If the live spread runs $0.05 above the recorded one, no trade passes. The EA's panel shows the live spread against the limit and counts the signals it skipped.
- **The tuning weeks look busier than they were.** MT5 recorded no spread for the first two weeks (until about Jul 8); the test filled those minutes with the hour's median, so 92 of 433 tuning trades rest on a spread nobody saw. Without them it is about 7.3 trades a day at -$0.10 each.
- **No version inside David's ranges made money.** A 216-version grid (take profit $0.15-0.30, stop 2-3x, spread limit 40% or 50%, body 0, 0.5 or 0.8, M5 alignment off, candle or EMA) lost on both the tuning and the test weeks. All 54 versions with a $0.15 target took no test trades at all, because their spread limit ($0.06-0.075) is below the usual spread. The smallest losses came only from fewer trades. M5 alignment roughly halved the trades and left the result per trade the same, so it is off by default. A body filter of 0.8 lost about $0.02 a trade less than none. Grid: `ea/v130_grid.csv`.
- **One lead that doesn't hold up.** Keeping the same entries open to each module's time exit (5 or 20 minutes, no target, no stop) shows +$0.86 a trade and +$5.72 a day on the test weeks. Three days made all of it: without them it is -$0.33 a trade. It also has no stop, and the same check on the tuning weeks gave +$0.39 a trade that turns into -$0.17 without its best three days. It is the news-day snap-back from the spike-fade update again, not something to build on.

Code: `ea/ea_replica_v130.py` (signals match the MQL5 code bar for bar). Entries the EA should take with the defaults, filtered on the recorded spread: `ea/expected_entries_v130.csv`.

## Files

| File | What it is |
|---|---|
| `ea/GoldMicroScalp.mq5` | The EA. Goes in MQL5/Experts |
| `ea/GoldMicroScalpSignals.mq5` | The indicator, showing the same signals. Goes in MQL5/Indicators |
| `ea/expected_trades.csv` | Every trade the EA should take on Jun 26 to Oct 9, 2026 with default inputs, to compare with MT5's Strategy Tester |
| `ea/ea_replica.py` | Python copy of the EA used for the numbers below (signals match the MQL5 code bar for bar) |
| `ea/ea_replica_v130.py` | Python copy of v1.30's signals and filters, used for the v1.30 numbers |
| `ea/expected_entries_v130.csv` | The 627 entries v1.30 should take on Jun 26 to Oct 9, 2026 with default inputs, filtered on the recorded spread |
| `ea/v130_grid.csv` | The 216 v1.30 versions inside David's ranges, scored on the tuning and test weeks |
| `data/XAUUSD_M1.csv` | The 1-minute data (from your MT5 export), 100,000 bars, Jun 26 to Oct 9, 2026 |
| `families/` | The seven research groups' code and outputs |
| `code/mlib.py` | The test engine (version 2, after an audit fixed four bugs) |
| `verify/` | The independent check of the averaging-down grid |

Neither .mq5 file is compiled yet, because MetaEditor isn't available here. Press F7 in MetaEditor and paste any errors in the thread.

## How it was tested

- **Data:** 76 trading days of 1-minute XAUUSD from your MT5 export (Jun 26 to Oct 9, 2026). 5-, 15-, 60-minute and 4-hour candles were built from it or taken from the same export.
- **Tuning and test:** every rule and setting was chosen on Jun 26 to Aug 31 (47 days). The picks were then run once on Sep 1 to Oct 9 (29 days).
- **Costs:** the spread recorded on each bar plus $0.05 for slippage (typical total $0.18-0.24 per trade). Also checked at the recorded spread alone and at a flat $0.30. Commission is not included; on raw-spread accounts it adds about $0.07 a trade.
- **Fills:** when the target and the stop both fall inside the same minute, the test splits the outcome by fair odds. The usual shortcut, "the target fills first", makes even coin-flip entries look like they earn $100+ a day. MT5's tester does the same unless set to "Every tick based on real ticks".
- **Baseline:** every pick was compared with random buy/sell directions on the same minutes. A real signal should beat that.
- **Audit:** an independent check of the test engine found four bugs. The worst one held positions over the nightly break into the reopen print. All were fixed, and every result was re-run.

## Results by idea (test weeks, after costs)

| Idea | What it does | Trades a day | $ a day | Random directions, same minutes |
|---|---|---|---|---|
| Textbook candle patterns (16 patterns, M1) | hammer, engulfing, harami, stars, soldiers/crows, doji... | ~210 | -58 | -57 |
| Strong 2-min candle against the H1 trend, trade with the trend | the EA's PB module | 16 | -2.5 to -2.9 | -4.0 to -4.3 |
| Forming 5- and 15-min candles, read before they close | partial body, breaks in progress, pin bars forming | 2-6 | -0.5 to -2.0 | about the same |
| Smart-money setups on M1/M5 | liquidity sweeps, fair value gaps, break of structure, order blocks | 9-15 | -2.0 to -2.9 | -2.0 to -3.2 |
| Momentum and mean reversion | spike fades, RSI, z-score, VWAP distance | 4-9 | -1.0 to -2.7 | -1.0 to -3.0 |
| Multi-timeframe trend in the New York session | trend on M5/M15/H1/H4 all agree, enter every minute | 43 | -5.3 | -0.1 |
| First minute of a 15-min candle breaking the last one, faded | the EA's QB module | 2 | -0.4 to -0.5 | -0.5 to -0.6 |
| Machine-learning models (LightGBM, logistic) | candle, forming-candle, trend, time and volume features | 4-7 | -2.0 to -4.1 | -1.0 to -2.0 |
| Exit tricks and stacking (wider stops, break-even, day targets, many positions at once) | on the strongest signal found | 9 | -2.2 to -4.6 | -2.4 to -3.5 |
| Averaging-down grid, basket closes at +$0.30, no stop | add 0.01 lot every $2 against | 52 | +9.42 (test weeks), about -18 on the 14 months before | +9.10 |

What the tests showed:
- **Textbook patterns on 1-3 minute candles carry no direction.** Their average move over 1-3 minutes was -$0.10 to +$0.13, against a ~$0.18 spread. Taken as taught, they lose $40-134 a day under brackets.
- **Reading the candle before it closes doesn't help.** No forming-candle condition beat the spread even on the tuning weeks.
- **High win rates hide the losses.** Most picks won 75-90% of trades and still lost money, because one stop costs as much as 5-20 targets.
- **The only steady effect is a snap-back after big moves** (a $3-6 spike tends to retrace). Most of that retrace is over $1, and a target of $1 or less cuts it off.
- **Exit tricks change the shape, not the sign.** Wider stops raise the win rate and make each loss bigger. More open positions multiply the spread paid. A daily target or loss stop cuts the number of trades, not the loss per trade.
- **Tuning-week profits didn't survive.** Picks that made $1-18 a day on Jun-Aug lost on Sep-Oct. Seen across tens of thousands of versions, that is what luck looks like.

## The EA: GoldMicroScalp

Trades one 0.01 lot per signal, several positions at once, no limit on the number of trades a day. Every signal is checked at the close of each 1-minute bar; the trade opens on the next tick.

| Module | Signal | Target (v1.10) | Stop (v1.10) | Close after | Max open (v1.10 → v1.20) |
|---|---|---|---|---|---|
| PB | A strong 2-minute candle (body at least the average of the last 20 and 90% of its range) running against the H1 trend: trade with the H1 trend | $1.00 | $5 | 20 min | 3 |
| SF | A 1-minute jump over 3x the average 1-minute range, moving away from the day's VWAP: trade against it | $0.50 | $5 | 5 min | 1 → 3 |
| QB | 15:00-19:59 server time: the first minute of a 15-minute candle closes beyond the last 15-minute high or low: trade against it | $0.50 | $2 | 5 min | 1 → 3 |
| CP | The 16 textbook patterns on M1, with the H1 trend (off in v1.10, on in v1.20) | $0.50 | $3 | 5 min | 3 → 5 |

v1.20 changed every module to a $0.10 target, a $0.30 first stop beyond the spread and a trailing stop. Since v1.30 the defaults are a $0.25 target, a $0.60 first stop and a trail from +$0.08 at $0.04; PB and CP need a minimum candle body, CP takes only engulfing, stars and soldiers/crows, and QB stops at 18:59 with the session window. See the two 15 Oct updates above.

Account settings: no entries before 01:05 or after 22:29 server time, and since v1.30 only on signal candles from 15:00 to 18:59; everything closed at 22:58; skip entries while the spread is over 50 points or, since v1.30, over 50% of the module's take profit; at most 12 positions open at once (10 in v1.10), and stop opening trades for the day once today's closed loss reaches $15 (set 0 to turn it off). Magic numbers 20261020-20261023, so it runs beside your other EAs. It needs a **hedging** account and refuses to start on a netting one.

Expected results for the v1.10 defaults, as the EA places trades (next-tick entry, spread filter, daily stop):

| Defaults (PB + SF + QB) | $ a day | Trades a day | Winners | Days at +$5 | Losing days | Worst day | Worst drawdown |
|---|---|---|---|---|---|---|---|
| Tuning weeks, Jun 26 to Aug 31 | +0.48 | 20 | 79% | 36% | 43% | -$20 | -$72 |
| **Test weeks, Sep 1 to Oct 9** | **-3.94** | 19 | 76% | 24% | 66% | -$19 | -$115 |
| Test weeks, no $15 daily stop | -4.55 | 22 | 75% | 24% | 66% | -$29 | -$133 |
| Test weeks, with CP switched on | -16.75 | 45 | 67% | 0% | 100% | -$23 | -$471 |

The daily stop only blocks new trades. Positions already open still run to their own stops, so a day can end below -$15.

## The indicator: GoldMicroScalpSignals

Put it on an XAUUSD M1 chart. It marks the minutes the EA would trade, inside the same entry hours: an arrow under the candle is a buy, over the candle a sell. Blue is PB, orange SF, violet QB, grey CP. The bottom-left panel shows the H1 trend, the live spread, today's signal count per module, and the spread those trades would pay. It can share a chart with the EA, whose panel is top-left. Since v1.30 it applies the same session window, body, pattern, M5 and spread filters. For past candles it uses the spread MT5 recorded on the entry minute (a recorded 0 counts as unknown and isn't filtered); the panel also shows the spread limit and how many of today's signals it skipped for spread. It doesn't show the daily stop or the open-position caps.

## How to run it

1. Demo account only, hedging mode.
2. Copy the two files into MQL5/Experts and MQL5/Indicators, open them in MetaEditor and press F7.
3. Strategy Tester: XAUUSD, model **"Every tick based on real ticks"**. "1 minute OHLC" makes tight targets look better than they are.
4. For v1.30, compare the tester's entry times and directions with `ea/expected_entries_v130.csv` (Jun 29 to Oct 9, 2026, default inputs). The tester's own spread decides which pass the spread limit, so expect fewer or more where the spread sits near $0.125. `ea/expected_trades.csv` is for v1.10. Your broker's spread and commission will move the totals. For a pure signal check, set the daily loss and the spread filter to 0 and compare entry times only.
