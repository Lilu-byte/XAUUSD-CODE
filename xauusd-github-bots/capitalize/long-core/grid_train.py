"""Score every pre-listed rule on TRAINING windows only (2005-04..2015-12 and 2016-07..2021-12).
Scale-free metrics (1-oz position returns, swap = same % of price as today) so 2005 and 2021 compare.
Selection rule fixed in advance: highest mean Sharpe across the two training windows,
must have positive return in both. No test-window numbers are computed here."""
from rules import *

R = catalog()
rows = []
def score(name, on):
    t, p, held = run(on, swap='scaled')
    row = dict(rule=name)
    for tag, w in (('A', TRAIN_A), ('B', TRAIN_B)):
        m = metr(window(p, w)); ts = tstats(t, w)
        yrs = (pd.Timestamp(w[1]) - pd.Timestamp(w[0])).days / 365.25
        row.update({f'{tag}_ret': m['ret_yr'], f'{tag}_sh': m['sharpe'], f'{tag}_dd': m['dd_pct'], f'{tag}_mar': m['mar'],
                    f'{tag}_tr_yr': round(ts['trades'] / yrs, 1), f'{tag}_inmkt': round(window(held, w).mean() * 100, 0)})
    row['score'] = round((row['A_sh'] + row['B_sh']) / 2, 3)
    return row
rows.append(score('HOLD', np.ones(len(D1), bool)))
for k, f in R.items():
    rows.append(score(k, f()))
g = pd.DataFrame(rows)
g.to_csv(OUT + 'grid_train.csv', index=False)
print('variants:', len(R))
pd.set_option('display.width', 250)
print(g.sort_values('score', ascending=False).to_string(index=False))
