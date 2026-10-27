"""Independent reimplementation of the 'golden-cross long core' (D1 SMA50 > SMA200, 0.01 lot, long or flat).
Written from the candidate's written rules only (no code reused from long-core/).

Two independent engines:
  A) gbt.simulate (shared project engine) -> trade list, booked by exit date
  B) my own explicit mark-to-market loop (no gbt simulator), D1 bars
Costs: buy at ask = open + $0.30 spread + $0.10 slip, sell at bid open - $0.10 slip,
swap $0.126 per night (triple Wednesday), fixed from 2016; for pre-2016 I scale it to 1.10%/yr of price.
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
import gbt

OUT = '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-long-core/'
d = gbt.load('D1').copy()
c = d.close
f, s = c.rolling(50).mean(), c.rolling(200).mean()
up = (f > s) & s.notna()           # decided at the close of bar i
dn = (f <= s) & s.notna()

# ---------- A) gbt.simulate ----------
tA = gbt.simulate(d, up.astype(float).values, exit_long=dn.values)
tA['entry_time'] = tA.entry_time.dt.date; tA['exit_time'] = tA.exit_time.dt.date
print('A) gbt.simulate trades (booked by exit):')
print(tA[['entry_time', 'entry', 'exit_time', 'exit', 'gross', 'swap', 'pnl']].round(2).to_string())

# ---------- B) own mark-to-market loop ----------
SPREAD, SLIP, SW = 0.30, 0.10, 0.126
o, cl = d.open.values, c.values
dow = d.index.dayofweek.values
n = len(d)
pos = np.zeros(n)        # position held at the CLOSE of bar i
pnl = np.zeros(n)        # MTM P&L booked on bar i (close-to-close, incl. fills and swap)
swp = np.zeros(n)
upv, dnv = up.values, dn.values
trades = []; cur = None
SW_SCALED = 0.011 / 365   # 1.10%/yr of price per night (pre-2016 option)
def swap_night(i, scaled):
    # night between bar i-1 and bar i; triple if bar i-1 was a Wednesday
    k = 3.0 if dow[i - 1] == 2 else 1.0
    if scaled and d.index[i].year < 2016:
        return k * SW_SCALED * cl[i - 1]
    return k * SW

def run(scaled):
    pos = np.zeros(n); pnl = np.zeros(n); trades = []; cur = None
    for i in range(1, n):
        p_prev = pos[i - 1]
        # decision from closed bar i-1, fill at open of bar i
        if p_prev == 0 and upv[i - 1]:
            ent = o[i] + SPREAD + SLIP
            pnl[i] += cl[i] - ent
            pos[i] = 1; cur = dict(entry_time=d.index[i].date(), entry=ent, swap=0.0)
        elif p_prev == 1 and dnv[i - 1]:
            sw = swap_night(i, scaled)          # held over the night into bar i
            ex = o[i] - SLIP
            pnl[i] += ex - cl[i - 1] - sw
            cur['swap'] += sw
            cur.update(exit_time=d.index[i].date(), exit=ex); cur['gross'] = ex - cur['entry']
            trades.append(cur); cur = None; pos[i] = 0
        elif p_prev == 1:
            sw = swap_night(i, scaled)
            pnl[i] += cl[i] - cl[i - 1] - sw
            cur['swap'] += sw
            pos[i] = 1
    if cur is not None:
        cur.update(exit_time=None, exit=np.nan, gross=cl[-1] - cur['entry'])
        trades.append(cur)
    t = pd.DataFrame(trades); t['pnl'] = t.gross - t.swap
    return pd.Series(pnl, index=d.index), pd.Series(pos, index=d.index), t

pB, posB, tB = run(scaled=False)
pBs, _, tBs = run(scaled=True)

# hold baseline: long from the first bar of each window (MTM with swap). Implemented as MTM close-to-close
hold_mtm = pd.Series(np.r_[0, np.diff(cl)], index=d.index)
hold_sw = pd.Series(np.r_[0, [3 * SW if dow[i - 1] == 2 else SW for i in range(1, n)]], index=d.index)
hold_sw_scaled = pd.Series(np.r_[0, [(3 if dow[i - 1] == 2 else 1) * (SW_SCALED * cl[i - 1] if d.index[i].year < 2016 else SW)
                                     for i in range(1, n)]], index=d.index)
hold = hold_mtm - hold_sw

# compare trade lists
m = tA.copy(); m['exit_time'] = m.exit_time.astype(str)
b = tB.copy(); b['exit_time'] = b.exit_time.astype(str)
print('\nB) own loop trades vs A:', len(tB), 'vs', len(tA))
mm = pd.merge(tA, tB, on='entry_time', how='outer', suffixes=('_A', '_B'))
mm['d_pnl'] = mm.pnl_B - mm.pnl_A
print(mm[['entry_time', 'entry_A', 'entry_B', 'exit_time_A', 'exit_time_B', 'swap_A', 'swap_B', 'pnl_A', 'pnl_B', 'd_pnl']].round(2).to_string())


def win(p, a, b_):
    x = p[(p.index >= a) & (p.index <= b_)]
    eq = x.cumsum(); dd = (eq - eq.cummax()).min()
    mo = x.groupby(x.index.to_period('M')).sum()
    return dict(per_day=round(x.mean(), 2), total=round(x.sum(), 0), max_dd=round(dd, 0), days=len(x),
                losing_months=f'{(mo < 0).sum()}/{len(mo)}', sharpe=round(x.mean() / x.std() * np.sqrt(252), 2))

rows = []
for lab, a, b_ in [('trainB 2016-07-29..2021-12', '2016-07-29', '2021-12-31'), ('test 2022-01..2026-10', '2022-01-01', '2026-10-31'),
                   ('common 2025-05..2026-10', '2025-05-01', '2026-10-31'), ('train 2016-07-01..2021-12', '2016-07-01', '2021-12-31')]:
    r = win(pB, a, b_); r['what'] = 'rule ' + lab; rows.append(r)
    r = win(hold, a, b_); r['what'] = 'hold ' + lab; rows.append(r)
S = pd.DataFrame(rows).set_index('what'); print('\nMTM summary (own loop):'); print(S.to_string())

yr = pd.DataFrame({'rule': pB.groupby(pB.index.year).mean(), 'hold': hold.groupby(hold.index.year).mean()}).round(2)
print('\nBy year $/day (from 2016-07-29 for 2016):')
y16 = pB[pB.index >= '2016-07-29']; h16 = hold[hold.index >= '2016-07-29']
yr2 = pd.DataFrame({'rule': y16.groupby(y16.index.year).mean(), 'hold': h16.groupby(h16.index.year).mean()}).round(2)
print(yr2.T.to_string())

# % of price per year, pre-2016 (scaled swap): yearly return on start-of-year close
pct = []
for y in range(2005, 2016):
    m_ = (d.index.year == y)
    p0 = cl[np.where(m_)[0][0] - 1]
    pct.append(dict(year=y, rule=round(100 * pBs[m_].sum() / p0, 1),
                    hold=round(100 * (hold_mtm - hold_sw_scaled)[m_].sum() / p0, 1)))
print('\nPre-2016 % of start-of-year price (scaled swap):'); print(pd.DataFrame(pct).set_index('year').T.to_string())

# in-market time and trades/yr
for lab, a, b_ in [('2005-2026', '2005-01-01', '2026-12-31'), ('2016-07..2021', '2016-07-29', '2021-12-31'), ('2022..2026', '2022-01-01', '2026-12-31')]:
    x = posB[(posB.index >= a) & (posB.index <= b_)]
    tt = tB[(pd.to_datetime(tB.entry_time) >= a) & (pd.to_datetime(tB.entry_time) <= b_)]
    print(f'{lab}: in market {x.mean()*100:.0f}%  entries {len(tt)}  per yr {len(tt)/((x.index[-1]-x.index[0]).days/365.25):.2f}')

print('\nLast state:', d.index[-1].date(), 'SMA50', round(f.iloc[-1], 1), 'SMA200', round(s.iloc[-1], 1), 'pos', posB.iloc[-1])
pB.rename('core_mtm').to_frame().assign(pos=posB, hold=hold).to_csv(OUT + 'core_daily_mtm.csv')
S.to_csv(OUT + 'summary.csv')
tB.to_csv(OUT + 'trades_own.csv', index=False)
