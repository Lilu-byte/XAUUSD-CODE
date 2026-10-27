"""Versions of the family, written once in M15-version terms, and how each maps to a window.

A spec is a dict. Timeframe sets are given as GoldAllAgree's 'Use M5 = off' version uses them on
an M15 base (M15, M30, H1, H4). On another window they map like harness.pair_parts maps the EA:
- pair (M5 base):   M5 is added to every set (the EA's real version is M5 + M15, M30, H1, H4).
- h1_old (H1 base): only H1 and H4 exist; a set keeps its H1/H4 members (empty -> H1).
`drop` = how many of the set may disagree (need = size - drop, at least 1).
EMAs: 'emas' = (fast, slow) for every timeframe, or 'lo'/'hi' pairs for M5/M15/M30 and H1/H4.

kinds
  change/agree  : replace GoldAllAgree's rule with agree(tfs, need, emas)            (long)
  change/armed  : GoldAllAgree + re-entries on `fast` while `anchors` stay up       (long)
  change/cool   : GoldAllAgree with a cool-down of `minutes` after each exit         (long)
  short         : added stream, short while agree(tfs, need, emas, side=-1)
  sibling       : added stream from agree(tfs, need, emas, side) that may only ENTER while
                  GoldAllAgree is flat; mode 'hold' (exits on its own rule), 'handoff' (also exits
                  when GoldAllAgree enters) or 'free' (no flat condition at all)
"""
import sys
sys.dont_write_bytecode = True
import aa_more as A

T4 = ('M15', 'M30', 'H1', 'H4')
EMAS = [(5, 20), (8, 32), (10, 40), (12, 48), (15, 60), (20, 80)]


def map_tfs(tfs, window):
    base = A.base_tf(window)
    if base == 'M5': return ('M5',) + tuple(tfs)
    if base == 'M15': return tuple(tfs)
    k = tuple(t for t in tfs if t in ('H1', 'H4'))
    return k if k else ('H1',)


def map_emas(spec, tfs):
    if 'emas' in spec: return tuple(spec['emas'])
    return {t: tuple(spec['lo'] if t in ('M5', 'M15', 'M30') else spec['hi']) for t in tfs}


def rule(spec, window, side=1):
    base = A.base_tf(window)
    tfs = map_tfs(spec['tfs'], window)
    need = max(1, len(tfs) - spec.get('drop', 0))
    return A.agree(base, tfs, map_emas(spec, tfs), need, side)


def main_on(window):
    base = A.base_tf(window)
    return A.agree(base, A.WIN_TFS[window])


