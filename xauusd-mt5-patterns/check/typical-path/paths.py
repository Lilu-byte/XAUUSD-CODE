import numpy as np, pandas as pd, json, sys
KINDS = ["double_top","double_bottom","triple_top","triple_bottom","head_shoulders","inv_head_shoulders","asc_triangle","desc_triangle","sym_triangle","rising_wedge","falling_wedge","rectangle","broadening","channel_up","channel_down","bull_flag","bear_flag","bull_pennant","bear_pennant","cup_handle","inv_cup_handle","rounding_bottom","rounding_top"]
GROUP = [0]*6 + [1,1,1,2,2,1,1,2,2,3,3,3,3,4,4,4,4]
FILES = {'D1':'/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv','H4':'/mnt/project-files/xauusd-price-action/data/XAUUSD_H4.csv',
         'H1':'/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv','M15':'/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv',
         'M5':'/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv'}
K = 16; STEPS = np.arange(K + 1); HL = 2.0   # path over 0..2 pattern lengths, 17 points
rng = np.random.default_rng(5)
rows = []
for tf, f in FILES.items():
    df = pd.read_csv(f); c = df.close.values; h = df.high.values; l = df.low.values; n = len(c)
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    a = np.zeros(n); a[0] = tr[0]
    for i in range(1, n): a[i] = a[i-1] + (tr[i] - a[i-1]) / 14
    t = pd.to_datetime(df.time, format='%Y.%m.%d %H:%M')
    for line in open(f'pj/{tf}.txt'):
        kd, s, e, brk, conf, dr, entry, stop, target = line.split(); kd, s, e, brk, conf, dr = map(int, (kd, s, e, brk, conf, dr))
        entry, stop, target = float(entry), float(stop), float(target)
        L = e - s; D = abs(target - entry)
        if D <= 0 or L < 4: continue
        idx = conf + np.floor(STEPS * HL * L / K + 0.5).astype(int)
        if idx[-1] >= n: continue
        y = dr * (c[idx] - c[conf]) / D
        # baseline: random bars, same direction, distance scaled by ATR there
        base = []
        for _ in range(20):
            j = int(rng.integers(300, n - int(HL * L) - 2)); bi = j + (idx - conf)
            base.append(dr * (c[bi] - c[j]) / (D * a[j] / a[conf]))
        rows.append(dict(tf=tf, kind=kd, grp=GROUP[kd], date=t[conf], L=L, y=y, base=np.array(base), tgt_frac=D))
print('patterns with a full path:', len(rows))
def table(sub):
    Y = np.array([r['y'] for r in sub]); B = np.concatenate([r['base'] for r in sub])
    return np.percentile(Y, [25, 50, 75], axis=0), np.percentile(B, [25, 50, 75], axis=0), len(sub)
split = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else '2024-01-01')
tr_ = [r for r in rows if r['date'] < split]; te = [r for r in rows if r['date'] >= split]
print('train', len(tr_), 'test', len(te), 'split', split.date())
# out-of-sample check, pooled by kind (falls back to its group when the kind has < 40 train cases)
cov = []; err_p = []; err_b = []; err_0 = []; up_p = []; up_b = []; sign_ok = []
for r in te:
    sub = [q for q in tr_ if q['kind'] == r['kind']]
    if len(sub) < 40: sub = [q for q in tr_ if q['grp'] == r['grp']]
    (q25, q50, q75), (b25, b50, b75), m = table(sub)
    y = r['y'][1:]
    cov.append(np.mean((y >= q25[1:]) & (y <= q75[1:])))
    err_p.append(np.mean(abs(y - q50[1:]))); err_b.append(np.mean(abs(y - b50[1:]))); err_0.append(np.mean(abs(y)))
    up_p.append(r['y'][-1] > 0); up_b.append(np.mean(r['base'][:, -1] > 0))
    sign_ok.append(np.sign(q50[-1]) == np.sign(r['y'][-1]))
print(f"test: inside the 25-75% band {np.mean(cov):.1%} (50% = well calibrated)")
print(f"test: error vs pattern median {np.mean(err_p):.3f}, vs random-entry median {np.mean(err_b):.3f}, vs flat {np.mean(err_0):.3f} (in target distances)")
print(f"test: moved the pattern's way after 2 lengths {np.mean(up_p):.1%}, random entries same way {np.mean(up_b):.1%}")
print(f"test: median's direction right {np.mean(sign_ok):.1%}")
# full-data table per kind
out = {}
print(f"{'kind':20s} {'n':>4s}  med@1L  med@2L  q25@2L q75@2L | rand med@2L  wayUp%  randUp%")
for k in range(23):
    sub = [q for q in rows if q['kind'] == k]; pooled = len(sub) < 40
    if pooled: sub2 = [q for q in rows if q['grp'] == GROUP[k]]
    else: sub2 = sub
    (q25, q50, q75), (b25, b50, b75), m = table(sub2)
    way = np.mean([q['y'][-1] > 0 for q in sub2]); bway = np.mean([np.mean(q['base'][:, -1] > 0) for q in sub2])
    out[KINDS[k]] = dict(n=len(sub), pooled=pooled, npool=m, q25=q25.round(3).tolist(), q50=q50.round(3).tolist(), q75=q75.round(3).tolist(),
                         b50=b50.round(3).tolist(), way=round(way, 3), bway=round(bway, 3))
    print(f"{KINDS[k]:20s} {len(sub):4d}{'*' if pooled else ' '} {q50[8]:6.2f}  {q50[16]:6.2f}  {q25[16]:6.2f} {q75[16]:6.2f} | {b50[16]:6.2f}      {way:5.1%}  {bway:5.1%}")
Y = np.array([r['y'] for r in rows]); B = np.concatenate([r['base'] for r in rows])
print('ALL median path', np.percentile(Y, 50, axis=0)[::4].round(2), 'random', np.percentile(B, 50, axis=0)[::4].round(2))
json.dump(out, open('paths.json', 'w'))
