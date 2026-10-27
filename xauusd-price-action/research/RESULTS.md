# How high can XAUUSD direction accuracy go? (13 Oct 2026)

Data: David's MT5 export (D1 2004+, H4 2013+, H1 2016+, M15 2022+, M5 2025+, EURUSD M15, USD economic calendar 2022+). The USDX series in the export is too thin to use (flat bars, volume 1), and the XAGUSD files are truncated in the archive.

**Rule for every number below:** walk-forward. A model is trained only on years before the test year and scored on that unseen year. Confidence cut-offs come from the training data. Each result is compared with the plain up-rate (just guessing "up"), because gold rose most years.

| Approach | Test period | Accuracy | "Always up" on the same bars |
|---|---|---|---|
| Price action rules (merged prompt), hit 1R before stop | 2019–2026 | 51% | 50% (trend-only entries) |
| Daily ML model (LightGBM, 30 price features), next day | 2012–2026 | 52.2% | 52.1% |
|   same, only its 20% most confident days | 2012–2026 | 55.8% | 54% |
| Daily ML, next 5 days / next 20 days | 2012–2026 | 53% / 53% | 54% / 53% |
| H4 ML model + daily context, next H4 candle | 2017–2026 | 51.2% | 51.4% |
|   same, next 6 H4 candles (1 day), 5% most confident | 2017–2026 | 57.4% (n=312) | 56% |
| Hour-of-day drift (learned from past years) | 2018–2026 | 51.6–52.8% | |
| EURUSD M15 move → next XAU M15 | 2022–2026 | 49% | |
| USD data surprise → gold continuation after the first 15 min (+1h / +4h) | 2022–2026 | 44–50% | |
| USD data surprise → gold direction *during* the release bar (not tradeable) | 2022–2026 | 52–60% | |

Two warning signs that there is no hidden edge to dig out:
- The most confident predictions are not more accurate. The daily model's top 2–5% most confident days scored 38–56%, worse than its average in most cases.
- Every "best" subset scores about the same as simply being long on those bars.

**Ways to show 80%+ that are not real accuracy:**
- Shrink the profit target. A 0.25R target wins 80.6%, but each trade averages about zero.
- Score the news bar after the fact.
- Tune on the same data you report.

**Honest ceiling found: about 55–57% on selected days, which is mostly gold's upward drift.**
