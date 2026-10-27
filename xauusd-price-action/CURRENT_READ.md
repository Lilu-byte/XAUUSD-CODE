# XAUUSD read: as of Friday 9 Oct 2026 close (4195.20)

Source: David's MT5 export (broker time GMT+3, bid prices). The export stops at Friday's close, so Monday 12 and Tuesday 13 October are not included. Swings use the merged rules: Daily pivots 2 candles each side, H4 pivots 3 each side, structure breaks on closes only.

## Short verdict (gate format)

1. **Higher-timeframe bias:** Daily is bearish (lower highs and lower lows since the 4696.73 top on 25 Aug; the latest BOS was the 7 Oct close at 4100.98 below 4108.33). H4 is bullish: there was a CHoCH on 9 Oct when the 04:00 candle closed at 4181.70, above the 4143.36 swing high. **The timeframes conflict.**
2. **Liquidity note:** The equal lows at 4103.53/4103.67 (5 and 6 Oct) were taken on 7 Oct down to 4066.30, then reclaimed on 8 and 9 Oct. Buy-side liquidity sits just above, at 4207.33 (Friday high), 4219.27 (30 Sep) and 4226.45 (2 Oct, the Daily lower high).
3. **Setup status: NO SETUP.** H4 and Daily disagree, so requirement 1 fails; no confirming candle has formed in a direction both agree on.

## 1. Higher-timeframe bias (Daily + H4)
- **Daily structure:** LH/LL. Lower highs are 4696.73 (25 Aug), 4510.76 (3 Sep), 4399.53 (18 Sep) and 4226.45 (2 Oct). Swing lows were broken in sequence: 4282.40 on 16 Sep, 4234.94 on 28 Sep (a 166-point bear candle, 1.7x average range, closing at 7% of its range) and 4108.33 on 7 Oct. The current Daily low is 4066.30. All-time high is 5598.03 (29 Jan 2026), so price is about 25% below it.
- **H4 structure:** after the 4066.30 low, H4 made a higher low at 4105.15 (8 Oct 16:00), broke 4143.36 on a close and printed a higher high at 4207.33 (9 Oct 08:00). Locally that is HH/HL.
- **Key levels:** 4226.45 (Daily lower high; a close above it is a Daily CHoCH), 4207–4226 (buy-side liquidity cluster), 4168.29 (Friday's H4 pullback low), 4143.36 (broken H4 high), 4105.15 (H4 higher low), 4066.30 (Daily low).
- **Lean:** mixed. Daily points down, but the last two Daily candles are reclaiming the breakdown. Price sits in the upper part of the 4066–4226 swing range, close to the Daily lower high, so this is not a discount area for longs or a premium rejection for shorts yet.

## 2. Active candlestick patterns

| Pattern | TF | Location | Grade | Implies if confirmed | Invalidation |
|---|---|---|---|---|---|
| Failed breakdown / two-day bullish reversal (7 Oct low 4066.30, 9 Oct close 4195.20 at 85% of range) | Daily | Swept the 4103.5 equal lows and reclaimed the broken 4108.33 level | **C**: it runs against Daily LH/LL and sits below the 4226.45 lower high; not an engulfing by definition (8 Oct was bullish) | A Daily close above 4226.45 flips Daily to bullish (CHoCH) | A Daily close back below 4100 (the breakdown close); full failure below 4066.30 |
| Bullish CHoCH momentum candle (9 Oct 04:00, range 1.5x average, close at 90%) | H4 | Broke the 4143.36 swing high | **B as a structure event, not a setup**: it is a breakout candle, not a rejection or engulfing at a level | H4 continuation toward 4207–4226 | An H4 close below 4105.15 (the H4 higher low) |
| Upper-wick rejection (9 Oct 08:00, high 4207.33, close at 23% of range) | H4 | Just under the 4219–4226 Daily lower-high zone | **C**: against the fresh H4 CHoCH, and the next candles recovered to 4195 | Stalling below the Daily lower high | An H4 close above 4207.33 |

## 3. Candle quality and momentum
- **Rejection:** the Daily lows at 4066.30 were rejected; 7 Oct closed at 34% of range after trading 37 points below the equal lows, and 8 Oct was a small inside-style candle (0.46x average range), which is compression before Friday's expansion.
- **Close strength:** Friday Daily closed at 85% of its range (0.91x average), a strong close. On H4, the 08:00 wick at 4207 was the only clear selling, and the 16:00 and 20:00 candles absorbed the 4168 dip and closed near their highs into the weekend.
- **Range:** Daily ranges contracted from 166 points (28 Sep) to 40–100 points. No fresh expansion in either direction since 7 Oct.
- **Mixed signals:** yes. The Daily trend is still down, while the last two Daily candles and the H4 structure point up.

## 4. Scenarios
- **Primary: test of 4207–4226 buy-side liquidity.** The strong Friday close and the H4 HH/HL make a probe of the Friday high and the Daily lower high the nearer move. What happens there decides the bias:
  - *Confirms bullish:* a Daily close above 4226.45 (Daily CHoCH). H4 and Daily then agree, and the trade becomes a pullback long at 4168–4180 or 4143.
  - *Invalidates:* rejection in 4207–4226 followed by an H4 close below 4168.29.
- **Alternative: lower high holds, Daily downtrend resumes.** An H4 bearish engulfing or upper-wick rejection in 4207–4226, then H4 closes below 4168.29 and 4143.36, would put H4 back in line with Daily and allow a short setup.
  - *Confirms:* an H4 close below 4105.15 (a bearish H4 CHoCH).
  - *Invalidates:* a Daily close above 4226.45.

## 5. Timing and confirmation rules
- **Long version:** first a Daily close above 4226.45. Then an H4 bullish engulfing (or rejection) on a pullback into 4143–4180, with its low near a prior swing. Within the next 4 H1 candles, an H1 close above that H4 candle's high comes before invalidation. Invalidation is the pattern low.
- **Short version:** an H4 bearish engulfing or rejection that closes in its lower third inside 4207–4226. A sweep above 4207.33 or 4226.45 that closes back below would make it grade A. Within the next 4 H1 candles, an H1 close below that candle's low is required. Invalidation is the pattern high.
- **Minimum before calling anything valid:** H4 and Daily agree. Until then the answer stays NO SETUP.

**Caution from the backtest:** on 2019–2026 data these setups hit +1R before invalidation about as often as a coin flip (see [BACKTEST.md](BACKTEST.md)). Treat this read as a map of levels, not a forecast.
