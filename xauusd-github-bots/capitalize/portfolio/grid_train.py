"""Every portfolio-rule variant, scored on TRAIN ONLY (2016-07-29 .. 2021-12-31, trades closed in the window).
No test-period number is computed or printed here."""
from rules import *
import itertools, time

a, b = TRAIN
d = load('H1'); dtr = d[(d.index >= a) & (d.index < b)]
yrs = len(np.unique(dtr.index.normalize())) / 252

# GoldAllAgree proxy (long while H1 and H4 EMA20>EMA80), train only, for a portfolio view in old years
g = gaa_proxy(d)
sig_g = np.where(g > 0.5, 1.0, 0.0)
tg = simulate(d, sig_g, exit_long=(g < 0.5))
pgp = daily(*window(tg, d, a, b))
print('GAA proxy train $/day', round(pgp.mean(), 2), 'dd', round(maxdd(pgp)), 'by year', pgp.groupby(pgp.index.year).mean().round(2).to_dict())

rows = []; cache = {}
t0 = time.time()
for bot, dr, ga, rg, cut in variants():
    key = (bot, dr, ga, rg)
    if key not in cache:
        cache[key] = build(bot, dr, ga, rg)[1]
    t = apply_cut(cache[key], cut)
    tt, dd = window(t, d, a, b)
    tt = tt[tt.entry_time >= a]
    p = daily(tt, dd)
    yr = p.groupby(p.index.year).mean()
    comb = p + pgp
    w = tt.pnl[tt.pnl > 0].sum(); l = -tt.pnl[tt.pnl < 0].sum()
    rows.append(dict(bot=bot, dir=dr, gaa=ga, regime=rg, cut=cut, per_day=round(p.mean(), 3), trades_yr=round(len(tt) / yrs, 1),
                     win=round((tt.pnl > 0).mean() * 100, 1), pf=round(w / l, 2) if l > 0 else np.nan,
                     R_yr=round(tt.R.sum() / yrs, 1), max_dd=round(maxdd(p)), pos_years=int((yr[yr.index >= 2017] > 0).sum()),
                     worst_year=round(yr.min(), 2), long_share=round((tt.dir > 0).mean(), 2),
                     corr_gaa_proxy=round(np.corrcoef(p, pgp)[0, 1], 2), comb_per_day=round(comb.mean(), 3), comb_dd=round(maxdd(comb)),
                     **{f'y{k}': round(v, 2) for k, v in yr.items()}))
print('variants', len(rows), 'secs', round(time.time() - t0))
r = pd.DataFrame(rows)
r.to_csv(OUT + 'grid_train.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
cols = ['bot', 'dir', 'gaa', 'regime', 'cut', 'per_day', 'trades_yr', 'win', 'pf', 'R_yr', 'max_dd', 'pos_years', 'worst_year', 'corr_gaa_proxy', 'comb_per_day', 'comb_dd']
print('\nraw bots (no portfolio rule):'); print(r[(r.gaa == 'none') & (r.regime == 'none') & (r.cut == 'none')][cols].to_string(index=False))
print('\npositive train $/day:', (r.per_day > 0).sum(), 'of', len(r), '| positive R:', (r.R_yr > 0).sum())
el = r[r.trades_yr >= 10]
print('\nTop 20 by train $/day (>=10 trades/yr):'); print(el.sort_values('per_day', ascending=False).head(20)[cols].to_string(index=False))
print('\nTop 15 by train R/yr (>=10 trades/yr):'); print(el.sort_values('R_yr', ascending=False).head(15)[cols].to_string(index=False))
print('\nmean train $/day by factor:')
for f in ['bot', 'dir', 'gaa', 'regime', 'cut']:
    print(f, r.groupby(f).per_day.mean().round(3).to_dict(), '| R_yr', r.groupby(f).R_yr.mean().round(1).to_dict())
