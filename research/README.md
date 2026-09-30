# research/

Everything here exists to check the MQL5 code without MetaTrader. **None of it is a market-data backtest.**

| Path | What it is |
|---|---|
| `bundle.py` | Inlines `src/` into the self-contained MT5 files (indicator, EA, export script). |
| `make_presets.py` | Writes `MQL5/Presets/*.set` from the EA's own input list. |
| `run_checks.sh` | One command: MQL5 syntax check, unit tests, causality and window tests, synthetic worlds, Monte Carlo. Writes `results/`. |
| `mock/mql5_mock.h` | Small C++ stand-in for the MT5 API surface the project uses. |
| `mock/check_mq5.py` | Translates `.mq5` to C++ and runs `g++ -fsyntax-only`. Catches typos and type errors, not MetaEditor-specific rules. |
| `sim/harness.cpp` | Runs the *real* engine (`XAU_Core.mqh`). Modes: `units`, `causal`, `calib` (fills vs minute truth), `lab` (all 32 combinations per world), `labrules`, `replay` (daily Lab as the EA trades), `replayrules`, `replayconfirm`, and `real BASE.csv HTF.csv` for exported broker data. |
| `sim/montecarlo.cpp` | Risk arithmetic for "double the account in a month". |
| `results/` | Last saved outputs (referenced from the docs). |

Requirements: `g++` (C++17) and `python3`. Nothing else.
