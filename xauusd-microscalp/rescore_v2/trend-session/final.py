"""Final picks, locked from TRAIN (refine_train.csv plateau with both train months positive).
This script is the single look at TEST. Prints TRAIN and TEST under FAIR/base, TEST under OHLC/base,
FAIR/bar, FAIR/wide, random direction on the same bars (20 seeds), and TEST edge() moves."""
import warnings; warnings.filterwarnings('ignore')
import json
from sigs import *

PICKS = {
    'P1 NY trend, every bar': dict(sig=('T4', 'all', 'ny', 'any'), tp=1.0, sl=20, timeout=30, max_open=10, day_loss=0),
    'P2 NY trend, M1 pullback below EMA20': dict(sig=('T4', 'below1', 'ny', 'any'), tp=1.0, sl=20, timeout=30, max_open=10, day_loss=0),
    'P3 Nyao score + RSI7 dip, 09-22h, low spread': dict(sig=('NY5x', 'rsi7_30', 'day', 'lo'), tp=1.0, sl=20, timeout=30, max_open=10, day_loss=30),
}
H = Harness()


def run(sig, p, fill='FAIR', spread='base'):
    return H.run(sig, p['tp'], p['sl'], timeout=p['timeout'], max_open=p['max_open'], fill=fill, spread=spread,
                 day_loss=p['day_loss'])


def max_concurrent(trades):
    ev = pd.concat([pd.Series(1, index=trades.entry), pd.Series(-1, index=trades.entry + pd.to_timedelta(trades.bars, 'min'))]).sort_index(kind='stable')
    return int(ev.cumsum().max())


if __name__ == '__main__':
    out = {}
    for name, p in PICKS.items():
        sig = make(*p['sig'])
        r = {}
        d, t = run(sig, p)
        r['train'] = summarize(d, t, 'train'); r['test'] = summarize(d, t, 'test')
        te = t[t.entry >= SPLIT]
        r['test_max_concurrent'] = max_concurrent(te)
        r['test_avg_bars'] = te.bars.mean()
        dt = d[d.index >= SPLIT].pnl
        r['test_top3_days_share'] = dt.nlargest(3).sum() / dt.sum() if dt.sum() != 0 else np.nan
        r['test_by_week'] = dt.groupby(pd.Grouper(freq='W')).sum().round(1).tolist()
        r['test_long_short_pnl'] = te.groupby('dir').pnl.agg(['size', 'sum']).round(1).to_dict()
        for fill, spr in (('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide'), ('STOP', 'base')):
            dd, tt = run(sig, p, fill, spr)
            r[f'test_{fill}_{spr}'] = summarize(dd, tt, 'test')['per_day']
        rnd_tr, rnd_te = [], []
        for k in range(20):
            dd, tt = run(random_like(sig, k), p)
            rnd_tr.append(summarize(dd, tt, 'train')['per_day']); rnd_te.append(summarize(dd, tt, 'test')['per_day'])
        r['train_random_per_day'] = np.mean(rnd_tr); r['test_random_per_day'] = np.mean(rnd_te)
        r['test_random_sd'] = np.std(rnd_te)
        e = edge(H.m1, sig, horizons=(1, 2, 3, 5, 10, 20, 30))
        r['edge'] = e.round(3).to_dict(orient='index')
        out[name] = r

    pd.set_option('display.width', 250)
    for name, r in out.items():
        print(f'\n######## {name}')
        for per in ('train', 'test'):
            print(per, {k: round(v, 3) if isinstance(v, float) else v for k, v in r[per].items()})
        for k, v in r.items():
            if k not in ('train', 'test', 'edge'):
                print(k, round(v, 3) if isinstance(v, float) else v)
        print(pd.DataFrame(r['edge']).T[['signals_day', 'avg_spread', 'move_1m', 'move_5m', 'move_10m', 'move_20m', 'move_30m', 'hit_10m']].to_string())
    json.dump(out, open('final_results.json', 'w'), default=float, indent=1)
