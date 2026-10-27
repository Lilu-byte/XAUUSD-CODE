# Sandyyy123 / xauusd-scalper-research

**Licence:** the README says "Proprietary — All Rights Reserved … may not be used, run, copied, modified … without prior written permission". The LICENSE file it links does not exist. The strategy is a generic EMA/RSI/Stochastic combination; rebuild it from this description and do not copy the code.

## 1. Author's claims
The overview lists **targets**: "Win rate: 75%+", "Monthly return / max drawdown ratio: 4–5x", "~20 minutes".

The table "Backtest Results (Walk-Forward, Jan 2023 – Apr 2024)" reports:

| Metric | Value |
|---|---|
| Trades | 847 |
| Win rate | 77.3% |
| Avg duration | 18.4 min |
| Max drawdown | 4.2% |
| Monthly return | 18.6% |
| Return/DD | 4.43x |
| PF | 2.31 |
| Sharpe | 1.87 |

It also benchmarks itself against named myfxbook accounts ("Vantage Scalping Social", "Metafund Gold Signal"). Timeframe M5. No account type is given.

## 2. Timeframe
M5 throughout. The EA hard-codes PERIOD_M5 for all handles. Python uses yfinance `GC=F` 5m (gold **futures**, not spot XAUUSD). No HTF.

## 3. Defaults
- EA: EMA 20/50 (close), RSI 7 with OS 30 / OB 70, Stoch(5,3,3, SMA, low/high), ATR 14, SL 1.0·ATR, TP 1.5·ATR, max 2 concurrent, fixed lot 0.01, session 7–17 by the server-clock hour (commented "UTC"), deviation 20, magic 202400001.
- Python: same periods. Commission 0.0003 and slippage 0.0001 as *fractions of price* (about $0.60 and $0.20 at $2,000). Timeout 60 bars.

## 4. Entry
**EA (OnTick, every tick, no new-bar gate):** all values from bar 1.
- Long when EMA20 > EMA50, RSI < 30, %K < 20 and %K > %D.
- Short when EMA20 < EMA50, RSI > 70, %K > 80 and %K < %D.
- Gates: only server hour in [7, 17) and open positions < 2.
- No spread filter, no ATR gate (only ATR > 0), no news filter, no day-of-week rule.
- `stoch_k1` is read but never used. There is **no "RSI divergence"** anywhere.
- Because the shift-1 signal stays true for the whole bar, the EA opens **2 positions on consecutive ticks** of the same bar.

**Python (`generate_signals`):** same trend and trigger, with some differences:
- RSI uses a rolling *mean* of gains and losses (Cutler), not Wilder's.
- %K is the *raw* 5-bar value with no slowing; %D = SMA3(%K).
- ATR = SMA14(TR).
- Extra gate: ATR > 0.8·SMA50(ATR).
- Sessions 07:00–11:00 and 13:00–17:00, bar timestamp, end inclusive, in the yfinance index timezone.
- A long takes priority over a short on the same bar.

## 5. Exits
- **EA:** fixed SL = ask − 1·ATR, TP = ask + 1.5·ATR (mirrored for shorts). Nothing else: no BE, trailing, time exit or Friday close.
- **Python:** entry = signal-bar Close × (1 ± 0.0001). SL and TP are computed from the *unslipped* Close ± k·ATR. Each following bar checks SL before TP (pessimistic). If neither is hit within 60 bars, exit at bar 60's close. PnL is a percentage minus 0.0003.

## 6. Sizing
EA: fixed 0.01 lot. Python: equal percentage per trade, no compounding. No grid or martingale. Up to 2 concurrent positions, in the same direction.

## 7. Does the code match, and are the results real? **No; the results look fabricated or aspirational.**
- **yfinance gives 5-minute bars only for about the last 60 days.** `backtester.py`'s `__main__` asks for 2023-01-01 to 2024-04-30 at 5m, which returns empty or errors. The README's 15-month M5 walk-forward cannot have come from this code.
- Recent yfinance returns MultiIndex columns, so `row["Close"]` would also fail.
- `outputs/backtest_report.csv`, `src/data_fetcher.py` and `LICENSE` are all **missing**, though the README lists them.
- **Internal inconsistency:** at 77.3% win rate with a 1.5:1 reward/risk, the gross PF would be about 0.773·1.5 / 0.227 ≈ **5.1**, not 2.31. The costs needed to close that gap would also wipe out the "18.6%/month at 4.2% DD".
- The metrics code is unsound:
  - "monthly return" assumes 22 trades per month (`len(trades)/22`).
  - Sharpe annualises *per-trade* returns by √(252·78).
  - `open_count` is recomputed only from trades that timed out, so the concurrency limit is not enforced in time.
- `print_report` prints "Target: Win Rate >= 75% PASS/FAIL", and a comment says "client target: 4-5x". This reads like a freelance deliverable whose 75% is a **target**, not a measured result.
- The git history is a single commit ("Add proprietary license and notice", Sep 2026).
- The EA diverges from the Python: different RSI and Stochastic definitions, no ATR gate, one 7–17 window instead of two, and every-tick double entries.

**Conclusion:** the 75% win rate is a target, and the 77.3% table is not reproducible from the repo. There is no evidence of a real run.

## 8. Red flags
- No WebRequest, DLL, obfuscation or credential requests.
- Credential-style marketing: "PhD-level", "Dr. … PhD Data Science", unverifiable myfxbook benchmarks, fabricated-looking stats.
- A restrictive proprietary licence on a public repo.
- No paid links.

## 9. Reimplementation (M5; the Python version is the cleaner spec)
```
ema20,ema50 = EMA(C,20),EMA(C,50)          # adjust=False
rsi = RSI7 (choose Wilder for MT5 parity, or SMA for Python parity)
k = 100*(C-min(L,5))/(max(H,5)-min(L,5)); d = SMA3(k)   # MT5: slow %K = SMA3 of the raw ratio sums
atr = SMA14(TR)
long  = ema20>ema50 & rsi<30 & k<20 & k>d & atr>0.8*SMA50(atr) & session
short = ema20<ema50 & rsi>70 & k>80 & k<d & ...
on signal at close of bar t: enter at O[t+1] (or C[t]); SL=±1.0*atr[t]; TP=±1.5*atr[t]
exit: SL-first check on H/L each bar; timeout 60 bars; max 2 open (enforce in time)
```
Expect a win rate around 40–50%, which is what a 1:1.5 ATR bracket typically gives, not 75%.
