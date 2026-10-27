"""Step 2: fragility. Nudge the golden-cross parameters +/-30% (fast 35..65, slow 140..260, SMA and EMA),
plus execution/cost nudges, and report the spread of 2022-2026 results and the excess over holding gold.
Train-window numbers are shown only to see whether the neighbourhood was stable where it was picked."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-overfit-long-core')
from vsim import *

D1 = gbt.load('D1'); c = D1.close
SC = 0.126 * 365 / 4100 * 100   # scaled swap %/yr used for 2005-2015
ones = np.ones(len(D1), bool)
ph, _, _ = mtm(ones, D1); phs, _, _ = mtm(ones, D1, 'scaled', SC)
H = {w: win(ph, w).mean() for w in (TRAIN_B, TEST)}; H[TRAIN_A] = win(phs, TRAIN_A).mean()
pp, a, b, days = pair_daily()

rows = []
def score(tag, on, **kw):
    p, held, t = mtm(on, D1, **kw); pa, _, _ = mtm(on, D1, 'scaled', SC)
    r = dict(variant=tag)
    for nm, w, s in (('A', TRAIN_A, pa), ('B', TRAIN_B, p), ('test', TEST, p)):
        x = win(s, w); r[f'{nm}_pd'] = round(x.mean(), 2); r[f'{nm}_x'] = round(x.mean() - H[w], 2)
    x = win(p, TEST); eq = x.cumsum(); r['test_dd'] = round((eq - eq.cummax()).min(), 0)
    r['test_trades'] = int(((t.exit_time >= TEST[0]) & (t.entry_time <= TEST[1])).sum())
    r['test_inmkt'] = round(win(held, TEST).mean() * 100)
    for y in range(2022, 2027):
        r[f'y{y}'] = round(p.loc[str(y)].mean(), 2)
    core = p.reindex(days).fillna(0.0); z = pp + core; ez = z.cumsum()
    r['common_core'] = round(core.mean(), 2); r['pair_plus'] = round(z.mean(), 2); r['pair_plus_dd'] = round((ez - ez.cummax()).min(), 0)
    r['exit_2026'] = str(t[(t.exit_time >= '2026-01-01') & ~t.open_at_end].exit_time.min())[:10]
    rows.append(r)

for kind in ('sma', 'ema'):
    for f in (35, 40, 45, 50, 55, 60, 65):
        for s in (140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260):
            score(f'{kind}{f}/{s}', golden(c, f, s, kind))
base = golden(c, 50, 200)
# execution / timing nudges on the chosen 50/200
for lag in (1, 2, 3, 5, 10, 20):
    score(f'sma50/200 lag{lag}d', np.r_[np.zeros(lag, bool), base[:-lag]])
wk = pd.Series(D1.index.to_period('W-SUN'), index=D1.index); last = (wk != wk.shift(-1)).values.copy(); last[-1] = False
score('sma50/200 friday-only', pd.Series(np.where(last, base.astype(float), np.nan), index=D1.index).ffill().fillna(0).values.astype(bool))
for bd in (0.005, 0.01, 0.02):
    f50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
    st = np.zeros(len(c), bool); on_ = False
    for i in range(len(c)):
        if not on_ and f50.iloc[i] > s200.iloc[i] * (1 + bd): on_ = True
        elif on_ and f50.iloc[i] < s200.iloc[i] * (1 - bd): on_ = False
        st[i] = on_
    score(f'sma50/200 hyst{bd*100:.1f}%', st)
for sw in (0.063, 0.189, 0.252):
    score(f'sma50/200 swap ${sw:.3f}', base, swap=sw)
for sp in (0.0, 1.0, 3.0):
    score(f'sma50/200 spread ${sp:.1f}', base, spread=sp)

g = pd.DataFrame(rows)
g.to_csv(OUT + 'nudge_grid.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
gs = g[g.variant.str.match(r'^(sma|ema)\d+/\d+$')]
print(f'hold baselines $/day: trainA {H[TRAIN_A]:.2f}  trainB {H[TRAIN_B]:.2f}  test {H[TEST]:.2f}')
for kind in ('sma', 'ema'):
    x = gs[gs.variant.str.startswith(kind)]
    near = x[x.variant.apply(lambda v: 35 <= int(v[3:].split('/')[0]) <= 65 and 140 <= int(v.split('/')[1]) <= 260)]
    print(f'\n{kind.upper()} grid fast 35..65 x slow 140..260 ({len(x)} combos):')
    for col in ('A_x', 'B_x', 'test_pd', 'test_x', 'test_dd', 'common_core', 'pair_plus', 'pair_plus_dd'):
        q = x[col].quantile([0, .1, .5, .9, 1]).round(2).tolist()
        print(f'  {col:13s} min/p10/median/p90/max {q}')
    print('  share beating hold: trainA', f"{(x.A_x > 0).mean() * 100:.0f}%", 'trainB', f"{(x.B_x > 0).mean() * 100:.0f}%",
          'test', f"{(x.test_x > 0).mean() * 100:.0f}%", '| all three', f"{((x.A_x > 0) & (x.B_x > 0) & (x.test_x > 0)).mean() * 100:.0f}%")
    pv = x.assign(f=x.variant.str.extract(r'(\d+)/')[0].astype(int), s=x.variant.str.extract(r'/(\d+)')[0].astype(int)).pivot(index='f', columns='s', values='test_pd')
    print('  test $/day pivot (rows fast, cols slow):'); print(pv.to_string())
    pv = x.assign(f=x.variant.str.extract(r'(\d+)/')[0].astype(int), s=x.variant.str.extract(r'/(\d+)')[0].astype(int)).pivot(index='f', columns='s', values='B_x')
    print('  train-B excess vs hold $/day pivot:'); print(pv.to_string())
    print('  rank corr (train A+B excess) vs test excess:', round((x.A_x / H[TRAIN_A] + x.B_x).rank().corr(x.test_x.rank()), 2))
print('\nexecution / timing nudges of SMA 50/200:')
print(g[~g.variant.isin(gs.variant)].to_string(index=False))
print('\nchosen 50/200:'); print(g[g.variant == 'sma50/200'].to_string(index=False))
