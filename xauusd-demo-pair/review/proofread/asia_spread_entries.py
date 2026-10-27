import sys
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
import pandas as pd
from lib import load
d = load('M5')
t = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
sp = d.spread.reindex(t.entry_time).values
print('entry bars with recorded spread > 80 points:', (sp > 80).sum(), 'max', sp.max())
st = t[t.why == 'next open']
print('stale exits, spread at exit bar:', d.spread.reindex(st.exit_time).tolist())
