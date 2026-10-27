"""Signal parity under non-default v1.30 inputs, and the entry filter with the spread limit compared in whole points.
Run: python3 -I params_v130.py"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea/review/v130-signal-parity')
import numpy as np, pandas as pd
import compare_v130 as K          # re-runs the default comparison first (prints it), then exposes its arrays
import port_v130 as P
V = K.V; m = K.m; N = K.N; MODS = K.MODS

GIDX = {'engulf': [4, 5], 'star': [10, 11], 'three': [12, 13], 'hammer': [0, 1], 'invhammer': [2, 3],
        'harami': [6, 7], 'piercing': [8, 9], 'doji': [14, 15]}


def run(groups, body, mode, fades, sess, spr=K.SPR_raw):
    cp = np.zeros(16, np.bool_)
    for g in groups: cp[GIDX[g]] = True
    raw, take, d5 = P.run_ea(K.Ts, K.Os, K.Hs, K.Ls, K.Cs, K.Vs, spr, K.tr, 1500, True,
                             2, 1.0, 0.9, body, 3.0, 0.1, 15, 19, True, cp, body,
                             {'off': 0, 'candle': 1, 'ema': 2}[mode], fades, K.T5, K.O5, K.C5, K.E5,
                             65, 1349, 1378, True, sess[0], sess[1],
                             50.0, K.tpArr, 50, 0.01, K.modOn, False)
    S = V.signals(K.H, K.tr, dict(V.D, groups=tuple(groups), body=body, m5=mode, fades=fades, sess=sess))
    hrs = (K.H.tod >= 65) & (K.H.tod <= 1349)                        # firstTod/lastTod: in the EA's sig[] zeroing, in _sim_next for the replica
    S = {k: np.where(hrs, v, 0) for k, v in S.items()}
    bad = {k: int((np.asarray(S[k])[1500:] != raw[1500:, j]).sum()) for j, k in enumerate(MODS)}
    cnt = {k: int((np.asarray(S[k])[1500:] != 0).sum()) for k in MODS}
    return cnt, bad


print('\n== signal parity, non-default inputs (count of replica signals, mismatching bars) ==')
cases = [(V.CP_DEFAULT, 0.0, 'off', False, (900, 1140)), (V.CP_DEFAULT, 0.8, 'off', False, (900, 1140)),
         (tuple(GIDX), 0.0, 'off', False, (900, 1140)), (tuple(GIDX), 0.5, 'ema', True, (900, 1140)),
         (('hammer', 'doji'), 0.0, 'candle', True, (900, 1140)), (V.CP_DEFAULT, 0.5, 'off', False, (1320, 180)),
         (tuple(GIDX), 0.3, 'ema', False, (0, 1440))]
for c in cases:
    cnt, bad = run(*c)
    print(f'  groups={",".join(c[0])} body={c[1]} m5={c[2]} fades={c[3]} sess={c[4]}: signals {cnt}  mismatches {bad}')

# ---- entry filter with the limit compared in whole points (proposed fix) vs the replica ----
S, F, raw, take, take_med, d5 = K.ALL['off']
nrec = K.nrec
lim_pts = np.floor(0.5 * 0.25 / 0.01 + 1e-6)                        # 12 points
for name, spr in (('recorded spread', K.SPR_raw), ('replica spread series', K.SPR_med)):
    nxt = np.r_[spr[::-1][1:], 99.0]                                 # chronological next-bar spread, points
    ok = (K.gap_all <= 120) & (nxt <= 50) & (nxt <= lim_pts + 1e-9)
    rows = []
    for j, k in enumerate(MODS):
        a = np.asarray(F[k]); b = np.where(ok, raw[:, j], 0)
        rows.append(dict(module=k, replica=int((a[1500:] != 0).sum()), fixed_mql5=int((b[1500:] != 0).sum()),
                         mismatches=int((a[1500:] != b[1500:]).sum()),
                         of_which_recorded_zero=int(((a != b) & (nrec == 0))[1500:].sum())))
    print(f'\n== entries with the % limit compared in whole points (12 pts), {name} ==')
    print(pd.DataFrame(rows).set_index('module').to_string())

# ---- where the recorded zeros are ----
z = m.spread.values == 0
print('\nrecorded spread 0: first', m.index[z][0], ' last', m.index[z][-1], ' share of 15:00-18:59 bars', round(z[(K.H.tod >= 900) & (K.H.tod < 1140)].mean(), 3))
# ---- live EA: share of 13-point quotes the double comparison rejects, at this data's price range ----
lo, hi = int(m.low.min() * 100), int(m.high.max() * 100)
bids = np.arange(lo, hi) / 100.0; asks = (np.arange(lo, hi) + 13) / 100.0
rej = (asks - bids) > 50 / 100.0 * 0.25 + 0.01 / 2
print(f'live EA, 13-point quotes between {lo/100:.2f} and {hi/100:.2f}: rejected {rej.mean():.3f}, accepted {1 - rej.mean():.3f}')
bids12 = bids; asks12 = (np.arange(lo, hi) + 12) / 100.0; asks14 = (np.arange(lo, hi) + 14) / 100.0
print('  12-point rejected', ((asks12 - bids12) > 0.13).mean(), ' 14-point rejected', ((asks14 - bids) > 0.13).mean())
print('indicator, 13 * _Point > 0.125 + _Point/2 :', 13 * 0.01 > 0.125 + 0.005)
