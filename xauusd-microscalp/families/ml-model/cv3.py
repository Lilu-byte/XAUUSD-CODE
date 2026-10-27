"""Stage 2b (TRAIN only): DIRECT P&L target. For each M1 bar, the harness-exact P&L ($, FAIR fill, base spread)
of a long and of a short opened at that close with bracket (tp, sl, timeout). Two LightGBM regressors predict them;
trade the side with the larger prediction when it clears a threshold. 3-fold expanding walk-forward as cv2.
usage: python3 cv3.py"""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from feat import *
from mods import *
from mlib import *
from bracket import summ
from numba import njit


@njit(cache=True)
def bracket_pnl(o, h, l, c, spr, tod, day, tp, sl, timeout, END):
    """Per-bar P&L of one long / one short opened at close i (same exit rules as mlib._sim, FAIR fill)."""
    n = len(c); L = np.full(n, np.nan); S = np.full(n, np.nan)
    for i in range(n - 1):
        for s in (1, -1):
            e = c[i] + spr[i] if s == 1 else c[i]
            for j in range(i + 1, n):
                a = spr[j]; stale = (j - i >= timeout) or (tod[j] >= END) or (j == n - 1)
                if day[j] != day[i]:
                    px = o[j] if s == 1 else o[j] + a; pnl = (px - e) * s; break
                if s == 1:
                    tpp = e + tp; slp = e - sl
                    if o[j] <= slp or o[j] >= tpp: pnl = o[j] - e; break
                    ht = h[j] >= tpp; hs = l[j] <= slp
                    if ht and hs:
                        q = (o[j] - slp) / (tpp - slp); pnl = q * tpp + (1 - q) * slp - e; break
                    if ht: pnl = tp; break
                    if hs: pnl = -sl; break
                    if stale: pnl = c[j] - e; break
                else:
                    tpp = e - tp; slp = e + sl; ao = o[j] + a
                    if ao >= slp or ao <= tpp: pnl = e - ao; break
                    ht = l[j] + a <= tpp; hs = h[j] + a >= slp
                    if ht and hs:
                        q = (slp - ao) / (slp - tpp); pnl = e - (q * tpp + (1 - q) * slp); break
                    if ht: pnl = tp; break
                    if hs: pnl = -sl; break
                    if stale: pnl = e - (c[j] + a); break
            if s == 1: L[i] = pnl
            else: S[i] = pnl
    return L, S


if __name__ == '__main__':
    OUT = '/mnt/project-files/xauusd-microscalp/families/ml-model/'
    H = Harness(); m1 = H.m1; F = build(m1); T = m1.index
    ok = tradeable(m1) & (np.arange(len(m1)) > 150)
    B = [pd.Timestamp(x) for x in ('2026-07-20', '2026-08-03', '2026-08-17', '2026-09-01')]
    OOS = ok & (T >= B[0]) & (T < B[3])
    spr_imp = cost(m1).values      # imputed base spread for labels (zero-spread gap in early July)
    FSETS = {'all': list(GROUPS), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'], 'candle+forming': ['candle', 'forming']}
    BRK = [(1.0, 3.0, 10), (1.0, 5.0, 10), (1.0, 1.0, 5), (0.5, 1.0, 5)]
    rows = []; t0 = time.time()
    for tp, sl, to in BRK:
        Lp, Sp = bracket_pnl(H.o, H.h, H.l, H.c, spr_imp, H.tod, H.day, tp, sl, to, END_TOD)
        print(f'bracket {tp}/{sl}/{to}: mean long {np.nanmean(Lp[ok]):.3f} short {np.nanmean(Sp[ok]):.3f}', flush=True)
        for fs, groups in FSETS.items():
            cl = cols(F, groups)
            pL = np.full(len(m1), np.nan); pS = np.full(len(m1), np.nan)
            for fi in range(3):
                tr = ok & (T < B[fi]) & ~np.isnan(Lp) & ~np.isnan(Sp)
                va = ok & (T >= B[fi]) & (T < B[fi + 1])
                for y, P in ((Lp, pL), (Sp, pS)):
                    m = lgb.LGBMRegressor(objective='huber', alpha=1.0, **LGB).fit(F.loc[tr, cl], y[tr])
                    P[va] = m.predict(F.loc[va, cl])
            idx = np.where(OOS)[0]
            best = np.maximum(pL[idx], pS[idx]); side = np.where(pL[idx] >= pS[idx], 1, -1)
            for th_kind, th in [('abs', x) for x in (0.0, 0.05, 0.1, 0.2)] + [('q', x) for x in (0.005, 0.01, 0.02, 0.05)]:
                thr = np.full(len(idx), th) if th_kind == 'abs' else \
                    pd.Series(best).shift(1).rolling(3960, min_periods=500).quantile(1 - th).values
                sig = np.zeros(len(m1), int); sig[idx] = np.where(best >= thr, side, 0)
                for mo in (1, 3, 10, 50):
                    d, t = H.run(sig, tp, sl, timeout=to, max_open=mo)
                    r = dict(tp=tp, sl=sl, to=to, fs=fs, th=f'{th_kind}{th}', mo=mo, **summ(d, t))
                    r['aug'] = summ(d, t, pd.Timestamp('2026-08-01'))['per_day']
                    r['jul'] = summ(d, t, B[0], pd.Timestamp('2026-08-01'))['per_day']
                    rows.append(r)
            print(f'  {fs} {time.time() - t0:.0f}s', flush=True)
    R = pd.DataFrame(rows); R.to_csv(OUT + 'cv3_oos.csv', index=False)
    pd.set_option('display.width', 220)
    print('configs', len(R))
    print(R.pivot_table(index=['tp', 'sl', 'to', 'fs'], columns='th', values='per_day', aggfunc='max').round(2))
    print(R.sort_values('per_day', ascending=False).head(15).round(3).to_string(index=False))
