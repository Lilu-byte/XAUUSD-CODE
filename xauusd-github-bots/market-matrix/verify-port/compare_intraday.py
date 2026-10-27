"""Same port check on H4 and H1 (test_rules also runs them).  Swing 'live' here = the chart's own
1050-bar window (Pine line 954) evaluated at each bar, compared with mm's single-pass live capture."""
import sys, os, json
sys.dont_write_bytecode = True
HERE = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-port/'
os.environ['NUMBA_CACHE_DIR'] = HERE + '_numba'
sys.path.insert(0, HERE); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code'); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
import pine_indep as P
out = {}
for TF, warm in (('H4', '2014-09-01'), ('H1', '2017-06-01')):
    d = gbt.load(TF); p, anc = mm.all_panels(d)
    S, meta = P.all_series(d)
    h, l, c, v = (d[k].values.astype(float) for k in ('high', 'low', 'close', 'vol'))
    lw, dw = P.swing_live_windowed(h, l, c, v, P.SW_LEN, P.VW_APT, 1050)
    w0 = int(np.searchsorted(d.index, pd.Timestamp(warm)))
    r = {}
    for k in ('rsi', 'rsi_ma', 'macd', 'macd_sig', 'macd_hist', 'rti', 'rti_sig', 'asi', 'asi_sig', 'rng', 'ema89', 'sma200', 'vwap_redrawn'):
        a = p[k].values; b = np.asarray(S[k], float)
        dif = np.abs(a - b)[w0:]
        e = dict(max_abs_after_warm=float(np.nanmax(dif)))
        ref = {'rsi': 50, 'rti': 50, 'rti_sig': 50, 'rsi_ma': 50}.get(k, 0)
        if k not in ('ema89', 'sma200', 'vwap_redrawn'):
            e['sign_mismatch_after_warm'] = int((np.sign(np.nan_to_num(a - ref)) != np.sign(np.nan_to_num(b - ref)))[w0:].sum())
        r[k] = e
    r['vw_dir_redrawn_mismatch'] = int((p.vw_dir_redrawn.values != S['vw_dir_redrawn']).sum())
    r['vw_dir_live_window1050_vs_mm_mismatch_after_1050'] = int((p.vw_dir_live.values != dw)[1050:].sum())
    r['vwap_live_window1050_vs_mm_maxabs_after_1050'] = float(np.nanmax(np.abs(p.vwap_live.values - lw)[1050:]))
    an, ap, ak, acf = meta['anchors']
    r['anchors_identical'] = bool(len(an) == len(anc) and (an == anc.anchor_i.values).all() and (acf == anc.confirm_i.values).all()
                                  and (ak == anc.kind.values).all() and np.allclose(ap, anc.price.values))
    r['n_anchors'] = int(len(an))
    out[TF] = r
    print(TF, json.dumps(r), flush=True)
json.dump(out, open(HERE + 'compare_intraday.json', 'w'), indent=1)
