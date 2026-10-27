# zero-was-here / tradingbot ("Aurum v2")

## What it is
The repo's v1 was a PPO/Dreamer deep-RL gold bot that claimed "80-120%+ annual, Sharpe 3.5-4.5" (`legacy/README_v1.md` L162-165) with no evidence. It was rebuilt as v2, "Aurum", a Python research stack: about 200 .py files, about 1,450 tests, mkdocs documentation.

Aurum covers:
- Point-in-time Dukascopy bid/ask data.
- 15 strategies: TSMOM, EWMAC, Donchian, Kalman, z-fade, RSI2, Bollinger, vol-squeeze, ORB, macro, risk-off, seasonality, GBM, meta-label, PPO.
- A forecast combiner, vol-target sizer, risk manager and an event-driven simulator with costs.
- Walk-forward with Deflated Sharpe (DSR) and Probability of Backtest Overfitting (PBO).
- An optional Claude "LLM desk" overlay.

There is also a separate legacy grid EA, `mt5_ea/GoldHedgerPro_v4.mq5`.

## Author claims (v2)
They are unusually honest. README: "no strategy has a statistically demonstrated edge (best walk-forward DSR 0.05 vs 0.95 bar)". The v1 return claims were explicitly withdrawn as unsupported.

## Out-of-sample, after-cost evidence: YES (`docs/RESULTS.md`)
**Caveat:** run outputs (`runs/`) are git-ignored, so the tables are self-reported but documented as reproducible.

**Setup:**
- Data: XAUUSD H1 mid with recorded spreads, 2013-01 to 2026-09.
- Walk-forward: 3y train / 6m test, 18 folds, 24-bar embargo; OOS 2015-12 to 2024-12.
- Holdout: 2025-01 to 2026-09, evaluated once.
- Costs: real spread (min $0.10), $0.02 + 2% of bar range slippage, financing at Fed funds + 2.5%.
- Sizing: 10% vol target, 2x max leverage.

**Walk-forward OOS 2016-2024, net Sharpe (default config):**
- Combined: -0.26 [CI -0.95, 0.38]
- tsmom: 0.01
- ema_cross: 0.11
- donchian: -0.16
- kalman: 0.01
- vol_squeeze: 0.09
- zscore_fade: -1.51
- rsi2: -1.06
- bollinger_revert: -1.52
- orb: -1.58
- macro: -0.35
- intraday_seasonality: -0.81
- ml_gbm: 0 trades (validation AUC 0.43-0.57, failed its skill gate every fold)
- meta_label: -0.28
- Buy & hold: 0.48 (6.8% CAGR, -31% DD)

**Overfitting stats:** PBO 0.41 (default) and 0.90 (trend_core).

**Holdout 2025-01 to 2026-09 (trend_core):**
- Combined: Sharpe 1.34 [CI -0.08, 2.78], CAGR 9.5%, DD -8.4%
- tsmom: 1.43
- kalman: 1.50
- Buy & hold: 0.94 (24.6% CAGR)

**Pass/fail:**
- Protocol verdict: FAIL (walk-forward DSR 0.007, CI lower bound < 0).
- `rl_ppo` was never evaluated under the protocol (`docs/ml-and-rl.md` L12).
- No OOS evidence exists for the deep-RL bot the repo is known for.

## Key lessons recorded (useful for our project)
1. "Hourly mean reversion and opening-range breakouts lose reliably after costs". Their CIs lie entirely below zero, and flipping the sign doesn't help.
2. Trend following on H1 is regime-dependent: flat 2016-24, strong in the 2025-26 trend.
3. "Costs decide everything". tsmom made +$22.9k gross on $100k over 2016-24 but -$0.7k net.
4. Buy-and-hold gold beat every active book on raw return.
5. Suggested next steps: daily-bar TSMOM with monthly horizons, and a long-biased vol-targeted gold allocation with a trend overlay.

## Core rules (concrete, rebuildable; H1, forecast at bar close, fill next open)
- **tsmom:** z_h = ln(C_t/C_{t-h}) / (sigma_t * sqrt(h)) for h in (120, 480, 1440) bars. sigma = EWMA vol, half-life 240 bars. Forecast = mean(z x 0.6267) x FDM 1.253, clipped to [-1, 1].
- **ema_cross:** (EMA32 - EMA128 of ln C) / (sigma x sqrt(14.404)) x 0.6267, clipped.
- **donchian:**
  - Long on close > highest high of the prior 120 bars; short symmetric.
  - Exit on close < lowest low of the prior 60 bars, or on a fixed stop of 2.5 x ATR(48) from the entry close.
  - Forecast while in a position = ±0.8.
- **kalman_trend:** local-linear-trend slope t-stat, lookback 240, level_noise 1.0, obs_noise 0.1.
- **Position sizing:** forecast x 10% annual vol target, max leverage 2x, drawdown de-risking, rebalance band.

All parameters are in `docs/strategies.md`; code is in `aurum/strategies/`.

## Red flags
- **No committed secrets.** Configs read ANTHROPIC_API_KEY / MT5_PASSWORD from the environment. Only fake test keys appear (`tests/test_config.py`: "sk-ant-secret-value").
- **Legacy grid EA.** `mt5_ea/GoldHedgerPro_v4.mq5` (copyright "PCG", link peopleconnectglobal.com) is a grid/martingale hedger with `InpLotMultiplier=1.5`. The README itself warns: "effectively unbounded tail risk". Avoid it.
- **v1 audit, self-reported** (README "What changed from v1"):
  - Higher-timeframe and macro features leaked up to 55 min of future data.
  - The scaler was fitted on the full sample.
  - Reward shaping was compounded into reported equity.
  - The backtester fed random noise to a mock agent.
  - Crisis validation was hard-coded to pass.
  Treat anything in `legacy/` as worthless.
- **Results not independently verified.** Artifacts are git-ignored, and the 2025-26 holdout is declared "already used".

## Verdict: REBUILD (as a benchmark, not as an edge)
This is the most methodologically sound repo surveyed. Its value is twofold:
- It gives cost-model assumptions and a negative-results map to skip: H1 mean reversion, ORB and ML direction classifiers.
- It defines simple trend baselines (TSMOM / EWMAC 32-128 / Donchian 120-60 with a 2.5 ATR stop, vol-targeted) that any candidate strategy must beat after costs.

Do not expect alpha: their own OOS Sharpe is about 0 for 2016-24. Skip the PPO/Dreamer components and the grid EA.
