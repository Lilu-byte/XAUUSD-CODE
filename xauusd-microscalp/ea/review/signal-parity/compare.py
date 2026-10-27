"""Bar-by-bar comparison: MQL5 port (port.py) vs ea_replica.py signal functions."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea/review/signal-parity')
import ea_replica as R
from mlib import load_m1, load, ema, htf_on_m1
from port import run_ea

m = load_m1()
N = len(m)
tr_rep = R.h1_trend(m)                                  # replica's H1 trend (htf_on_m1)

# --- MQL5 port inputs: epoch seconds (server time treated as UTC, like MQL5 datetime) ---
Tc = (m.index.values.astype('datetime64[s]').astype(np.int64))
O, H, L, C = (m[k].values.astype(np.float64) for k in ('open', 'high', 'low', 'close'))
V = m.tick_volume.values.astype(np.int64)
rev = lambda a: np.ascontiguousarray(a[::-1])
Ts, Os, Hs, Ls, Cs, Vs = map(rev, (Tc, O, H, L, C, V))

# --- the three H1 trend variants ---
h1 = load('H1')
h1v = np.sign(ema(h1.close, 20) - ema(h1.close, 80)).values
h1t = h1.index.values.astype('datetime64[s]').astype(np.int64)
# EA H1Trend(): CopyBuffer(shift 1) at the first tick of the NEXT M1 bar (TimeCurrent ~ next bar open)
tnext = np.r_[Tc[1:], Tc[-1] + 60]
idx0 = np.searchsorted(h1t, tnext, 'right') - 1         # H1 bar 0 (contains the tick)
tr_ea = np.where(idx0 - 1 >= 0, h1v[np.clip(idx0 - 1, 0, None)], 0)
# Indicator TrendAt(time[i] + 60): iBarShift(H1, t - 1) then shift sh + 1
sh = np.searchsorted(h1t, Tc + 60 - 1, 'right') - 1
tr_ind = np.where(sh - 1 >= 0, h1v[np.clip(sh - 1, 0, None)], 0)

print('H1 trend variants vs replica (all bars): EA', (tr_ea == tr_rep).mean(), ' indicator', (tr_ind == tr_rep).mean())
bad_ind = np.where(tr_ind != tr_rep)[0]
print('  indicator trend differs on', len(bad_ind), 'bars; minute-of-hour of those:', pd.Series(m.index[bad_ind].minute).value_counts().head(3).to_dict())
bad_ea = np.where(tr_ea != tr_rep)[0]
print('  EA trend differs on', len(bad_ea), 'bars:', [str(x) for x in m.index[bad_ea][:10]])

rep = {'PB': R.sig_pullback(m, tr_rep), 'SF': R.sig_spike_fade(m), 'QB': R.sig_quarter_fade(m), 'CP': R.sig_patterns(m, tr_rep)}
rep = {k: np.nan_to_num(np.asarray(v, float)).astype(int) for k, v in rep.items()}


def cmp(port, label, warm=1500):
    rows = []
    for j, k in enumerate(('PB', 'SF', 'QB', 'CP')):
        a = rep[k][warm:]; b = port[warm:, j]
        both = ((a != 0) | (b != 0))
        rows.append(dict(module=k, replica=(a != 0).sum(), mql5=(b != 0).sum(), agree=((a == b) & (a != 0)).sum(),
                         replica_only=((a != 0) & (b == 0)).sum(), mql5_only=((a == 0) & (b != 0)).sum(),
                         opposite=((a != 0) & (b != 0) & (a != b)).sum(), bar_match=(a == b).mean(),
                         signal_match=((a == b) & both).sum() / max(both.sum(), 1)))
    print(f'\n== {label} (bars {warm}..{N - 1}) ==')
    print(pd.DataFrame(rows).set_index('module').to_string())


P_rep = run_ea(Ts, Os, Hs, Ls, Cs, Vs, tr_rep.astype(np.int64), 1500)
cmp(P_rep, 'MQL5 port, replica H1 trend, 1500-bar window (EA)')
cmp(P_rep, 'same, from bar 0 (incl. warm-up)', warm=0)
P_ea = run_ea(Ts, Os, Hs, Ls, Cs, Vs, tr_ea.astype(np.int64), 1500)
cmp(P_ea, 'MQL5 port, EA H1Trend() timing')
P_ind = run_ea(Ts, Os, Hs, Ls, Cs, Vs, tr_ind.astype(np.int64), 10 ** 9)
cmp(P_ind, 'MQL5 port, indicator TrendAt() timing, unlimited window (indicator)')

np.save('/mnt/project-files/xauusd-microscalp/ea/review/signal-parity/port_sig.npy', P_rep)

# mismatch listing
for j, k in enumerate(('PB', 'SF', 'QB', 'CP')):
    a = rep[k]; b = P_rep[:, j]
    d = np.where(a != b)[0]
    print(f'\n{k}: {len(d)} mismatching bars (all, incl. warm-up). First 15:')
    for p in d[:15]:
        print('  ', m.index[p], 'bar', p, 'replica', a[p], 'mql5', b[p], 'trend', tr_rep[p])

# window: EA: tod(signal bar open) in [01:05, 22:29] and TodOf(TimeCurrent()) < 22:58
tod = m.tod.values
win_ea = (tod >= 65) & (tod <= 1349) & (((tnext % 86400) // 60) < 1378)
win_rep = (tod >= 65) & (tod <= 1349) & ~m.last_of_session.values & (np.arange(N) < N - 1)
print('\nEntry window: bars where EA window != replica window:', (win_ea != win_rep).sum(),
      [str(x) for x in m.index[np.where(win_ea != win_rep)[0]][:12]])
for j, k in enumerate(('PB', 'SF', 'QB', 'CP')):
    a = np.where(win_rep, rep[k], 0)[1500:]; b = np.where(win_ea, P_rep[:, j], 0)[1500:]
    both = (a != 0) | (b != 0)
    print(f'  {k}: tradable signals replica {(a != 0).sum()} mql5 {(b != 0).sum()} match {((a == b) & both).sum() / max(both.sum(), 1):.4f}')
