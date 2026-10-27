"""Turn each Market Matrix panel into the trading rule a chart reader would take from it, and score it on XAUUSD.

Position (+1 long, -1 short, 0 flat) is decided on a CLOSED panel bar and held from the next bar's open.
One 0.01 lot ($1 per $1 move). Costs as in gbt.py: spread $0.30 + slippage $0.10 per entry, $0.10 slippage
per exit, swap $0.126 long / $0.046 short per night (triple on Wednesday night). For D1 history before 2016
the swap is scaled by price/4100 (a fixed $0.126 on $400 gold would be ~11% a year). P&L is marked to market
each bar. No stops: the indicator defines none.
Usage: python3 -I test_rules.py
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm

OUT = '/mnt/project-files/xauusd-github-bots/market-matrix/'
SPREAD, SLIP, SW_L, SW_S = gbt.SPREAD, gbt.SLIP, gbt.SWAP_L, gbt.SWAP_S
WIN = {'D1': {'train': ('2005-04-01', '2015-12-31'), 'test': ('2016-01-01', '2026-10-31')},
       'H4': {'train': ('2014-09-01', '2021-12-31'), 'test': ('2022-01-01', '2026-10-31')},
       'H1': {'train': ('2017-06-01', '2021-12-31'), 'test': ('2022-01-01', '2026-10-31')}}
RECENT = ('2022-01-01', '2026-10-31')
COMMON = ('2025-05-01', '2026-10-31')


def sim(d, pos, swap_scaled_before='2016-01-01'):
    """pos aligned to d (decided at bar close). Returns per-bar MTM pnl and trade list."""
    pos = np.nan_to_num(np.asarray(pos, float)).astype(int)
    o, c = d.open.values, d.close.values
    day = d.index.normalize().values
    dow = d.index.dayofweek.values
    scaled = d.index < pd.Timestamp(swap_scaled_before)
    n = len(d); pnl = np.zeros(n); held = np.zeros(n, int)
    cur = 0; ent = 0.0; ei = 0; trades = []
    for i in range(1, n):
        want = pos[i - 1]
        if cur != 0 and day[i] != day[i - 1]:   # rollover between i-1 and i while holding
            nights = 3.0 if dow[i - 1] == 2 else 1.0
            s = (SW_L if cur > 0 else SW_S) * (c[i - 1] / 4100.0 if scaled[i] else 1.0)
            pnl[i] -= nights * s
        if cur != 0 and want != cur:            # exit at this bar's open
            px = o[i] - SLIP if cur > 0 else o[i] + SPREAD + SLIP
            pnl[i] += cur * (px - c[i - 1])
            trades.append((ei, i, cur, ent, px))
            cur = 0
        elif cur != 0:
            pnl[i] += cur * (c[i] - c[i - 1]); held[i] = cur
        if cur == 0 and want != 0:              # enter at this bar's open
            cur = want; ei = i
            ent = o[i] + SPREAD + SLIP if cur > 0 else o[i] - SLIP
            pnl[i] += cur * (c[i] - ent); held[i] = cur
    if cur != 0:                                # still open at the end: marked at the last close
        trades.append((ei, n - 1, cur, ent, c[n - 1]))
    t = pd.DataFrame(trades, columns=['ei', 'xi', 'dir', 'entry', 'exit'])
    t[['ei', 'xi', 'dir']] = t[['ei', 'xi', 'dir']].astype(int)
    t['entry_time'] = d.index[t.ei]; t['exit_time'] = d.index[t.xi]
    t['gross'] = t.dir * (t.exit - t.entry)
    return pd.Series(pnl, d.index), t, pd.Series(held, d.index)


def per_day(p):
    """Bar pnl -> calendar trading-day pnl."""
    return p.groupby(p.index.normalize()).sum()


def metr(pb, d, w):
    p = per_day(pb.loc[w[0]:w[1]])
    eq = p.cumsum()
    px = d.close.groupby(d.index.normalize()).last().shift().reindex(p.index)
    r = p / px
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    m = p.groupby(p.index.to_period('M')).sum()
    return dict(per_day=round(p.mean(), 2), ret_yr=round(r.mean() * 252 * 100, 1), sharpe=round(sh, 2),
                max_dd=round((eq - eq.cummax()).min(), 0), losing_months=f'{(m < 0).sum()}/{len(m)}')


def state(enter_long, exit_long, enter_short, exit_short):
    """Event rules -> position series (enter on the event, hold until the exit event)."""
    el, xl, es, xs = (np.asarray(x, bool) for x in (enter_long, exit_long, enter_short, exit_short))
    out = np.zeros(len(el), int); cur = 0
    for i in range(len(el)):
        if cur == 1 and (xl[i] or es[i]):
            cur = 0
        elif cur == -1 and (xs[i] or el[i]):
            cur = 0
        if cur == 0:
            cur = 1 if el[i] else -1 if es[i] else 0
        out[i] = cur
    return out


def sgn(x): return np.sign(np.nan_to_num(np.asarray(x, float))).astype(int)
def up(x, lvl): x = pd.Series(x); return ((x > lvl) & (x.shift() <= lvl)).values
def dn(x, lvl): x = pd.Series(x); return ((x < lvl) & (x.shift() >= lvl)).values


def rules(p):
    c = p.close
    R = {}
    R['MA stack 20/50/200'] = np.where((c > p.sma20) & (p.sma20 > p.sma50) & (p.sma50 > p.sma200), 1,
                                       np.where((c < p.sma20) & (p.sma20 < p.sma50) & (p.sma50 < p.sma200), -1, 0))
    R['Close vs 200 SMA'] = sgn(c - p.sma200)
    R['Close vs 89 EMA (main chart)'] = sgn(c - p.ema89)
    R['Swing VWAP direction'] = p.vw_dir_live.values
    R['Swing VWAP direction + price side'] = np.where((p.vw_dir_live == 1) & (c > p.vwap_live), 1,
                                                      np.where((p.vw_dir_live == -1) & (c < p.vwap_live), -1, 0))
    R['RSI above/below 50 and its MA'] = np.where((p.rsi > 50) & (p.rsi > p.rsi_ma), 1, np.where((p.rsi < 50) & (p.rsi < p.rsi_ma), -1, 0))
    R['RSI 30/70 reversal, exit at 50'] = state(up(p.rsi, 30), (p.rsi > 50).values, dn(p.rsi, 70), (p.rsi < 50).values)
    R['MACD histogram sign'] = sgn(p.macd_hist)
    R['MACD line sign'] = sgn(p.macd)
    R['RTI vs its signal'] = sgn(p.rti - p.rti_sig)
    R['RTI above/below 50'] = sgn(p.rti - 50)
    R['RTI 20/80 reversal, exit at 50'] = state(up(p.rti, 20), (p.rti > 50).values, dn(p.rti, 80), (p.rti < 50).values)
    R['ASI vs its signal'] = sgn(p.asi - p.asi_sig)
    R['ASI sign'] = sgn(p.asi)
    R['ASI -8/+8 reversal, exit at 0'] = state(up(p.asi, -8), (p.asi > 0).values, dn(p.asi, 8), (p.asi < 0).values)
    R['Range Osc sign (close vs centre)'] = sgn(p.rng)
    R['Range Osc +/-100 breakout, exit at 0'] = state(up(p.rng, 100), (p.rng < 0).values, dn(p.rng, -100), (p.rng > 0).values)
    R['Range Osc +/-100 fade, exit at 0'] = state(up(p.rng, -100), (p.rng > 0).values, dn(p.rng, 100), (p.rng < 0).values)
    votes = (np.where((c > p.sma20) & (p.sma20 > p.sma50), 1, np.where((c < p.sma20) & (p.sma20 < p.sma50), -1, 0))
             + p.vw_dir_live.values + sgn(p.rsi - 50) + sgn(p.macd_hist) + sgn(p.rti - 50) + sgn(p.asi) + sgn(p.rng))
    for k in (4, 5, 6, 7):
        R[f'All panels: {k}+ of 7 agree'] = np.where(votes >= k, 1, np.where(votes <= -k, -1, 0))
    return R, votes


def shift_test(d, pos, w, runs=200, seed=3):
    """Share of circularly time-shifted copies of the same position series (same trades and exposure, timing
    broken) that the real timing beats, on window w."""
    rng = np.random.default_rng(seed)
    real = per_day(sim(d, pos)[0].loc[w[0]:w[1]]).mean()
    n = len(pos); res = []
    for _ in range(runs):
        k = rng.integers(n // 10, n - n // 10)
        res.append(per_day(sim(d, np.roll(pos, k))[0].loc[w[0]:w[1]]).mean())
    return round(100 * (np.array(res) < real).mean(), 0)


def main():
    rows = []
    store = {}
    for tf in ('D1', 'H4', 'H1'):
        d = gbt.load(tf)
        p, anc = mm.all_panels(d)
        R, votes = rules(p)
        hold = np.ones(len(d), int)
        hp = sim(d, hold)[0]
        for name, pos in list(R.items()) + [('Hold 0.01 lot long', hold)]:
            for mode in ('long+short', 'long only'):
                if name.startswith('Hold') and mode == 'long+short':
                    continue
                ps = np.asarray(pos, int) if mode == 'long+short' else np.clip(np.asarray(pos, int), 0, 1)
                pb, t, held = sim(d, ps)
                store[(tf, name, mode)] = pb
                row = dict(tf=tf, rule=name, mode=mode)
                for wn, w in (('train', WIN[tf]['train']), ('test', WIN[tf]['test']), ('22-26', RECENT), ('common', COMMON)):
                    m = metr(pb, d, w)
                    for k, v in m.items():
                        row[f'{wn}_{k}'] = v
                tt = t[(t.entry_time >= WIN[tf]['test'][0])]
                yrs = (d.index[-1] - pd.Timestamp(WIN[tf]['test'][0])).days / 365.25
                row['test_trades_yr'] = round(len(tt) / yrs, 1)
                row['test_win'] = round((tt.gross > 0).mean() * 100, 0) if len(tt) else np.nan
                row['time_in_mkt'] = round((held.loc[WIN[tf]['test'][0]:] != 0).mean() * 100, 0)
                rows.append(row)
        print(tf, 'done', flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(OUT + 'results.csv', index=False)
    pd.to_pickle(store, OUT + 'code/_bar_pnl.pkl')
    return res


if __name__ == '__main__':
    r = main()
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200); pd.set_option('display.max_columns', 40)
    print(r[['tf', 'rule', 'mode', 'train_sharpe', 'train_ret_yr', 'test_sharpe', 'test_ret_yr', 'test_per_day', '22-26_per_day',
             'common_per_day', 'test_max_dd', 'test_trades_yr', 'test_win', 'time_in_mkt']].to_string())
