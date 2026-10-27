"""Candidate signals chosen from the TRAIN edge scans (scan1/scan2/baseline/robust1). Definitions here are
the single source used by bracket.py and final_test.py."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs2 import *


def build(m1):
    o, h, l, c = arrs(m1)
    tod = m1.tod.values
    lon = (tod >= 600) & (tod < 900)          # 10:00-15:00 server = London morning
    ny = (tod >= 900) & (tod < 1140)          # 15:00-19:00 server = NY morning
    h1t = trend_h1(m1)
    C = {}
    # A: London liquidity-grab fade: close beyond the prior 30 M1 bars' high/low -> fade it
    C['A_lon_fade_brk30'] = np.where(lon, -breakout(o, h, l, c, 30), 0).astype(np.int8)
    # B: London M1 sweep reversal (wick beyond prior 5-bar extreme, close back inside)
    C['B_lon_sweep5'] = np.where(lon, sweep(o, h, l, c, 5), 0).astype(np.int8)
    # C: London forming-M5 sweep reversal ("before the M5 candle ends")
    C['C_lon_sweepform6'] = np.where(lon, sweep_forming(m1, 6, 5, 0.0), 0).astype(np.int8)
    # D: NY M1 sweep reversal only when it points with the H1 trend (EMA20 of closed H1 bars)
    s = sweep(o, h, l, c, 5)
    C['D_ny_sweep5_withH1'] = np.where(ny & (s * h1t > 0), s, 0).astype(np.int8)
    # E: all-day (no session filter) fade of 30-bar breakout, for the 'trade all day' question
    C['E_all_fade_brk30'] = (-breakout(o, h, l, c, 30)).astype(np.int8)
    # F: all-day M1 sweep reversal with depth/colour/close-back filters (the textbook version)
    C['F_all_sweep5_strict'] = sweep(o, h, l, c, 5, 0.3, True, 0.3)
    return C


def build2(m1):
    """Second-round candidates (after robust2.py)."""
    o, h, l, c = arrs(m1)
    tod = m1.tod.values
    lon = (tod >= 600) & (tod < 900)
    late = tod >= 1140                         # 19:00-23:15 server (US afternoon)
    C = {}
    C['P1_lon_fade_brk30'] = np.where(lon, -breakout(o, h, l, c, 30), 0).astype(np.int8)
    # SMC entry model: sweep of the 30-bar low (wick below, close back above) arms a long for 15 bars;
    # enter at the first close above the sweep bar's high (displacement / micro break of structure). Mirror.
    C['P2_late_sweep30_disp'] = np.where(late, sweep_then(o, h, l, c, 30, 15, 0, 0.2), 0).astype(np.int8)
    u = C['P1_lon_fade_brk30'].astype(int) + C['P2_late_sweep30_disp'].astype(int)
    C['P3_union'] = np.sign(u).astype(np.int8)
    return C
