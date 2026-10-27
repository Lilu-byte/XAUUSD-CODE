import json, random, numpy as np, pandas as pd
from detect import load
R = json.load(open('patterns.json'))
ST = json.load(open('stats.json'))
random.seed(11)
TFMIN = {'D1': 1440, 'H4': 240, 'H1': 60, 'M15': 15, 'M5': 5}
UNIT = {'D1': 0.1, 'H4': 0.1, 'H1': 0.05, 'M15': 0.01, 'M5': 0.01}
CAP = 48
frames = {tf: load(tf) for tf in TFMIN}
# choose instances: per kind, round-robin over timeframes
chosen = []
kinds = sorted(set(r['kind'] for r in R))
for k in kinds:
    rs = [r for r in R if r['kind'] == k and 8 <= r['e'] - r['s'] <= 180 and r.get('out')]
    by = {}
    for r in rs: by.setdefault(r['tf'], []).append(r)
    for v in by.values(): random.shuffle(v)
    pick = []
    while len(pick) < CAP and any(by.values()):
        for tf in ['D1', 'H4', 'H1', 'M15', 'M5']:
            if by.get(tf) and len(pick) < CAP: pick.append(by[tf].pop())
    chosen += pick
print(len(chosen))
# intervals
iv = {}
for r in chosen:
    span = r['e'] - r['s']
    n = len(frames[r['tf']])
    a0 = max(0, r['s'] - max(80, int(4 * span)))
    a1 = min(n - 1, max(r['brk'] + max(45, int(1.2 * span)), r['out']['i0'] + min(r['out']['horizon'], 160) + 12))
    r['_a'] = (a0, a1)
    iv.setdefault(r['tf'], []).append((a0, a1))
segs = []
segmap = {}
B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
def venc(vals):
    out = []
    for v in vals:
        z = (v << 1) ^ (v >> 63) if v < 0 else v << 1
        z = (-v << 1) - 1 if v < 0 else v << 1
        while True:
            b = z & 31; z >>= 5
            if z: out.append(B64[b | 32])
            else: out.append(B64[b]); break
    return ''.join(out)
for tf, lst in iv.items():
    lst.sort(); merged = []
    for a0, a1 in lst:
        if merged and a0 <= merged[-1][1] + 5: merged[-1][1] = max(merged[-1][1], a1)
        else: merged.append([a0, a1])
    df = frames[tf]; u = UNIT[tf]
    for a0, a1 in merged:
        d = df.iloc[a0:a1 + 1]
        O = np.round(d.open.values / u).astype(np.int64); H = np.round(d.high.values / u).astype(np.int64)
        L = np.round(d.low.values / u).astype(np.int64); C = np.round(d.close.values / u).astype(np.int64)
        prevC = np.r_[O[0], C[:-1]]
        vals = np.stack([O - prevC, H - np.maximum(O, C), np.minimum(O, C) - L, C - O], 1).ravel().tolist()
        t = ((d.time - pd.Timestamp('1970-01-01')) // pd.Timedelta('1min')).values.astype(np.int64)
        dt = np.r_[0, np.diff(t) // TFMIN[tf]].astype(np.int64).tolist()
        segmap[(tf, a0, a1)] = len(segs)
        segs.append(dict(tf=tf, u=u, t0=int(t[0]), p0=int(O[0]), b=venc(vals), dt=venc([x - 1 for x in dt[1:]])))
def segof(r):
    for (tf, a0, a1), sid in segmap.items():
        if tf == r['tf'] and a0 <= r['_a'][0] and r['_a'][1] <= a1: return sid, a0
rnd = lambda x: round(float(x), 2)
items = []
for r in chosen:
    sid, base = segof(r)
    o = r['out']
    it = dict(k=r['kind'], g=sid, a=r['_a'][0] - base, z=r['_a'][1] - base, s=r['s'] - base, e=r['e'] - base, b=r['brk'] - base,
              d=r['dir'], p=[[i - base, p, lab] for i, p, lab in r['pts']], l=[[x1 - base, y1, x2 - base, y2] for x1, y1, x2, y2 in r['lines']],
              en=rnd(o['entry']), st=rnd(r['stop']), tg=rnd(r['target']), c=o['i0'] - base, R=round(o['R'], 2), hit=o['hit'], hz=o['horizon'])
    if 'curve' in r: it['cv'] = [[i - base, p] for i, p in r['curve']]
    items.append(it)
# all instances inside stored segments (for accepting other correct answers)
others = []
for r in R:
    for (tf, a0, a1), sid in segmap.items():
        if tf == r['tf'] and a0 <= r['s'] and r['e'] <= a1:
            others.append([r['kind'], sid, r['s'] - a0, r['e'] - a0]); break
json.dump(dict(segs=segs, items=items, others=others, stats=ST), open('data.json', 'w'), separators=(',', ':'))
import os; print('bytes', os.path.getsize('data.json'), 'segs', len(segs), 'items', len(items), 'others', len(others))
