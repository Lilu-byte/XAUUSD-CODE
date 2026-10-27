# Port (literal) vs independent reference on real XAUUSD ranges.
import sys, math, time
import numpy as np
sys.path.insert(0, '/mnt/project-files/xauusd-volume-profile/review/maths')
from common import sel
from frvp_port import redraw
import frvp_ref as ref

RANGES = [
    ('M1', '1h  NFP 2026-10-02 16:00', '2026-10-02 16:00', '2026-10-02 16:59'),
    ('M1', '3h  Asia 2026-10-08', '2026-10-08 02:00', '2026-10-08 04:59'),
    ('M1', '4h  US 2026-10-09', '2026-10-09 15:30', '2026-10-09 19:29'),
    ('M1', 'day 2026-07-01', '2026-07-01 00:00', '2026-07-01 23:59'),
    ('M1', 'day 2026-09-16', '2026-09-16 00:00', '2026-09-16 23:59'),
    ('M1', 'day 2026-10-08', '2026-10-08 00:00', '2026-10-08 23:59'),
    ('M1', 'week 2026-08-10', '2026-08-10 00:00', '2026-08-14 23:59'),
    ('M1', 'week 2026-09-28', '2026-09-28 00:00', '2026-10-02 23:59'),
    ('M1', 'month 2026-07', '2026-07-01 00:00', '2026-07-31 23:59'),
    ('M1', 'month 2026-08', '2026-08-01 00:00', '2026-08-31 23:59'),
    ('M1', 'month 2026-09', '2026-09-01 00:00', '2026-09-30 23:59'),
    ('M1', 'all M1 26Jun-9Oct', '2026-06-26 00:00', '2026-10-09 23:59'),
    ('M5', 'M5 week 2025-11-10', '2025-11-10 00:00', '2025-11-14 23:59'),
    ('M5', 'M5 month 2026-01', '2026-01-01 00:00', '2026-01-31 23:59'),
    ('M5', 'M5 year 2025-10..2026-09', '2025-10-01 00:00', '2026-09-30 23:59'),
    ('H1', 'H1 month 2026-04', '2026-04-01 00:00', '2026-04-30 23:59'),
    ('H1', 'H1 year 2025', '2025-01-01 00:00', '2025-12-31 23:59'),
    ('H1', 'H1 all 2016-2026', '2016-01-01 00:00', '2026-12-31 23:59'),
    ('H4', 'H4 2024-2025', '2024-01-01 00:00', '2025-12-31 23:59'),
    ('H4', 'H4 all 2013-2026', '2013-01-01 00:00', '2026-12-31 23:59'),
]
CONFIGS = [dict(rows=24), dict(rows=60), dict(rows=120), dict(rowsize=0.5), dict(rowsize=1.0), dict(rowsize=5.0)]


def cfgname(c):
    return f"rows={c['rows']}" if 'rows' in c else f"size={c['rowsize']:.2f}"


agg = dict(rowvol_rel=0.0, rowvol_abs=0.0, poc_mismatch=0, dpoc=0.0, dvah=0.0, dval=0.0, grid_mismatch=0,
           min_share=1.0, max_share=0.0, not_minimal=0, wider_than_opt=0, max_extra_rows=0, n=0,
           sum_rel=0.0, ud_rel=0.0, lv_dpoc=[], lv_dvah=[], lv_dval=[], near_tie=0)
