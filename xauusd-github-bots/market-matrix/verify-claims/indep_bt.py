"""Independent backtest of the readings the claims lean on (own indicator code + own fill/cost loop).
Usage: python3 -I indep_bt.py   (writes indep_bt.json)
"""
import json, zipfile, sys
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/verify-claims')
from indep import load, truerange, pine_rma, pine_ema, OUT  # noqa: E402  (indep runs its checks on import; cheap)

SPREAD, SLIP, SWL, SWS = 0.30, 0.10, 0.126, 0.046


def bt(d, pos):
    """pos[i] decided at close of bar i, held from open of i+1. Returns per-bar pnl."""
    o, c = d.open.values, d.close.values
    day = d.index.normalize().values; dow = d.index.dayofweek.values
    early = d.index < pd.Timestamp('2016-01-01')
    n = len(c); pnl = np.zeros(n)
    pos = np.nan_to_num(np.asarray(pos, float)).astype(int)
    for t in range(1, n):
        q = pos[t - 1]; qp = pos[t - 2] if t >= 2 else 0
        if qp != 0 and day[t] != day[t - 1]:
            pnl[t] -= (3.0 if dow[t - 1] == 2 else 1.0) * (SWL if qp > 0 else SWS) * (c[t - 1] / 4100 if early[t] else 1.0)
        if qp != 0 and q != qp:
            pnl[t] += (o[t] - SLIP - c[t - 1]) if qp > 0 else -(o[t] + SPREAD + SLIP - c[t - 1])
        elif qp != 0:
            pnl[t] += qp * (c[t] - c[t - 1])
        if q != 0 and q != qp:
            pnl[t] += (c[t] - (o[t] + SPREAD + SLIP)) if q > 0 else ((o[t] - SLIP) - c[t])
    return pd.Series(pnl, d.index)


def metrics(pb, d, a, b):
    p = pb.groupby(pb.index.normalize()).sum().loc[a:b]
    px = d.close.groupby(d.index.normalize()).last().shift().reindex(p.index)
    r = p / px
    eq = p.cumsum()
    return dict(per_day=round(float(p.mean()), 2), sharpe=round(float(r.mean() / r.std() * np.sqrt(252)), 2),
                max_dd=round(float((eq - eq.cummax()).min()), 0), total=round(float(p.sum()), 0))


def state(el, xl, es, xs):
    out = np.zeros(len(el), int); cur = 0
    for i in range(len(el)):
        if cur == 1 and (xl[i] or es[i]): cur = 0
        elif cur == -1 and (xs[i] or el[i]): cur = 0
        if cur == 0: cur = 1 if el[i] else -1 if es[i] else 0
        out[i] = cur
    return out


def readings(d):
    C = d.close.values; H = d.high.values; L = d.low.values; cs = d.close
    s20, s50, s200 = (cs.rolling(n).mean().values for n in (20, 50, 200))
    R = {}
    R['MA stack 20/50/200'] = np.where((C > s20) & (s20 > s50) & (s50 > s200), 1, np.where((C < s20) & (s20 < s50) & (s50 < s200), -1, 0))
    macd = pine_ema(C, 12) - pine_ema(C, 26)
    R['MACD line sign'] = np.sign(np.nan_to_num(macd)).astype(int)
    tr = truerange(H, L, C)
    a = pine_rma(tr, 2000); a = np.where(np.isnan(a), pine_rma(tr, 200), a) * 2
    w = (cs - cs.shift()).abs() / cs.shift()
    mean = ((cs * w).rolling(50).sum() / w.rolling(50).sum()).values
    osc = pd.Series(100 * (C - mean) / a)
    up = ((osc > 100) & (osc.shift() <= 100)).values; dn = ((osc < -100) & (osc.shift() >= -100)).values
    R['Range Osc +/-100 breakout, exit at 0'] = state(up, (osc < 0).values, dn, (osc > 0).values)
    dd = cs.diff().values
    rsi = pd.Series(100 - 100 / (1 + pine_rma(np.nan_to_num(np.clip(dd, 0, None)), 14) / pine_rma(np.nan_to_num(np.clip(-dd, 0, None)), 14)))
    R['RSI 30/70 reversal, exit at 50'] = state(((rsi > 30) & (rsi.shift() <= 30)).values, (rsi > 50).values,
                                                ((rsi < 70) & (rsi.shift() >= 70)).values, (rsi < 50).values)
    R['Hold'] = np.ones(len(C), int)
    return R


out = {}
WIN = {'H4': [('MT5 train', '2014-09-01', '2021-12-31'), ('MT5 test', '2022-01-01', '2026-10-31')],
       'H1': [('MT5 train', '2017-06-01', '2021-12-31'), ('MT5 test', '2022-01-01', '2026-10-31')]}
for tf in ('H4', 'H1'):
    d = load(tf)
    R = readings(d)
    for name, pos in R.items():
        for mode in ('long only', 'long+short'):
            if name == 'Hold' and mode == 'long+short': continue
            ps = np.clip(pos, 0, 1) if mode == 'long only' else pos
            pb = bt(d, ps)
            for wn, a, b in WIN[tf]:
                out[f'{tf} | {name} | {mode} | {wn}'] = metrics(pb, d, a, b)

# OANDA 2007-2016 (same loading recipe as oanda_check.py, re-written)
ZIP = '/tmp/claude-0/portfolio-oanda/lean/Data/cfd/oanda/hour/xauusd.zip'
try:
    raw = pd.read_csv(zipfile.ZipFile(ZIP).open('xauusd.csv'), header=None, names=['t', 'o', 'h', 'l', 'c', 'v', 'ao', 'ah', 'al', 'ac', 'av'])
    utc = pd.to_datetime(raw.t, format='%Y%m%d %H:%M')
    ny = utc.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    off = np.where([x.dst() != pd.Timedelta(0) for x in ny], 3, 2)
    srv = utc + pd.to_timedelta(off, unit='h')
    h1 = pd.DataFrame({'open': raw.o.values, 'high': raw.h.values, 'low': raw.l.values, 'close': raw.c.values, 'vol': raw.v.values.astype(float)},
                      index=pd.DatetimeIndex(srv))
    h1 = h1[~h1.index.duplicated()].sort_index()
    h1 = h1[(h1.index < pd.Timestamp('2016-07-29')) & (h1.index.dayofweek < 5)]
    h4 = h1.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'vol': 'sum'}).dropna()
    out['oanda_vol_sum'] = float(h1.vol.sum())
    for tf, d in (('H4', h4), ('H1', h1)):
        R = readings(d)
        for name, pos in R.items():
            for mode in ('long only', 'long+short'):
                if name == 'Hold' and mode == 'long+short': continue
                ps = np.clip(pos, 0, 1) if mode == 'long only' else pos
                out[f'{tf} | {name} | {mode} | OANDA 2007-16'] = metrics(bt(d, ps), d, '2007-01-01', '2016-07-28')
except Exception as e:  # noqa
    out['oanda_error'] = repr(e)
json.dump(out, open(OUT + 'indep_bt.json', 'w'), indent=1)
for k, v in out.items():
    print(k, v)
