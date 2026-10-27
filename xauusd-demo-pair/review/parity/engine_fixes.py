"""Apply the proposed engine.py fixes in memory (file untouched) and compare with the EA port."""
import sys, os, tempfile, types; sys.dont_write_bytecode = True
os.environ['NUMBA_DISABLE_CACHING'] = '1'
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
src = open('/mnt/project-files/xauusd-5-a-day/code/engine.py').read().replace('@njit(cache=True)', '@njit')
fix2 = [("    pos = 0; ent = 0.0; e_sc = 1.0; tpd = 0.0; sld = 0.0", "    pos = 0; ent = 0.0; e_sc = 1.0; tpd = 0.0; sld = 0.0; eday = -1"),
        ("                if dp >= target - 1e-9 or nt >= max_tr or dp <= -maxloss: done = True",
         "                if eday == cur and (dp >= target - 1e-9 or nt >= max_tr or dp <= -maxloss): done = True   # a trade carried in from yesterday does not use up today's trade"),
        ("            e_sc = sc[i]; pos = int(sig[i]); nt += 1; dtr[cur] += 1", "            e_sc = sc[i]; pos = int(sig[i]); nt += 1; dtr[cur] += 1; eday = cur")]
def mod(s, name):
    m = types.ModuleType(name); exec(compile(s, name, 'exec'), m.__dict__); return m
orig = mod(src, 'eng_orig')
s2 = src
for a, b in fix2:
    assert s2.count(a) == 1, a
    s2 = s2.replace(a, b)
f2 = mod(s2, 'eng_fix2')
s3 = s2.replace('END = 23 * 60 + 30', 'END = 22 * 60 + 45'); f3 = mod(s3, 'eng_fix2_2245')
P = orig.prep('M5'); P1 = dict(P); P1['sc'] = np.ones_like(P['sc'])
days = pd.bdate_range('2025-05-06', '2026-10-09')
e = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
ea = e.groupby(e.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0)
def st(s):
    eq = s.cumsum(); m = s.groupby(s.index.to_period('M')).sum()
    return f'{s.mean():.3f}/day dd {(eq - eq.cummax()).min():.0f} wm {m.min():.0f}'
for tp in (5, 8):
    out = []
    for name, M, PP in (('orig scaled', orig, P), ('orig sc=1 (fix0)', orig, P1), ('fix0+fix2', f2, P1), ('fix0+fix2+END2245', f3, P1)):
        ab = M.sim(PP, 'asia_break', 'any', 540, tp, 50).pnl.reindex(days, fill_value=0)
        out.append(f'{name}: Asia {st(ab)} | EA+Asia {st(ea + ab)}')
    print(f'TP{tp}:', ' || '.join(out))
# asia2.py-style window for the M5 row (2025-05-06..2026-10-10, engine's own dates, no reindex)
for tp in (5, 8):
    for name, PP in (('scaled', P), ('sc=1', P1)):
        r = orig.sim(PP, 'asia_break', 'any', 540, tp, 50); r = r[(r.index >= '2025-05-06') & (r.index < '2026-10-10')]
        print(f'asia2 M5 TP{tp} {name}:', {k: round(float(v), 2) for k, v in orig.summ(r).items() if k in ('per_day', 'hit5', 'loss_days', 'worst_month', 'max_dd')})
print('--- fix0+fix2, asia2 M5 window and combo columns')
for tp in (5, 8):
    r = f2.sim(P1, 'asia_break', 'any', 540, tp, 50); r = r[(r.index >= '2025-05-06') & (r.index < '2026-10-10')]
    print(f'asia2 M5 TP{tp}:', {k: round(float(v), 2) for k, v in f2.summ(r).items() if k in ('per_day', 'hit5', 'loss_days', 'worst_month', 'max_dd')})
    ab = f2.sim(P1, 'asia_break', 'any', 540, tp, 50).pnl.reindex(days, fill_value=0); s = ea + ab
    print(f'  combo EA+Asia TP{tp}: {s.mean():.2f}/day, days>=5 {(s >= 4.99).mean():.2f}, {st(s)}')
