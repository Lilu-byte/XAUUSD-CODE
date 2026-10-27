"""Pair (GoldAllAgree + GoldAsiaBreak) on a mark-to-market daily basis (the rule legs are MTM; the pair in
diagnostics.py is booked on exit dates). Marks open GoldAllAgree / AsiaBreak trades at each server day's last M5 close.
Usage: python3 -I pair_mtm.py (after verify.py)"""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest')
import numpy as np, pandas as pd
import gbt
from verify import pair_daily, combo, COMMON

OUT = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest/'
m = gbt.load('M5'); days = pd.DatetimeIndex(np.unique(m.index.normalize()))
eod = m.close.groupby(m.index.normalize()).last()
pair_r, a, b = pair_daily()
def mtm(tr, ent_col, pnl_col, dir_col=None):
    out = pd.Series(0.0, index=days)
    for _, r in tr.iterrows():
        d0, d1 = r.entry_time.normalize(), r.exit_time.normalize()
        if d0 == d1:
            out[d1] += r[pnl_col]; continue
        sgn = 1 if dir_col is None else r[dir_col]
        marks = eod.loc[d0:d1].iloc[:-1]           # day-end marks before the exit day
        prev = r[ent_col]
        for dd, px in marks.items():
            out[dd] += sgn * (px - prev); prev = px
        out[d1] += r[pnl_col] - sgn * (prev - r[ent_col])   # remainder (incl. swap) on exit day
    return out
pa = mtm(a, 'entry', 'pnl_usd'); pb = mtm(b, 'entry_px', 'pnl', 'dir')
pair_m = (pa + pb).loc[COMMON[0]:COMMON[1]]
S = pd.read_pickle(OUT + '_verify_daily.pkl')['daily']
res = dict(pair_realized=combo(pd.Series(0.0, pair_m.index), pair_r.loc[COMMON[0]:COMMON[1]]),
           pair_mtm=combo(pd.Series(0.0, pair_m.index), pair_m),
           pair_mtm_plus_a=combo(S[('H4', 'a_MA_stack')], pair_m),
           pair_mtm_plus_e=combo(S[('H1', 'e_all_5of7')], pair_m),
           multi_day_trades=dict(allagree=int((a.exit_time.dt.normalize() != a.entry_time.dt.normalize()).sum()),
                                 asiabreak=int((b.exit_time.dt.normalize() != b.entry_time.dt.normalize()).sum())))
print(json.dumps(res, indent=1))
json.dump(res, open(OUT + 'pair_mtm_results.json', 'w'), indent=1)
