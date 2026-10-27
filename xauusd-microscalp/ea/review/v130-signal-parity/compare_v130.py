"""Bar-by-bar parity: literal port of the v1.30 MQL5 code (port_v130.py) vs ea_replica_v130.signals() + run_module's
gap/spread filter. Run: python3 -I compare_v130.py"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea/review/v130-signal-parity')
import numpy as np, pandas as pd
import ea_replica_v130 as V
import ea_replica as R
from mlib import Harness, spread_series, load
from ea_sim import LAST_ENTRY_TOD, FIRST_ENTRY_TOD
import port_v130 as P

pd.set_option('display.width', 250)
H = Harness(); m = H.m1; N = len(m)
tr = R.h1_trend(m).astype(np.int64)

# ---- M1 arrays, series order ----
Tc = m.index.values.astype('datetime64[s]').astype(np.int64)
rev = lambda a: np.ascontiguousarray(a[::-1])
Ts, Os, Hs, Ls, Cs = (rev(x) for x in (Tc, m.open.values, m.high.values, m.low.values, m.close.values))
Vs = rev(m.tick_volume.values.astype(np.int64))
SPR_raw = rev(m.spread.values.astype(np.float64))                    # recorded spread, points (0 on ~10% of bars)
SPR_med = rev(np.round(m.spread_usd.values * 100, 6))               # replica's spread (zeros -> hour median), points

# ---- M5 series as the terminal holds it (the whole export, chronological) ----
m5 = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv')
t5 = pd.to_datetime(m5.time, format='%Y.%m.%d %H:%M')
T5 = t5.values.astype('datetime64[s]').astype(np.int64)
O5 = m5.open.values.astype(np.float64); C5 = m5.close.values.astype(np.float64)
E5 = P.mt5_ema(C5, 9)

# ---- H1 trend for the indicator: TrendAt(time[i] + 60) ----
h1 = load('H1'); h1v = np.sign(V.ema(h1.close, 20) - V.ema(h1.close, 80)).values.astype(np.int64)
h1t = h1.index.values.astype('datetime64[s]').astype(np.int64)
t = Tc + 60
sh = np.searchsorted(h1t, t - 1, 'right') - 1
sh = np.where(h1t[np.clip(sh, 0, None)] + 3600 > t, sh - 1, sh)
tr_ind = np.where(sh >= 0, h1v[np.clip(sh, 0, None)], 0).astype(np.int64)
print('indicator TrendAt == replica trend on', (tr_ind == tr).sum(), 'of', N, 'bars')

cpOn = np.zeros(16, np.bool_)
for g in V.CP_DEFAULT:                                              # engulf 4,5  star 10,11  three 12,13
    cpOn[{'engulf': [4, 5], 'star': [10, 11], 'three': [12, 13]}[g]] = True
tpArr = np.full(4, 0.25); modOn = np.ones(4, np.bool_)
MODS = ('PB', 'SF', 'QB', 'CP')


def port(mode, spr, trend, window=1500, need_full=True, ind=False, fades=False):
    raw, take, d5 = P.run_ea(Ts, Os, Hs, Ls, Cs, Vs, spr, trend, window, need_full,
                             2, 1.0, 0.9, 0.5, 3.0, 0.1, 15, 19, True, cpOn, 0.5,
                             {'off': 0, 'candle': 1, 'ema': 2}[mode], fades, T5, O5, C5, E5,
                             65, 1349, 1378, True, 900, 1140,
                             50.0, tpArr, 50, 0.01, modOn, ind)
    return raw, take, d5


def replica(mode, fades=False):
    p = dict(V.D, m5=mode, fades=fades)
    S = V.signals(H, tr, p)
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    seen = spread_series(m, 'bar'); nxt = np.r_[seen[1:], 99.0]
    lim = min(0.50, p['spread_pct'] / 100.0 * p['tp'])
    win = (H.tod <= LAST_ENTRY_TOD) & (H.tod >= FIRST_ENTRY_TOD) & ~H.last & (np.arange(N) < N - 1)   # _sim_next entry test
    F = {k: np.where((gap == 60) & (nxt <= lim + 1e-9) & win, s, 0) for k, s in S.items()}
    return S, F, gap


def table(A, B, label, warm=1500):
    rows = []
    for j, k in enumerate(MODS):
        a = np.asarray(A[k])[warm:]; b = B[warm:, j]
        rows.append(dict(module=k, replica=int((a != 0).sum()), mql5=int((b != 0).sum()), match=int(((a == b) & (a != 0)).sum()),
                         replica_only=int(((a != 0) & (b == 0)).sum()), mql5_only=int(((a == 0) & (b != 0)).sum()),
                         opposite=int(((a != 0) & (b != 0) & (a != b)).sum())))
    D = pd.DataFrame(rows).set_index('module')
    print(f'\n== {label} (bars {warm}..{N - 1}) =='); print(D.to_string())
    return D


def first_mism(A, B, k, extra, n=8, warm=1500):
    j = MODS.index(k); a = np.asarray(A[k]); b = B[:, j]
    d = np.where(a != b)[0]; d = d[d >= warm]
    out = []
    for p in d[:n]:
        out.append(f'{m.index[p]} p={p} replica={a[p]} mql5={b[p]} ' + extra(p))
    return out


rec = m.spread.values; gap_all = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
nrec = np.r_[rec[1:], -1]; nmed = np.r_[np.round(m.spread_usd.values[1:] * 100, 6), -1]
why = lambda p: f'next-bar recorded spread {nrec[p]} pts (replica sees {nmed[p]:.1f}), gap {gap_all[p]}s, tod {H.tod[p]}'

ALL = {}
for mode in ('off', 'candle', 'ema'):
    S, F, gap = replica(mode)
    raw, take, d5 = port(mode, SPR_raw, tr)
    _, take_med, _ = port(mode, SPR_med, tr)
    ALL[mode] = (S, F, raw, take, take_med, d5)
    t1 = table(S, raw, f'm5={mode}: SIGNALS (replica signals() vs MQL5 sig[] after M5 + hours/session zeroing)')
    for k in MODS:
        L = first_mism(S, raw, k, lambda p: f'tr {tr[p]} d5 {d5[p]}')
        if L: print(f'  {k} first raw mismatches:'); [print('    ', x) for x in L]
    t2 = table(F, take, f'm5={mode}: ENTRIES (replica + run_module gap/spread filter vs EA entry filter, recorded spread)')
    for k in MODS:
        L = first_mism(F, take, k, why, n=5)
        if L: print(f'  {k} first entry mismatches:'); [print('    ', x) for x in L]
    table(F, take_med, f'm5={mode}: ENTRIES, EA fed the replica spread series (zeros -> hour median)')

# ---- decomposition of entry mismatches, m5 off ----
S, F, raw, take, take_med, d5 = ALL['off']
print('\n== decomposition of ENTRY mismatches, m5=off (bars >= 1500) ==')
for j, k in enumerate(MODS):
    a = F[k]; b = take[:, j]; d = np.where(a != b)[0]; d = d[d >= 1500]
    cat = pd.Series(np.select([nrec[d] == 13, (nrec[d] == 0), gap_all[d] != 60], ['next spread = 13 pts', 'recorded spread 0', 'gap != 60'], 'other'))
    sig_raw = (raw[1500:, j] != 0).sum()
    print(f'  {k}: {len(d)} mismatches  {cat.value_counts().to_dict()}  (raw signals {sig_raw}, entries replica {(a[1500:] != 0).sum()} mql5 {(b[1500:] != 0).sum()})')

# ---- the indicator: unlimited window, TrendAt, gap == 60, spread[i-1] ----
for mode in ('off', 'candle', 'ema'):
    S, F, raw, take, take_med, d5 = ALL[mode]
    raw_i, take_i, _ = port(mode, SPR_raw, tr_ind, window=10 ** 9, need_full=False, ind=True)
    table(F, take_i, f'm5={mode}: INDICATOR marks vs replica entries')
    table({k: take[:, j] for j, k in enumerate(MODS)}, take_i, f'm5={mode}: INDICATOR marks vs EA entries (both recorded spread)')

# ---- fades=True quick check ----
S, F, gap = replica('candle', fades=True)
raw, take, d5 = port('candle', SPR_raw, tr, fades=True)
table(S, raw, 'm5=candle, fades=True: SIGNALS')

# ---- how much the 13-point rule moves: entries in the test weeks ----
S, F, raw, take, take_med, d5 = ALL['off']
te = m.index >= V.SPLIT
for j, k in enumerate(MODS):
    a = (F[k] != 0); b = (take[:, j] != 0)
    print(f'{k}: entries TEST replica {int((a & te).sum())}  EA-proxy {int((b & te).sum())}  extra 13-pt {int((b & ~a & te & (nrec == 13)).sum())}')
np.save('/mnt/project-files/xauusd-microscalp/ea/review/v130-signal-parity/take_off.npy', ALL['off'][3])
