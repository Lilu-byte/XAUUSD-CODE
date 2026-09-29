# MONKE XAU LITE (v18.10)

Paired MetaTrader 5 files for gold (any symbol containing XAU or GOLD):

- `MONKE_XAU_LITE.mq5` - indicator (eyes). Any gold chart, any timeframe.
- `MONKE_XAU_LITE_EA.mq5` - Expert Advisor (hands). ONE chart only. Magic `880025`, lock `ML_LOCK_880025`.

The "shared gates" block is byte-identical in both files. A new gate goes in both, or the box lies.

Install: remove old MONKE indicators/EAs -> compile both files -> indicator on any gold chart -> EA on one chart -> AutoTrading on.

Rule of thumb: only with H4, only after a closed candle, one ticket, sit until Bank or Leave.
This is a map plus gates, not a prediction. No win rate is promised.
