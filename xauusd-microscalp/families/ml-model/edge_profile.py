"""TRAIN-only diagnostic: for walk-forward OOS signals (Jul20-Aug31) of candidate configs, the avg favourable
move over 1..10 min vs spread, and how volatile the signal bars are (why a $1 TP cap matters)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from bracket import oos_signal
from mlib import *
m1 = load_m1(); rng = (m1.high - m1.low).values
lo = (m1.index >= pd.Timestamp('2026-07-20')) & (m1.index < SPLIT)
print('all OOS bars: median M1 range', np.median(rng[lo]).round(2))
for cfg in sys.argv[1:]:
    sig, k = oos_signal(len(m1), cfg)
    e = edge(m1, sig, horizons=(1, 2, 3, 5, 10, 20)).loc[['train']]
    nxt = np.roll(rng, -1)
    print(cfg, ' median range of signal bar / next bar:', np.median(rng[sig != 0]).round(2), np.median(nxt[sig != 0]).round(2))
    print(e.round(3).to_string())
