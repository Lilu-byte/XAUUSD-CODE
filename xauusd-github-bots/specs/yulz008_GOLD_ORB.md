# yulz008/GOLD_ORB — GOLD_ORB/GOLD_ORB.mq5 (Ulysses O. Andulte, 2022)

Source read: `GOLD_ORB.mq5`, `Include/price_action.mqh`, `Trade.mqh`, `TrailingStops.mqh`, `MoneyManagement.mqh`, `RiskManagement.mqh`, `TradeVirtual.mqh` (skimmed), `Indicators.mqh`, `Input/default_input.set` (UTF-16), `readme.txt`, `README.md`. Alglib/Fuzzy/Math/Stat library code skipped. The repo tree (git HEAD) also contains a compiled **`GOLD_ORB/GOLD_ORB.ex5`** and `Test Cases/Test Cases.pptx` — not in the text-only clone; not opened.

## 1. Author's claims
- "Expert Advisor for XAUUSD (GOLD) on 1HR TF"; readme.txt: "Profitable on Bull Market". Tested on "ICMarkets MT5 (Real Account Server)", hedging account.
- Backtest results only as screenshots (no win rate / PF / period stated in text). Educational framing ("meant to be used for learning... no warranty").

## 2. Timeframes
Chart TF = H1 (all logic uses `_Period`). No HTF. An SMA(100, close) of the chart TF is computed each bar but **never used** in any decision.

## 3. Inputs (code defaults; set file differs only where noted)
StartOfTradingHour_ServerTime 1; TakeProfit 1200 pts ($12.00); StopLoss 400 pts ($4.00); MaxTradePerDay 2; LongPosition true; ShortPosition true; EnableTrail true; MaxEquityDrawdownPercent **10** (set file: **0**); MaxRiskPerTradePercent 1; FixedVolume 0.1; SlopeDetection false; LossStreakCounter 0; PriceActionORB_CandleComposition 3.
Hard-coded: trailing 700 pts / min profit 100 pts / step 10 pts; long-wick threshold 500 pts; range-extension threshold 0.1 price; deviation 50 pts; magic = 0 (never set).

## 4. Entry rules — evaluated once at the first tick of each new H1 bar (server time)
State machine in `Price_Action::Open_Range_Breakout()`; `prev` = bar 1 (last closed), `hour` = hour of current bar 0.
1. **Daily reset** at the bar with hour == 1 (requires flag `first_candle`, which is re-armed at hour == 2): range = 0, counters = 0, long_flag = short_flag = false, trade_today = true. No signal on this bar.
2. **Initial range** at the next bar (hour 2): from the 01:00 candle:
   - R_high = wick high, unless upper wick (high - max(open,close)) > 500 pts ($5) -> R_high = body high. Store B_high = body high.
   - R_low = wick low, unless lower wick > $5 -> R_low = body low. Store B_low = body low.
   - counters stay 0 here and UpdateFlags then makes cR = cS = 1.
