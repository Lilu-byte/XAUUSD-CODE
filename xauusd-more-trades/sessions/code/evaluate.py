"""Score the 3 candidates picked on m15_train (candidates.json) on every window, once.

For each: the stream alone and pair + stream (harness.score) on pair (M5, fixed $), m15_train,
m15_test (M15, scaled $) and h1_old (H1, scaled $; NY/US ranges widened to whole hours);
daily correlation with the pair; the pair-window combined $/day with the stream's 3 best days
zeroed; 200 random-direction versions (same entry bars, TP, SL, exit rule) on m15_test; and the
pass test of the pre-registered rules. Writes ../results.json; prints a summary.
"""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/sessions/code')
import json, numpy as np, pandas as pd
import sessions as S, harness as H

OUT = '/mnt/project-files/xauusd-more-trades/sessions/'
WINS = ('pair', 'm15_train', 'm15_test', 'h1_old')
KEYS = ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'worst_month')
cands = json.load(open(OUT + 'candidates.json'))
base = {w: H.pair_parts(w) for w in WINS}
pick = lambda s: {k: (float(s[k]) if k in s else None) for k in KEYS}
res = []
for c in cands:
    name, mode, tp, sl = c['setup'], c['mode'], c['tp'], c['sl']
    r = dict(setup=name, mode=mode, tp=tp, sl=sl, alone={}, combined={})
    for w in WINS:
        T = S.window_trades(w, name, mode, tp, sl)
        r['alone'][w] = pick(H.score(T, w))
        r['combined'][w] = pick(H.score({**base[w], 'X': T}, w))
        if w == 'pair':
            pair_tr = pd.concat(list(base[w].values()))
            r['corr_pair'] = float(H.corr(T, pair_tr, w))
            x = H.per_day(T, w); top3 = x.nlargest(3).index
            pdaily = H.per_day(pair_tr, w)
            r['best3_removed_pair_per_day'] = round(float((pdaily + x.where(~x.index.isin(top3), 0)).mean()), 2)
            r['top3_days'] = {str(k.date()): round(float(x[k]), 1) for k in top3}
            Tw = H.in_window(T, w); r['pair_win_rate'] = round(float((Tw.pnl > 0).mean()), 3)
            r['pair_exits'] = Tw.why.value_counts().to_dict()
        if w == 'm15_test':
            r['corr_m15_test'] = float(H.corr(T, pd.concat(list(base[w].values())), w))
            sig = S.setup_signals('M15', name, mode)
            rng = np.random.default_rng(20261017)
            real = H.per_day(T, w).mean()
            rnd = np.array([H.per_day(S.simulate(S.Bars('M15'), sig, tp, sl, scale=True,
                                                  dirs=rng.choice([-1, 1], len(sig))), w).mean() for _ in range(200)])
            r['random_pct_test'] = round(float((rnd < real).mean() * 100), 1)
            r['random_median_p95'] = [round(float(np.median(rnd)), 2), round(float(np.percentile(rnd, 95)), 2)]
    P, T_, Te, O = (r['combined'][w] for w in WINS)
    A = r['alone']
    a = P['per_day'] >= 4.66 and P['trades_day'] >= 1.59 + 0.3 and P['max_dd'] >= -294 and P['max_dd_mtm'] >= -255
    b = Te['per_day'] >= 4.06 and Te['max_dd'] >= -308 and Te['max_dd_mtm'] >= -417
    cc = A['m15_train']['per_day'] > 0 and A['m15_test']['per_day'] > 0
    d = O['per_day'] >= -0.88 and O['max_dd'] >= -1505
    e = r['random_pct_test'] >= 95
    r['tests'] = dict(a=a, b=b, c=cc, d=d, e=e)
    r['verdict'] = 'pass' if all((a, b, cc, d, e)) else ('near' if a and b else 'fail')
    res.append(r)
    print(f"\n== {name} / {mode} / TP {tp} SL {sl}   verdict {r['verdict'].upper()}  tests {r['tests']}")
    for w in WINS:
        print(f"  {w:9s} alone {A[w]}\n  {'':9s} pair+ {r['combined'][w]}")
    print(f"  corr with pair {r['corr_pair']} (m15_test {r['corr_m15_test']}); pair $/day without its 3 best days "
          f"{r['best3_removed_pair_per_day']} {r['top3_days']}; random-direction pct on m15_test {r['random_pct_test']} "
          f"(median, p95 {r['random_median_p95']}); pair-window win rate {r['pair_win_rate']} exits {r['pair_exits']}")
json.dump(res, open(OUT + 'results.json', 'w'), indent=1, default=str)
