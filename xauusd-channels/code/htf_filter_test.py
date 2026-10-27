"""Does the higher timeframe's live label help? Same break trades as signal_test.py, but a long needs the higher timeframe
UP and a short needs it DOWN (as of its last closed candle); otherwise stay flat. Exit on the opposite break or when the
higher timeframe stops agreeing is NOT used: exits are the opposite break, as before."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd, gbt, seg
HTF = {'M5': 'H1', 'M15': 'H4', 'H1': 'D1', 'H4': 'D1'}; MINB = {'M5': 40, 'M15': 30}
def run(tf):
    d = gbt.load(tf); o, h, l, c = [d[k].values for k in ('open', 'high', 'low', 'close')]
    _, ev = seg.segment(o, h, l, c, MINB.get(tf, 20), 0.2, 0.6, k=2.0, nc=2)
    H = gbt.load(HTF[tf]); hl = np.full(len(H), 2)
    seg.segment(*[H[k].values for k in ('open', 'high', 'low', 'close')], 20, 0.2, 0.6, k=2.0, nc=2, live=hl)
    hper = (H.index[1:] - H.index[:-1]).min() if HTF[tf] != 'D1' else pd.Timedelta('1D')
    lper = (d.index[1:] - d.index[:-1]).min()
    hclose = H.index + hper                       # when each higher-timeframe candle closes
    return d, o, c, ev, H, hl, hclose, lper
rows = []
for tf in ['H4', 'H1', 'M15', 'M5']:
    d, o, c, ev, H, hl, hclose, lper = run(tf)
    idx = d.index; day = idx.normalize().values
    for mode in ['long+short', 'long only']:
        trades = []; pos = 0; ent = 0
        for t, dr in ev + [(len(c) - 2, 0)]:
            if t + 1 >= len(c): break
            j = np.searchsorted(hclose, idx[t] + lper, side='right') - 1   # last higher-timeframe candle closed by now
            hlab = hl[j] if j >= 0 else 2
            want = pos
            if dr == 1: want = 1 if hlab == 1 else 0
            if dr == -1: want = (-1 if hlab == -1 else 0) if mode == 'long+short' else 0
            if dr == 0: want = 0
            if want != pos:
                if pos:
                    pnl = (o[t + 1] - o[ent]) * pos - 0.40
                    nights = np.unique(day[ent:t + 2]); nn = len(nights) - 1
                    wed = sum(1 for x in nights[:-1] if pd.Timestamp(x).dayofweek == 2)
                    pnl -= (nn + 2 * wed) * (gbt.SWAP_L if pos > 0 else gbt.SWAP_S)
                    trades.append((idx[t + 1], pnl))
                pos = want; ent = t + 1
        tr = pd.DataFrame(trades, columns=['t', 'pnl']).set_index('t'); days = (idx[-1] - idx[0]).days
        yr = tr.pnl.groupby(tr.index.year).sum()
        rows.append(dict(tf=tf, htf=HTF[tf], mode=mode, trades=len(tr), win=round((tr.pnl > 0).mean() * 100), total=round(tr.pnl.sum()),
                         per_day=round(tr.pnl.sum() / days, 2), hold_gold=round(c[-1] - o[0]), years_up=f"{(yr > 0).sum()}/{len(yr)}",
                         dd=round((tr.pnl.cumsum().cummax() - tr.pnl.cumsum()).max())))
r = pd.DataFrame(rows); print(r.to_string()); r.to_csv('../htf_filter_test.csv', index=False)
