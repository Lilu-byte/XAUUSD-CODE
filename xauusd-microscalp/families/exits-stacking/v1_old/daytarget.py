"""Stage C (TRAIN only): daily profit target ($5) / daily loss limit on top of the best Stage-B brackets and a
few 'user-style' high-win brackets. RAND fills (one realised path per seed, 5 seeds averaged) so that the
stop-for-the-day logic sees realistic win/loss sequences."""
from sigs import *
import itertools

m1 = repaired_m1(); S = build(m1); tr = m1.index < SPLIT
H = Harness(m1[tr])
B = pd.read_csv(OUT + 'grid_b_train_rep.csv')
B = B[B.trades_day >= 20].sort_values('per_trade', ascending=False)
B = B.drop_duplicates(['sig', 'tp', 'sl', 'gate', 'lag']).head(6)
cfg = [(r.sig, r.tp, r.sl, int(r.timeout), r.gate, int(r.lag), int(r.max_open), int(r.cooldown)) for r in B.itertuples()]
for s in ('AB', 'CF', 'HTF', 'PB'):
    for tp, sl, to in ((0.1, 5.0, 30), (0.2, 20.0, 30), (0.3, 0.3, 3)):
        cfg.append((s, tp, sl, to, 0, 0, 1, 0))
DT = [(0, 0), (5, 0), (10, 0), (5, 5), (5, 10), (5, 20), (5, 50), (0, 20), (0, 50)]
rows = []
for (s, tp, sl, to, g, lag, mo, cd), (dt, dl) in itertools.product(cfg, DT):
    sig = (S[s] if not g else gate(S[s], m1, g, lag))[tr]
    acc = []
    for seed in range(5):
        d, t = run_pw(H, sig, tp, sl, timeout=to, max_open=mo, cooldown=cd, day_target=dt, day_loss=dl,
                      fill='RAND', seed=seed)
        acc.append(summ(d, t, 'train'))
    r = pd.DataFrame(acc).mean().to_dict()
    r.update(sig=s, tp=tp, sl=sl, timeout=to, gate=g, lag=lag, max_open=mo, cooldown=cd, day_target=dt, day_loss=dl)
    rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(OUT + 'daytarget_train.csv', index=False)
pd.set_option('display.width', 250)
c = ['sig', 'tp', 'sl', 'timeout', 'gate', 'max_open', 'cooldown', 'day_target', 'day_loss', 'per_day', 'trades_day', 'win',
     'per_trade', 'days_ge5', 'losing_days', 'worst_day', 'max_dd']
print('configs', len(R), ' positive per_day:', (R.per_day > 0).sum())
print(R.sort_values('per_day', ascending=False)[c].head(15).round(3).to_string(index=False))
print('\neffect of day_target/day_loss (median over brackets):')
print(R.groupby(['day_target', 'day_loss'])[['per_day', 'per_trade', 'days_ge5', 'losing_days', 'worst_day']].median().round(3))
print('\nexample AB 0.1/5/30:')
print(R[(R.sig == 'AB') & (R.tp == 0.1) & (R.sl == 5.0)][c].round(3).to_string(index=False))
