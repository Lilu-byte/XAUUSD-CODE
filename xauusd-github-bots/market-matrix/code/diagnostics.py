"""Diagnostics for the Market Matrix study: how much the swing VWAP redraws, how the Range Oscillator's bounds drift,
how alike the panels are, today's reading, and timing / pair checks for the leading rules.
Run after test_rules.py.  Usage: python3 -I diagnostics.py
"""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
from test_rules import sim, per_day, metr, rules, shift_test, WIN, COMMON, RECENT, OUT

out = {}
d1 = gbt.load('D1')
p, anc = mm.all_panels(d1)

# 1. swing VWAP redraw
anc['delay_bars'] = anc.confirm_i - anc.anchor_i
anc['move_usd'] = np.where(anc.kind == -1, anc.confirm_close - anc.price, anc.price - anc.confirm_close)
anc['move_pct'] = 100 * anc.move_usd / anc.price
anc.to_csv(OUT + 'swing_anchors_D1.csv', index=False)
out['swing'] = dict(n=len(anc), median_delay=float(anc.delay_bars.median()), median_move_pct=round(float(anc.move_pct.median()), 1),
                    days_recoloured_pct=round(100 * float((p.vw_dir_live != p.vw_dir_redrawn).mean()), 1),
                    vwap_redrawn_diff_median_usd=round(float((p.vwap_live - p.vwap_redrawn).abs()[p.vw_dir_live != p.vw_dir_redrawn].median()), 1),
                    last=anc.tail(4)[['anchor_time', 'price', 'kind', 'confirm_time', 'confirm_close', 'delay_bars', 'move_usd']].astype(str).to_dict('records'))

# 2. Range Oscillator bounds drift
a14 = mm.pine_atr(d1, 14)
yr = p.groupby(p.index.year)
out['range_osc'] = dict(
    beyond_100_pct_by_year={int(k): round(100 * float((g.rng.abs() > 100).mean()), 0) for k, g in yr if g.rng.notna().any()},
    atr14_over_atr2000_last=round(float(a14.iloc[-1] / (p.rng_atr.iloc[-1] / 2)), 2),
    atr14_last=round(float(a14.iloc[-1]), 1), atr2000_last=round(float(p.rng_atr.iloc[-1] / 2), 1))

# 3. how alike the panels are (D1 bull/bear votes)
c = p.close
V = pd.DataFrame({'MA 20/50': np.where((c > p.sma20) & (p.sma20 > p.sma50), 1, np.where((c < p.sma20) & (p.sma20 < p.sma50), -1, 0)),
                  'Swing VWAP': p.vw_dir_live, 'RSI': np.sign(p.rsi - 50), 'MACD hist': np.sign(p.macd_hist),
                  'RTI': np.sign(p.rti - 50), 'ASI': np.sign(p.asi), 'Range Osc': np.sign(p.rng)}, index=p.index).loc['2005-04':]
corr = V.corr().round(2)
corr.to_csv(OUT + 'panel_vote_correlation_D1.csv')
off = corr.values[np.triu_indices(7, 1)]
out['panel_corr'] = dict(mean=round(float(off.mean()), 2), min=round(float(off.min()), 2), max=round(float(off.max()), 2),
                         rsi_vs_rti_asi_rng={k: float(corr.loc['RSI', k]) for k in ['MACD hist', 'RTI', 'ASI', 'Range Osc']})

# 4. today's reading (last closed D1 bar, 9 Oct 2026)
last = p.iloc[-1]
out['today'] = {k: round(float(last[k]), 2) for k in ['close', 'sma20', 'sma50', 'sma200', 'rsi', 'rsi_ma', 'macd', 'macd_sig', 'macd_hist',
                                                       'rti', 'rti_sig', 'asi', 'asi_sig', 'rng', 'vwap_live', 'vw_dir_live']}
out['today']['votes'] = {k: int(V.iloc[-1][k]) for k in V.columns}
hi50 = d1.high.rolling(50).max()
out['today']['last_50day_high'] = str(d1.index[np.where(d1.high.values >= hi50.values)[0][-1]].date())

# 5. leading rules: timing test, by year, pair
from importlib import import_module
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/long-core')
common = import_module('common')
pair_d, _, _, _ = common.pair_daily()
pair_d = pair_d.loc[COMMON[0]:COMMON[1]]
lead = [('D1', 'MACD line sign', 'long only'), ('D1', 'Close vs 89 EMA (main chart)', 'long only'),
        ('H4', 'MA stack 20/50/200', 'long only'), ('H1', 'Range Osc +/-100 breakout, exit at 0', 'long only'),
        ('H1', 'All panels: 5+ of 7 agree', 'long only'), ('H1', 'MACD histogram sign', 'long only'),
        ('D1', 'All panels: 7+ of 7 agree', 'long only'), ('H4', 'Hold 0.01 lot long', 'long only')]
cache = {}
res = []
for tf, name, mode in lead:
    if tf not in cache:
        d = gbt.load(tf); pp, _ = mm.all_panels(d); R, _ = rules(pp)
        R['Hold 0.01 lot long'] = np.ones(len(d), int)
        cache[tf] = (d, R)
    d, R = cache[tf]
    pos = np.asarray(R[name], int)
    if mode == 'long only':
        pos = np.clip(pos, 0, 1)
    pb, t, held = sim(d, pos)
    pd_ = per_day(pb)
    yrs = pd_.groupby(pd_.index.year).mean().round(2).to_dict()
    row = dict(tf=tf, rule=name, mode=mode,
               beats_shifted_train=shift_test(d, pos, WIN[tf]['train'], runs=100) if not name.startswith('Hold') else np.nan,
               beats_shifted_test=shift_test(d, pos, WIN[tf]['test'], runs=100) if not name.startswith('Hold') else np.nan,
               by_year=yrs)
    x = pd_.reindex(pair_d.index, fill_value=0.0)
    comb = pair_d + x
    eq = comb.cumsum()
    m = comb.groupby(comb.index.to_period('M')).sum()
    row.update(corr_with_pair=round(float(np.corrcoef(x, pair_d)[0, 1]), 2),
               corr_weekly=round(float(np.corrcoef(x.resample('W').sum(), pair_d.resample('W').sum())[0, 1]), 2),
               rule_common=round(float(x.mean()), 2), pair_plus_rule=round(float(comb.mean()), 2),
               pair_plus_rule_dd=round(float((eq - eq.cummax()).min()), 0), losing_months=f'{(m < 0).sum()}/{len(m)}')
    res.append(row)
peq = pair_d.cumsum(); pm = pair_d.groupby(pair_d.index.to_period('M')).sum()
out['pair_alone'] = dict(per_day=round(float(pair_d.mean()), 2), dd=round(float((peq - peq.cummax()).min()), 0),
                         losing_months=f'{(pm < 0).sum()}/{len(pm)}')
out['leaders'] = res
json.dump(out, open(OUT + 'diagnostics.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
