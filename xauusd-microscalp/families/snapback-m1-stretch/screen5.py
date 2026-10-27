"""Stage 5 (TRAIN only): neighbourhood of the run trigger (run length 3-5, k 3.5-5) and of RSI3/z60 thresholds,
onset, pure time exit, SL 12, max_open 1 (run) / 3 (rsi). Prints TRAIN and halves."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim, stats
E = EASim(); m = E.H.m1; f = features(m)
ok_bar = valid(m, f) & E.ok & (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29) & ~m.last_of_session.values
onset = lambda s0: np.where(np.r_[0, s0[:-1]] == s0, 0, s0)
rows = []
for ml in (3, 4, 5):
    for k in (3.5, 4, 4.5, 5):
        s = np.where(ok_bar, onset(sig_run(f, ml, k)), 0)
        for N in (2, 3, 4, 5):
            d, t = E.run(s, tp=1000, sl=12, timeout=N, max_open=1)
            a, b, c = (stats(d, t, p) for p in ('train', 'h1', 'h2'))
            rows.append(dict(sig=f'run{ml}_{k}a_on', N=N, pd=a['per_day'], h1=b['per_day'], h2=c['per_day'], tday=a['trades_day'], pt=a['per_trade']))
for th in (95, 97.5, 98.5):
    for zt in (1.5, 2, 2.5):
        s = np.where(ok_bar, both(sig_rsi(f, 3, th), sig_z(f, 60, zt)), 0)
        for N in (3, 5, 8):
            d, t = E.run(s, tp=1000, sl=12, timeout=N, max_open=3)
            a, b, c = (stats(d, t, p) for p in ('train', 'h1', 'h2'))
            rows.append(dict(sig=f'rsi3_{th}&z60_{zt}', N=N, pd=a['per_day'], h1=b['per_day'], h2=c['per_day'], tday=a['trades_day'], pt=a['per_trade']))
R = pd.DataFrame(rows)
print(len(R), 'configs scored (TRAIN)')
pd.set_option('display.width', 250)
for c in ('pd', 'pt', 'tday'):
    print(c); print(R.pivot(index='sig', columns='N', values=c).round(2).to_string())
R['minh'] = R[['h1', 'h2']].min(axis=1)
print('min-half $/day'); print(R.pivot(index='sig', columns='N', values='minh').round(2).to_string())
