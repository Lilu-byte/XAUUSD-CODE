"""Step 3: run the rule unchanged on a different data source: OANDA XAUUSD hourly (QuantConnect/Lean repo,
2006-03..2019-02, timestamps ~UTC), rebuilt into daily bars on the MT5 server-day convention
(day boundary = 17:00 New York = 00:00 server). Also the same SMA nudge grid there.
Usage: python3 -I oanda.py /path/to/xauusd.csv"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-overfit-long-core')
from vsim import *

src = sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/oanda-lean-vlc/x/xauusd.csv'
h = pd.read_csv(src, header=None, names=['t', 'bo', 'bh', 'bl', 'bc', 'v1', 'ao', 'ah', 'al', 'ac', 'v2'])
h.index = pd.to_datetime(h.t, format='%Y%m%d %H:%M')
srv = h.index.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None) + pd.Timedelta(hours=7)
h['day'] = srv.normalize()
h = h[h.day.dt.dayofweek < 5]
g = h.groupby('day')
od = pd.DataFrame({'open': g.bo.first(), 'high': g.bh.max(), 'low': g.bl.min(), 'close': g.bc.last(),
                   'ask_open': g.ao.first(), 'nh': g.bo.size()})
od = od[od.nh >= 12]   # drop thin holiday stubs
print('OANDA daily bars', od.index[0].date(), '..', od.index[-1].date(), len(od), '| median spread at open',
      round((od.ask_open - od.open).median(), 2), '| 2006 median', round((od.ask_open - od.open).loc['2006'].median(), 2))

D1 = gbt.load('D1')
j = od.join(D1[['close']].rename(columns={'close': 'mt5'}), how='inner')
print('overlap days with MT5 D1:', len(j), '| daily-return corr', round(j.close.pct_change().corr(j.mt5.pct_change()), 4),
      '| median |close diff| $', round((j.close - j.mt5).abs().median(), 2))

SC = 0.126 * 365 / 4100 * 100
W = {'2007-2015 (pre-project)': ('2007-01-01', '2015-12-31'), '2007-2012 bull': ('2007-01-01', '2012-12-31'),
     '2013-2015 bear': ('2013-01-01', '2015-12-31'), '2016-07..2019-02': ('2016-07-29', '2019-02-28'),
     'all 2007-03..2019-02': ('2007-01-01', '2019-02-28')}
c = od.close
ones = np.ones(len(od), bool)


def evalrule(on, swap_pct=SC, use_real_spread=False):
    sp = 0.30
    if use_real_spread:
        # real OANDA spread at the fill bar's open (median of the history if missing)
        sp = float((od.ask_open - od.open).median())
    p, held, t = mtm(on, od, 'scaled', swap_pct, spread=sp)
    return p, held, t


base = golden(c, 50, 200)
res = []
for sw_lbl, sw in (('swap 1.12%/yr', SC), ('swap 3%/yr', 3.0)):
    p, held, t = evalrule(base, sw); ph, _, _ = evalrule(ones, sw)
    for lbl, w in W.items():
        x, y = win(p, w), win(ph, w)
        rr, ry = (x / c.shift().reindex(x.index)), (y / c.shift().reindex(y.index))
        res.append(dict(swap=sw_lbl, window=lbl, rule_pd=round(x.mean(), 2), hold_pd=round(y.mean(), 2),
                        rule_ret=round(rr.mean() * 252 * 100, 1), hold_ret=round(ry.mean() * 252 * 100, 1),
                        rule_sh=round(rr.mean() / rr.std() * np.sqrt(252), 2), hold_sh=round(ry.mean() / ry.std() * np.sqrt(252), 2),
                        rule_dd=round((x.cumsum() - x.cumsum().cummax()).min(), 0), hold_dd=round((y.cumsum() - y.cumsum().cummax()).min(), 0),
                        inmkt=round(win(held, w).mean() * 100)))
r = pd.DataFrame(res); pd.set_option('display.width', 250)
print('\nSMA 50/200 golden cross on OANDA daily vs holding 1 oz ($ per day, %/yr, Sharpe, MTM drawdown):')
print(r.to_string(index=False))
r.to_csv(OUT + 'oanda_golden.csv', index=False)

p, held, t = evalrule(base); ph, _, _ = evalrule(ones)
yy = pd.DataFrame({'rule_%': (p / c.shift()).groupby(p.index.year).sum() * 100, 'hold_%': (ph / c.shift()).groupby(ph.index.year).sum() * 100}).loc[2007:].round(1)
print('\nby year % of price (swap 1.12%/yr):'); print(yy.T.to_string())
print('\ntrades on OANDA:'); print(t[['entry_time', 'entry', 'exit_time', 'exit', 'pnl']].round({'entry': 1, 'exit': 1, 'pnl': 1}).to_string(index=False))

# compare trade dates with MT5 D1 version (same rule)
pm, hm, tm = mtm(golden(D1.close, 50, 200), D1, 'scaled', SC)
both = tm[(tm.entry_time >= '2007-01-01') & (tm.entry_time <= '2019-02-28')][['entry_time', 'exit_time']]
print('\nMT5 D1 trades in same span (entry, exit):', [(str(a)[:10], str(b)[:10]) for a, b in both.values])
agree = (pd.Series(held.values, od.index).reindex(D1.index).loc['2007':'2019-02'] == hm.loc['2007':'2019-02']).mean()
print('days where OANDA and MT5 versions are in the same state:', round(agree * 100, 1), '%')

# nudge grid on OANDA
rows = []
for kind in ('sma', 'ema'):
    for f in (35, 40, 45, 50, 55, 60, 65):
        for s in (140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260):
            q, _, _ = evalrule(golden(c, f, s, kind))
            row = dict(kind=kind, fast=f, slow=s)
            for lbl, w in W.items():
                row[lbl] = round(win(q, w).mean() - win(ph, w).mean(), 3)
            rows.append(row)
G = pd.DataFrame(rows); G.to_csv(OUT + 'oanda_nudge_grid.csv', index=False)
print('\nOANDA nudge grid: excess $/day over holding 1 oz (swap 1.12%/yr), share of combos beating hold, median, min, max:')
for kind in ('sma', 'ema'):
    x = G[G.kind == kind]
    for lbl in W:
        print(f'  {kind} {lbl:24s} beats hold {(x[lbl] > 0).mean() * 100:4.0f}%  median {x[lbl].median():+.3f}  range {x[lbl].min():+.3f}..{x[lbl].max():+.3f}')
