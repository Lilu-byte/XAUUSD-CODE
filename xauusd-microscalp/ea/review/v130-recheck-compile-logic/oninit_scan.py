"""Port of EA OnInit session checks (GoldMicroScalp.mq5:427-446) for a few input sets."""
def parse(s):
    p = s.split(':')
    return -1 if len(p) != 2 else int(p[0]) * 60 + int(p[1])
def oninit(first, last, sf, st, on=True, close='22:58'):
    f, l, c, a, b = parse(first), parse(last), parse(close), parse(sf), parse(st)
    if min(f, l, c, a, b) < 0 or a > 1440 or b > 1440: return 'refuse: times'
    if a == 1440: a = 0
    if on and a == b: return 'refuse: same'
    ins = (lambda t: True) if not on else ((lambda t: a <= t < b) if a <= b else (lambda t: t >= a or t < b))
    mins = [t for t in range(1440) if f <= t <= l and ins(t)]
    if not mins: return 'refuse: no overlap'
    ent = [t for t in mins if (t + 1) % 1440 < c]            # entry minute (bar close) before the close-all time, EA:822
    return f'ok: {len(mins)} signal minutes {mins[0]//60:02d}:{mins[0]%60:02d}-{mins[-1]//60:02d}:{mins[-1]%60:02d}, {len(ent)} can still enter before close-all'
for args in [('01:05', '22:29', '15:00', '19:00'), ('01:05', '22:29', '22:30', '23:30'), ('01:05', '22:29', '24:00', '00:00'),
             ('01:05', '22:29', '24:00', '24:00'), ('01:05', '22:29', '00:00', '24:00'), ('01:05', '22:29', '23:00', '02:00'),
             ('22:00', '02:00', '15:00', '19:00', False), ('01:05', '22:29', '15:00', '19:00', True, '14:00')]:
    print(args, '->', oninit(*args))
