"""Independent re-implementation (written from the Pine source, not from mm.py) used to test the claims.
Usage: python3 -I indep.py   (writes indep_results.json next to this file)
"""
import json, sys, zipfile
import numpy as np, pandas as pd

OUT = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-claims/'
F = {'D1': '/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv',
     'H4': '/mnt/project-files/xauusd-price-action/data/XAUUSD_H4.csv',
     'H1': '/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv'}


def load(tf):
    d = pd.read_csv(F[tf])
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    return d[['open', 'high', 'low', 'close', 'tick_volume']].rename(columns={'tick_volume': 'vol'}).astype(float)


def truerange(h, l, c):
    tr = np.empty(len(c)); tr[0] = h[0] - l[0]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])
    return tr


def pine_rma(x, n):
    """ta.rma: na until n values, seeded with their SMA, then alpha=1/n."""
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1] = np.mean(x[:n])
        for i in range(n, len(x)):
            out[i] = (x[i] + (n - 1) * out[i - 1]) / n
    return out


def pine_ema(x, n):
    a = 2.0 / (n + 1); out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1] = np.mean(x[:n])
        for i in range(n, len(x)):
            out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


# ---------------- swing VWAP, line by line from Pine 517-598 ----------------
def swing_pine(H, L, C, V, swLen=50, apt=20.0):
    n = len(C)
    value = [np.nan] * n; dirAt = [0] * n
    anchors = []
    ph = np.nan; pl = np.nan; phI = -1; plI = -1; last = 0; wp = np.nan; wv = np.nan
    alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, round(max(5.0, min(300.0, apt)))))
    live_dir = np.zeros(n, int); live_val = np.full(n, np.nan)
    for j in range(n):
        hj, lj, cj, vj = H[j], L[j], C[j], V[j]
        nh = True; nl = True
        for k in range(max(0, j - swLen + 1), j + 1):
            if H[k] > hj: nh = False
            if L[k] < lj: nl = False
        if nh: ph = hj; phI = j
        if nl: pl = lj; plI = j
        direction = 1 if phI > plI else -1
        if last != 0 and direction != last:
            ai = plI if direction > 0 else phI
            ap = pl if direction > 0 else ph
            anchors.append((ai, j, ap, -1 if direction > 0 else 1))
            wp = ap * V[ai]; wv = V[ai]
            for k in range(ai, j + 1):
                hc3 = (H[k] + L[k] + C[k]) / 3.0
                wp = (1 - alpha) * wp + alpha * hc3 * V[k]
                wv = (1 - alpha) * wv + alpha * V[k]
                value[k] = wp / wv if wv > 0 else np.nan
                dirAt[k] = direction
        else:
            hc3 = (hj + lj + cj) / 3.0
            if np.isnan(wp):
                wp = hc3 * vj; wv = vj
            wp = (1 - alpha) * wp + alpha * hc3 * vj
            wv = (1 - alpha) * wv + alpha * vj
            value[j] = wp / wv if wv > 0 else np.nan
            dirAt[j] = direction
        live_dir[j] = direction; live_val[j] = value[j]
        last = direction
    return np.array(value), np.array(dirAt), live_val, live_dir, anchors


def asi_pine(C, lb=15, top=0.15, bot=0.15):
    n = len(C); val = np.zeros(n)
    for t in range(n):
        prev = [C[t - k] / C[t - k - 1] - 1 for k in range(1, lb + 1) if t - k - 1 >= 0]
        if not prev: continue
        prev.sort(); cnt = len(prev)
        wi = max(0, min(cnt - 1, int(np.ceil(cnt * (1 - top))) - 1))
        li = max(0, min(cnt - 1, int(np.ceil(cnt * bot)) - 1))
        w, l = prev[wi], prev[li]
        cur = C[t] / C[t - lb] - 1 if t - lb >= 0 else np.nan
        val[t] = (cur - l) / (w - l) * 2 - 1 if (not np.isnan(cur) and w != l) else 0.0
    return val


