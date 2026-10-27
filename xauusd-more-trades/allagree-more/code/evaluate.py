"""Score the picks (../picks.json, chosen on m15_train) once on every window.
For each: pair + candidate combined (H.score), the candidate alone, its own daily P&L (an added
stream's P&L; for a change, changed GoldAllAgree minus GoldAllAgree), the random-direction check
on m15_test (200 runs, same entry and exit times, same costs), the pair-window $/day with the
candidate's 3 best days taken out, its daily correlation with the pair, and the verdict.
Rule (e) applies where the rule picks a direction against the long-only pair: the short stream.
For long-only candidates the percentile is shown for information.
Usage: python3 -I evaluate.py  -> printed summary, ../results.json"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/allagree-more/code')
import json
import numpy as np, pandas as pd
import aa_more as A, specs as SP
H = A.H
D = '/mnt/project-files/xauusd-more-trades/allagree-more/'
WINS = ('pair', 'm15_train', 'm15_test', 'h1_old')
KEYS = ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'worst_month', 'pos_months')


def f(x): return float(x) if isinstance(x, (np.floating, np.integer)) else x


def parts(spec, w, base):
    kind, t = SP.build(spec, w)
    if kind == 'change':
        return kind, t, {'AllAgree': t, 'AsiaBreak': base['AsiaBreak']}, H.per_day(t, w) - H.per_day(base['AllAgree'], w)
    return kind, t, {**base, 'cand': t}, H.per_day(t, w)


def random_pct(t, w, cost, side_fixed, n=200):
    base = A.base_tf(w)
    t = H.in_window(t, w).reset_index(drop=True)
    runs, lp, sp = A.random_dir(t, base, n=n, cost=cost)
    N = len(H.days(w))
    real = (lp if side_fixed == 1 else sp).sum() / N
    null = np.array([r.sum() / N for r in runs])
    return dict(real=round(real, 2), null_median=round(float(np.median(null)), 2),
                null_p95=round(float(np.percentile(null, 95)), 2), pct=round(100 * float((null < real).mean()), 1))


def verdict(R, spec):
    p, te, tr, h = (R['windows'][w] for w in ('pair', 'm15_test', 'm15_train', 'h1_old'))
    c = {}
    c['a'] = (p['combined']['per_day'] >= 4.66 and p['combined']['trades_day'] >= 1.59 + 0.3
              and p['combined']['max_dd'] >= -294 and p['combined']['max_dd_mtm'] >= -255)
    c['b'] = (te['combined']['per_day'] >= 4.06 and te['combined']['max_dd'] >= -308 and te['combined']['max_dd_mtm'] >= -417)
    c['c'] = (tr['alone']['per_day'] > 0 and te['alone']['per_day'] > 0 and tr['own_per_day'] > 0 and te['own_per_day'] > 0)
    c['d'] = h['combined']['per_day'] >= -0.88 and h['combined']['max_dd'] >= -1505
    c['e'] = (R['random_m15_test']['pct'] >= 95) if spec['kind'] == 'short' else None
    if c['a'] and c['b'] and c['c'] and c['d'] and c['e'] in (True, None): v = 'pass'
    elif c['a'] and c['b']: v = 'near'
    else: v = 'fail'
    return c, v


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    picks = json.load(open(D + 'picks.json'))
    base = {w: H.pair_parts(w) for w in WINS}
    bs = {w: H.score(base[w], w) for w in WINS}
    bdaily = {w: sum(H.per_day(x, w) for x in base[w].values()) for w in WINS}
    for w in WINS: print('baseline', w, {k: f(bs[w][k]) for k in KEYS})
    out = []
    for pk in picks:
        spec = pk['spec']; R = dict(name=pk['name'], family=pk['family'], how=pk['how'], spec=spec, windows={})
        print('\n=== candidate', pk['name'], '|', pk['how'])
        for w in WINS:
            kind, t, comb, own = parts(spec, w, base[w])
            s = H.score(comb, w); a = H.score(t, w)
            res = dict(combined={k: f(s[k]) for k in KEYS}, alone={k: f(a[k]) for k in KEYS},
                       own_per_day=round(float(own.mean()), 2),
                       by_year={str(k): v for k, v in (s.get('per_day_by_year') or {'2025': s.get('per_day_2025'), '2026': s.get('per_day_2026')}).items()},
                       own_by_year={str(k): round(float(v), 2) for k, v in own.groupby(own.index.year).mean().items()},
                       corr_with_pair=round(float(own.corr(bdaily[w])), 2))
            if kind == 'change':     # both GoldAllAgree versions at the flat $0.30 + $0.10 a fill
                _, tf = SP.build(spec, w, cost='fixed'); bf = A.baseline_aa(w, 'fixed')
                res['fixed_cost'] = dict(changed_pair=round(float((H.per_day(tf, w) + H.per_day(base[w]['AsiaBreak'], w)).mean()), 2),
                                         base_pair=round(float((H.per_day(bf, w) + H.per_day(base[w]['AsiaBreak'], w)).mean()), 2))
            if w == 'pair':
                daily = sum(H.per_day(x, w) for x in comb.values())
                top = own.sort_values(ascending=False).index[:3]
                res['best3_removed_per_day'] = round(float((daily - own.where(own.index.isin(top), 0)).mean()), 2)
                res['best3_days'] = {str(k.date()): round(float(own[k]), 0) for k in top}
            R['windows'][w] = res
            print(f'  {w:9s} combined', res['combined'], '| alone', {k: res['alone'][k] for k in ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm')},
                  '| own', res['own_per_day'], 'corr', res['corr_with_pair'], res.get('fixed_cost', ''))
        kind, t = SP.build(spec, 'm15_test')
        cost = 'bar' if kind == 'change' else 'fixed'
        R['random_m15_test'] = random_pct(t, 'm15_test', cost, spec.get('side', -1 if spec['kind'] == 'short' else 1))
        print('  random direction m15_test:', R['random_m15_test'])
        print('  pair window w/o its 3 best days:', R['windows']['pair']['best3_removed_per_day'], R['windows']['pair']['best3_days'])
        R['checks'], R['verdict'] = verdict(R, spec)
        print('  checks', R['checks'], '->', R['verdict'].upper())
        out.append(R)
    json.dump(dict(baseline={w: {k: f(bs[w][k]) for k in KEYS} for w in WINS}, candidates=out),
              open(D + 'results.json', 'w'), indent=1)
