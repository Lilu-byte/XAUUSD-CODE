"""Base SMC signal set used by scan2/scan3 (TRAIN scans). build_base(H) -> dict name -> int8 array."""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs2 import *


def build_base(H):
    m1 = H.m1; o, h, l, c = arrs(m1)
    b5, p5 = htf_bars(m1, 5); O5, H5, L5, C5 = arrs(b5)
    P = lambda s: place(m1, p5, s)
    base = {}
    for N in (5, 15, 30, 60):
        base[f'sweep_M1_N{N}_strict'] = sweep(o, h, l, c, N, 0.3, True, 0.3)
        base[f'sweep_M1_N{N}_loose'] = sweep(o, h, l, c, N)
    for N in (10, 30, 45):
        base[f'sweep_M5_N{N}'] = P(sweep(O5, H5, L5, C5, N, 0.66, False, 0.3))
    for N, bk in itertools.product((6, 12, 24), (0.0, 0.3)):
        base[f'sweepform_M5_N{N}_b{bk}'] = sweep_forming(m1, N, 5, bk)
    for k in (3, 5, 8):
        base[f'swsweep_M1_k{k}'] = swing_sweep(o, h, l, c, k)
    for k in (3, 5):
        base[f'swsweep_M5_k{k}'] = P(swing_sweep(O5, H5, L5, C5, k, 48))
    for N, W, cf in itertools.product((15, 30, 60), (5, 15), (0, 1, 2)):
        base[f'sweepthen_N{N}_W{W}_c{cf}'] = sweep_then(o, h, l, c, N, W, cf, 0.2)
    for g in (0.5, 1.0, 2.0):
        base[f'fvgret_M1_g{g}'] = fvg_retrace(o, h, l, c, g, 15, 0)
    for g in (0.2, 0.5):
        base[f'fvgret_M5_g{g}'] = P(fvg_retrace(O5, H5, L5, C5, g * 2.2, 15, 0))
    for k in (5, 8):
        base[f'ob_M1_k{k}'] = structure(o, h, l, c, k, 30, kind=2)
    for k in (3, 5):
        base[f'ob_M5_k{k}'] = P(structure(O5, H5, L5, C5, k, 10, kind=2))
    for k in (2, 3):
        base[f'bos_M5_k{k}'] = P(structure(O5, H5, L5, C5, k, kind=0))
    base['choch_M5_k3'] = P(structure(O5, H5, L5, C5, 3, kind=3))
    for N in (30, 60):
        base[f'brk_M5_N{N}'] = P(breakout(O5, H5, L5, C5, N))
        base[f'brk_M1_N{N}'] = breakout(o, h, l, c, N)
    for st, e in itertools.product((5, 10), (0.2, 0.5)):
        base[f'rnrej_{st}_e{e}'] = round_level(o, h, l, c, st, 'reject', e)
    pdh, pdl = day_levels(m1)
    base['pdhl_sweep'] = level_events(m1, H.day, pdh, pdl, 0, 0.0, 3)
    base['pdhl_break'] = level_events(m1, H.day, pdh, pdl, 1, 0.0, 3)
    ah, al = session_range(m1, 60, 600)
    base['asia_sweep'] = level_events(m1, H.day, ah, al, 0, 0.0, 3)
    base['asia_break'] = level_events(m1, H.day, ah, al, 1, 0.0, 3)
    return base
