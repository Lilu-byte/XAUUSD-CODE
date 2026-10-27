"""TRAIN only (halves A=Jul, B=Aug): strong-candle (marubozu-like) signals on k-minute candles,
filtered by HTF trend, followed or faded. Generalises the theme that edge_halves.py surfaced
(fade marubozu / continuation patterns that run against the M15/H1 trend)."""
from pats import *
H = Harness(); m = H.m1
ok = m.tod.values < END_TOD - 15
A = ok & (m.index < pd.Timestamp('2026-08-01')); B = ok & (m.index >= pd.Timestamp('2026-08-01')) & (m.index < SPLIT)
nA = len(np.unique(m.index[A].date)); nB = len(np.unique(m.index[B].date))
spr = spread_series(m, 'base'); HZ = (1, 2, 3, 5, 10)
FWD = {k: (m.close.shift(-k) - m.close).values for k in HZ}
TRD = {'M15': trend(m, 'M15'), 'H1': trend(m, 'H1'), 'none': np.ones(len(m))}
pos = pd.Series(np.arange(len(m)), index=m.index)

def kcandles(k, rolling):
    """per M1 row: body, range, avgbody(20 prior k-candles), colour of the k-min candle ending at that row."""
    cols = {c: np.full(len(m), np.nan) for c in ('body', 'rng', 'avg', 'col')}
    for p in (range(k) if rolling else [0]):
        d = m.resample(f'{k}min', label='left', closed='left', offset=f'{p}min').agg(
            {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        b = (d.close - d.open).abs(); r = d.high - d.low
        vals = dict(body=b, rng=r, avg=b.rolling(20).mean().shift(1), col=np.sign(d.close - d.open))
        rows = pos.reindex(d.index + pd.Timedelta(minutes=k - 1)).values; g = ~np.isnan(rows); rows = rows[g].astype(int)
        for c, v in vals.items(): cols[c][rows] = np.asarray(v)[g]
    return cols

rows = []
for k in (1, 2, 3):
    for rolling in (False, True):
        if k == 1 and rolling: continue
        K = kcandles(k, rolling)
        for q in (1.0, 1.5, 2.0, 3.0):
            for fr in (0.5, 0.75, 0.9):
                strong = (K['body'] >= q * K['avg']) & (K['body'] >= fr * K['rng'])
                col = np.where(strong, K['col'], 0); col = np.nan_to_num(col)
                for htf in ('none', 'M15', 'H1'):
                    t = TRD[htf]
                    for rel in (('all',) if htf == 'none' else ('against', 'with')):
                        c2 = col if rel == 'all' else np.where(col == (-t if rel == 'against' else t), col, 0)
                        for dirn, mult in (('follow', 1), ('fade', -1)):
                            sg = c2 * mult; r = dict(k=k, roll=rolling, q=q, fr=fr, htf=htf, rel=rel, dir=dirn)
                            for lab, msk, nd in (('A', A, nA), ('B', B, nB)):
                                mm = msk & (sg != 0); r['day' + lab] = mm.sum() / nd
                                for h in HZ: r[f'{lab}{h}'] = np.nanmean(FWD[h][mm] * sg[mm] - spr[mm]) if mm.sum() > 10 else np.nan
                            rows.append(r)
df = pd.DataFrame(rows)
mn = np.minimum(df[[f'A{h}' for h in HZ]].values, df[[f'B{h}' for h in HZ]].values)
df['rob'] = np.nanmax(mn, 1); df['rob_h'] = np.array(HZ)[np.nanargmax(np.nan_to_num(mn, nan=-9), 1)]
df.to_csv('pullback_train.csv', index=False)
pd.set_option('display.width', 250)
print('configs', len(df))
c = ['k','roll','q','fr','htf','rel','dir','dayA','dayB','A1','B1','A3','B3','A5','B5','A10','B10','rob','rob_h']
q = df[(df.dayA >= 3) & (df.dayB >= 3)]
print(q.sort_values('rob', ascending=False)[c].head(25).round(3).to_string(index=False))
print('\nfade vs follow, mean of net5 over all configs:', df.groupby(['rel','dir'])[['A5','B5','A10','B10']].mean().round(3))
