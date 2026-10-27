import sys; sys.dont_write_bytecode = True
"""Port of GoldAllAgree.mq5 timing onto the M5 export, compared with expected_trades_M5.csv.
EA: at the first tick of each M5 bar (time = bar open) it reads shift-1 EMA20/80 on M5..H4,
buys at ask (bar open + spread) / closes at bid (bar open). Spread filter 80 pts on entry."""
import sys, pandas as pd, numpy as np
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load, ema, align, SWAP_LONG
TFS = ['M5', 'M15', 'M30', 'H1', 'H4']
b = load('M5'); t = b.index
# 1) rebuild the replay in memory (same code as expected_trades.py) and check the CSV is current
bc = t + pd.Timedelta(minutes=5)
def sig_on(index):
    T = [align(load(tf), tf, index, np.sign(ema(load(tf).close, 20) - ema(load(tf).close, 80)).values).fillna(0).values for tf in TFS]
    return (np.vstack(T) > 0).all(0), T
def swap(e, x):
    nights = pd.date_range(e.normalize(), x.normalize(), freq='D')[1:]
    return sum(3 if n.dayofweek == 3 else 1 for n in nights) * SWAP_LONG
up_r, _ = sig_on(bc)
csv = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
# 2) EA timing: decision at each bar open t_i
up_e, Te = sig_on(t)
o = b.open.values; spr = b.spread.values * 0.01
def ea_trades(spread_filter=True, maxspr=0.80):
    rows = []; pos = False
    for i in range(len(t)):
        if pos and not up_e[i]:
            rows[-1].update(exit_time=t[i], exit=o[i]); pos = False
        elif not pos and up_e[i] and (not spread_filter or spr[i] <= maxspr):
            rows.append(dict(entry_time=t[i], entry=o[i] + spr[i])); pos = True
    if pos: rows.pop()
    tr = pd.DataFrame(rows)
    tr['pnl_usd'] = [x - e - swap(a, z) for a, e, z, x in zip(tr.entry_time, tr.entry, tr.exit_time, tr.exit)]
    return tr
ea = ea_trades(); ea_nf = ea_trades(False)
print('replay CSV trades', len(csv), 'pnl', round(csv.pnl_usd.sum(), 2))
print('EA port (spread filter on) trades', len(ea), 'pnl', round(ea.pnl_usd.sum(), 2), '| filter off', len(ea_nf), round(ea_nf.pnl_usd.sum(), 2))
# 3) match: replay entry at close time bc; EA should enter at the first bar open >= that time
nxt = lambda ts: t[np.searchsorted(t.values, np.asarray(ts, dtype='datetime64[ns]'))]
csv['ea_entry_expected'] = nxt(csv.entry_time); csv['ea_exit_expected'] = nxt(csv.exit_time)
for name, E in (('filter on', ea), ('filter off', ea_nf)):
    m = csv.merge(E, left_on='ea_entry_expected', right_on='entry_time', how='outer', suffixes=('_r', '_e'), indicator=True)
    both = m[m._merge == 'both']
    same_exit = (both.ea_exit_expected == both.exit_time_e)
    print(f'[{name}] matched entries {len(both)}/{len(csv)} (replay-only {(m._merge=="left_only").sum()}, EA-only {(m._merge=="right_only").sum()}), same exit {same_exit.sum()}')
    d = both.pnl_usd_e - both.pnl_usd_r
    print(f'   pnl diff on matched: sum {d.sum():.2f}, mean {d.mean():.3f}, |diff|>1$: {(d.abs()>1).sum()}')
    if name == 'filter off':
        gap_e = (both.entry_time_e - both.entry_time_r) > pd.Timedelta(minutes=5)
        gap_x = (both.exit_time_e - both.exit_time_r) > pd.Timedelta(minutes=5)
        print('   trades whose entry falls in a session gap:', gap_e.sum(), 'pnl diff', round(d[gap_e].sum(), 2), '| exit in gap:', gap_x.sum(), 'pnl diff', round(d[gap_x].sum(), 2))
        print('   entry/exit replay timestamps in gaps:', both.entry_time_r[gap_e].dt.strftime('%H:%M').value_counts().to_dict(), both.exit_time_r[gap_x].dt.strftime('%H:%M').value_counts().to_dict())
        un = m[m._merge != 'both']
        print(un[['entry_time_r', 'exit_time_r', 'pnl_usd_r', 'entry_time_e', 'exit_time_e', 'pnl_usd_e', '_merge']].to_string())
# 4) decision disagreements: EA decision at bar open t_i vs replay decision at close of bar i-1
prev_close = pd.Series(up_r, index=bc)
# replay decision applying at EA tick t_i is the one at the last bc <= t_i
r_at = prev_close.reindex(prev_close.index.union(t)).ffill().reindex(t).fillna(False).values.astype(bool)
dis = r_at != up_e
print('bars where EA decision != replay decision:', dis.sum(), 'at times', pd.Series(t[dis]).dt.strftime('%H:%M').value_counts().head(5).to_dict())
for k, tf in enumerate(TFS):
    _, Tr = sig_on(bc)
    break
