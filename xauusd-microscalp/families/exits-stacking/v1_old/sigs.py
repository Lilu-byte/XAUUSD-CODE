"""Simple direction signals for the exits-stacking family (all decided at the close of M1 bar i, no look-ahead).
AB    always buy                       CF   coin flip (fixed seed)
COL   M1 candle colour follow           FADE M1 candle colour fade (mirror of COL)
HTF   M5, M15 and H1 trend agree (closed-bar close vs EMA20 of that TF, via htf_on_m1) -> trade that way
PB    pullback in trend: M15 & H1 trend agree and the last 3 M1 closes moved against it (close[i] < close[i-3]
      in an up-trend) -> enter with the trend
HCOL  M1 candle colour follow only when it agrees with the HTF agreement
"""
from mysim import *

_TF = {}


def trend_tf(m1, tf, n=20):
    if tf not in _TF:
        d = load(tf)
        _TF[tf] = d
    d = _TF[tf]
    v = np.sign(d.close - ema(d.close, n)).values      # value of the CLOSED bar (indexed by its open)
    return htf_on_m1(m1, d, tf, v).values


def build(m1):
    n = len(m1); S = {}
    S['AB'] = np.ones(n)
    S['CF'] = np.where(np.random.default_rng(12345).random(n) < .5, 1., -1.)
    col = np.sign(m1.close - m1.open).values
    S['COL'] = col
    S['FADE'] = -col
    t5, t15, t60 = trend_tf(m1, 'M5'), trend_tf(m1, 'M15'), trend_tf(m1, 'H1')
    agree = np.where((t5 == t15) & (t15 == t60), t60, 0)
    S['HTF'] = np.nan_to_num(agree)
    tr2 = np.nan_to_num(np.where(t15 == t60, t60, 0))
    back = np.sign(m1.close - m1.close.shift(3)).values
    S['PB'] = np.where((tr2 != 0) & (back == -tr2), tr2, 0)
    S['HCOL'] = np.where((S['HTF'] != 0) & (col == S['HTF']), col, 0)
    return {k: np.nan_to_num(v).astype(float) for k, v in S.items()}


if __name__ == '__main__':
    m1 = load_m1(); S = build(m1)
    tr = m1.index < SPLIT
    for k, v in S.items():
        print(k, 'train signals/day %.0f' % ((v[tr] != 0).sum() / 47), 'long share %.2f' % ((v[tr] == 1).sum() / max((v[tr] != 0).sum(), 1)))
