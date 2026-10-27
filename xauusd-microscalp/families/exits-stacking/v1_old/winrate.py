"""Why win rate rises as TP shrinks / stop widens while profit per trade does not (TRAIN, coin-flip entries,
max_open=1, timeout 30, FAIR fills, base spread on repaired data).  Random-walk prediction for a bracket of
tp/sl with spread s (bid must move +tp+s to win, -(sl-s) to lose):  P(win) = (sl - s) / (tp + sl),
expected P&L = P*tp - (1-P)*sl = -s, break-even win rate = sl / (tp + sl)."""
from sigs import *

m1 = repaired_m1(); S = build(m1); tr = m1.index < SPLIT
H = Harness(m1[tr]); sig = S['CF'][tr]
rows = []
for tp in (0.10, 0.20, 0.30, 0.50, 1.00):
    for sl in (0.30, 0.50, 1.0, 2.0, 5.0, 10.0, 20.0):
        d, t = run_pw(H, sig, tp, sl, timeout=30)
        dr, trr = run_pw(H, sig, tp, sl, timeout=30, fill='RAND', seed=1)
        s = t.spr.mean()
        w = trr[trr.pnl > 0]; lo = trr[trr.pnl <= 0]
        rows.append(dict(tp=tp, sl=sl, win_FAIR=t.pwin.mean(), win_RAND=(trr.pnl > 0).mean(),
                         win_theory=max(sl - s, 0) / (tp + sl), win_breakeven=sl / (tp + sl),
                         avg_win=w.pnl.mean(), avg_loss=lo.pnl.mean(), per_trade=t.pnl.mean(), spread=s,
                         resid=t.pnl.mean() + s, timeout_frac=(t.kind == 3).mean(), wins_per_loss=sl / tp,
                         per_day=d.pnl.mean(), trades_day=len(t) / len(d)))
R = pd.DataFrame(rows)
R.to_csv(OUT + 'winrate_train.csv', index=False)
pd.set_option('display.width', 250)
print(R.round(3).to_string(index=False))
print('\ncorr(win_FAIR, per_trade) = %.2f ; per_trade range %.3f..%.3f ; mean spread %.3f' %
      (R.win_FAIR.corr(R.per_trade), R.per_trade.min(), R.per_trade.max(), R.spread.mean()))
