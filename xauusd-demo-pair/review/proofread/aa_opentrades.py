import pandas as pd, sys
t = pd.read_csv(sys.argv[1])
print(t.columns.tolist())
for c in t.columns:
    if 'time' in c.lower() or 'entry' in c.lower() or 'exit' in c.lower():
        try:
            s = pd.to_datetime(t[c])
            print(c, s.dt.strftime('%H:%M').isin(['01:00','01:05','01:10','00:00','23:55','22:55']).sum(), 'of', len(s), 'near session open/close')
            print(s.dt.strftime('%H:%M').value_counts().head(6).to_dict())
        except Exception as e:
            pass
