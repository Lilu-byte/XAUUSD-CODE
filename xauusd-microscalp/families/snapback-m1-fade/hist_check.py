"""Long-history check of the effect on data the M1 work never touched: M5 bars 2025-05-05..2026-06-25 and M15 bars
2022-07-08..2025-05-04 (plus the M1 period itself for comparison). There are no M1 bars before 2026-06-26, so the M1
picks cannot be replayed; these are ANALOG rules on M5/M15 bars, fixed before running (no tuning on these periods):
  SNAP : fade a 1-bar move |close[i]-close[i-1]| > k x mean(high-low, last 240 minutes of bars), no gate,
         time exit after 1-2 bars, max 2 open, $25 disaster stop                                    (analog of P1)
  TOWARD: same move but only when it runs toward the session VWAP from the other side (fade = trade back to the
         VWAP side), time exit after 15 minutes (3 M5 bars / 1 M15 bar), max 3 open, $25 stop          (analog of P2)
Entry at the next bar open (EA rule: next bar directly follows, spread filter off because the M5/M15 recorded
spread is the bar minimum and often 0-4 points). Costs: flat $0.20 and flat $0.30 per trade (recorded M5/M15
spreads are too optimistic to use). FAIR fills (irrelevant for pure time exits)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *

FILES = {'M5': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv', 'M15': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv'}


def load_bars(tf):
    d = pd.read_csv(FILES[tf]); d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    d = d[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    d = d[d.index.dayofweek < 5]
    d['spread_usd'] = 0.20
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=30)) | nxt.isna()
    return d


def bar_filter(m, s, secs):
    s = np.sign(np.nan_to_num(np.asarray(s, float)))
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    return np.where(gap == secs, s, 0)


def run(H, m, s, secs, hold, mo, spread):
    s = bar_filter(m, s, secs)
    H._spr['flat'] = np.full(len(m), spread)
    return H.run_x(s, (1000.0,), 25.0, hold, mo, 0, spread='flat', filt=False)


def per(d, t, a, b):
    dd = d[(d.index >= a) & (d.index < b)]; tt = t[(t.entry >= a) & (t.entry < b)]
    nd = max(len(dd), 1)
    return dd.pnl.mean(), len(tt) / nd, tt.pnl.mean() if len(tt) else np.nan, (dd.pnl < 0).mean(), (dd.pnl.cumsum() - dd.pnl.cumsum().cummax()).min()


M1START = pd.Timestamp('2026-06-26')
PERIODS = {'M5': [('M5 pre-M1 2025-05-05..2026-06-25', pd.Timestamp('2025-05-01'), M1START),
                  ('M5 on the M1 period (Jun 26-Oct 9 2026)', M1START, pd.Timestamp('2026-10-10'))],
           'M15': [('M15 2022-07-08..2025-05-04', pd.Timestamp('2022-07-01'), pd.Timestamp('2025-05-05')),
                   ('M15 2025-05-05..2026-06-25', pd.Timestamp('2025-05-05'), M1START),
                   ('M15 on the M1 period', M1START, pd.Timestamp('2026-10-10'))]}
RULES = {'M5': [('SNAP', k, h, 2) for k in (1.5, 2.0, 2.5, 3.0) for h in (1, 2)] + [('TOWARD', k, 3, 3) for k in (1.5, 2.0, 2.5)],
         'M15': [('SNAP', k, 1, 2) for k in (1.5, 2.0, 2.5)] + [('TOWARD', k, 1, 3) for k in (1.5, 2.0)]}
SECS = {'M5': 300, 'M15': 900}
NATR = {'M5': 48, 'M15': 16}

if __name__ == '__main__':
    ncfg = 0
    for tf in ('M5', 'M15'):
        m = load_bars(tf); H = H2(m); f = feats(m, atr_n=NATR[tf])
        print(f'\n===== {tf}: {m.index[0]} .. {m.index[-1]}, {len(m)} bars')
        for kind, k, hold, mo in RULES[tf]:
            s = fade_signal(f, 1, 'atr', k, 'none' if kind == 'SNAP' else 'toward')
            for spread in (0.20, 0.30):
                d, t = run(H, m, s, SECS[tf], hold, mo, spread); ncfg += 1
                line = f'{kind:6s} k {k:3.1f} hold {hold} bar(s) max {mo} cost ${spread:.2f}: '
                for name, a, b in PERIODS[tf]:
                    pdv, tpd, ptr, ld, dd = per(d, t, a, b)
                    line += f' | {name.split(" ")[1][:7]}: {pdv:+6.2f}/day {tpd:4.1f} tr/d {ptr:+.3f}/tr DD {dd:+5.0f}'
                print(line)
            if spread == 0.30 and ((tf == 'M5' and (kind, k, hold) in (('SNAP', 2.0, 1), ('TOWARD', 2.0, 3))) or
                                   (tf == 'M15' and (kind, k) in (('SNAP', 2.0), ('TOWARD', 1.5)))):
                pass
        # random-direction baseline (10 seeds) for one central SNAP and TOWARD rule at $0.20
        for kind, k, hold, mo in ([('SNAP', 2.0, 1, 2), ('TOWARD', 2.0, 3, 3)] if tf == 'M5' else [('SNAP', 2.0, 1, 2), ('TOWARD', 1.5, 1, 3)]):
            s = fade_signal(f, 1, 'atr', k, 'none' if kind == 'SNAP' else 'toward')
            for name, a, b in PERIODS[tf]:
                r = [per(*run(H, m, random_like(s, z), SECS[tf], hold, mo, 0.20), a, b)[0] for z in range(10)]
                d, t = run(H, m, s, SECS[tf], hold, mo, 0.20)
                lg = per(*run(H, m, np.where(s != 0, 1.0, 0.0), SECS[tf], hold, mo, 0.20), a, b)[0]
                sh = per(*run(H, m, np.where(s != 0, -1.0, 0.0), SECS[tf], hold, mo, 0.20), a, b)[0]
                print(f'  baseline {kind} k {k} {name}: pick {per(d, t, a, b)[0]:+.2f}/day; random dirs {np.mean(r):+.2f} (sd {np.std(r):.2f}); '
                      f'always long {lg:+.2f}; always short {sh:+.2f}')
    print('\nhistory configs scored:', ncfg)
