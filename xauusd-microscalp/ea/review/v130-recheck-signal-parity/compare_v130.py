"""RE-RUN of the bar-by-bar parity for the FIXED v1.30 code (after the review fixes).
Literal port of the MQL5 code (port_v130.py in this folder) vs ea_replica_v130.signals() + run_module's gap/spread
filter, for the EA (OnTick entry filter = SpreadVeto on the recorded next-bar spread) and for the indicator
(marks; recorded spread 0 = unknown, no spread check). All port inputs are PARSED from the two .mq5 files' defaults.
Run: NUMBA_CACHE_DIR=<scratch> python3 -I -B compare_v130.py"""
import sys, re
sys.dont_write_bytecode = True
HERE = '/mnt/project-files/xauusd-microscalp/ea/review/v130-recheck-signal-parity'
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
sys.path.insert(0, HERE)
import numpy as np, pandas as pd
import ea_replica_v130 as V
import ea_replica as R
from mlib import Harness, spread_series, load
from ea_sim import LAST_ENTRY_TOD, FIRST_ENTRY_TOD
import port_v130 as P

pd.set_option('display.width', 250)
EA_SRC = open('/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalp.mq5').read()
IN_SRC = open('/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalpSignals.mq5').read()


def inputs(src):
    out = {}
    for mm in re.finditer(r'^input\s+(\w+)\s+(\w+)\s*=\s*([^;]+);', src, re.M):
        ty, name, val = mm.group(1), mm.group(2), mm.group(3).strip()
        if ty == 'bool': v = val == 'true'
        elif ty in ('int', 'long'): v = int(val)
        elif ty == 'double': v = float(val)
        elif ty == 'string': v = val.strip('"')
        elif ty == 'ENUM_M5_ALIGN': v = {'M5_OFF': 0, 'M5_CANDLE': 1, 'M5_EMA': 2}[val]
        else: raise ValueError(ty)
        out[name] = v
    return out


def tod(s):
    a, b = s.split(':'); return int(a) * 60 + int(b)


EAI, INI = inputs(EA_SRC), inputs(IN_SRC)
PATS = [('InpCPHammer', 0), ('InpCPInvHammer', 2), ('InpCPEngulf', 4), ('InpCPHarami', 6), ('InpCPPiercing', 8),
        ('InpCPStar', 10), ('InpCPThree', 12), ('InpCPDoji', 14)]


def port_args(I):
    cp = np.zeros(16, np.bool_)
    for nm, j in PATS: cp[j] = cp[j + 1] = I[nm]
    sf = tod(I['InpSessionFrom']); sf = 0 if sf == 1440 else sf
    return dict(n=I['InpPBMinutes'], k=I['InpPBBodyMult'], maru=I['InpPBMaru'], pbMinBody=I['InpPBMinBody'],
                sfmult=I['InpSFMult'], qbk=I['InpQBK'], h0=I['InpQBFromHour'], h1=I['InpQBToHour'],
                cptrend=I['InpCPTrend'], cpOn=cp, cpMinBody=I['InpCPMinBody'], m5fades=I['InpM5Fades'],
                firstTod=tod(I['InpFirstEntry']), lastTod=tod(I['InpLastEntry']),
                closeTod=tod(I.get('InpCloseAll', '22:58')), sessOn=I['InpSessionOn'], sessFrom=sf, sessTo=tod(I['InpSessionTo']),
                pctTP=I['InpMaxSpreadPctTP'], tpArr=np.array([I['InpPBTP'], I['InpSFTP'], I['InpQBTP'], I['InpCPTP']]),
                maxPts=I['InpMaxSpreadPts'], modOn=np.array([I['InpPB'], I['InpSF'], I['InpQB'], I['InpCP']]),
                histSpread=I.get('InpHistSpread', True), ema=I['InpM5EMA'], m5default=I['InpM5Align'])


