"""Fill-free move after each pre-specified fade signal, per year and per side, vs the average spread.
move_c{h}: close[i+h] - close[i] in the signal direction (as mlib.edge); move_o{h}: close[i+h] - open[i+1]
(what a next-bar-open entry can capture). Only signals the EA could take (entry hours, next bar contiguous,
spread filter) and whose h bars stay inside the session. Writes edge_history.csv."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
from hlib import *
H_ = (1, 2, 3, 4, 6)
rows = []
for tf in ('M5', 'M15'):
    d = load_tf(tf); f = features(d, tf); sc = Scorer(d, tf, f.ar)
    c = d.close.values; o = d.open.values; spr = d.spread_usd.values + 0.05
    tod = d.tod.values; sess = d.index.normalize().values
    yr = d.index.year.values
    n_ = len(d)
    okh = (tod >= 65) & (tod <= 22 * 60 + 29) & ~d.last_of_session.values & sc.entry_ok
    # same-session check for horizon h (no break inside i+1..i+h)
    bm = BARMIN[tf]
    t = d.index.values.astype('datetime64[m]').astype(np.int64)
    for n in (1, 2):
        for k in (2.5, 3, 4):
            for g in (0, 1):
                s = signal(d, f, n, k, g)
                for per_name, per in [('year', yr)]:
                    for y in np.unique(per):
                        for side in ('all', 'long', 'short'):
                            m = (s != 0) & okh & (per == y)
                            if side == 'long': m &= s > 0
                            if side == 'short': m &= s < 0
                            idx = np.where(m)[0]
                            r = dict(tf=tf, n=n, k=k, gate=g, year=int(y), side=side, signals=len(idx),
                                     days=len(np.unique(sess[per == y])))
                            if len(idx) == 0: rows.append(r); continue
                            r['avg_spread'] = spr[np.minimum(idx + 1, n_ - 1)].mean()
                            r['ar'] = f.ar.values[idx].mean()
                            for h in H_:
                                j = idx + h
                                v = j < n_
                                j = np.where(v, j, n_ - 1)
                                v &= (t[j] - t[idx] == h * bm)          # bars i..i+h contiguous, same session
                                ii = idx[v]; jj = j[v]; sg = s[ii]
                                mc = (c[jj] - c[ii]) * sg; mo = (c[jj] - o[ii + 1]) * sg
                                r[f'move_c{h}'] = mc.mean(); r[f'move_o{h}'] = mo.mean()
                                r[f'hit_o{h}'] = (mo > 0).mean(); r[f'nmove_o{h}'] = (mo / f.ar.values[ii]).mean()
                            rows.append(r)
E = pd.DataFrame(rows)
# unconditional drift per bar per year (always-long move from next open to close i+h), for reference
E.to_csv('/mnt/project-files/xauusd-microscalp/families/snapback-history/edge_history.csv', index=False)
pd.set_option('display.width', 250)
for tf in ('M5', 'M15'):
    x = E[(E.tf == tf) & (E.side == 'all')]
    print(f'\n{tf}: fill-free move from next-bar open to close of bar i+h, minus avg base spread; [signals/yr]  (h = 1/2/3/6)')
    for (n, k, g), gx in x.groupby(['n', 'k', 'gate']):
        parts = []
        for _, r in gx.iterrows():
            if r.signals < 5: parts.append(f"{r.year}: n/a[{r.signals}]"); continue
            parts.append(f"{r.year}: " + '/'.join(f"{r[f'move_o{h}'] - r.avg_spread:+.2f}" for h in (1, 2, 3, 6)) + f" [{r.signals}]")
        print(f'  n{n} k{k} gate{g}  ' + ' | '.join(parts))
