"""(a) engine.run re-implemented with a trade list (checked against the numba engine);
(b) a port of GoldAsiaBreak.mq5 on the same M5 bars. Compare both."""
import os, sys, tempfile
sys.dont_write_bytecode = True                     # never write .pyc into the project code folders
import atexit, shutil
_nb = tempfile.mkdtemp(); os.environ['NUMBA_CACHE_DIR'] = _nb; atexit.register(shutil.rmtree, _nb, True)  # keep numba's cache out of xauusd-5-a-day/code
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-5-a-day/code')
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from engine import prep, sim, SPREAD, SLIP, END
from lib import load, SWAP_LONG, SWAP_SHORT

P = prep('M5'); idx = P['index']
o, h, l, c, sc, day, tod = P['o'], P['h'], P['l'], P['c'], P['sc'], P['day'], P['tod']
sig = P['sigs']['asia_break']
spr_bar = load('M5').reindex(idx).spread.values * 0.01

def engine_trades(tp, sl, scale=True, target=5.0, max_tr=1):
    rows = []; pos = 0; cur = -1; dp = 0.0; nt = 0; done = False
    for i in range(len(c)):
        if day[i] != cur: cur = day[i]; dp = 0.0; nt = 0; done = False
        if pos != 0:
            ex = False; why = ''
            if pos == 1:
                slp = ent - sld; tpp = ent + tpd
                if o[i] <= slp: px = o[i] - SLIP * e_sc; ex = True; why = 'SL'
                elif l[i] <= slp: px = slp - SLIP * e_sc; ex = True; why = 'SL'
                elif h[i] >= tpp: px = tpp; ex = True; why = 'TP'
                elif tod[i] >= END: px = c[i] - SLIP * e_sc; ex = True; why = 'EOD'
                pnl = px - ent if ex else 0
            else:
                a = SPREAD * e_sc; slp = ent + sld; tpp = ent - tpd
                if o[i] + a >= slp: px = o[i] + a + SLIP * e_sc; ex = True; why = 'SL'
                elif h[i] + a >= slp: px = slp + SLIP * e_sc; ex = True; why = 'SL'
                elif l[i] + a <= tpp: px = tpp; ex = True; why = 'TP'
                elif tod[i] >= END: px = c[i] + a + SLIP * e_sc; ex = True; why = 'EOD'
                pnl = ent - px if ex else 0
            if ex:
                pos = 0; dp += pnl / e_sc
                rows[-1].update(exit_time=idx[i], why=why, pnl=pnl / e_sc, pnl_real=pnl, exit_day=cur)
                if dp >= target - 1e-9 or nt >= max_tr: done = True
                continue
        if pos == 0 and not done and tod[i] >= 540 and tod[i] < END - 15 and sig[i] != 0 and nt < max_tr:
            e_sc = sc[i] if scale else 1.0; pos = int(sig[i]); nt += 1
            tpd = tp * e_sc; sld = sl * e_sc
            ent = c[i] + (SPREAD + SLIP) * e_sc if pos == 1 else c[i] - SLIP * e_sc
            rows.append(dict(sig_bar=idx[i], entry_time=idx[i] + pd.Timedelta(minutes=5), dir=pos, entry_px=ent, e_sc=e_sc))
    if pos: rows.pop()
    return pd.DataFrame(rows)

def nights(e, x, d):
    n = pd.date_range(e.normalize(), x.normalize(), freq='D')[1:]
    return sum(3 if k.dayofweek == 3 else 1 for k in n) * (SWAP_LONG if d == 1 else SWAP_SHORT)

