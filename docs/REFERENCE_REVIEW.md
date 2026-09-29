# Review of the MONKE reference files

Studied: `MONKE_XAU_ULTIMATE.mq5` (indicator, 2059 lines), `MONKE_XAU_ULTIMATE_EA.mq5` (EA, 1745 lines) and the
"XAUUSD Professional Market Playbook" (docx). Nothing was copied; ideas were taken only where they hold up.

## Ideas worth taking (and what became of them)
| Idea in the reference | Verdict | Where it went |
|---|---|---|
| Block trend continuation once ~90% of the average daily range (ADR) is used | Good, cheap, de-risking | Built: `adr_block` (tested neutral within noise, removes ~9% of trades, the late-day ones) |
| Sessions follow London/New York local time, not frozen GMT integers | Correct, and the playbook is right that DST silently breaks fixed hours | Built: London-local session windows, DST-aware server clock (US/EU rules, unit-tested against real transition times) |
| Forecast cone calibrated from the model's own realised error (RMSE) instead of an assumed width | Very good | Built: cone = realised one-step RMSE x sqrt(horizon) |
| Separate bar-1 and bar-4 hit-rates | Good | Built: both shown in the panel |
| "NO MAP" when the tape is choppy or spiking; do not invent candles | Good, honest | Built: efficiency-ratio and volatility-spike test; only the range cone is drawn |
| One EA / one position per symbol; second instance must not stack trades | Good; their own notes say stacking hurt them | Built: instance lock + "never open while any position exists on this symbol" |
| Two-step fill (open, then attach stops) for brokers that reject stops on the market request | Real broker quirk | Built as a fallback only, and it closes the position if stops cannot be attached (never leaves one naked) |
| Daily halt on realised P/L only (their floating-P/L halt tripped on a $180 account) | Reasonable option | Built as `InpDailyLossRealized` (default off; the equity-based limit is stricter) |
| Halve size when D1 fights the trade | Sensible | Built: `InpD1Scale` |
| Trimmed-mean bar range that ignores crash bars | Good idea | Backlog (see IMPROVEMENTS.md) |
| Stops beyond the sweep wick and off round numbers | Agrees with my structural stop + buffer | Already covered |
| Bank 50% at 1R, trail a runner | Identical to my trade plan | Already covered |
| Expectancy in R, not win-rate | Agrees | Already the headline metric |

## Problems found in the reference (so they were not copied)
| Problem | Detail |
|---|---|
| **News filter is broken** | `int count = CalendarValueHistory(...)`: that function returns `bool`, so `count` is 0 or 1 and the loop only ever inspects the *first* event. Most red-folder releases would be missed. |
| **Two copies of the logic** | Indicator and EA each carry their own ~1500 lines of scoring. They will drift; "the indicator is the map and the EA is the hands" cannot be guaranteed. This project builds both from one engine. |
| **Unvalidated magic numbers** | Score thresholds such as `MinScore=10`, `EntryScore=12`, a "62% certainty" gate, `0.45` wick ratios. No test or trial anywhere shows they mean anything. |
| **Hardcoded GMT fix window** | `FixWindow` freezes 09:20-10:50 GMT while a comment admits it depends on BST. It also switches off most of the London open that the playbook itself calls the primary window. |
| **Claims that cannot be checked** | "Low-60s win-rate on filtered 4H+15m samples", named sources, a dated 2026 brief. No data, code or citation to verify any of it. Treat as opinion. |
| **Account-specific tuning** | Several rules exist because of one $189 demo account ("DIE 4261, hard stop ~4263"). That is anecdote, not a rule. |
| **No verification** | No causality test, no null test, no unit tests, no statement of what the numbers would be on random data. |
| **`#property strict`** | MQL4 leftover; has no effect in MQL5. |
| **Forecast state as global mutable trackers** | Hit-rate decays by ad-hoc multipliers (`*3/4`, `=15`); the statistic is not a hit-rate any more. Mine recomputes from the loaded history. |

## Net assessment
The playbook's *process* advice (direction first, stop beyond the wick, size from the stop, journal in R, no stacking, freeze around
fixes and news) is sound and mostly matches what was already built. The code adds several real engineering ideas, listed above,
and one clear bug (news loop). Neither the code nor the playbook contains evidence that its rules make money.
