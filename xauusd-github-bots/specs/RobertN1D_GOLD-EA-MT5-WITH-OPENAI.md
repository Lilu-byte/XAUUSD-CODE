# RobertN1D / GOLD-EA-MT5-WITH-OPENAI

## What it is
A single MQL5 file, `EA-MT5-OPENAI.mq5` (about 107 KB), plus a README. The README opens with an advert: "The files in this repository were created using AlgoStrategyLab.com", a chat-to-EA code generator. The EA is mostly a chart dashboard, with an M1 XAUUSD scalper underneath. Every ~10 s it sends a text "market context" to OpenAI and reads back `BUY|SELL|WAIT|confidence|reason|summary`.

## Author claims
"Production MetaTrader 5 Expert Advisor for M1 XAUUSD scalping", "AI-guided". **There are no performance numbers at all.** The README gives only generic backtest advice (use every tick, test 3-6 months). There is no report, no equity curve and no trade list.

## Out-of-sample / after-cost evidence
None.

## Web requests / keys
- One endpoint only: `WebRequest("POST", "https://api.openai.com/v1/chat/completions", ...)` (line ~2135). It uses `Authorization: Bearer <InpOpenAIAPIKey>`.
- Key input default: `"YOUR OPENAI HERE"` (line 46). **No real key is committed.** Model default `gpt-5-mini`, temperature 0.7, max_tokens 10000.
- No other URLs and no telemetry or exfiltration endpoints in the EA code. The only external link is the AlgoStrategyLab advert in the README.
- Cost/latency: one LLM call every 10 seconds (`updateInterval = 10`, which contradicts the input `InpAIUpdateMinutes=1`).

## What the "AI signal" actually does
- `BuildMarketContext()` writes RSI, EMAs, ATR, pivots, session, daily range, etc. into a prompt. The LLM returns BUY/SELL/WAIT plus a confidence.
- If AI is "active" and returns BUY or SELL with confidence >= 0.5 (because `InpAIOverride=true` lowers the threshold from 0.7), the EA opens a 0.01-lot market order on a new M1 bar.
- **WebRequest does not work in the MT5 Strategy Tester.** Any backtest therefore runs the fallback `CallOpenAI_Simulated()`. That function sets `g_AIIsActive=false` and fakes a response: RSI<35 gives "BUY 0.85", otherwise WAIT. Because AI is then not active, trading falls through to the traditional rule below. **The AI part cannot be backtested and is non-deterministic (temp 0.7).**

## Core rules (fallback / backtestable path)
- TF: M1, evaluated once per new M1 bar. Magic 123456.
- Long only: RSI(14) <= 35 AND EMA20 > EMA50 (`InpRequireBullishMA`). Reads indicator buffer [0], i.e. the forming bar.
- Pyramiding: up to `InpMaxPositions=10` concurrent positions, and a new one can open every bar while the condition holds.
- Initial SL = ask - 2.0 x ATR(14). No TP.
- Exits (`ManageAIPositions`, every tick):
  - Close as soon as profit >= `InpMinProfitPct` = 0.05% of price (about $1.0-1.5 on gold at $2-3k), labelled "PROFIT HUNGRY".
  - Close on an opposite AI signal with conf >= 0.7.
- Trailing (`ManageTrailingStopLoss`): once profit > 0.01%, SL goes to breakeven +1 pt. It then trails at max(0.999 x peak, bid - 10 pts) and modifies on every tick.
- The spread filter is commented out ("disabled for crypto"). No session or news filter in the trading path, despite inputs `InpRequireSupport` / `InpRequireGoodSession` (declared, not used in `CheckAndExecuteTrades`).

## Red flags
- An advert or lure repo for an AI EA-generator site. The README mentions files that do not exist (`trading-off.mq5`, `trading-updated-gold-with-loss-protection.mq5`) and a hard-coded local Windows path (`C:\Users\16139\...`).
- Payoff profile: tiny fixed take-profit (~0.05%) against a 2xATR stop, with up to 10 stacked entries. That is a classic high-win-rate, negative-skew scalper whose edge, if any, is consumed by spread (gold spread is typically 0.01-0.03% per trade).
- The LLM signal is not reproducible, cannot be tested in the tester, and costs money per call.
- Uses the forming-bar indicator value, so tester results differ by modelling mode.

## Verdict: SKIP
There is no evidence and no real edge hypothesis. The only rebuildable part is "M1 RSI<=35 in EMA20>EMA50 uptrend, take +0.05%, 2xATR stop", a generic dip-buy scalper. That scalper is dominated by costs, and other specs cover it better. The "AI" is an untestable LLM call.
