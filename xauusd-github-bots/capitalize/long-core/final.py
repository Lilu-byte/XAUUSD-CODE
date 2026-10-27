"""Score the rule picked on training (golden cross: SMA50 > SMA200 on D1 closes, long 0.01 lot, else flat)
ONCE on 2022-01..2026-10, with baselines (hold 0.01 lot incl. swap; the pair), the common window,
the pair combination, a random-timing test and a margin check. Usage: python3 -I final.py [rule_name]"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/long-core')
from rules import *

name = sys.argv[1] if len(sys.argv) > 1 else 'golden50_200'
R = catalog()
on = R[name]()
t, p, held = run(on, swap='fixed')
ts_, ps_, _ = run(on, swap='scaled')
th, ph, _ = hold(swap='fixed')
_, phs, _ = hold(swap='scaled')

def line(lbl, pp, tt=None, w=None):
    m = metr(pp)
    s = f"{lbl:34s} $/day {m['per_day']:6.2f}  maxDD(MTM) {m['max_dd']:7.0f}  ret/yr {m['ret_yr']:5.1f}%  Sharpe {m['sharpe']:5.2f}  losing months {m['losing_months']}"
    if tt is not None:
        x = tstats(tt, w); s += f"  trades {x['trades']}  win {x['win']}%"
    print(s)

print(f'=== {name} ===')
print('TRAIN A 2005-04..2015-12 (swap scaled to price):')
line('  rule', window(ps_, TRAIN_A), ts_, TRAIN_A); line('  hold 0.01', window(phs, TRAIN_A))
print('TRAIN B 2016-07..2021-12 (fixed $0.126 swap):')
line('  rule', window(p, TRAIN_B), t, TRAIN_B); line('  hold 0.01', window(ph, TRAIN_B))
print('TEST 2022-01..2026-10 (fixed swap) -- scored once:')
line('  rule', window(p, TEST), t, TEST); line('  hold 0.01', window(ph, TEST))
print('  test time in market', round(window(held, TEST).mean() * 100), '%')
by = p.loc['2016-07-29':].groupby(p.loc['2016-07-29':].index.year).mean().round(2)
byh = ph.loc['2016-07-29':].groupby(ph.loc['2016-07-29':].index.year).mean().round(2)
print('by year $/day rule:', by.to_dict()); print('by year $/day hold:', byh.to_dict())
byA = ps_.loc['2005-04-01':'2015-12-31']; byA = (byA / D1.close.shift().reindex(byA.index)).groupby(byA.index.year).sum().mul(100).round(1)
byAh = phs.loc['2005-04-01':'2015-12-31']; byAh = (byAh / D1.close.shift().reindex(byAh.index)).groupby(byAh.index.year).sum().mul(100).round(1)
print('2005-2015 by year % of price, rule:', byA.to_dict()); print('2005-2015 by year % of price, hold:', byAh.to_dict())
# swap paid
tt = t[(t.exit_time >= TEST[0])]
print('test-window swap paid on closed+open trades: $', round(tt.swap.sum(), 0), 'gross', round(tt.gross.sum(), 0))
print('all trades since 2016:'); print(t[t.exit_time >= '2016-01-01'][['entry_time', 'entry', 'exit_time', 'exit', 'gross', 'swap', 'pnl', 'open_at_end']].round(2).to_string(index=False))

# ---------- random timing: same number/length of on- and off-runs, shuffled ----------
def runs(x):
    x = np.asarray(x, bool); b = np.flatnonzero(np.diff(x.astype(int))) + 1
    seg = np.split(x, b); return [(s[0], len(s)) for s in seg]

def rand_timing(on, w, nrun=300, seed=7):
    idx = (D1.index >= w[0]) & (D1.index <= w[1])
    i0, i1 = np.flatnonzero(idx)[[0, -1]]
    seg = runs(on[i0:i1 + 1]); onl = [l for s, l in seg if s]; offl = [l for s, l in seg if not s]
    rng = np.random.default_rng(seed); res = []
    for _ in range(nrun):
        a = list(rng.permutation(onl)); b = list(rng.permutation(offl)); st = rng.random() < len(onl) / max(1, len(onl) + len(offl))
        z = []
        while a or b:
            if st and a: z += [True] * a.pop()
            elif not st and b: z += [False] * b.pop()
            elif a: z += [True] * a.pop()
            else: z += [False] * b.pop()
            st = not st
        x = on.copy(); x[i0:i1 + 1] = np.array(z, bool)
        _, pr, _ = run(x, swap='fixed'); res.append(window(pr, w).mean())
    return np.array(res)

base = window(p, TEST).mean()
rt = rand_timing(on, TEST)
print(f'random timing (test): rule beats {np.mean(rt < base) * 100:.0f}% of {len(rt)} shuffles; shuffles median $/day {np.median(rt):.2f}')
rtB = rand_timing(on, ('2005-04-01', '2021-12-31'))
baseB = window(p, ('2005-04-01', '2021-12-31')).mean()
print(f'random timing (2005-2021 train): rule beats {np.mean(rtB < baseB) * 100:.0f}%')

# ---------- common window and the pair ----------
pp, a, b, days = pair_daily()
core = p.reindex(days).fillna(0.0)        # MTM, D1 dates == M5 dates in server time
miss = set(days) - set(p.index); print('M5 days missing from D1:', len(miss))
core_real = t.groupby(t.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
hold_c = ph.reindex(days).fillna(0.0)

def show(lbl, x):
    eq = x.cumsum(); m = x.groupby(x.index.to_period('M')).sum()
    print(f'{lbl:40s} $/day {x.mean():6.2f}  maxDD {(eq - eq.cummax()).min():7.0f}  losing months {(m < 0).sum()}/{len(m)}  worst month {m.min():6.0f}')
    return dict(per_day=round(x.mean(), 2), max_dd=round((eq - eq.cummax()).min(), 0), losing=f'{(m < 0).sum()}/{len(m)}')

print('COMMON WINDOW May 2025..Oct 2026 (372 M5 trading days):')
r_core = show('  core alone (MTM)', core)
show('  core alone (realized at exit)', core_real)
show('  hold 0.01 alone (MTM)', hold_c)
r_pair = show('  pair alone', pp)
r_both = show('  pair + core (core MTM)', pp + core)
show('  pair + core (core realized at exit)', pp + core_real)
show('  pair + hold 0.01 (MTM)', pp + hold_c)
print('  corr(core MTM, pair) daily', round(np.corrcoef(core, pp)[0, 1], 2), ' weekly',
      round(np.corrcoef(core.resample('W').sum(), pp.resample('W').sum())[0, 1], 2))
print('  core in market on common window:', round(held.reindex(days).fillna(False).mean() * 100), '%')
mc = (pp + core).groupby(days.to_period('M')).sum().round(0); print('  monthly pair+core:', mc.to_dict())

# ---------- margin / open lots ----------
ev = []
for _, r in a.iterrows(): ev += [(r.entry_time, 1), (r.exit_time, -1)]
for _, r in b.iterrows(): ev += [(r.entry_time, 1), (r.exit_time, -1)]
ev.sort(key=lambda z: (z[0], z[1])); cur = 0; mx = 0; tm = None
for tt_, dlt in ev:
    cur += dlt
    if cur > mx: mx, tm = cur, tt_
print('pair max simultaneous positions:', mx, 'at', tm)
# times when pair has 2 open AND core is long that day
ov = [(tt_) for tt_, dlt in ev]
pos = pd.Series([z[1] for z in ev], index=[z[0] for z in ev]).groupby(level=0).sum().cumsum()
two = pos[pos >= 2]
core_on_day = held.reindex(two.index.normalize()).fillna(False).values
print('moments pair holds 2 positions:', len(two), ' of them with core long:', int(core_on_day.sum()))
for lev in (20, 100, 500):
    px = 4200; lots = 3; mrg = lots * px / lev; drop = 0.05 * px * lots
    print(f'  leverage 1:{lev}: margin for 0.03 lot ${mrg:.0f}; 5% drop costs ${drop:.0f}; margin level after drop {(3000 - drop) / mrg * 100:.0f}%')
# worst moves for the core while held
dd1 = p[held].min(); print('worst single day for the core (MTM): $', round(dd1, 0), 'on', p[held].idxmin().date())
w5 = p.rolling(5).sum()[held].min(); print('worst 5-day stretch for the core: $', round(w5, 0))

# ---------- small summary files ----------
summ = []
for lbl, pp_, w in (('rule_trainB', p, TRAIN_B), ('hold_trainB', ph, TRAIN_B), ('rule_test', p, TEST), ('hold_test', ph, TEST)):
    m = metr(window(pp_, w)); m['what'] = lbl; summ.append(m)
summ.append(dict(what='common_core_mtm', **r_core)); summ.append(dict(what='common_pair', **r_pair)); summ.append(dict(what='common_pair_plus_core', **r_both))
pd.DataFrame(summ).to_csv(OUT + f'final_summary_{name}.csv', index=False)
pd.DataFrame({'rule': by, 'hold': byh}).to_csv(OUT + f'final_by_year_{name}.csv')
t.to_csv(OUT + f'final_trades_{name}.csv', index=False)
print('saved summary, by-year and trade list for', name)
