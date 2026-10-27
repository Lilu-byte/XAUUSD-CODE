import sys; sys.path.insert(0,'/mnt/project-files/xauusd-strategy-check/code')
from load import *; from bt import *
d=mt5(); c=d.close
start='2005-04-01'  # first date with a 200-day average
P={'buy&hold 1x':pd.Series(1.0,index=c.index),
   'MA200 1x':ma_rule(c),
   'volsize only (no filter)':volsize(c),
   'MA200 + volsize (proposed)':ma_rule(c)*volsize(c)}
for fin in ['today','ffr']:
  for exe in ['close','open']:
    print(f'--- financing={fin} execution={exe}')
    rows=[stats(run(d,p,fin=fin,exe=exe)[start:],p[start:],k) for k,p in P.items()]
    print(pd.DataFrame(rows).to_string(index=False))
