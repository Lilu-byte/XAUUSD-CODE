"""Stage 4 (TRAIN only): choose the picks by a rule fixed before looking at TEST.
Time-exit group (stage 2b grid, TP 1000 or $2-6, with BE/trail variants):
  score = mean over the cell and its grid neighbours (threshold +/- 1 step, N +/- 1 step; other settings equal) of
          min(per_day Jun 26-Jul 31, per_day Aug)                                   -> rewards a stable plateau
  risk limits on TRAIN: max drawdown >= -$100 and worst day >= -$60 ($3,000 account)
  best cell per region ('snap' and 'toward'), then TRAIN-only robustness: 1-bar latency, flat $0.30 spread, +$0.07
  commission, STOP / OHLC fills, random directions and always-long / always-short on the same bars.
TP <= $1 group (stage 3): same score over (to +/- 1 step, lad_max +/- 1 step) neighbours, same risk limits."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *

pd.set_option('display.width', 250)
R = pd.read_csv(FAM + 's2b_refine_train.csv.gz')
R['minh'] = R[['pd_A', 'pd_B']].min(axis=1)
key = ['region', 'k', 'mode', 'fresh', 'sgate', 'sl', 'tp', 'mo', 'be_trig', 'be_lock', 'trail']
TH = {(reg, md): sorted(R[(R.region == reg) & (R['mode'] == md)].th.unique()) for reg in R.region.unique() for md in ('atr', 'usd')}
NS = {reg: sorted(R[R.region == reg].N.unique()) for reg in R.region.unique()}
idx = R.set_index(key + ['th', 'N']).minh
sc = []
for r in R.itertuples(index=False):
    ths = TH[(r.region, r.mode)]; ns = NS[r.region]
    ti = ths.index(r.th); ni = ns.index(r.N)
    base = tuple(getattr(r, c) for c in key)
    vals = [r.minh]
    for th2 in (ths[ti - 1] if ti > 0 else None, ths[ti + 1] if ti + 1 < len(ths) else None):
        if th2 is not None: vals.append(idx.get(base + (th2, r.N), np.nan))
    for n2 in (ns[ni - 1] if ni > 0 else None, ns[ni + 1] if ni + 1 < len(ns) else None):
        if n2 is not None: vals.append(idx.get(base + (r.th, n2), np.nan))
    sc.append(np.nanmean(vals))
R['score'] = sc
ok = (R.dd_tr >= -100) & (R.wd_tr >= -60)
c = ['region', 'k', 'mode', 'th', 'fresh', 'sgate', 'N', 'sl', 'tp', 'mo', 'be_trig', 'trail', 'score', 'pd_tr', 'pd_A', 'pd_B', 'tpd_tr',
     'pt_tr', 'win_tr', 'wd_tr', 'dd_tr', 'ls_tr']
for reg in ('snap', 'toward'):
    x = R[(R.region == reg) & ok].sort_values('score', ascending=False)
    print(f'\n{reg}: {len(x)} of {(R.region == reg).sum()} cells inside the risk limits; top 10 by neighbour-smoothed min-half:')
    print(x[c].head(10).round(2).to_string(index=False))

L = pd.read_csv(FAM + 's3_tp1_train.csv.gz')
L['minh'] = L[['pd_A', 'pd_B']].min(axis=1)
lad = L[L.kind == 'lad'].copy()
lkey = ['sig', 'tp', 'sl', 'lad_q', 'lad_window', 'mode']
TO = [3, 5, 10, 15]; LM = [1, 3, 6, 10]
lidx = lad.set_index(lkey + ['to', 'lad_max']).minh
lidx = lidx[~lidx.index.duplicated()]
sc = []
for r in lad.itertuples(index=False):
    base = tuple(getattr(r, k) for k in lkey); vals = [r.minh]
    ti = TO.index(r.to); li = LM.index(r.lad_max)
    for t2 in ([TO[ti - 1]] if ti > 0 else []) + ([TO[ti + 1]] if ti + 1 < len(TO) else []):
        vals.append(lidx.get(base + (t2, r.lad_max), np.nan))
    for l2 in ([LM[li - 1]] if li > 0 else []) + ([LM[li + 1]] if li + 1 < len(LM) else []):
        vals.append(lidx.get(base + (r.to, l2), np.nan))
    sc.append(np.nanmean(vals))
lad['score'] = sc
legs = L[L.kind == 'legs'].copy(); legs['score'] = legs.minh       # legs grid is small: no smoothing
T = pd.concat([lad, legs])
okl = (T.dd_tr >= -100) & (T.wd_tr >= -60)
cl = ['sig', 'kind', 'tp', 'sl', 'to', 'lad_max', 'lad_q', 'lad_window', 'mode', 'score', 'pd_tr', 'pd_A', 'pd_B', 'tpd_tr', 'pt_tr', 'win_tr',
      'wd_tr', 'dd_tr', 'ls_tr']
print('\nTP<=$1 group: top 10 by smoothed min-half inside the risk limits:')
print(T[okl].sort_values('score', ascending=False)[cl].head(10).round(2).to_string(index=False))
