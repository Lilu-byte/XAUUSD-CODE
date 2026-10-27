"""Independent re-run of the Market Matrix headline backtests with gbt.simulate (not test_rules.sim).

Rules are re-written here from their plain-English descriptions (test_rules.py is NOT imported). mm.all_panels is used
only for the indicator values. gbt.simulate books trades; this script then spreads each trade's P&L over the bars it
was open (mark-to-market at bid closes, swap on the bar after each rollover) so that window $/day, Sharpe and drawdown
are measured the same way the main session did. gbt.simulate drops a trade still open at the end of data, so a
synthetic bar (1 minute after the last bar, open = last close) is appended and every open trade is closed there.
Usage: python3 -I verify.py
"""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm

OUT = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest/'
END = '2026-10-09'
W = {'D1': {'train': ('2005-04-01', '2015-12-31'), 'test': ('2016-01-01', END)},
     'H4': {'train': ('2014-09-01', '2021-12-31'), 'test': ('2022-01-01', END)},
     'H1': {'train': ('2017-06-01', '2021-12-31'), 'test': ('2022-01-01', END)}}
R22 = ('2022-01-01', END)
COMMON = ('2025-05-01', END)


def with_tail(d):
    """Append a synthetic bar 1 minute after the last bar with OHLC = last close (same server day)."""
    t = d.index[-1] + pd.Timedelta(minutes=1)
    last = d.iloc[[-1]].copy()
    last.index = [t]
    last[['open', 'high', 'low']] = last.close.values[0]
    return pd.concat([d, last])


def run(d, want):
    """want: 1 = be long after this bar's close, 0 = be flat. Returns gbt trade list and bar MTM pnl (fixed and
    price/4100-scaled swap before 2016)."""
    want = np.asarray(want, float)
    dx = with_tail(d)
    sig = np.append(want, 0.0)
    xl = np.append(want == 0, True)
    xl[-2] = True                      # close any open trade at the synthetic bar's open (= last close - slip)
    t = gbt.simulate(dx, sig, exit_long=xl)
    c = dx.close.values; day = dx.index.normalize().values; dow = dx.index.dayofweek.values
    early = dx.index < pd.Timestamp('2016-01-01')
    n = len(dx)
    gross = np.zeros(n); swf = np.zeros(n); sws = np.zeros(n)
    for ei, xi, en, ex in zip(t.ei.astype(int), t.xi.astype(int), t.entry.values, t.exit.values):
        if xi == ei:
            gross[xi] += ex - en; continue
        gross[ei] += c[ei] - en
        gross[ei + 1:xi] += c[ei + 1:xi] - c[ei:xi - 1]
        gross[xi] += ex - c[xi - 1]
        for j in range(ei + 1, xi + 1):
            if day[j] != day[j - 1]:
                nts = 3.0 if dow[j - 1] == 2 else 1.0
                swf[j] += nts * gbt.SWAP_L
                sws[j] += nts * gbt.SWAP_L * (c[j - 1] / 4100.0 if early[j] else 1.0)
    # consistency: per-trade gbt pnl equals the MTM sum over its bars
    assert abs((gross - swf).sum() - t.pnl.sum()) < 1e-6 * max(1, abs(t.pnl.sum())), ((gross - swf).sum(), t.pnl.sum())
    idx = dx.index
    return t, pd.Series(gross - swf, idx), pd.Series(gross - sws, idx), dx


def daily(bar, d):
    return bar.groupby(bar.index.normalize()).sum()


def metrics(p_day, dx, w):
    p = p_day.loc[w[0]:w[1]]
    eq = np.concatenate([[0.0], p.cumsum().values])
    px = dx.close.groupby(dx.index.normalize()).last().shift().reindex(p.index)
    r = p / px
    m = p.groupby(p.index.to_period('M')).sum()
    return dict(per_day=round(p.mean(), 3), sharpe_ret=round(r.mean() / r.std() * np.sqrt(252), 2),
                sharpe_usd=round(p.mean() / p.std() * np.sqrt(252), 2),
                max_dd=round((eq - np.maximum.accumulate(eq)).min(), 0), total=round(p.sum(), 0),
                losing_months=f'{(m < 0).sum()}/{len(m)}', days=len(p))


def cross_up(x, lvl):
    x = np.asarray(x, float); prev = np.r_[np.nan, x[:-1]]
    return (x > lvl) & (prev <= lvl)


def sign0(x):
    x = np.asarray(x, float)
    return np.where(np.isnan(x), 0, np.sign(x))


