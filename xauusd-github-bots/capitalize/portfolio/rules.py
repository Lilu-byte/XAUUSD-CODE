"""Portfolio rules for a third trend EA next to GoldAllAgree + GoldAsiaBreak.
build(bot, dirn, gaa, regime) -> (d, shadow trades)   signal-level rules, run through gbt.simulate
apply_cut(trades, cut)        -> trades actually taken (subset of the shadow trades; the EA keeps
                                 running its virtual trades and copies one to a real order only if not paused)
gaa:    'none'  | 'skip'  = no new long while GoldAllAgree holds its long
        | 'skipclose' = skip + close our long at the first H1 close where GoldAllAgree holds a long (caps lots at 0.02)
        | 'only' = longs only while GoldAllAgree holds a long (confirmation; up to 0.03 lots)
regime: 'none' | 'sma200' (D1 close > 200-day SMA for longs, below for shorts) | 'mom252' (close vs 252 D1 bars ago)
cut:    'none' | 'm3' (pause rest of month after 3 losing real trades that month)
        | 'ec10' / 'ec20' (take a trade only if the last 10/20 virtual trades closed before it sum > 0)
        | 'd90' / 'd180' (only if virtual P&L closed in the last 90/180 calendar days > 0)"""
from common import *

_A = {}


def h1_atr():
    if 'a' not in _A:
        _A['a'] = atr(load('H1'), 14).values
    return _A['a']


def build(bot, dirn='both', gaa='none', regime='none', gaa_actual=True):
    d, sig, kw = candidate(bot)
    sig = np.asarray(sig, float).copy()
    kw = dict(kw)
    if dirn == 'long':
        sig[sig < 0] = 0
    lok, sok = d1_regime(d, regime)
    sig[(sig > 0) & ~lok] = 0
    sig[(sig < 0) & ~sok] = 0
    g = gaa_state(d, prefer_actual=gaa_actual) > 0.5
    if gaa in ('skip', 'skipclose'):
        sig[(sig > 0) & g] = 0
    if gaa == 'skipclose':
        xl = kw.get('exit_long'); xl = np.zeros(len(d), bool) if xl is None else np.asarray(xl, bool).copy()
        kw['exit_long'] = xl | g
    if gaa == 'only':
        sig[(sig > 0) & ~g] = 0
    t = simulate(d, sig, **kw)
    t['atr'] = h1_atr()[t.ei.astype(int) - 1]      # ATR on the signal bar
    t['R'] = t.pnl / t.atr
    return d, t, sig, kw


def apply_cut(t, cut):
    if cut == 'none' or len(t) == 0:
        return t.copy()
    take = np.zeros(len(t), bool)
    et = t.entry_time.values; xt = t.exit_time.values; pnl = t.pnl.values
    if cut == 'm3':
        mon = (t.entry_time.dt.year * 12 + t.entry_time.dt.month).values
        for i in range(len(t)):
            # losing REAL trades closed this month before this entry
            prior = take[:i] & (xt[:i] <= et[i]) & (mon[:i] == mon[i]) & (pnl[:i] < 0)
            take[i] = prior.sum() < 3
        return t[take].copy()
    if cut.startswith('ec'):
        n = int(cut[2:])
        for i in range(len(t)):
            closed = np.where(xt[:i] <= et[i])[0]
            if len(closed) < n:
                take[i] = True   # not enough history yet: trade
            else:
                take[i] = pnl[closed[-n:]].sum() > 0
        return t[take].copy()
    if cut.startswith('d'):
        days = np.timedelta64(int(cut[1:]), 'D')
        for i in range(len(t)):
            m = (xt[:i] <= et[i]) & (xt[:i] > et[i] - days)
            take[i] = (et[i] - et[0] < days) or pnl[:i][m].sum() > 0
        return t[take].copy()
    raise KeyError(cut)


BOTS = {'maxi': ['both', 'long'], 'donchian': ['both', 'long'], 'maker_tung': ['long']}
GAAS = ['none', 'skip', 'skipclose', 'only']
REGIMES = ['none', 'sma200', 'mom252']
CUTS = ['none', 'm3', 'ec10', 'ec20', 'd90', 'd180']


def variants():
    for b, dirs in BOTS.items():
        for dr in dirs:
            for g in GAAS:
                for r in REGIMES:
                    for c in CUTS:
                        yield b, dr, g, r, c