def rti_pine(C, length=100, sens=95):
    c = pd.Series(C)
    dev = c.rolling(2).std(ddof=0)
    up = (c + dev).values; lo = (c - dev).values
    ur = max(1, min(length, int(round(sens / 100 * length))))
    lr = max(1, min(length, int(round((100 - sens) / 100 * length))))
    rk_u = int(np.ceil((ur - 0.5) * 100 / length / 100 * length)); rk_l = int(np.ceil((lr - 0.5) * 100 / length / 100 * length))
    out = np.full(len(C), np.nan)
    for t in range(length, len(C)):
        wu = np.sort(up[t - length + 1:t + 1]); wl = np.sort(lo[t - length + 1:t + 1])
        hi, lw = wu[rk_u - 1], wl[rk_l - 1]
        if hi != lw: out[t] = 100 * (C[t] - lw) / (hi - lw)
    return out, rk_u, rk_l


def range_osc(C, atr2):
    c = pd.Series(C)
    w = (c - c.shift()).abs() / c.shift()
    mean = ((c * w).rolling(50).sum() / w.rolling(50).sum()).values
    return 100 * (C - mean) / atr2, mean


res = {}
d1 = load('D1'); H, L, C, V = (d1[k].values for k in ('high', 'low', 'close', 'vol'))
ix = d1.index
res['d1_last'] = dict(date=str(ix[-1].date()), close=float(C[-1]), n_bars=len(C))

# ---------- claim 3/4: swing VWAP ----------
val, dirF, lval, ldir, anc = swing_pine(H, L, C, V)
A = pd.DataFrame(anc, columns=['ai', 'ci', 'price', 'kind'])
A['anchor'] = ix[A.ai].date; A['confirm'] = ix[A.ci].date; A['conf_close'] = C[A.ci]
A['delay'] = A.ci - A.ai
A['move_pct'] = np.where(A.kind == 1, (A.price - A.conf_close) / A.price, (A.conf_close - A.price) / A.price) * 100
# is the anchor the true extreme between the previous anchor and the confirmation bar?
true_ext = []
for i, r in A.iterrows():
    s = A.ai[i - 1] if i > 0 else 0
    seg_h, seg_l = H[s:r.ci + 1], L[s:r.ci + 1]
    true_ext.append(bool(np.isclose(r.price, seg_h.max())) if r.kind == 1 else bool(np.isclose(r.price, seg_l.min())))
A['is_true_extreme'] = true_ext
A.to_csv(OUT + 'anchors_indep_D1.csv', index=False)
m = pd.read_csv('/mnt/project-files/xauusd-github-bots/market-matrix/swing_anchors_D1.csv')
recol = ldir != dirF
res['swing'] = dict(n=len(A), median_delay=float(A.delay.median()), mean_delay=round(float(A.delay.mean()), 1),
                    median_move_pct=round(float(A.move_pct.median()), 2),
                    pct_days_recoloured_all=round(100 * recol.mean(), 1),
                    pct_days_recoloured_from_2005_04=round(100 * recol[ix >= '2005-04-01'].mean(), 1),
                    anchors_not_true_extreme=int((~A.is_true_extreme).sum()),
                    matches_main_csv=bool(len(m) == len(A) and np.allclose(m.price.values, A.price.values) and (m.anchor_i.values == A.ai.values).all()),
                    labelled_turns=int(len(A) - 2),
                    jan2026=A[A.anchor.astype(str) == '2026-01-29'].astype(str).to_dict('records'),
                    last3=A.tail(3).astype(str).to_dict('records'))
# is 29 Jan 2026 the highest high of the swing?
seg = d1.loc['2023-10-06':'2026-03-23']
res['swing']['max_high_2023_10_06_to_2026_03_23'] = [str(seg.high.idxmax().date()), float(seg.high.max())]
res['swing']['close_2026_03_23'] = float(d1.close.loc['2026-03-23'])
# half-life check
alpha = 1.0 - np.exp(-np.log(2.0) / 20)
res['vwap_half_life_bars'] = round(float(np.log(0.5) / np.log(1 - alpha)), 3)
res['vwap_zero_volume'] = 'with volume 0 every value is na (Pine 577/595: weightedVolume > 0 ? ... : na)'

