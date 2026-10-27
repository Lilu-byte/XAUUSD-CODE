"""Simple direction signals for the exits-stacking family (decided at the close of M1 bar i; no look-ahead).
AB    always buy                      AS   always sell (drift diagnostic only)
CF    coin flip (fixed seed)
COL   M1 candle colour follow (close > open -> buy, close < open -> sell, doji -> none)
HTF   M5, M15 and H1 trend agree (last CLOSED bar's close vs its EMA20, mapped with htf_on_m1) -> trade that way
PB    pullback in trend: M15 and H1 trends agree and close[i] < close[i-3] in an up-trend (> in a down-trend)
      -> enter with the trend
MR    round-1 mean reversion: |close[i] - close[i-3]| > 3 x (240-bar mean M1 high-low range) -> fade the move
MR6   same, fixed threshold $6
"""
from mysim2 import *

_TF = {}


def trend_tf(m1, tf, n=20):
    if tf not in _TF:
        _TF[tf] = load(tf)
    d = _TF[tf]
    v = np.sign(d.close - ema(d.close, n)).values      # value of the CLOSED bar (indexed by its open time)
    return htf_on_m1(m1, d, tf, v).values


def build(m1):
    n = len(m1); S = {}
    S['AB'] = np.ones(n)
    S['AS'] = -np.ones(n)
    S['CF'] = np.where(np.random.default_rng(12345).random(n) < .5, 1., -1.)
    col = np.sign(m1.close - m1.open).values
    S['COL'] = col
    t5, t15, t60 = trend_tf(m1, 'M5'), trend_tf(m1, 'M15'), trend_tf(m1, 'H1')
    S['HTF'] = np.nan_to_num(np.where((t5 == t15) & (t15 == t60), t60, 0))
    tr2 = np.nan_to_num(np.where(t15 == t60, t60, 0))
    back = np.sign(m1.close - m1.close.shift(3)).values
    S['PB'] = np.where((tr2 != 0) & (back == -tr2), tr2, 0)
    r3 = (m1.close - m1.close.shift(3)).values
    a240 = (m1.high - m1.low).rolling(240).mean().values
    S['MR'] = np.where(np.abs(r3) > 3 * a240, -np.sign(r3), 0)
    S['MR6'] = np.where(np.abs(r3) > 6.0, -np.sign(r3), 0)
    return {k: np.nan_to_num(v).astype(float) for k, v in S.items()}


if __name__ == '__main__':
    m1 = load_m1(); S = build(m1)
    tr = m1.index < SPLIT; nd = len(np.unique(m1.index[tr].normalize()))
    for k, v in S.items():
        print(f'{k:4s} TRAIN signals/day {(v[tr] != 0).sum() / nd:7.0f}  long share {(v[tr] == 1).sum() / max((v[tr] != 0).sum(), 1):.2f}')
