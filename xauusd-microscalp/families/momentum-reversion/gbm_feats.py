"""Scale-free feature matrix for the family (all from bars <= i) and per-bar bracket labels from the harness."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from feats import *


def feature_matrix(m, f):
    a = f.atr240
    X = pd.DataFrame(index=m.index)
    for k in (1, 2, 3, 5, 10): X[f'r{k}a'] = f[f'r{k}'] / a
    X['r30a'] = (m.close - m.close.shift(30)) / a
    X['body_a'] = f.body / a; X['rng_a'] = f.rng / a
    X['uw_a'] = (m.high - np.maximum(m.open, m.close)) / a; X['lw_a'] = (np.minimum(m.open, m.close) - m.low) / a
    X['cloc'] = f.cloc; X['streak'] = f.streak
    for n in (2, 3, 7): X[f'rsi{n}'] = f[f'rsi{n}']
    for n in (10, 20, 60): X[f'z{n}'] = f[f'z{n}']
    X['vw_da'] = f.vw_d / a
    X['vrel'] = f.vrel; X['rexp'] = f.rexp; X['vreg'] = f.vreg; X['atrq'] = f.atrq
    X['atr240'] = a; X['tod'] = f.tod; X['spr'] = f.spr
    X['prev_body_a'] = f.body.shift(1) / a; X['prev_rng_a'] = f.rng.shift(1) / a
    return X


def bracket_labels(H, tp, sl, to):
    """pnl of a long and of a short opened at every bar's close, same bracket (via the harness)."""
    n = len(H.m1); out = {}
    for d in (1, -1):
        days, tr = H.run(np.full(n, d), tp, sl, to, max_open=64)
        lab = pd.Series(np.nan, index=H.m1.index)
        lab[tr.entry.values] = tr.pnl.values
        out[d] = lab.values
    return out
