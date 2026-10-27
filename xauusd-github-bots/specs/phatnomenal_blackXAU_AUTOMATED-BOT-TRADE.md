# phatnomenal/blackXAU_AUTOMATED-BOT-TRADE — blackXAU2.mq5 (v1.22 "H4_Zone_Retest_M5_Fixed")

Source read: `blackXAU2.mq5` (~230 lines), `README.md`.

## 1. Author's claims
- "Backtest — Symbol: XAUUSD, Timeframe: M5, Period: Jan 2022 – Oct 2025, Model: Every tick". Results only as screenshots; text claims "consistent trade execution, controlled drawdown, and stable risk-adjusted returns", "includes realistic spreads and commissions". **No win rate / PF / account size stated in text.**
- README strategy: "marks the first H4 candle of the current day" as zone, buy and sell retests, SL = breakout candle low/high, TP 1.5x risk, "high-impact" news filter.

## 2. Timeframes
- Signal bars hard-coded `PERIOD_M5` (chart TF irrelevant).
- Zone: **D1 previous day high/low** (ZoneMode 0, default). ZoneMode 1 uses H4.
- Filters: H1 EMA(50) & EMA(200) close; SL/TP ATR(14) on H1. Trail mode 1 (off) uses ATR(14) M15.

## 3. Inputs (code defaults)
Lots **0.1** (README says 0.01); MaxWaitSeconds 86400; UseRiskPercent false; RiskPercent 1.0; Slippage 10; OnlyOnePosition true; UseNewsFilter true; NewsFilterMinutes 30; NewsFilterCurrency "USD"; UseTrailingStop true; TrailingMode 0; TrailingStart 200 pts; TrailingStep 100 pts; BE_MovePoints 300; MaxSpreadPoints 50; UseSessionFilter true; SessionStartHour 7; SessionEndHour 22; ShortLotMultiplier 0.5 (dead); ZoneMode 0; ZoneFirstH4Count 4; BreakoutBodyPct 50; BreakoutMinPoints 200; UseEMAFilter true; EMA 50/200 on H1; UseATRSizing true; ATR_Period 14 H1; ATR_SL_Mult 1.5; ATR_TP_Mult 3.0; Magic 202503.

## 4. Entry rules — LONG ONLY (sell block is commented out)
OnTick order: session gate -> zone update -> news gate -> if not first tick of a new M5 bar: trail and return -> else evaluate.
- **Session** (server `TimeCurrent()` hour): 7 <= hour <= 22 (i.e. 07:00-22:59). Outside, the EA returns immediately — **no trailing/BE management** outside session or during news.
- **News**: any calendar event with importance >= MODERATE (not only high) whose country currency contains "USD" within +/-30 min of now -> skip tick. MT5 calendar functions do not work in the Strategy Tester, so this is a no-op in the author's backtests.
- **Zone** (recomputed when D1 bar 1 changes): zoneHigh/zoneLow = previous D1 high/low.
- **Breakout** (evaluated on closed M5 bar 1 at the open of bar 0): close1 > zoneHigh and open1 <= zoneHigh and (|close1-open1| >= 50% of (high1-low1) or |close1-open1| >= 200 pts = $2.00) -> waiting=true, dir=+1, breakoutTime = bar1 open time. (Bearish breakout below zoneLow is also detected and sets dir=-1 but then nothing can be executed; it does overwrite/replace a pending long setup.) A newer breakout overwrites the old one.
- Expire setup when now - breakoutTime > 86400 s.
- **Retest** check only at each new M5 bar's first tick (= bar open): requires spread <= 50 pts (else return, setup kept); EMA filter: current H1 close (= bid) > EMA50_H1[1] and > EMA200_H1[1] (else return, setup kept); then if **Bid <= zoneHigh** -> buy market at Ask.
  - If a position already exists on the symbol with this magic -> setup cancelled.
  - Setup is cleared after the order attempt regardless of result.
- No day-of-week filter, no cooldown, one setup at a time, max one position.

## 5. Exits
- SL/TP computed from **entry = zoneHigh** (not the fill): SL = zoneHigh - 1.5 x ATR14_H1[1]; TP = zoneHigh + 3.0 x ATR14_H1[1]. (With UseATRSizing=false: SL = breakout candle low, TP = zoneHigh + 1.5 x (zoneHigh - SL) — this is what the README describes.) If the bar opens below the SL level, the order is rejected.
- Trailing (every tick in session, for **all positions on the symbol, any magic**): buy: if Bid - open > 200 pts ($2.00): newSL = Bid - 100 pts ($1.00), modify if > SL + 1 pt. BE: if profit >= 300 pts and SL < open -> SL = open (redundant: trail already above open).
  - Effect: once +$2 profit, SL ratchets $1 behind bid tick-by-tick. With H1 ATR of $5-$20 the 3xATR TP is rarely reached; most winners exit by the $1 trail (~+$1 to +$x).
- No partials, no time exit, no EOD/Friday close, no opposite-signal exit.

## 6. Sizing
Fixed 0.1 lot. Risk mode: 1% balance / (SL points x tick value), floored to step (assumes tick size == point). No hedging, grid or martingale.

## 7. Code vs README
- README says first H4 candle of the day; code default is **previous day's D1 range**. ZoneMode 1 is buggy: it takes the first H4 bar of today plus the **3 preceding (yesterday's) H4 bars** (index +k goes back in time), computed at the first tick of the day when today's first H4 bar has barely started.
- README describes sells; **shorts are commented out**.
- README SL = breakout candle extreme & TP 1.5R; code default is ATR-based SL/TP from the zone level.
- README Lots 0.01; code 0.1. "High-impact" news filter actually uses >= moderate and is inert in the tester.
- Trailing/BE suspended outside 07-22 server hours and during news windows.
- No look-ahead: breakout uses closed M5 bar, EMA/ATR on closed H1 bar [1]; the EMA comparison uses live price.

## 8. Red flags
None. No WebRequest, no DLL, no credentials, no paid links, no obfuscation (code is one-liner-compressed but readable). Uses built-in MT5 Calendar API only. Trailing touches other EAs'/manual positions on the same symbol.

## 9. Reimplementation notes
```
M5 bars, server time; zoneH = prev D1 high (zoneL = prev D1 low for bear-breakout overwrite)
at open of each M5 bar t (closed bar b=t-1), if 7<=hour(t)<=22:
  if b.close>zoneH and b.open<=zoneH and (body>=0.5*range or body>=2.00): setup=+1, t0=b.time
  elif b.close<zoneL and b.open>=zoneL and (same body test): setup=-1 (dead; just cancels long)
  if setup and t - t0 > 1 day: setup=0
  if setup==+1 and spread<=0.50 and bid>EMA50_H1[last closed] and bid>EMA200_H1[last closed]:
     if open(t) <= zoneH:
        if no position: buy at ask; atr=ATR14_H1[last closed]; SL=zoneH-1.5atr; TP=zoneH+3atr
        setup=0
manage intrabar (only while 7<=hour<=22): if bid-entry>2.00: SL=max(SL, bid-1.00)
```
Use tick or M1 data for the trailing; on M5 OHLC, the $1 trail makes results path-dependent.
