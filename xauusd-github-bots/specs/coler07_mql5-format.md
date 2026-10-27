# coler07_mql5-format — XAUUSD_Martingale_EA.mq5 (always-in EMA-trend martingale grid)

Files read: `MQL5/Experts/XAUUSD_Martingale_EA.mq5`, `analyze_history.py`, `README.md`. ("Project created by Manus AI".)

## 1. Claims vs evidence
- No performance claims. README says parameters were "inferred" from a commercial EA's trade history (`2341644.history.csv`, "Trend AI EA mt5"): InitialLot 0.01, multiplier 2.0, GridStep 500 pts, TP 500 pts, MaxOrders 8.
- The history CSV is **not in the repo**; `analyze_history.py` reads `/home/ubuntu/upload/2341644.history.csv` (an agent sandbox path). No backtest, no saved output. Nothing verifiable.

## 2. Data / timeframe / timezone
Live MT5 EA, M15 hard-coded (`TimeFrame = PERIOD_M15`, regardless of chart). Broker server time; no session logic. No backtester in repo (you would run it in MT5 Strategy Tester).

## 3. Inputs that trade
InitialLot 0.01, LotMultiplier 2.0, GridStep 500 (points), TakeProfit 500 (**unused**), MaxOrders 8, MagicNumber 144401, FastMAPeriod 10, SlowMAPeriod 30, MAMethod EMA on close.
Point size matters: on a 2-digit gold quote 500 pts = **$5.00**; on 3-digit = $0.50.

## 4. Entry rules
- `OnTick` acts only on the **first tick of each new M15 bar** (everything below is evaluated once per bar, at bar open).
- If no EA positions: `fast = EMA10[1]`, `slow = EMA30[1]` (last closed bar). `fast > slow` → market BUY 0.01; `fast < slow` → market SELL 0.01. **No crossover needed** — the EA is always in the market in the direction of the EMA regime. (Note: `iMA` is called as if it returned a value — in MQL5 it returns a handle, so as written the "MA values" are handle integers, making the comparison effectively meaningless/constant. A faithful rebuild of the *intended* logic uses the EMA values.)
- Grid add (if 1 ≤ count < 8): `last = PriceOpen` of the last position in the terminal's enumeration (normally the most recent); `price = Ask` (buy series) / `Bid` (sell series); if `|price − last| / _Point >= 500` → open same-direction market order of `0.01 × 2^count` (0.02, 0.04 … 1.28). **Absolute distance**: it adds when price moves 500 pts *in favour* as well as against.

## 5. Exit rules
- After grid logic, same bar-open tick: sum `position.Profit()` (floating P&L, excludes swap/commission) of all EA positions of the series type; if `>= $1.00` → close every position. `target_currency_profit` is computed but never used.
- **No stop loss, no max-loss, no time exit.** At 8 orders the grid just stops adding and waits for the basket to reach +$1 (or a margin call).
- No backtest of its own → no SL/TP-same-bar, cost, or look-ahead modelling. In a rebuild, evaluate on bar open only and include spread (Ask/Bid) since profit is measured from fills.

## 6. Sizing / martingale
Geometric martingale ×2, 8 levels: total 2.55 lots (255 oz) after 7 steps. With $5 steps (2-digit), the 8th order is ~$35 from the first; average entry of the full basket sits ~$29.5 from the first entry. A further ~$X adverse move costs ≈ 2.55 × 100 × X dollars ($255 per $1). Gold routinely moves $50-100/day → expect account-ending drawdowns on trend days. Basket target is a fixed $1 regardless of size (≈ 0.4 cents per oz at full size), i.e. tiny wins, huge tail losses.

## 7. Red flags
- Martingale with no stop is the defining risk. Uses `SetMarginMode(MARGIN_FREE_MARGIN)` (not a real CTrade method in MQL5 — likely compile error; LLM-generated code).
- `iMA` handle-as-value bug (above). No network calls, no credentials. Mentions a commercial EA but no links/lures.

## 8. Reimplementation notes
```
on each new M15 bar open t (price = open[t]; ask = open+spread, bid = open):
  pos = open EA positions
  if not pos:
      f, s = EMA10(close)[t-1], EMA30(close)[t-1]
      if f>s: open BUY 0.01 at ask   elif f<s: open SELL 0.01 at bid
  else:
      n = len(pos); last = pos[-1].open_price
      px = ask if dir==BUY else bid
      if n < 8 and abs(px - last) >= 500*point: open dir lot=0.01*2**n at px
  pnl = sum(lot*100*(bid-entry) if BUY else lot*100*(entry-ask))
  if pnl >= 1.0: close all at bid/ask
```
(Optionally simulate intrabar margin-call using bar high/low.) Use `point=0.01` unless your data is 3-digit.

**What inflates win rate:** almost every basket closes at +$1, so per-basket win rate approaches 100% until one trend leg reaches level 8 and keeps going; that single loss can exceed thousands of wins. Report max basket drawdown and worst MAE, not win rate. Also note the favourable-direction add means it pyramids into winners too (then closes at +$1 immediately since the profit check runs right after).
