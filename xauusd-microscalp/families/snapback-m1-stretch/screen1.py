"""Stage 1 (TRAIN only): every single stretch trigger, faded, pure time exit after N bars.
 (a) fill-free: mean P&L per signal of 'enter at the next bar open, exit at the close of bar i+N' (base spread),
     over ALL signals (overlapping), TRAIN and its halves;
 (b) the same as a trade under _sim_next: TP off, disaster SL $25, max_open 1, no cooldown.
Prints only TRAIN numbers. Writes screen1_train.csv."""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim, stats

E = EASim(); m = E.H.m1; f = features(m)
ok_bar = valid(m, f) & E.ok & (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29) & ~m.last_of_session.values
S = {k: np.where(ok_bar, v, 0) for k, v in singles(f).items()}
o, c = m.open.values, m.close.values; spr = E.H._spr['base']; idx = m.index.values
n = len(c); NS = (2, 3, 5, 8, 10, 15)
h1 = m.index < pd.Timestamp('2026-08-01'); tr = E.train
ndays = {k: len(np.unique(m.index[s].normalize())) for k, s in (('tr', tr), ('h1', h1), ('h2', tr & ~h1))}
rows = []; t0 = time.time()
for name, s in S.items():
    for N in NS:
        j = np.minimum(np.arange(n) + N, n - 1)
        contig = (idx[j] - idx).astype('timedelta64[m]').astype(np.int64) == N
        e1 = np.minimum(np.arange(n) + 1, n - 1)
        pl = np.where(s == 1, c[j] - o[e1] - spr[e1], o[e1] - c[j] - spr[j])
        r = dict(sig=name, N=N)
        for per, sel in (('tr', tr), ('h1', h1), ('h2', tr & ~h1)):
            mm = (s != 0) & sel & contig
            r[f'n_{per}'] = mm.sum() / ndays[per]; r[f'ff_{per}'] = pl[mm].mean() if mm.any() else np.nan
        r['long_tr'] = (s[(s != 0) & tr] == 1).mean()
        d, t = E.run(s, tp=1000, sl=25, timeout=N, max_open=1)
        for per in ('train', 'h1', 'h2'):
            st = stats(d, t, per)
            r[f'pd_{per}'] = st['per_day']; r[f'pt_{per}'] = st['per_trade']
            if per == 'train': r['tday'] = st['trades_day']; r['worst_day'] = st['worst_day']
        rows.append(r)
R = pd.DataFrame(rows)
R.to_csv('/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch/screen1_train.csv', index=False)
print(f'{len(S)} signals x {len(NS)} horizons = {len(R)} configs scored ({time.time() - t0:.0f}s)')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
# summary: best horizon per signal by TRAIN sim $/day, plus whether both halves are positive
best = R.sort_values('pd_train', ascending=False).groupby('sig').head(1).sort_values('pd_train', ascending=False)
cols = ['sig', 'N', 'n_tr', 'long_tr', 'ff_tr', 'ff_h1', 'ff_h2', 'tday', 'pd_train', 'pd_h1', 'pd_h2', 'pt_train', 'worst_day']
print(best[cols].round(3).to_string(index=False))
