"""POST-HOC (hindsight, not for choosing): every one of the 360 variants on the test window and the common window
with the pair, to check whether train ranks carried over at all. Written after final.py was run once."""
from rules import *
d = load('H1'); pg, pa = pair_daily(); pair = pg + pa; days = pair.index
tr = pd.read_csv(OUT + 'grid_train.csv')
rows = []; cache = {}
for bot, dr, ga, rg, cut in variants():
    key = (bot, dr, ga, rg)
    if key not in cache: cache[key] = build(bot, dr, ga, rg)[1]
    t = apply_cut(cache[key], cut)
    tt, dd = window(t, d, *TEST); tt = tt[tt.entry_time >= TEST[0]]; p = daily(tt, dd)
    tc = t[t.entry_time >= COMMON]
    p3 = tc.groupby(tc.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0); comb = pair + p3
    yr = p.groupby(p.index.year).mean()
    rows.append(dict(bot=bot, dir=dr, gaa=ga, regime=rg, cut=cut, test_per_day=round(p.mean(), 3), test_dd=round(maxdd(p)),
                     test_pos_years=int((yr > 0).sum()), y2022=round(yr.get(2022, 0), 2), y2023=round(yr.get(2023, 0), 2), y2024=round(yr.get(2024, 0), 2),
                     y2025=round(yr.get(2025, 0), 2), y2026=round(yr.get(2026, 0), 2),
                     common_alone=round(p3.mean(), 2), with_pair=round(comb.mean(), 2), with_pair_dd=round(maxdd(comb)),
                     with_pair_losing=losing_months(comb)[0], ratio=round(comb.sum() / -maxdd(comb), 2)))
r = pd.DataFrame(rows).merge(tr[['bot', 'dir', 'gaa', 'regime', 'cut', 'per_day', 'trades_yr']].rename(columns={'per_day': 'train_per_day'}),
                             on=['bot', 'dir', 'gaa', 'regime', 'cut'])
r.to_csv(OUT + 'posthoc_all_test.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print('Spearman train vs test $/day:', round(r.train_per_day.rank().corr(r.test_per_day.rank()), 2),
      '| train-positive variants positive in test:', ((r.train_per_day > 0) & (r.test_per_day > 0)).sum(), '/', (r.train_per_day > 0).sum(),
      '| all positive in test:', (r.test_per_day > 0).sum(), '/', len(r))
print('test variants positive in all 5 years 2022-2026:', (r.test_pos_years == 5).sum())
r['train_rank'] = r.train_per_day.rank(ascending=False)
print('pick test rank', int(r[(r.bot == 'donchian') & (r.dir == 'both') & (r.gaa == 'none') & (r.regime == 'sma200') & (r.cut == 'none')].test_per_day.rank().iloc[0]) if False else '',
      'test-rank of pick:', int(r.test_per_day.rank(ascending=False)[(r.bot == 'donchian') & (r.dir == 'both') & (r.gaa == 'none') & (r.regime == 'sma200') & (r.cut == 'none')].iloc[0]), 'of', len(r))
pair_ratio = pair.sum() / -maxdd(pair)
print('pair alone: $/day', round(pair.mean(), 2), 'dd', round(maxdd(pair)), 'losing months', losing_months(pair)[0], 'profit/dd', round(pair_ratio, 2))
print('variants whose pair+third beats the pair on profit/DD:', (r.ratio > pair_ratio).sum(), 'of', len(r))
print('\nhindsight top 12 by pair+third profit/DD (common window):')
print(r.sort_values('ratio', ascending=False).head(12).to_string(index=False))
print('\nmean test $/day by factor (hindsight):')
for f in ['bot', 'dir', 'gaa', 'regime', 'cut']:
    print(f, r.groupby(f).test_per_day.mean().round(3).to_dict(), '| with_pair', r.groupby(f).with_pair.mean().round(2).to_dict(), '| dd', r.groupby(f).with_pair_dd.mean().round(0).to_dict())
