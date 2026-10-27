"""Mirror (direction-flip) transform for feat.build features: mirror(F) = the features that build() would produce on the
price series reflected as P' = K - P (up-moves become down-moves, upper wicks become lower wicks, ...).
Used to (1) augment training data with the mirrored copy (label sign flipped) and (2) make a score exactly antisymmetric:
score(x) = (f(x) - f(mirror(x))) / 2, so the model cannot carry a net long/short bias learned from the TRAIN trend
(gold +$600 in Jul-Aug 2026) and can only use direction-symmetric patterns (e.g. fading large candles).
check: python3 feat_mirror.py"""
import numpy as np, pandas as pd

NEG = ('_body', 'ret', 'z10', 'z30', 'z120', 'd_ret', 'tv_body', '_d20', '_d50', '_trend', '_slope', '_ret3')
ONE_MINUS = ('stoch', '_pos', 'd_pos', 'rnd5', 'rnd10')


def mirror(F):
    G = F.copy()
    for c in F.columns:
        if c.endswith('_uw'):
            G[c] = F[c[:-3] + '_lw']
        elif c.endswith('_lw'):
            G[c] = F[c[:-3] + '_uw']
        elif c.startswith('hh'):
            G[c] = F['ll' + c[2:]]
        elif c.startswith('ll'):
            G[c] = F['hh' + c[2:]]
        elif c in ('up5', 'up10'):
            G[c] = float(c[2:]) - F[c]
        elif c.startswith('rsi') or c.endswith('_rsi'):
            G[c] = 100.0 - F[c]
        elif c.endswith(NEG) or c.startswith('ret') or (c[0] == 'z' and c[1:].isdigit()):
            G[c] = -F[c]
        elif c.endswith(ONE_MINUS) or c.startswith('stoch'):
            G[c] = 1.0 - F[c]
    return G


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
    from feat import build, load
    from mlib import load_m1
    K = 10000.0
    m1 = load_m1()
    cache = {tf: load(tf) for tf in ('M5', 'M15', 'H1', 'H4')}

    def flip(d):
        e = d.copy(); e['open'] = K - d.open; e['close'] = K - d.close; e['high'] = K - d.low; e['low'] = K - d.high
        return e
    F = build(m1, cache); Fm = build(flip(m1), {k: flip(v) for k, v in cache.items()})
    M = mirror(F)
    a = M.iloc[3000:].values.astype(float); b = Fm.iloc[3000:].values.astype(float)
    err = np.nanmax(np.abs(a - b) / (np.abs(b) + 1e-2), axis=0)
    nan_mis = (np.isnan(a) != np.isnan(b)).mean(axis=0)
    bad = [(F.columns[j], round(float(err[j]), 4), round(float(nan_mis[j]), 4)) for j in range(F.shape[1])
           if err[j] > 1e-3 or nan_mis[j] > 0]
    # c % 5 differs at exact multiples of 5 (rnd5 = 0 -> 1); count those as fine
    print('columns:', F.shape[1], ' mismatching (col, max rel err, nan mismatch share):', bad)
