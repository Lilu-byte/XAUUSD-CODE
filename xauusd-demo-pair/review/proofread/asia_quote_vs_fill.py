# Scratch: asia_ea.trades() as published vs. with SL/TP set from the quote (what the EA sends), not from the fill.
import sys, inspect
sys.path.insert(0, '/mnt/project-files/xauusd-5-a-day/code')
import asia_ea as A          # module level only loads data; the __main__ block (which writes the CSV) does not run
import pandas as pd
src = inspect.getsource(A.trades)
old_b = "if dr == 1: ent = o[i] + sp[i] + SLIP; SLp, TPp = ent - sl, ent + tp"
old_s = "else: ent = o[i] - SLIP; SLp, TPp = ent + sl, ent - tp"
assert src.count(old_b) == 1 and src.count(old_s) == 1
src2 = src.replace("def trades(", "def trades_q(").replace(old_b, "if dr == 1: q = o[i] + sp[i]; ent = q + SLIP; SLp, TPp = q - sl, q + tp").replace(old_s, "else: q = o[i]; ent = q - SLIP; SLp, TPp = q + sl, q - tp")
exec(src2, A.__dict__)
D0, D1 = A.DAYS[0], A.DAYS[-1] + pd.Timedelta(days=1)
for tp in (5, 8):
    a = A.trades(tp, 50); a = a[(a.exit_time >= D0) & (a.exit_time < D1)]
    b = A.trades_q(tp, 50); b = b[(b.exit_time >= D0) & (b.exit_time < D1)]
    print(f'TP{tp}: published {len(a)} trades ${a.pnl.sum():.1f} ({A.per_day(a).mean():.3f}/day) | from quote {len(b)} trades ${b.pnl.sum():.1f} ({A.per_day(b).mean():.3f}/day)')
    m = a.merge(b, on='entry_time', how='outer', suffixes=('_a', '_b'), indicator=True)
    diff = m[(m._merge != 'both') | (m.why_a != m.why_b)]
    print('  trades whose exit reason differs or that appear in only one:', len(diff))
    print(diff[['entry_time', 'why_a', 'why_b', 'pnl_a', 'pnl_b']].to_string() if len(diff) else '')
    print('  TP gross published:', a[a.why == 'TP'].gross.round(2).value_counts().head(3).to_dict(), ' from quote:', b[b.why == 'TP'].gross.round(2).value_counts().head(3).to_dict())
