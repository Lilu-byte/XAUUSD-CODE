# francomascareloai / EA_SCALPER_XAUUSD

## What it is
A public "building in public" snapshot of an SMC/ICT gold scalper. It contains:
- The main EA, `MQL5/Experts/EA_SCALPER_XAUUSD.mq5` (1.8k lines), plus about 40k lines of includes under `MQL5/Include/EA_SCALPER/`.
- Aggressive variants and a `SmartPropAI_Template`.
- Python backtest/validation scripts.
- About 150 docs, mostly in Portuguese, written by named AI "agents" (ARGUS / ORACLE / FORGE / CRUCIBLE).

The README says the real strategy and the Nautilus Python stack are private: "None of the proprietary rules, parameters ... are included".

## Author claims
README: "analyzed 5,000+ trading bots ... Most were the same recycled martingale/grid". There is **no dataset or tabulated survey of those bots in the repo**. The closest material is AI-written web research:
- `DOCS/03_RESEARCH/FINDINGS/WORLD_BEST_TRADING_ROBOTS_ANALYSIS.md`: MyFXBook top-10 and FTMO trader anecdotes.
- `XAUUSD_BREAKOUT_EA_PATTERNS_RESEARCH.md`: a red-flag taxonomy.

The README says it makes no performance claims. Some internal docs nevertheless declare "GO":
- `04_REPORTS/VALIDATION/FINAL_VALIDATION_REPORT.md`: "GO FOR LIVE", WR 87.1%, PF 7.57, Sharpe 268, on 15M ticks from Oct-Dec 2024 only.
- `REALISTIC_BACKTEST_REPORT_20251202.md`: "STRONG GO", PF 6.74.

These were later contradicted, see below.

## Out-of-sample / after-cost evidence (all self-reported, Python backtester; all negative or breakeven)
- **`VALIDATION/STRATEGY_COMPARISON_REPORT.md`** (M5, 2020-01 to 2025-11, spread x1.5, 0.5% risk). **Every strategy has PF < 1**:

  | Strategy | PF | Return |
  |---|---|---|
  | MA cross 20/50 | 0.82 | -8.4% |
  | RSI mean reversion | 0.68 | |
  | Donchian breakout | 0.79 | |
  | ADX+EMA trend | 0.45 | |
  | Momentum scalper | ~0.7 | |
  | EA confluence score >= 50 | 0.93 | |
  | EA confluence score >= 70 | 0.51 | |

- **`BACKTESTS/BASELINE_METRICS.md`:** MA 10/50 on 2020-24, 9,915 trades: PF 0.97, -52%, max DD 83%.
- **`VALIDATION/PHASE2_CRITICAL_FINDING.md`:** the EA logic over full-year 2024 returned **-26.1%**, with 4/12 profitable months and 840 trades. The earlier PF 1.80 "came from only the last 3 weeks of December 2024" (cherry-picked).
- **`VALIDATION/CRITICAL_ANALYSIS_FINAL.md`:** the 87% WR / PF 7.26 / 2,501% results are "illusory" because of **look-ahead bias**. Swing highs/lows are used before confirmation, and OB/FVG displacement checks `h[i+1:i+4]` (future bars). Verdict NO-GO.
- **`VALIDATION/EXHAUSTIVE_FILTER_ANALYSIS_FINAL.md`** (50+ filter configs):
  - All session filters lose money; London-NY overlap is worst (PF 0.56).
  - Timeframe (M1-M30) and risk % make no difference.
  - Only a Hurst gate reaches breakeven: best PF 1.05, +0.4%, on 36 trades.
- **`VALIDATION/TRENDFOLLOW_2024_ANALYSIS_20251224.md`** (M3/M5 trend-follow, 5 windows of 2024): Jan -0.05%, Mar -4.02%, Jun -3.84%, Sep -2.15%, Nov +9.98%.
- **`models/wfa_results.json`:** ML direction model, 17 folds, IS and OOS accuracy about 0.46-0.58, i.e. a coin flip.
- **`04_REPORTS/DECISIONS/2025-12-27_DEEP_AUDIT_REPORT.md`:** "NOT READY FOR LIVE TRADING". It lists critical bugs in the OB, FVG, sweep and structure detectors.