3. **Each later bar** (until next day's 01:00 bar; runs through midnight):
   - If 1 <= cR <= 3: if prev.high > R_high + 0.1 and prev.body_high > B_high + 0.1 -> R_high = prev.high (or prev.body_high if prev upper wick > $5), B_high = prev.body_high, reset cR to 1. Same for support with lows (prev.low < R_low - 0.1 and prev.body_low < B_low - 0.1).
   - Then cR += 1 unless reset (-> 1); same for cS.
   - **Buy signal**: cR > 3 and prev is bullish (close > open) and prev.close > R_high and trade_today and not long_flag. -> set long_flag (if MaxTradePerDay==2) or trade_today=false (if ==1).
   - **Sell signal** (checked only if no buy returned): cS > 3 and prev bearish and prev.close < R_low and trade_today and not short_flag.
   - In practice the range is the 01:00 candle extended by any new high/low made within 3 bars of the last extension; once 3 bars pass with no extension the side is frozen. Signals effectively need 3 consecutive non-extending candles after the last extension: with no extension the 02:00, 03:00, 04:00 candles complete the box and the first realistic signal is decided at the 06:00 bar open from the 05:00 candle (a 05:00-bar signal from the 04:00 candle is only possible in a <=0.1 edge case).
   - When both flags set, trade_today=false. Max per day: 1 long + 1 short. (MaxTradePerDay other than 1/2 => no limit.)
4. Market order at Ask/Bid at the bar-0 open tick. **No position-count limit, no spread filter, no session end, no day-of-week rule**; positions from previous days stay open, so several can coexist (hedging). MA100 filter is not applied.

## 5. Exits
- SL = entry -/+ 400 pts ($4.00); TP = entry +/- 1200 pts ($12.00) (3R), relative to the fill price (Ask for buy, Bid for sell).
- Trailing (every tick, **all account positions, no magic/symbol filter**): buy: newSL = Bid - 7.00; modify if newSL > currentSL + 0.10 and Bid - open >= 1.00. Sell: newSL = Ask + 7.00; modify if newSL < currentSL - 0.10 (or SL==0) and open - Ask >= 1.00. Because the initial SL is $4 away, trailing effectively starts once profit > ~$3.10 and then trails $7 behind (i.e. loosens nothing; only moves when it tightens).
- No breakeven, no partials, no time exit, no EOD/Friday close, no opposite-signal exit.

## 6. Sizing
`MoneyManagement`: if risk% > 0: lots = (Balance x 1% / 400) / SYMBOL_TRADE_TICK_VALUE, rounded to volume step (risk% capped at 10). With tick value $1/0.01/lot -> $10k => 0.25 lots (correct 1% risk only if tick size == point). FixedVolume 0.1 used only if risk% = 0. Recomputed every tick from current balance. No grid/martingale; hedging (simultaneous long+short) allowed and expected.

## 7. Code vs README / bugs
- **Blocking bug**: in `RiskManagementModule` the drawdown `if` has no braces, so `execute_trade = false;` runs on every tick whenever MaxEquityDrawdownPercent != 0. With the code default (10) **no real orders are ever sent** (only virtual trades). It trades only with the provided set file (value 0). The drawdown stop therefore never works as described.
- Possible compile clash: input `LossStreakCounter` has the same name as the function `LossStreakCounter()` in RiskManagement.mqh.
- README says trail "activates at 700 points ... 100 points minimum"; code is a 700-pt trailing distance with 100-pt min profit.
- MA100 described as optional example; computed, unused (handle leak each bar).
- No look-ahead: decisions use closed bar 1 at bar-0 open.

## 8. Red flags
- Compiled `GOLD_ORB.ex5` committed in repo (not touched). No WebRequest, no `#import`/DLL, no credentials, no paid links. Trailing module modifies *any* position on the account (incl. manual trades / other EAs).

## 9. Reimplementation notes
```
H1 bars, server time. For each bar t (decide at open of t using closed bar p=t-1):
 if hour(t)==1 and armed: reset(); armed=False; init_next=True; continue
 if hour(t)==2: armed=True
 if init_next: set R/B from p (wick>5$ -> use body); cR=cS=1; init_next=False
 else:
   ext = Rset and 1<=cR<=3 and p.high>R_high+0.1 and body_high(p)>B_high+0.1
   if ext: extend high (use body if upper wick>5$); cR=1  else: cR+=1   # same for low/cS
 if cR>3 and p.bull and p.close>R_high and not long_done: BUY at open(t); long_done=True
 elif cS>3 and p.bear and p.close<R_low and not short_done: SELL; short_done=True
 orders: SL 4.00, TP 12.00; trail: when profit>=1.00, SL=max(SL, price-7.00) if improves by >0.10
 run faithfully with set-file values (MaxEquityDrawdownPercent=0), else nothing trades
```
Counter detail: ResetVariables sets counters to 0; the init bar's UpdateFlags makes them 1; each non-extending bar adds 1; an extension sets 1. Signal needs counter > 3, checked after the update on the same bar.
