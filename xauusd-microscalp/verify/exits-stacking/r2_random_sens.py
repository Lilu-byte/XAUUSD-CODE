"""Step 3 (random-direction baseline, 50 seeds) and step 4 (sensitivity) on the M1 data."""
from common import *

m1, H, g = load_m1_harness()
SPLIT = mlib.SPLIT
mr = mr_signal(m1)
TE0, TE_MID, TE1 = SPLIT, pd.Timestamp('2026-09-21'), None
pd.set_option('display.width', 250)


def avg(sig, seeds=range(5), lo=SPLIT, hi=None, **kw):
    rows = [summ(g, *g.run(sig, seed=s, **kw), lo=lo, hi=hi) for s in seeds]
    df = pd.DataFrame(rows)
    out = df.mean(numeric_only=True).to_dict()
    out['worst_day_min'] = df.worst_day.min(); out['max_dd_float_min'] = df.max_dd_float.min(); out['forced_sum'] = int(df.n_forced.sum())
    return out


base = avg(mr)
print(f'claim TEST per_day {base["per_day"]:+.3f}')

# ---- 3. random direction, same signal bars, 50 seeds (each averaged over the same 5 FAIR path seeds)
rnd = []
for s in range(50):
    rs = mlib.random_like(mr, 1000 + s)
    r = avg(rs)
    rnd.append(dict(seed=s, per_day=r['per_day'], worst_day=r['worst_day_min'], dd=r['max_dd_float_min'], forced=r['forced_sum'],
                    basket_win=r['basket_win'], baskets_day=r['baskets_day']))
rnd = pd.DataFrame(rnd)
rnd.to_csv(VOUT + 'r2_random50.csv', index=False)
share = (rnd.per_day >= base['per_day']).mean()
print(f'random direction 50 seeds TEST: mean {rnd.per_day.mean():+.3f} sd {rnd.per_day.std():.3f} min {rnd.per_day.min():+.2f} max {rnd.per_day.max():+.2f}; '
      f'share >= claim {share:.2f}; seeds with a losing worst day {(rnd.worst_day < 0).mean():.2f}; median worst day {rnd.worst_day.median():+.1f}; '
      f'median maxDDfloat {rnd.dd.median():+.0f}; seeds with forced closes {(rnd.forced > 0).mean():.2f}')
# also TRAIN for the random baseline
rtr = [avg(mlib.random_like(mr, 1000 + s), lo=None, hi=SPLIT)['per_day'] for s in range(50)]
trc = avg(mr, lo=None, hi=SPLIT)['per_day']
print(f'random direction 50 seeds TRAIN: mean {np.mean(rtr):+.3f}; claim TRAIN {trc:+.3f}; share >= claim {(np.array(rtr) >= trc).mean():.2f}')
# coin flip on EVERY bar (no MR timing) for contrast
cf = np.where(np.random.default_rng(7).random(len(m1)) < .5, 1, -1)
r = avg(cf)
print(f'coin flip on every bar (not MR bars) TEST: per_day {r["per_day"]:+.2f} baskets/day {r["baskets_day"]:.1f} worst_day {r["worst_day_min"]:+.1f} forced {r["forced_sum"]}')

# ---- 4. sensitivity
rows = []
def add(label, sig=mr, lo=SPLIT, hi=None, **kw):
    r = avg(sig, lo=lo, hi=hi, **kw); r['label'] = label; rows.append(r)
    print(f'{label:38s} per_day {r["per_day"]:+7.2f} pos/day {r["positions_day"]:5.1f} bsk/day {r["baskets_day"]:5.1f} per_pos {r["per_position"]:+.3f} '
          f'bwin {r["basket_win"]:.4f} worst_day {r["worst_day_min"]:+8.1f} maxDDf {r["max_dd_float_min"]:+8.1f} maxlev {r["max_levels"]:.0f} forced {r["forced_sum"]}')

add('TEST FAIR base (claim)')
add('TEST OHLC path', path='OHLC', seeds=[0])
add('TEST FAIRO path (open-only odds)', path='FAIRO')
add('TEST ADV path (extreme vs basket first)', path='ADV', seeds=[0])
add('TEST FAV path (favourable first)', path='FAV', seeds=[0])
add('TEST spread bar', spread='bar')
add('TEST spread wide 0.30', spread='wide')
add('TEST gap fills all crossed levels', gap_multi=True)
add('TEST 1st half (Sep 1-20)', hi=TE_MID)
add('TEST 2nd half (Sep 21-Oct 9)', lo=TE_MID)
longs = np.where(mr == 1, 1, 0); shorts = np.where(mr == -1, -1, 0)
add('TEST longs only', sig=longs)
add('TEST shorts only', sig=shorts)
add('TRAIN longs only', sig=longs, lo=None, hi=SPLIT)
add('TRAIN shorts only', sig=shorts, lo=None, hi=SPLIT)
# realistic frictions: slippage on every fill (adds + the close-all), modelled as extra spread
for x in (0.10, 0.20, 0.40):
    add(f'TEST spread base+{x:.2f}', spr=g.spr['base'] + x)
# spread spikes: real spreads around news/rollover can be several $; double the spread in high-range bars
rng_ = (m1.high - m1.low).values; a240 = (m1.high - m1.low).rolling(240).mean().bfill().values
spk = g.spr['base'] + np.where(rng_ > 3 * a240, 0.5, 0.0)
add('TEST +$0.50 spread on bars with range>3x atr', spr=spk)
# neighbourhood of the frozen parameters
for st in (1.5, 2.5, 3.0):
    add(f'TEST step {st}', step=st)
for bt in (0.2, 0.5, 1.0):
    add(f'TEST basket target {bt}', btp=bt)
for ml in (10, 20, 30):
    add(f'TEST max positions {ml}', maxlev=ml)
for bs in (100.0, 300.0):
    add(f'TEST basket stop -{bs:.0f}', bsl=bs)
add('TEST earlier session end 21:58', end_tod=21 * 60 + 58)
add('TEST entries only to 21:00', last_tod=21 * 60)
pd.DataFrame(rows).to_csv(VOUT + 'r2_sensitivity.csv', index=False)

# exposure profile (for calibrating coarser-timeframe proxies)
days, bask, eql, levh = g.run(mr, seed=0)
bt = bask[bask.start >= SPLIT]
inmkt = bt.bars.sum() / len(np.unique(m1.index[m1.index >= SPLIT].normalize()))
print(f'\nTEST seed0: baskets {len(bt)}, bars in market/day {inmkt:.0f}, depth quantiles {bt.levels.quantile([.5, .9, .99, .999]).tolist()}, '
      f'max {bt.levels.max()}, P(levels>=10) {(bt.levels >= 10).mean():.4f}')
bt2 = bask
print('ALL seed0 deepest baskets:'); print(bask.sort_values('mae').head(8).to_string())