# ---------- claim 5: Range Oscillator ----------
tr = truerange(H, L, C)
atr14 = pine_rma(tr, 14)
atr2000_full = pine_rma(tr, 2000); atr200_full = pine_rma(tr, 200)
a_full = np.where(np.isnan(atr2000_full), atr200_full, atr2000_full) * 2
osc_full, mean = range_osc(C, a_full)
# TradingView: calc_bars_count = 2700 -> the request context only sees the last 2700 D1 bars
W0 = len(C) - 2700
trw = truerange(H[W0:], L[W0:], C[W0:])
a2000w = pine_rma(trw, 2000); a200w = pine_rma(trw, 200)
a_w = np.full(len(C), np.nan); a_w[W0:] = np.where(np.isnan(a2000w), a200w, a2000w) * 2
osc_w = 100 * (C - mean) / a_w
y26 = ix.year == 2026
# "as of each day" variant: window of 2700 bars ending on that day
osc_asof = []
for t in np.where(y26)[0]:
    s = t - 2699
    trx = truerange(H[s:t + 1], L[s:t + 1], C[s:t + 1])
    ax = pine_rma(trx, 2000)[-1] * 2
    osc_asof.append(100 * (C[t] - mean[t]) / ax)
osc_asof = np.array(osc_asof)
res['range'] = dict(window_start=str(ix[W0].date()),
                    beyond100_2026_fullhistory_pct=round(100 * float((np.abs(osc_full[y26]) > 100).mean()), 1),
                    beyond100_2026_tvwindow_pct=round(100 * float((np.abs(osc_w[y26]) > 100).mean()), 1),
                    beyond100_2026_asof_each_day_pct=round(100 * float((np.abs(osc_asof) > 100).mean()), 1),
                    atr14_last=round(float(atr14[-1]), 2), atr2000_full_last=round(float(a_full[-1] / 2), 2),
                    atr2000_tvwindow_last=round(float(a_w[-1] / 2), 2),
                    ratio_full=round(float(atr14[-1] / (a_full[-1] / 2)), 2), ratio_tv=round(float(atr14[-1] / (a_w[-1] / 2)), 2),
                    osc_last_full=round(float(osc_full[-1]), 1), osc_last_tv=round(float(osc_w[-1]), 1),
                    atr2000_bars_in_years=round(2000 / (len(C) / ((ix[-1] - ix[0]).days / 365.25)), 1),
                    median_atr14_over_atr2000_2026_tv=round(float(np.median(atr14[y26] / (a_w[y26] / 2))), 2),
                    beyond100_by_year_tv={int(y): round(100 * float((np.abs(osc_w[ix.year == y]) > 100).mean()), 0) for y in range(2024, 2027)})

# ---------- claim 6: ASI and RTI ----------
asi = asi_pine(C)
r1 = pd.Series(C).pct_change()
R15 = pd.Series(C) / pd.Series(C).shift(15) - 1
sd15 = r1.shift(1).rolling(15).std(ddof=0)
x = (R15 / sd15).values
ok = ~np.isnan(x) & (np.arange(len(C)) > 300)
b = np.polyfit(x[ok], asi[ok], 1)
z15 = (R15 / (sd15 * np.sqrt(15))).values
c_ = pd.Series(C)
mom = R15.values
ok2 = ok & ~np.isnan(mom)
res['asi'] = dict(corr_with_R15_over_sd1=round(float(np.corrcoef(x[ok], asi[ok])[0, 1]), 3),
                  slope=round(float(b[0]), 3), intercept=round(float(b[1]), 3),
                  corr_with_raw_R15=round(float(np.corrcoef(mom[ok2], asi[ok2])[0, 1]), 3),
                  spearman_with_R15_over_sd1=round(float(pd.Series(x[ok]).rank().corr(pd.Series(asi[ok]).rank())), 3),
                  asi_8_in_true_15bar_z=round(8 / np.sqrt(15), 2),
                  pct_abs_asi_gt8=round(100 * float((np.abs(asi[ok]) > 8).mean()), 1),
                  win_rank='3rd largest of 15 (index 12)', lose_rank='3rd smallest of 15 (index 2)')
