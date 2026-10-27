"""Stage 4 (TRAIN only): candidate checks before choosing picks: random directions on the same bars (20 seeds),
always-long/short on the same bars, fill and cost variants, 1-bar latency, the share of the edge that comes
from bars where the 3-bar spike fade also fires, and unions (more trades without lower $/trade?)."""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim, stats, random_like

E = EASim(); m = E.H.m1; f = features(m)
ok_bar = valid(m, f) & E.ok & (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29) & ~m.last_of_session.values
onset = lambda s0: np.where(np.r_[0, s0[:-1]] == s0, 0, s0)
run44 = onset(sig_run(f, 4, 4)); z602 = sig_z(f, 60, 2); spike = sig_spike3(f)
rz = both(sig_rsi(f, 3, 97.5), z602)
r6 = f.r3.values; mr6 = onset(np.where(np.abs(r6) > 6, -sg(r6), 0))
C = {  # name: (signal, N, sl, tp, max_open, cooldown)
    'RUN44_on N3 SL12 mo1': (run44, 3, 12, 1000, 1, 0),
    'RUN44_z60_on N3 SL12 mo1': (onset(both(sig_run(f, 4, 4), z602)), 3, 12, 1000, 1, 0),
    'RSI3z60 N5 SL12 mo1': (rz, 5, 12, 1000, 1, 0),
    'RSI3z60 N5 SL12 mo3': (rz, 5, 12, 1000, 3, 0),
    'RSI3z60_on N5 SL12 mo1': (onset(rz), 5, 12, 1000, 1, 0),
    'RSI3z60 not-spike N5 SL12 mo3': (np.where(spike != 0, 0, rz), 5, 12, 1000, 3, 0),
    'RSI3z60 & spike N5 SL12 mo3': (np.where(spike != 0, rz, 0), 5, 12, 1000, 3, 0),
    'spike & RUN44 N3 SL12 mo1': (np.where(spike != 0, run44, 0), 3, 12, 1000, 1, 0),
    'spike not-RUN44(any bar) N3 SL12 mo1': (np.where(sig_run(f, 4, 4) != 0, 0, onset(spike)), 3, 12, 1000, 1, 0),
    'MR6_on N3 SL12 mo1 (ref)': (mr6, 3, 12, 1000, 1, 0),
    'MR6_on N5 SL12 mo1 (ref)': (mr6, 5, 12, 1000, 1, 0),
    'RUN44_on|MR6_on N3 SL12 mo1': (union(run44, mr6), 3, 12, 1000, 1, 0),
    'RUN44_on|MR6_on N3 SL12 mo3': (union(run44, mr6), 3, 12, 1000, 3, 0),
    'RUN44_on|RSI3z60 N3 SL12 mo3': (union(run44, rz), 3, 12, 1000, 3, 0),
    'RUN44_on|RSI3z60 N5 SL12 mo3': (union(run44, rz), 5, 12, 1000, 3, 0),
    'RUN44_on|RSI3z60_on N3 SL12 mo3': (union(run44, onset(rz)), 3, 12, 1000, 3, 0),
}
pd.set_option('display.width', 250)
rows = []; ncfg = 0
for name, (s, N, sl, tp, mo, cd) in C.items():
    s = np.where(ok_bar, s, 0)
    kw = dict(tp=tp, sl=sl, timeout=N, max_open=mo, cooldown=cd)
    d, t = E.run(s, **kw); st = stats(d, t, 'train'); h1 = stats(d, t, 'h1'); h2 = stats(d, t, 'h2'); ncfg += 1
    r = dict(name=name, pd=st['per_day'], h1=h1['per_day'], h2=h2['per_day'], tday=st['trades_day'], pt=st['per_trade'],
             win=st['win'], long=st['long_share'], ge5=st['days_ge5'], lose=st['losing_days'], worst=st['worst_day'],
             wtr=st['worst_trade'], dd=st['max_dd'])
    rnd = [stats(*E.run(random_like(s, z), **kw), 'train')['per_day'] for z in range(20)]; ncfg += 20
    r['rnd'] = np.mean(rnd); r['rnd_sd'] = np.std(rnd)
    r['along'] = stats(*E.run(np.abs(s), **kw), 'train')['per_day']
    r['ashort'] = stats(*E.run(-np.abs(s), **kw), 'train')['per_day']
    r['ohlc'] = stats(*E.run(s, fill='OHLC', **kw), 'train')['per_day']
    r['stop'] = stats(*E.run(s, fill='STOP', **kw), 'train')['per_day']
    r['bar'] = stats(*E.run(s, spread='bar', **kw), 'train')['per_day']
    r['wide'] = stats(*E.run(s, spread='wide', **kw), 'train')['per_day']
    r['comm'] = stats(*E.run(s, extra=0.07, **kw), 'train')['per_day']
    r['lat1'] = stats(*E.run(s, latency=1, **kw), 'train')['per_day']
    ncfg += 8
    rows.append(r)
R = pd.DataFrame(rows).set_index('name')
print(f'{ncfg} simulations ({len(C)} candidate configs + baselines/variants), TRAIN only')
print(R.round(2).to_string())
