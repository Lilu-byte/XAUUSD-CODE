"""Step 4: how many variants were effectively tried, and is the golden cross's difference from holding
distinguishable from noise? Imports the candidate's rule catalog read-only (run with python3 -B so no
bytecode is written into their folder); P&L is computed with my own simulator."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-overfit-long-core')
from vsim import *
sys.path.insert(1, '/mnt/project-files/xauusd-github-bots/capitalize/long-core')
import rules as R0

D1 = gbt.load('D1'); c = D1.close
SC = 0.126 * 365 / 4100 * 100
cat = R0.catalog()
ones = np.ones(len(D1), bool)
phs, _, _ = mtm(ones, D1, 'scaled', SC)
hret = phs / c.shift()
TR = ('2005-04-01', '2021-12-31')
X = {}
for k, f in cat.items():
    p, _, _ = mtm(f(), D1, 'scaled', SC)
    X[k] = win(p / c.shift() - hret, TR)
X = pd.DataFrame(X).fillna(0.0)
C = np.corrcoef(X.values.T); lam = np.clip(np.linalg.eigvalsh(C), 0, None)[::-1]
neff = lam.sum() ** 2 / (lam ** 2).sum()
cum = np.cumsum(lam) / lam.sum()
print(f'catalog rules: {len(cat)} (+ HOLD); effective independent bets in the excess-over-hold returns, train 2005-2021:'
      f' participation ratio {neff:.1f}; eigenvectors for 80%/90%/95% of variance: '
      f'{np.searchsorted(cum, .8) + 1}/{np.searchsorted(cum, .9) + 1}/{np.searchsorted(cum, .95) + 1}')
print('prior project work on the same D1 family over 2004-2026 (incl. the 2022-2026 test years): STRATEGY.md 6 rules, CHECK.md 10 variants')

# information ratio of golden cross vs hold, train and test, with a block bootstrap
on = R0.golden(False)
p, held, t = mtm(on, D1, 'scaled', SC)
ex = p / c.shift() - hret
rng = np.random.default_rng(11)
def ir_ci(x, block=63, n=4000):
    x = x.dropna().values; T = len(x); nb = int(np.ceil(T / block)); res = []
    for _ in range(n):
        st = rng.integers(0, T - block, nb); s = np.concatenate([x[a:a + block] for a in st])[:T]
        res.append(s.mean() / s.std() * np.sqrt(252))
    res = np.array(res); return np.percentile(res, [5, 50, 95]), (res > 0).mean()
for lbl, w in (('train A 2005-04..2015', TRAIN_A), ('train B 2016-07..2021', TRAIN_B), ('train A+B', TR), ('test 2022..2026-10', TEST)):
    x = win(ex, w); ir = x.mean() / x.std() * np.sqrt(252); yrs = len(x) / 252
    ci, pp = ir_ci(x)
    print(f'{lbl:24s} excess vs hold {x.mean() * 252 * 100:+5.1f}%/yr  IR {ir:+.2f}  t {ir * np.sqrt(yrs):+.2f}  '
          f'block-bootstrap 90% IR range {ci[0]:+.2f}..{ci[2]:+.2f}  P(IR>0) {pp * 100:.0f}%')
# what a best-of-N pick is worth under the null (excess IR 0) over the 16.7-year training span
T = len(win(ex, TR)) / 252
for N in (1, round(neff), 44, 60):
    sims = rng.standard_normal((20000, int(N))).max(axis=1) / np.sqrt(T)
    print(f'  null: best of {int(N):2d} independent rules -> expected max train IR {sims.mean():.2f} (95th pct {np.percentile(sims, 95):.2f})')
# train-score ranking of the catalog vs its test excess (re-computed with my simulator)
rows = []
ph, _, _ = mtm(ones, D1)
for k, f in cat.items():
    ps, _, _ = mtm(f(), D1, 'scaled', SC); pf, _, _ = mtm(f(), D1)
    sa = win(ps / c.shift(), TRAIN_A); sb = win(pf / c.shift(), TRAIN_B)
    rows.append(dict(rule=k, train=(sa.mean() / sa.std() + sb.mean() / sb.std()) / 2 * np.sqrt(252),
                     test_x=win(pf - ph, TEST).mean()))
g = pd.DataFrame(rows).sort_values('train', ascending=False)
print(f'rank corr train score vs test excess over hold (44 rules): {g.train.rank().corr(g.test_x.rank()):+.2f};'
      f' rules beating hold in test: {(g.test_x > 0).sum()}/44; top-5 by train, test excess $/day: '
      + ', '.join(f'{r.rule} {r.test_x:+.2f}' for r in g.head(5).itertuples()))