rti, rku, rkl = rti_pine(C)
cs = pd.Series(C)
q95 = cs.rolling(100).quantile(0.95, interpolation='nearest'); q05 = cs.rolling(100).quantile(0.05, interpolation='nearest')
st_pct = (100 * (cs - q05) / (q95 - q05)).values
st_raw = (100 * (cs - cs.rolling(100).min()) / (cs.rolling(100).max() - cs.rolling(100).min())).values
st_hl = (100 * (cs - d1.low.reset_index(drop=True).rolling(100).min()) / (d1.high.reset_index(drop=True).rolling(100).max() - d1.low.reset_index(drop=True).rolling(100).min())).values
okr = ~np.isnan(rti) & ~np.isnan(st_pct)
res['rti'] = dict(rank_upper=rku, rank_lower=rkl,
                  corr_with_close_stoch_5_95pct=round(float(np.corrcoef(rti[okr], st_pct[okr])[0, 1]), 4),
                  mean_abs_diff_pts=round(float(np.mean(np.abs(rti[okr] - st_pct[okr]))), 2),
                  corr_with_close_minmax_stoch=round(float(np.corrcoef(rti[okr], st_raw[okr])[0, 1]), 4),
                  corr_with_highlow_stoch100=round(float(np.corrcoef(rti[okr], st_hl[okr])[0, 1]), 4),
                  pct_outside_0_100=round(100 * float(((rti[okr] < 0) | (rti[okr] > 100)).mean()), 1))

# ---------- claim 7: vote correlation, alternatives ----------
sma = lambda n: cs.rolling(n).mean().values
s20, s50, s200 = sma(20), sma(50), sma(200)
dd = cs.diff()
up_ = pd.Series(np.clip(dd.values, 0, None)); dn_ = pd.Series(np.clip(-dd.values, 0, None))
rsi = 100 - 100 / (1 + pine_rma(np.nan_to_num(up_.values), 14) / pine_rma(np.nan_to_num(dn_.values), 14))
rsi_ma = pd.Series(rsi).rolling(9).mean().values
ema12, ema26 = pine_ema(C, 12), pine_ema(C, 26)
macd = ema12 - ema26
sig = np.full(len(C), np.nan); okm = ~np.isnan(macd); sig[okm] = pine_ema(macd[okm], 9)
hist = macd - sig
rti_sig = np.full(len(C), np.nan); okt = ~np.isnan(rti); rti_sig[okt] = pine_ema(rti[okt], 20)
asi_sig = pd.Series(asi).rolling(14).mean().values
sg = lambda v: np.sign(np.nan_to_num(v))
base = pd.DataFrame({'MA 20/50': np.where((C > s20) & (s20 > s50), 1, np.where((C < s20) & (s20 < s50), -1, 0)),
                     'Swing VWAP': ldir, 'RSI': sg(rsi - 50), 'MACD hist': sg(hist), 'RTI': sg(rti - 50),
                     'ASI': sg(asi), 'Range Osc': sg(osc_full)}, index=ix).loc['2005-04':]


def meancorr(df):
    cm = df.corr().values; return round(float(cm[np.triu_indices(df.shape[1], 1)].mean()), 3)


