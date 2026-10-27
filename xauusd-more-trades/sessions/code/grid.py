"""Grid on m15_train ONLY (Jul 2022 - Jun 2024, M15, $ scaled to price/4000).

16 setups x 3 direction rules (break / fade / fail) x TP {3,5,8,10} x SL {15,25,35,50} = 768.
Pre-registered pick (written before running):
  eligible = alone trades/day >= 0.30, and pair + stream on m15_train has max_dd not deeper than
             -$323 (baseline -313 - 10) and max_dd_mtm not deeper than -$344 (baseline -334 - 10);
  rank by the stream's own $/day on m15_train (ties: shallower combined max_dd); keep the best eligible version of each family
  (london, nyopen, usdata, prevday); candidates = the 3 families with the highest best.
Writes ../grid_m15_train.csv and ../candidates.json; prints a summary.
"""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/sessions/code')
import json, itertools, numpy as np, pandas as pd
import sessions as S, harness as H

W = 'm15_train'; OUT = '/mnt/project-files/xauusd-more-trades/sessions/'
TPS, SLS = (3, 5, 8, 10), (15, 25, 35, 50)
D = H.days(W)
base = H.pair_parts(W)
base_daily = sum(H.per_day(t, W) for t in base.values())
base_eq_mtm = sum(H.mtm_daily(t, W) for t in base.values())
dd = lambda eq: (eq - eq.cummax()).min()
print('baseline m15_train', round(base_daily.mean(), 2), 'dd', round(dd(base_daily.cumsum())), 'mtm', round(dd(base_eq_mtm)))

B = S.Bars('M15')
lo_, hi_ = np.datetime64(D[0] - pd.Timedelta(days=7)), np.datetime64(D[-1])
rows = []
for name, mode in itertools.product(S.SETUPS, S.MODES):
    sig = [s for s in S.setup_signals('M15', name, mode) if lo_ <= B.dates[s[0]] <= hi_]   # train days only
    for tp, sl in itertools.product(TPS, SLS):
        T = S.simulate(B, sig, tp, sl, scale=True)
        dly = H.per_day(T, W); comb = base_daily + dly
        n = len(H.in_window(T, W))
        rows.append(dict(setup=name, family=S.SETUPS[name][0], mode=mode, tp=tp, sl=sl,
                         alone_per_day=round(dly.mean(), 3), alone_trades_day=round(n / len(D), 3),
                         win=round((H.in_window(T, W).pnl > 0).mean(), 3) if n else np.nan,
                         alone_dd=round(dd(dly.cumsum())),
                         comb_per_day=round(comb.mean(), 3), comb_dd=round(dd(comb.cumsum())),
                         comb_dd_mtm=round(dd(base_eq_mtm + H.mtm_daily(T, W))),
                         corr=round(dly.corr(base_daily), 3)))
G = pd.DataFrame(rows)
G.to_csv(OUT + 'grid_m15_train.csv', index=False)
print(f'versions scored on m15_train: {len(G)}; stream positive alone: {(G.alone_per_day > 0).sum()} '
      f'({(G.alone_per_day > 0).mean():.0%}); median {G.alone_per_day.median():.2f} $/day')
print('positive share by mode:', G.groupby('mode').alone_per_day.apply(lambda x: f'{(x > 0).mean():.0%}').to_dict())
print('positive share by family:', G.groupby('family').alone_per_day.apply(lambda x: f'{(x > 0).mean():.0%}').to_dict())
print('best $/day by setup x mode:')
print(G.pivot_table(index='setup', columns='mode', values='alone_per_day', aggfunc='max').round(2).to_string())
el = G[(G.alone_trades_day >= 0.30) & (G.comb_dd >= -323) & (G.comb_dd_mtm >= -344)]
print(f'eligible: {len(el)}')
cols = ['setup', 'mode', 'tp', 'sl', 'alone_per_day', 'alone_trades_day', 'win', 'alone_dd', 'comb_per_day', 'comb_dd', 'comb_dd_mtm', 'corr']
print('top 12 eligible:'); print(el.sort_values('alone_per_day', ascending=False)[cols].head(12).to_string(index=False))
# ties at 3 decimals broken by the shallower combined drawdown (USD 15m vs LDN 09-15:30 tie at 0.176;
# unrounded 0.1763 vs 0.1757, so the same pick either way)
best = el.sort_values(['alone_per_day', 'comb_dd'], ascending=False, kind='mergesort').groupby('family').head(1)
print('best per family:'); print(best[cols + ['family']].to_string(index=False))
cand = best.head(3)
json.dump(cand[['setup', 'family', 'mode', 'tp', 'sl', 'alone_per_day']].to_dict('records'), open(OUT + 'candidates.json', 'w'), indent=1)
print('CANDIDATES:', cand[['setup', 'mode', 'tp', 'sl', 'alone_per_day']].values.tolist())
