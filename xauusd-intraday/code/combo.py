"""Part 2 (all timeframes together) and Part 3 (merge of Part 1 and Part 2).

Two base timelines:
  * M5 timeline, 2025-05 to 2026-10, uses all five timeframes; test = 2026.
  * M15 timeline, 2022-07 to 2026-10, uses M15/M30/H1/H4 (no M5 history that far); test = from 2024-07.
Higher-timeframe values are only used once their bar has closed.
"""
import json, sys, pandas as pd, numpy as np
import lib
from lib import *

COSTX = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0   # cost stress multiplier
lib.SLIP *= COSTX
picks = json.load(open('/mnt/project-files/xauusd-intraday/per_tf_picks.json'))
G = dict(grid())
TFS = ['M5', 'M15', 'M30', 'H1', 'H4']
data = {tf: load(tf) for tf in TFS}


def run(base, tfs, split):
    b = data[base].copy(); b['spread'] *= COSTX
    bc = b.index + pd.Timedelta(minutes=MIN[base])        # base bar close times
    trend = {}; pick = {}
    for tf in tfs:
        d = data[tf]
        trend[tf] = align(d, tf, bc, s_cross(d, 20, 80).values).fillna(0).values
        pick[tf] = align(d, tf, bc, G[picks[tf]](d).fillna(0).values).fillna(0).values
    T = np.vstack([trend[t] for t in tfs]); P = np.vstack([pick[t] for t in tfs])
    vote = T.mean(0)
    up_all, dn_all = (T > 0).all(0), (T < 0).all(0)
    S = lambda a: pd.Series(np.asarray(a, float), index=b.index)
    # top-down pullback: H4 and H1 up-trend, base timeframe dips below its 20-bar mean by 1.5 sd
    z = (b.close - b.close.rolling(20).mean()) / b.close.rolling(20).std()
    bias_up = S((trend['H4'] > 0) & (trend['H1'] > 0)).astype(bool)
    pull = hold(bias_up & (z < -1.5), (~bias_up) | (z > 1.0), S(np.zeros(len(b))).astype(bool), S(np.zeros(len(b))).astype(bool))
    pull_trend = hold(bias_up & (z < -1.5), ~bias_up, S(np.zeros(len(b))).astype(bool), S(np.zeros(len(b))).astype(bool))
    ens = P.mean(0)
    strategies = {
        'COMBINED: all timeframes agree (long+short)': S(up_all.astype(int) - dn_all.astype(int)),
        'COMBINED: all timeframes agree up (long only)': S(up_all),
        'COMBINED: vote-weighted, long only': S(np.clip(vote, 0, 1)),
        'COMBINED: H4+H1 trend, dip entry, exit on bounce': pull,
        'COMBINED: H4+H1 trend, dip entry, exit on trend end': pull_trend,
        'MERGE: average of single-timeframe picks': S(ens),
        'MERGE: majority (3+ of picks long), one lot': S(P.sum(0) >= (len(tfs) // 2 + 1)),
        'MERGE: picks average, only when all timeframes agree up': S(ens * up_all),
        'MERGE: 50/50 picks average + all-agree-up': S(0.5 * ens + 0.5 * up_all),
    }
    for tf in tfs: strategies[f'single {tf}: {picks[tf]}'] = S(pick[tf])
    strategies['buy and hold'] = S(np.ones(len(b)))
    strategies['buy and hold at 0.6x'] = S(np.full(len(b), 0.6))
    rows = []
    for name, p in strategies.items():
        dl, _, _ = backtest(b, p)
        for per, a, e in (('train', b.index[0], split), ('test', split, None)):
            m = (dl.index >= a) & ((dl.index < e) if e is not None else True)
            pm = (b.index >= a) & ((b.index < e) if e is not None else True)
            st = stats(dl[m], p[pm].diff().abs().sum() / 2, p[pm].abs().mean())
            rows.append(dict(strategy=name, period=per, **st))
    r = pd.DataFrame(rows).pivot(index='strategy', columns='period')
    r.columns = [f'{b_}_{a_}' for a_, b_ in r.columns]
    r = r[['train_sharpe', 'train_ret_yr', 'test_sharpe', 'test_ret_yr', 'test_max_dd', 'test_trades_yr', 'test_exposure']]
    return r.reindex(list(strategies))


pd.set_option('display.width', 250)
f = lambda x: f'{x:.2f}'
for base, tfs, split in (('M15', ['M15', 'M30', 'H1', 'H4'], '2024-07-01'), ('M5', TFS, '2026-01-01')):
    r = run(base, tfs, split)
    tag = f'{base}_x{COSTX:g}'
    r.to_csv(f'/mnt/project-files/xauusd-intraday/combo_{tag}.csv')
    print(f'\n===== base {base}, timeframes {tfs}, test from {split}, costs x{COSTX:g} =====')
    print(r.to_string(float_format=f))
