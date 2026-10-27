"""Model fitting helpers. score > 0 means 'up', |score| = confidence."""
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer

LGB = dict(num_leaves=15, learning_rate=0.03, n_estimators=300, min_child_samples=300, subsample=0.7,
           subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, n_jobs=4, random_state=1)


def make_y(fwd, cost, kind):
    """fwd: forward bid move ($); cost: spread per bar ($)."""
    if kind in ('bin', 'binw', 'logit'):
        return (fwd > 0).astype(int), (np.abs(fwd) if kind == 'binw' else None)
    if kind == 'tri':      # 0 down beyond cost, 1 flat, 2 up beyond cost
        return np.where(fwd > cost, 2, np.where(fwd < -cost, 0, 1)), None
    if kind == 'reg':
        return fwd, None
    raise ValueError(kind)


def fit(X, fwd, cost, kind, **kw):
    y, w = make_y(fwd, cost, kind)
    p = {**LGB, **kw}
    if kind in ('bin', 'binw'):
        m = lgb.LGBMClassifier(objective='binary', **p).fit(X, y, sample_weight=w)
    elif kind == 'tri':
        m = lgb.LGBMClassifier(objective='multiclass', **p).fit(X, y)
    elif kind == 'reg':
        q = np.nanquantile(np.abs(y), 0.99)
        m = lgb.LGBMRegressor(objective='huber', alpha=1.0, **p).fit(X, np.clip(y, -q, q))
    elif kind == 'logit':
        m = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(),
                          LogisticRegression(C=kw.get('C', 0.01), max_iter=500)).fit(X, y)
    m.kind_ = kind
    return m


def score(m, X):
    if m.kind_ in ('bin', 'binw', 'logit'):
        return m.predict_proba(X)[:, 1] - 0.5
    if m.kind_ == 'tri':
        p = m.predict_proba(X); return p[:, 2] - p[:, 0]
    return m.predict(X)


def roll_thr(s, q, window=3960):
    """Trailing threshold: the (1-q) quantile of |score| over the previous `window` rows (excludes the
    current row; known live). Returns array; NaN until 500 rows of history."""
    a = pd.Series(np.abs(s))
    return a.shift(1).rolling(window, min_periods=500).quantile(1 - q).values


def signal(s, thr):
    s = np.asarray(s); ok = np.abs(s) >= thr
    return np.where(ok & ~np.isnan(thr), np.sign(s), 0).astype(int)
