"""Stage 2 (TRAIN only): shortlisted triggers x a second condition (at most two conditions), every-bar vs onset,
pure time exit N in (3, 5, 8), disaster SL $25, max_open 1. Also the overlap of each trigger with the plain
3-bar spike fade (|C-C[i-3]| > 3A or > $6). Writes screen2_train.csv; prints a TRAIN summary only."""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim, stats

E = EASim(); m = E.H.m1; f = features(m)
ok_bar = valid(m, f) & E.ok & (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29) & ~m.last_of_session.values
tr = E.train
T = {}
for ml in (4, 5):
    for k in (3, 4, 5, 6): T[f'run{ml}_{k}a'] = sig_run(f, ml, k)
T['rsi3_97.5'] = sig_rsi(f, 3, 97.5); T['rsi3_98.5'] = sig_rsi(f, 3, 98.5)
T['fm5_1.5'] = sig_fm5(f, 1.5); T['fm5_2.0'] = sig_fm5(f, 2.0)
T['z60_3.5'] = sig_z(f, 60, 3.5); T['z30_3.5'] = sig_z(f, 30, 3.5); T['z20_3'] = sig_z(f, 20, 3)
T['rexp4_q0.33'] = sig_rexp(f, 4, 0.33); T['rexp3_q0.2'] = sig_rexp(f, 3, 0.2)
vs = -sg(f.vwd.values)                     # fade direction implied by the VWAP side (above VWAP -> sell)
C2 = {'none': None,
      'vside': vs,
      'vwap2a': sig_vwap(f, 2), 'vwap4a': sig_vwap(f, 4),
      'ema2a': sig_ema(f, 2), 'ema3a': sig_ema(f, 3),
      'z60_2': sig_z(f, 60, 2), 'rsi3_95': sig_rsi(f, 3, 95), 'fm5_1.0': sig_fm5(f, 1.0)}
spike = sig_spike3(f)
rows = []; t0 = time.time(); ncfg = 0
for tn, ts in T.items():
    ts = np.where(ok_bar, ts, 0)
    ov = ((ts != 0) & (spike != 0) & tr).sum() / max(((ts != 0) & tr).sum(), 1)
    for cn, cs in C2.items():
        if cn == tn: continue
        s0 = ts if cs is None else both(ts, cs)
        for onset in (False, True):
            s = s0.copy()
            if onset: s = np.where(np.r_[0, s0[:-1]] == s0, 0, s0)       # first bar of the condition only
            for N in (3, 5, 8):
                d, t = E.run(s, tp=1000, sl=25, timeout=N, max_open=1); ncfg += 1
                r = dict(trig=tn, cond=cn, onset=onset, N=N, spike_overlap=ov,
                         sig_day=((s != 0) & tr).sum() / 47)
                for per in ('train', 'h1', 'h2'):
                    st = stats(d, t, per); r[f'pd_{per}'] = st['per_day']; r[f'pt_{per}'] = st['per_trade']
                    if per == 'train':
                        r.update(tday=st['trades_day'], worst_day=st['worst_day'], long=st['long_share'],
                                 win=st['win'], dd=st['max_dd'])
                rows.append(r)
R = pd.DataFrame(rows)
R.to_csv('/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch/screen2_train.csv', index=False)
print(f'{ncfg} configs scored ({time.time() - t0:.0f}s)')
pd.set_option('display.width', 250)
R['minh'] = R[['pd_h1', 'pd_h2']].min(axis=1)
cols = ['trig', 'cond', 'onset', 'N', 'spike_overlap', 'tday', 'long', 'win', 'pd_train', 'pd_h1', 'pd_h2', 'pt_train', 'worst_day', 'dd']
print('--- top 30 by min(half) $/day')
print(R.sort_values('minh', ascending=False).head(30)[cols].round(3).to_string(index=False))
print('--- overlap with the 3-bar spike fade, per trigger')
print(R.groupby('trig').spike_overlap.first().round(2).to_string())
