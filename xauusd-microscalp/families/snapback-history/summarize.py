"""Summaries of grid_summary.csv / grid_quarters.csv and the pre-specified pick rule:
  Pick A = M15 setting with the highest SEL (2022-07..2024-12) $/day;  Pick B = M5 setting with the highest
  SEL (2025-05..2025-12) $/day;  Pick C = M15 setting (not A) with the most positive SEL quarters, tie-break SEL $/day."""
import pandas as pd, numpy as np
OUT = '/mnt/project-files/xauusd-microscalp/families/snapback-history/'
G = pd.read_csv(OUT + 'grid_summary.csv'); Q = pd.read_csv(OUT + 'grid_quarters.csv')
K = ['tf', 'n', 'k', 'gate', 'N', 'sl', 'max_open']
W = G.pivot_table(index=K, columns='period', values=['per_day', 'per_trade', 'trades_day', 'rand_per_day', 'long_per_day',
                                                      'short_per_day', 'wide_per_day', 'lat1_per_day', 'win', 'worst_day',
                                                      'worst_trade', 'long_share', 'rand_beats', 'per_trade_over_ar'])
def col(v, p): return W[(v, p)]
for tf in ('M5', 'M15'):
    w = W.loc[tf]
    print(f'\n=== {tf}: {len(w)} settings')
    for p in ('SEL', 'LATER', 'LATER_CLEAN', 'M1ERA', 'PRE_M1', 'ALL'):
        x = w[('per_day', p)]; y = w[('per_trade', p)]; rb = w[('rand_beats', p)]; r = w[('rand_per_day', p)]
        print(f'  {p:11s}: $/day median {x.median():+.2f} (best {x.max():+.2f}, worst {x.min():+.2f}); positive {int((x > 0).sum())}/{len(x)}; '
              f'>= +5/day {int((x >= 5).sum())}; median $/trade {y.median():+.3f}; median random same bars {r.median():+.2f}; '
              f'beats all 20 random seeds {int((rb == 0).sum())}')
    # by factor in SEL and LATER
    for fac in ('n', 'k', 'gate', 'N', 'sl', 'max_open'):
        a = G[(G.tf == tf)].groupby(['period', fac]).per_trade.median().unstack(0)[['SEL', 'LATER', 'LATER_CLEAN', 'M1ERA']]
        print(f'  median $/trade by {fac}: ' + '; '.join(f"{i}: " + '/'.join(f'{v:+.2f}' for v in rr.values) for i, rr in a.iterrows()) + '  (SEL/LATER/LATER_CLEAN/M1ERA)')
# quarter stability
print('\n=== quarter stability (share of settings positive per quarter, base cost)')
for tf in ('M5', 'M15'):
    q = Q[Q.tf == tf].groupby('quarter')
    print(f'  {tf}: ' + ' '.join(f"{k}:{(g.per_day > 0).mean():.2f}" for k, g in q))
    print(f'  {tf} median $/day: ' + ' '.join(f"{k}:{g.per_day.median():+.2f}" for k, g in q))
    print(f'  {tf} median random $/day: ' + ' '.join(f"{k}:{g.rand_per_day.median():+.2f}" for k, g in q))
# picks
S = G[G.period == 'SEL'].set_index(K)
a = S.loc['M15'].per_day.idxmax(); b = S.loc['M5'].per_day.idxmax()
qs = Q[(Q.tf == 'M15') & (Q.quarter < '2025Q1')].groupby(K[1:]).per_day.apply(lambda x: (x > 0).sum())
cand = pd.DataFrame({'posq': qs, 'sel': S.loc['M15'].per_day}).drop(index=a)
c = cand.sort_values(['posq', 'sel'], ascending=False).index[0]
print('\nPICKS (pre-specified rule):', 'A M15', a, ' B M5', b, ' C M15', c, 'posq', cand.loc[c, 'posq'])
print('\n=== top 8 per TF by SEL $/day (SEL | LATER_CLEAN | M1ERA | LATER)')
for tf in ('M5', 'M15'):
    w = W.loc[tf].sort_values(('per_day', 'SEL'), ascending=False).head(8)
    for i, r in w.iterrows():
        print(f"  {tf} n{i[0]} k{i[1]} g{i[2]} N{i[3]} sl{i[4]} mo{i[5]}: " + ' | '.join(
            f"{r[('per_day', p)]:+.2f}/d {r[('trades_day', p)]:.2f}t {r[('per_trade', p)]:+.2f}pt rnd{r[('rand_per_day', p)]:+.2f}" for p in ('SEL', 'LATER_CLEAN', 'M1ERA', 'LATER')))
