import sys; sys.dont_write_bytecode = True
import pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-demo-pair/review/replay-fidelity')
from asia_port import ea_trades, per_day
for tp in (5, 8):
    for ct in (1410, 1365):
        A = ea_trades(tp, 50, close_tod=ct)
        o = A[A.nights > 0]
        print(f'TP{tp} close {ct//60}:{ct%60:02d}: trades {len(A)}, $/day {per_day(A).mean():.3f}, overnight {len(o)}:',
              [(str(r.entry_time), str(r.exit_time), r.why, round(r.pnl, 1)) for r in o.itertuples()])