AE, AI = port_args(EAI), port_args(INI)
print('EA defaults used by the port       :', {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in AE.items()})
print('indicator defaults used by the port:', {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in AI.items()})
diff = {k: (AE[k], AI[k]) for k in AE if k != 'closeTod' and not np.array_equal(np.asarray(AE[k]), np.asarray(AI[k]))}
print('EA vs indicator signal/filter defaults that differ:', diff if diff else 'none')
print('replica D:', {k: V.D[k] for k in ('tp', 'spread_pct', 'sess', 'body_pb', 'body_cp', 'm5', 'fades')}, 'CP groups', V.CP_DEFAULT)
assert AE['pbMinBody'] == V.D['body_pb'] and AE['cpMinBody'] == V.D['body_cp'] and AE['pctTP'] == V.D['spread_pct']
assert (AE['sessFrom'], AE['sessTo']) == V.D['sess'] and np.all(AE['tpArr'] == V.D['tp'])

H = Harness(); m = H.m1; N = len(m)
tr = R.h1_trend(m).astype(np.int64)
Tc = m.index.values.astype('datetime64[s]').astype(np.int64)
rev = lambda a: np.ascontiguousarray(a[::-1])
Ts, Os, Hs, Ls, Cs = (rev(x) for x in (Tc, m.open.values, m.high.values, m.low.values, m.close.values))
Vs = rev(m.tick_volume.values.astype(np.int64))
SPR_raw = rev(m.spread.values.astype(np.float64))                    # recorded spread, points (0 on ~10% of bars)
SPR_med = rev(np.round(m.spread_usd.values * 100, 6))               # replica's spread (zeros -> hour median), points

m5 = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv')
T5 = pd.to_datetime(m5.time, format='%Y.%m.%d %H:%M').values.astype('datetime64[s]').astype(np.int64)
O5 = m5.open.values.astype(np.float64); C5 = m5.close.values.astype(np.float64)
E5 = {9: P.mt5_ema(C5, 9)}
for A in (AE, AI): E5.setdefault(A['ema'], P.mt5_ema(C5, A['ema']))

# H1 trend for the indicator: TrendAt(time[i] + 60)
h1 = load('H1'); h1v = np.sign(V.ema(h1.close, 20) - V.ema(h1.close, 80)).values.astype(np.int64)
h1t = h1.index.values.astype('datetime64[s]').astype(np.int64)
t = Tc + 60
sh = np.searchsorted(h1t, t - 1, 'right') - 1
sh = np.where(h1t[np.clip(sh, 0, None)] + 3600 > t, sh - 1, sh)
tr_ind = np.where(sh >= 0, h1v[np.clip(sh, 0, None)], 0).astype(np.int64)
print('indicator TrendAt == replica trend on', int((tr_ind == tr).sum()), 'of', N, 'bars')
MODS = ('PB', 'SF', 'QB', 'CP')
MODE = {'off': 0, 'candle': 1, 'ema': 2}


def port(mode, spr, trend, A, window=1500, need_full=True, ind=False, fades=None, **over):
    a = dict(A, **over)
    return P.run_ea(Ts, Os, Hs, Ls, Cs, Vs, spr, trend, window, need_full,
                    a['n'], a['k'], a['maru'], a['pbMinBody'], a['sfmult'], a['qbk'], a['h0'], a['h1'], a['cptrend'], a['cpOn'], a['cpMinBody'],
                    MODE[mode], a['m5fades'] if fades is None else fades, T5, O5, C5, E5[a['ema']],
                    a['firstTod'], a['lastTod'], a['closeTod'], a['sessOn'], a['sessFrom'], a['sessTo'],
                    float(a['pctTP']), a['tpArr'].astype(np.float64), a['maxPts'], 0.01, a['modOn'], ind, a['histSpread'])


gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
win = (H.tod <= LAST_ENTRY_TOD) & (H.tod >= FIRST_ENTRY_TOD) & ~H.last & (np.arange(N) < N - 1)   # _sim_next entry test


