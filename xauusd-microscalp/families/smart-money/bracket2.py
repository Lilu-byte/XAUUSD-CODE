"""TRAIN bracket grid for the second-round candidates (cands.build2). Only TRAIN rows of the
results are read. Writes bracket2_train.csv.gz and prints the best robust configs per candidate."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from cands import *
from mlib import Harness, summarize

t0 = time.time()
H = Harness(); m1 = H.m1
C = build2(m1)
TP = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0)
SL = (0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0)
TO = (1, 2, 3, 5, 10, 20, 30)
MO = (1, 3, 10, 50)
JUL = pd.Timestamp('2026-08-01')
rows = []
for name, s in C.items():
    for tp, sl, to, mo in itertools.product(TP, SL, TO, MO):
        days, tr = H.run(s, tp, sl, timeout=to, max_open=mo)
        d = days[days.index < SPLIT]; t = tr[tr.entry < SPLIT]
        p = d.pnl
        rows.append(dict(cand=name, tp=tp, sl=sl, to=to, mo=mo, per_day=p.mean(), tr_day=len(t) / len(d),
                         per_trade=t.pnl.mean(), win=(t.pnl > 0).mean(), jul=p[p.index < JUL].mean(),
                         aug=p[p.index >= JUL].mean(), worst=p.min(), dd=(p.cumsum() - p.cumsum().cummax()).min()))
df = pd.DataFrame(rows)
df.to_csv('/mnt/project-files/xauusd-microscalp/families/smart-money/bracket2_train.csv.gz', index=False)
print('configs run', len(df), 'in', round(time.time() - t0), 's')


def smooth(g):
    """Average per_day over the config and its grid neighbours (tp, sl, timeout +-1 step, same max_open)."""
    key = {(r.tp, r.sl, r.to, r.mo): r.per_day for r in g.itertuples()}
    out = []
    for r in g.itertuples():
        i, j, k = TP.index(r.tp), SL.index(r.sl), TO.index(r.to)
        vals = []
        for di, dj, dk in itertools.product((-1, 0, 1), repeat=3):
            a, b, cc = i + di, j + dj, k + dk
            if 0 <= a < len(TP) and 0 <= b < len(SL) and 0 <= cc < len(TO):
                vals.append(key[(TP[a], SL[b], TO[cc], r.mo)])
        out.append(np.mean(vals))
    return pd.Series(out, index=g.index)


df['nbr'] = df.groupby('cand', group_keys=False).apply(smooth)
pd.set_option('display.width', 250)
for name, g in df.groupby('cand', sort=False):
    print(f'\n== {name}: share of configs with TRAIN per_day > 0: {(g.per_day > 0).mean():.2f}; '
          f'mean per_trade over grid {g.per_trade.mean():.3f}')
    print(g.sort_values('nbr', ascending=False).head(6).round(3).to_string(index=False))
    print('  best raw per_day:', g.sort_values('per_day', ascending=False).head(1)[['tp', 'sl', 'to', 'mo', 'per_day', 'jul', 'aug', 'nbr']].round(2).to_dict('records'))
