# research/

Everything here exists to check the MQL5 code without MetaTrader. **None of it is a market-data backtest.**

| Path | What it is |
|---|---|
| `bundle.py` | Inlines `src/` into the two self-contained MT5 files. |
| `run_checks.sh` | One command: MQL5 syntax check, unit tests, causality and window tests, synthetic worlds, Monte Carlo. Writes `results/`. |
| `mock/mql5_mock.h` | Small C++ stand-in for the MT5 API surface the project uses. |
| `mock/check_mq5.py` | Translates `.mq5` to C++ and runs `g++ -fsyntax-only`. Catches typos and type errors, not MetaEditor-specific rules. |
| `sim/harness.cpp` | Runs the *real* engine (`XAU_Core.mqh`) on synthetic gold-like data. |
| `sim/montecarlo.cpp` | Risk arithmetic for "double the account in a month". |
| `results/` | Last saved outputs (referenced from the docs). |

Requirements: `g++` (C++17) and `python3`. Nothing else.