def replica(mode, fades=False, p=None):
    p = dict(V.D, m5=mode, fades=fades) if p is None else p
    S = V.signals(H, tr, p)
    seen = spread_series(m, 'bar'); nxt = np.r_[seen[1:], 99.0]                     # = run_module lines
    lim = min(0.50, p['spread_pct'] / 100.0 * p['tp']) if p['spread_pct'] > 0 else 0.50
    F = {k: np.where((gap == 60) & (nxt <= lim + 1e-9) & win, s, 0) for k, s in S.items()}
    return S, F


def via_run_module(S, p):
    """Entries straight out of V.run_module (cap 4, hold 1 so a slot is always free; no daily stop in run_module)."""
    out = {}
    for k, s in S.items():
        T = V.run_module(H, s, p['tp'], p['sl'], 1, 4, p['spread_pct'])
        a = np.zeros(N, np.int64); a[T.ei.values] = T.dir.values; out[k] = a
    return out


def table(A, B, label, warm=1500):
    rows = []
    for j, k in enumerate(MODS):
        a = np.asarray(A[k])[warm:]; b = B[warm:, j]
        d = np.where(a != b)[0] + warm
        rows.append(dict(module=k, left=int((a != 0).sum()), right=int((b != 0).sum()), match=int(((a == b) & (a != 0)).sum()),
                         left_only=int(((a != 0) & (b == 0)).sum()), right_only=int(((a == 0) & (b != 0)).sum()),
                         opposite=int(((a != 0) & (b != 0) & (a != b)).sum()),
                         mism_rec0=int((nrec[d] == 0).sum()), mism_other=int((nrec[d] != 0).sum())))
    D = pd.DataFrame(rows).set_index('module')
    print(f'\n== {label} (bars {warm}..{N - 1}) =='); print(D.to_string())
    return D


rec = m.spread.values
nrec = np.r_[rec[1:], -1]; nmed = np.r_[np.round(m.spread_usd.values[1:] * 100, 6), -1]


def detail(A, B, k, n=6, warm=1500, only_other=True):
    j = MODS.index(k); a = np.asarray(A[k]); b = B[:, j]
    d = np.where(a != b)[0]; d = d[d >= warm]
    if only_other: d = d[nrec[d] != 0]
    return [f'{m.index[p]} p={p} left={a[p]} right={b[p]} next-bar recorded {nrec[p]} pts, replica sees {nmed[p]:.1f}, gap {gap[p]}s, tod {H.tod[p]}'
            for p in d[:n]]


ALL = {}; SUMMARY = []
for mode in ('off', 'candle', 'ema'):
    S, F = replica(mode)
    Fr = via_run_module(S, dict(V.D, m5=mode))
    chk = {k: int((F[k] != Fr[k]).sum()) for k in MODS}
    print(f'\n######## m5={mode} ########   compare-filter vs V.run_module entries, mismatching bars: {chk}')
    raw, take, d5 = port(mode, SPR_raw, tr, AE)
    _, take_med, _ = port(mode, SPR_med, tr, AE)
    raw_i, take_i, _ = port(mode, SPR_raw, tr_ind, AI, window=10 ** 9, need_full=False, ind=True)
    ALL[mode] = (S, F, raw, take, take_med, raw_i, take_i, d5)
    t1 = table(S, raw, f'm5={mode}: SIGNALS  left = replica signals(), right = EA sig[] after M5 + hours/session zeroing')
    t1i = table(S, raw_i, f'm5={mode}: SIGNALS  left = replica signals(), right = indicator sig[] (TrendAt, full history)')
    t2 = table(F, take, f'm5={mode}: ENTRIES  left = replica + run_module filter, right = EA OnTick filter on the RECORDED next-bar spread')
    for k in MODS:
        L = detail(F, take, k)
        if L: print(f'  {k} mismatches not explained by a recorded 0:'); [print('    ', x) for x in L]
    t3 = table(F, take_med, f'm5={mode}: ENTRIES  left = replica, right = EA fed the replica spread series (zeros -> hour median)')
    for k in MODS:
        L = detail(F, take_med, k, only_other=False)
        if L: print(f'  {k} mismatches:'); [print('    ', x) for x in L]
    t4 = table(F, take_i, f'm5={mode}: left = replica entries, right = INDICATOR marks')
    for k in MODS:
        L = detail(F, take_i, k)
        if L: print(f'  {k} mismatches not explained by a recorded 0:'); [print('    ', x) for x in L]
    t5 = table({k: take[:, j] for j, k in enumerate(MODS)}, take_i, f'm5={mode}: left = EA entries, right = INDICATOR marks (both recorded spread)')
    for k in MODS:
        SUMMARY.append(dict(m5=mode, module=k, sig_replica=t1.loc[k, 'left'], sig_EA=t1.loc[k, 'right'],
                            sig_mism=int(t1.loc[k, 'left_only'] + t1.loc[k, 'right_only'] + t1.loc[k, 'opposite']),
                            sig_ind_mism=int(t1i.loc[k, 'left_only'] + t1i.loc[k, 'right_only'] + t1i.loc[k, 'opposite']),
                            ent_replica=t2.loc[k, 'left'], ent_EA=t2.loc[k, 'right'],
                            EA_mism=int(t2.loc[k, 'mism_rec0'] + t2.loc[k, 'mism_other']), EA_mism_rec0=t2.loc[k, 'mism_rec0'],
                            EAmed_mism=int(t3.loc[k, 'mism_rec0'] + t3.loc[k, 'mism_other']),
                            ind_marks=t4.loc[k, 'right'], ind_mism=int(t4.loc[k, 'mism_rec0'] + t4.loc[k, 'mism_other']),
                            ind_mism_rec0=t4.loc[k, 'mism_rec0'], ind_vs_EA_mism=int(t5.loc[k, 'mism_rec0'] + t5.loc[k, 'mism_other'])))

