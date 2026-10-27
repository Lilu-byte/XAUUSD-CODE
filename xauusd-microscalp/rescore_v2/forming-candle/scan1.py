"""TRAIN-only edge scan of forming-candle conditions (no TEST rows are touched).
Each condition gives a mask and a 'bullish-sense' direction d (+1 = the pattern reads bullish).
Signed move = fwd_k * d: positive = continuation pays, negative = fade pays."""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from feats import *

m1 = load_m1()
X = build(m1)
F = fwd(m1)
TR = X.train.values
HALF = X.half.values
ND_TR = len(np.unique(m1.index[TR].date))
KS = (1, 2, 3, 5, 10)


def conds(X, p, mins):
    o, h, l, c, m = (X[p + k].values for k in 'ohlcm')
    p1o, p1h, p1l, p1c = (X[p + 'p1' + k].values for k in 'ohlc')
    p2o, p2c, p3o, p3c = X[p + 'p2o'].values, X[p + 'p2c'].values, X[p + 'p3o'].values, X[p + 'p3c'].values
    ar = X[p + 'ar12'].values
    hp, lp = X[p + 'h_prev'].values, X[p + 'l_prev'].values
    rg = h - l
    body = c - o
    bn = body / ar
    clv = np.where(rg > 0, (c - l) / np.where(rg > 0, rg, 1), 0.5)
    rn = rg / ar
    col = np.sign(body)
    pcol = np.sign(p1c - p1o)
    p1bn = (p1c - p1o) / ar
    lw = np.minimum(o, c) - l; uw = h - np.maximum(o, c)
    out = {}
    for mm in mins:
        M = m == mm
        tag = f'{p}m{mm}'
        # strong partial body closing near extreme
        for thr in (0.3, 0.6, 1.0):
            for cl in (0.75, 0.9):
                bull = M & (bn > thr) & (clv >= cl); bear = M & (bn < -thr) & (clv <= 1 - cl)
                out[f'{tag}_body>{thr}_clv{cl}'] = (bull | bear, np.where(bull, 1, -1))
        # big partial range regardless of colour: direction = colour
        for thr in (1.0, 1.5, 2.5):
            s = M & (rn > thr) & (col != 0)
            out[f'{tag}_range>{thr}'] = (s, col)
        # engulfing previous closed candle (body engulf in progress)
        bull = M & (pcol < 0) & (c > p1o) & (o <= p1c + 0.05 * ar)
        bear = M & (pcol > 0) & (c < p1o) & (o >= p1c - 0.05 * ar)
        out[f'{tag}_engulf'] = (bull | bear, np.where(bull, 1, -1))
        # engulf with a substantial prior candle
        bull2 = bull & (p1bn < -0.4); bear2 = bear & (p1bn > 0.4)
        out[f'{tag}_engulf_big'] = (bull2 | bear2, np.where(bull2, 1, -1))
        # intrabar breakout of previous candle's high/low on THIS minute (first break)
        bu = M & (h > p1h) & ((hp <= p1h) | (mm == 1)); bd = M & (l < p1l) & ((lp >= p1l) | (mm == 1))
        x = bu ^ bd
        out[f'{tag}_break_first'] = (x, np.where(bu, 1, -1))
        bu_c = bu & (c > p1h); bd_c = bd & (c < p1l)
        x = bu_c ^ bd_c
        out[f'{tag}_break_close'] = (x, np.where(bu_c, 1, -1))
        bu_f = bu & (c <= p1h); bd_f = bd & (c >= p1l)       # broke then closed back inside (failed so far)
        x = bu_f ^ bd_f
        out[f'{tag}_break_wickonly'] = (x, np.where(bu_f, 1, -1))
        # pin bar forming: long lower wick = bullish read
        for wf in (0.5, 0.65):
            for rthr in (0.5, 1.0):
                bull = M & (lw > wf * rg) & (rn > rthr); bear = M & (uw > wf * rg) & (rn > rthr)
                x = bull ^ bear
                out[f'{tag}_pin{wf}_r>{rthr}'] = (x, np.where(bull, 1, -1))
        # colour vs previous colour (direction = forming colour), with min body
        for thr in (0.2, 0.5):
            same = M & (col == pcol) & (np.abs(bn) > thr) & (np.abs(p1bn) > thr)
            opp = M & (col == -pcol) & (np.abs(bn) > thr) & (np.abs(p1bn) > thr)
            out[f'{tag}_samecol{thr}'] = (same, col)
            out[f'{tag}_oppcol{thr}'] = (opp, col)
        # three closed candles same colour + forming same colour
        c2 = np.sign(p2c - p2o); c3 = np.sign(p3c - p3o)
        run = M & (pcol == c2) & (c2 == c3) & (col == pcol) & (col != 0)
        out[f'{tag}_run4'] = (run, col)
        run3 = M & (pcol == c2) & (c2 == c3) & (pcol != 0)
        out[f'{tag}_run3_prev'] = (run3, pcol)          # read = prior run direction
        # position of current close within previous candle's range (beyond = breakout already)
        pr = p1h - p1l
        loc = np.where(pr > 0, (c - p1l) / np.where(pr > 0, pr, 1), 0.5)
        bull = M & (loc > 1.0); bear = M & (loc < 0.0)
        out[f'{tag}_beyond_prev'] = (bull | bear, np.where(bull, 1, -1))
    return out


def scan(C):
    rows = []
    for name, (msk, d) in C.items():
        msk = msk & TR
        n = msk.sum()
        if n < 150: continue
        r = dict(name=name, sig_day=n / ND_TR, spread=X.spr.values[msk].mean())
        for k in KS:
            v = F[k][msk] * d[msk]
            r[f'mv{k}'] = np.nanmean(v)
        for hh in (0, 1):
            mm = msk & (HALF == hh)
            r[f'h{hh}_mv1'] = np.nanmean(F[1][mm] * d[mm]); r[f'h{hh}_mv3'] = np.nanmean(F[3][mm] * d[mm])
        v = F[3][msk] * d[msk]
        r['t3'] = np.nanmean(v) / (np.nanstd(v) / np.sqrt(np.isfinite(v).sum()))
        rows.append(r)
    return pd.DataFrame(rows)


if __name__ == '__main__':
    C = {}
    C.update(conds(X, 'f5', (1, 2, 3, 4, 5)))
    C.update(conds(X, 'f15', (1, 3, 5, 8, 11, 14, 15)))
    R = scan(C)
    R['best_abs'] = R[[f'mv{k}' for k in KS]].abs().max(axis=1)
    R['net_best'] = R.best_abs - R.spread
    R.to_csv(FC + 'scan1_train.csv', index=False)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_rows', 200)
    print('conditions scanned:', len(R), ' train days', ND_TR)
    print('Distribution of best |move| over horizons minus spread:')
    print(R.net_best.describe().round(3))
    cols = ['name', 'sig_day', 'spread'] + [f'mv{k}' for k in KS] + ['h0_mv1', 'h1_mv1', 'h0_mv3', 'h1_mv3', 't3', 'net_best']
    print('\nTop 40 by |t3|:')
    print(R.reindex(R.t3.abs().sort_values(ascending=False).index)[cols].head(40).round(3).to_string(index=False))
    print('\nTop 25 by net_best:')
    print(R.sort_values('net_best', ascending=False)[cols].head(25).round(3).to_string(index=False))
