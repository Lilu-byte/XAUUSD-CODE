import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from feats import *

KS = (1, 2, 3, 5, 10, 15, 20)


class Scanner:
    """Train-only edge measurement: TRAIN-A (Jun26-Jul31), TRAIN-B (Aug), TRAIN (all). Never touches TEST."""

    def __init__(self, m, f):
        self.m, self.f = m, f
        self.F = fwd(m, KS)
        self.spr = spread_series(m, 'base')
        self.ok = valid_mask(m, f)
        idx = m.index
        self.pA = (idx < A_SPLIT); self.pB = (idx >= A_SPLIT) & (idx < SPLIT); self.pT = idx < SPLIT
        self.nd = {p: len(np.unique(idx[s].date)) for p, s in (('A', self.pA), ('B', self.pB), ('T', self.pT))}
        self.rows = []

    def add(self, name, d):
        """d: +1/-1/0 array of FOLLOW direction. Records follow; fade is just the negative move."""
        d = np.nan_to_num(np.asarray(d, float)); d[~self.ok] = 0
        r = dict(name=name)
        for p, s in (('A', self.pA), ('B', self.pB), ('T', self.pT)):
            sel = (d != 0) & s
            r[f'n{p}'] = sel.sum() / self.nd[p]
            r[f'spr{p}'] = self.spr[sel].mean() if sel.any() else np.nan
            for k in KS:
                x = (self.F[k] * d)[sel]; x = x[~np.isnan(x)]
                r[f'm{k}{p}'] = x.mean() if len(x) else np.nan
        # t-stat of 3-bar move on train
        sel = (d != 0) & self.pT; x = (self.F[3] * d)[sel]; x = x[~np.isnan(x)]
        r['t3'] = x.mean() / (x.std() / np.sqrt(len(x))) if len(x) > 10 else np.nan
        self.rows.append(r)
        return r

    def table(self):
        t = pd.DataFrame(self.rows).set_index('name')
        # best |move| at any horizon on train, with the direction (follow +, fade -)
        mv = t[[f'm{k}T' for k in KS]]
        t = t[mv.notna().any(axis=1)].copy(); mv = mv.loc[t.index]
        t['bestk'] = mv.abs().fillna(0).idxmax(axis=1).str[1:-1].astype(int)
        t['bestm'] = [t.loc[i, f'm{k}T'] for i, k in zip(t.index, t.bestk)]
        t['net'] = t.bestm.abs() - t.sprT
        t['dir'] = np.where(t.bestm > 0, 'follow', 'fade')
        t['A_B_same'] = [np.sign(t.loc[i, f'm{k}A']) == np.sign(t.loc[i, f'm{k}B']) for i, k in zip(t.index, t.bestk)]
        t['netA'] = [abs(t.loc[i, f'm{k}A']) * (1 if np.sign(t.loc[i, f'm{k}A']) == np.sign(t.loc[i, 'bestm']) else -1)
                     - t.loc[i, 'sprA'] for i, k in zip(t.index, t.bestk)]
        t['netB'] = [abs(t.loc[i, f'm{k}B']) * (1 if np.sign(t.loc[i, f'm{k}B']) == np.sign(t.loc[i, 'bestm']) else -1)
                     - t.loc[i, 'sprB'] for i, k in zip(t.index, t.bestk)]
        return t