print('\n== PARITY SUMMARY (bars 1500..end; mism = bars where the two differ; rec0 = of which the next bar\'s recorded spread is 0) ==')
SM = pd.DataFrame(SUMMARY).set_index(['m5', 'module'])
print(SM.to_string())
SM.to_csv(HERE + '/parity_summary.csv')

# ---- recorded-0 mismatches: always the replica's hour median above the limit while the recorded 0 passes ----
S, F, raw, take, take_med, raw_i, take_i, d5 = ALL['off']
for j, k in enumerate(MODS):
    d = np.where(F[k] != take[:, j])[0]; d = d[d >= 1500]
    print(f'{k}: m5=off EA-vs-replica mismatches {len(d)}: next recorded spread {pd.Series(nrec[d]).value_counts().to_dict()}, '
          f'replica sees {pd.Series(nmed[d]).value_counts().to_dict()}, EA-only {int(((take[d, j] != 0) & (F[k][d] == 0)).sum())}')
z = m.spread.values == 0
print('recorded spread 0: first', m.index[z][0], ' last', m.index[z][-1], ' bars', int(z.sum()))

# ---- fades=True ----
for mode in ('candle', 'ema'):
    S, F = replica(mode, fades=True)
    raw, take, d5 = port(mode, SPR_raw, tr, AE, fades=True)
    raw_i, take_i, _ = port(mode, SPR_raw, tr_ind, AI, window=10 ** 9, need_full=False, ind=True, fades=True)
    table(S, raw, f'm5={mode}, fades=True: SIGNALS replica vs EA')
    table(F, take, f'm5={mode}, fades=True: ENTRIES replica vs EA (recorded spread)')
    table({k: take[:, j] for j, k in enumerate(MODS)}, take_i, f'm5={mode}, fades=True: EA entries vs INDICATOR marks')

# ---- indicator with InpHistSpread = false: marks = signals on bars with a 60 s next bar ----
raw_i, take_i, _ = port('off', SPR_raw, tr_ind, AI, window=10 ** 9, need_full=False, ind=True, histSpread=False)
S, F = replica('off')
G = {k: np.where((gap == 60) & win, s, 0) for k, s in S.items()}
table(G, take_i, 'm5=off, InpHistSpread=false: left = replica signals with a 60 s next bar, right = indicator marks')
np.save(HERE + '/take_off.npy', ALL['off'][3])
