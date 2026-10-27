# BAKOME-Hub/BAKOMEGoldScalper — Ultimate_ICT_Gold_Scalper_v3.0.mq5

Source read: `Ultimate_ICT_Gold_Scalper_v3.0.mq5` (612 lines), `README.md`, `FUNDING.json`.

## 1. Author's claims (README)
- "Backtest Results (XAUUSD, M5, 2024-2025)": 342 trades, **Win Rate 68.7%**, **PF 1.82**, Max DD 12.4%, "Average RR 1:2.3", "real tick data, 1% risk per trade, default parameters". No account size, no report file.
- Claims "1800+ lines of production-ready code", FVG / Order Blocks / Liquidity Sweeps / Silver Bullet, partial close, "AI-powered market structure".

## 2. Timeframes
- Hard-coded `PERIOD_M5` for all price reads, ATR(14) on M5 (chart TF irrelevant).
- H4 EMA(200, close) = bias. H1 EMA(34) handle created but **never read**. D1/W1 current high/low read only into an unused liquidity array.

## 3. Inputs that affect trading (defaults)
RiskPercent 1.0; MaxDailyRiskPercent 5.0; MaxDailyProfitPercent 8.0; MaxPositions 2; MaxDailyTrades 10; MinATR_Points 100; MaxSpreadPoints 50; ATR_SL_Multiplier 2.0; ATR_TP_Multiplier 3.0; TradeAsianSession false; TradeLondonSession true; TradeNewYorkSession true; LondonStartHour 7; NewYorkStartHour 13; UseSilverBullet true; LondonSilverBullet true, LondonKillZone 8-9; NewYorkSilverBullet true, NYKillZone 15-16; UseBreakEven true, BE_TriggerATR 1.0; UseTrailingStop true, Trail_StartATR 1.5, Trail_StepATR 0.5; SlippagePoints 10.
Inputs with **no effect**: UseLiquiditySweeps, UseFairValueGaps, UseOrderBlocks, LiquidityLookback, FVG_Lookback, FVG_MinSizeATR (structures are computed every tick but never used in a decision), UsePartialClose / PartialClosePercent / PartialCloseTriggerATR (no code), UseAsyncExecution, EnablePerformanceMode.

## 4. Entry rules (as coded) — evaluated on EVERY TICK, no new-bar gate
1. Kill zone (server time, `TimeCurrent()` hour): 08:00-08:59 or 15:00-15:59. If UseSilverBullet=false it **never trades**.
2. Bias: `close[0]` of M5 (forming bar = current bid) vs H4 EMA200 buffer[0] (forming H4 bar). Above -> BUY, below -> SELL.
3. Gates (`CanOpenNewPosition`): own-magic open positions < 2; `SYMBOL_SPREAD` <= 50 points; ATR(14,M5)[0]/point >= 100 (ATR >= $1.00); session hour in [7,11) or [13,17) (kill zones are inside these anyway).
4. Daily limits: trade counter >= 10 or equity vs start balance <= -5% or >= +8% blocks. **Bug: `ResetDailyStats()` is never called**, so the counter and start balance are set only at OnInit -> after 10 trades total the EA stops forever (until re-attached) and the % limits are measured from the start of the run.
- No day-of-week rule, no cooldown, no new-bar check -> at 08:00 the first two ticks open two same-direction positions immediately; after one closes, another opens on the next tick while in the window.
- Market order at Ask (buy) / Bid (sell).

## 5. Exits
- SL = entry -/+ 2.0 x ATR(14,M5)[0]; TP = entry +/- 3.0 x ATR (1.5R).
- Break-even: only called when `StopLoss()==0 && Profit()>0`; SL is always set at entry -> **never fires**. (Also compares money profit to an ATR price value.)
- Trailing: one-shot. When position `Profit()` (account currency!) >= 1.5 x ATR (price units, e.g. 1.5x3.0 = 4.5), set SL = Bid - 0.5xATR (buy) / Ask + 0.5xATR (sell) if it improves the SL, then `trailingActive=true` and never trails again. Unit mismatch means it triggers at a tiny $ profit with large lots.
- No partial close, no time exit, no Friday/EOD close, no opposite-signal exit.

## 6. Sizing
`lot = Balance*1%/(ATR*Point*10)`, rounded 2 dp, clamped [0.01, 100]. With ATR=3.0, point=0.01: $10k -> 100/(0.3) = 333 -> **100 lots** (min would be 0.33 even on $100). Real risk is ~ lot*2ATR*100 = absurd; broker usually rejects (no money / volume max). No hedging logic, no grid, no martingale; but two same-direction positions allowed.

## 7. Code vs README
- **File line 1 is a Markdown fence "```cpp"** -> as committed it will not compile in MetaEditor.
- 612 lines, not "1800+". FVG/OB/liquidity/Silver Bullet "ICT" logic is decorative: the only signal is price vs H4 EMA200 inside a 1-hour window.
- Partial close claimed, absent. BE claimed, dead. "Daily loss limits" broken (never reset). Lot formula wrong by orders of magnitude.
- README backtest (68.7% WR, 1:2.3 RR, PF 1.82) is not reproducible from this code: fixed 1.5R TP with immediate entries and broken sizing. Treat as unverified/likely fabricated.
- Look-ahead: none per se (uses current forming values in real time), but backtest should use the live bid vs forming H4 EMA.

## 8. Red flags
- No WebRequest, no DLL imports, no credential requests, no obfuscation.
- README + FUNDING.json solicit crypto donations (BTC/ETH/SOL/USDT addresses), Drips, GitHub Sponsors. Marketing language ("institutional-grade", "AI-powered") not backed by code. Inflated claims.

## 9. Reimplementation notes (faithful, with obvious unit bugs replaced)
```
on each M5 bar (or tick-level approx: use bar open of each M5 bar within window):
  hour = server_hour(t)
  if hour not in {8, 15}: continue
  if n_open >= 2 or spread_pts > 50 or ATR14_M5/0.01 < 100: continue
  if total_trades_since_start >= 10: stop   # faithful bug; set False to "fix"
  bias = sign(price - EMA200_H4_current)   # H4 EMA incl. forming bar
  open market in bias dir: SL = 2*ATR, TP = 3*ATR
manage: once floating profit >= 1.5*ATR (use price distance, intended), move SL to price -/+ 0.5*ATR once.
size: use proper 1% risk on 2*ATR SL (original formula is broken).
```
Expect it to open two trades at the very start of 08:00 and 15:00 windows, and re-enter on the next tick after any close.
