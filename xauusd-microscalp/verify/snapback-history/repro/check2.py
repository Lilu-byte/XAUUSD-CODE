"""Execution realism: stopped trades, slippage beyond the stop, finer-resolution replays (M5 from 2025-05, M1 from
2026-06-26), real entry spread from M1 first-minute bars, the wide-spread trades, top trades."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro')
from vlib import *

d = load(M15_FILE, 15, 'month_hour'); dates = pd.DatetimeIndex(np.unique(d.date.values))
s, ar, vw, mv = signal(d); base = d.spr_bar.values + 0.05
T = trades(d, s, base)
T['ar'] = ar[T.i.values]; T['move'] = mv[T.i.values]
T['nxt_spr'] = d.spr_bar.values[T.i.values + 1]
o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values

# ---- stops
st = T[T.kind != 'time'].copy()
print(f'non-time exits: {len(st)} ({st.kind.value_counts().to_dict()}), TRAIN {int((st.entry < TEST[0]).sum())}, TEST {int((st.entry >= TEST[0]).sum())}')
Tx = trades(d, s, base, stop_fill='extreme').set_index('i')
st['pnl_extreme'] = Tx.loc[st.i, 'pnl'].values
Tn = trades(d, s, base, sl=1e6).set_index('i'); st['pnl_nostop'] = Tn.loc[st.i, 'pnl'].values
print('stopped trades (signal bar, dir, move/AR, pnl exact, pnl at bar extreme, pnl without stop):')
for _, r in st.iterrows():
    print(f"   {r.entry} {r.dir:+d} mv {r.move:+.1f} AR {r.ar:.2f} -> {r.pnl:+.1f} / {r.pnl_extreme:+.1f} / {r.pnl_nostop:+.1f}")
for slip in (1, 3, 5, 10):
    T2 = T.copy(); T2.loc[T2.kind.str.startswith('stop'), 'pnl'] -= slip
    a = stats(T2, dates, *TRAIN); b = stats(T2, dates, *TEST)
    print(f'stop slippage ${slip}: TRAIN {a["per_day"]:+.3f}/d  TEST {b["per_day"]:+.3f}/d')

# ---- top trades
print('top 10 trades:'); tt = T.sort_values('pnl', ascending=False).head(10)
for _, r in tt.iterrows():
    print(f"   {r.entry} {r.dir:+d} mv {r.move:+.1f} AR {r.ar:.2f} pnl {r.pnl:+.1f}")
print('worst 5 days:'); p = per_day(T, dates); print('   ' + '; '.join(f'{k.date()} {v:+.1f}' for k, v in p.sort_values().head(5).items()))
print('best 5 days:  ' + '; '.join(f'{k.date()} {v:+.1f}' for k, v in p.sort_values(ascending=False).head(5).items()))

# ---- wide-spread trades (next-bar recorded spread >= $0.30)
w = T[T.nxt_spr >= 0.30]
print(f'trades with next-bar recorded (minimum) spread >= $0.30: {len(w)}, total ${w.pnl.sum():+.1f}, {w.pnl.mean():+.2f}/tr; '
      f'years {w.entry.dt.year.value_counts().sort_index().to_dict()}; mean recorded spread {w.nxt_spr.mean():.2f}; '
      f'TRAIN share of TRAIN profit {w[w.entry < TEST[0]].pnl.sum() / T[T.entry < TEST[0]].pnl.sum():.0%}')

# ---- M5 replay (2025-05-05 onward): entry at open of the first M5 bar of M15 bar i+1, stop checked on M5 bars,
#      exit at close of the last M5 bar inside M15 bar i+2 (or session end). Spread: M5 recorded + 0.05.
def replay(fine, step, T, label, lat_steps=0):
    fi = fine.index; fpos = pd.Series(np.arange(len(fine)), index=fi)
    fo, fh, fl, fc = fine.open.values, fine.high.values, fine.low.values, fine.close.values
    fs = fine.spr_bar.values + 0.05; ftod = fine.tod.values; flast = fine.last.values
    out = []
    for _, r in T.iterrows():
        i = int(r.i); t_in = d.index[i + 1] + pd.Timedelta(minutes=step * lat_steps)
        t_end = d.index[min(i + 2, len(d) - 1)] + pd.Timedelta(minutes=15)       # end of M15 bar i+2
        if t_in not in fpos.index: out.append(np.nan); continue
        j0 = fpos[t_in]; dr = r.dir
        e = fo[j0] + fs[j0] if dr == 1 else fo[j0]
        px = None
        for j in range(j0, len(fine)):
            a = fs[j]
            if fine.index[j].normalize() != fine.index[j0].normalize(): px = fo[j] if dr == 1 else fo[j] + a; break
            done = (fine.index[j] + pd.Timedelta(minutes=step) >= t_end) or flast[j] or ftod[j] >= END_TOD
            if dr == 1:
                slp = e - 25
                if j > j0 and fo[j] <= slp: px = fo[j]; break
                if fl[j] <= slp: px = slp; break
                if done: px = fc[j]; break
            else:
                slp = e + 25
                if j > j0 and fo[j] + a >= slp: px = fo[j] + a; break
                if fh[j] + a >= slp: px = slp; break
                if done: px = fc[j] + a; break
        out.append((px - e) if dr == 1 else (e - px))
    R = T.copy(); R['pnl_fine'] = out
    ok = R.pnl_fine.notna()
    print(f'{label}: {int(ok.sum())} of {len(R)} trades replayed; M15 sim total ${R.pnl[ok].sum():+.1f} ({R.pnl[ok].mean():+.2f}/tr) vs '
          f'fine replay ${R.pnl_fine[ok].sum():+.1f} ({R.pnl_fine[ok].mean():+.2f}/tr); max |diff| {np.abs(R.pnl - R.pnl_fine)[ok].max():.2f}')
    return R

m5 = load(M5_FILE, 5, 'month_hour')
# data consistency: M15 vs M5 resampled
g = m5[['open', 'high', 'low', 'close']].resample('15min', label='left', closed='left')
r15 = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(), 'close': g.close.last()}).dropna()
jj = d[['open', 'high', 'low', 'close']].join(r15, rsuffix='_5', how='inner')
print(f'M15 vs M5-resampled bars: {len(jj)} common, OHLC match share ' +
      ', '.join(f"{k} {(np.abs(jj[k] - jj[k + '_5']) < 0.005).mean():.4f}" for k in ('open', 'high', 'low', 'close')))
T5 = T[T.entry >= m5.index[0] + pd.Timedelta(hours=1)]
R5 = replay(m5, 5, T5, 'M5 replay (2025-05-05..)')
R5b = replay(m5, 5, T5, 'M5 replay, entry 5 min late (2nd M5 bar)', lat_steps=1)

m1 = load(M1_FILE, 1, 'hour')
T1 = T[T.entry >= m1.index[0] + pd.Timedelta(hours=1)]
R1 = replay(m1, 1, T1, 'M1 replay (2026-06-26..)')
R1b = replay(m1, 1, T1, 'M1 replay, entry 1 min late', lat_steps=1)
# real entry spread: M1 first-minute recorded spread at the entry minute vs M15 recorded spread of bar i+1
fm = m1.spr_bar.reindex(d.index[T1.i.values + 1]).values
print(f'M1-era trades: M15 recorded entry-bar spread mean ${T1.nxt_spr.mean():.3f}; M1 entry-minute recorded spread mean ${np.nanmean(fm):.3f} '
      f'(both are bar minimums; true first-tick spread is higher)')
# same comparison on all M15 bars of the M1 era vs signal bars
allfm = m1.spr_bar.reindex(d.index[(d.index >= m1.index[0])]).values
print(f'   all M15 bars in M1 era: M15 recorded spread mean ${d.spr_bar[d.index >= m1.index[0]].mean():.3f}, '
      f'M1 first-minute mean ${np.nanmean(allfm):.3f}')
