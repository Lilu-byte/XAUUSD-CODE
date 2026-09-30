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

echo "[0/5] build self-contained MT5 files and presets"
python3 research/bundle.py
python3 research/make_presets.py

echo "[1/5] MQL5 syntax check (translated to C++)"
python3 research/mock/check_mq5.py MQL5/Indicators/XAU_Oracle.mq5 MQL5/Experts/XAU_Sniper_EA.mq5 MQL5/Scripts/XAU_DataExport.mq5

echo "[2-4/5] engine harness"
g++ -std=c++17 -O2 -Wall -Wextra -o "$BIN/harness" research/sim/harness.cpp
"$BIN/harness" all | tee "$OUT/harness_results.txt" | tail -3

echo "[real] broker data in research/data (if any)"
# 0.35 = the round-trip cost the EA and the indicator assume by default (InpCostPrice)
export XAU_COST=0.35
g++ -std=c++17 -O2 -Wall -Wextra -o "$BIN/ideas" research/sim/ideas.cpp
for f in research/data/XAUUSD_*.csv; do
  [ -e "$f" ] || continue
  tf=$(basename "$f" .csv | sed 's/XAUUSD_//')
  case "$tf" in M5|M15) H=research/data/XAUUSD_H1.csv ;; H1) H=research/data/XAUUSD_H4.csv ;; H4) H=research/data/XAUUSD_D1.csv ;; *) H=auto ;; esac
  [ -e "$H" ] || H=auto
  "$BIN/harness" real "$f" "$H" 2 1 10000 > "$OUT/real_${tf}_results.txt" 2>&1 || true
  # daily/4-hour files are too short for a 10,000-bar replay window: replay with a shorter one as well
  case "$tf" in
    D1) "$BIN/harness" real "$f" auto 2 1 2500 2>&1 | sed -n '/LIVE REPLAY/,$p' >> "$OUT/real_${tf}_results.txt" || true ;;
    H4) "$BIN/harness" real "$f" "$H" 2 1 6000 2>&1 | sed -n '/LIVE REPLAY/,$p' >> "$OUT/real_${tf}_results.txt" || true ;;
  esac
  case "$tf" in D1|H4) BY=5 ;; H1) BY=2 ;; *) BY=1 ;; esac
  "$BIN/harness" realblocks "$f" $BY >> "$OUT/real_${tf}_results.txt" 2>&1 || true
  # idea screen: discovery (older 60%) vs holdout (newest 40%); intraday files with a higher-timeframe file only
  case "$tf" in M5|M15|H1|H4) [ "$H" != auto ] && "$BIN/ideas" "$f" "$H" 2 1 > "$OUT/ideas_${tf}.txt" 2>&1 || true ;; esac
  echo "  $f -> $OUT/real_${tf}_results.txt"
done

echo "[5/5] Monte Carlo"
g++ -std=c++17 -O2 -Wall -Wextra -o "$BIN/montecarlo" research/sim/montecarlo.cpp
"$BIN/montecarlo" > "$OUT/montecarlo_results.md"
echo "done -> $OUT"
rm -rf "$BIN"
