"""Effect on test_rules.py results of the mismatches found: (a) Range Oscillator with TradingView's
calc_bars_count=2700 ATR(2000) instead of full-history ATR(2000); (b) my Pine-seeded series in place of mm's
for every panel (warm-up only).  Uses test_rules' own sim/metr/rules unchanged."""
import sys, os, json
sys.dont_write_bytecode = True
HERE = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-port/'
os.environ['NUMBA_CACHE_DIR'] = HERE + '_numba'
sys.path.insert(0, HERE); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code'); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
import pine_indep as P
from test_rules import sim, metr, rules, WIN, RECENT, COMMON
rows = []
for TF in ('D1', 'H4', 'H1'):
    d = gbt.load(TF); p, _ = mm.all_panels(d)
    R0, v0 = rules(p)
    q = p.copy(); q['rng'] = np.load(HERE + f'rng_tvwindow_{TF}.npy')
    R1, v1 = rules(q)
    variants = {'tv_window_rng': R1}
    if TF == 'D1':
        z = np.load(HERE + 'pine_series_D1.npz')
        q2 = q.copy()
        for k in ('rsi', 'rsi_ma', 'macd', 'macd_sig', 'macd_hist', 'rti', 'rti_sig', 'asi', 'asi_sig', 'ema89', 'sma20', 'sma50', 'sma200',
                  'vwap_live', 'vw_dir_live'):
            q2[k] = z[k]
        variants['all_pine_series'] = rules(q2)[0]
    for vn, R in variants.items():
        for name in R0:
            for mode in ('long+short', 'long only'):
                a = np.asarray(R0[name], int); b = np.asarray(R[name], int)
                if mode == 'long only':
                    a = np.clip(a, 0, 1); b = np.clip(b, 0, 1)
                ndiff = int((a != b).sum())
                if ndiff == 0:
                    continue
                pa, ta, _ = sim(d, a); pb, tb, _ = sim(d, b)
                row = dict(tf=TF, variant=vn, rule=name, mode=mode, bars_pos_differ=ndiff,
                           bars_differ_test=int((a != b)[d.index >= pd.Timestamp(WIN[TF]['test'][0])].sum()))
                for wn, w in (('train', WIN[TF]['train']), ('test', WIN[TF]['test']), ('22-26', RECENT), ('common', COMMON)):
                    ma, mb = metr(pa, d, w), metr(pb, d, w)
                    row[f'{wn}_per_day_mm'] = ma['per_day']; row[f'{wn}_per_day_alt'] = mb['per_day']
                    row[f'{wn}_sharpe_mm'] = ma['sharpe']; row[f'{wn}_sharpe_alt'] = mb['sharpe']
                row['trades_mm'] = len(ta); row['trades_alt'] = len(tb)
                rows.append(row)
    print(TF, 'done', flush=True)
df = pd.DataFrame(rows)
df.to_csv(HERE + 'rule_effect.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)
print(df.to_string())
