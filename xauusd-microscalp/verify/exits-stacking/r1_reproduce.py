"""Step 1: reproduce the claim with my own signal + grid code; cross-check against mlib Harness.run; hand-check baskets."""
from common import *

m1, H, g = load_m1_harness()
SPLIT = mlib.SPLIT
mr = mr_signal(m1)
tr = m1.index < SPLIT; te = ~tr
ndtr = len(np.unique(m1.index[tr].normalize())); ndte = len(np.unique(m1.index[te].normalize()))
print(f'MR signals/day TRAIN {(mr[tr] != 0).sum() / ndtr:.1f} TEST {(mr[te] != 0).sum() / ndte:.1f}; long share TEST {(mr[te] == 1).mean() / max((mr[te] != 0).mean(), 1e-9):.2f}')

# --- cross-check: maxlev=1 grid == Harness.run bracket TP 0.30, no SL, no timeout
d1, b1, _, _ = g.run(mr, maxlev=1)
dh, th = H.run(mr, tp=0.30, sl=1e6, timeout=10 ** 9, max_open=1, fill='FAIR', spread='base')
print('maxlev=1 grid vs Harness.run: n', len(b1), len(th), ' total', round(b1.pnl.sum(), 3), round(th.pnl.sum(), 3),
      ' max |day diff|', float((d1.pnl - dh.pnl).abs().max()))
same = (len(b1) == len(th)) and np.array_equal(b1.start.values, th.entry.values)
print('  same entry bars:', same)

# --- claim reproduction: 5 seeds FAIR / base
R = {'train': [], 'test': []}; RUNS = []
for seed in range(5):
    out = g.run(mr, step=2.0, maxlev=50, btp=0.3, seed=seed)
    RUNS.append(out)
    R['train'].append(summ(g, *out, hi=SPLIT)); R['test'].append(summ(g, *out, lo=SPLIT))
for k in ('train', 'test'):
    df = pd.DataFrame(R[k])
    print(f'{k.upper():5s} mean of 5 seeds: per_day {df.per_day.mean():+.2f} positions/day {df.positions_day.mean():.1f} baskets/day {df.baskets_day.mean():.1f} '
          f'per_pos {df.per_position.mean():+.3f} basket_win {df.basket_win.mean():.4f} days>=5 {df.days_ge5.mean():.3f} worst_day {df.worst_day.mean():+.1f} '
          f'(min seed {df.worst_day.min():+.1f}) maxDDfloat (worst seed) {df.max_dd_float.min():+.1f} max_levels {df.max_levels.max()} forced {df.n_forced.sum()}')
    print('   per seed per_day', df.per_day.round(2).tolist())

# --- hand-check: print a few baskets with their bars (seed 0)
days, bask, eql, levh = RUNS[0]
idx = m1.index
spr = g.spr['base']
def show(row, extra=3):
    i0 = idx.get_loc(row.start); i1 = idx.get_loc(row.end)
    print(f'\n basket start {row.start} dir {row.dir:+d} levels {row.levels} pnl {row.pnl:+.3f} why {row.why} end {row.end}')
    sub = m1.iloc[i0 - 3:i1 + 2][['open', 'high', 'low', 'close', 'spread_usd']].copy()
    sub['base_spr'] = spr[i0 - 3:i1 + 2]; sub['sig'] = mr[i0 - 3:i1 + 2]
    print(sub.head(12).to_string())
    a240 = (m1.high - m1.low).rolling(240).mean().iloc[i0]
    print(f'  signal check: close[i]-close[i-3] = {m1.close.iloc[i0] - m1.close.iloc[i0 - 3]:+.2f}, 3*atr240 = {3 * a240:.2f}')
    if row.dir == 1:
        e = m1.close.iloc[i0] + spr[i0]; print(f'  long entry ask {e:.2f}; 1-lot target bid {e + 0.3:.2f}')
    else:
        e = m1.close.iloc[i0]; print(f'  short entry bid {e:.2f}; 1-lot target ask {e - 0.3:.2f} -> bid {e - 0.3 - spr[i0 + 1]:.2f} (spread of bar i+1)')

bt = bask[bask.start >= SPLIT]
show(bt.iloc[0]); show(bt.iloc[1])
show(bt[bt.levels == 3].iloc[0])
deep = bt.sort_values('levels').iloc[-1]
print('\n deepest TEST basket (seed 0):', deep.to_dict())

# manual replay of a 3-level basket bar by bar using the 4-vertex FAIR path is seed dependent; replay with OHLC path instead
dO, bO, _, _ = g.run(mr, path='OHLC')
r3 = bO[(bO.start >= SPLIT) & (bO.levels == 3)].iloc[0]
i0 = idx.get_loc(r3.start); i1 = idx.get_loc(r3.end)
print(f'\nOHLC-path 3-level basket: {r3.to_dict()}')
d = r3.dir; ent = [m1.close.iloc[i0] + (spr[i0] if d == 1 else 0)]
for i in range(i0 + 1, i1 + 1):
    o_, h_, l_, c_ = m1.open.iloc[i], m1.high.iloc[i], m1.low.iloc[i], m1.close.iloc[i]; a = spr[i]
    path = [o_, l_, h_, c_] if c_ > o_ else [o_, h_, l_, c_]
    print(f'  bar {idx[i]} O {o_} H {h_} L {l_} C {c_} spr {a:.3f} path {path}')
    closed = False
    for v, q in enumerate(path):
        prev = m1.close.iloc[i - 1] if v == 0 else path[v - 1]
        lo_, hi_ = min(prev, q), max(prev, q)
        # adds
        while len(ent) < 50:
            if d == 1 and q < prev and ent[-1] - 2 - a >= q - 1e-12 and (v == 0 or ent[-1] - 2 - a <= prev + 1e-12):
                px = q if v == 0 else ent[-1] - 2 - a; ent.append(px + a); print(f'     add long at ask {px + a:.2f}'); prev = px
                if v == 0: break
            elif d == -1 and q > prev and ent[-1] + 2 <= q + 1e-12:
                px = q if v == 0 else ent[-1] + 2; ent.append(px); print(f'     add short at bid {px:.2f}'); prev = px
                if v == 0: break
            else:
                break
        n = len(ent); E = sum(ent)
        tgt = (E + 0.3) / n if d == 1 else (E - 0.3) / n - a
        if d == 1 and q > prev and q >= tgt:
            px = q if v == 0 else max(tgt, prev); print(f'     TARGET long: bid {px:.3f} pnl {n * px - E:+.3f}'); closed = True; break
        if d == -1 and q < prev and q <= tgt:
            px = q if v == 0 else min(tgt, prev); print(f'     TARGET short: bid {px:.3f} pnl {E - n * (px + a):+.3f}'); closed = True; break
    if closed: break
print(f'  manual replay entries {np.round(ent, 2).tolist()} vs sim levels {r3.levels} pnl {r3.pnl:+.3f}')
