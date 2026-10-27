# Simulates GoldAllAgree FlatSince ranges vs the bars real M5 checks read.
# Calendar: Mon-Fri, ticks 01:00-22:59 server time (daily break 23:00-01:00, weekend).
import datetime as dt, sys
C = 300
TFS = {'M5':300,'M15':900,'M30':1800,'H1':3600,'H4':14400}
start = dt.datetime(2026,9,7)   # a Monday
def ts(d): return int((d - dt.datetime(1970,1,1)).total_seconds())
m5 = []
for day in range(14):
    d = start + dt.timedelta(days=day)
    if d.weekday() >= 5: continue
    t0 = ts(d) + 3600
    for k in range((23-1)*12): m5.append(t0 + k*300)
m5set = set(m5)
tfbars = {n: sorted({b - b % P for b in m5}) for n, P in TFS.items()}
import bisect
def shift1_at_check(n, B):
    P = TFS[n]; bars = tfbars[n]
    i = bisect.bisect_left(bars, B - B % P)   # index of bar 0 (open == floor(B,P))
    return bars[i-1] if i > 0 else None
def last_closed_now(n, N):
    P = TFS[n]; bars = tfbars[n]
    i = bisect.bisect_right(bars, N) - 1      # bar 0 now
    return bars[i-1]
def truth(n, t, N):
    s = set()
    for B in m5:
        if t < B <= N:
            x = shift1_at_check(n, B)
            if x is not None: s.add(x)
    return s
def code_range(n, t, N, fixed):
    P = TFS[n]; bars = tfbars[n]
    if not fixed:
        tc = t - t % C + C
        frm = tc - tc % P - P
    else:
        i = bisect.bisect_right(m5, t) - 1     # check bar containing t
        if i + 1 >= len(m5) or m5[i+1] > N: return set()
        tc = m5[i+1]
        j = bisect.bisect_right(bars, tc - tc % P - 1) - 1
        frm = bars[j]
    to = last_closed_now(n, N)
    if to < frm: return set()
    return {b for b in bars if frm <= b <= to}
bad = {False:{}, True:{}}
import random
random.seed(1)
cases = []
# closes at chosen times: just after daily open, Monday open, just before break, Friday close, mid-session
for B in m5[300:-300]:
    for off in (0, 2, 150):
        cases.append(B + off)
for t in cases:
    for lag in (60, 400, 1000, 4000, 20000, 90000, 200000):
        N = t + lag
        k = bisect.bisect_right(m5, N) - 1
        N = m5[k] + 1    # 'now' = just after the latest check bar's first tick
        if N <= t: continue
        for n in TFS:
            T = truth(n, t, N); 
            for fx in (False, True):
                R = code_range(n, t, N, fx)
                miss = T - R; extra = R - T
                # extra bars that are the current shift-1 are harmless (current signal reads them)
                extra = {e for e in extra if e != last_closed_now(n, N)}
                miss = {e for e in miss if e != last_closed_now(n, N)}
                if miss or extra:
                    key = (n, 'miss' if miss else 'extra', dt.datetime.utcfromtimestamp(t).strftime('%a %H:%M'))
                    bad[fx][key] = bad[fx].get(key, 0) + 1
for fx in (False, True):
    print('FIXED' if fx else 'CURRENT', 'mismatching (tf, kind, close time) ->', len(bad[fx]))
    for k in sorted(bad[fx])[:40]: print('  ', k, bad[fx][k])
