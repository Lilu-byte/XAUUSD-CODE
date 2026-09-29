#!/usr/bin/env bash
# One-command verification of everything that can be verified without MetaTrader.
#   1. syntax/type-check the .mq5 sources by translating them to C++ (mock API)
#   2. unit tests for the trade simulator, sizing, news fallback
#   3. causality (no look-ahead) test
#   4. synthetic worlds: no-edge control, trending, mean-reverting, walk-forward gating
#   5. Monte Carlo risk arithmetic
# Results are written to research/results/.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=research/results
BIN=$(mktemp -d)
mkdir -p "$OUT"

echo "[0/5] build self-contained MT5 files"
python3 research/bundle.py

echo "[1/5] MQL5 syntax check (translated to C++)"
python3 research/mock/check_mq5.py MQL5/Indicators/XAU_Oracle.mq5 MQL5/Experts/XAU_Sniper_EA.mq5

echo "[2-4/5] engine harness"
g++ -std=c++17 -O2 -Wall -Wextra -o "$BIN/harness" research/sim/harness.cpp
"$BIN/harness" all | tee "$OUT/harness_results.txt" | tail -3

echo "[5/5] Monte Carlo"
g++ -std=c++17 -O2 -Wall -Wextra -o "$BIN/montecarlo" research/sim/montecarlo.cpp
"$BIN/montecarlo" > "$OUT/montecarlo_results.md"
echo "done -> $OUT"
rm -rf "$BIN"
