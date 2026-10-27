import pandas as pd, sys
d = pd.read_csv(sys.argv[1])
d['t'] = pd.to_datetime(d['time'], format='%Y.%m.%d %H:%M')
d['day'] = d['t'].dt.date
first = d.groupby('day').first()
x = first[first['t'].dt.strftime('%H:%M') == '01:05']
print(x['t'].dt.day_name().value_counts())
print(x['tick_volume'].describe())
lo = first[first['tick_volume'] <= 20]
print(lo[['time','tick_volume']].to_string())
