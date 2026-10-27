import sys; sys.path.insert(0,'/mnt/project-files/xauusd-microscalp/code')
from mlib import *
m = load_m1()
T = pd.read_csv('/mnt/project-files/xauusd-microscalp/ea/expected_trades.csv', parse_dates=['entry'])
T['ei'] = m.index.get_indexer(T.entry); T['xi'] = T.ei + T.bars
DEF = {'PB': (1.0, 5.0, 20, 3), 'SF': (0.5, 5.0, 5, 1), 'QB': (0.5, 2.0, 5, 1), 'CP': (0.5, 3.0, 5, 3)}
for mod, g in T.groupby('module'):
    tp, sl, to, mo = DEF[mod]
    xs = g.xi.values; same = g.ei.isin(set(xs)).sum(); same_to = g.ei.isin(set(g[g.bars==to].xi)).sum()
    print(mod, 'n', len(g), 'entries on a bar where same-module trade exits', same, 'of which timeout exit', same_to,
          'bars dist', g.bars.value_counts().sort_index().to_dict() if mod != 'CP' else '')
    # concurrency
    mx = 0
    ev = sorted([(e, 1) for e in g.ei] + [(x, -1) for x in g.xi], key=lambda z: (z[0], z[1]))
    cur = 0
    for _, d in ev: cur += d; mx = max(mx, cur)
    print('   max concurrent', mx)
