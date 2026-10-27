"""Stage C (TRAIN only, mlib v2): daily profit target / daily loss limit on top of the best Stage-B MR configs and
'user-style' high-win-rate brackets on the dense signals. RAND fills (one realised path per seed, 5 seeds averaged)
so the stop-for-the-day logic sees a real win/loss sequence (FAIR books expected values on mixed bars)."""
from sigs2 import *
import itertools

m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
B = pd.read_csv(OUT + 'stageB2_train.csv')
B = B[(B.sig.isin(['MR', 'MR6'])) & (B.be_trig == 0) & (B.pd_jul > 0) & (B.pd_aug > 0)].sort_values('per_day', ascending=False)
B = B.drop_duplicates(['sig', 'tp', 'sl', 'timeout', 'gate', 'lag']).head(6)
cfg = [(r.sig, r.tp, r.sl, int(r.timeout), r.gate, int(r.lag), int(r.max_open), int(r.cooldown)) for r in B.itertuples()]
for s in ('AB', 'CF', 'HTF', 'PB'):
    for tp, sl, to in ((0.1, 5.0, 30), (0.2, 20.0, 30), (0.3, 0.3, 3), (1.0, 0.5, 10)):
        for mo in (1, 5):
            cfg.append((s, tp, sl, to, 0, 0, mo, 0))
DT = [(0, 0), (2, 0), (5, 0), (10, 0), (5, 5), (5, 10), (5, 20), (5, 50), (0, 10), (0, 20), (0, 50)]
rows = []
for (s, tp, sl, to, g, lag, mo, cd), (dt, dl) in itertools.product(cfg, DT):
    sig = (S[s] if not g else gate(S[s], m1, g, lag))[tr]
    acc = []
    for seed in range(5):
        d, t = run_pw(H, sig, tp, sl, timeout=to, max_open=mo, cooldown=cd, day_target=dt, day_loss=dl, fill='RAND', seed=seed)
        acc.append(summ(d, t, 'train'))
    r = pd.DataFrame(acc).mean().to_dict()
    r.update(sig=s, tp=tp, sl=sl, timeout=to, gate=g, lag=lag, max_open=mo, cooldown=cd, day_target=dt, day_loss=dl)
    rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(OUT + 'daytarget2_train.csv', index=False)
pd.set_option('display.width', 250)
c = ['sig', 'tp', 'sl', 'timeout', 'gate', 'max_open', 'cooldown', 'day_target', 'day_loss', 'per_day', 'trades_day', 'win',
     'per_trade', 'days_ge5', 'losing_days', 'worst_day', 'max_dd', 'pd_jul', 'pd_aug']
print('configs', len(R), ' positive per_day:', (R.per_day > 0).sum())
print(R.sort_values('per_day', ascending=False)[c].head(12).round(3).to_string(index=False))
key = ['sig', 'tp', 'sl', 'timeout', 'gate', 'lag', 'max_open', 'cooldown']
b = R[(R.day_target == 0) & (R.day_loss == 0)].set_index(key)
print('\npaired effect vs no day limits (median over the', len(cfg), 'configs):')
out = []
for (dt, dl), g in R.groupby(['day_target', 'day_loss']):
    x = g.set_index(key).join(b, rsuffix='_0', how='inner')
    out.append(dict(day_target=dt, day_loss=dl, per_trade_chg=(x.per_trade - x.per_trade_0).median(),
                    per_day_chg=(x.per_day - x.per_day_0).median(), trades_ratio=(x.trades_day / x.trades_day_0).median(),
                    days_ge5=x.days_ge5.median(), days_ge5_0=x.days_ge5_0.median(), worst_day=x.worst_day.median(),
                    worst_day_0=x.worst_day_0.median()))
print(pd.DataFrame(out).round(3).to_string(index=False))
for s, tp, sl in (('AB', 0.1, 5.0), ('MR', 0.75, 20.0)):
    print(f'\nexample {s} {tp}/{sl}:')
    print(R[(R.sig == s) & (R.tp == tp) & (R.sl == sl)][c].round(3).to_string(index=False))
