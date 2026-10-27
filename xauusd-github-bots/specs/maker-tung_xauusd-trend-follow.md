# maker-tung/xauusd-trend-follow — src/XAUUSD_TrendFollow.mq5 v1.00

Source read: `src/XAUUSD_TrendFollow.mq5` (~330 lines), `setfiles/H1_FTMO_primary.set`, `README.md`, `docs/*.md`. The `reports/` and `screenshots/` referenced in README are **not in the repo clone**.

## 1. Author's claims
- "MetaTrader 5 Strategy Tester, FTMO-Server data feed, Period: January 2022 - May 2026, 100% real ticks, Spread 0.30, Initial deposit $10,000, Leverage 1:30", H1.
- Net +$5,480 (+54.8%), Max equity DD 6.22%, worst day -1.00%, **Win Rate 25.8%**, **PF ~1.17**, Sharpe ~2.42, ~1,354 trades long-only, avg hold ~5.4 h, "profitable every year".
- Excluded M5 variant (risk 0.35%, TP 5R, SL 1.5R): +76.4%, DD 12.07%, PF 1.17, Sharpe 2.42 (identical PF/Sharpe to H1 — looks copy-pasted).
- Internal inconsistencies: README text says "28% win rate" elsewhere; docs say time exit (60 bars) closes 14% of trades, which alone implies avg hold >= 8.4 h, contradicting 5.4 h. Sharpe 2.42 with PF 1.17 is implausibly high. Numbers are self-reported, no report file present.

## 2. Timeframes
`InpTimeframe` = PERIOD_H1 for all indicators and bar logic. No HTF data.
**Set-file bug**: `InpTimeframe=12` in `H1_FTMO_primary.set`. In MQL5 the enum value 12 is **PERIOD_M12** (H1 = 16385), so loading the provided set file runs it on M12.

## 3. Inputs (defaults; set file identical except TF)
EMA_Trend 200; EMA_Fast 9; EMA_Slow 21; UseADXFilter true; ADX_Period 14; ADX_MinLevel 20; UseMACDCross true (MACD 12/26/9 close, hard-coded); UseStochCross true (Stoch 5/3/3, SMA, Low/High, hard-coded); UseEMACross true; Stoch_MaxLevel 60; RiskPercent 0.25; TP_ATR 6.0; SL_ATR 1.25; ATR_Period 14; MaxBarsInTrade 60; DailyLossLimit 4.0%; MaxLossLimit 8.0%; OnlyOnePosition true; Slippage 30; Magic 20260523.

## 4. Entry rules — LONG ONLY, evaluated once on the first tick of each new H1 bar
All on closed bars (shift 1 = last closed, shift 2 = the one before). All EMAs close-based.
1. Trend: close[1] > EMA200[1].
2. ADX(14) main line [1] >= 20 (DI lines not used).
3. Trigger (OR, any one):
   - MACD main[1] > signal[1] and main[2] <= signal[2]
   - Stoch %K[1] > %D[1] and %K[2] <= %D[2] and %K[1] < 60
   - EMA9[1] > EMA21[1] and EMA9[2] <= EMA21[2]
4. Gates: no own position (OnlyOnePosition); risk limits OK (see 6). No session/hour filter, no day-of-week filter, no spread filter, no cooldown (can re-enter on the very next bar after an exit if a trigger fires).
- Market buy at Ask at the open of bar 0. A signal arising while a position is open is simply skipped (not queued).

## 5. Exits
- SL = Ask - 1.25 x ATR(14)[1]; TP = Ask + 6.0 x ATR(14)[1] (4.8R). Fixed, set at entry.
- Time exit: every tick, if `iBarShift(openTime) >= 60` (i.e. 60 H1 bars since the entry bar) -> close at market (in bar terms: close at the open of the 60th bar after the entry bar).
- No breakeven, no trailing, no partials, no Friday/weekend close, no opposite-signal exit (there are no shorts).

## 6. Sizing / risk
- lot = Balance x 0.25% / (SLdist / tick_size x tick_value), floored to lot step, clamped to [min, max]. (Typical XAUUSD contract 100 oz: loss per lot = SLdist x 100 USD.) Note clamping up to min lot can over-risk small accounts.
- Daily stop: equity vs equity at first tick of the server-calendar day <= -4% -> no new entries that day.
- Max loss: equity vs balance at OnInit <= -8% -> permanent halt (also stops time-exit management; SL/TP remain).
- Single position, no hedging, no grid, no martingale.

## 7. Code vs README
- Code matches README's signal description well (README pseudo-code is accurate). Long-only, bar-close evaluation; no look-ahead or repaint (all shifts >= 1; entry at next bar open).
- Discrepancies: set-file timeframe bug (M12); performance docs internally inconsistent; reports/screenshots missing. README "Peak entry hours 13-16 server time" is an observation, not a filter.

## 8. Red flags
- None in code: no WebRequest, no DLL, no credentials, no obfuscation, no product links. License CC BY-NC 4.0. Positioned as a "portfolio demonstration"; FTMO-prop-firm framing only.

## 9. Reimplementation notes
```
H1 bars, signals on closed bar i, entry at open of bar i+1:
if not halted and no position and day_equity_ok:
  if close[i] > EMA200[i] and ADX14[i] >= 20 and (
       crossup(MACD12_26_9.main, .signal, i) or
       (crossup(Stoch5_3_3.K, .D, i) and K[i] < 60) or
       crossup(EMA9, EMA21, i)):
     entry = open[i+1] + spread (ask); atr = ATR14[i]
     SL = entry - 1.25*atr ; TP = entry + 6*atr
     size = 0.25% balance / (1.25*atr*contract)
manage each bar: SL/TP intrabar (assume SL first if both hit);
  if bars_since_entry_bar >= 60: close at open of that bar
crossup(a,b,i): a[i] > b[i] and a[i-1] <= b[i-1]
```
Use ATR = Wilder-smoothed? NOTE: MT5 iATR is a simple moving average of True Range (not Wilder). MT5 ADX uses its own EMA-style smoothing (iADX, not Wilder ADXW). MT5 Stoch "MODE_SMA, STO_LOWHIGH" = %K raw over 5 then SMA3 slowing, %D = SMA3 of %K. MACD signal in MT5 is an SMA(9) of the MACD line, not an EMA.
