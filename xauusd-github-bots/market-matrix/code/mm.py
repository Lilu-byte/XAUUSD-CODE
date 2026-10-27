"""Python port of the calculations in "Market Matrix (Zeiierman)" (Pine Script v6, CC BY-NC-SA 4.0).

Only the numbers are ported, not the drawing. Defaults are the script's own inputs. Each function takes
an OHLCV DataFrame (gbt.load) for the panel timeframe and returns series aligned to its bars, computed on
CLOSED bars only (value at bar i uses bars <= i). Pine details kept:
  ta.rsi / ta.atr use RMA; ta.macd's signal is an EMA; ta.stdev is the population stdev;
  ta.percentile_nearest_rank(src, n, p) = sorted window value at rank ceil(p/100*n).
Known approximations: Pine seeds EMA/RMA with an SMA (pandas seeds with the first value; differences vanish
after warm-up); the Range Oscillator's ATR(2000) is computed on all history instead of TradingView's
2,700-bar request window.
"""
import numpy as np, pandas as pd
from numba import njit

# script defaults
RSI_LEN, RSI_MA = 14, 9
MACD_F, MACD_S, MACD_SIG = 12, 26, 9
RTI_LEN, RTI_SENS, RTI_SIG = 100, 95, 20
ASI_LB, ASI_TOP, ASI_BOT, ASI_MA = 15, 0.15, 0.15, 14
RNG_LEN, RNG_MULT = 50, 2.0
SW_LEN, VW_APT = 50, 20.0
EMA_LEN = 89


def ema(x, n): return x.ewm(span=n, adjust=False).mean()
def rma(x, n): return x.ewm(alpha=1 / n, adjust=False).mean()


def tr(d):
    pc = d.close.shift()
    return pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)


def pine_atr(d, n):
    """ta.atr: RMA of true range, seeded with the SMA of the first n values (na before that)."""
    t = tr(d).values
    out = np.full(len(t), np.nan)
    if len(t) > n:
        out[n] = np.nanmean(t[1:n + 1])
        a = 1 / n
        for i in range(n + 1, len(t)):
            out[i] = a * t[i] + (1 - a) * out[i - 1]
    return pd.Series(out, index=d.index)


def rsi(c, n=RSI_LEN):
    dd = c.diff()
    return 100 - 100 / (1 + rma(dd.clip(lower=0), n) / rma((-dd).clip(lower=0), n))


def macd(c, f=MACD_F, s=MACD_S, sig=MACD_SIG):
    m = ema(c, f) - ema(c, s)
    sg = ema(m, sig)
    return m, sg, m - sg


def _nearest_rank(x, n, pct):
    """ta.percentile_nearest_rank over the last n values including the current one."""
    v = x.values
    out = np.full(len(v), np.nan)
    if len(v) < n:
        return pd.Series(out, index=x.index)
    w = np.lib.stride_tricks.sliding_window_view(v, n)
    rank = int(np.ceil(pct / 100.0 * n))
    out[n - 1:] = np.sort(w, axis=1)[:, rank - 1]
    return pd.Series(out, index=x.index)


def rti(d, length=RTI_LEN, sens=RTI_SENS, sig=RTI_SIG):
    """Relative Trend Index: where the close sits between a trimmed 100-bar high (95th percentile of close+stdev2)
    and low (5th percentile of close-stdev2), scaled 0-100. In effect a 100-bar stochastic with outliers cut."""
    c = d.close
    dev = c.rolling(2).std(ddof=0)
    up, lo = c + dev, c - dev
    ur = max(1, min(length, int(round(sens / 100 * length))))
    lr = max(1, min(length, int(round((100 - sens) / 100 * length))))
    hi = _nearest_rank(up, length, (ur - 0.5) * 100 / length)
    lw = _nearest_rank(lo, length, (lr - 0.5) * 100 / length)
    ok = up.shift(length - 1).notna() & lo.shift(length - 1).notna() & (hi != lw)
    r = (100 * (c - lw) / (hi - lw)).where(ok)
    return r, ema(r.dropna(), sig).reindex(r.index)


def asi(d, lb=ASI_LB, top=ASI_TOP, bot=ASI_BOT, ma=ASI_MA):
    """Absolute Strength Index: the lb-bar return placed between the 85th and 15th percentile of the previous lb
    ONE-bar returns, mapped so that loser -> -1 and winner -> +1. Because a 15-bar return is compared with
    1-bar returns, it is roughly (15-bar return) / (1-bar volatility): a momentum z-score, typically -8..+8."""
    c = d.close.values
    n = len(c)
    r1 = np.full(n, np.nan); r1[1:] = c[1:] / c[:-1] - 1
    val = np.zeros(n)
    for t in range(n):
        prev = [r1[t - k] for k in range(1, lb + 1) if t - k >= 1 and not np.isnan(r1[t - k])]
        if not prev:
            continue
        prev.sort()
        cnt = len(prev)
        wi = min(cnt - 1, max(0, int(np.ceil(cnt * (1 - top))) - 1))
        li = min(cnt - 1, max(0, int(np.ceil(cnt * bot)) - 1))
        win, los = prev[wi], prev[li]
        cur = c[t] / c[t - lb] - 1 if t - lb >= 0 else np.nan
        val[t] = (cur - los) / (win - los) * 2 - 1 if not np.isnan(cur) and win != los else 0.0
    v = pd.Series(val, index=d.index)
    return v, v.rolling(ma).mean()


