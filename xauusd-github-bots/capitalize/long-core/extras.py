"""CFD core vs unleveraged gold ETF; account equity / margin path with the pair; worst-start scenario."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/long-core')
from rules import *

on = golden(False)
t, p, held = run(on, swap='fixed')
th, ph, hh = hold(swap='fixed')
c = D1.close
# ---- swap vs ETF fee per 1 oz held, test window ----
w = window(c, TEST); nights = 0
dw = w.index.dayofweek
nights = sum(3 if dw[i - 1] == 2 else 1 for i in range(1, len(w)))
cfd_swap = nights * SWAP
print(f'TEST hold 1 oz: CFD swap paid ${cfd_swap:.0f} ({cfd_swap / len(w):.2f}/day); gold move ${w.iloc[-1] - w.iloc[0]:.0f}')
for fee in (0.0010, 0.0025, 0.0040):
    etf = (w * fee / 252).sum()
    print(f'   ETF {fee * 100:.2f}%/yr fee on 1 oz: ${etf:.0f} -> saves ${cfd_swap - etf:.0f} = ${(cfd_swap - etf) / len(w):.2f}/day')
print(f'   CFD swap today as % of price: {SWAP * 365 / c.iloc[-1] * 100:.2f}%/yr; in Jan 2022: {SWAP * 365 / w.iloc[0] * 100:.2f}%/yr')
# rule-on-ETF: same signal, no swap, fee 0.25% while held, 1 oz
tr_held = window(held, TEST)
fee_rule = (w[tr_held.values] * 0.0025 / 252).sum()
print(f'   golden-cross core, test: CFD swap ${t[t.exit_time >= TEST[0]].swap.sum():.0f} vs ETF fee ~${fee_rule:.0f}')
# ---- account path with the pair, common window ----
pp, a, b, days = pair_daily()
core = p.reindex(days).fillna(0.0)
eq = 3000 + (pp + core).cumsum()
px = c.reindex(days)
hd = held.reindex(days).fillna(False)
print('common window equity: start 3000, min', round(eq.min(), 0), 'on', eq.idxmin().date(), ' end', round(eq.iloc[-1], 0))
# worst start: begin the whole setup at the equity peak before the worst drawdown
x = (pp + core).cumsum(); peak_day = x[:x.sub(x.cummax()).idxmin()].idxmax(); trough = x.sub(x.cummax()).idxmin()
e_tr = 3000 + x[trough] - x[peak_day]
print('worst start (begin at', peak_day.date(), '): equity at trough', trough.date(), round(e_tr, 0))
for lev in (20, 30, 100):
    m3 = 3 * px[trough] / lev
    print(f'   1:{lev}: 0.03 lot margin ${m3:.0f}; margin level {e_tr / m3 * 100:.0f}%; after a further 5% drop on 0.03 lot: {(e_tr - 0.15 * px[trough]) / m3 * 100:.0f}%')
# same for hold-forever and for the fastest post-hoc rule (for context)
# ---- how often is the core long while GoldAllAgree is long ----
ev = pd.concat([pd.DataFrame({'t': a.entry_time, 'd': 1}), pd.DataFrame({'t': a.exit_time, 'd': -1})]).sort_values('t')
aa_on_days = set()
for _, r in a.iterrows():
    for dd_ in pd.date_range(r.entry_time.normalize(), r.exit_time.normalize()): aa_on_days.add(dd_)
both = sum(1 for d_ in days if d_ in aa_on_days and hd[d_])
print('days GoldAllAgree has a position:', len(aa_on_days & set(days)), ' of which the core is also long:', both)
# day of the worst core loss: what did the pair do
wd = p[held].idxmin(); print('worst core day', wd.date(), 'core', round(p[wd], 0), 'pair that day', round(pp.get(wd, 0), 0))
