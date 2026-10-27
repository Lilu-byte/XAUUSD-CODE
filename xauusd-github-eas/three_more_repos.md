# Three more GitHub "EA" repos (read 2026-10-14)

## 1. Opselon/NexusTradingForexBot ("Nexus Scalp Engine", v9.0.15, last commit 12 Oct 2026)
- Not an MT5 EA. A large Python 3.11 platform (~1,750 .py files, web dashboard, Go API, installer) that runs beside MT5 on Windows and sends orders through its own bridge. Target: XAUUSD M1.
- Signal: a PyTorch neural network (TCN + attention) on 50 features, then "smart money" rules (order blocks, fair value gaps, liquidity sweeps), then a risk engine.
- Evidence of profit: none published. Its own docs/project/status.md: the newer 70-feature model was "NOT_ELIGIBLE" on out-of-sample walk-forward; the TASK-09 report says no candidate was trained or validated. No backtest or live P&L for the active 50-feature model was found in the README or status page.
- Much of the repo is written and audited by AI agent swarms (agents/, forensic_reports/), heavy on process, light on results.
- Install path includes `iex (irm .../install.ps1)` (runs a downloaded script). Defaults to PAPER mode.
- Fit: M1 scalping is what our tests found loses to spread. Not worth running for the $5/day goal.

## 2. KamranAliOfficial/forex-ea-mt5-robotic-trading (last commit Jun 2025)
- README only, no files. It lists 179 commercial EAs and indicators as compiled .ex4/.ex5 and .rar/.zip (names like "ForexCracked.com-Multi-Purpose-EA", "...by @freepremiumEAandindicators", "HAXOR VIRUS.ex4").
- These are cracked/leaked paid products. Compiled files can't be read or checked, and cracked EA bundles are a common way to spread malware. No strategy or results to evaluate.
- Fit: don't download or run anything from it.

## 3. NulvexN/Forex-Scalping-EA-MT5-MT1 (last commit Apr 2026)
- Not an EA and not connected to MT5. A Windows C# app (Form1.cs) that draws a fake chart: prices are random (`RNG.NextDouble()`), and each trade's direction and win/loss are coin flips with a 62% win chance (`isWin = RNG.NextDouble() > .38`). Its own roadmap lists "Real MT5 integration" as not done.
- It still asks for an MT5 login and password.
- The "MQL5" folder holds no MQL5: it has unrelated commented-out C#/C++ hacking utilities (LDAP domain-controller enumeration, MSSQL credential probing).
- Fake star/fork badges point at torvalds/linux; a GitHub Action commits every minute (from a rambler.ru address) to make the repo look active.
- Typical lure-repo pattern. Fit: don't build, run, or enter credentials.

## Bottom line
None of the three is a usable XAUUSD EA. Only Nexus is real software, and its own tests haven't shown an edge.
