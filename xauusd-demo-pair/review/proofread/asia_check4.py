import sys
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
import pandas as pd
from lib import load
d = load('M5')
for t, dr, ent, ex in [('2025-08-22 09:40', -1, 3326.65, '2025-08-22 17:55'), ('2025-11-18 09:25', -1, 4003.58, '2025-11-18 15:35'),
                       ('2025-12-01 12:05', 1, 4259.68, '2025-12-01 22:45'), ('2026-01-27 09:35', 1, 5096.67, '2026-01-27 16:20')]:
    x = d.loc[t:ex]
    o = x.open.iloc[0]
    if dr == 1:
        print(t, 'buy  open', o, 'ask', o + 0.3, 'fill', ent, 'best bid high', x.high.max(), 'TP from fill', round(ent + 5, 2), 'TP from ask', round(o + 0.3 + 5, 2))
    else:
        print(t, 'sell open(bid)', o, 'fill', ent, 'best ask low', round(x.low.min() + 0.3, 2), 'TP from fill', round(ent - 5, 2), 'TP from bid', round(o - 5, 2))
