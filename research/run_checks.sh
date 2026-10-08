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
# The same defaults as the EA and the indicator: cost 0.35 per trade (InpCostPrice), cost guard 20 costs,
# daily trend filter AUTO (H1 and above buy only in a daily uptrend), Lab window AUTO (H1 25,000 bars, else 10,000).
export XAU_COST=0.35
# overnight swap per oz per night charged on positions held past server midnight (typical gold CFD level;
# the EA and the indicator read the broker's real value)
export XAU_SWAPL=0.50 XAU_SWAPS=0.20
D1FILE=research/data/XAUUSD_D1.csv
[ -e "$D1FILE" ] && export XAU_D1=$D1FILE
for p in ideas meta drift forecast entries shortfc mechanisms zones sizefc enginefc supertrend; do g++ -std=c++17 -O2 -Wall -Wextra -o "$BIN/$p" research/sim/$p.cpp; done
for f in research/data/XAUUSD_*.csv; do
  [ -e "$f" ] || continue
  tf=$(basename "$f" .csv | sed 's/XAUUSD_//')
  case "$tf" in M5|M15) H=research/data/XAUUSD_H1.csv ;; H1) H=research/data/XAUUSD_H4.csv ;; H4) H=research/data/XAUUSD_D1.csv ;; *) H=auto ;; esac
  [ -e "$H" ] || H=auto
  case "$tf" in H1|H4|D1) export XAU_D1MODE=2 ;; *) export XAU_D1MODE=0 ;; esac
  case "$tf" in H1) LB=25000 ;; *) LB=10000 ;; esac
  "$BIN/harness" real "$f" "$H" 2 1 $LB > "$OUT/real_${tf}_results.txt" 2>&1 || true
  # daily/4-hour files are too short for a 10,000-bar replay window: replay with a shorter one as well
  case "$tf" in
    D1) "$BIN/harness" real "$f" auto 2 1 2500 2>&1 | sed -n '/LIVE REPLAY/,$p' >> "$OUT/real_${tf}_results.txt" || true ;;
    H4) "$BIN/harness" real "$f" "$H" 2 1 6000 2>&1 | sed -n '/LIVE REPLAY/,$p' >> "$OUT/real_${tf}_results.txt" || true ;;
  esac
  case "$tf" in D1|H4) BY=5 ;; H1) BY=2 ;; *) BY=1 ;; esac
  "$BIN/harness" realblocks "$f" $BY >> "$OUT/real_${tf}_results.txt" 2>&1 || true
  # TREND mode (the AUTO default on H1 and H4): 50% Lab target, every passing combination trades (MULTI line)
  case "$tf" in
    H1) { echo; echo "== TREND MODE (Lab target 50%, all passing combinations, buys only in a daily uptrend) =="; XAU_TARGET=50 XAU_RANDCTRL=1 "$BIN/harness" real "$f" "$H" 2 1 25000 2>&1 | sed -n '/LIVE REPLAY/,$p'; } >> "$OUT/real_${tf}_results.txt" || true ;;
    H4) { echo; echo "== TREND MODE (Lab target 50%, all passing combinations, buys only in a daily uptrend) =="; XAU_TARGET=50 XAU_RANDCTRL=1 "$BIN/harness" real "$f" "$H" 2 1 6000 2>&1 | sed -n '/LIVE REPLAY/,$p';
          echo "== TREND MODE, 10,000-bar Lab (the EA's AUTO window on H4) =="; XAU_TARGET=50 "$BIN/harness" real "$f" "$H" 2 1 10000 2>&1 | sed -n '/LIVE REPLAY/,$p'; } >> "$OUT/real_${tf}_results.txt" || true ;;
  esac
  unset XAU_D1MODE
  # research programs on the intraday files (older part vs newer part, walk-forward)
  if [ "$H" != auto ]; then
    case "$tf" in M5|M15|H1|H4)
      "$BIN/ideas" "$f" "$H" 2 1 > "$OUT/ideas_${tf}.txt" 2>&1 || true
      "$BIN/meta" "$f" "$H" 0.35 0 1 > "$OUT/meta_${tf}.txt" 2>&1 || true
      [ -e "$D1FILE" ] && "$BIN/drift" "$f" "$H" "$D1FILE" 0.35 > "$OUT/drift_${tf}.txt" 2>&1 || true
      "$BIN/forecast" "$f" "$H" 3000 > "$OUT/forecast_${tf}.txt" 2>&1 || true
      "$BIN/entries" "$f" "$H" > "$OUT/entries_${tf}.txt" 2>&1 || true
      "$BIN/shortfc" "$f" "$H" > "$OUT/shortfc_${tf}.txt" 2>&1 || true
      [ -e "$D1FILE" ] && "$BIN/mechanisms" "$f" "$H" "$D1FILE" 0.35 0.50 0.20 > "$OUT/mechanisms_${tf}.txt" 2>&1 || true
      # round 11: supply/demand zones, size forecasts, and the engine's own forecast code (new vs old)
      [ -e "$D1FILE" ] && "$BIN/zones" "$f" "$H" "$D1FILE" 0.35 > "$OUT/zones_${tf}.txt" 2>&1 || true
      [ -e "$D1FILE" ] && "$BIN/sizefc" "$f" "$H" "$D1FILE" > "$OUT/sizefc_${tf}.txt" 2>&1 || true
      [ -e "$D1FILE" ] && "$BIN/enginefc" "$f" "$H" "$D1FILE" > "$OUT/enginefc_${tf}.txt" 2>&1 || true
      # round 12: the Adaptive Supertrend indicator traded on its own (rejected; kept as a check)
      [ -e "$D1FILE" ] && "$BIN/supertrend" "$f" "$H" "$D1FILE" > "$OUT/supertrend_${tf}.txt" 2>&1 || true
    ;; esac
  fi
  # M30 is built from the M15 file (the export has no M30); its higher timeframe is H4, as in MT5
  if [ "$tf" = M15 ] && [ -e research/data/XAUUSD_H4.csv ]; then
    XAU_AGG=1800 "$BIN/harness" real "$f" research/data/XAUUSD_H4.csv 2 1 10000 > "$OUT/real_M30_results.txt" 2>&1 || true
    "$BIN/entries" "$f" research/data/XAUUSD_H4.csv 1800 > "$OUT/entries_M30.txt" 2>&1 || true
    "$BIN/shortfc" "$f" research/data/XAUUSD_H4.csv 1800 > "$OUT/shortfc_M30.txt" 2>&1 || true
  fi
  echo "  $f -> $OUT/real_${tf}_results.txt"
done

echo "[5/5] Monte Carlo"
g++ -std=c++17 -O2 -Wall -Wextra -o "$BIN/montecarlo" research/sim/montecarlo.cpp
"$BIN/montecarlo" > "$OUT/montecarlo_results.md"
echo "done -> $OUT"
rm -rf "$BIN"
