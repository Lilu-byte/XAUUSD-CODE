"""Diagnostic only (NOT used to pick anything; candidates were fixed by grid.py on m15_train):
the same 768 versions on m15_test and on the pair window, to see whether train results carry
over at all and whether ANY version of this family would have passed (a) and (b) in hindsight.
Writes ../grid_all_windows.csv; prints a summary."""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/sessions/code')
import itertools, numpy as np, pandas as pd
import sessions as S, harness as H

OUT = '/mnt/project-files/xauusd-more-trades/sessions/'
G = pd.read_csv(OUT + 'grid_m15_train.csv')
dd = lambda eq: (eq - eq.cummax()).min()
for w, tf in (('m15_test', 'M15'), ('pair', 'M5')):
    base = H.pair_parts(w)
    bd = sum(H.per_day(t, w) for t in base.values()); bm = sum(H.mtm_daily(t, w) for t in base.values())
    B = S.Bars(tf); D = H.days(w)
    lo_ = np.datetime64(D[0] - pd.Timedelta(days=7)); hi_ = np.datetime64(D[-1])
    out = {}
    for name, mode in itertools.product(S.SETUPS, S.MODES):
        sig = [s for s in S.setup_signals(tf, name, mode) if lo_ <= B.dates[s[0]] <= hi_]
        for tp, sl in itertools.product((3, 5, 8, 10), (15, 25, 35, 50)):
            T = S.simulate(B, sig, tp, sl, scale=(tf != 'M5'))
            x = H.per_day(T, w); c = bd + x
            out[(name, mode, tp, sl)] = (x.mean(), len(H.in_window(T, w)) / len(D), c.mean(), dd(c.cumsum()),
                                         dd(bm + H.mtm_daily(T, w)))
    for j, k in enumerate(('alone', 'trades', 'comb', 'comb_dd', 'comb_dd_mtm')):
        G[f'{w}_{k}'] = [round(out[(r.setup, r.mode, r.tp, r.sl)][j], 3) for r in G.itertuples()]
G.to_csv(OUT + 'grid_all_windows.csv', index=False)
print('share positive alone: train %.0f%%, m15_test %.0f%%, pair %.0f%%' % tuple(
    (G[c] > 0).mean() * 100 for c in ('alone_per_day', 'm15_test_alone', 'pair_alone')))
print('rank corr train vs m15_test %.2f, train vs pair %.2f, m15_test vs pair %.2f' % (
    G.alone_per_day.corr(G.m15_test_alone, 'spearman'), G.alone_per_day.corr(G.pair_alone, 'spearman'),
    G.m15_test_alone.corr(G.pair_alone, 'spearman')))
tp_ = G[G.alone_per_day > 0]
print(f'{len(tp_)} train-positive versions: positive on m15_test {(tp_.m15_test_alone > 0).sum()}, on pair {(tp_.pair_alone > 0).sum()}, on both {((tp_.m15_test_alone > 0) & (tp_.pair_alone > 0)).sum()}')
print('by mode, mean alone $/day (train, m15_test, pair):')
print(G.groupby('mode')[['alone_per_day', 'm15_test_alone', 'pair_alone']].mean().round(2).to_string())
A = (G.pair_comb >= 4.66) & (G.pair_trades >= 0.30) & (G.pair_comb_dd >= -294) & (G.pair_comb_dd_mtm >= -255)
Bm = (G.m15_test_comb >= 4.06) & (G.m15_test_comb_dd >= -308) & (G.m15_test_comb_dd_mtm >= -417)
print(f'hindsight: versions meeting (a) {A.sum()}, (b) {Bm.sum()}, both {(A & Bm).sum()}, both + positive on train {(A & Bm & (G.alone_per_day > 0)).sum()}')
cols = ['setup', 'mode', 'tp', 'sl', 'alone_per_day', 'm15_test_alone', 'pair_alone', 'pair_trades', 'pair_comb', 'pair_comb_dd', 'pair_comb_dd_mtm', 'm15_test_comb_dd', 'm15_test_comb_dd_mtm']
print('versions meeting (a) and (b):'); print(G[A & Bm][cols].to_string(index=False))
print('top 8 by m15_test + pair alone (hindsight):')
print(G.assign(s=G.m15_test_alone + G.pair_alone).sort_values('s', ascending=False)[cols].head(8).to_string(index=False))
