"""Long-history check of the 'all timeframes agree up' idea with the timeframes that
exist that far back: H1 + H4 (+ D1). OANDA hourly 2006-03..2019-02 (Lean repo,
fetched to /tmp/claude-0/oanda/xauusd.csv) and MT5 H1 2016-07..2026-10.
Nothing here was tuned: EMA20/80 on every timeframe, as in combo.py."""
import pandas as pd, numpy as np
from lib import *


def oanda_h1():
    d = pd.read_csv('/tmp/claude-0/oanda/xauusd.csv', header=None)
    d.index = pd.to_datetime(d[0], format='%Y%m%d %H:%M')
    return pd.DataFrame({'open': (d[1] + d[6]) / 2, 'high': (d[2] + d[7]) / 2, 'low': (d[3] + d[8]) / 2,
                         'close': (d[4] + d[9]) / 2, 'spread': (d[9] - d[4]) / 0.01})


def rs(d, rule):
    g = d.resample(rule, label='left', closed='left')
    return pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(),
                         'close': g.close.last(), 'spread': g.spread.mean()}).dropna()


def evaluate(label, h1, h4, d1):
    bc = h1.index + pd.Timedelta(minutes=60)
    t1 = s_cross(h1, 20, 80).values
    t4 = align(h4, 'H4', bc, s_cross(h4, 20, 80).values).fillna(0).values
    td = align(d1, 'D1', bc, s_cross(d1, 20, 80).values).fillna(0).values
    S = lambda a: pd.Series(np.asarray(a, float), index=h1.index)
    strat = {'H1+H4 agree up': S((t1 > 0) & (t4 > 0)),
             'H1+H4+D1 agree up': S((t1 > 0) & (t4 > 0) & (td > 0)),
             'H4 trend alone': S(t4 > 0),
             'H1 trend alone': S(t1 > 0),
             'buy and hold': S(np.ones(len(h1)))}
    out = []
    for n, p in strat.items():
        dl, tr, ex = backtest(h1, p)
        st = stats(dl, tr, ex)
        yr = dl.groupby(dl.index.year).sum()
        out.append(dict(test=label, rule=n, **st, losing_years=f'{(yr < 0).sum()}/{len(yr)}'))
    return out


rows = []
o = oanda_h1()
rows += evaluate('OANDA 2006-2019', o, rs(o, '4h'), rs(o, '1D'))
h1, h4, d1 = load('H1'), load('H4'), load('D1')
rows += evaluate('MT5 2016-2026', h1, h4, d1)
rows += evaluate('MT5 2016-2024 (before test)', h1[:'2024-06-30'], h4[:'2024-06-30'], d1[:'2024-06-30'])
r = pd.DataFrame(rows)
pd.set_option('display.width', 200)
print(r.to_string(index=False, float_format=lambda x: f'{x:.2f}'))
r.to_csv('/mnt/project-files/xauusd-intraday/long_history.csv', index=False)