def ea_trades(tp, sl, spread='const', slip=SLIP, maxspr=0.80, close_tod=1410, last_entry=15, with_swap=True):
    """GoldAsiaBreak.mq5 on bars: OnTick work happens at each bar's first tick (= bar open)."""
    sp = np.full(len(c), SPREAD) if spread == 'const' else np.maximum(spr_bar, 0)
    dates = idx.normalize().values
    rows = []; pos = 0; traded = None
    asia_hi = {}; asia_lo = {}; asia_n = {}
    for i in range(len(c)):
        dt = dates[i]
        if tod[i] < 540:   # Asian bar (CopyRates dayStart .. dayStart+9h-1)
            asia_hi[dt] = max(asia_hi.get(dt, -1e18), h[i]); asia_lo[dt] = min(asia_lo.get(dt, 1e18), l[i]); asia_n[dt] = asia_n.get(dt, 0) + 1
        # --- first tick of bar i (price = open)
        if pos != 0:
            ex = False
            if pos == 1:
                if o[i] <= SLp: px = o[i] - slip; ex, why = True, 'SL'
                elif o[i] >= TPp: px = o[i]; ex, why = True, 'TP'
                elif tod[i] >= (close_tod[i] if hasattr(close_tod, "__len__") else close_tod): px = o[i] - slip; ex, why = True, 'EOD'
            else:
                a = sp[i]
                if o[i] + a >= SLp: px = o[i] + a + slip; ex, why = True, 'SL'
                elif o[i] + a <= TPp: px = o[i] + a; ex, why = True, 'TP'
                elif tod[i] >= (close_tod[i] if hasattr(close_tod, "__len__") else close_tod): px = o[i] + a + slip; ex, why = True, 'EOD'
            if ex:
                rows[-1].update(exit_time=idx[i], why=why, exit_px=px); pos = 0
        if pos == 0 and traded != dt and tod[i] >= 540 and tod[i] < (close_tod[i] if hasattr(close_tod, "__len__") else close_tod) - last_entry and i > 0:
            if asia_n.get(dt, 0) >= 12:
                c1 = c[i - 1]; d = 1 if c1 > asia_hi[dt] else (-1 if c1 < asia_lo[dt] else 0)
                if d != 0 and not (maxspr > 0 and sp[i] > maxspr):
                    pos = d; traded = dt
                    if d == 1: ent = o[i] + sp[i] + slip; SLp = ent - sl; TPp = ent + tp
                    else: ent = o[i] - slip; SLp = ent + sl; TPp = ent - tp
                    rows.append(dict(entry_time=idx[i], dir=d, entry_px=ent))
        # --- rest of bar i: broker-side SL/TP (SL first if both)
        if pos != 0:
            if pos == 1:
                if l[i] <= SLp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='SL', exit_px=SLp - slip); pos = 0
                elif h[i] >= TPp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='TP', exit_px=TPp); pos = 0
            else:
                a = sp[i]
                if h[i] + a >= SLp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='SL', exit_px=SLp + slip); pos = 0
                elif l[i] + a <= TPp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='TP', exit_px=TPp); pos = 0
    if pos: rows.pop()
    tr = pd.DataFrame(rows)
    tr['pnl_gross'] = np.where(tr.dir == 1, tr.exit_px - tr.entry_px, tr.entry_px - tr.exit_px)
    tr['swap'] = [nights(e, x, d) for e, x, d in zip(tr.entry_time, tr.exit_time, tr.dir)] if with_swap else 0.0
    tr['pnl'] = tr.pnl_gross - tr.swap
    tr['nights'] = [len(pd.date_range(e.normalize(), x.normalize(), freq='D')) - 1 for e, x in zip(tr.entry_time, tr.exit_time)]
    return tr

days = pd.bdate_range('2025-05-06', '2026-10-09')
def per_day(tr, col='pnl', when='exit_time'):
    return tr.groupby(tr[when].dt.normalize())[col].sum().reindex(days, fill_value=0)

if __name__ == '__main__':
    for tp, sl in ((5, 50), (8, 50)):
        print(f'===== TP {tp} SL {sl}')
        ref = sim(P, 'asia_break', 'any', 540, tp, sl).pnl.reindex(days, fill_value=0)
        E = engine_trades(tp, sl)
        chk = per_day(E)
        print('engine re-impl matches numba engine daily pnl:', np.allclose(chk.values, ref.values), '| engine $/day', round(ref.mean(), 3), 'trades', len(E))
        E1 = engine_trades(tp, sl, scale=False)
        print('engine without price scaling: $/day', round(per_day(E1).mean(), 3))
        print('engine exits by reason:', E.why.value_counts().to_dict(), '| overnight holds:', (E.exit_time.dt.normalize() != E.entry_time.dt.normalize()).sum())
        for name, kw in (('EA port, const spread 0.30, no swap', dict(with_swap=False)),
                         ('EA port, const spread 0.30, swap', dict()),
                         ('EA port, bar spread, swap', dict(spread='bar')),
                         ('EA port, bar spread, swap, no slip', dict(spread='bar', slip=0.0))):
            A = ea_trades(tp, sl, **kw)
            pdA = per_day(A)
            print(f'{name}: trades {len(A)}, $/day {pdA.mean():.3f}, total {A.pnl.sum():.0f}, exits {A.why.value_counts().to_dict()}, '
                  f'overnight {(A.nights > 0).sum()} (swap ${A.swap.sum():.0f}), max nights {A.nights.max()}')
        A = ea_trades(tp, sl, with_swap=False)
        # trade-list match vs engine (scaled, as reported)
        m = E.merge(A, on='entry_time', how='outer', suffixes=('_g', '_a'), indicator=True)
        b = m[m._merge == 'both']
        print('match vs engine: both', len(b), 'engine-only', (m._merge == 'left_only').sum(), 'EA-only', (m._merge == 'right_only').sum(),
              '| same dir', (b.dir_g == b.dir_a).sum(), '| same exit reason', (b.why_g == b.why_a).sum(),
              '| same exit bar', ((b.exit_time_g - b.exit_time_a).abs() <= pd.Timedelta(minutes=5)).sum())
        diff = b.why_g + '->' + b.why_a
        print('   exit reason changes (engine->EA):', diff[b.why_g != b.why_a].value_counts().to_dict())
        print('   pnl on matched trades: engine (scaled $)', round(b.pnl_g.sum(), 0), 'engine real $', round(b.pnl_real.sum(), 0), 'EA', round(b.pnl_a.sum(), 0))
        if tp == 5:
            om = m[m._merge != 'both'].copy(); om['d'] = om.entry_time.dt.normalize()
            print('   unmatched entries by month:', om.groupby([om.d.dt.to_period('M'), om._merge]).size().unstack(fill_value=0).to_dict())
            pre = b.entry_time < '2026-03-01'
            print('   matched pre-Mar-2026:', pre.sum(), 'same exit reason', (b.why_g == b.why_a)[pre].sum(), '| post:', (~pre).sum(), 'same exit reason', (b.why_g == b.why_a)[~pre].sum())
