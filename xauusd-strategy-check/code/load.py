import pandas as pd, numpy as np
def mt5():
    d=pd.read_csv('/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv')
    d['time']=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M'); return d.set_index('time')
def oanda():
    d=pd.read_csv('/tmp/claude-0/oanda/xauusd.csv',header=None)
    d.index=pd.to_datetime(d[0],format='%Y%m%d %H:%M')
    o=pd.DataFrame({'open':(d[1]+d[6])/2,'high':(d[2]+d[7])/2,'low':(d[3]+d[8])/2,'close':(d[4]+d[9])/2,'spread':d[9]-d[4]})
    return o
