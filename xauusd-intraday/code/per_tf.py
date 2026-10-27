"""Part 1: each timeframe on its own. Pick the best rule on the training years
(by Sharpe), then score every rule on the unseen test years."""
import pandas as pd, numpy as np, json
from lib import *

SPLIT = {'M5': '2026-01-01', 'M15': '2024-07-01', 'M30': '2024-07-01', 'H1': '2024-07-01', 'H4': '2024-07-01'}
COMMON = '2026-01-01'
rows, picks, positions = [], {}, {}
for tf in ['M5', 'M15', 'M30', 'H1', 'H4']:
    d = load(tf); sp = SPLIT[tf]
    bh, _, _ = backtest(d, pd.Series(1.0, index=d.index))
    for name, f in grid() + [('buy and hold', lambda d: pd.Series(1.0, index=d.index))]:
        p = f(d).fillna(0)
        dl, tr, ex = backtest(d, p)
        n_tr = (p.diff().abs() > 0)
        def part(a, b=None):
            m = (dl.index >= a) & ((dl.index < b) if b else True)
            pm = (d.index >= a) & ((d.index < b) if b else True)
            return stats(dl[m], (p[pm].diff().abs().sum()) / 2, p[pm].abs().mean())
        tr_s, te_s, cm_s = part(d.index[0].strftime('%Y-%m-%d'), sp), part(sp), part(COMMON)
        rows.append(dict(tf=tf, rule=name, **{'train_' + k: v for k, v in tr_s.items()},
                         **{'test_' + k: v for k, v in te_s.items()}, common_sharpe=cm_s['sharpe'], common_ret=cm_s['ret_yr']))
        positions[(tf, name)] = p
r = pd.DataFrame(rows)
r.to_csv('/mnt/project-files/xauusd-intraday/per_tf_all.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
fmt = r.copy()
for tf in r.tf.unique():
    s = r[(r.tf == tf) & (r.rule != 'buy and hold')]
    best = s.loc[s.train_sharpe.idxmax()]
    picks[tf] = best.rule
    rank = (s.test_sharpe.rank(ascending=False)[best.name])
    bhr = r[(r.tf == tf) & (r.rule == 'buy and hold')].iloc[0]
    print(f"\n== {tf} (test from {SPLIT[tf]}) ==  train pick: {best.rule}")
    print(f"  train Sharpe {best.train_sharpe:.2f} ret {best.train_ret_yr:.1%} | TEST Sharpe {best.test_sharpe:.2f} ret {best.test_ret_yr:.1%} dd {best.test_max_dd:.1%} trades/yr {best.test_trades_yr:.0f} | rank in test {rank:.0f}/{len(s)}")
    print(f"  buy&hold TEST Sharpe {bhr.test_sharpe:.2f} ret {bhr.test_ret_yr:.1%} dd {bhr.test_max_dd:.1%}")
    print(f"  rules with test Sharpe > buy&hold: {(s.test_sharpe > bhr.test_sharpe).sum()}/{len(s)};  train-test Sharpe corr {s.train_sharpe.corr(s.test_sharpe):.2f}")
    print(s.sort_values('test_sharpe', ascending=False)[['rule', 'train_sharpe', 'test_sharpe', 'test_ret_yr', 'test_max_dd', 'test_trades_yr']].head(6).to_string(index=False, float_format=lambda x: f'{x:.2f}'))
json.dump(picks, open('/mnt/project-files/xauusd-intraday/per_tf_picks.json', 'w'), indent=1)