def range_osc(d, length=RNG_LEN, mult=RNG_MULT):
    """Range Oscillator: distance of the close from a 50-bar average in which each bar is weighted by the size of
    its own move, in units of 2 x ATR(2000) (ATR(200) until 2000 bars exist). +/-100 = close 2 long-run ATRs away."""
    c = d.close
    w = (c - c.shift()).abs() / c.shift()
    wp = (c * w).rolling(length).sum(); wt = w.rolling(length).sum()
    mean = (wp / wt).where(wt != 0)
    a = pine_atr(d, 2000).fillna(pine_atr(d, 200)) * mult
    osc = 100 * (c - mean) / a
    return osc, mean, a


@njit(cache=True)
def _swing(h, l, c, v, sw, apt):
    """Swing anchored VWAP exactly as swing_vwap() in the script, run bar by bar.
    Returns the value as it was at each bar's close (live), the final redrawn array (what the panel shows
    afterwards), the live direction, the redrawn direction, and the anchors (anchor bar, confirm bar, price, kind)."""
    n = len(c)
    final = np.full(n, np.nan); live = np.full(n, np.nan)
    dfin = np.zeros(n, np.int64); dlive = np.zeros(n, np.int64)
    anc = np.zeros((n, 4))
    na_ = 0
    ph = np.nan; pl = np.nan; phi = -1; pli = -1; last = 0
    wp = np.nan; wv = np.nan
    alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, apt))
    for j in range(n):
        nh = True; nl = True
        for k in range(max(0, j - sw + 1), j + 1):
            if h[k] > h[j]:
                nh = False
            if l[k] < l[j]:
                nl = False
        if nh:
            ph = h[j]; phi = j
        if nl:
            pl = l[j]; pli = j
        direction = 1 if phi > pli else -1
        if last != 0 and direction != last:
            ai = pli if direction > 0 else phi
            ap = pl if direction > 0 else ph
            if ai >= 0:
                anc[na_, 0] = ai; anc[na_, 1] = j; anc[na_, 2] = ap; anc[na_, 3] = -1 if direction > 0 else 1
                na_ += 1
                wp = ap * v[ai]; wv = v[ai]
                for k in range(ai, j + 1):
                    hc3 = (h[k] + l[k] + c[k]) / 3.0
                    wp = (1 - alpha) * wp + alpha * hc3 * v[k]
                    wv = (1 - alpha) * wv + alpha * v[k]
                    final[k] = wp / wv if wv > 0 else np.nan
                    dfin[k] = direction
        else:
            hc3 = (h[j] + l[j] + c[j]) / 3.0
            if np.isnan(wp):
                wp = hc3 * v[j]; wv = v[j]
            wp = (1 - alpha) * wp + alpha * hc3 * v[j]
            wv = (1 - alpha) * wv + alpha * v[j]
            final[j] = wp / wv if wv > 0 else np.nan
            dfin[j] = direction
        live[j] = final[j]; dlive[j] = direction
        last = direction
    return live, final, dlive, dfin, anc[:na_]


def swing_vwap(d, sw=SW_LEN, apt=VW_APT):
    live, final, dl, df, anc = _swing(d.high.values, d.low.values, d.close.values, d.vol.values.astype(float), sw, apt)
    ix = d.index
    a = pd.DataFrame(anc, columns=['anchor_i', 'confirm_i', 'price', 'kind'])
    a[['anchor_i', 'confirm_i', 'kind']] = a[['anchor_i', 'confirm_i', 'kind']].astype(int)
    a['anchor_time'] = ix[a.anchor_i]; a['confirm_time'] = ix[a.confirm_i]
    a['confirm_close'] = d.close.values[a.confirm_i]
    return (pd.Series(live, ix), pd.Series(final, ix), pd.Series(dl, ix), pd.Series(df, ix), a)


def all_panels(d):
    """Every series the six panels and the main chart show, on closed bars of d."""
    c = d.close
    out = pd.DataFrame(index=d.index)
    out['close'] = c
    out['sma20'], out['sma50'], out['sma200'] = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    out['ema89'] = ema(c, EMA_LEN)
    out['rsi'] = rsi(c); out['rsi_ma'] = out.rsi.rolling(RSI_MA).mean()
    out['macd'], out['macd_sig'], out['macd_hist'] = macd(c)
    out['rti'], out['rti_sig'] = rti(d)
    out['asi'], out['asi_sig'] = asi(d)
    out['rng'], out['rng_mean'], out['rng_atr'] = range_osc(d)
    vl, vf, dl, dfin, anc = swing_vwap(d)
    out['vwap_live'], out['vwap_redrawn'], out['vw_dir_live'], out['vw_dir_redrawn'] = vl, vf, dl, dfin
    return out, anc
