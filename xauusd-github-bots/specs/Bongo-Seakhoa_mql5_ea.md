# Bongo-Seakhoa / mql5_ea (DayTradingEA_v2.mq5)

## 1. Author's claims
- The README makes no performance claims: "The notebook is research tooling, not proof of live profitability"; intended for "M5 and M15 charts".
- **Nothing in the repo is XAUUSD-specific.** No file mentions XAU or gold. The notebook tests **EURUSD M15** from 2022-01-01 to the run date.
- Notebook output: "Total Trades: 3198, Total Profit: 0.598…, Win Rate: 61.91%". That profit is a sum of raw price differences for 1 unit, i.e. about 1.9 pips per trade before commission. The repo's own audit.md calls it "effectively flat before commission and slippage".
- Signal and entry are on the same bar close, so the notebook trades with some look-ahead.

## 2. Timeframe
Chart TF (`_Period`), intended M5 or M15. No HTF data.

## 3. Defaults
BB(20, 2.0, close), EMA 20 (close), RSI 14, ATR 14, ATR SL mult 2.0, risk 2% of equity, min lot 0.01, max daily DD 3%, max total DD 10% from peak, magic 202603, max spread 30 pts (SYMBOL_SPREAD), slippage 10, re-entry wait 2 candles, session 7–20 server time, Friday cutoff true (hard-coded 20:00), RSI buy max 40, RSI sell min 60.

## 4. Entry (OnTick runs only on a new candle, detected by a change in iBars)
Indicators come from bar 1 (BB upper/mid/lower, EMA, RSI, ATR). Price conditions mix bars 1–4.
**Buy signal**, all of:
- C2 < BBlow[1] or L2 < BBlow[1]
- C4 < EMA[1] and C3 < EMA[1]
- C4 > C3 > C2 (three falling closes)
- RSI[1] < 40
- Bullish pattern on bar 1:
  - hammer (lowerWick > 2·body, upperWick < 0.5·body, body > 0.1·range), **or**
  - engulfing (bar 2 bearish, bar 1 bullish, C1 > O2, O1 < C2).

**Sell** is the mirror: C2 > BBup[1] or H2 > BBup[1]; C4, C3 > EMA; C4 < C3 < C2; RSI > 60; shooting star or bearish engulfing.

Then:
- **Immediate entry** if C2 is back inside the band: BBlow < C2 < BBmid for a buy (BBmid < C2 < BBup for a sell). In practice this means only the wick pierced the band.
- Otherwise go into **pending**: store that bar's bands. On each of the next 2 new bars, enter if C1 is inside (storedLow, storedMid) for a buy (mirror for a sell). Cancel after 2 bars. While pending, no new signals are generated.

Gates, checked only while flat:
- Drawdown breaker: daily DD from day-start equity ≥ 3%, or DD from peak ≥ 10%. The total-DD lock is effectively permanent, because equity cannot recover while flat.
- Session: hour in [7, 20); no Saturday or Sunday; no Friday ≥ 20:00.
- Spread ≤ 30 pts.
- At most 1 position. No news filter, no cooldown, no daily trade cap.
- Market order at ask/bid on the first tick of the new bar.

## 5. Exits (checked once per new bar from C1 and bar-1 indicators; no market closes)
- Initial SL = entry ∓ 2·ATR[1]. TP = the opposite band (BBup[1] for a buy).
- Breakeven: when C1 ≥ entry + (entry − SL), set SL = entry + 2 pts. This uses the *current* SL distance.
- EMA trail: when C1 ≥ EMA[1] and EMA > SL, set SL = EMA.
- Fibonacci trail: for f in {0.236, 0.382, 0.5, 0.618}, target = EMA + f·(BBup − EMA). When C1 ≥ target and target > SL, set SL = target. The highest level reached wins.
- TP only expands: if BBup[1] > TP, set TP = BBup[1] (mirrored for sells).
- Stop-level distance is not validated on modify, so a modify can fail silently.
- No time exit, no Friday close (the "friday_cutoff" input only blocks entries), no opposite-signal exit, no partial closes, no DD-triggered close.

## 6. Sizing
lots = 2%·equity / (SLdist · tickValue/tickSize), floored to step and clamped to at least 0.01. One position at a time. No grid, martingale or hedge.

## 7. Code vs README
v2 matches the README bullets.
- "Daily and total drawdown circuit breakers" only gate new entries, and only while flat. The daily reset also only happens while flat.
- The indexing is asymmetric: bands from bar 1 but the breach test on bar 2, and the pattern on bar 1. This is not look-ahead (all bars are closed) but it is easy to get wrong in a port.
- Black_Box.mq5: audit.md says its iBands buffers were mapped wrong (0 = upper; the base is buffer 0) and that its "re-entry wait" only re-read past candles. The CHANGELOG claims both were later fixed.
- TestEA.mq5: older EMA20/EMA50 version with 5% risk; the audit says its trailing stop never reached the broker.
- Not tuned for gold. A 30-pt spread cap on XAUUSD (0.30 $) blocks many brokers' typical 20–40 pt spreads part of the time.

## 8. Red flags
- No WebRequest, DLL, obfuscation or paid product.
- The notebook contains a hard-coded MT5 **login number (number withheld here)** with the password and server redacted. That is a credential-hygiene issue, not a lure.
- FUNDING.yml links a PayPal donation (paypal.me/Bongi917). That is a donation link, not a product sale.

## 9. Reimplementation (any TF; decide at the open of bar t, k = t−k)
```
bbU,bbM,bbL,ema,rsi,atr = ind[t-1]
if pos: (long shown)
   if C1>=entry+(entry-SL): SL=max(SL,entry+2pt)
   if C1>=ema: SL=max(SL,ema)
   for f in fibs: x=ema+f*(bbU-ema); if C1>=x: SL=max(SL,x)
   TP=max(TP,bbU)                       # check SL/TP intrabar on H/L
elif dd_ok and 7<=hour<20 and weekday and not(fri>=20) and spread<=30:
   if pending: n-=1; if bbL_p<C1<bbM_p: enter; pending=False
               elif n<=0: pending=False
   else:
     buy = (C2<bbL or L2<bbL) and C4<ema and C3<ema and C4>C3>C2 and rsi<40 and bull_pat(bar1,bar2)
     if buy: if bbL<C2<bbM: enter else pending(buy, bands, n=2)
   enter: SL=fill-2*atr; TP=bbU; lots=2%eq/SLdist
```
