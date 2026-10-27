import sys; sys.dont_write_bytecode = True
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-demo-pair/review/replay-fidelity')
from asia_port import engine_trades, ea_trades, per_day, P, idx, days
for tp in (5, 8):
    E1 = engine_trades(tp, 50, scale=False); A = ea_trades(tp, 50, with_swap=False)
    E1['pnl'] = E1.pnl_real
    m = E1.merge(A, on='entry_time', how='outer', suffixes=('_g', '_a'), indicator=True)
    b = m[m._merge == 'both']
    same_x = (b.exit_time_g - b.exit_time_a).abs() <= pd.Timedelta(minutes=5)
    print(f'TP{tp} unscaled engine vs EA: matched {len(b)}/{len(E1)} engine, EA {len(A)}; same dir {(b.dir_g==b.dir_a).sum()}; same exit reason {(b.why_g==b.why_a).sum()}; same exit bar {same_x.sum()}; '
          f'pnl matched engine {b.pnl_g.sum():.0f} EA {b.pnl_a.sum():.0f}; |diff|>1: {((b.pnl_g-b.pnl_a).abs()>1).sum()}; $/day engine {per_day(E1).mean():.3f} EA {per_day(A).mean():.3f}')
    bad = b[~same_x | (b.why_g != b.why_a)]
    print(bad[['entry_time', 'dir_g', 'why_g', 'exit_time_g', 'pnl_g', 'why_a', 'exit_time_a', 'pnl_a']].round(2).to_string())
    print(m[m._merge != 'both'][['entry_time', 'dir_g', 'dir_a', 'why_a', 'exit_time_a', 'pnl_a', '_merge']].round(2).to_string())
    E = engine_trades(tp, 50)
    print('engine EOD exits after 2026-03-01:', ((E.why == 'EOD') & (E.exit_time >= '2026-03-01')).sum(), '| overnight holds (engine scaled):', (E.exit_time.dt.normalize() > E.entry_time.dt.normalize()).sum(),
          '| EA overnight holds:', (A.nights > 0).sum(), A[A.nights > 0][['entry_time', 'exit_time', 'why', 'pnl']].round(2).to_dict('records'))
