# How to capitalize on gold's trend

17 Oct 2026. David asked, after the GitHub bot study: "how can we capitalize on that?" (the finding that only trend-following made money on gold). I tested four ways to ride the trend on his $3,000 MT5 account with one 0.01 lot per trade, then had the two leading candidates checked independently. Code and results are in the subfolders here.

## Bottom line

- **The trend "edge" is gold's own rise, not a timing skill.** None of the four approaches beat simply holding 0.01 lot of gold out of sample. Holding made **$1.74 a day** after swap from Jan 2022 to Oct 2026; the best trend rule made $1.38, the others $0.71-1.01.
- **How to capitalize on it:** if you want gold's long-term rise, own gold directly with separate money through a low-fee, unleveraged gold ETF, sized so a 30-50% fall is bearable (gold fell 26% from 28 Jan to 24 Jun 2026). That avoids the CFD's overnight swap (about 1-2.5% a year) and margin, and it can be sized below 1 oz, which MT5's 0.01-lot minimum can't. Check the fund's fee and your tax treatment first.
- **In MT5, keep the two EAs you have.** GoldAllAgree is already a controlled trend bet (worst drawdown $285 with GoldAsiaBreak). Every third trend bot I tried adds $1.6-2.1 a day on May 2025 to Oct 2026, but only by adding the same risk again: drawdown rises from $285 to $410-1,380, and three of the four push losing months from 6 to 8-10 of 18. Several of them lost money in 2026.
- **Right now every trend rule tested is out or short.** On 9 Oct gold closed at 4,195, below its 200-day average (4,530) and below where it was 6 months earlier; GoldAllAgree has been flat since late August. Shorts lost money in every out-of-sample test.
- **The quickest real step is still getting the pair running on demo:** compile GoldAllAgree and GoldAsiaBreak with F7 and follow `/mnt/project-files/xauusd-demo-pair/SETUP.md`.

## What was tested

Each approach was chosen using only Jul 2016 to Dec 2021 (H1/H4/D1 data; D1 back to 2004 for the daily rule), then scored once on Jan 2022 to Oct 2026. About 700 variants in total. Costs: $0.30 spread, $0.10 slippage, swap $0.126 long / $0.046 short per night (triple on Wednesday), stop assumed first when stop and target share a bar.

| Approach (folder) | Final rule | 2016-21 $/day | 2022-26 $/day (hold: 1.74) | Older unseen data | Added to the pair, May 2025-Oct 2026 |
|---|---|---|---|---|---|
| Regime-gated breakout (`regime-breakout/`) | H1 close beyond the 120-bar high/low; longs only if gold is up over 6 months, shorts only if down; stop 2.5 ATR(48); exit on a 60-bar opposite break | +0.20 | +1.01 | OANDA 2006-16: +0.18 (hold +0.08) | $6.69/day, drawdown $486, 10/18 losing months |
| Let winners run (`trend-exits/`) | Long only, D1 above 200-day average, H1 close above the 120-bar high; stop 2 ATR, then a trailing stop 4 ATR below the highest high | +0.20 | +0.71 | OANDA 2007-16: -0.02 (hold +0.10) | $6.49/day, drawdown $410, 8/18 |
| Long core (`long-core/`) | D1: long while the 50-day average is above the 200-day, else flat; no stop | +0.15 | +1.38 | D1 2005-15: helped only by missing the 2013 crash | $6.80/day, drawdown $1,379 (up to $1,670 intraday), 6/18 |
| Third EA with portfolio rules (`portfolio/`) | Donchian 120/60 breakout, longs only above the D1 200-day average, shorts only below | +0.17 | +0.80 | OANDA 2007-16: +0.12 (hold +0.11) | $6.26/day, drawdown $534, 10/18 |
| For comparison: the pair alone | | | | | $4.68/day, drawdown $285, 6/18 |
| For comparison: pair + simply holding 0.01 lot | | | | | $7.07/day, drawdown $1,468 |

By year ($/day; 2016 is Aug-Dec, 2026 is to 9 Oct):

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Holding 0.01 lot | -1.84 | +0.41 | -0.26 | +0.75 | +1.27 | -0.43 | -0.20 | +0.75 | +1.99 | +6.39 | -0.80 |
| Regime-gated breakout | +0.87 | -0.02 | -0.08 | +0.14 | +0.54 | +0.11 | -0.71 | +0.27 | +1.19 | +4.20 | -0.19 |
| Let winners run | +0.18 | -0.09 | +0.05 | +0.49 | +0.60 | 0.00 | -0.58 | -0.08 | +0.48 | +2.54 | +1.27 |
| Long core | -1.24 | +0.05 | -0.21 | +0.72 | +1.27 | -0.46 | -0.55 | -0.26 | +1.99 | +6.39 | -1.30 |
| Third EA (Donchian + 200-day) | +0.99 | -0.06 | -0.02 | +0.14 | +0.49 | -0.03 | -0.89 | +0.05 | +1.19 | +4.20 | -1.00 |

## Why none of them is worth building

- **Regime-gated breakout.** The 6-month filter helps a little in every period (+$0.15 a day), but coin-flip directions on the same entry bars do as well out of sample (it beats 57% of 500 random runs). Its 5 best trades made more than its total profit; the other 119 lost $215. Shorts lost $281 out of sample, and today the filter would only allow shorts.
- **Let winners run.** The trailing stop beat a fixed target only in the training years. It was flat on 2007-2016 data, including the 2007-2011 gold bull market. Its correlation with the pair is 0.40 daily and 0.79 weekly: the same bet as GoldAllAgree.
- **Long core.** It is a lower-exposure copy of holding gold. One trade (Dec 2023 to Jun 2026) made 112% of its out-of-sample profit; 2025 made 97%. Only 18% of nearby average lengths beat holding. With the pair it can take the account down about half from its peak, and if switched on on 28 Jan 2026 it would have lost $1,353 on its own.
- **Third EA with portfolio rules.** Rules chosen on 2016-2021 did not carry over (train and test rankings uncorrelated). Capping exposure, by skipping trades while GoldAllAgree is long, removes all its profit, because it earns in exactly the months GoldAllAgree does.

## Checks

- The regime-gated breakout and the long core were each rebuilt independently from their written rules. Both reproduced trade for trade, with no look-ahead and no cost errors.
- The long core was also checked for fragility and on OANDA data (verdict: not better than holding), and for live practicality (margin is safe at 0.03 lot; the risk is drawdown, not a margin call).
- Two further checks on the regime-gated breakout (fragility and live costs) stopped early because of a usage limit. Its own study already ran the OANDA test and coin-flip comparison, and the rebuild confirmed its numbers, so the verdict does not depend on them.
- These checks found a flaw in the shared engine (a trade could reopen at the open of the bar where it had just been stopped). It is fixed, and `../REPORT.md` was corrected. It changed two training-year trades here and none of the conclusions.
- Margin: the pair plus any one of these reaches at most 0.03 lot (about 4x the account in gold). A 5% drop with all three open costs about $630.
