import pandas as pd, sys
d = pd.read_csv(sys.argv[1])
d['t'] = pd.to_datetime(d['time'], format='%Y.%m.%d %H:%M')
d['day'] = d['t'].dt.date
first = d.groupby('day').first()
print(first['t'].dt.strftime('%H:%M').value_counts().head(10))
print('tick_volume of first bar when at 01:00 / 00:00:')
fb = first[first['t'].dt.strftime('%H:%M').isin(['01:00','00:00'])]
print(fb['tick_volume'].describe())
print((fb['tick_volume'] <= 5).sum(), 'days with <=5 ticks in the opening M5 bar')