## Lessons the author recorded (useful)
1. Plain indicator systems on M5 gold (MA cross, RSI reversion, Donchian, ADX trend) all lose after realistic spread. Their verdict: "the problem is the fundamental entry/exit logic", not the filters.
2. **SMC/ICT detectors are a look-ahead trap.** Swings, order blocks and FVG "displacement" are confirmed only by later bars. Every spectacular result in the repo traced back to this. A swing confirmed with an N-bar lag (they use 5) is mandatory.
3. Short or cherry-picked windows mislead. Dec-2024 alone gave PF 1.8; the full year gave -26%. 2024 trend months inflate trend-following results.
4. Trend-following intraday on gold is regime-dependent: only strongly trending months (Nov 2024) paid. The author's proposed fix is a Hurst > 0.55 gate. Their own grid only lifts PF to about 1.0, so treat the Hurst rescue as a data-mined, unproven fix.
5. Session filters (including the popular London/NY overlap) did not create an edge. ML direction classifiers were at coin-flip level, and footprint/order-flow filters degraded walk-forward efficiency.
6. Market survey: MyFXBook/marketplace gold EAs with >1000% gains "usually indicate hidden martingale". Red flags are recovery modes, lot multipliers, post-2018-only backtests, >80% win rate and Sharpe > 3.

## Core rules of the public EA (not cleanly rebuildable)
- **Timeframes:** entry M15, regime/trend H1, confirmation M5 (MTF off by default).
- **Entry score:** a 9-factor 0-100 confluence score in `Signal/CConfluenceScorer.mqh`, with weights structure 15, regime 15, sweep 12, AMD 10, OB 10, FVG 8, premium/discount zone 5, MTF 12, footprint 13. Weights are re-weighted by session, and there is a "bandit-lite" gate.
- **Trade filter:** execute when score >= 60, minimum R:R 1.5, max spread 40 points, news filter on, Asian session off, Friday close at 14 GMT.
- **Regime:** Hurst 0.55 / 0.45 bands plus Shannon entropy, window 100.
- **Exits:** partial TPs, 40% at 1.5R, 30% at 2.5R, trail the rest. Risk 0.5% per trade, daily loss cap 4.5%, total 9%.
- **Recovery entries** are ON by default: a re-entry at 0.5x size after a -0.5% loss, up to 2 per day. That is mild averaging.

The proprietary parameters are not public, the detectors are self-declared buggy, and the logic is far too discretionary or complex to reproduce faithfully.

## Red flags
- **Third-party commercial EA committed.** `DOCS/06_REFERENCE/MQL5/Bots thirds/RTX_BARBAR_V31_Trial December.mq5` and its `.set` include an unlock credential (`InpPassword=sanchitchopra`) and settings with martingale on (`InpMartingaleLotMultiplier=1.1`, `InpMartingaleMaxOrders=1000`). The TWS Trade Pilot settings are committed too.
- **Contradictory reports.** "GO" reports with Sharpe 268 sit alongside NO-GO reports; the documentation is AI-generated and of uneven reliability.
- **Restrictive use terms.** `TRADING_RESTRICTIONS.md` forbids live, prop, broker-connected paper and commercial use; backtesting in a sandbox is allowed. There is no LICENSE file despite the reference to one.
- **Solicitation.** Telegram and GitHub Sponsors, though explicitly "not signals".
- **Network calls.** The WebRequests go only to a localhost Python bridge (`127.0.0.1:8000`: fundamentals, COT, news, memory). There are no external endpoints or API keys.

## Verdict: SKIP the strategy, KEEP the lessons
There is nothing concrete with positive out-of-sample evidence. The author's own honest tests show indicator families losing on M5 gold and the SMC confluence engine at PF about 0.9-1.0 once look-ahead is removed. The value of this repo is its negative results and the look-ahead warning for SMC detectors. Use those as screening rules for every other repo.