lines = []
t_start = time.time()
for tf, name, t0, t1 in RANGES:
    df = sel(tf, t0, t1)
    H = df['high'].tolist(); L = df['low'].tolist(); O = df['open'].tolist(); C = df['close'].tolist()
    V = df['tick_volume'].tolist()
    lines.append(f"\n{name}  [{tf}, {len(df)} candles, {t0} .. {t1}]  low {min(L):.2f} high {max(H):.2f}")
    for c in CONFIGS:
        p = redraw(H, L, O, C, V, InpRows=c.get('rows', 60), InpRowSize=c.get('rowsize', 0.0))
        r = ref.profile(df, rows=c.get('rows', 60), rowsize=c.get('rowsize', 0.0))
        lv = ref.profile(df, rows=c.get('rows', 60), rowsize=c.get('rowsize', 0.0), model='levels')
        tot_p = np.array(p['tot']); up_p = np.array(p['up']); dn_p = np.array(p['dn'])
        gm = p['rows'] != r['rows']
        if gm:
            agg['grid_mismatch'] += 1
            lines.append(f"  {cfgname(c):10s} GRID MISMATCH port rows {p['rows']} ref rows {r['rows']}")
            continue
        dabs = float(np.max(np.abs(tot_p - r['tot'])))
        drel = dabs / float(r['tot'].max())
        dud = float(max(np.max(np.abs(up_p - r['up'])), np.max(np.abs(dn_p - r['dn'])))) / float(r['tot'].max())
        srel = abs(p['sum'] - float(np.sum(V))) / float(np.sum(V))
        share = p['acc'] / p['sum']
        minimal = (p['acc'] - p['last']) < p['sum'] * 0.70 - p['sum'] * 1e-12 or (p['vaLo'] == p['poc'] == p['vaHi'])
        w = p['vaHi'] - p['vaLo'] + 1
        srt = np.sort(tot_p)[::-1]
        near = srt[1] >= srt[0] * (1 - 1e-9) if len(srt) > 1 else False
        agg['near_tie'] += int(near)
        agg['n'] += 1
        agg['rowvol_rel'] = max(agg['rowvol_rel'], drel); agg['rowvol_abs'] = max(agg['rowvol_abs'], dabs)
        agg['ud_rel'] = max(agg['ud_rel'], dud); agg['sum_rel'] = max(agg['sum_rel'], srel)
        agg['poc_mismatch'] += int(p['poc'] != r['poc'])
        agg['dpoc'] = max(agg['dpoc'], abs(p['pocPx'] - r['pocPx']))
        agg['dvah'] = max(agg['dvah'], abs(p['vah'] - r['vah']))
        agg['dval'] = max(agg['dval'], abs(p['val'] - r['val']))
        agg['min_share'] = min(agg['min_share'], share); agg['max_share'] = max(agg['max_share'], share)
        agg['not_minimal'] += int(not minimal)
        if w > r['opt_w']: agg['wider_than_opt'] += 1; agg['max_extra_rows'] = max(agg['max_extra_rows'], w - r['opt_w'])
        va_same = (p['vaLo'], p['vaHi']) == (r['vaLo'], r['vaHi'])
        agg['lv_dpoc'].append(abs(lv['pocPx'] - r['pocPx']) / r['g'].get('sc', 1) if False else abs(lv['pocPx'] - r['pocPx']))
        agg['lv_dvah'].append(abs(lv['vah'] - r['vah'])); agg['lv_dval'].append(abs(lv['val'] - r['val']))
        step = p['step']
        lines.append(
            f"  {cfgname(c):10s} rows {p['rows']:4d} step {step:8.4f}{' CAPPED' if p['capped'] else ''} | "
            f"max|row diff| {dabs:.3g} ({drel:.1e} of POC row) | POC port {p['pocPx']:.4f} ref {r['pocPx']:.4f} | "
            f"VAH {p['vah']:.4f}/{r['vah']:.4f} VAL {p['val']:.4f}/{r['val']:.4f} | VA same rows {va_same} | "
            f"VA share {share*100:.3f}% (w/o last row {(p['acc']-p['last'])/p['sum']*100:.3f}%) | "
            f"VA rows {w} narrowest {r['opt_w']} any-rows min {r['kmin']} | "
            f"levels model: POC {lv['pocPx']-r['pocPx']:+.2f} VAH {lv['vah']-r['vah']:+.2f} VAL {lv['val']-r['val']:+.2f}")

print("PORT vs REFERENCE: summary over", agg['n'], "profiles (", len(RANGES), "ranges x", len(CONFIGS), "grids )")
print(f"  grid (rows) mismatches: {agg['grid_mismatch']}")
print(f"  max |row volume diff|: {agg['rowvol_abs']:.3g} ticks absolute, {agg['rowvol_rel']:.2e} of the POC row; up/down split {agg['ud_rel']:.2e}")
print(f"  max |profile total - sum of tick volume| / sum: {agg['sum_rel']:.2e}")
print(f"  POC row mismatches: {agg['poc_mismatch']}; max |POC price diff| ${agg['dpoc']:.2e}; VAH ${agg['dvah']:.2e}; VAL ${agg['dval']:.2e}")
print(f"  value-area share: min {agg['min_share']*100:.4f}%  max {agg['max_share']*100:.4f}%")
print(f"  value areas where the last row added was not needed: {agg['not_minimal']}")
print(f"  value areas wider than the narrowest window around the POC: {agg['wider_than_opt']} of {agg['n']} (max {agg['max_extra_rows']} extra rows)")
print(f"  profiles whose 2nd-biggest row is within 1e-9 of the POC row: {agg['near_tie']}")
a = np.array
print(f"  levels model vs continuous model (sensitivity, $): POC median {np.median(agg['lv_dpoc']):.3f} max {max(agg['lv_dpoc']):.2f}; "
      f"VAH median {np.median(agg['lv_dvah']):.3f} max {max(agg['lv_dvah']):.2f}; VAL median {np.median(agg['lv_dval']):.3f} max {max(agg['lv_dval']):.2f}")
print(f"  run time {time.time()-t_start:.0f}s")
print("\n".join(lines))
