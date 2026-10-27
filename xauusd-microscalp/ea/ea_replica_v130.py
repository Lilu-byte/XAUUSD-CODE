"""Python copy of GoldMicroScalp.mq5 v1.30's entry rules, scored with mlib v2 (FAIR fills).
Builds on ea_replica.py (v1.10 signals, checked bar by bar against the MQL5 code) and adds the v1.30 filters:
  - session window: signal bar opening from SESS_FROM up to (not including) SESS_TO, server time
  - spread: the next bar's spread must be at most SPREAD_PCT % of the module's take profit (and <= 50 points)
  - body: PB's n-minute candle body >= BODY_PB (0.8) x the average range of the previous 20 such candles;
          CP's last candle body >= BODY_CP (0.5) x the average range of the previous 20 M1 bars
  - CP: only the enabled patterns vote (default: engulfing, morning/evening star, three soldiers/crows)
  - optional M5 alignment: the last M5 candle closed by the signal time closed in the trade's direction
    ('candle'), or the M5 EMA(9) rose/fell over that candle ('ema'); PB and CP only unless fades=True
Exits: take profit from the entry, first stop beyond the spread, holding time, 22:58 close, $15 daily stop.
The trailing stop is NOT modelled, and the take profit and first stop are barely modelled either: with a $0.25
target and a ~$0.74 stop, almost every trade is decided inside its first minute, which 1-minute candles can't
show. The FAIR fill rule then values most trades at about minus the spread, so the -$/trade figure is set by
that assumption; the script also prints the other fill rules (stop first ... target first) as a range.
Costs: the spread MT5 recorded on the entry bar plus $0.05 slippage; the spread filter sees the recorded spread.
Run: python3 -I ea_replica_v130.py   (train grid, defaults on train and test, random-direction check,
     fill-free move vs spread, writes expected_entries_v130.csv)
"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-candles/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import itertools
import numpy as np, pandas as pd
from mlib import Harness, SPLIT, FILL, spread_series, resample, load, ema, random_like
from patterns import detect
from ea_sim import _sim_next
import ea_replica as R

PAT_GROUPS = {'engulf': ['Bullish engulfing', 'Bearish engulfing'], 'star': ['Morning star', 'Evening star'],
              'three': ['Three white soldiers', 'Three black crows'], 'hammer': ['Hammer', 'Hanging man'],
              'invhammer': ['Inverted hammer', 'Shooting star'], 'harami': ['Bullish harami', 'Bearish harami'],
              'piercing': ['Piercing line', 'Dark cloud cover'], 'doji': ['Doji after fall', 'Doji after rise']}
CP_DEFAULT = ('engulf', 'star', 'three')

# v1.30 defaults (EA input names in brackets)
D = dict(tp=0.25,            # [InpPBTP ... InpCPTP] take profit $ from the entry
         sl=0.60,            # [InpPBSL ... InpCPSL] first stop $ beyond the spread
         hold={'PB': 20, 'SF': 5, 'QB': 5, 'CP': 5}, cap={'PB': 3, 'SF': 3, 'QB': 3, 'CP': 5},
         spread_pct=50,      # [InpMaxSpreadPctTP]
         sess=(15 * 60, 19 * 60),   # [InpSessionStart, InpSessionEnd]
         body_pb=0.8,        # [InpPBMinBody]
         body_cp=0.5,        # [InpCPMinBody]
         m5='off', fades=False)


def pb_signal(m, trend, n=2, k=1.0, maru=0.9, body_min=0.0):
    c = resample(m, n)
    body = (c.close - c.open).abs(); rng = c.high - c.low
    avg = body.shift(1).rolling(20).mean(); avgr = rng.shift(1).rolling(20).mean()
    colour = np.sign(c.close - c.open)
    hit = (body >= k * avg) & (body >= maru * rng) & (rng > 0) & (body >= body_min * avgr)
    raw = pd.Series(np.where(hit, -colour, 0.0), index=c.index)
    known = pd.Series(raw.values, index=c.index + pd.Timedelta(minutes=n))
    v = known.reindex(m.index + pd.Timedelta(minutes=1)).fillna(0).values
    return np.where(v == trend, v, 0)


_P = {}
def cp_signal(m, trend, groups=CP_DEFAULT, body_min=0.0, use_trend=True):
    if 'P' not in _P: _P['P'] = detect(m[['open', 'high', 'low', 'close']])
    P = _P['P']
    names = [n for g in groups for n in PAT_GROUPS[g]]
    v = np.sign(sum(P[n].values for n in names)) if names else np.zeros(len(m))
    body = (m.close - m.open).abs(); avgr = (m.high - m.low).shift(1).rolling(20).mean()
    v = np.where((body >= body_min * avgr).values, v, 0)
    return np.where(v == trend, v, 0) if use_trend else v


def m5_dir(m, mode, period=9):
    """Direction of the last M5 candle closed by each M1 bar's close (mode 'candle'), or of the M5 EMA over it ('ema')."""
    if mode == 'off': return None
    m5 = load('M5')
    if mode == 'candle': v = np.sign(m5.close - m5.open).values
    else:
        e = ema(m5.close, period); v = np.sign(e - e.shift(1)).fillna(0).values
    known = pd.Series(v, index=m5.index + pd.Timedelta(minutes=5))
    at = m.index + pd.Timedelta(minutes=1)
    return known.reindex(known.index.union(at)).ffill().reindex(at).fillna(0).values


