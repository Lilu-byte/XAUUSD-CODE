"""Quick replays of the three other EAs in the archive (18 Oct 2026), one 0.01 lot per unit,
project costs (spread $0.30 + slip $0.10, swap $0.126 long / $0.046 short a night, triple into Thursday).
Server time = New York + 7 h in this export (session opens 01:00 = 18:00 NY all year).
"""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import pdh as P

SP, SL_, SWL, SWS = 0.30, 0.10, 0.126, 0.046


def nmult(prev_day, day):
    k = pd.date_range(prev_day, day, freq='D')[1:]
    return sum(3 if z.dayofweek == 3 else 1 for z in k)


def summary(name, r, start, end):
    r = r[(r.exit_time >= start) & (r.exit_time <= end)]
    nd = len(pd.bdate_range(start, end))
    eq = r.pnl.cumsum()
    y = r.groupby(r.exit_time.dt.year).pnl.sum().round(0).astype(int).to_dict()
    print(f'{name} {start}..{end}: trades {len(r)}, $/day {r.pnl.sum()/nd:.2f}, total ${r.pnl.sum():.0f}, '
          f'closed dd ${(eq-eq.cummax()).min():.0f}, by year {y}')


# ---------------------------------------------------------------- Turtle D1 (long only, System 2)
def turtle(entry=55, exit_=20, n_=20, stopn=2.0, sizing=None):
    d = P.load('D1'); o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    N = P.wilder_atr(d, n_).values
    hh = d.high.rolling(entry).max().shift(1).values; ll = d.low.rolling(exit_).min().shift(1).values
    t = d.index; rows = []; pos = False; skipped = 0
    for i in range(entry + 1, len(d)):
        if pos:
            sl = max(sl, ll[i])
            if o[i] <= sl: px = o[i] - SL_
            elif l[i] <= sl: px = sl - SL_
            else: continue
            sw = nmult(t[ei], t[i]) * SWL
            rows.append(dict(entry_time=t[ei], exit_time=t[i], entry_px=ent, exit_px=px, R=(px-ent-sw)/(stopn*N[ei-1]), pnl=px-ent-sw))
            pos = False
            continue
        lvl = hh[i]
        if h[i] + SP >= lvl:
            if sizing is not None and np.floor(sizing / (stopn * N[i - 1])) < 1: skipped += 1; continue
            ent = (max(o[i] + SP, lvl)) + SL_; sl = ent - SL_ - stopn * N[i - 1]; ei = i; pos = True
    r = pd.DataFrame(rows); r.attrs['skipped'] = skipped
    return r


# ---------------------------------------------------------------- EWMAC H1
def ewmac(fast=16, slow=64, vol=100, div=2.11, cap=2.0):
    d = P.load('H1'); c = d.close
    raw = (c.ewm(span=fast, adjust=False).mean() - c.ewm(span=slow, adjust=False).mean()) / c.diff().ewm(span=vol, adjust=False).std()
    tgt = np.round(np.clip(raw / div, 0, cap) * 2).values
    o = d.open.values; t = d.index; day = t.normalize()
    pos = 0; pnl = np.zeros(len(d)); cur = 0
    for i in range(1, len(d)):
        # hold `pos` from open i-1 to open i
        pnl[i] += pos * (o[i] - o[i - 1])
        if day[i] != day[i - 1]: pnl[i] -= pos * SWL * nmult(day[i - 1], day[i])
        want = int(tgt[i - 1]) if np.isfinite(tgt[i - 1]) else 0
        if abs(want - pos) >= 1:
            dq = want - pos
            pnl[i] -= dq * (SP + SL_) if dq > 0 else -dq * SL_   # buy at ask+slip, sell at bid-slip
            pos = want
    s = pd.Series(pnl, index=t)
    return s


# ---------------------------------------------------------------- FOMC follow H1
FOMC = '20160127,20160316,20160427,20160615,20160727,20160921,20161102,20161214,20170201,20170315,20170503,20170614,20170726,20170920,20171101,20171213,20180131,20180321,20180502,20180613,20180801,20180926,20181108,20181219,20190130,20190320,20190501,20190619,20190731,20190918,20191030,20191211,20200129,20200429,20200610,20200729,20200916,20201105,20201216,20210127,20210317,20210428,20210616,20210728,20210922,20211103,20211215,20220126,20220316,20220504,20220615,20220727,20220921,20221102,20221214,20230201,20230322,20230503,20230614,20230726,20230920,20231101,20231213,20240131,20240320,20240501,20240612,20240731,20240918,20241107,20241218,20250129,20250319,20250507,20250618,20250730,20250917,20251029,20251210,20260128,20260318,20260429,20260617,20260729,20260916,20261028,20261209'.split(',')


