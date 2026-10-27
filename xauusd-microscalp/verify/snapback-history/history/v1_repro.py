"""Step 1: reproduce pick C on M15 independently; hand-coded trade loop cross-check; baselines; truncation test."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history')
from vlib import *

d = load('M15'); f, w = features(d, 15)
s = signal(d, f, 2, 4.0, 1)
# 1) compare with the colleague's signal
hf = hlib.features(d, 'M15'); hs = hlib.signal(d, hf, 2, 4.0, 1)
print('signal bars mine', int((s != 0).sum()), 'colleague', int((hs != 0).sum()), 'mismatches', int((s != hs).sum()))
E = Eng(d, 15)
days, T = E.run(s, 2, 25, 3)
P = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None), 'TEST_CLEAN': ('2025-01-01', '2026-06-26'),
     'M1ERA': ('2026-06-26', None), 'ALL': (None, None)}
for p, (lo, hi) in P.items():
    print(f'{p:10s}', fmt(stats(days, T, lo, hi)))

# 2) hand-coded loop (plain python, no numba), same rules
o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
spr = d.spread_usd.values + 0.05; tod = d.tod.values; last = d.last_of_session.values
dayk = d.index.normalize().values
ok = E.entry_ok
openpos = []; trades = []
for i in range(len(d)):
    keep = []
    for (si, dr, e) in openpos:                      # exits on bar i (opened at signal bar si < i)
        px = None
        if dayk[i] != dayk[si]:
            px = o[i] if dr == 1 else o[i] + spr[i]
        elif dr == 1:
            if o[i] <= e - 25: px = o[i]
            elif l[i] <= e - 25: px = e - 25
        else:
            if o[i] + spr[i] >= e + 25: px = o[i] + spr[i]
            elif h[i] + spr[i] >= e + 25: px = e + 25
        if px is None and (i - si >= 2 or tod[i] >= 22 * 60 + 58 or last[i] or i == len(d) - 1):
            px = c[i] if dr == 1 else c[i] + spr[i]
        if px is None: keep.append((si, dr, e))
        else: trades.append((si, dr, (px - e) * dr))
    openpos = keep
    if s[i] != 0 and ok[i] and 65 <= tod[i] <= 22 * 60 + 29 and not last[i] and i < len(d) - 1 and len(openpos) < 3:
        dr = int(s[i]); e = o[i + 1] + spr[i + 1] if dr == 1 else o[i + 1]
        openpos.append((i, dr, e))
M = pd.DataFrame(trades, columns=['ei', 'dir', 'pnl']).sort_values('ei').reset_index(drop=True)
TT = T.sort_values('ei').reset_index(drop=True)
same = len(M) == len(TT) and (M.ei.values == TT.ei.values).all()
print('hand loop trades', len(M), 'engine', len(TT), 'same entries', same,
      'max |pnl diff|', float(np.abs(M.pnl.values - TT.pnl.values).max()) if same else 'n/a', 'total hand', round(M.pnl.sum(), 2), 'engine', round(TT.pnl.sum(), 2))

# 3) baselines on TRAIN and TEST: 200 random-direction seeds, 200 permutations of the pick's own directions
# (keeps the long/short count exactly; controls for drift), always long/short
def per(days, lo, hi):
    x = days.pnl
    if lo: x = x[x.index >= pd.Timestamp(lo)]
    if hi: x = x[x.index < pd.Timestamp(hi)]
    return x.mean()
rng = np.random.default_rng(11)
idx = np.where(s != 0)[0]
res = {p: dict(r=[], perm=[]) for p in P}
for z in range(200):
    r = np.zeros(len(s)); r[idx] = np.where(rng.random(len(idx)) < .5, 1, -1)
    dr_, _ = E.run(r, 2, 25, 3)
    q = np.zeros(len(s)); q[idx] = rng.permutation(s[idx])
    dq_, _ = E.run(q, 2, 25, 3)
    for p, (lo, hi) in P.items():
        res[p]['r'].append(per(dr_, lo, hi)); res[p]['perm'].append(per(dq_, lo, hi))
dl, _ = E.run(np.where(s != 0, 1., 0.), 2, 25, 3); dsh, _ = E.run(np.where(s != 0, -1., 0.), 2, 25, 3)
for p, (lo, hi) in P.items():
    act = per(days, lo, hi); r = np.array(res[p]['r']); q = np.array(res[p]['perm'])
    print(f'{p:10s} pick {act:+.3f}/d | random mean {r.mean():+.3f} sd {r.std():.3f} share>=pick {(r >= act).mean():.3f} | '
          f'permuted dirs mean {q.mean():+.3f} share>=pick {(q >= act).mean():.3f} | always long {per(dl, lo, hi):+.3f} short {per(dsh, lo, hi):+.3f}')

# 4) cost / fill / latency variants on TRAIN and TEST
dB, TB = E.run(s, 2, 25, 3, spread='bar'); dW, TW = E.run(s, 2, 25, 3, spread='wide')
dO, TO = E.run(s, 2, 25, 3, fill='OHLC'); dS, TS = E.run(s, 2, 25, 3, fill='STOP'); dL, TL = E.run(s, 2, 25, 3, latency=1)
dN, TN = E.run(s, 2, 25, 3, spread_filter=False)
for p, (lo, hi) in P.items():
    print(f'{p:10s} base {per(days, lo, hi):+.3f} bar {per(dB, lo, hi):+.3f} flat0.30 {per(dW, lo, hi):+.3f} '
          f'comm {stats(days, T, lo, hi, extra=COMM)["per_day"]:+.3f} OHLC {per(dO, lo, hi):+.3f} STOP {per(dS, lo, hi):+.3f} '
          f'lat1 {per(dL, lo, hi):+.3f} no-spread-filter {per(dN, lo, hi):+.3f}')
print('trades removed by the spread filter (uses bar i+1 lowest spread):', len(TN) - len(T))

# 5) truncation test on my signal: 400 random bars
bad = 0; rr = np.random.default_rng(5).integers(300, len(d) - 1, 400)
for i in rr:
    dc = d.iloc[:i + 1]; fc, _ = features(dc, 15)
    bad += int(signal(dc, fc, 2, 4.0, 1)[i] != s[i])
print('truncation test: 400 bars, mismatches', bad)
T.to_csv('/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickC_trades_M15.csv', index=False)
