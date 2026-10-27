"""Score every rebuilt bot: full history of its timeframe, by year, the common May 2025 - Oct 2026 window
(where the GoldAllAgree + GoldAsiaBreak pair made $4.66/day), and against random directions."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
from gbt import simulate, stats, by_year, daily, coinflip
from bots import REGISTRY

OUT = '/mnt/project-files/xauusd-github-bots/'
COMMON = pd.Timestamp('2025-05-05')
only = sys.argv[1:]
rows, years, trades = [], {}, []
for name, fn in REGISTRY.items():
    if only and not any(o in name for o in only): continue
    d, sig, kw = fn()
    t = simulate(d, sig, **kw)
    r = stats(t, d, name); r['tf_from'] = str(d.index[0].date())
    dc = d[d.index >= COMMON]; tc = t[t.entry_time >= COMMON]
    rc = stats(tc, dc); r['common_per_day'] = rc['per_day']; r['common_win'] = rc['win']
    cf = coinflip(d, sig, runs=40, **{k: v for k, v in kw.items()})
    r['coinflip_median'] = round(float(np.median(cf)), 2); r['beats_random_%'] = round(float((cf < r['per_day']).mean() * 100))
    rows.append(r); years[name] = by_year(t, d)
    t = t.assign(bot=name); trades.append(t)
    print(json.dumps(r, default=str)); print('   by year', years[name], flush=True)
res = pd.DataFrame(rows)
tag = '_'.join(only) if only else 'all'
res.to_csv(OUT + f'results_{tag}.csv', index=False)
pd.DataFrame(years).T.to_csv(OUT + f'results_by_year_{tag}.csv')
pd.concat(trades).drop(columns=['ei', 'xi']).round(2).to_csv(OUT + f'trades_{tag}.csv', index=False)
