"""TRAIN only: (1) best user-style brackets (TP<=0.3, timeout<=3) per candidate from bracket_train.csv;
(2) union of the three pullback-fade variants (M2 q1 H1, M3 q2 M15, forming-M5 minute-3 strong vs M15)
bracket grid, to see if more trades/day keep the edge."""
import itertools
from sigs import *
b = pd.read_csv('bracket_train.csv')
pd.set_option('display.width', 250)
u = b[(b.tp <= 0.3) & (b.to <= 3)]
print('best user-style bracket (TP<=0.3, timeout<=3) per signal, TRAIN:')
print(u.loc[u.groupby('sig').per_day.idxmax()][['sig','tp','sl','to','mo','per_day','trades_day','per_trade','win']].round(3).to_string(index=False))
H = Harness(); m = H.m1
f = forming(m, 5); c5 = resample(m, 5)
avg5 = htf_on_m1(m, c5, 'M5', (c5.close - c5.open).abs().rolling(20).mean().values).values
body = np.abs(f.f_close - f.f_open).values; rng = (f.f_high - f.f_low).values; col = np.sign(f.f_close - f.f_open).values
t15 = trend(m, 'M15')
s_form = np.where((f.f_minute.values == 3) & (body >= avg5) & (body >= 0.9 * rng) & (col == -t15), -col, 0)
s1 = pullback(m, 2, False, 1.0, 0.9, 'H1'); s2 = pullback(m, 3, False, 2.0, 0.9, 'M15')
U = np.sign(s1 + s2 + s_form)
MID = pd.Timestamp('2026-08-01'); rows = []
for tp, sl, to, mo in itertools.product((0.5, 0.75, 1.0), (3, 5, 8), (10, 20, 30), (1, 3, 10)):
    days, tr = H.run(U, tp, sl, timeout=to, max_open=mo)
    d = days[days.index < SPLIT]; t = tr[tr.entry < SPLIT]
    rows.append(dict(tp=tp, sl=sl, to=to, mo=mo, per_day=d.pnl.mean(), A=d.pnl[d.index < MID].mean(), B=d.pnl[d.index >= MID].mean(),
                     trades_day=len(t) / len(d), per_trade=t.pnl.mean(), win=(t.pnl > 0).mean()))
df = pd.DataFrame(rows)
print('\nunion signals/day (train):', round(((U != 0) & (m.index < SPLIT)).sum() / 47, 1), ' configs', len(df))
print(df.sort_values('per_day', ascending=False).head(6).round(3).to_string(index=False))
r = df[(df.A > 0) & (df.B > 0)]
print('positive both halves:', len(r)); print(r.assign(mn=np.minimum(r.A, r.B)).sort_values('mn', ascending=False).head(5).round(3).to_string(index=False))
