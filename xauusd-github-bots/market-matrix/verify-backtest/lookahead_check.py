"""Look-ahead checks.
1. Truncation test: recompute mm.all_panels on data cut at bar k and compare bar k's values with the full-history run.
   Any difference on a column the rules use means that column peeks at later bars.
2. Same-bar test: the position decided on bar i must not change if bar i+1's OHLC is altered (it is filled at i+1's open).
3. Delay test: hold every position one extra bar (decide at close i, fill at open i+2) to see how much of the result
   depends on the very first bar after the signal.
Usage: python3 -I lookahead_check.py
"""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest')
import numpy as np, pandas as pd
import gbt, mm
from verify import rule_positions, run, daily, metrics, W

OUT = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest/'
USED = ['sma20', 'sma50', 'sma200', 'rsi', 'macd', 'macd_hist', 'rti', 'asi', 'rng', 'vw_dir_live', 'vwap_live']
res = {}
rng = np.random.default_rng(7)
for tf in ('D1', 'H4', 'H1'):
    d = gbt.load(tf)
    full, _ = mm.all_panels(d)
    pos_full = rule_positions(tf, full)
    n = len(d)
    cuts = sorted(set([3000, n // 2, n - 500, n - 2] + list(rng.integers(2500, n - 1, 6))))
    bad = {}
    pos_bad = {}
    for k in cuts:
        cut = d.iloc[:k + 1]
        p, _ = mm.all_panels(cut)
        for col in full.columns:
            a, b = full[col].values[k], p[col].values[k]
            if not ((np.isnan(a) and np.isnan(b)) or abs(a - b) <= 1e-9 * max(1.0, abs(a))):
                bad.setdefault(col, []).append((str(d.index[k]), float(a), float(b)))
        pp = rule_positions(tf, p)
        for nm in pp:
            if pp[nm][k] != pos_full[nm][k] or not np.array_equal(pp[nm], pos_full[nm][:k + 1]):
                pos_bad.setdefault(nm, []).append(str(d.index[k]))
    # same-bar test: perturb bar k+1 heavily, positions up to k must not move
    k = n - 300
    d2 = d.copy()
    d2.iloc[k + 1:, :4] = d2.iloc[k + 1:, :4] * 1.2
    p2, _ = mm.all_panels(d2)
    pos2 = rule_positions(tf, p2)
    same = {nm: bool(np.array_equal(pos2[nm][:k + 1], pos_full[nm][:k + 1])) for nm in pos2}
    # delay test
    delay = {}
    for nm, want in pos_full.items():
        if nm == 'b_hold':
            continue
        lagged = np.r_[0.0, np.asarray(want, float)[:-1]]
        for lab, w_ in (('as_is', want), ('one_bar_later', lagged)):
            t, bf, bs, dx = run(d, w_)
            pf = daily(bf, dx)
            delay[f'{nm} {lab}'] = {wn: metrics(pf, dx, W[tf][wn])['per_day'] for wn in ('train', 'test')} | \
                                   {'test_sharpe': metrics(pf, dx, W[tf]['test'])['sharpe_ret']}
    res[tf] = dict(cuts=[str(d.index[k]) for k in cuts], value_mismatch_cols={c: v[:2] for c, v in bad.items()},
                   used_cols_mismatch=[c for c in bad if c in USED], position_mismatch=pos_bad,
                   positions_unchanged_when_future_bars_altered=same, delay=delay)
    print(tf, json.dumps(res[tf], default=str), flush=True)
json.dump(res, open(OUT + 'lookahead_results.json', 'w'), indent=1, default=str)