def fomc(trail=2.0, sizing=None):
    d = P.load('H1'); o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    pc = d.close.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().shift(1).values   # EA: ATR of bars up to the one before the signal bar
    t = d.index; pos_ = {ts: k for k, ts in enumerate(t)}
    rows = []; skipped = 0
    for ds in FOMC:
        k = pos_.get(pd.Timestamp(ds) + pd.Timedelta(hours=21))       # 14:00 NY bar
        if k is None or k + 1 >= len(d) or t[k + 1] != t[k] + pd.Timedelta(hours=1): continue
        if c[k] == o[k]: continue
        dr = 1 if c[k] > o[k] else -1
        i = k + 1
        if dr == 1: ent = o[i] + SP + SL_; sl = l[k] - SP - SL_
        else: ent = o[i] - SL_; sl = h[k] + SP + SL_ - SP   # short stop as a bid level (ask = bid + spread)
        if sizing is not None and np.floor(sizing / abs(ent - sl)) < 1: skipped += 1; continue
        exit_at = pd.Timestamp(ds) + pd.Timedelta(hours=25)              # 18:00 NY = 01:00 server next day
        j = i; px = None
        while j < len(d):
            if t[j] >= exit_at: px = (o[j] - SL_) if dr == 1 else (o[j] + SP + SL_); break
            if j > i:   # trail from the previous close
                w = c[j - 1] - trail * atr[j - 1] if dr == 1 else c[j - 1] + trail * atr[j - 1]
                if (dr == 1 and w > sl) or (dr == -1 and w < sl): sl = w
            if dr == 1 and l[j] <= sl: px = min(o[j], sl) - SL_; break
            if dr == -1 and h[j] >= sl: px = max(o[j], sl) + SP + SL_; break
            j += 1
        sw = (SWL if dr == 1 else SWS) * nmult(t[i].normalize(), t[j].normalize())
        g = (px - ent) * dr - sw
        rows.append(dict(entry_time=t[i], exit_time=t[j], dir=dr, entry_px=ent, exit_px=px, R=g / abs(ent - sl if False else (o[i] - (l[k] if dr == 1 else h[k])) or 1), pnl=g))
    r = pd.DataFrame(rows); r.attrs['skipped'] = skipped
    return r


if __name__ == '__main__':
    tu = turtle()
    print('Turtle trades', len(tu), 'mean R %.2f' % tu.R.mean())
    summary('Turtle D1 0.01 lot', tu, '2004-06-11', '2026-10-09')
    summary('Turtle D1 0.01 lot', tu, '2016-08-01', '2026-10-09')
    summary('Turtle D1 0.01 lot', tu, '2025-05-06', '2026-10-09')
    for risk in (0.5, 1.0):
        x = turtle(sizing=3000 * risk / 100)
        print(f'Turtle with EA sizing at {risk}% of $3,000: trades {len(x)}, last entry',
              x.entry_time.max().date() if len(x) else None, 'skipped', x.attrs['skipped'])
    d1 = P.load('D1')
    for a, b in (('2004-06-11', '2026-10-09'), ('2016-08-01', '2026-10-09'), ('2025-05-06', '2026-10-09')):
        x = d1[a:b].close; nd = len(pd.bdate_range(a, b))
        print(f'  hold 0.01 lot {a}..{b}: $/day {(x.iloc[-1]-x.iloc[0]-0.4-0.126*(x.index[-1]-x.index[0]).days)/nd:.2f}')

    e = ewmac()
    for a, b in (('2016-08-01', '2026-10-09'), ('2016-08-01', '2021-06-30'), ('2021-07-01', '2026-10-09'), ('2025-05-06', '2026-10-09')):
        s = e[a:b]; dd = s.groupby(s.index.normalize()).sum(); eq = dd.cumsum()
        print(f'EWMAC H1 (0-4 units of 0.01) {a}..{b}: $/day {s.sum()/len(pd.bdate_range(a,b)):.2f}, total ${s.sum():.0f}, '
              f'dd ${(eq-eq.cummax()).min():.0f}, by year', s.groupby(s.index.year).sum().round(0).astype(int).to_dict())

    f = fomc()
    print('FOMC trades', len(f), 'win %.2f' % (f.pnl > 0).mean())
    summary('FOMC H1 0.01 lot', f, '2016-01-01', '2026-10-09')
    x = fomc(sizing=15.0); print('FOMC with EA sizing (0.5% of $3,000): trades', len(x), 'skipped', x.attrs['skipped'],
                                  'last', x.entry_time.max().date() if len(x) else None)
