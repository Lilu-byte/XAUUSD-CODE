"""Why win rate rises as TP shrinks / stop widens while profit per trade does not (TRAIN, coin-flip entries,
max_open=1, timeout 30, FAIR fills, base spread, mlib v2). Random-walk prediction for a bracket tp/sl with spread s
(the bid must rise tp + s to win and fall sl - s to lose):  P(win) = (sl - s) / (tp + sl),
expected P&L = P*tp - (1-P)*sl = -s  for EVERY bracket; break-even win rate = sl / (tp + sl)."""
from sigs2 import *

m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
sig = S['CF'][tr]
rows = []
for tp in (0.10, 0.20, 0.30, 0.50, 0.75, 1.00):
    for sl in (0.30, 0.50, 1.0, 2.0, 5.0, 10.0, 20.0):
        d, t = run_pw(H, sig, tp, sl, timeout=30)
        _, trr = run_pw(H, sig, tp, sl, timeout=30, fill='RAND', seed=1)
        s = t.spr.mean()
        w = trr[trr.pnl > 0]; lo = trr[trr.pnl <= 0]
        rows.append(dict(tp=tp, sl=sl, win=t.pwin.mean(), win_theory=max(sl - s, 0) / (tp + sl),
                         win_breakeven=sl / (tp + sl), avg_win=w.pnl.mean(), avg_loss=lo.pnl.mean(),
                         per_trade=t.pnl.mean(), spread=s, resid=t.pnl.mean() + s, timeout_frac=(t.kind == 3).mean(),
                         avg_bars=t.bars.mean(), per_day=d.pnl.mean(), trades_day=len(t) / len(d)))
R = pd.DataFrame(rows)
R.to_csv(OUT + 'winrate2_train.csv', index=False)
pd.set_option('display.width', 250)
print(R.round(3).to_string(index=False))
print('\ncorr(win, per_trade) = %.2f ; win range %.2f..%.2f ; per_trade range %+.3f..%+.3f ; mean spread %.3f' %
      (R.win.corr(R.per_trade), R.win.min(), R.win.max(), R.per_trade.min(), R.per_trade.max(), R.spread.mean()))
# long vs short and Jul vs Aug split of the resid, to show it is a property of the price path, not of direction
for tp, sl in ((0.1, 20.0), (0.3, 5.0), (1.0, 0.5), (1.0, 0.3)):
    d, t = run_pw(H, sig, tp, sl, timeout=30)
    t['res'] = t.pnl + t.spr
    j = t.entry < HALF
    print(f'tp {tp} sl {sl}: resid long {t.res[t.dir == 1].mean():+.3f} short {t.res[t.dir == -1].mean():+.3f} | Jul {t.res[j].mean():+.3f} Aug {t.res[~j].mean():+.3f}')
