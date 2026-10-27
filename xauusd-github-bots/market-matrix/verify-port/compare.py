"""Compare mm.all_panels (main session port) with pine_indep (written from the Pine source) on D1.
Usage: python3 -I compare.py   (writes compare_D1.json and diff csvs in this folder)"""
import sys, os, json
sys.dont_write_bytecode = True
HERE = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-port/'
os.environ['NUMBA_CACHE_DIR'] = HERE + '_numba'
sys.path.insert(0, HERE)
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
import pine_indep as P

TF = sys.argv[1] if len(sys.argv) > 1 else 'D1'
d = gbt.load(TF)
N = len(d)
p, anc = mm.all_panels(d)
S, meta = P.all_series(d)
h, l, c, v = (d[k].values.astype(float) for k in ('high', 'low', 'close', 'vol'))

# swing live: brute-force rerun on [0,t] for every t, and on the chart's 1050 / 441-bar windows
S['vwap_live'], S['vw_dir_live'] = P.swing_live_windowed(h, l, c, v, P.SW_LEN, P.VW_APT, 10 ** 9)
lw1050, dw1050 = P.swing_live_windowed(h, l, c, v, P.SW_LEN, P.VW_APT, 1050)
lw441, dw441 = P.swing_live_windowed(h, l, c, v, P.SW_LEN, P.VW_APT, 441)

WARM = {'D1': '2005-04-01', 'H4': '2014-09-01', 'H1': '2017-06-01'}[TF]
w0 = int(np.searchsorted(d.index, pd.Timestamp(WARM)))
res = {'tf': TF, 'bars': N, 'warm_start': WARM, 'warm_bar': w0}
cols = ['rsi', 'rsi_ma', 'macd', 'macd_sig', 'macd_hist', 'rti', 'rti_sig', 'asi', 'asi_sig', 'rng', 'rng_mean', 'rng_atr',
        'ema89', 'sma20', 'sma50', 'sma200', 'vwap_live', 'vwap_redrawn']
sign_ref = {'rsi': 50, 'rsi_ma': 50, 'macd': 0, 'macd_sig': 0, 'macd_hist': 0, 'rti': 50, 'rti_sig': 50, 'asi': 0, 'asi_sig': 0,
            'rng': 0}
cmp = {}
for k in cols:
    a = p[k].values.astype(float); b = np.asarray(S[k], float)
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    both = ~nan_a & ~nan_b
    dif = np.abs(a - b)
    r = dict(first_valid_mm=int(np.argmax(~nan_a)), first_valid_pine=int(np.argmax(~nan_b)),
             nan_mismatch_all=int((nan_a != nan_b).sum()), nan_mismatch_after_warm=int((nan_a != nan_b)[w0:].sum()),
             max_abs_all=float(np.nanmax(dif[both])) if both.any() else None,
             max_abs_after_warm=float(np.nanmax(dif[w0:][both[w0:]])) if both[w0:].any() else None,
             argmax_after_warm=str(d.index[w0 + int(np.nanargmax(np.where(both[w0:], dif[w0:], -1)))].date()))
    for lim in (200, 500, 1000):
        r[f'max_abs_from_bar{lim}'] = float(np.nanmax(dif[lim:][both[lim:]]))
    if k in sign_ref:
        ref = sign_ref[k]
        sa = np.sign(np.nan_to_num(a - ref)); sb = np.sign(np.nan_to_num(b - ref))
        mis = np.where(sa != sb)[0]
        r['sign_mismatch_all'] = int(len(mis)); r['sign_mismatch_after_warm'] = int((mis >= w0).sum())
        r['sign_mismatch_bars'] = [str(d.index[i].date()) for i in mis[:12]]
    cmp[k] = r
# pairwise sign of rule inputs
pairs = {'rsi-rsi_ma': ('rsi', 'rsi_ma'), 'rti-rti_sig': ('rti', 'rti_sig'), 'asi-asi_sig': ('asi', 'asi_sig'),
         'close-ema89': ('close', 'ema89'), 'close-sma200': ('close', 'sma200'), 'close-vwap_live': ('close', 'vwap_live')}
