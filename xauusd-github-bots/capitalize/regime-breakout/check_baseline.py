"""Sanity: reproduce the pair's $4.68/day and the report's Maxi / Donchian numbers; buy-and-hold baselines."""
import numpy as np, pandas as pd
from common import *
days, pp, a, b = pair_daily()
print('pair common window', summarize(pp), 'first/last day', days[0].date(), days[-1].date())
for nm in ['MAXI', 'DON']:
    d, sig, kw = base(nm); t = simulate(d, sig, **kw)
    print(nm, stats(t, d, nm)['per_day'], 'common', summarize(window_daily(t, d, *COMMON))['per_day'], 'yrs', years(daily(t, d)).to_dict())
d = load('H1')
print('hold 0.01 lot test 2022-01..2026-10 (net of swap, gross):', hold_per_day(d, *TEST))
print('hold train:', hold_per_day(d, *TRAIN), 'hold common:', hold_per_day(d, *COMMON))
R = d1_regimes()
print(R.loc['2016':].apply(lambda s: s.value_counts(normalize=True).round(2).to_dict()))
