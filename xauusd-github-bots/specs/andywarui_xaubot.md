# andywarui / xaubot

## What it is
A sprawling ML pipeline for XAUUSD M1 on MT5 data, with about 30 status / plan / "COMPLETE" markdown files. The intended path is LightGBM (26 features) then an optional multi-TF Transformer, exported to ONNX and run by MQL5 EAs (`mt5_expert_advisor/XAUUSD_NeuralBot_*.mq5`, `MT5_XAUBOT/Experts/XAUUSD_Neural_Bot_v2.mq5`). A whole Windows `.venv` is committed, which accounts for about 4,600 of the ~4,700 files. The Transformer weights were never available ("Git LFS HTTP 502", `AB_TESTING_REPORT.md`).

## Author claims (contradictory, depending on the doc)
- **`TRAINING_RESULTS.md`:** 66.25% accuracy, "75.88% win rate, profit factor 6.29, $295K profit".
- **`python_training/models/oos_results.json`** ("REALISTIC OOS", last 12 months): 15,324 trades, WR 74.1%, PF 4.60. The "LIVE-READY" variant has WR 80.5%, PF 3.67.
- **`AB_TESTING_REPORT.md`, Model A:** +472.81%, PF 1.56, WR 43.8%, DD 16%, 381 trades. It reports test accuracy 87.8% with 88.5% HOLD classes.
- **`MODEL_PERFORMANCE_ANALYSIS.md` / `FINAL_ANALYSIS_AND_SOLUTION.md`:** the first MT5 model (trained on synthetic data) lost **-76.41%** over 3 years, with 149 trades, WR 28.9% and PF 0.82.
- **`PROJECT_STATUS.md`:** the Strategy Tester figures are *expected* ("Win Rate 63-68%, PF 1.4-1.6"). `MT5_TEST_CHECKLIST.md` has blank fields ("Win rate: _______").
- **`PYTHON_BACKTESTING_SUMMARY.md`:** the numbers ($4,250 / PF 1.52) are labelled "Example Output".
- **`python_training/backtesting/results/vigorous_backtest_summary.json`:** walk-forward, Monte Carlo and robustness all report `"status": "ERROR"`.

## Out-of-sample, after-cost evidence: NONE credible
The only real MT5 tester result in the repo is the -76% loss. Every positive number comes from a Python "backtest" that is not a price simulation. `python_training/test_oos.py` `run_backtest_oos()` works like this:
- `if signal == label: pips = TP_PIPS - 2*spread - slip`, else `-(SL_PIPS + ...)`.
- So a "correct" classification is credited the full +80-pip take profit.

The labels (`python_training/build_features_m1.py` `create_labels`, tp 80 / sl 40 "pips" = $0.80 / $0.40, 12 bars ahead) are:
- 2 = long TP hit first
- **0 ("SHORT") = long SL hit first**, i.e. price fell $0.40
- 1 = neither

A correct "SHORT" is therefore paid as if price fell $0.80 when only a $0.40 fall is implied. That is why SHORT is the majority class (51-58%) and the win rate looks like 77%.

Costs are also tiny: spread 2.5-3 "pips" = $0.025-0.03, against a real XAUUSD spread of roughly $0.10-0.35.

`wfo_results.json` reports only classification accuracy per fold (fold 1: 65%, driven by the SHORT majority class), not P&L.

## Data leakage / methodology problems
1. **Higher-TF look-ahead.** `merge_higher_tf_features` uses `pd.merge_asof(..., direction='backward')` on bar *open* time. Each M1 row is joined with the M5/M15/H1/H4/D1 bar that has *already opened but not closed*. `D1_position` = (D1 close - low) / range then contains up to ~24 h of future data. This plausibly explains much of the accuracy.
2. **Inconsistent splits.** Time-ordered 70/15/15 iloc split in the main path. Random `train_test_split(random_state=42)` in `train_synthetic_model.py`. A model trained on synthetic data was taken all the way to MT5.
3. **Non-stationary features.** Raw `ema_10/20/50` price levels are used as features (`config/features_order.json`), which breaks across price regimes.
4. **Subsampling.** `test_oos.py` keeps 1/N rows ("Sample for speed"), and overlapping 12-bar labels are counted as independent trades.
5. **Label/threshold drift.** Scripts use different horizons (15-bar return, 10-bar return, TP/SL first-touch), so the docs' numbers don't refer to one model.

## Core rules (if one insisted on rebuilding)
- **Timeframe:** M1, signal per bar.
- **Features (26):** M1 candle body, range, close position, returns over 1/5/15/60 bars, TR, ATR14, RSI14, EMA10/20/50, hour sin/cos, and for each of M5/M15/H1/H4/D1 the trend (sign of close-EMA20) and position in range.
- **Model:** LightGBM, 3-class, 500 trees, learning rate 0.05, 31 leaves, balanced classes.
- **Trade:** enter when max probability >= 0.60, with TP $0.80 / SL $0.40 (Python) or $8 / $4 (EA tests). Max 5 trades per day, plus a "hybrid validation" filter on spread/RSI/MACD/ADX/ATR.

The edge hypothesis is just "M1 classifier", with no economic rationale.

## Red flags
- No hard-coded credentials found. The `mt5.login(account, password, server)` call in `python_monitoring/monitor_live_performance.py` uses variables, not literals.
- Committed `.venv`.
- `q-dev-chat-*.md` AI-assistant transcripts.
- Many "PHASE COMPLETE" docs that contradict one another.

## Verdict: SKIP
There are no valid out-of-sample results. The headline numbers come from a scoring function that pays the full TP for any correct class plus understated costs, and the features look ahead via the higher-TF joins. The only real tester run lost 76%. Nothing here is worth rebuilding. If anything, it is a useful catalogue of ML-backtest mistakes to avoid: `merge_asof` on bar open time, accuracy-as-P&L, asymmetric labels.