def signals(H, tr, p):
    m = H.m1
    S = {'PB': pb_signal(m, tr, body_min=p['body_pb']), 'SF': R.sig_spike_fade(m), 'QB': R.sig_quarter_fade(m),
         'CP': cp_signal(m, tr, p.get('groups', CP_DEFAULT), p['body_cp'])}
    a = m5_dir(m, p['m5'])
    if a is not None:
        for k in (('PB', 'CP', 'SF', 'QB') if p['fades'] else ('PB', 'CP')):
            S[k] = np.where(S[k] == a, S[k], 0)
    t0, t1 = p['sess']
    tod = m.tod.values
    ins = (tod >= t0) & (tod < t1) if t0 <= t1 else (tod >= t0) | (tod < t1)
    return {k: np.where(ins, np.sign(np.nan_to_num(v)), 0).astype(np.int64) for k, v in S.items()}


def run_module(H, s, tp, sl, hold, cap, spread_pct, spread='base', filt='bar', fill='FAIR'):
    m = H.m1
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    seen = spread_series(m, filt)                                  # spread the EA sees at entry (recorded, or +$0.05)
    nxt = np.r_[seen[1:], 99.0]
    lim = min(0.50, spread_pct / 100.0 * tp) if spread_pct > 0 else 0.50
    s = np.where((gap == 60) & (nxt <= lim + 1e-9), s, 0)
    spr = H._spr[spread]
    # first stop is measured beyond the spread: distance from the entry = sl + spread at entry (use the next bar's)
    slx = sl + float(np.median(np.r_[spr[1:], spr[-1]][s != 0])) if (s != 0).any() else sl
    dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, spr, H.tod, H.day, H.last, s,
                                         float(tp), float(slx), int(hold), int(cap), FILL[fill], 0.0, 0.0, 0)
    return pd.DataFrame({'entry': m.index[ti], 'ei': ti, 'xi': np.where(to >= 0, to, ti), 'dir': tdr, 'pnl': tpn})


def run(H, tr, p, spread='base', filt='bar', S=None, daily=15.0, fill='FAIR'):
    S = signals(H, tr, p) if S is None else S
    out = []
    for k, s in S.items():
        T = run_module(H, s, p['tp'], p['sl'], p['hold'][k], p['cap'][k], p['spread_pct'], spread, filt, fill)
        T['module'] = k; out.append(T)
    T = pd.concat(out).sort_values('entry')
    return (R.daily_stop(T, daily) if daily > 0 else T), S


def score(T, dates, per):
    sel = (dates < SPLIT) if per == 'train' else (dates >= SPLIT)
    p = R.per_day(T, dates)[sel]; tt = T[(T.entry >= SPLIT) == (per == 'test')]
    eq = p.cumsum()
    return dict(per_day=round(p.mean(), 2), trades_day=round(len(tt) / sel.sum(), 1),
                per_trade=round(tt.pnl.mean(), 3) if len(tt) else np.nan, win=round((tt.pnl > 0).mean(), 2) if len(tt) else np.nan,
                losing_days=round((p < 0).mean(), 2), worst_day=round(p.min(), 1), max_dd=round((eq - eq.cummax()).min(), 1))


def move_vs_spread(H, S, horizons=(1, 2, 3, 5)):
    """Fill-free check: average move of the price in the trade's direction from the entry (next bar open) vs the spread paid."""
    m = H.m1; o = m.open.values; spr = H._spr['base']
    rows = []
    for per in ('train', 'test'):
        sel = (m.index < SPLIT) if per == 'train' else (m.index >= SPLIT)
        for k, s in list(S.items()) + [('ALL', None)]:
            sig = sum(S.values()) if s is None else s
            sig = np.sign(sig)
            idx = np.where((sig != 0) & sel)[0]; idx = idx[idx + max(horizons) + 1 < len(m)]
            if not len(idx): continue
            r = dict(period=per, module=k, n=len(idx), spread=round(spr[idx + 1].mean(), 3))
            for h in horizons:
                r[f'move_{h}m'] = round(((o[idx + 1 + h] - o[idx + 1]) * sig[idx]).mean(), 3)
            rows.append(r)
    return pd.DataFrame(rows)


