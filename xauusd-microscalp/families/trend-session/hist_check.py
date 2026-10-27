"""Out-of-period check on OLDER data (all before 2026-09-01, so still TRAIN by date; TEST untouched):
does the M5/M15/H1/H4 EMA20>EMA80 trend continue over the next 5-30 minutes, by server hour?
Uses M5 bars 2025-05-05..2026-06-25 (before the M1 file starts) and M1 train for comparison.
Entry at an M5 close, move of the M5 close k bars later, spread = recorded M5 spread + $0.05."""
import warnings; warnings.filterwarnings('ignore')
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *
from features import rsi

m5 = load('M5'); m15 = load('M15'); h1 = load('H1'); h4 = load('H4')
END = pd.Timestamp('2026-06-26')


def on(d_lo, lo_min, d_hi, tf, vals):
    """values on closed d_hi bars, as known at the close of each d_lo bar (open + lo_min)."""
    known = pd.Series(np.asarray(vals, float), index=d_hi.index + pd.Timedelta(minutes=MIN[tf]))
    known = known[~known.index.duplicated(keep='last')]
    at = d_lo.index + pd.Timedelta(minutes=lo_min)
    return known.reindex(known.index.union(at)).ffill().reindex(at).values


def tr(d): return np.sign(ema(d.close, 20) - ema(d.close, 80)).values

t_m5 = tr(m5)  # M5 bar's own EMA trend is known at its close
t15 = on(m5, 5, m15, 'M15', tr(m15)); t1 = on(m5, 5, h1, 'H1', tr(h1)); t4 = on(m5, 5, h4, 'H4', tr(h4))
agree = t_m5 + t15 + t1 + t4
d = np.where(agree == 4, 1, np.where(agree == -4, -1, 0))

if __name__ == '__main__':
    c = m5.close.values; spr = m5.spread.values * 0.01 + 0.05
    tod = m5.index.hour * 60 + m5.index.minute
    r14 = rsi(m5.close, 14).values
    sel = m5.index < END
    same_day = lambda k: np.r_[(m5.index[k:].normalize() == m5.index[:-k].normalize()), np.zeros(k, bool)]
    print('M5 history', m5.index[0].date(), '..', m5.index[sel][-1].date(), 'days', len(np.unique(m5.index[sel].date)))
    rows = []
    for k in (1, 2, 6):
        fwd = np.r_[c[k:] - c[:-k], np.full(k, np.nan)]
        fwd[~same_day(k)] = np.nan
        for name, ses in (('ny 15:30-18', (tod >= 930) & (tod < 1080)), ('lon 10-13', (tod >= 600) & (tod < 780)),
                          ('asia 3-9', (tod >= 180) & (tod < 540)), ('other', ~((tod >= 930) & (tod < 1080)))):
            for trig, tm in (('all', np.ones(len(c), bool)), ('rsi14 dip', np.where(d > 0, r14 < 45, r14 > 55))):
                mk = sel & ses & (d != 0) & tm & ~np.isnan(fwd)
                mv = fwd[mk] * d[mk]
                dd = m5.index[mk].normalize()
                g = pd.Series(mv - mv.mean()).groupby(dd).sum().values
                se = np.sqrt((g ** 2).sum()) / len(mv)
                # by half of the history
                h = m5.index[mk] < pd.Timestamp('2025-12-01')
                rows.append(dict(k_min=5 * k, sess=name, trig=trig, n_day=mk.sum() / len(np.unique(m5.index[sel].date)),
                                 move=mv.mean(), spr=spr[mk].mean(), net=mv.mean() - spr[mk].mean(), t_move=mv.mean() / se,
                                 net_h1=mv[h].mean() - spr[mk][h].mean(), net_h2=mv[~h].mean() - spr[mk][~h].mean(),
                                 long_mv=mv[d[mk] > 0].mean(), short_mv=mv[d[mk] < 0].mean()))
    pd.set_option('display.width', 250)
    print(pd.DataFrame(rows).round(3).to_string())

    # hourly profile of the trend move over 10 min (2 M5 bars)
    k = 2
    fwd = np.r_[c[k:] - c[:-k], np.full(k, np.nan)]; fwd[~same_day(k)] = np.nan
    mk = sel & (d != 0) & ~np.isnan(fwd)
    x = pd.DataFrame({'hr': m5.index.hour[mk], 'mv': fwd[mk] * d[mk], 'spr': spr[mk]})
    print('\nM5 history: trend-direction 10-min move by server hour (all bars in agreement)')
    print(x.groupby('hr').agg(n=('mv', 'size'), mv=('mv', 'mean'), spr=('spr', 'mean')).round(3).T.to_string())