Sx = dict(S); Sx['close'] = c
for nm, (x, y) in pairs.items():
    sa = np.sign(np.nan_to_num(p[x].values - p[y].values)); sb = np.sign(np.nan_to_num(np.asarray(Sx[x]) - np.asarray(Sx[y])))
    mis = np.where(sa != sb)[0]
    cmp[nm] = dict(sign_mismatch_all=int(len(mis)), sign_mismatch_after_warm=int((mis >= w0).sum()),
                   bars=[str(d.index[i].date()) for i in mis[:12]])
for nm, mmcol, mine in (('vw_dir_live', 'vw_dir_live', S['vw_dir_live']), ('vw_dir_redrawn', 'vw_dir_redrawn', S['vw_dir_redrawn'])):
    mis = np.where(p[mmcol].values != mine)[0]
    cmp[nm] = dict(mismatch_all=int(len(mis)), bars=[str(d.index[i].date()) for i in mis[:12]])
# chart-window variants of the live swing
for W, lv, dv in ((1050, lw1050, dw1050), (441, lw441, dw441)):
    mis = np.where(dv != S['vw_dir_live'])[0]
    dif = np.abs(lv - S['vwap_live'])
    after = np.arange(N) >= W
    cmp[f'vw_live_window{W}_vs_fullhistory'] = dict(
        dir_mismatch_all=int(len(mis)), dir_mismatch_after_first_full_window=int((mis >= W).sum()),
        value_max_abs_after_first_full_window=float(np.nanmax(dif[after])),
        value_bars_diff_gt_0p01_after=int((dif[after] > 0.01).sum()),
        mismatch_bars=[str(d.index[i].date()) for i in mis[mis >= W][:12]])
# anchors
an, ap, ak, acf = meta['anchors']
mine_anc = pd.DataFrame(dict(anchor_i=an, confirm_i=acf, price=ap, kind=ak))
mine_anc['tag'] = P.tags(ap, ak)
mm_tags = P.tags(anc.price.values, anc.kind.values)
same = (len(mine_anc) == len(anc)) and bool((mine_anc[['anchor_i', 'confirm_i', 'kind']].values == anc[['anchor_i', 'confirm_i', 'kind']].values).all()) \
    and bool(np.allclose(mine_anc.price.values, anc.price.values))
cmp['anchors'] = dict(n_mine=len(mine_anc), n_mm=len(anc), identical=same, tags_identical=mm_tags == list(mine_anc.tag),
                      tag_counts=mine_anc.tag.value_counts().to_dict(),
                      median_delay=float((mine_anc.confirm_i - mine_anc.anchor_i).median()))
mine_anc['anchor_time'] = d.index[mine_anc.anchor_i]; mine_anc['confirm_time'] = d.index[mine_anc.confirm_i]
mine_anc.to_csv(HERE + f'anchors_pine_{TF}.csv', index=False)
cmp['redraw'] = dict(days_live_ne_redrawn_pct=round(100 * float((S['vw_dir_live'] != S['vw_dir_redrawn']).mean()), 2))
# ASI index arithmetic
wi, li, cnt = meta['asi_wi'], meta['asi_li'], meta['asi_cnt']
cmp['asi_idx'] = dict(win_idx_at_count15=sorted(set(wi[cnt == 15].tolist())), loss_idx_at_count15=sorted(set(li[cnt == 15].tolist())),
                      rti_ranks=meta['rti_par'])
# EMA-seed sensitivity: alternative ta.ema seed
alt = P.ema_first_value_seed(c, 12) - P.ema_first_value_seed(c, 26)
alt_sig = P.ema_first_value_seed(alt, 9)
cmp['ema_seed_alt'] = dict(macd_max_abs_after_warm=float(np.nanmax(np.abs(alt - S['macd'])[w0:])),
                          hist_max_abs_after_warm=float(np.nanmax(np.abs((alt - alt_sig) - S['macd_hist'])[w0:])))
res['compare'] = cmp
json.dump(res, open(HERE + f'compare_{TF}.json', 'w'), indent=1, default=str)
np.savez(HERE + f'pine_series_{TF}.npz', index=d.index.values.astype('datetime64[ns]'), vw1050=lw1050, dw1050=dw1050, vw441=lw441, dw441=dw441,
         **{k: np.asarray(v_, float) for k, v_ in S.items()})
print(json.dumps(res, indent=1, default=str))
