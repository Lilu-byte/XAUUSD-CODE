"""Check the candidate's common-window and pair numbers (daily close basis, M5 trading days), and two
practical sensitivities: (1) a broker whose D1 chart has Sunday bars (6 bars a week) makes SMA50/200 cover fewer
weekdays -> proxy SMA42/167 on our 5-day bars; (2) neighbouring cross lengths (not a selection, only fragility).
Usage: python3 -I claims.py"""
import sys, io, contextlib
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-practical-long-core')
import numpy as np, pandas as pd
import gbt
with contextlib.redirect_stdout(io.StringIO()):
    from core_stress import sim, D1, w, dd, TEST, TRAIN_B

c = D1.close
a = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
b = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
days = pd.DatetimeIndex(np.unique(gbt.load('M5').index.normalize()))
pair = (a.groupby(a.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0.0)
        + b.groupby(b.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0))


def summary(x):
    eq = x.cumsum(); m = x.groupby(x.index.to_period('M')).sum()
    return f'$/day {x.mean():5.2f}  maxDD {(eq - eq.cummax()).min():6.0f}  losing months {(m < 0).sum()}/{len(m)}  worst month {m.min():5.0f}'


on = (c.rolling(50).mean() > c.rolling(200).mean()).values
p, held, t = sim(on); ph, _, _ = sim(np.ones(len(c), bool))
core = p.reindex(days).fillna(0.0); hold = ph.reindex(days).fillna(0.0)
core_real = t.groupby(t.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
print('=== Common window on M5 trading days (372), daily close MTM ===')
print('  pair              ', summary(pair))
print('  core              ', summary(core))
print('  core booked@exit  ', summary(core_real))
print('  pair + core       ', summary(pair + core))
print('  pair + hold 0.01  ', summary(pair + hold))
print('  corr(core, pair) daily', round(np.corrcoef(core, pair)[0, 1], 2))
print('  days >= $5 pair:', round((pair >= 5).mean() * 100), '%  pair+core:', round((pair + core >= 5).mean() * 100), '%')

print('\n=== Fragility of the cross lengths (test 2022-01..2026-10 $/day; train 2016-07..2021-12) ===')
rows = []
for f, s in ((42, 167), (45, 180), (50, 200), (55, 220), (50, 150), (50, 250), (40, 200), (60, 200)):
    o = (c.rolling(f).mean() > c.rolling(s).mean()).values
    pp, _, tt = sim(o)
    lbl = f'SMA{f}/{s}' + ('  (proxy: broker with Sunday D1 bars)' if f == 42 else '')
    r = dict(rule=f'SMA{f}/{s}', train=round(w(pp, TRAIN_B).mean(), 2), test=round(w(pp, TEST).mean(), 2),
             test_dd=round(dd(w(pp, TEST)), 0), trades_test=int((tt.exit_time >= TEST[0]).sum()))
    rows.append(r)
    print(f"  {lbl:46s} train {r['train']:5.2f}  test {r['test']:5.2f}  test DD {r['test_dd']:6.0f}  trades in test {r['trades_test']}")
print('  hold 0.01: train', round(w(ph, TRAIN_B).mean(), 2), ' test', round(w(ph, TEST).mean(), 2))
pd.DataFrame(rows).to_csv('/mnt/project-files/xauusd-github-bots/capitalize/verify-practical-long-core/cross_fragility.csv', index=False)

# how often would a live demo month show anything?
ent = t.entry_time[t.entry_time >= '2005-01-01']
gaps = ent.diff().dt.days.dropna()
print('\n=== Live verification ===')
print(f'  days between core entries since 2005: median {gaps.median():.0f}, max {gaps.max():.0f};'
      f' share of calendar months with an entry or exit: {pd.concat([t.entry_time, t.exit_time]).dt.to_period("M").nunique() / ((D1.index[-1] - pd.Timestamp("2005-04-01")).days / 30.44) * 100:.0f}%')
