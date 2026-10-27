"""Score the candidates picked on m15_train (../picks.json) on every window, once.
For each: pair + candidate combined (H.score), the candidate alone, the random-direction check on
m15_test (200 runs, same entry times / TP / SL / exits), the pair-window $/day without the
candidate's 3 best days, its daily correlation with the pair, and the pre-registered verdict.
Usage: python3 -I evaluate.py   -> prints a summary, writes ../results.json"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/asia-more/code')
import json
import numpy as np, pandas as pd
import asia_more as A
from train_grid import build
H = A.H
D = '/mnt/project-files/xauusd-more-trades/asia-more/'
WINS = ('pair', 'm15_train', 'm15_test', 'h1_old')
KEYS = ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'worst_month')


def alone_daily(alone, w):
    return alone if isinstance(alone, pd.Series) else H.per_day(alone, w)


def random_pct(alone, w, n=200):
    tf, scale = A.window_tf_scale(w)
    t = H.in_window(alone, w)
    ents = list(zip(t.entry_time, t.dir, t.tp, t.sl))
    real = A.sim_fixed(tf, ents, scale=scale)
    r = H.per_day(real, w).mean()
    null = []
    for seed in range(n):
        g = np.random.default_rng(seed)
        dirs = np.where(g.random(len(ents)) < 0.5, 1, -1)
        x = A.sim_fixed(tf, [(e, int(d), a, b) for (e, _, a, b), d in zip(ents, dirs)], scale=scale)
        null.append(H.per_day(x, w).mean())
    null = np.array(null)
    return dict(real=round(r, 2), engine=round(H.per_day(t, w).mean(), 2), null_median=round(np.median(null), 2),
                null_p95=round(np.percentile(null, 95), 2), pct=round(100 * (null < r).mean(), 1))


if __name__ == '__main__':
    picks = json.load(open(D + 'picks.json'))
    base = {w: H.pair_parts(w) for w in WINS}
    bs = {w: H.score(base[w], w) for w in WINS}
    for w in WINS: print('baseline', w, {k: bs[w][k] for k in KEYS})
    out = []
    for p in picks:
        spec = p['spec']; res = dict(family=p['family'], spec=spec, windows={})
        print('\n=== candidate', p['family'], spec)
        for w in WINS:
            comb, alone, t = build(spec, w, base[w])
            s = H.score(comb, w)
            ad = alone_daily(alone, w); eq = ad.cumsum()
            a = dict(per_day=round(ad.mean(), 2), max_dd=round((eq - eq.cummax()).min(), 0),
                     trades_day=round(s['trades_day'] - bs[w]['trades_day'], 2))
            if not isinstance(alone, pd.Series):
                a['max_dd_mtm'] = H.score(alone, w)['max_dd_mtm']
                a['by_year'] = H.per_day(alone, w).groupby(lambda k: k.year).mean().round(2).to_dict()
            res['windows'][w] = dict(combined={k: s[k] for k in KEYS}, combined_by_year=s.get('per_day_by_year', {k: s[k] for k in s if k.startswith('per_day_2')}),
                                     alone=a)
            print(f'  {w:9s} combined', {k: s[k] for k in KEYS}, '| alone', a)
            if w == 'pair':
                pd_ = sum(H.per_day(x, w) for x in base[w].values())
                ad2 = ad.copy(); ad2[ad.nlargest(3).index] = 0.0
                comb_daily = sum(H.per_day(x, w) for x in comb.values())
                extra = comb_daily - pd_ if spec['kind'] == 'change' else ad
                e2 = extra.copy(); e2[extra.nlargest(3).index] = 0.0
                res['best3_removed_pair_per_day'] = round((pd_ + e2).mean(), 2)
                res['corr_with_pair'] = round(extra.corr(pd_), 2)
                print('  pair: combined $/day without the candidate\'s 3 best days', res['best3_removed_pair_per_day'],
                      '| daily corr with the pair', res['corr_with_pair'],
                      '| corr with GoldAsiaBreak alone', round(extra.corr(H.per_day(base[w]['AsiaBreak'], w)), 2))
            if w == 'm15_test':
                if isinstance(alone, pd.Series):
                    res['random'] = None
                else:
                    res['random'] = random_pct(alone, w)
                    print('  random direction on m15_test (200 runs):', res['random'])
        W_ = res['windows']; c = {w: W_[w]['combined'] for w in WINS}
        a_ok = (c['pair']['per_day'] >= 4.66 and c['pair']['trades_day'] >= 1.59 + 0.3 and
                c['pair']['max_dd'] >= -294 and c['pair']['max_dd_mtm'] >= -255)
        b_ok = c['m15_test']['per_day'] >= 4.06 and c['m15_test']['max_dd'] >= -308 and c['m15_test']['max_dd_mtm'] >= -417
        c_ok = W_['m15_train']['alone']['per_day'] > 0 and W_['m15_test']['alone']['per_day'] > 0
        d_ok = c['h1_old']['per_day'] >= -0.88 and c['h1_old']['max_dd'] >= -1505
        e_ok = res['random'] is None or res['random']['pct'] >= 95
        res['checks'] = dict(a=a_ok, b=b_ok, c=c_ok, d=d_ok, e=e_ok)
        res['verdict'] = 'pass' if all((a_ok, b_ok, c_ok, d_ok, e_ok)) else ('near' if a_ok and b_ok else 'fail')
        print('  checks', res['checks'], '->', res['verdict'].upper())
        out.append(res)
    json.dump(out, open(D + 'results.json', 'w'), indent=1, default=float)
