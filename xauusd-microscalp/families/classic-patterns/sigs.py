"""Named candidate signals (all parameters chosen on TRAIN in edge_scan / edge_halves / pullback_scan)."""
from pats import *

_pos = None
def kc(m, k, rolling):
    pos = pd.Series(np.arange(len(m)), index=m.index)
    cols = {c: np.full(len(m), np.nan) for c in ('body', 'rng', 'avg', 'col')}
    for p in (range(k) if rolling else [0]):
        d = m.resample(f'{k}min', label='left', closed='left', offset=f'{p}min').agg(
            {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        b = (d.close - d.open).abs(); r = d.high - d.low
        vals = dict(body=b, rng=r, avg=b.rolling(20).mean().shift(1), col=np.sign(d.close - d.open))
        rows = pos.reindex(d.index + pd.Timedelta(minutes=k - 1)).values; g = ~np.isnan(rows); rows = rows[g].astype(int)
        for c, v in vals.items(): cols[c][rows] = np.asarray(v)[g]
    return cols

def pullback(m, k, rolling, q, fr, htf):
    """Strong k-min candle (body >= q*avg body of prior 20, body >= fr*range) whose colour is AGAINST
    the htf EMA20/80 trend -> enter in the trend direction (i.e. fade the candle)."""
    K = kc(m, k, rolling); t = trend(m, htf)
    strong = (K['body'] >= q * K['avg']) & (K['body'] >= fr * K['rng'])
    col = np.nan_to_num(np.where(strong, K['col'], 0))
    return np.where(col == -t, -col, 0).astype(float)

def pattern(m, k, mode, name, filt='none', dirn='follow'):
    s = on_m1(m, k, mode)[name]
    if filt != 'none':
        tf, w = filt.split('_'); t = trend(m, tf)
        s = np.where((np.sign(s) == t) if w == 'with' else (np.sign(s) == -t), s, 0)
    return np.sign(s) * (1 if dirn == 'follow' else -1)

def candidates(m):
    C = {}
    C['PB_M3_q2_H1'] = pullback(m, 3, False, 2.0, 0.9, 'H1')
    C['PB_M3_q2_M15'] = pullback(m, 3, False, 2.0, 0.9, 'M15')
    C['PB_M2_q1_H1'] = pullback(m, 2, False, 1.0, 0.9, 'H1')
    C['PB_M3roll_q1.5_M15'] = pullback(m, 3, True, 1.5, 0.9, 'M15')
    C['PB_M3roll_q2_M15'] = pullback(m, 3, True, 2.0, 0.9, 'M15')
    C['votecont_M2_H1against_fade'] = pattern(m, 2, 'fixed', 'vote_cont', 'H1_against', 'fade')
    C['votecont_M3roll_M15against_fade'] = pattern(m, 3, 'rolling', 'vote_cont', 'M15_against', 'fade')
    C['morningstar_M2roll_H1with_fade'] = pattern(m, 2, 'rolling', 'morning_star', 'H1_with', 'fade')
    C['piercing_M3_H1with_fade'] = pattern(m, 3, 'fixed', 'piercing', 'H1_with', 'fade')
    C['voteall_M1_follow'] = pattern(m, 1, 'fixed', 'vote_all')
    C['voterev_M3roll_follow'] = pattern(m, 3, 'rolling', 'vote_rev')
    return C
