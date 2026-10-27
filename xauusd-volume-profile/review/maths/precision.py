# How much does the M1 source matter? Same ranges built from M1, M5, M15 and H1 candles with the
# literal port; differences of POC/VAH/VAL in $ (and in rows) against the M1-built profile.
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-volume-profile/review/maths')
from common import sel, resample, load
from frvp_port import redraw

RANGES = [
    ('2h',    '2h NFP 2026-10-02 15-17', '2026-10-02 15:00', '2026-10-02 16:59'),
    ('4h',    '4h US 2026-10-09 15-19',  '2026-10-09 15:00', '2026-10-09 18:59'),
    ('4h',    '4h London 2026-09-22',     '2026-09-22 09:00', '2026-09-22 12:59'),
    ('8h',    '8h Asia 2026-10-08 01-09', '2026-10-08 01:00', '2026-10-08 08:59'),
    ('day',   'day 2026-07-01', '2026-07-01 00:00', '2026-07-01 23:59'),
    ('day',   'day 2026-08-20', '2026-08-20 00:00', '2026-08-20 23:59'),
    ('day',   'day 2026-09-16', '2026-09-16 00:00', '2026-09-16 23:59'),
    ('day',   'day 2026-10-08', '2026-10-08 00:00', '2026-10-08 23:59'),
    ('week',  'week 2026-07-06', '2026-07-06 00:00', '2026-07-10 23:59'),
    ('week',  'week 2026-08-10', '2026-08-10 00:00', '2026-08-14 23:59'),
    ('week',  'week 2026-09-28', '2026-09-28 00:00', '2026-10-02 23:59'),
    ('month', 'month 2026-07', '2026-07-01 00:00', '2026-07-31 23:59'),
    ('month', 'month 2026-08', '2026-08-01 00:00', '2026-08-31 23:59'),
    ('month', 'month 2026-09', '2026-09-01 00:00', '2026-09-30 23:59'),
    ('all',   'all 2026-06-29..10-09', '2026-06-29 00:00', '2026-10-09 23:59'),
]
CONFIGS = [dict(InpRows=24), dict(InpRows=60), dict(InpRows=120), dict(InpRowSize=0.5), dict(InpRowSize=1.0), dict(InpRowSize=5.0)]
TFS = ['M5', 'M15', 'H1']


def cname(c): return f"rows={c['InpRows']}" if 'InpRows' in c else f"size={c['InpRowSize']:.2f}"


def build(df, c):
    return redraw(df['high'].tolist(), df['low'].tolist(), df['open'].tolist(), df['close'].tolist(), df['tick_volume'].tolist(), **c)


# 0) the files agree with M1 resampled over the M1 period
m1all = load('M1')
for tf, rule in (('M5', '5min'), ('M15', '15min'), ('H1', '1h')):
    rs = resample(m1all.loc['2026-06-29':'2026-10-09 23:59'][['open', 'high', 'low', 'close', 'tick_volume']], rule)
    f = load(tf).loc['2026-06-29':'2026-10-09 23:59']
    j = rs.join(f[['open', 'high', 'low', 'close', 'tick_volume']], rsuffix='_f', how='outer')
    bad = j.isna().any(axis=1).sum()
    diff = sum(int((np.abs(j[c] - j[c + '_f']) > 1e-9).sum()) for c in ['open', 'high', 'low', 'close', 'tick_volume'])
    print(f"{tf} file vs M1 resampled (29 Jun - 9 Oct): {len(j)} candles, missing on one side {bad}, differing fields {diff}")

rows_out = []
for cls, name, t0, t1 in RANGES:
    m1 = sel('M1', t0, t1)
    base = {cname(c): build(m1, c) for c in CONFIGS}
    for tf in TFS:
        d = sel(tf, t0, t1)
        for c in CONFIGS:
            p0 = base[cname(c)]; p = build(d, c)
            same_grid = p['rows'] == p0['rows'] and abs(p['base'] - p0['base']) < 1e-9 and abs(p['step'] - p0['step']) < 1e-9
            a0 = np.array(p0['tot']) / p0['sum']; a = np.array(p['tot']) / p['sum'] if same_grid else None
            dist = 0.5 * np.abs(a0 - a).sum() if same_grid else np.nan
            rows_out.append(dict(cls=cls, range=name, tf=tf, cfg=cname(c), n1=len(m1), n=len(d), step=p0['step'],
                                 dPOC=p['pocPx'] - p0['pocPx'], dVAH=p['vah'] - p0['vah'], dVAL=p['val'] - p0['val'],
                                 pocRows=abs(p['poc'] - p0['poc']), dist=dist, same_grid=same_grid,
                                 sh0=p0['acc'] / p0['sum'], sh=p['acc'] / p['sum'], vw0=p0['vah'] - p0['val'], vw=p['vah'] - p['val']))
R = pd.DataFrame(rows_out)
R.to_csv('/mnt/project-files/xauusd-volume-profile/review/maths/precision_rows.csv', index=False)
print(f"\nprofiles compared: {len(R)}; grids identical to the M1 grid: {R.same_grid.mean()*100:.0f}%")
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
for col in ('dPOC', 'dVAH', 'dVAL'): R['a' + col] = R[col].abs()
R['aVAw'] = (R.vw - R.vw0).abs()
print("\nby range length and source TF: median / max |difference| vs M1 in $ (all 6 grids pooled)")
g = R.groupby(['cls', 'tf'], sort=False)
out = g.agg(n=('aPOC'.replace('aPOC', 'adPOC'), 'size'),
            POC_med=('adPOC', 'median'), POC_max=('adPOC', 'max'),
            VAH_med=('adVAH', 'median'), VAH_max=('adVAH', 'max'),
            VAL_med=('adVAL', 'median'), VAL_max=('adVAL', 'max'),
            POC_moved=('pocRows', lambda s: (s > 0).mean()),
            POC_far=('pocRows', lambda s: (s > 2).mean()),
            dist_med=('dist', 'median'), dist_max=('dist', 'max'))
print(out.round(3).to_string())
print("\n  POC_moved = share of profiles whose POC row differs from the M1 one; POC_far = more than 2 rows away;")
print("  dist = share of the volume that sits in different rows (half the L1 distance of the normalised profiles)")
print("\nby grid and source TF, day-and-shorter ranges only: median |dPOC| / |dVAH| / |dVAL| in $ and median step")
s = R[R.cls.isin(['2h', '4h', '8h', 'day'])].groupby(['cfg', 'tf'], sort=False).agg(
    step=('step', 'median'), POC=('adPOC', 'median'), VAH=('adVAH', 'median'), VAL=('adVAL', 'median'),
    POC_max=('adPOC', 'max'), dist=('dist', 'median'))
print(s.round(3).to_string())
print("\nevery profile (M1 vs other TF), $ differences:")
print(R[['range', 'tf', 'cfg', 'n1', 'n', 'step', 'dPOC', 'dVAH', 'dVAL', 'pocRows', 'dist', 'sh0', 'sh']].round(3).to_string(index=False))
