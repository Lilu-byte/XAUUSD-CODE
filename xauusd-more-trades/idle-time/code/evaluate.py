"""Score the (at most 3) candidates picked by grid.py once on every window, with H.score.

For each candidate: pair + candidate and the candidate alone on pair, m15_train, m15_test and
h1_old; its daily correlation with the pair; the pair-window combined $/day with the candidate's
3 best days zeroed; 200 random-direction versions on m15_test (same entry bars, TP, SL, gate and
exits) and the real rule's percentile; and the pre-registered verdict. The ungated twin of each
candidate is shown for reference only (it is not a candidate). Writes ../results.json.
Run: python3 -I evaluate.py
"""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/idle-time/code')
import json, numpy as np, pandas as pd
import idle as I, harness as H

OUT = '/mnt/project-files/xauusd-more-trades/idle-time/'
WINS = ('pair', 'm15_train', 'm15_test', 'h1_old')
KEYS = ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'worst_month')
BASE = {'pair': dict(per_day=4.66, trades_day=1.59, max_dd=-284, max_dd_mtm=-245),
        'm15_test': dict(per_day=4.06, max_dd=-298, max_dd_mtm=-407),
        'h1_old': dict(per_day=-0.88, max_dd=-1368)}


def f(x):
    return float(x) if isinstance(x, (np.floating, float, int, np.integer)) else x


def run(c, gate=None):
    g = gate or c['gate']; res = {'combined': {}, 'alone': {}, 'by_year': {}}
    for w in WINS:
        P = I.pair(w); t = I.stream(w, c['spec'], c['tp'], c['sl'], g)
        s = H.score({**P, 'cand': t}, w); a = H.score(t, w, mtm=False, by_period=False)
        res['combined'][w] = {k: f(s[k]) for k in KEYS}
        res['alone'][w] = dict(per_day=f(a['per_day']), trades_day=f(a['trades_day']), max_dd=f(a['max_dd']),
                               win_rate=round(float((H.in_window(t, w).pnl > 0).mean()), 3))
        d = H.per_day(t, w); res['by_year'][w] = {int(k): round(float(v), 2) for k, v in d.groupby(d.index.year).mean().items()}
        if w in ('pair', 'm15_test'):
            res[f'corr_{w}'] = f(H.corr(t, I.pair_trades(w), w))
        if w == 'pair':
            pdaily = sum(H.per_day(x, w) for x in P.values())
            top3 = d.nlargest(3).index
            res['best3_removed_pair_per_day'] = round(float((pdaily + d.where(~d.index.isin(top3), 0)).mean()), 2)
            res['top3_days'] = {str(k.date()): round(float(d[k]), 1) for k in top3}
            res['pair_exits'] = H.in_window(t, w).why.value_counts().to_dict()
    return res


def random_pct(c, n=200, seed=20261017):
    w = 'm15_test'; tf = I.tf_of(w)
    ent, dr = I.signal(tf, c['spec'])
    real = H.per_day(I.bracket(tf, ent, dr, c['tp'], c['sl'], True, c['gate']), w).mean()
    rng = np.random.default_rng(seed)
    rnd = np.array([H.per_day(I.bracket(tf, ent, rng.choice([-1, 1], len(ent)), c['tp'], c['sl'], True, c['gate']), w).mean()
                    for _ in range(n)])
    return round(float((rnd < real).mean() * 100), 1), round(float(np.median(rnd)), 2), round(float(np.percentile(rnd, 95)), 2)


def verdict(r):
    p, t, h = r['combined']['pair'], r['combined']['m15_test'], r['combined']['h1_old']
    a = (p['per_day'] >= 4.66 and p['trades_day'] >= 1.59 + 0.3 - 1e-9 and p['max_dd'] >= -294 and p['max_dd_mtm'] >= -255)
    b = (t['per_day'] >= 4.06 and t['max_dd'] >= -308 and t['max_dd_mtm'] >= -417)
    cc = r['alone']['m15_train']['per_day'] > 0 and r['alone']['m15_test']['per_day'] > 0
    d = h['per_day'] >= -0.88 and h['max_dd'] >= -1505
    e = r['random_pct_test'] >= 95
    tests = dict(a=a, b=b, c=cc, d=d, e=e)
    v = 'pass' if all(tests.values()) else ('near' if a and b else 'fail')
    return tests, v


if __name__ == '__main__':
    C = json.load(open(OUT + 'candidates.json'))
    out = []
    for c in C:
        name = f"{c['signal']}, TP {c['tp']:.0f} / SL {c['sl']:.0f}, gate {c['gate']}"
        r = run(c); r['name'] = name; r['cand'] = c
        r['random_pct_test'], r['random_median'], r['random_p95'] = random_pct(c)
        r['tests'], r['verdict'] = verdict(r)
        u = run(c, 'none'); r['ungated_reference'] = {'combined': u['combined'], 'alone': u['alone']}
        out.append(r)
        print('\n' + name)
        for w in WINS:
            cb, al, ub = r['combined'][w], r['alone'][w], u['combined'][w]
            print(f"  {w:9s} pair+: {cb['per_day']:+.2f}/day {cb['trades_day']:.2f} tr/day dd {cb['max_dd']:.0f} mtm {cb['max_dd_mtm']:.0f} "
                  f"worst month {cb['worst_month']:.0f} | alone {al['per_day']:+.2f}/day {al['trades_day']:.2f} tr/day dd {al['max_dd']:.0f} "
                  f"win {al['win_rate']:.2f} | ungated pair+ {ub['per_day']:+.2f} dd {ub['max_dd']:.0f} mtm {ub['max_dd_mtm']:.0f} "
                  f"(alone {u['alone'][w]['per_day']:+.2f})")
        print(f"  by year alone: {r['by_year']}")
        print(f"  corr with pair: pair {r['corr_pair']}, m15_test {r['corr_m15_test']}; pair $/day w/o its 3 best days "
              f"{r['best3_removed_pair_per_day']} {r['top3_days']}; exits on pair {r['pair_exits']}")
        print(f"  random direction (m15_test, 200): pct {r['random_pct_test']}, median {r['random_median']}, p95 {r['random_p95']}")
        print(f"  tests {r['tests']} -> {r['verdict'].upper()}")
    json.dump(out, open(OUT + 'results.json', 'w'), indent=1, default=str)
