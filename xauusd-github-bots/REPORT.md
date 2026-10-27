# GitHub XAUUSD bots: what they claim, what they actually do

16 Oct 2026, corrected 17 Oct 2026 (see "Correction" at the end). I found 24 public gold bot repos on GitHub, read the code of all of them as text, and rebuilt every one with testable logic in our own backtest, on David's MT5 data. Nothing was downloaded beyond source text, and nothing was run or compiled from the repos. Per-repo notes are in `specs/`; code is in `code/` (`gbt.py` engine, `bots.py` and `custom.py` rebuilds, `run_all.py`). Raw tables: `results_all.csv`, `results_by_year_all.csv`, `trades_all.csv`.

## Bottom line

- **No GitHub bot beats the pair you already have.** GoldAllAgree + GoldAsiaBreak made **$4.68 a day** on May 2025 to Oct 2026. The best GitHub bot on the same window made $2.63 a day, and it lost money every year from 2018 to 2023.
- **The high win rates are fake or worthless.** Every bot claiming 68-81% wins either has no code behind the number, counts "wins" that lose money, or wins tiny amounts and then loses a lot at once. The highest real win rate (99.5%, a martingale grid) would have wiped out a $3,000 account in February 2023.
- **What makes money on gold is the same thing we found before: being long while it trends.** The only rebuilds that ended positive are slow H1 trend followers, and all their profit is in 2024-2026.
- So I did **not** build a new "perfect bot". Building one from these parts would only add more trend exposure to what GoldAllAgree already does. See "If you still want a third EA" below.

## Results (one 0.01 lot, spread $0.30 + $0.10 slippage, swap on overnight trades, stop assumed first when stop and target are in the same bar)

"Common window" is May 2025 to Oct 2026, the same window as the pair's $4.68 a day. "Beats random" is how often the bot beat the same entries with coin-flip directions (40 runs).

| Bot (repo) | TF, data from | Author's claim | Our win rate | $/day, full data | $/day, common window | Beats random | Verdict |
|---|---|---|---|---|---|---|---|
| Maxi0-912 breakout + RSI | H1, 2016 | PF 1.22, 38% win | 33% | +0.26 | +2.63 | 80% | Best on the common window; lost money 2018-2023 |
| zero-was-here Donchian 120/60 | H1, 2016 | Says itself: no proven edge | 25% | +0.45 | +2.22 | 82% | Honest benchmark, same story |
| maker-tung TrendFollow (long only) | H1, 2016 | 25.8% win, PF 1.17 | 21% | +0.26 | +1.38 | 90% | Lost 2018-2021 |
| AhadRasheed PDH/PDL break, as coded | M5, 2025 | 40% win, PF 1.34 | 28% | +0.88 | +0.88 | n/a | Bug: gets stuck, no trades in 2026; fixed version -5.84/day |
| ilahuerta pullback window, ATR cap scaled | M5, 2025 | 55% win, PF 1.64 | 46% | +0.10 | +0.10 | 70% | Faithful version barely trades (-0.08) |
| GoldReversionGuard z-score | M5, 2025 | none | 33% | -0.04 | -0.04 | 32% | 6 trades a year; without its ADX filter 64% win, -0.02/day |
| n30 TickRobust z-score | M1, Jun 2026 | none | 100% (1 trade) | +0.05 | n/a | n/a | 1 trade in 76 days; without ADX 64% win, -0.60/day |
| FvgGold (fair value gaps) | M15, 2022 | 45% win, +48.7% in 6 months | 17% | -0.01 | 0.00 | n/a | Bug: stale order blocks it after 2022; fixed version -0.39/day |
| Sandyyy123 "75%" scalper | M5, 2025 | 77.3% win, PF 2.31 | 38% | +0.08 | +0.08 | 95% | About break-even (2025 -0.36, 2026 +0.45); claimed table can't come from its code |
| Bongo BB reversion | M15, 2022 | none (EURUSD notebook) | 55% | -0.19 | -0.35 | 20% | Not built for gold |
| GOLD_ORB opening range | H1, 2016 | screenshots only | 27% | -0.60 | -0.75 | 60% | Loses most years |
| Rithick574 EMA 21/55 + ADX | M15, 2022 | none | 34% | -0.66 | -0.65 | 5% | Worse than random |
| blackXAU prev-day-high retest | M5, 2025 | screenshots only | 70% | -0.74 | -0.74 | 18% | High win rate, small wins, bigger losses |
| ikeawesom PDH/PDL sweep | M15, 2022 | ~70% win | 39% (76% by its own "win" rule) | -1.05 | -1.32 | n/a | Its "wins" are not profits |
| BAKOME "ICT" gold scalper | M5, 2025 | 68.7% win, PF 1.82 | 52% | -2.71 | -2.71 | 42% | ICT code never used; doesn't compile as committed |
| coler07 martingale grid | M15, 2022 | none | 99.5% | +72.92 on paper | n/a | n/a | **Wipes out $3,000 on 3 Feb 2023** (one basket -$8,580) |

