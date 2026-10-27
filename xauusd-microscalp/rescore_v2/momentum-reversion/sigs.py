"""Candidate signals (direction to TRADE, decided at the M1 close). All inputs use bars <= i."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from feats import *

sg = lambda x: np.sign(np.nan_to_num(np.asarray(x, float)))


def pullback(f, k, th, ref='vwap', vreg=None):
    """Fade a sharp k-bar move of more than th x atr240 when it goes AGAINST the session-VWAP side
    (price above VWAP and drops sharply -> buy; below VWAP and spikes up -> sell)."""
    r = f[f'r{k}'].values; a = f.atr240.values
    fade = np.where(np.abs(r) > th * a, -sg(r), 0)
    if ref == 'vwap': side = sg(f.vw_d.values)
    elif ref == 'vwap1atr': side = np.where(np.abs(f.vw_d.values) > a, sg(f.vw_d.values), 0)
    elif ref == 'none': side = fade
    out = np.where(side == fade, fade, 0)
    if vreg is not None: out = np.where(f.vreg.values > vreg, out, 0)
    return out.astype(float)


def union(*ss):
    """First non-zero wins (they agree in direction by construction when built from the same side rule)."""
    out = np.zeros(len(ss[0]))
    for s in ss: out = np.where(out == 0, s, out)
    return out


def candidates(m, f):
    b = sg(f.body.values)
    C = {
        'pb_r3_3': pullback(f, 3, 3),
        'pb_r3_2.5': pullback(f, 3, 2.5),
        'pb_r3_2': pullback(f, 3, 2),
        'pb_r1_1.5': pullback(f, 1, 1.5),
        'pb_r5_2.5': pullback(f, 5, 2.5),
        'pb_r3_2.5_v1a_vr1.2': pullback(f, 3, 2.5, 'vwap1atr', 1.2),
        'pb_union': union(pullback(f, 1, 1.5), pullback(f, 3, 2.5), pullback(f, 5, 2.5)),
        'fade_r3_6$_running': np.where((np.abs(f.r3.values) > 6) & (b == sg(f.r3.values)), -sg(f.r3.values), 0).astype(float),
        'fade_rexp2.5_atrq.5': np.where((f.rexp.values > 2.5) & (f.atrq.values > .5), -b, 0).astype(float),
    }
    ok = valid_mask(m, f)
    return {k: np.where(ok, v, 0) for k, v in C.items()}
