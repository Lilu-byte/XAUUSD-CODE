"""Range Oscillator ATR: full-history ta.atr(2000) (mm.py) vs the value TradingView computes inside
request.security(..., calc_bars_count = 2700) (Pine line 438), evaluated at the chart's last bar t."""
import sys, os, json
sys.dont_write_bytecode = True
HERE = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-port/'
os.environ['NUMBA_CACHE_DIR'] = HERE + '_numba'
sys.path.insert(0, HERE); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code'); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
import pine_indep as P
out = {}
for TF in sys.argv[1:] or ['D1']:
    d = gbt.load(TF); N = len(d)
    h, l, c = (d[k].values.astype(float) for k in ('high', 'low', 'close'))
    p, _ = mm.all_panels(d)
    full2000 = P.p_atr(h, l, c, 2000)
    win2000 = P._window_atr(P.p_tr(h, l, c), h - l, 2000, 2700)
    win200 = P._window_atr(P.p_tr(h, l, c), h - l, 200, 2700)
    full200 = P.p_atr(h, l, c, 200)
    raw_full = np.where(np.isnan(full2000), full200, full2000)
    raw_win = np.where(np.isnan(win2000), win200, win2000)
    mean = P._range_mean(c, P.RNG_LEN)
    osc_win = 100 * (c - mean) / (2 * raw_win)
    osc_full = 100 * (c - mean) / (2 * raw_full)
    np.save(HERE + f'rng_tvwindow_{TF}.npy', osc_win)
    ix = d.index
    r = {}
    # mm vs my full-history version, excluding the single seed bar 1999
    dd = np.abs(p.rng.values - osc_full); dd[1999] = np.nan
    r['mm_vs_pine_fullhist_rng_maxabs_excl_bar1999'] = float(np.nanmax(dd))
    r['bar1999'] = str(ix[1999]); r['bar2699'] = str(ix[2699])
    ratio = raw_full / raw_win
    for nm, (a, b) in {'all': (0, N), 'from_bar2699': (2699, N)}.items():
        sl = slice(a, b)
        r[f'atr_ratio_full_over_window_{nm}'] = dict(min=float(np.nanmin(ratio[sl])), median=float(np.nanmedian(ratio[sl])), max=float(np.nanmax(ratio[sl])))
        dif = np.abs(p.rng.values[sl] - osc_win[sl])
        r[f'rng_maxabs_mm_vs_tvwindow_{nm}'] = float(np.nanmax(dif))
        r[f'rng_medianabs_mm_vs_tvwindow_{nm}'] = float(np.nanmedian(dif))
        sa = np.sign(np.nan_to_num(p.rng.values[sl])); sb = np.sign(np.nan_to_num(osc_win[sl]))
        r[f'rng_sign_mismatch_{nm}'] = int((sa != sb).sum())
        for lv in (100, -100):
            za = (p.rng.values[sl] > lv) if lv > 0 else (p.rng.values[sl] < lv)
            zb = (osc_win[sl] > lv) if lv > 0 else (osc_win[sl] < lv)
            r[f'beyond_{lv}_mm_vs_tv_{nm}'] = [int(za.sum()), int(zb.sum()), int((za != zb).sum())]
    yrs = pd.Series(ratio, ix).groupby(ix.year).median().round(3).to_dict()
    r['atr_ratio_full_over_window_by_year'] = {int(k): v for k, v in yrs.items() if not np.isnan(v)}
    r['last'] = dict(time=str(ix[-1]), atr2000_full=float(full2000[-1]), atr2000_window=float(win2000[-1]),
                     rng_mm=float(p.rng.values[-1]), rng_tv=float(osc_win[-1]))
    out[TF] = r
json.dump(out, open(HERE + 'range_window.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