Buy and hold (0.01 lot, before swap) for comparison: $2.23 a day from Jul 2022, $2.55 a day on the common window.

The three H1 trend bots by year ($/day):

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Maxi0-912 breakout | +0.70 | 0.00 | -0.28 | -0.52 | -0.49 | -0.44 | -0.73 | -0.09 | +0.23 | +1.22 | +4.46 |
| Donchian 120/60 | +0.54 | +0.09 | -0.29 | -0.09 | +0.37 | +0.08 | -0.43 | +0.25 | +0.39 | +2.15 | +2.33 |
| maker-tung | -0.41 | +0.13 | -0.69 | -0.25 | -0.72 | -0.87 | +0.19 | +0.70 | +1.42 | +3.37 | -0.62 |

## Traps and red flags found

- **Results that can't be real:** Sandyyy123 (77.3% table; its data source only serves 60 days of 5-minute bars, and the numbers contradict each other), FvgGold (+$4,874 on 0.01 lot in 64 trades is impossible; the most is about $430), BAKOME (claims 1,800 lines and ICT logic; 612 lines, and the only signal is price vs the H4 200 EMA), ilahuerta (metrics document contradicts itself, no costs).
- **Closed-source adverts:** Leotaby "Gold Sniper" (81.7% win) has no code, only a link to buy it on MQL5 Market. RobertN1D is an advert for an EA-generator site; its "AI" sends prices to ChatGPT and can't be backtested.
- **Leaked secrets:** Maxi0-912 has a hard-coded MT5 demo login, passwords and a Telegram bot token. francomascareloai committed someone else's paid EA with its unlock password and martingale switched on. Bongo's notebook has an MT5 login number.
- **Compiled file:** yulz008 GOLD_ORB ships a .ex5 next to the source. I didn't touch it; if you ever try that repo, compile the .mq5 yourself and never run the .ex5.
- **Machine-learning repos:** andywarui's "74% win, PF 4.6" comes from scoring that pays the full target whenever the predicted class matches, with future higher-timeframe bars leaking in. Its only real MT5 test lost 76%. zero-was-here and francomascareloai both report, honestly, that nothing they tried had a proven edge after costs.

## If you still want a third EA

The only bot worth considering is the Maxi0-912 H1 breakout (close beyond the last 40 H1 highs/lows, with the 200 EMA trend, RSI 75/25, stop 2 ATR, target 2x the stop). Added to the pair on May 2025 to Oct 2026 it lifts the total from $4.68 to $7.31 a day, but the worst drawdown doubles from $285 to $599 and 8 of 18 months lose. It's more of the same trend bet (correlation 0.31 with the pair), and it lost money every year from 2018 to 2023. I don't recommend it. A follow-up study of four ways to ride the trend is in `capitalize/CAPITALIZE.md`.

## How the rebuilds were done

- Each bot's default inputs, entry and exit rules came from its code, not its README (see `specs/`). Fixed 0.01 lot instead of risk-% sizing, so dollar daily-loss limits apply but %-limits don't.
- Bugs that stop a bot trading were fixed so the idea gets tested (BAKOME's daily counter, GOLD_ORB's drawdown flag, the martingale's broken moving average); bugs that change results are tested both ways (AhadRasheed's stuck state, FvgGold's stale order).
- Approximations: bots that act on every tick are run once per bar; bots that hold several positions are run with one; target re-aiming on the z-score bots is done at bar closes. SmartMoney.MQ5 (M1 only, with a trailing-stop bug that closes every winner at about +1R), dns2jtm (a DeMarker averaging grid, same failure as the martingale), Shivkeerth (its own saved output loses $221k) and JoelPasapera (the script doesn't run) were not rebuilt.
- Data: H1 Jul 2016 to Oct 2026, M15 Jul 2022 on, M5 May 2025 on, M1 Jun 2026 on (David's MT5 export, server time GMT+3). The authors tuned on their own periods, which mostly overlap 2022-2026, so the 2016-2021 H1 years are the cleanest unseen test.

## Correction (17 Oct 2026)

The follow-up study found a flaw in the shared engine (`code/gbt.py`): after a stop or target was hit inside a bar, it could open a new trade at that same bar's open, which comes earlier in time than the stop. That is impossible live. It is fixed, and every row above was re-run. Main changes: Maxi0-912 went from +$0.38 to +$0.26 a day (common window $3.18 to $2.63), and adding it to the pair from $7.86 to $7.31 a day. BAKOME went from -$9.43 to -$2.71 a day (it re-entered constantly), and Sandyyy123 from -$0.21 to +$0.08. No verdict changed. The custom-loop bots (ikeawesom, FvgGold, martingale) did not use that code and are unchanged.
