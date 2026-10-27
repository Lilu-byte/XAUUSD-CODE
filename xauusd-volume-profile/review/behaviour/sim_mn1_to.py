# Line 259: to = iTime(sB) + PeriodSeconds(_Period) - 1.  PeriodSeconds(PERIOD_MN1) is 30 days.
# Shows which days of the last month the profile covers on an MN1 chart.
from datetime import datetime, timedelta
for y, m in [(2026, 1), (2026, 2), (2026, 4), (2026, 7), (2028, 2)]:
    start = datetime(y, m, 1)
    to = start + timedelta(seconds=30 * 86400 - 1)
    nxt = datetime(y + (m == 12), m % 12 + 1, 1)
    real_end = nxt - timedelta(seconds=1)
    diff = (to - real_end).total_seconds() / 86400
    print(f"{start:%Y-%m} candle: profile ends {to:%Y-%m-%d %H:%M:%S}, candle really ends {real_end:%Y-%m-%d %H:%M:%S}"
          f" -> {'misses' if diff < 0 else 'adds'} {abs(diff):.0f} day(s)")
