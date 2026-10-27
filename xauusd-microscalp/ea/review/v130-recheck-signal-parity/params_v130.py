"""Re-run, FIXED v1.30: signal parity under non-default inputs, and the entry filter (SpreadVeto / SpreadTooWide with
the pt*0.001 tolerance) under other spread % and take-profit values. Run: NUMBA_CACHE_DIR=<scratch> python3 -I -B params_v130.py"""
import sys, contextlib, io
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea/review/v130-recheck-signal-parity')
import numpy as np, pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import compare_v130 as K          # runs the default comparison silently (see compare_v130.out), exposes its arrays
P = K.P; V = K.V; m = K.m; N = K.N; MODS = K.MODS; AE = K.AE; AI = K.AI

GIDX = {'engulf': [4, 5], 'star': [10, 11], 'three': [12, 13], 'hammer': [0, 1], 'invhammer': [2, 3],
        'harami': [6, 7], 'piercing': [8, 9], 'doji': [14, 15]}


def sig_case(groups, body_pb, body_cp, mode, fades, sess):
    cp = np.zeros(16, np.bool_)
    for g in groups: cp[GIDX[g]] = True
    raw, take, d5 = K.port(mode, K.SPR_raw, K.tr, AE, fades=fades, cpOn=cp, pbMinBody=body_pb, cpMinBody=body_cp,
                           sessFrom=sess[0], sessTo=sess[1])
    raw_i, _, _ = K.port(mode, K.SPR_raw, K.tr_ind, AI, window=10 ** 9, need_full=False, ind=True, fades=fades, cpOn=cp,
                         pbMinBody=body_pb, cpMinBody=body_cp, sessFrom=sess[0], sessTo=sess[1])
    S = V.signals(K.H, K.tr, dict(V.D, groups=tuple(groups), body_pb=body_pb, body_cp=body_cp, m5=mode, fades=fades, sess=sess))
    hrs = (K.H.tod >= AE['firstTod']) & (K.H.tod <= AE['lastTod'])      # EA zeroes sig[] outside 01:05-22:29; replica does it in _sim_next
    S = {k: np.where(hrs, v, 0) for k, v in S.items()}
    cnt = {k: int((np.asarray(S[k])[1500:] != 0).sum()) for k in MODS}
    bad = {k: int((np.asarray(S[k])[1500:] != raw[1500:, j]).sum()) for j, k in enumerate(MODS)}
    bad_i = {k: int((np.asarray(S[k])[1500:] != raw_i[1500:, j]).sum()) for j, k in enumerate(MODS)}
    return cnt, bad, bad_i


print('== signal parity, non-default inputs (replica signal count; mismatching bars vs EA; vs indicator) ==')
cases = [(V.CP_DEFAULT, 0.0, 0.0, 'off', False, (900, 1140)), (V.CP_DEFAULT, 0.5, 0.5, 'off', False, (900, 1140)),
         (V.CP_DEFAULT, 1.2, 0.8, 'off', False, (900, 1140)), (tuple(GIDX), 0.0, 0.0, 'off', False, (900, 1140)),
         (tuple(GIDX), 0.8, 0.5, 'ema', True, (900, 1140)), (('hammer', 'doji'), 0.8, 0.0, 'candle', True, (900, 1140)),
         (V.CP_DEFAULT, 0.8, 0.5, 'off', False, (1320, 180)), (tuple(GIDX), 0.3, 0.3, 'ema', False, (0, 1440))]
for c in cases:
    cnt, bad, bad_i = sig_case(*c)
    print(f'  groups={",".join(c[0])} body_pb={c[1]} body_cp={c[2]} m5={c[3]} fades={c[4]} sess={c[5]}: signals {cnt}  EA mism {bad}  ind mism {bad_i}')

print('\n== entries under other spread limits (bars 1500..end): mismatching bars, replica vs EA (replica spread series), '
      'replica vs EA (recorded), of which recorded 0, EA vs indicator ==')
rows = []
for tp in (0.20, 0.25, 0.30, 0.60):
    for pct in (0, 40, 50, 52, 60, 100):
        p = dict(V.D, tp=tp, sl=max(0.60, tp + 0.05), spread_pct=pct)
        S, F = K.replica('off', p=p)
        tpa = np.full(4, tp)
        _, take_med, _ = K.port('off', K.SPR_med, K.tr, AE, pctTP=float(pct), tpArr=tpa)
        _, take, _ = K.port('off', K.SPR_raw, K.tr, AE, pctTP=float(pct), tpArr=tpa)
        _, take_i, _ = K.port('off', K.SPR_raw, K.tr_ind, AI, window=10 ** 9, need_full=False, ind=True, pctTP=float(pct), tpArr=tpa)
        r = dict(tp=tp, pct=pct, limit=round(min(0.5, pct / 100 * tp) if pct > 0 else 0.5, 4))
        for j, k in enumerate(MODS):
            a = F[k]; d_med = a != take_med[:, j]; d_rec = a != take[:, j]; d_ind = take[:, j] != take_i[:, j]
            r[f'{k}_n'] = int((a[1500:] != 0).sum())
            r[f'{k}_med'] = int(d_med[1500:].sum()); r[f'{k}_rec'] = int(d_rec[1500:].sum())
            r[f'{k}_rec0'] = int((d_rec & (K.nrec == 0))[1500:].sum()); r[f'{k}_ind'] = int(d_ind[1500:].sum())
        rows.append(r)
D = pd.DataFrame(rows)
print(D.to_string(index=False))
print('any replica-vs-EA mismatch NOT on a recorded-0 bar:',
      int(sum((D[f'{k}_rec'] - D[f'{k}_rec0']).sum() for k in MODS)), '| any on the replica spread series:',
      int(sum(D[f'{k}_med'].sum() for k in MODS)), '| any EA-vs-indicator:', int(sum(D[f'{k}_ind'].sum() for k in MODS)))

# ---- the tolerance itself, live quotes: share of n-point quotes the EA (SpreadVeto) and the indicator reject ----
lo, hi = int(m.low.min() * 100), int(m.high.max() * 100)
bids = np.arange(lo, hi) / 100.0
for pts in (11, 12, 13, 14):
    asks = (np.arange(lo, hi) + pts) / 100.0; spr = asks - bids
    rej_pct = spr > 50 / 100.0 * 0.25 + 0.01 * 0.001
    rej_pts = np.floor(spr / 0.01 + 0.5) > 50
    print(f'live EA, {pts}-point quotes at {lo/100:.2f}..{hi/100:.2f}: % limit rejects {rej_pct.mean():.3f}, MathRound points = {np.unique(np.floor(spr / 0.01 + 0.5)).tolist()}')
print('indicator, n * _Point > 0.125 + _Point*0.001 for n = 12, 13:', 12 * 0.01 > 0.125 + 0.01 * 0.001, 13 * 0.01 > 0.125 + 0.01 * 0.001)
for pct, tp in ((52, 0.25), (40, 0.25), (60, 0.25), (50, 0.20), (50, 0.30)):
    lim = pct / 100.0 * tp
    ok = [n for n in range(0, 60) if not (n * 0.01 > lim + 0.01 * 0.001)]
    lo_q = [n for n in range(0, 60) if not ((np.arange(lo, hi) + n) / 100.0 - bids > lim + 0.01 * 0.001).any()]
    print(f'  pct {pct} tp {tp}: limit {lim:.4f}; largest passing n: indicator {max(ok)}, live EA (every price) {max(lo_q)}, replica {max(n for n in range(60) if n * 0.01 <= lim + 1e-9)}')
