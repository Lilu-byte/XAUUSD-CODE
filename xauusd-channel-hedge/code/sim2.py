"""Channel-middle hedge, many pairs allowed. Rules as in sim.py (docstring there), plus:
a new pair opens on a middle touch only when no other pair still has BOTH legs open and fewer than maxpos pairs are open.
Floating loss: a lone buy is marked at the bar low, a lone sell at the bar high + spread, two open legs at the close."""
import numpy as np, pandas as pd
SL_L, SW_S = 0.126, 0.046

def run(x, d=1.0, mode='none', k=1.0, L=20, W=0.0, lab=None, slip=0.05, dfrac=None, maxpos=1):
    o, h, l, c = (x[k_].values for k_ in ('open', 'high', 'low', 'close'))
    sp = np.maximum(x.spread.values, 10) * 0.01
    mid, up, lo, n, lb, brk = x.mid.values, x.up.values, x.lo.values, x.n.values, x.lab.values, x.brk.values
    day = x.index.normalize().values; wd = x.index.dayofweek.values
    N = len(c); closed = 0.0; trades = []; eq = np.zeros(N); worst_eq = np.zeros(N); P = []
    for t in range(1, N):
        newday = day[t] != day[t-1]; mult = 3 if wd[t-1] == 2 else 1
        keep = []
        for p in P:
            if newday: p['pnl'] -= mult * ((SL_L if p['b'] else 0) + (SW_S if p['s'] else 0))
            if t > p['t0']:
                hit = None
                if p['bs'] is not None and p['b'] and l[t] <= p['bs']:
                    p['pnl'] += min(o[t], p['bs']) - p['be'] - slip; p['b'] = False
                if p['ss'] is not None and p['s'] and h[t] + sp[t] >= p['ss']:
                    p['pnl'] += p['se'] - max(o[t] + sp[t], p['ss']) - slip; p['s'] = False
                if p['b'] and h[t] >= p['btp']:
                    p['pnl'] += p['btp'] - p['be']; p['b'] = False; hit = 'b'
                if p['s'] and l[t] + sp[t] <= p['stp']:
                    p['pnl'] += p['se'] - p['stp']; p['s'] = False; hit = 's' if hit is None else 'both'
                if hit in ('b', 's') and not p['armed']:
                    p['armed'] = True
                    if hit == 'b' and p['s']:
                        if mode == 'close': p['pnl'] += p['se'] - (c[t] + sp[t]) - slip; p['s'] = False
                        elif mode == 'x': p['ss'] = p['btp'] + sp[t] + k * p['d']
                        elif mode == 'edge': p['ss'] = max(p['top'], p['btp']) + sp[t]
                    if hit == 's' and p['b']:
                        if mode == 'close': p['pnl'] += c[t] - p['be'] - slip; p['b'] = False
                        elif mode == 'x': p['bs'] = p['stp'] - k * p['d']
                        elif mode == 'edge': p['bs'] = min(p['bot'], p['stp'])
                elif hit == 'both': p['armed'] = True
                if p['armed'] and mode == 'brk' and brk[t] and (p['b'] or p['s']):
                    if p['b']: p['pnl'] += c[t] - p['be'] - slip; p['b'] = False
                    if p['s']: p['pnl'] += p['se'] - (c[t] + sp[t]) - slip; p['s'] = False
            if p['b'] and p['s']: fl = p['pnl'] + (c[t] - p['be']) + (p['se'] - c[t] - sp[t])
            else: fl = p['pnl'] + ((l[t] - p['be']) if p['b'] else 0) + ((p['se'] - h[t] - sp[t]) if p['s'] else 0)
            p['worst'] = min(p['worst'], fl); p['fl'] = fl
            if not p['b'] and not p['s']:
                trades.append((p['t0'], t, p['pnl'], p['worst'])); closed += p['pnl']
            else: keep.append(p)
        P = keep
        if len(P) < maxpos and not any(p['b'] and p['s'] for p in P) and n[t] >= L and (up[t] - lo[t]) >= W \
                and (lab is None or lb[t] in lab) and l[t] <= mid[t] <= h[t]:
            dd = d if dfrac is None else dfrac * (up[t] - lo[t]) / 2
            m = mid[t]; p = dict(t0=t, b=True, s=True, be=m + sp[t] + slip, se=m - slip, pnl=0.0, worst=0.0, armed=False,
                                bs=None, ss=None, top=m + up[t], bot=m + lo[t], d=dd, fl=-sp[t] - 2 * slip)
            p['btp'] = p['be'] + dd; p['stp'] = p['se'] - dd; P.append(p)
        f = sum(q['pnl'] + ((c[t] - q['be']) if q['b'] else 0) + ((q['se'] - c[t] - sp[t]) if q['s'] else 0) for q in P)
        eq[t] = closed + f; worst_eq[t] = closed + sum(q['fl'] for q in P)
    for p in P: trades.append((p['t0'], N - 1, None, p['worst']))
    tr = pd.DataFrame(trades, columns=['t0', 't1', 'pnl', 'worst'])
    days = max(1, len(np.unique(day))); done = tr.dropna()
    peak = np.maximum.accumulate(eq)
    return dict(pairs=len(tr), win=round((done.pnl > 0).mean() * 100, 1) if len(done) else 0,
                total=round(eq[-1], 1), per_day=round(eq[-1] / days, 2),
                per_pair=round(eq[-1] / max(1, len(tr)), 3), max_dd=round((peak - worst_eq).max(), 1),
                worst_pair=round(tr.worst.min(), 1) if len(tr) else 0,
                longest_days=round((tr.t1 - tr.t0).max() / (1440 / x.attrs.get('mins', 1)), 1) if len(tr) else 0,
                open_end=len(P), max_open=None), tr, eq