if __name__ == '__main__':
    H = Harness(); tr = R.h1_trend(H.m1)
    pd.set_option('display.width', 220)
    # 1) small grid on the TUNING weeks only (inside David's ranges)
    rows = []
    for tp, mult, pct, body, m5 in itertools.product((0.15, 0.20, 0.25, 0.30), (2.0, 2.5, 3.0), (40, 50),
                                                       (0.0, 0.5, 0.8), ('off', 'candle', 'ema')):
        p = dict(D, tp=tp, sl=round(tp * mult, 2), spread_pct=pct, body_pb=body, body_cp=body, m5=m5)
        T, _ = run(H, tr, p)
        te = score(T, H.dates, 'test')
        rows.append(dict(tp=tp, sl=p['sl'], pct=pct, body=body, m5=m5, **{f'tr_{k}': v for k, v in score(T, H.dates, 'train').items()},
                         te_per_day=te['per_day'], te_trades_day=te['trades_day']))
    G = pd.DataFrame(rows).sort_values('tr_per_day', ascending=False)
    G.to_csv('/mnt/project-files/xauusd-microscalp/ea/v130_grid.csv', index=False)
    print('grid (216 versions), best 12 on the tuning weeks:'); print(G.head(12).to_string(index=False))
    print('share of versions making money: train', round((G.tr_per_day > 0).mean(), 3), ' test', round((G.te_per_day > 0).mean(), 3),
          '| versions with no test trades:', int((G.te_trades_day == 0).sum()), 'of', len(G))
    # 2) defaults
    for name, kw in (('v1.30 defaults', dict(spread='base', filt='bar')), ('same, live spread $0.05 above recorded', dict(spread='base', filt='base')),
                     ('same, recorded spread, no slippage', dict(spread='bar', filt='bar')), ('same, no daily stop', dict(daily=0.0)),
                     ('fill rule: stop first', dict(fill='STOP')), ('fill rule: 1-min OHLC path', dict(fill='OHLC')),
                     ('fill rule: target first', dict(fill='TARGET'))):
        T, S = run(H, tr, D, **kw)
        print(f'{name:34s} TRAIN', score(T, H.dates, 'train')); print(f'{"":34s} TEST ', score(T, H.dates, 'test'))
    T, S = run(H, tr, D)
    print('by module, TEST (with the shared daily stop):')
    for k, g in T.groupby('module'): print('  ', k, score(g, H.dates, 'test'))
    te = T[T.entry >= SPLIT]
    print('TEST trades decided in the entry minute:', round(((te.xi - te.ei) <= 1).mean(), 3),
          '| trades a day by week:', te.groupby(te.entry.dt.to_period('W')).size().div(5).round(1).tolist())
    # gross result before costs, same entries: price change from the entry bar open to the exit, in the trade's direction
    o = H.m1.open.values; c = H.m1.close.values; spr = H._spr['base']
    for per, tt in (('TRAIN', T[T.entry < SPLIT]), ('TEST', te)):
        g = tt.pnl.values + spr[tt.ei.values + 1]
        print(f'{per} per trade before spread and slippage: {g.mean():+.3f} (t {g.mean() / g.std() * np.sqrt(len(g)):.1f}, n {len(g)}), spread+slippage paid {spr[tt.ei.values + 1].mean():.3f}')
    # 3) random directions on the same bars
    for per in ('train', 'test'):
        me = score(T, H.dates, per)['per_day']; rnd = []
        for z in range(200):
            Sr = {k: random_like(v, z * 10 + i).astype(np.int64) for i, (k, v) in enumerate(S.items())}
            Tr, _ = run(H, tr, D, S=Sr); rnd.append(score(Tr, H.dates, per)['per_day'])
        rnd = np.array(rnd)
        print(f'random directions, same bars, {per.upper()} $/day: median {np.median(rnd):+.2f}, best {rnd.max():+.2f}; '
              f'v1.30 {me:+.2f} beats {(rnd < me).mean():.0%} of 200 runs')
    # 4) fill-free: how far price moves the trade's way vs the spread
    print(move_vs_spread(H, S).to_string(index=False))
    # 5) expected entries for MT5's tester (entries only; exits depend on the trailing stop)
    E = T[['entry', 'module', 'dir']].copy(); E['signal_bar'] = E.entry; E['entry_bar'] = E.entry + pd.Timedelta(minutes=1)
    E[['signal_bar', 'entry_bar', 'module', 'dir']].to_csv('/mnt/project-files/xauusd-microscalp/ea/expected_entries_v130.csv', index=False)
    print('expected_entries_v130.csv:', len(E), 'entries')