alt1 = base.copy(); alt1['MACD hist'] = sg(macd)[ix >= '2005-04']; alt1 = alt1.rename(columns={'MACD hist': 'MACD line'})
alt2 = base.copy(); alt2['RSI'] = sg(rsi - rsi_ma)[ix >= '2005-04']; alt2['RTI'] = sg(rti - rti_sig)[ix >= '2005-04']; alt2['ASI'] = sg(asi - asi_sig)[ix >= '2005-04']
alt3 = base.copy(); alt3['MA 20/50'] = np.where((C > s20) & (s20 > s50) & (s50 > s200), 1, np.where((C < s20) & (s20 < s50) & (s50 < s200), -1, 0))[ix >= '2005-04']
alt4 = base.copy(); alt4['Swing VWAP'] = dirF[ix >= '2005-04']
# agreement rate (same non-zero sign) as an alternative measure
agree = []
cols = base.columns
for i in range(7):
    for j in range(i + 1, 7):
        a_, b_ = base[cols[i]].values, base[cols[j]].values
        nz = (a_ != 0) & (b_ != 0)
        agree.append((a_[nz] == b_[nz]).mean())
cb = base.corr()
res['votes'] = dict(mean_corr_main_defs=meancorr(base), min=round(float(cb.values[np.triu_indices(7, 1)].min()), 2),
                    max=round(float(cb.values[np.triu_indices(7, 1)].max()), 2),
                    mean_corr_macd_line_instead_of_hist=meancorr(alt1),
                    mean_corr_signal_crosses_for_rsi_rti_asi=meancorr(alt2),
                    mean_corr_full_200_stack=meancorr(alt3),
                    mean_corr_redrawn_vwap=meancorr(alt4),
                    mean_pairwise_same_sign_rate=round(float(np.mean(agree)), 3),
                    first_principal_component_share=round(float(np.linalg.eigvalsh(cb.values)[-1] / 7), 3))
# ---------- claim 9: last bar ----------
lastv = {'close': C[-1], 'sma20': s20[-1], 'sma50': s50[-1], 'sma200': s200[-1], 'rsi': rsi[-1], 'rsi_ma': rsi_ma[-1],
         'macd': macd[-1], 'macd_sig': sig[-1], 'hist': hist[-1], 'rti': rti[-1], 'rti_sig': rti_sig[-1], 'asi': asi[-1],
         'asi_sig': asi_sig[-1], 'osc_full': osc_full[-1], 'osc_tv': osc_w[-1], 'vwap': lval[-1], 'vw_dir': ldir[-1],
         'low50': L[-50:].min(), 'high50': H[-50:].max(),
         'last_50bar_high_date': str(ix[[j for j in range(len(C)) if H[j] >= H[max(0, j - 49):j + 1].max()][-1]].date()),
         'last_50bar_low_date': str(ix[[j for j in range(len(C)) if L[j] <= L[max(0, j - 49):j + 1].min()][-1]].date())}
res['last_bar'] = {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in lastv.items()}
res['last_bar']['votes_main_defs'] = {k: int(base[k].iloc[-1]) for k in base.columns}
res['last_bar']['alt_readings'] = {'RSI vs its MA': int(np.sign(rsi[-1] - rsi_ma[-1])), 'RTI vs its EMA': int(np.sign(rti[-1] - rti_sig[-1])),
                                   'ASI vs its SMA': int(np.sign(asi[-1] - asi_sig[-1])), 'MACD line': int(np.sign(macd[-1])),
                                   'MA 20/50/200 stack': int(alt3['MA 20/50'].iloc[-1]),
                                   'close vs swing VWAP': int(np.sign(C[-1] - lval[-1])),
                                   'close vs 89 EMA': int(np.sign(C[-1] - pine_ema(C, 89)[-1])),
                                   'RSI 30/70 zone': 'neutral' if 30 < rsi[-1] < 70 else 'extreme',
                                   'ASI +/-8 zone': 'neutral' if -8 < asi[-1] < 8 else 'extreme',
                                   'Range Osc beyond -100 (fade reader would call this oversold)': bool(osc_w[-1] < -100)}
json.dump(res, open(OUT + 'indep_results.json', 'w'), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
