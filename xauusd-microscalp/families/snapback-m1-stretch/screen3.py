"""Stage 3 (TRAIN only): trade grid on the shortlisted triggers, plus the 3-bar spike fade (reference, not tuned)
and unions with it. Grid: N (2,3,4,5,8) x SL (5,8,12,25) x TP (off,2,3,4,6) x max_open (1,2,3,5) x cooldown (0,3,5).
Writes screen3_train.csv; prints TRAIN summaries only."""
import sys, time, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim, stats

E = EASim(); m = E.H.m1; f = features(m)
ok_bar = valid(m, f) & E.ok & (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29) & ~m.last_of_session.values
onset = lambda s0: np.where(np.r_[0, s0[:-1]] == s0, 0, s0)
run44 = sig_run(f, 4, 4); z602 = sig_z(f, 60, 2); spike = sig_spike3(f)
rz = both(sig_rsi(f, 3, 97.5), z602)
S = {'RUN44_on': onset(run44),
     'RUN44_z60_on': onset(both(run44, z602)),
     'RSI3z60': rz,
     'FM5_2': sig_fm5(f, 2.0),
     'SPIKE3_ref': spike,
     'RUN44_on_not_spike': np.where(spike != 0, 0, onset(run44)),
     'RUN44_on|SPIKE3': union(onset(run44), spike),
     'RSI3z60|SPIKE3': union(rz, spike)}
S = {k: np.where(ok_bar, v, 0) for k, v in S.items()}
grid = list(itertools.product((2, 3, 4, 5, 8), (5, 8, 12, 25), (1000, 2, 3, 4, 6), (1, 2, 3, 5), (0, 3, 5)))
rows = []; t0 = time.time()
for name, s in S.items():
    for N, sl, tp, mo, cd in grid:
        d, t = E.run(s, tp=tp, sl=sl, timeout=N, max_open=mo, cooldown=cd)
        r = dict(sig=name, N=N, sl=sl, tp=tp, mo=mo, cd=cd)
        for per in ('train', 'h1', 'h2'):
            st = stats(d, t, per); r[f'pd_{per}'] = st['per_day']; r[f'pt_{per}'] = st['per_trade']
            if per == 'train':
                r.update(tday=st['trades_day'], worst_day=st['worst_day'], long=st['long_share'], win=st['win'],
                         dd=st['max_dd'], ge5=st['days_ge5'], lose=st['losing_days'], wtrade=st['worst_trade'])
        rows.append(r)
R = pd.DataFrame(rows)
R.to_csv('/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch/screen3_train.csv', index=False)
print(f'{len(R)} configs scored ({time.time() - t0:.0f}s)')
pd.set_option('display.width', 250)
R['minh'] = R[['pd_h1', 'pd_h2']].min(axis=1)
cols = ['sig', 'N', 'sl', 'tp', 'mo', 'cd', 'tday', 'long', 'win', 'pd_train', 'pd_h1', 'pd_h2', 'pt_train', 'ge5', 'lose', 'worst_day', 'dd']
for name in S:
    x = R[R.sig == name]
    print(f'--- {name}: best 4 by min(half) $/day; base config (N3 SL25 TP off mo1 cd0) and grid median')
    print(x.sort_values('minh', ascending=False).head(4)[cols].round(2).to_string(index=False, header=name == list(S)[0]))
    b = x[(x.N == 3) & (x.sl == 25) & (x.tp == 1000) & (x.mo == 1) & (x.cd == 0)]
    print(b[cols].round(2).to_string(index=False, header=False))
    print(f'    grid median $/day {x.pd_train.median():+.2f}, share of grid with both halves > 0: {(x.minh > 0).mean():.2f}')
