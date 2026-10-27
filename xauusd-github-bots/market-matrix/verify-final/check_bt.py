import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt
from test_rules import per_day, WIN
B = pd.read_pickle('/mnt/project-files/xauusd-github-bots/market-matrix/code/_bar_pnl.pkl')
V = pd.read_pickle('/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest/_verify_daily.pkl')['daily']
m = {('H4','a_MA_stack'):('H4','MA stack 20/50/200','long only'), ('H4','b_hold'):('H4','Hold 0.01 lot long','long only'),
     ('D1','c_MACD_line'):('D1','MACD line sign','long only'), ('D1','b_hold'):('D1','Hold 0.01 lot long','long only'),
     ('H1','d_RangeOsc_break'):('H1','Range Osc +/-100 breakout, exit at 0','long only'), ('H1','e_all_5of7'):('H1','All panels: 5+ of 7 agree','long only'),
     ('H1','b_hold'):('H1','Hold 0.01 lot long','long only')}
out = {}
for k, k2 in m.items():
    a = V[k]; b = per_day(B[k2])
    j = a.index.intersection(b.index)
    diff = (a.reindex(j) - b.reindex(j)).abs()
    out[str(k)] = dict(maxdiff_from2016=float(diff.loc['2016-01-01':].max()), n_gt_0p01_from2016=int((diff.loc['2016-01-01':] > 0.01).sum()),
                       maxdiff_all=float(diff.max()), argmax_all=str(diff.idxmax()), days_only_verify=int(len(a.index.difference(b.index))),
                       days_only_main=int(len(b.index.difference(a.index))), last_verify=str(a.index[-1]), last_main=str(b.index[-1]))
# usd vs ret sharpe for all readings on test windows
rows = []
for (tf, name, mode), pb in B.items():
    d = gbt.load(tf)
    for wn in ('train', 'test'):
        w = WIN[tf][wn]
        p = per_day(pb.loc[w[0]:w[1]])
        px = d.close.groupby(d.index.normalize()).last().shift().reindex(p.index)
        r = p / px
        rows.append(dict(tf=tf, rule=name, mode=mode, win=wn, sh_ret=r.mean()/r.std()*np.sqrt(252), sh_usd=p.mean()/p.std()*np.sqrt(252)))
S = pd.DataFrame(rows)
res = {}
for (tf, wn), g in S.groupby(['tf', 'win']):
    h = g[g.rule.str.startswith('Hold')].iloc[0]
    x = g[~g.rule.str.startswith('Hold')]
    flips = x[(x.sh_ret >= h.sh_ret) != (x.sh_usd >= h.sh_usd)]
    res[f'{tf}|{wn}'] = dict(hold_ret=round(h.sh_ret, 3), hold_usd=round(h.sh_usd, 3), spearman=round(x.sh_ret.rank().corr(x.sh_usd.rank()), 3),
                            n_usd_higher=int((x.sh_usd > x.sh_ret).sum()), n=len(x),
                            flips_vs_hold=[f"{r.rule}|{r['mode']}: ret {r.sh_ret:.2f} usd {r.sh_usd:.2f}" for _, r in flips.iterrows()])
out['usd_vs_ret'] = res
json.dump(out, open('check_bt.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
