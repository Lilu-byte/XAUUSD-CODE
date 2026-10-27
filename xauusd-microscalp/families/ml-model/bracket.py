"""Stage 3 (TRAIN only): turn walk-forward OOS scores (Jul20-Aug31) of candidate models into M1 signals and
run the harness over a TP/SL/timeout/max_open grid. FAIR fills, base spread.
usage: python3 bracket.py 'k|fs|kind|cx|q' ['k|fs|kind|cx|q' ...]"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mods import roll_thr, signal
from mlib import *

OUT = '/mnt/project-files/xauusd-microscalp/families/ml-model/'
LO, HI = pd.Timestamp('2026-07-20'), pd.Timestamp('2026-09-01')


def summ(days, trades, lo=LO, hi=HI):
    d = days[(days.index >= lo) & (days.index < hi)]; t = trades[(trades.entry >= lo) & (trades.entry < hi)]
    p = d.pnl; eq = p.cumsum()
    return dict(per_day=p.mean(), trades_day=len(t) / len(d), win=(t.pnl > 0).mean(), per_trade=t.pnl.mean(),
                days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(), worst_day=p.min(), max_dd=(eq - eq.cummax()).min())


def oos_signal(n_m1, cfg, src='m1'):
    k, fs, kind, cx, q = cfg.split('|')
    z = np.load(OUT + f'tmp_scores_k{k}.npz')
    s = z[f'{k}|{fs}|{kind}|{cx}']; idx = z['idx']
    sig = np.zeros(n_m1, int); sig[idx] = signal(s, roll_thr(s, float(q)))
    return sig, int(k)


if __name__ == '__main__':
    H = Harness(); rows = []
    for cfg in sys.argv[1:]:
        sig, k = oos_signal(len(H.m1), cfg)
        for tp in (0.1, 0.2, 0.3, 0.5, 0.75, 1.0):
            for sl in (0.5, 1, 2, 3, 5):
                for to in sorted({k, 2 * k, 10}):
                    for mo in (1, 3, 10, 50):
                        days, tr = H.run(sig, tp, sl, timeout=to, max_open=mo)
                        rows.append(dict(cfg=cfg, tp=tp, sl=sl, to=to, mo=mo, **summ(days, tr),
                                         aug=summ(days, tr, pd.Timestamp('2026-08-01'))['per_day']))
    R = pd.DataFrame(rows); pd.set_option('display.width', 220)
    R.to_csv(OUT + 'bracket_oos.csv', mode='a', index=False, header=not __import__('os').path.exists(OUT + 'bracket_oos.csv'))
    print('configs', len(R))
    for cfg, g in R.groupby('cfg'):
        print('\n', cfg, ' best 8 by OOS per_day (Jul20-Aug31):')
        print(g.sort_values('per_day', ascending=False).head(8).round(3).to_string(index=False))
        print(' median per_day over grid', round(g.per_day.median(), 3), ' share of grid > 0:', round((g.per_day > 0).mean(), 3))
