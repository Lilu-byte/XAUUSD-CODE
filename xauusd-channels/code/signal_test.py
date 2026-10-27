"""Does a confirmed channel break predict anything? Trade each break: long on an upside break, short (or flat) on a
downside break, hold until the opposite break. Fill at the next bar's open, $0.40 cost per trade, swap per night.
Settings are the v1.10 defaults (shortest stretch by timeframe, 2 closes to confirm, buffer 0.2 ATR, 2 sigma); they were never tuned on returns."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd, gbt, seg
rows = []
for tf in ['H4', 'H1', 'M15', 'M5']:
    d = gbt.load(tf)
    o, h, l, c = [d[k].values for k in ('open', 'high', 'low', 'close')]
    L = {'M5': 40, 'M15': 30}.get(tf, 20)
    _, ev = seg.segment(o, h, l, c, L, 0.2, 0.6, k=2.0, nc=2)
    idx = d.index; day = idx.normalize().values; wd = idx.dayofweek.values
    for mode in ['long+short', 'long only']:
        trades = []; pos = 0; ent = 0
        for t, dr in ev + [(len(c) - 2, 0)]:
            if t + 1 >= len(c): break
            want = dr if mode == 'long+short' else max(dr, 0)
            if dr == 0: want = 0
            if want != pos:
                if pos:
                    px = o[t + 1]; pnl = (px - o[ent]) * pos - 0.40
                    nights = np.unique(day[ent:t + 2]); nn = len(nights) - 1
                    wed = sum(1 for x in nights[:-1] if pd.Timestamp(x).dayofweek == 2)
                    pnl -= (nn + 2 * wed) * (gbt.SWAP_L if pos > 0 else gbt.SWAP_S)
                    trades.append((idx[t + 1], pnl))
                pos = want; ent = t + 1
        tr = pd.DataFrame(trades, columns=['t', 'pnl']).set_index('t')
        days = (idx[-1] - idx[0]).days
        hold = c[-1] - o[0] - days * 0.126 * 5 / 7 * 1.0
        yr = tr.pnl.groupby(tr.index.year).sum()
        rows.append(dict(tf=tf, mode=mode, start=str(idx[0].date()), trades=len(tr), win=round((tr.pnl > 0).mean() * 100),
                         total=round(tr.pnl.sum()), per_day=round(tr.pnl.sum() / days, 2), hold_gold=round(c[-1] - o[0]),
                         years_up=f"{(yr > 0).sum()}/{len(yr)}",
                         dd=round((tr.pnl.cumsum().cummax() - tr.pnl.cumsum()).max())))
r = pd.DataFrame(rows); print(r.to_string()); r.to_csv('../signal_test.csv', index=False)
