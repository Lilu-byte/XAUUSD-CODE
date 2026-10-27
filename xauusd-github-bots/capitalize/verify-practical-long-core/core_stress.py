"""Adversarial check (live practicality) of the golden-cross long core.
Own D1 mark-to-market simulator (not the candidate's code). Rule: at a D1 close, want long if SMA50 > SMA200;
act at the next D1 open. 0.01 lot = 1 oz = $1 per $1.
Costs stressed: entry spread/slippage (rollover fills), exit slippage, swap level ($ fixed multiples,
% of price per year, and an approximate Fed-funds + markup financing path), fill at 02:00 server (H1 open)
instead of the D1 open. Also: profit concentration (best trades / best year) and sample size.
Usage: python3 -I core_stress.py
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
import gbt

OUT = '/mnt/project-files/xauusd-github-bots/capitalize/verify-practical-long-core/'
D1 = gbt.load('D1'); H1 = gbt.load('H1')
c = D1.close
TRAIN_B = ('2016-07-29', '2021-12-31'); TEST = ('2022-01-01', '2026-10-31'); COMMON = ('2025-05-01', '2026-10-31')

# approximate effective Fed funds by month (my own table; 2026 assumed flat at the Dec-2025 level)
FF = {}
def _ff(y, vals):
    for mth, v in enumerate(vals, 1): FF[(y, mth)] = v
_ff(2016, [0.34, 0.38, 0.36, 0.37, 0.37, 0.38, 0.39, 0.40, 0.40, 0.40, 0.41, 0.54])
_ff(2017, [0.65, 0.66, 0.79, 0.90, 0.91, 1.04, 1.15, 1.16, 1.15, 1.15, 1.16, 1.30])
_ff(2018, [1.41, 1.42, 1.51, 1.69, 1.70, 1.82, 1.91, 1.91, 1.95, 2.19, 2.20, 2.27])
_ff(2019, [2.40, 2.40, 2.41, 2.42, 2.38, 2.38, 2.40, 2.13, 2.04, 1.83, 1.55, 1.55])
_ff(2020, [1.55, 1.58, 0.65, 0.05, 0.05, 0.08, 0.09, 0.10, 0.09, 0.09, 0.09, 0.09])
_ff(2021, [0.09, 0.08, 0.07, 0.07, 0.06, 0.08, 0.10, 0.09, 0.08, 0.08, 0.08, 0.08])
_ff(2022, [0.08, 0.08, 0.20, 0.33, 0.77, 1.21, 1.68, 2.33, 2.56, 3.08, 3.78, 4.10])
_ff(2023, [4.33, 4.57, 4.65, 4.83, 5.06, 5.08, 5.12, 5.33, 5.33, 5.33, 5.33, 5.33])
_ff(2024, [5.33] * 8 + [5.13, 4.83, 4.64, 4.48])
_ff(2025, [4.33] * 8 + [4.22, 4.09, 3.88, 3.72])
_ff(2026, [3.64] * 12)


def sim(on, d=D1, spread=0.30, slip_in=0.10, slip_out=0.10, swap=0.126, swap_mode='fixed', fill=None):
    """on[i]: desired state decided at close of bar i (acts at bar i+1 open).
    swap_mode 'fixed' ($/night), 'pct' (swap = %/yr of prior close, 365-day), 'ff' (Fed funds + swap %/yr markup).
    fill: optional array of fill prices per bar to use instead of the bar open (bid).
    Returns daily MTM P&L Series, held mask, trades DataFrame."""
    o = d.open.values if fill is None else fill
    cl = d.close.values; n = len(d); dow = d.index.dayofweek.values
    ym = list(zip(d.index.year, d.index.month))
    pnl = np.zeros(n); held = np.zeros(n, bool); tr = []
    pos = False; ent = 0.0; ei = 0; sw = 0.0; mae = 0.0
    for i in range(1, n):
        want = on[i - 1]
        if pos:
            k = 3.0 if dow[i - 1] == 2 else 1.0
            if swap_mode == 'fixed': s = swap
            elif swap_mode == 'pct': s = cl[i - 1] * swap / 100 / 365
            else: s = cl[i - 1] * (FF.get(ym[i - 1], 0.0) + swap) / 100 / 365
            pnl[i] -= k * s; sw += k * s
            if not want:
                px = o[i] - slip_out
                # if filling later than the open (e.g. 02:00), the move open->fill belongs to this day too
                pnl[i] += px - cl[i - 1]
                tr.append((d.index[ei], ent, d.index[i], px, px - ent, sw, mae)); pos = False
            else:
                pnl[i] += cl[i] - cl[i - 1]; held[i] = True
                mae = min(mae, D1.low.values[i] - ent if d is D1 else 0)
        elif want:
            ent = o[i] + spread + slip_in; ei = i; pos = True; sw = 0.0
            pnl[i] += cl[i] - ent; held[i] = True; mae = min(0.0, d.low.values[i] - ent)
    if pos:
        tr.append((d.index[ei], ent, d.index[n - 1], cl[n - 1], cl[n - 1] - ent, sw, mae))
    t = pd.DataFrame(tr, columns=['entry_time', 'entry', 'exit_time', 'exit', 'gross', 'swap', 'mae'])
    t['pnl'] = t.gross - t.swap
    return pd.Series(pnl, index=d.index), pd.Series(held, index=d.index), t


def w(s, win): return s.loc[win[0]:win[1]]
def dd(s): e = s.cumsum(); return (e - e.cummax()).min()


on = (c.rolling(50).mean() > c.rolling(200).mean()).values
hold_on = np.ones(len(c), bool)

p, held, t = sim(on)
ph, _, _ = sim(hold_on)
print('=== Reproduction (own simulator, base costs: spread 0.30 + slip 0.10, swap $0.126/night) ===')
for lbl, win in (('train 2016-07..2021-12', TRAIN_B), ('TEST 2022-01..2026-10', TEST), ('common 2025-05..2026-10', COMMON)):
    print(f'  {lbl:26s} rule $/day {w(p, win).mean():6.2f} maxDD {dd(w(p, win)):7.0f} | hold $/day {w(ph, win).mean():6.2f} maxDD {dd(w(ph, win)):7.0f}')
yr = p.loc['2016-07-29':].groupby(p.loc['2016-07-29':].index.year).mean().round(2)
yh = ph.loc['2016-07-29':].groupby(ph.loc['2016-07-29':].index.year).mean().round(2)
print('  by year rule:', yr.to_dict()); print('  by year hold:', yh.to_dict())
print('  current state on last bar', D1.index[-1].date(), 'want long =', bool(on[-1]),
      ' SMA50', round(c.rolling(50).mean().iloc[-1], 0), 'SMA200', round(c.rolling(200).mean().iloc[-1], 0))

# ---------- sample size ----------
print('\n=== Sample size ===')
tt = t[t.entry_time >= '2005-01-01']
yrs = (D1.index[-1] - pd.Timestamp('2005-04-01')).days / 365.25
print(f'  round trips 2005-04..2026-10: {len(tt)} in {yrs:.1f} yrs = {len(tt) / yrs:.2f}/yr; '
      f'winners {(tt.pnl > 0).sum()}, losers {(tt.pnl <= 0).sum()}')
tw = t[(t.exit_time >= TEST[0])]
print(f'  trades touching the test window: {len(tw)} (one of them opened in Dec 2021); trades opened in test: {(t.entry_time >= TEST[0]).sum()}')
print(tw[['entry_time', 'entry', 'exit_time', 'exit', 'gross', 'swap', 'pnl', 'mae']].round({'entry': 1, 'exit': 1, 'gross': 1, 'swap': 1, 'pnl': 1, 'mae': 1}).to_string(index=False))
print('  worst adverse excursion from entry, any trade since 2005 (MAE, $/oz, D1 lows):', round(tt.mae.min(), 0),
      ' on trade entered', tt.loc[tt.mae.idxmin(), 'entry_time'].date())
print('  worst closed trade since 2005: $', round(tt.pnl.min(), 0))

# ---------- concentration of test profit ----------
print('\n=== Where the test profit comes from (MTM, 2022-01..2026-10) ===')
pt = w(p, TEST); tot = pt.sum()
# MTM profit attributed to each trade inside the test window
attr = []
for _, r in t.iterrows():
    a_ = pt.loc[max(r.entry_time, pd.Timestamp(TEST[0])):r.exit_time].sum() if r.exit_time >= pd.Timestamp(TEST[0]) else 0.0
    if r.exit_time >= pd.Timestamp(TEST[0]): attr.append((r.entry_time.date(), r.exit_time.date(), round(a_, 0)))
attr = sorted(attr, key=lambda z: -z[2])
print(f'  total test MTM P&L ${tot:.0f} over {len(pt)} days')
for a_ in attr: print(f'    trade {a_[0]} -> {a_[1]}: ${a_[2]:.0f}  = {a_[2] / tot * 100:.0f}% of the total')
best5 = sum(z[2] for z in attr[:5])
print(f'  best 5 trades (there are only {len(attr)}): ${best5:.0f} = {best5 / tot * 100:.0f}% of total; best 1: {attr[0][2] / tot * 100:.0f}%')
yt = pt.groupby(pt.index.year).sum().round(0)
print('  test $ by year:', yt.to_dict(), f' best year {yt.idxmax()} = {yt.max() / tot * 100:.0f}% of total;',
      f'test without {yt.idxmax()}: ${tot - yt.max():.0f} = {(tot - yt.max()) / (len(pt) - (pt.index.year == yt.idxmax()).sum()):.2f}/day')
# monthly bootstrap CI of test $/day
m = pt.groupby(pt.index.to_period('M')).agg(['sum', 'count'])
rng = np.random.default_rng(3); bs = []
for _ in range(5000):
    k = rng.integers(0, len(m), len(m)); bs.append(m['sum'].values[k].sum() / m['count'].values[k].sum())
bs = np.array(bs)
print(f'  monthly-bootstrap 90% interval for test $/day: {np.percentile(bs, 5):.2f} .. {np.percentile(bs, 95):.2f};  P($/day <= 0) = {np.mean(bs <= 0) * 100:.0f}%')
dif = pt - w(ph, TEST); md = dif.groupby(dif.index.to_period('M')).sum()
tstat = md.mean() / md.std() * np.sqrt(len(md))
print(f'  rule minus hold, test: ${dif.mean():.2f}/day, monthly t-stat {tstat:.2f}')

# ---------- cost stress ----------
print('\n=== Cost stress, TEST 2022-01..2026-10 $/day (rule | hold) ===')
rows = []
def case(lbl, **kw):
    pr, _, tr_ = sim(on, **kw); phh, _, _ = sim(hold_on, **kw)
    r = dict(case=lbl, rule_test=round(w(pr, TEST).mean(), 2), hold_test=round(w(phh, TEST).mean(), 2),
             rule_trainB=round(w(pr, TRAIN_B).mean(), 2), rule_common=round(w(pr, COMMON).mean(), 2),
             rule_test_dd=round(dd(w(pr, TEST)), 0), swap_paid_test=round(tr_[tr_.exit_time >= TEST[0]].swap.sum(), 0))
    rows.append(r)
    print(f"  {lbl:44s} rule {r['rule_test']:5.2f} | hold {r['hold_test']:5.2f}   (train {r['rule_trainB']:5.2f}, common {r['rule_common']:5.2f}, test DD {r['rule_test_dd']:6.0f}, swap paid {r['swap_paid_test']:4.0f})")
case('base (0.30+0.10, $0.126)')
case('spread 0.60 + slip 0.30 both sides', spread=0.60, slip_in=0.30, slip_out=0.30)
case('spread 1.00 + slip 0.50 both sides', spread=1.00, slip_in=0.50, slip_out=0.50)
case('rollover fill: spread 5.00 + slip 2.00 both', spread=5.00, slip_in=2.00, slip_out=2.00)
case('swap x2 ($0.252)', swap=0.252)
case('swap x3 ($0.378)', swap=0.378)
case('swap 2.5%/yr of price', swap=2.5, swap_mode='pct')
case('swap 4%/yr of price', swap=4.0, swap_mode='pct')
case('swap Fed funds + 1.5%/yr (approx path)', swap=1.5, swap_mode='ff')
case('swap Fed funds + 2.5%/yr (approx path)', swap=2.5, swap_mode='ff')
case('worst combo: spread 1+slip 0.5, FF+2.5%', spread=1.00, slip_in=0.50, slip_out=0.50, swap=2.5, swap_mode='ff')
# break-even swap
for s in np.arange(0.2, 3.01, 0.05):
    pr, _, _ = sim(on, swap=s)
    if w(pr, TEST).mean() <= 0:
        print(f'  break-even fixed swap for the test: about ${s:.2f}/night per 0.01 lot ({s / 0.126:.1f}x today)'); break
else:
    print('  test stays positive up to $3.00/night swap')

# ---------- fill at 02:00 server (H1 bar open) instead of the D1 open ----------
f2 = np.full(len(D1), np.nan)
hidx = H1.index
for i, day in enumerate(D1.index):
    if day < hidx[0]: continue
    j = hidx.searchsorted(day + pd.Timedelta(hours=2))
    if j < len(hidx) and hidx[j].normalize() == day: f2[i] = H1.open.values[j]
fill = np.where(np.isnan(f2), D1.open.values, f2)
case('fill at 02:00 server H1 open (base costs)', fill=fill)
pd.DataFrame(rows).to_csv(OUT + 'cost_stress.csv', index=False)
print('saved cost_stress.csv')