def build(spec, window, cost=None):
    """-> ('change', new GoldAllAgree trades) or ('added', the stream's trades)."""
    base = A.base_tf(window); k = spec['kind']
    if k == 'change/agree':
        return 'change', A.trades(base, rule(spec, window), cost=cost or 'bar')
    if k == 'change/armed':
        tfs = A.WIN_TFS[window]
        anchors = tuple(t for t in spec['anchors'])
        fast = map_tfs(spec['fast'], window)
        if base == 'H1': fast = tuple(t for t in fast if t in ('H1', 'H4')) or ('H1',)
        full = A.agree(base, tfs, (20, 80)); anc = A.agree(base, anchors, (20, 80))
        fst = A.agree(base, fast, tuple(spec.get('fast_emas') or (20, 80)))
        armed = A.np.zeros(len(full), bool); a = False
        for i in range(len(full)):
            a = bool(full[i]) or (a and bool(anc[i])); armed[i] = a
        return 'change', A.trades(base, full | (armed & fst), cost=cost or 'bar')
    if k == 'change/cool':
        n = -(-spec['minutes'] // A.MIN[base])
        return 'change', A.trades(base, A.cooldown(main_on(window), n), cost=cost or 'bar')
    if k == 'short':
        return 'added', A.trades(base, rule(spec, window, side=-1), side=-1, cost=cost or 'fixed')
    if k == 'sibling':
        side = spec.get('side', 1)
        on = A.sibling(main_on(window), rule(spec, window, side), spec['mode'])
        return 'added', A.trades(base, on, side=side, cost=cost or 'fixed')
    raise ValueError(k)


def name(spec):
    k = spec['kind']; s = k
    if 'tfs' in spec: s += ' ' + '+'.join(spec['tfs']) + (f" -{spec['drop']}" if spec.get('drop') else '')
    if 'emas' in spec: s += ' EMA%d/%d' % tuple(spec['emas'])
    if 'lo' in spec: s += ' lo%d/%d hi%d/%d' % (tuple(spec['lo']) + tuple(spec['hi']))
    if k == 'change/armed':
        s += ' anchors ' + '+'.join(spec['anchors']) + ' fast ' + '+'.join(spec['fast'])
        if spec.get('fast_emas'): s += ' fastEMA%d/%d' % tuple(spec['fast_emas'])
    if k == 'change/cool': s += f" {spec['minutes']}min"
    if k == 'sibling': s += f" side{spec.get('side', 1):+d} {spec['mode']}"
    return s


def grid():
    G = []
    # 1. changes to GoldAllAgree: EMA pairs x timeframe sets x how many may disagree
    sets = [(T4, (0, 1, 2)), (('M15', 'M30', 'H1'), (0, 1)), (('M15', 'H1', 'H4'), (0, 1)),
            (('M30', 'H1', 'H4'), (0, 1)), (('M15', 'M30', 'H4'), (0, 1)),
            (('M15', 'H1'), (0,)), (('M15', 'H4'), (0,)), (('M30', 'H4'), (0,)), (('M15', 'M30'), (0,)), (('H1', 'H4'), (0,))]
    for tfs, drops in sets:
        for d in drops:
            for e in EMAS:
                if tfs == T4 and d == 0 and e == (20, 80): continue      # that is the EA itself
                G.append(dict(kind='change/agree', tfs=tfs, drop=d, emas=e))
    #    faster EMAs on the fast timeframes only, or slower/faster on H1/H4
    for lo in ((5, 20), (10, 40), (15, 60)):
        for hi in ((20, 80), (10, 40), (30, 120), (50, 200)):
            if lo == hi: continue
            G.append(dict(kind='change/agree', tfs=T4, drop=0, lo=lo, hi=hi))
    #    re-entry on the fast timeframe(s) while the slow ones stay up since all agreed
    for anchors, fast in ((('H1', 'H4'), ('M15',)), (('H4',), ('M15',)), (('H4',), ('M15', 'M30')), (('H1', 'H4'), ('M30',))):
        for fe in (None, (10, 40), (5, 20)):
            G.append(dict(kind='change/armed', anchors=anchors, fast=fast, fast_emas=fe))
    #    cool-down after an exit
    for m in (60, 120, 240, 480):
        G.append(dict(kind='change/cool', minutes=m))
    # 2. short-side mirror as an added stream
    for tfs, d in ((T4, 0), (T4, 1), (('M15', 'M30', 'H1'), 0), (('M30', 'H1', 'H4'), 0), (('M15', 'H1', 'H4'), 0),
                   (('H1', 'H4'), 0), (('M15', 'H4'), 0)):
        for e in EMAS + [(30, 120)]:
            G.append(dict(kind='short', tfs=tfs, drop=d, emas=e))
    # 3. a faster sibling stream that may only enter while GoldAllAgree is flat
    for tfs, d in ((('M15', 'M30', 'H1'), 0), (('M15', 'M30'), 0), (('M15', 'H1'), 0), (T4, 1), (T4, 0)):
        for e in ((5, 20), (10, 40), (15, 60), (20, 80)):
            if tfs == T4 and d == 0 and e == (20, 80): continue
            for mode in ('hold', 'handoff', 'free'):
                G.append(dict(kind='sibling', tfs=tfs, drop=d, emas=e, side=1, mode=mode))
            if e != (20, 80):        # a 20/80 short rule can never overlap GoldAllAgree = family 2
                G.append(dict(kind='sibling', tfs=tfs, drop=d, emas=e, side=-1, mode='hold'))
    return G