def rule_positions(tf, p):
    c = p.close.values
    s20, s50, s200 = p.sma20.values, p.sma50.values, p.sma200.values
    pos = {}
    if tf == 'H4':
        pos['a_MA_stack'] = ((c > s20) & (s20 > s50) & (s50 > s200)).astype(float)
        pos['b_hold'] = np.ones(len(c))
    if tf == 'D1':
        pos['c_MACD_line'] = (p.macd.values > 0).astype(float)
        pos['b_hold'] = np.ones(len(c))
    if tf == 'H1':
        rg = p.rng.values; up = cross_up(rg, 100.0)
        st = np.zeros(len(c)); cur = 0
        for i in range(len(c)):
            if cur == 1 and rg[i] < 0:
                cur = 0
            if cur == 0 and up[i]:
                cur = 1
            st[i] = cur
        pos['d_RangeOsc_break'] = st
        ma = np.where((c > s20) & (s20 > s50), 1, np.where((c < s20) & (s20 < s50), -1, 0))
        votes = (ma + p.vw_dir_live.values + sign0(p.rsi.values - 50) + sign0(p.macd_hist.values)
                 + sign0(p.rti.values - 50) + sign0(p.asi.values) + sign0(p.rng.values))
        pos['e_all_5of7'] = (votes >= 5).astype(float)
        pos['b_hold'] = np.ones(len(c))
    return pos


def pair_daily():
    a = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
    b = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
    days = pd.DatetimeIndex(np.unique(gbt.load('M5').index.normalize()))
    return (a.groupby(a.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0.0)
            + b.groupby(b.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)), a, b


def combo(x, pair):
    x = x.reindex(pair.index, fill_value=0.0)
    s = pair + x
    eq = np.concatenate([[0.0], s.cumsum().values])
    m = s.groupby(s.index.to_period('M')).sum()
    return dict(per_day=round(s.mean(), 2), max_dd=round((eq - np.maximum.accumulate(eq)).min(), 0),
                losing_months=f'{(m < 0).sum()}/{len(m)}', rule_alone=round(x.mean(), 2))


def main():
    res = {}; dailies = {}; trades = {}
    for tf in ('D1', 'H4', 'H1'):
        d = gbt.load(tf)
        p, _ = mm.all_panels(d)
        for name, want in rule_positions(tf, p).items():
            t, bf, bs, dx = run(d, want)
            pf, ps = daily(bf, dx), daily(bs, dx)
            dailies[(tf, name)] = pf
            trades[(tf, name)] = t
            row = {}
            for wn in ('train', 'test'):
                row[wn] = metrics(pf, dx, W[tf][wn])
            row['train_scaled_swap'] = metrics(ps, dx, W[tf]['train'])
            row['2022_26'] = metrics(pf, dx, R22)
            row['common'] = metrics(pf, dx, COMMON)
            tt = t[t.entry_time >= W[tf]['test'][0]]
            row['test_trades'] = int(len(tt))
            row['test_win_pct'] = round(100 * float((tt.gross > 0).mean()), 1) if len(tt) else None
            # realized view (gbt.daily books each trade on its exit day), test window
            rd = gbt.daily(t, dx).loc[W[tf]['test'][0]:W[tf]['test'][1]]
            row['test_realized_per_day'] = round(rd.mean(), 3)
            res[f'{tf} {name}'] = row
            print(tf, name, json.dumps(row['test']), '| train', row['train']['sharpe_ret'], 'scaled', row['train_scaled_swap']['sharpe_ret'], flush=True)
    pair, a, b = pair_daily()
    pc = pair.loc[COMMON[0]:COMMON[1]]
    res['pair_alone'] = combo(pd.Series(0.0, index=pc.index), pc)
    res['pair_plus_a'] = combo(dailies[('H4', 'a_MA_stack')], pc)
    res['pair_plus_e'] = combo(dailies[('H1', 'e_all_5of7')], pc)
    res['pair_plus_d'] = combo(dailies[('H1', 'd_RangeOsc_break')], pc)
    res['pair_plus_c'] = combo(dailies[('D1', 'c_MACD_line')], pc)
    res['pair_last_trade'] = dict(allagree=str(a.exit_time.max()), asiabreak=str(b.exit_time.max()))
    json.dump(res, open(OUT + 'verify_results.json', 'w'), indent=1, default=str)
    pd.to_pickle({'daily': dailies, 'trades': trades}, OUT + '_verify_daily.pkl')
    print(json.dumps({k: res[k] for k in ('pair_alone', 'pair_plus_a', 'pair_plus_e', 'pair_plus_d', 'pair_plus_c', 'pair_last_trade')}, indent=1))
    return res


if __name__ == '__main__':
    main()
