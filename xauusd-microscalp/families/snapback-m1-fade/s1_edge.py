"""Stage 1 (TRAIN only): net $ per signal of a pure time exit after N bars, as the EA would enter (open of the next bar,
long pays the ask there, short pays the ask at the exit), base spread, EA filter, no caps (every signal bar counted,
overlapping). Exit at the bid/ask close of bar i+N; signals whose exit bar is not in the same session are dropped.
Gives the landscape over signal definitions and N before any position caps are involved."""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *

m, H = load_train()
f = feats(m)
o, c = m.open.values, m.close.values
sp = H._spr['base']
day = H.day; n = len(m)
okhours = (m.tod.values >= FIRST_ENTRY_TOD) & (m.tod.values <= LAST_ENTRY_TOD) & ~m.last_of_session.values
NS = list(range(1, 16))
isA = (m.index < HALF)
ndA = len(np.unique(m.index[isA].normalize())); ndB = len(np.unique(m.index[~isA].normalize()))
# net per-bar outcome arrays for long and short at each N
LONG = {}; SHORT = {}
for N in NS:
    j = np.arange(n) + N
    jj = np.minimum(j, n - 1)
    same = (j < n) & (day[jj] == day) & (m.tod.values[jj] <= END_TOD)
    lg = c[jj] - (np.r_[o[1:], np.nan] + np.r_[sp[1:], np.nan])
    sh = np.r_[o[1:], np.nan] - (c[jj] + sp[jj])
    LONG[N] = np.where(same, lg, np.nan); SHORT[N] = np.where(same, sh, np.nan)

rows = []
TH = {'atr': [1.5, 2, 2.5, 3, 3.5, 4, 5], 'usd': [2, 3, 4, 5, 6, 8, 10]}
for k, mode, gate, fresh, sg in itertools.product((1, 2, 3), ('atr', 'usd'), ('none', 'away', 'toward'), (False, True), (0.0, 0.15)):
    for th in TH[mode]:
        s = fade_signal(f, k, mode, th, gate, fresh, sg)
        s = ea_filter(m, s) * okhours
        sel = s != 0
        for N in NS:
            x = np.where(s == 1, LONG[N], np.where(s == -1, SHORT[N], np.nan))
            a = x[sel & isA]; b = x[sel & ~isA]
            a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
            rows.append(dict(k=k, mode=mode, th=th, gate=gate, fresh=fresh, sgate=sg, N=N,
                             nA=len(a) / ndA, nB=len(b) / ndB, mA=a.mean() if len(a) else np.nan, mB=b.mean() if len(b) else np.nan,
                             m=np.r_[a, b].mean() if len(a) + len(b) else np.nan,
                             longsh=(s[sel] == 1).mean() if sel.any() else np.nan))
R = pd.DataFrame(rows)
R['n'] = (R.nA * ndA + R.nB * ndB) / (ndA + ndB)
R['both'] = (R.mA > 0) & (R.mB > 0)
R.to_csv(FAM + 's1_edge_train.csv', index=False)
print('cells', len(R), 'signals', len(R) // len(NS))
print('share of cells with mean net > 0 in both halves:', round(R.both.mean(), 3))
pd.set_option('display.width', 250)
print('\nshare both-halves-positive by k x gate (all thresholds, N, fresh, sgate):')
print(R.pivot_table(index='k', columns='gate', values='both', aggfunc='mean').round(3).to_string())
print('\nshare both-halves-positive by N:')
print(R.groupby('N').both.mean().round(3).to_string())
print('\nmean net per signal by N (median over signal defs with n >= 3/day):')
print(R[R.n >= 3].groupby('N')[['mA', 'mB']].median().round(3).T.to_string())
print('\nsgate effect (median mA, mB over cells with n>=3):')
print(R[R.n >= 3].groupby('sgate')[['mA', 'mB']].median().round(3).to_string())
print('\nfresh effect:')
print(R[R.n >= 3].groupby('fresh')[['mA', 'mB']].median().round(3).to_string())
c = ['k', 'mode', 'th', 'gate', 'fresh', 'sgate', 'N', 'nA', 'nB', 'mA', 'mB', 'longsh']
R['pot'] = R.n * R[['mA', 'mB']].min(axis=1)
print('\ntop 25 by n/day x min(halves mean), n >= 3/day:')
print(R[(R.n >= 3) & R.both].sort_values('pot', ascending=False)[c + ['pot']].head(25).round(3).to_string(index=False))
