//+------------------------------------------------------------------+
//|                                                    XAU_Core.mqh  |
//|  Platform-independent XAUUSD confluence engine.                  |
//|                                                                  |
//|  Shared by the XAU_Oracle indicator and the XAU_Sniper EA so both |
//|  always produce the same signals, trade plan and statistics.      |
//|                                                                  |
//|  Design rules                                                    |
//|   * Arrays are chronological (index 0 = oldest, n-1 = newest).   |
//|   * Signals are computed on CLOSED bars only and use data <= i,  |
//|     so history and live behaviour are identical (no repainting).  |
//|   * No platform calls in here - the code is also compiled and     |
//|     tested as plain C++ (see research/) against a mock header.    |
//+------------------------------------------------------------------+
#ifndef XAU_CORE_MQH
#define XAU_CORE_MQH

#ifdef __MQL5__
   #define XCD(name)     const double &name[]
   #define XD(name)      double &name[]
   #define XCT(name)     const datetime &name[]
   #define XCI(name)     const int &name[]
   #define XI(name)      int &name[]
   #define XDARR(name)   double name[]
   #define XIARR(name)   int name[]
   #define XTARR(name)   datetime name[]
   #define XCRATES(name) const MqlRates &name[]
#endif

//--- strategy module ids
#define XM_COUNT      8
#define XM_PULLBACK   0
#define XM_SWEEP      1
#define XM_BREAKOUT   2
#define XM_SQUEEZE    3
#define XM_VWAP       4
#define XM_DIVERGE    5
#define XM_FVG        6
#define XM_ROUND      7

#define XHOLD_MAX     200

//--- reason codes when a bar produces no tradable signal
//--- how a simulated trade ended
#define XE_NONE       0
#define XE_STOP       1
#define XE_TRAIL      2
#define XE_TP2        3
#define XE_TIME       4
#define XE_TP1_FULL   5

#define XR_OK         0
#define XR_SESSION    1
#define XR_FRIDAY     2
#define XR_VOL_LOW    3
#define XR_VOL_HIGH   4
#define XR_WARMUP     5
#define XR_NOSETUP    6
#define XR_SL_WIDE    7
#define XR_GRADE      8

//+------------------------------------------------------------------+
//| small math helpers (avoid MathMax/MathMin overload ambiguity)    |
//+------------------------------------------------------------------+
double XMin(const double a, const double b) { return (a < b) ? a : b; }
double XMax(const double a, const double b) { return (a > b) ? a : b; }
int    XMinI(const int a, const int b)      { return (a < b) ? a : b; }
int    XMaxI(const int a, const int b)      { return (a > b) ? a : b; }
double XAbs(const double a)                 { return (a < 0.0) ? -a : a; }
double XClamp(const double x, const double lo, const double hi)
{
   if(x < lo) return lo;
   if(x > hi) return hi;
   return x;
}

string XModuleName(const int m)
{
   switch(m)
   {
      case XM_PULLBACK: return "Trend Pullback";
      case XM_SWEEP:    return "Liquidity Sweep";
      case XM_BREAKOUT: return "Session Breakout";
      case XM_SQUEEZE:  return "Squeeze Break";
      case XM_VWAP:     return "VWAP Fade";
      case XM_DIVERGE:  return "RSI Divergence";
      case XM_FVG:      return "FVG Retest";
      case XM_ROUND:    return "Round Level";
   }
   return "?";
}

string XModuleShort(const int m)
{
   switch(m)
   {
      case XM_PULLBACK: return "PB";
      case XM_SWEEP:    return "SW";
      case XM_BREAKOUT: return "BO";
      case XM_SQUEEZE:  return "SQ";
      case XM_VWAP:     return "VW";
      case XM_DIVERGE:  return "DV";
      case XM_FVG:      return "FG";
      case XM_ROUND:    return "RN";
   }
   return "?";
}

string XGradeName(const int g)
{
   if(g >= 3) return "A+";
   if(g == 2) return "A";
   if(g == 1) return "B";
   return "-";
}

string XReasonText(const int r)
{
   switch(r)
   {
      case XR_OK:       return "ready";
      case XR_SESSION:  return "outside trading session";
      case XR_FRIDAY:   return "Friday cut-off";
      case XR_VOL_LOW:  return "market too quiet";
      case XR_VOL_HIGH: return "volatility spike - stand aside";
      case XR_WARMUP:   return "loading history";
      case XR_NOSETUP:  return "no confluence yet";
      case XR_SL_WIDE:  return "stop too wide for a clean setup";
      case XR_GRADE:    return "setup below minimum grade";
   }
   return "";
}

//+------------------------------------------------------------------+
//| position sizing helpers                                          |
//+------------------------------------------------------------------+
// Lots that lose exactly risk_money if sl_dist (price units) is hit.
double XRawLots(const double risk_money, const double sl_dist,
                const double tick_size, const double tick_value)
{
   if(sl_dist <= 0.0 || tick_size <= 0.0 || tick_value <= 0.0 || risk_money <= 0.0) return 0.0;
   const double loss_per_lot = (sl_dist / tick_size) * tick_value;
   if(loss_per_lot <= 0.0) return 0.0;
   return risk_money / loss_per_lot;
}

// Round DOWN to the volume step and clamp to [vmin, vmax]. Returns 0 if below vmin.
double XNormLotsDown(const double lots, const double vmin, const double vmax, const double vstep)
{
   if(lots <= 0.0 || vstep <= 0.0) return 0.0;
   double v = MathFloor(lots / vstep + 1e-9) * vstep;
   if(v > vmax) v = vmax;
   if(v < vmin) return 0.0;
   return v;
}

//+------------------------------------------------------------------+
//| configuration                                                    |
//+------------------------------------------------------------------+
struct XConfig
{
   // time model (all "GMT" hours are GMT clock hours 0..24)
   int    gmt_offset_sec;    // broker server time minus GMT in WINTER (standard) time
   int    dst_mode;          // 0 fixed offset, 1 server follows US DST (New-York-close servers), 2 follows EU DST
   bool   london_sessions;   // trade_start/end/fri_cutoff are London local clock (follows UK DST)
   int    day_roll_hour;     // GMT hour a new trading day starts (FX roll)
   double asia_start, asia_end;
   double trade_start, trade_end, fri_cutoff;
   bool   use_session_filter;
   int    base_sec;          // seconds per base bar
   int    htf_sec;           // seconds per higher-timeframe bar
   int    warmup;            // bars before signals are trusted

   // indicator periods
   int    ema1, ema2, ema3, atr_p, rsi_p, adx_p, bb_p, don_p;
   double htf_adx_min;
   double pb_adx_min;        // trend pullbacks need a trending market on the base timeframe

   // scorer
   double w[XM_COUNT];
   int    en[XM_COUNT];
   double w_htf, w_inter;
   double score_min;
   int    min_confluence;
   double min_margin;        // winning side must beat the other side by this much
   int    min_grade;
   double grade_a_add, grade_ap_add;

   // filters
   double atr_ratio_min, atr_ratio_max, min_atr_price;
   double asia_compress;
   double round_step;
   double adr_block;         // block trend continuation once this share of the average daily range is used (0 = off)
   int    regime_on;         // 1 = weight modules by the efficiency-ratio regime
   double er_lo, er_hi;      // efficiency-ratio regime thresholds
   double reg_trend_lo;      // trend-module weight multiplier in a choppy regime
   double reg_mr_hi;         // mean-reversion-module weight multiplier in a strongly trending regime
   double fc_er_min;         // below this efficiency ratio the forecast is 'no map' (range only)

   // trade plan
   double sl_atr_min, sl_atr_max, sl_buffer_atr;
   int    sl_lookback;
   double tp1_r, tp2_r, partial_pct, trail_atr;
   int    max_hold_bars;     // 0 = derive from hold_minutes
   int    hold_minutes;
   int    min_hold_bars;
   double cost_price;        // round-turn spread+slippage in price units (simulation only)

   // forecast
   double fc_drift, fc_decay, fc_mr;

   void Defaults()
   {
      gmt_offset_sec = 0;   dst_mode = 0;   london_sessions = true;   day_roll_hour = 22;
      asia_start = 0.0;     asia_end = 7.0;
      trade_start = 7.0;    trade_end = 20.0;   fri_cutoff = 19.0;
      use_session_filter = true;
      base_sec = 900;       htf_sec = 3600;     warmup = 250;

      ema1 = 21; ema2 = 50; ema3 = 200; atr_p = 14; rsi_p = 14; adx_p = 14; bb_p = 20; don_p = 20;
      htf_adx_min = 15.0;  pb_adx_min = 18.0;

      w[XM_PULLBACK] = 1.0;  w[XM_SWEEP] = 1.0;   w[XM_BREAKOUT] = 0.8; w[XM_SQUEEZE] = 0.6;
      w[XM_VWAP]     = 0.5;  w[XM_DIVERGE] = 0.5; w[XM_FVG] = 0.6;      w[XM_ROUND] = 0.3;
      for(int m = 0; m < XM_COUNT; m++) en[m] = 1;
      w_htf = 0.8;  w_inter = 0.3;
      score_min = 1.7;  min_confluence = 2;  min_margin = 0.5;  min_grade = 1;
      grade_a_add = 0.6;  grade_ap_add = 1.2;

      atr_ratio_min = 0.6;  atr_ratio_max = 2.6;  min_atr_price = 0.0;
      asia_compress = 0.7;  round_step = 10.0;
      adr_block = 0.90;  regime_on = 0;  er_lo = 0.20;  er_hi = 0.45;  reg_trend_lo = 0.5;  reg_mr_hi = 0.5;  fc_er_min = 0.12;

      sl_atr_min = 0.9;  sl_atr_max = 2.6;  sl_buffer_atr = 0.15;  sl_lookback = 3;
      tp1_r = 1.0;  tp2_r = 2.5;  partial_pct = 0.5;  trail_atr = 2.0;
      max_hold_bars = 0;  hold_minutes = 480;  min_hold_bars = 8;
      cost_price = 0.30;

      fc_drift = 0.10;  fc_decay = 0.93;  fc_mr = 0.03;
   }
};

//+------------------------------------------------------------------+
//| result structures                                                |
//+------------------------------------------------------------------+
struct XSignal
{
   int    dir;        // +1 buy, -1 sell, 0 none
   int    grade;      // 1=B 2=A 3=A+
   int    n_agree;    // modules voting for the winning side
   int    primary;    // strongest voting module, -1 if none
   int    mask;       // bitmask of agreeing modules
   int    reason;     // XR_* when dir == 0
   double score;      // winning-side score
   double score_opp;  // opposing-side score
   double entry, sl, tp1, tp2, risk, atr;

   void Reset()
   {
      dir = 0; grade = 0; n_agree = 0; primary = -1; mask = 0; reason = XR_NOSETUP;
      score = 0.0; score_opp = 0.0; entry = 0.0; sl = 0.0; tp1 = 0.0; tp2 = 0.0; risk = 0.0; atr = 0.0;
   }
};

struct XTradeResult
{
   bool   ok;          // simulated at all
   bool   closed;      // resolved (false = still open at last_idx)
   int    dir;
   int    entry_idx, exit_idx, bars, stage, exit_kind;
   bool   tp1_hit;
   int    bars_to_tp1;
   double entry, risk;
   double r_net;       // realised R after costs (closed trades)
   double float_r;     // current R incl. banked partials (open trades)
   double mfe_r, mae_r;
   double cur_sl;      // active stop price
   void Reset()
   {
      ok = false; closed = false; dir = 0; entry_idx = -1; exit_idx = -1; bars = 0; stage = 0; exit_kind = XE_NONE;
      tp1_hit = false; bars_to_tp1 = 0; entry = 0.0; risk = 0.0; r_net = 0.0; float_r = 0.0;
      mfe_r = 0.0; mae_r = 0.0; cur_sl = 0.0;
   }
};

struct XStats
{
   int    n, wins, losses, scratch, tp1_hits, nh_all, nh_win;
   double sum_r, sum_r2, sum_win, sum_loss, sum_mfe;
   int    hold_all[XHOLD_MAX];
   int    hold_win[XHOLD_MAX];

   void Reset()
   {
      n = 0; wins = 0; losses = 0; scratch = 0; tp1_hits = 0; nh_all = 0; nh_win = 0;
      sum_r = 0.0; sum_r2 = 0.0; sum_win = 0.0; sum_loss = 0.0; sum_mfe = 0.0;
   }
   void Add(const XTradeResult &r)
   {
      n++;
      sum_r += r.r_net;
      sum_r2 += r.r_net * r.r_net;
      sum_mfe += r.mfe_r;
      if(r.tp1_hit) tp1_hits++;
      const bool win = (r.r_net > 0.05);
      if(win)                      { wins++;   sum_win += r.r_net; }
      else if(r.r_net < -0.05)     { losses++; sum_loss += -r.r_net; }
      else                         { scratch++; }
      if(nh_all < XHOLD_MAX) { hold_all[nh_all] = r.bars; nh_all++; }
      if(win && nh_win < XHOLD_MAX)
      {
         hold_win[nh_win] = (r.bars_to_tp1 > 0) ? r.bars_to_tp1 : r.bars;
         nh_win++;
      }
   }
   double WinRate()      const { return (n > 0) ? 100.0 * wins / n : 0.0; }
   double Expectancy()   const { return (n > 0) ? sum_r / n : 0.0; }
   double ProfitFactor() const { return (sum_loss > 1e-9) ? sum_win / sum_loss : ((sum_win > 0.0) ? 99.0 : 0.0); }
   double ExpStdErr()    const
   {
      if(n < 2) return 0.0;
      const double m = sum_r / n;
      const double var = (sum_r2 - n * m * m) / (n - 1);
      return MathSqrt(XMax(var, 0.0) / n);
   }
   double Tp1Rate()      const { return (n > 0) ? 100.0 * tp1_hits / n : 0.0; }

   // percentile (0..1) of holding time in bars; winners = time to first target, else whole trade
   int HoldPct(const bool winners, const double pct) const
   {
      const int cnt = winners ? nh_win : nh_all;
      if(cnt <= 0) return 0;
      int tmp[XHOLD_MAX];
      for(int i = 0; i < cnt; i++) tmp[i] = winners ? hold_win[i] : hold_all[i];
      for(int i = 1; i < cnt; i++)
      {
         const int key = tmp[i];
         int j = i - 1;
         while(j >= 0 && tmp[j] > key) { tmp[j + 1] = tmp[j]; j--; }
         tmp[j + 1] = key;
      }
      int idx = (int)MathFloor(pct * (cnt - 1) + 0.5);
      if(idx < 0) idx = 0;
      if(idx > cnt - 1) idx = cnt - 1;
      return tmp[idx];
   }
};

struct XTrial
{
   XStats all;
   XStats mod[XM_COUNT];
   XStats grade[4];
   void Reset()
   {
      all.Reset();
      for(int m = 0; m < XM_COUNT; m++) mod[m].Reset();
      for(int g = 0; g < 4; g++) grade[g].Reset();
   }
};

//+------------------------------------------------------------------+
//| generic indicator helpers                                        |
//+------------------------------------------------------------------+
void XCalcEMA(XCD(src), XD(dst), const int cnt, const int period)
{
   if(cnt <= 0) return;
   const double a = 2.0 / (period + 1.0);
   dst[0] = src[0];
   for(int i = 1; i < cnt; i++) dst[i] = dst[i - 1] + a * (src[i] - dst[i - 1]);
}

void XCalcATR(XCD(h), XCD(l), XCD(c), XD(atr), const int cnt, const int p)
{
   if(cnt <= 0) return;
   atr[0] = h[0] - l[0];
   for(int i = 1; i < cnt; i++)
   {
      double tr = h[i] - l[i];
      tr = XMax(tr, XAbs(h[i] - c[i - 1]));
      tr = XMax(tr, XAbs(l[i] - c[i - 1]));
      atr[i] = (atr[i - 1] * (p - 1) + tr) / p;
   }
}

void XCalcRSI(XCD(c), XD(rsi), const int cnt, const int p)
{
   if(cnt <= 0) return;
   double ag = 0.0, al = 0.0;
   rsi[0] = 50.0;
   for(int i = 1; i < cnt; i++)
   {
      const double ch = c[i] - c[i - 1];
      const double g = (ch > 0.0) ? ch : 0.0;
      const double ls = (ch < 0.0) ? -ch : 0.0;
      if(i <= p)
      {
         ag += g / p;
         al += ls / p;
         rsi[i] = 50.0;
         if(i < p) continue;
      }
      else
      {
         ag = (ag * (p - 1) + g) / p;
         al = (al * (p - 1) + ls) / p;
      }
      rsi[i] = (al < 1e-12) ? 100.0 : 100.0 - 100.0 / (1.0 + ag / al);
   }
}

void XCalcADX(XCD(h), XCD(l), XCD(c), XD(pdi), XD(mdi), XD(adx), const int cnt, const int p)
{
   double smtr = 0.0, smp = 0.0, smm = 0.0, dxsum = 0.0, av = 0.0;
   for(int i = 0; i < cnt; i++) { pdi[i] = 0.0; mdi[i] = 0.0; adx[i] = 0.0; }
   for(int i = 1; i < cnt; i++)
   {
      const double up = h[i] - h[i - 1];
      const double dn = l[i - 1] - l[i];
      const double pdm = (up > dn && up > 0.0) ? up : 0.0;
      const double mdm = (dn > up && dn > 0.0) ? dn : 0.0;
      double tr = h[i] - l[i];
      tr = XMax(tr, XAbs(h[i] - c[i - 1]));
      tr = XMax(tr, XAbs(l[i] - c[i - 1]));
      if(i <= p) { smtr += tr; smp += pdm; smm += mdm; }
      else       { smtr = smtr - smtr / p + tr; smp = smp - smp / p + pdm; smm = smm - smm / p + mdm; }
      if(i < p) continue;
      if(smtr < 1e-12) continue;
      pdi[i] = 100.0 * smp / smtr;
      mdi[i] = 100.0 * smm / smtr;
      const double den = pdi[i] + mdi[i];
      const double dx = (den < 1e-12) ? 0.0 : 100.0 * XAbs(pdi[i] - mdi[i]) / den;
      if(i < 2 * p - 1)      { dxsum += dx; }
      else if(i == 2 * p - 1) { dxsum += dx; av = dxsum / p; adx[i] = av; }
      else                   { av = (av * (p - 1) + dx) / p; adx[i] = av; }
   }
}

// map every base bar to the latest COMPLETED higher-TF bar (or -1)
void XMapTF(XCT(bt), const int bn, const int base_sec, XCT(ht), const int hn, const int htf_sec, XI(map))
{
   int j = -1;
   for(int i = 0; i < bn; i++)
   {
      const datetime close_t = bt[i] + base_sec;
      while(j + 1 < hn && ht[j + 1] + htf_sec <= close_t) j++;
      map[i] = j;
   }
}

//--- calendar maths for daylight saving (Howard Hinnant's civil-date algorithms)
long XDaysFromCivil(const int y0, const int m, const int d)
{
   const long y = (m <= 2) ? y0 - 1 : y0;
   const long era = ((y >= 0) ? y : y - 399) / 400;
   const long yoe = y - era * 400;
   const long mp = (m > 2) ? m - 3 : m + 9;
   const long doy = (153 * mp + 2) / 5 + d - 1;
   const long doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
   return era * 146097 + doe - 719468;
}

int XYearOfDays(const long z0)
{
   const long z = z0 + 719468;
   const long era = ((z >= 0) ? z : z - 146096) / 146097;
   const long doe = z - era * 146097;
   const long yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
   long y = yoe + era * 400;
   const long doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
   const long mp = (5 * doy + 2) / 153;
   const long m = (mp < 10) ? mp + 3 : mp - 9;
   if(m <= 2) y++;
   return (int)y;
}

// days-since-epoch of the n-th Sunday (n>=1) of a month
long XNthSunday(const int y, const int m, const int n)
{
   const long first = XDaysFromCivil(y, m, 1);
   const long dow = (first + 4) % 7;                 // 0 = Sunday
   return first + (7 - dow) % 7 + 7 * (n - 1);
}

long XLastSunday(const int y, const int m)
{
   const long next = (m == 12) ? XDaysFromCivil(y + 1, 1, 1) : XDaysFromCivil(y, m + 1, 1);
   const long last = next - 1;
   const long dow = (last + 4) % 7;
   return last - dow;
}

// US daylight time: 2nd Sunday of March 07:00 UTC .. 1st Sunday of November 06:00 UTC
bool XUsDst(const long gmt_sec)
{
   const int y = XYearOfDays(gmt_sec / 86400);
   const long a = XNthSunday(y, 3, 2) * 86400 + 7 * 3600;
   const long b = XNthSunday(y, 11, 1) * 86400 + 6 * 3600;
   return (gmt_sec >= a && gmt_sec < b);
}

// EU/UK summer time: last Sunday of March 01:00 UTC .. last Sunday of October 01:00 UTC
bool XEuDst(const long gmt_sec)
{
   const int y = XYearOfDays(gmt_sec / 86400);
   const long a = XLastSunday(y, 3) * 86400 + 3600;
   const long b = XLastSunday(y, 10) * 86400 + 3600;
   return (gmt_sec >= a && gmt_sec < b);
}

// Server-time minus GMT that applied at server timestamp t.
int XOffsetAt(const XConfig &c, const datetime t)
{
   int off = c.gmt_offset_sec;
   if(c.dst_mode == 0) return off;
   const long g = (long)t - c.gmt_offset_sec;
   if(c.dst_mode == 1 && XUsDst(g)) off += 3600;
   else if(c.dst_mode == 2 && XEuDst(g)) off += 3600;
   return off;
}

double XHourGmt(const datetime t, const int gmt_offset_sec)
{
   long s = ((long)t - gmt_offset_sec) % 86400;
   if(s < 0) s += 86400;
   return (double)s / 3600.0;
}

// 0 = Sunday ... 5 = Friday, 6 = Saturday (GMT calendar)
int XWeekdayGmt(const datetime t, const int gmt_offset_sec)
{
   long d = ((long)t - gmt_offset_sec) / 86400;
   return (int)((d + 4) % 7);
}

//+------------------------------------------------------------------+
//| the engine                                                       |
//+------------------------------------------------------------------+
class CXauEngine
{
public:
   XConfig cfg;
   int     n, hn, in_n;
   bool    inter_invert;

   // base series
   XTARR(m_t); XDARR(m_o); XDARR(m_h); XDARR(m_l); XDARR(m_c); XDARR(m_v);
   // base indicators
   XDARR(m_ema1); XDARR(m_ema2); XDARR(m_ema3); XDARR(m_atr); XDARR(m_atrref);
   XDARR(m_rsi); XDARR(m_adx); XDARR(m_pdi); XDARR(m_mdi);
   XDARR(m_bbw); XDARR(m_bbp); XDARR(m_donh); XDARR(m_donl); XDARR(m_vavg);
   XDARR(m_vwap); XDARR(m_vsd); XDARR(m_hour);
   XIARR(m_daybars); XIARR(m_asiaok); XDARR(m_asiahi); XDARR(m_asialo);
   XDARR(m_pdh); XDARR(m_pdl); XDARR(m_adr); XDARR(m_adru); XDARR(m_er);
   // higher timeframe
   XTARR(m_ht); XDARR(m_hc); XDARR(m_hh); XDARR(m_hl); XDARR(m_hema2); XDARR(m_hema3);
   XDARR(m_hpdi); XDARR(m_hmdi); XDARR(m_hadx0); XIARR(m_hbias0);
   XIARR(m_hmap); XIARR(m_bias); XDARR(m_hadx);
   // intermarket proxy
   XTARR(m_it); XDARR(m_ic); XDARR(m_iema1); XDARR(m_iema2); XIARR(m_idir0); XIARR(m_imap); XIARR(m_inter);
   // votes and scores
   XDARR(m_vote);
   XDARR(m_scl); XDARR(m_scs); XIARR(m_nal); XIARR(m_nas); XIARR(m_mkl); XIARR(m_mks); XDARR(m_snet);
   // seasonality (mean range by GMT hour, normalised)
   double  season[24];
   // forecast output
   int     fc_n;
   XTARR(fc_t); XDARR(fc_o); XDARR(fc_h); XDARR(fc_l); XDARR(fc_c); XDARR(fc_up); XDARR(fc_dn);
   double  fc_drift_atr;
   double  fc_rmse;      // realised one-step error of the drift model (calibrates the cone)
   bool    fc_nomap;     // choppy / spiking market: show range only, no directional path

   CXauEngine() { cfg.Defaults(); n = 0; hn = 0; in_n = 0; inter_invert = false; fc_n = 0; fc_drift_atr = 0.0; fc_rmse = 0.0; fc_nomap = false; }

   //--- data loading ------------------------------------------------
   bool SetBase(XCRATES(r), const int cnt)
   {
      if(cnt < 1) return false;
      n = cnt;
      ArrayResize(m_t, n); ArrayResize(m_o, n); ArrayResize(m_h, n);
      ArrayResize(m_l, n); ArrayResize(m_c, n); ArrayResize(m_v, n);
      for(int i = 0; i < n; i++)
      {
         m_t[i] = r[i].time; m_o[i] = r[i].open; m_h[i] = r[i].high;
         m_l[i] = r[i].low;  m_c[i] = r[i].close; m_v[i] = (double)r[i].tick_volume;
      }
      return true;
   }
   bool SetHTF(XCRATES(r), const int cnt)
   {
      hn = (cnt < 0) ? 0 : cnt;
      ArrayResize(m_ht, hn); ArrayResize(m_hc, hn); ArrayResize(m_hh, hn); ArrayResize(m_hl, hn);
      for(int i = 0; i < hn; i++) { m_ht[i] = r[i].time; m_hc[i] = r[i].close; m_hh[i] = r[i].high; m_hl[i] = r[i].low; }
      return hn > 0;
   }
   // Optional proxy series (e.g. DXY or EURUSD) on the SAME timeframe as the base.
   // invert = true when the proxy moves opposite to gold (DXY), false for EURUSD-like.
   bool SetInter(XCRATES(r), const int cnt, const bool invert)
   {
      in_n = (cnt < 0) ? 0 : cnt;
      inter_invert = invert;
      ArrayResize(m_it, in_n); ArrayResize(m_ic, in_n);
      for(int i = 0; i < in_n; i++) { m_it[i] = r[i].time; m_ic[i] = r[i].close; }
      return in_n > 0;
   }

   //--- derived helpers ---------------------------------------------
   int MaxHold() const
   {
      if(cfg.max_hold_bars > 0) return cfg.max_hold_bars;
      const int b = (cfg.hold_minutes * 60) / (cfg.base_sec > 0 ? cfg.base_sec : 900);
      return XMaxI(b, cfg.min_hold_bars);
   }
   double LowestLow(const int a, const int b) const
   {
      double x = m_l[a];
      for(int k = a + 1; k <= b; k++) if(m_l[k] < x) x = m_l[k];
      return x;
   }
   double HighestHigh(const int a, const int b) const
   {
      double x = m_h[a];
      for(int k = a + 1; k <= b; k++) if(m_h[k] > x) x = m_h[k];
      return x;
   }
   double MinRsi(const int a, const int b) const
   {
      double x = m_rsi[a];
      for(int k = a + 1; k <= b; k++) if(m_rsi[k] < x) x = m_rsi[k];
      return x;
   }
   double MaxRsi(const int a, const int b) const
   {
      double x = m_rsi[a];
      for(int k = a + 1; k <= b; k++) if(m_rsi[k] > x) x = m_rsi[k];
      return x;
   }
   bool Spike(const int i) const { return m_vavg[i] > 0.0 && m_v[i] >= 1.3 * m_vavg[i]; }

   double SeasonAt(const datetime t) const
   {
      int h = (int)XHourGmt(t, XOffsetAt(cfg, t));
      if(h < 0) h = 0;
      if(h > 23) h = 23;
      return season[h];
   }

   //--- main computation --------------------------------------------
   bool Compute()
   {
      if(n < cfg.warmup + 60) return false;
      SizeArrays();
      ComputeBaseIndicators();
      ComputeSessionLevels();
      ComputeHTF();
      ComputeVotes();
      ComputeScores();
      return true;
   }

   // Re-derive scores after cfg weights / enable flags changed.
   void ComputeScores()
   {
      for(int i = 0; i < n; i++)
      {
         double sl = 0.0, ss = 0.0;
         int nl = 0, ns = 0, ml = 0, ms = 0;
         if(i >= cfg.warmup)
         {
            for(int m = 0; m < XM_COUNT; m++)
            {
               if(cfg.en[m] == 0) continue;
               const double v = m_vote[i * XM_COUNT + m];
               double wm = cfg.w[m];
               if(cfg.regime_on == 1)
               {
                  const bool trend_mod = (m == XM_PULLBACK || m == XM_BREAKOUT || m == XM_SQUEEZE);
                  const bool mr_mod = (m == XM_VWAP || m == XM_DIVERGE);
                  if(trend_mod && m_er[i] < cfg.er_lo) wm *= cfg.reg_trend_lo;
                  if(mr_mod && m_er[i] > cfg.er_hi) wm *= cfg.reg_mr_hi;
               }
               if(v > 0.0)      { sl += wm * v;  nl++; ml |= (1 << m); }
               else if(v < 0.0) { ss += wm * -v; ns++; ms |= (1 << m); }
            }
            const double b = (double)m_bias[i];
            sl += cfg.w_htf * b;  ss -= cfg.w_htf * b;
            const double x = (double)m_inter[i];
            sl += cfg.w_inter * x;  ss -= cfg.w_inter * x;
         }
         m_scl[i] = sl; m_scs[i] = ss; m_nal[i] = nl; m_nas[i] = ns; m_mkl[i] = ml; m_mks[i] = ms;
         m_snet[i] = sl - ss;
      }
   }

   //--- filters -------------------------------------------------------
   int FilterReason(const int i) const
   {
      if(i < cfg.warmup || i >= n) return XR_WARMUP;
      const double a = m_atr[i];
      if(a < cfg.min_atr_price) return XR_VOL_LOW;
      if(m_atrref[i] > 0.0)
      {
         const double ratio = a / m_atrref[i];
         if(ratio < cfg.atr_ratio_min) return XR_VOL_LOW;
         if(ratio > cfg.atr_ratio_max) return XR_VOL_HIGH;
      }
      if(cfg.use_session_filter && cfg.base_sec <= 7200)
      {
         double hrn = m_hour[i] + cfg.base_sec / 3600.0;      // the next bar's open (GMT), where we would enter
         const int off = XOffsetAt(cfg, m_t[i]);
         if(cfg.london_sessions && XEuDst((long)m_t[i] - off)) hrn += 1.0;   // London local clock
         if(hrn >= 24.0) hrn -= 24.0;
         if(!(hrn >= cfg.trade_start && hrn < cfg.trade_end)) return XR_SESSION;
         if(XWeekdayGmt(m_t[i], off) == 5 && hrn >= cfg.fri_cutoff) return XR_FRIDAY;
      }
      return XR_OK;
   }

   //--- signal ------------------------------------------------------
   // returns true when a tradable signal exists at closed bar i
   bool Evaluate(const int i, XSignal &s) const
   {
      s.Reset();
      if(i < 0 || i >= n) return false;
      const int fr = FilterReason(i);
      if(fr != XR_OK) { s.reason = fr; return false; }

      const double sl = m_scl[i], ss = m_scs[i];
      int dir = 0;
      if(sl >= cfg.score_min && m_nal[i] >= cfg.min_confluence && (sl - ss) >= cfg.min_margin) dir = 1;
      else if(ss >= cfg.score_min && m_nas[i] >= cfg.min_confluence && (ss - sl) >= cfg.min_margin) dir = -1;
      if(dir == 0) { s.reason = XR_NOSETUP; s.score = XMax(sl, ss); return false; }

      s.dir = dir;
      s.score     = (dir > 0) ? sl : ss;
      s.score_opp = (dir > 0) ? ss : sl;
      s.n_agree   = (dir > 0) ? m_nal[i] : m_nas[i];
      s.mask      = (dir > 0) ? m_mkl[i] : m_mks[i];
      double best = 0.0;
      for(int m = 0; m < XM_COUNT; m++)
      {
         if((s.mask & (1 << m)) == 0) continue;
         const double v = XAbs(m_vote[i * XM_COUNT + m]) * cfg.w[m];
         if(v > best) { best = v; s.primary = m; }
      }
      s.grade = 1;
      if(s.score >= cfg.score_min + cfg.grade_a_add) s.grade = 2;
      if(s.score >= cfg.score_min + cfg.grade_ap_add && s.n_agree >= 3) s.grade = 3;
      if(s.grade < cfg.min_grade) { s.dir = 0; s.reason = XR_GRADE; return false; }
      if(!BuildPlan(i, dir, s)) { s.dir = 0; s.reason = XR_SL_WIDE; return false; }
      s.reason = XR_OK;
      return true;
   }

   // Structural stop, then TP levels in R multiples.
   bool BuildPlan(const int i, const int dir, XSignal &s) const
   {
      const double a = m_atr[i];
      if(a <= 0.0) return false;
      const double entry = m_c[i];
      const int lb = XMaxI(1, cfg.sl_lookback);
      double sl, dist;
      if(dir > 0)
      {
         sl = LowestLow(i - lb + 1, i) - cfg.sl_buffer_atr * a;
         dist = entry - sl;
         if(dist < cfg.sl_atr_min * a) { sl = entry - cfg.sl_atr_min * a; dist = entry - sl; }
      }
      else
      {
         sl = HighestHigh(i - lb + 1, i) + cfg.sl_buffer_atr * a;
         dist = sl - entry;
         if(dist < cfg.sl_atr_min * a) { sl = entry + cfg.sl_atr_min * a; dist = sl - entry; }
      }
      if(dist > cfg.sl_atr_max * a) return false;
      s.entry = entry; s.sl = sl; s.risk = dist; s.atr = a;
      s.tp1 = entry + dir * cfg.tp1_r * dist;
      s.tp2 = entry + dir * cfg.tp2_r * dist;
      return true;
   }

   //--- bar-based trade simulator ------------------------------------
   // Entry at the OPEN of bar i+1. Bars up to last_idx may be used.
   // Pessimistic tie-breaks: a bar touching both stop and target counts as stopped;
   // the runner cannot reach TP2 on the same bar that TP1 was filled.
   bool SimulateTrade(const int i, const int dir, const double sl_price, const int last_idx, XTradeResult &r) const
   {
      r.Reset();
      const int e = i + 1;
      if(e > last_idx || e >= n || dir == 0) return false;
      const double a = m_atr[i];
      const double entry = m_o[e];
      const double risk = (dir > 0) ? (entry - sl_price) : (sl_price - entry);
      if(risk < 0.4 * a || risk <= 0.0) return false;

      const int maxh = MaxHold();
      const int jend = XMinI(last_idx, e + maxh - 1);
      double stopf = -risk;
      const double tp1f = cfg.tp1_r * risk, tp2f = cfg.tp2_r * risk;
      double rem = 1.0, real = 0.0, ext = 0.0, mfe = 0.0, mae = 0.0, lastfcl = 0.0;
      int stage = 0;
      bool closed = false;
      int exit_idx = jend;
      int ek = XE_NONE;

      r.ok = true; r.dir = dir; r.entry_idx = e; r.entry = entry; r.risk = risk;

      for(int j = e; j <= jend; j++)
      {
         const double fhi = (dir > 0) ? (m_h[j] - entry) : (entry - m_l[j]);
         const double flo = (dir > 0) ? (m_l[j] - entry) : (entry - m_h[j]);
         const double fcl = (dir > 0) ? (m_c[j] - entry) : (entry - m_c[j]);
         lastfcl = fcl;
         if(fhi > mfe) mfe = fhi;
         if(flo < mae) mae = flo;

         if(stage == 0)
         {
            if(flo <= stopf) { real += rem * (stopf / risk); rem = 0.0; closed = true; exit_idx = j; ek = XE_STOP; break; }
            if(fhi >= tp1f)
            {
               real += cfg.partial_pct * cfg.tp1_r;
               rem = 1.0 - cfg.partial_pct;
               stage = 1; stopf = 0.0; ext = fhi;
               r.tp1_hit = true; r.bars_to_tp1 = j - e + 1;
               if(rem <= 1e-9) { rem = 0.0; closed = true; exit_idx = j; ek = XE_TP1_FULL; break; }
               if(flo <= stopf) { rem = 0.0; closed = true; exit_idx = j; ek = XE_TRAIL; break; }
               const double tr0 = ext - cfg.trail_atr * a;
               if(tr0 > stopf) stopf = tr0;
               if(j - e + 1 >= maxh) { real += rem * (fcl / risk); rem = 0.0; closed = true; exit_idx = j; ek = XE_TIME; break; }
               continue;
            }
         }
         else
         {
            if(flo <= stopf) { real += rem * (stopf / risk); rem = 0.0; closed = true; exit_idx = j; ek = XE_TRAIL; break; }
            if(fhi >= tp2f)  { real += rem * cfg.tp2_r;      rem = 0.0; closed = true; exit_idx = j; ek = XE_TP2; break; }
            if(fhi > ext) ext = fhi;
            const double tr1 = ext - cfg.trail_atr * a;
            if(tr1 > stopf) stopf = tr1;
         }
         if(j - e + 1 >= maxh) { real += rem * (fcl / risk); rem = 0.0; closed = true; exit_idx = j; ek = XE_TIME; break; }
      }

      r.stage = stage;
      r.exit_kind = ek;
      r.bars = exit_idx - e + 1;
      r.exit_idx = exit_idx;
      r.mfe_r = mfe / risk;
      r.mae_r = mae / risk;
      r.cur_sl = entry + dir * stopf;
      if(closed)
      {
         r.closed = true;
         r.r_net = real - cfg.cost_price / risk;
         r.float_r = r.r_net;
      }
      else
      {
         r.closed = false;
         r.float_r = real + rem * (lastfcl / risk);
      }
      return true;
   }

   //--- historical trial ----------------------------------------------
   // One trade at a time per stream. Only resolved trades are counted.
   void RunTrial(const int from_i, const int last_closed, XTrial &tr) const
   {
      tr.Reset();
      int busy_all = -1;
      int busy_m[XM_COUNT];
      for(int m = 0; m < XM_COUNT; m++) busy_m[m] = -1;
      const int start = XMaxI(from_i, cfg.warmup);
      XSignal s;
      XTradeResult r;
      for(int i = start; i < last_closed; i++)
      {
         // composite strategy
         if(i > busy_all && Evaluate(i, s))
         {
            if(SimulateTrade(i, s.dir, s.sl, last_closed, r))
            {
               busy_all = r.exit_idx;
               if(r.closed) { tr.all.Add(r); tr.grade[s.grade].Add(r); }
            }
         }
         // each module on its own (never against the higher-timeframe trend)
         if(FilterReason(i) != XR_OK) continue;
         for(int m = 0; m < XM_COUNT; m++)
         {
            const double v = m_vote[i * XM_COUNT + m];
            if(v == 0.0 || i <= busy_m[m]) continue;
            const int d = (v > 0.0) ? 1 : -1;
            if(m_bias[i] * d < 0) continue;
            XSignal p;
            p.Reset();
            if(!BuildPlan(i, d, p)) continue;
            if(SimulateTrade(i, d, p.sl, last_closed, r))
            {
               busy_m[m] = r.exit_idx;
               if(r.closed) tr.mod[m].Add(r);
            }
         }
      }
   }

   // Switch off modules whose own trial shows a clearly negative expectancy.
   // Returns the number of modules disabled.
   int ApplyGating(const XTrial &tr, const int min_trades, const double min_exp_r)
   {
      int off = 0;
      for(int m = 0; m < XM_COUNT; m++)
      {
         cfg.en[m] = 1;
         if(tr.mod[m].n >= min_trades && tr.mod[m].Expectancy() < min_exp_r) { cfg.en[m] = 0; off++; }
      }
      ComputeScores();
      return off;
   }

   //--- forecast --------------------------------------------------------
   // Expected-value path for the next `steps` bars, starting at start_price.
   // ref_i = last CLOSED bar whose indicators/score seed the drift.
   void Forecast(const int ref_i, const double start_price, const datetime t_first, const int steps)
   {
      fc_n = 0;
      if(ref_i < cfg.warmup || ref_i >= n || steps < 1) return;
      ArrayResize(fc_t, steps); ArrayResize(fc_o, steps); ArrayResize(fc_h, steps);
      ArrayResize(fc_l, steps); ArrayResize(fc_c, steps); ArrayResize(fc_up, steps); ArrayResize(fc_dn, steps);
      const double a = m_atr[ref_i];
      const double e = m_ema1[ref_i];
      // calibrate the cone on how wrong this very drift model has been over the last 100 bars
      double se = 0.0;
      int ne = 0;
      for(int k = XMaxI(cfg.warmup, ref_i - 100); k < ref_i; k++)
      {
         const double ex = m_atr[k] * XClamp(m_snet[k] / 3.0, -1.0, 1.0) * cfg.fc_drift;
         const double er1 = (m_c[k + 1] - m_c[k]) - ex;
         se += er1 * er1;
         ne++;
      }
      fc_rmse = (ne >= 20) ? MathSqrt(se / ne) : 0.63 * a;
      fc_nomap = (m_er[ref_i] < cfg.fc_er_min) || (m_atrref[ref_i] > 0.0 && a / m_atrref[ref_i] > cfg.atr_ratio_max);
      const double dir_s = fc_nomap ? 0.0 : XClamp(m_snet[ref_i] / 3.0, -1.0, 1.0);
      fc_drift_atr = dir_s * cfg.fc_drift;
      const double mr = fc_nomap ? 0.0 : ((m_adx[ref_i] < 20.0) ? cfg.fc_mr : cfg.fc_mr * 0.4);
      double px = start_price;
      double decay = 1.0;
      for(int j = 0; j < steps; j++)
      {
         const datetime tj = t_first + (datetime)j * cfg.base_sec;
         const double sea = SeasonAt(tj);
         const double move = a * (fc_drift_atr * decay) - mr * (px - e);
         const double o = px;
         const double c = px + move;
         const double rng = XMax(a * sea, XAbs(c - o));
         const double wick = XMax(0.5 * (rng - XAbs(c - o)), 0.1 * rng);
         fc_t[j] = tj;
         fc_o[j] = o;
         fc_c[j] = c;
         fc_h[j] = XMax(o, c) + wick;
         fc_l[j] = XMin(o, c) - wick;
         const double sigma = fc_rmse * sea * MathSqrt((double)(j + 1));
         fc_up[j] = c + sigma;
         fc_dn[j] = c - sigma;
         px = c;
         decay *= cfg.fc_decay;
      }
      fc_n = steps;
   }

   // How often did the sign of the score predict the direction `horizon` bars later?
   void ForecastAudit(const int horizon, const double min_abs_score, const int from_i, const int last_closed,
                      int &n_tot, int &n_hit) const
   {
      n_tot = 0; n_hit = 0;
      const int start = XMaxI(from_i, cfg.warmup);
      for(int i = start; i + horizon <= last_closed; i++)
      {
         const double s = m_snet[i];
         if(XAbs(s) < min_abs_score) continue;
         const double mv = m_c[i + horizon] - m_c[i];
         if(mv == 0.0) continue;
         n_tot++;
         if((s > 0.0) == (mv > 0.0)) n_hit++;
      }
   }

private:
   void SizeArrays()
   {
      ArrayResize(m_ema1, n); ArrayResize(m_ema2, n); ArrayResize(m_ema3, n);
      ArrayResize(m_atr, n);  ArrayResize(m_atrref, n);
      ArrayResize(m_rsi, n);  ArrayResize(m_adx, n);  ArrayResize(m_pdi, n); ArrayResize(m_mdi, n);
      ArrayResize(m_bbw, n);  ArrayResize(m_bbp, n);  ArrayResize(m_donh, n); ArrayResize(m_donl, n);
      ArrayResize(m_vavg, n); ArrayResize(m_vwap, n); ArrayResize(m_vsd, n);  ArrayResize(m_hour, n);
      ArrayResize(m_daybars, n); ArrayResize(m_asiaok, n); ArrayResize(m_asiahi, n); ArrayResize(m_asialo, n);
      ArrayResize(m_pdh, n);  ArrayResize(m_pdl, n);  ArrayResize(m_adr, n);  ArrayResize(m_adru, n);  ArrayResize(m_er, n);
      ArrayResize(m_hmap, n); ArrayResize(m_bias, n); ArrayResize(m_hadx, n);
      ArrayResize(m_imap, n); ArrayResize(m_inter, n);
      ArrayResize(m_vote, n * XM_COUNT);
      ArrayResize(m_scl, n);  ArrayResize(m_scs, n);  ArrayResize(m_nal, n); ArrayResize(m_nas, n);
      ArrayResize(m_mkl, n);  ArrayResize(m_mks, n);  ArrayResize(m_snet, n);
   }

   void ComputeBaseIndicators()
   {
      XCalcEMA(m_c, m_ema1, n, cfg.ema1);
      XCalcEMA(m_c, m_ema2, n, cfg.ema2);
      XCalcEMA(m_c, m_ema3, n, cfg.ema3);
      XCalcATR(m_h, m_l, m_c, m_atr, n, cfg.atr_p);
      XCalcEMA(m_atr, m_atrref, n, 100);
      XCalcRSI(m_c, m_rsi, n, cfg.rsi_p);
      XCalcADX(m_h, m_l, m_c, m_pdi, m_mdi, m_adx, n, cfg.adx_p);

      // Bollinger bandwidth (relative) and its percentile over 100 bars
      for(int i = 0; i < n; i++)
      {
         m_bbw[i] = 0.0;
         if(i < cfg.bb_p - 1) continue;
         double sum = 0.0, sq = 0.0;
         for(int k = i - cfg.bb_p + 1; k <= i; k++) { sum += m_c[k]; sq += m_c[k] * m_c[k]; }
         const double mean = sum / cfg.bb_p;
         const double var = sq / cfg.bb_p - mean * mean;
         const double sd = MathSqrt(XMax(var, 0.0));
         m_bbw[i] = (mean > 0.0) ? 4.0 * sd / mean : 0.0;
      }
      for(int i = 0; i < n; i++)
      {
         const int a0 = XMaxI(0, i - 99);
         int below = 0, tot = 0;
         for(int k = a0; k <= i; k++) { tot++; if(m_bbw[k] <= m_bbw[i]) below++; }
         m_bbp[i] = (tot > 0) ? (double)below / tot : 0.5;
      }
      // Donchian (prior don_p bars, excluding the current bar) and average tick volume (prior 20)
      for(int i = 0; i < n; i++)
      {
         if(i < cfg.don_p) { m_donh[i] = m_h[i]; m_donl[i] = m_l[i]; }
         else
         {
            double hh = m_h[i - cfg.don_p], ll = m_l[i - cfg.don_p];
            for(int k = i - cfg.don_p + 1; k <= i - 1; k++) { if(m_h[k] > hh) hh = m_h[k]; if(m_l[k] < ll) ll = m_l[k]; }
            m_donh[i] = hh; m_donl[i] = ll;
         }
         if(i < 20) m_vavg[i] = 0.0;
         else
         {
            double sv = 0.0;
            for(int k = i - 20; k < i; k++) sv += m_v[k];
            m_vavg[i] = sv / 20.0;
         }
      }
      // Kaufman efficiency ratio: net move / path length over 30 bars (0 = pure chop, 1 = straight line)
      for(int i = 0; i < n; i++)
      {
         m_er[i] = 0.0;
         if(i < 30) continue;
         double path = 0.0;
         for(int k = i - 29; k <= i; k++) path += XAbs(m_c[k] - m_c[k - 1]);
         m_er[i] = (path > 0.0) ? XAbs(m_c[i] - m_c[i - 30]) / path : 0.0;
      }
      // intraday range seasonality by GMT hour
      double hs[24], hc[24];
      double allsum = 0.0; int allc = 0;
      for(int k = 0; k < 24; k++) { hs[k] = 0.0; hc[k] = 0.0; season[k] = 1.0; }
      if(cfg.base_sec <= 3600)
      {
         for(int i = 0; i < n; i++)
         {
            int hh = (int)XHourGmt(m_t[i], XOffsetAt(cfg, m_t[i]));
            if(hh < 0) hh = 0;
            if(hh > 23) hh = 23;
            hs[hh] += (m_h[i] - m_l[i]) / XMax(m_atrref[i], 1e-9);
            hc[hh] += 1.0;
            allsum += (m_h[i] - m_l[i]) / XMax(m_atrref[i], 1e-9); allc++;
         }
         const double gm = (allc > 0) ? allsum / allc : 1.0;
         for(int k = 0; k < 24; k++)
            if(hc[k] >= 5.0 && gm > 0.0) season[k] = XClamp((hs[k] / hc[k]) / gm, 0.5, 2.0);
      }
   }

   void ComputeSessionLevels()
   {
      long prev_day = -1, prev_cal = -1;
      double day_hi = 0.0, day_lo = 0.0, pdh_v = 0.0, pdl_v = 0.0;
      double a_hi = -1e18, a_lo = 1e18;
      int a_bars = 0;
      double ranges[14];
      int nr = 0, rpos = 0;
      double cpv = 0.0, cv = 0.0, cpp = 0.0;
      int bars_today = 0;
      const bool intraday = (cfg.base_sec <= 7200);
      for(int i = 0; i < n; i++)
      {
         const long tt = (long)m_t[i] - XOffsetAt(cfg, m_t[i]);
         const long day = (tt - (long)cfg.day_roll_hour * 3600) / 86400;
         const long cal = tt / 86400;
         long sec = tt % 86400;
         if(sec < 0) sec += 86400;
         const double hr = (double)sec / 3600.0;
         m_hour[i] = hr;

         if(day != prev_day)
         {
            if(prev_day != -1)
            {
               pdh_v = day_hi; pdl_v = day_lo;
               ranges[rpos] = day_hi - day_lo;
               rpos = (rpos + 1) % 14;
               if(nr < 14) nr++;
            }
            day_hi = m_h[i]; day_lo = m_l[i];
            cpv = 0.0; cv = 0.0; cpp = 0.0; bars_today = 0;
            prev_day = day;
         }
         else
         {
            if(m_h[i] > day_hi) day_hi = m_h[i];
            if(m_l[i] < day_lo) day_lo = m_l[i];
         }
         if(cal != prev_cal) { a_hi = -1e18; a_lo = 1e18; a_bars = 0; prev_cal = cal; }
         if(hr >= cfg.asia_start && hr < cfg.asia_end)
         {
            if(m_h[i] > a_hi) a_hi = m_h[i];
            if(m_l[i] < a_lo) a_lo = m_l[i];
            a_bars++;
         }
         m_asiaok[i] = (intraday && hr >= cfg.asia_end && a_bars >= 6) ? 1 : 0;
         m_asiahi[i] = a_hi; m_asialo[i] = a_lo;

         const double tp = (m_h[i] + m_l[i] + m_c[i]) / 3.0;
         const double vol = XMax(m_v[i], 1.0);
         cpv += tp * vol; cv += vol; cpp += tp * tp * vol; bars_today++;
         m_vwap[i] = cpv / cv;
         m_vsd[i] = MathSqrt(XMax(cpp / cv - m_vwap[i] * m_vwap[i], 0.0));
         m_daybars[i] = bars_today;

         m_pdh[i] = pdh_v; m_pdl[i] = pdl_v;
         double adr = 0.0;
         if(nr >= 5)
         {
            for(int k = 0; k < nr; k++) adr += ranges[k];
            adr /= nr;
         }
         m_adr[i] = adr;
         m_adru[i] = (adr > 0.0) ? (day_hi - day_lo) / adr : 0.0;
      }
   }

   void ComputeHTF()
   {
      // higher-timeframe bias
      if(hn > 0)
      {
         ArrayResize(m_hema2, hn); ArrayResize(m_hema3, hn);
         ArrayResize(m_hpdi, hn);  ArrayResize(m_hmdi, hn); ArrayResize(m_hadx0, hn); ArrayResize(m_hbias0, hn);
         XCalcEMA(m_hc, m_hema2, hn, cfg.ema2);
         XCalcEMA(m_hc, m_hema3, hn, cfg.ema3);
         XCalcADX(m_hh, m_hl, m_hc, m_hpdi, m_hmdi, m_hadx0, hn, cfg.adx_p);
         for(int j = 0; j < hn; j++)
         {
            int b = 0;
            if(j >= 220 && m_hadx0[j] >= cfg.htf_adx_min)
            {
               if(m_hema2[j] > m_hema3[j] && m_hc[j] > m_hema2[j]) b = 1;
               else if(m_hema2[j] < m_hema3[j] && m_hc[j] < m_hema2[j]) b = -1;
            }
            m_hbias0[j] = b;
         }
         XMapTF(m_t, n, cfg.base_sec, m_ht, hn, cfg.htf_sec, m_hmap);
         for(int i = 0; i < n; i++)
         {
            const int j = m_hmap[i];
            m_bias[i] = (j >= 0) ? m_hbias0[j] : 0;
            m_hadx[i] = (j >= 0) ? m_hadx0[j] : 0.0;
         }
      }
      else
      {
         for(int i = 0; i < n; i++) { m_hmap[i] = -1; m_bias[i] = 0; m_hadx[i] = 0.0; }
      }
      // intermarket proxy (optional)
      if(in_n > 60)
      {
         ArrayResize(m_iema1, in_n); ArrayResize(m_iema2, in_n); ArrayResize(m_idir0, in_n);
         XCalcEMA(m_ic, m_iema1, in_n, 20);
         XCalcEMA(m_ic, m_iema2, in_n, 50);
         for(int j = 0; j < in_n; j++)
         {
            int d = 0;
            if(j >= 60)
            {
               if(m_iema1[j] > m_iema2[j] && m_ic[j] > m_iema1[j]) d = 1;
               else if(m_iema1[j] < m_iema2[j] && m_ic[j] < m_iema1[j]) d = -1;
            }
            m_idir0[j] = inter_invert ? -d : d;
         }
         XMapTF(m_t, n, cfg.base_sec, m_it, in_n, cfg.base_sec, m_imap);
         for(int i = 0; i < n; i++) m_inter[i] = (m_imap[i] >= 0) ? m_idir0[m_imap[i]] : 0;
      }
      else
      {
         for(int i = 0; i < n; i++) { m_imap[i] = -1; m_inter[i] = 0; }
      }
   }

   //--- strategy modules -----------------------------------------------
   double VotePullback(const int i) const
   {
      const int b = m_bias[i];
      const double a = m_atr[i];
      const double rng = m_h[i] - m_l[i];
      if(b == 0 || a <= 0.0 || rng <= 0.0) return 0.0;
      if(m_adx[i] < cfg.pb_adx_min) return 0.0;
      double s = 0.55;
      if(m_adx[i] > 22.0) s += 0.15;
      if(m_hadx[i] > 25.0) s += 0.15;
      if(b > 0)
      {
         if(!(m_ema1[i] > m_ema2[i] && m_c[i] > m_ema3[i])) return 0.0;
         const double lo5 = LowestLow(i - 4, i);
         if(!(lo5 <= m_ema1[i] + 0.25 * a)) return 0.0;
         if(!(lo5 >= m_ema2[i] - 0.6 * a)) return 0.0;
         if(!(m_c[i] > m_ema1[i] && m_c[i] > m_o[i])) return 0.0;
         if(!(m_rsi[i] > m_rsi[i - 1] && MinRsi(i - 5, i) < 50.0 && m_rsi[i] < 68.0)) return 0.0;
         const double lw = XMin(m_o[i], m_c[i]) - m_l[i];
         if(!(lw >= 0.35 * rng || (m_c[i] - m_l[i]) >= 0.65 * rng)) return 0.0;
         if(lw >= 0.5 * rng) s += 0.15;
         return XMin(s, 1.0);
      }
      if(!(m_ema1[i] < m_ema2[i] && m_c[i] < m_ema3[i])) return 0.0;
      const double hi5 = HighestHigh(i - 4, i);
      if(!(hi5 >= m_ema1[i] - 0.25 * a)) return 0.0;
      if(!(hi5 <= m_ema2[i] + 0.6 * a)) return 0.0;
      if(!(m_c[i] < m_ema1[i] && m_c[i] < m_o[i])) return 0.0;
      if(!(m_rsi[i] < m_rsi[i - 1] && MaxRsi(i - 5, i) > 50.0 && m_rsi[i] > 32.0)) return 0.0;
      const double uw = m_h[i] - XMax(m_o[i], m_c[i]);
      if(!(uw >= 0.35 * rng || (m_h[i] - m_c[i]) >= 0.65 * rng)) return 0.0;
      if(uw >= 0.5 * rng) s += 0.15;
      return -XMin(s, 1.0);
   }

   double VoteSweep(const int i) const
   {
      const double a = m_atr[i];
      const double rng = m_h[i] - m_l[i];
      if(a <= 0.0 || rng <= 0.0) return 0.0;
      const double dl = 0.03 * a;
      // candidate levels below / above price
      double lo_lv[3], hi_lv[3];
      int nlo = 0, nhi = 0;
      if(m_pdl[i] > 0.0) { lo_lv[nlo] = m_pdl[i]; nlo++; }
      if(m_pdh[i] > 0.0) { hi_lv[nhi] = m_pdh[i]; nhi++; }
      if(m_asiaok[i] == 1) { lo_lv[nlo] = m_asialo[i]; nlo++; hi_lv[nhi] = m_asiahi[i]; nhi++; }
      lo_lv[nlo] = LowestLow(i - 30, i - 2);  nlo++;
      hi_lv[nhi] = HighestHigh(i - 30, i - 2); nhi++;

      int hits_l = 0, hits_s = 0;
      const double lw = XMin(m_o[i], m_c[i]) - m_l[i];
      const double uw = m_h[i] - XMax(m_o[i], m_c[i]);
      const double lo2 = XMin(m_l[i], m_l[i - 1]);
      const double hi2 = XMax(m_h[i], m_h[i - 1]);
      for(int k = 0; k < nlo; k++)
      {
         const double L = lo_lv[k];
         const bool one = (m_l[i] < L - dl && m_c[i] > L && lw >= 0.4 * rng);
         const bool two = (lo2 < L - dl && m_c[i - 1] <= L + 0.05 * a && m_c[i] > L && m_c[i] > m_o[i] && (m_c[i] - m_o[i]) >= 0.4 * a);
         if(one || two) hits_l++;
      }
      for(int k = 0; k < nhi; k++)
      {
         const double L = hi_lv[k];
         const bool one = (m_h[i] > L + dl && m_c[i] < L && uw >= 0.4 * rng);
         const bool two = (hi2 > L + dl && m_c[i - 1] >= L - 0.05 * a && m_c[i] < L && m_c[i] < m_o[i] && (m_o[i] - m_c[i]) >= 0.4 * a);
         if(one || two) hits_s++;
      }
      if(hits_l == 0 && hits_s == 0) return 0.0;
      const bool longside = (hits_l >= hits_s);
      const int hits = longside ? hits_l : hits_s;
      double s = 0.55;
      if(Spike(i)) s += 0.15;
      if((longside ? lw : uw) >= 0.55 * rng) s += 0.15;
      if(hits >= 2) s += 0.15;
      s = XMin(s, 1.0);
      return longside ? s : -s;
   }

   // state carried between bars: index of the first close outside the Asian range today
   double VoteBreakout(const int i, const int bk_up_bar, const int bk_dn_bar) const
   {
      if(m_asiaok[i] == 0 || m_adr[i] <= 0.0) return 0.0;
      const double a = m_atr[i];
      if(a <= 0.0) return 0.0;
      if(m_hour[i] >= cfg.trade_end) return 0.0;
      const double arange = m_asiahi[i] - m_asialo[i];
      if(arange > cfg.asia_compress * m_adr[i]) return 0.0;
      const double body = XAbs(m_c[i] - m_o[i]);
      const double rng = m_h[i] - m_l[i];
      if(rng <= 0.0 || body < 0.6 * a || body < 0.55 * rng) return 0.0;
      double s = 0.6;
      if(m_vavg[i] > 0.0 && m_v[i] > 1.5 * m_vavg[i]) s += 0.2;
      if(body >= 1.0 * a) s += 0.2;
      if(m_c[i] > m_asiahi[i] + 0.1 * a && m_c[i] > m_o[i] && bk_up_bar >= 0 && i - bk_up_bar <= 6) return s;
      if(m_c[i] < m_asialo[i] - 0.1 * a && m_c[i] < m_o[i] && bk_dn_bar >= 0 && i - bk_dn_bar <= 6) return -s;
      return 0.0;
   }

   double VoteSqueeze(const int i) const
   {
      const double a = m_atr[i];
      if(a <= 0.0) return 0.0;
      double mn = 1.0;
      for(int k = i - 6; k <= i - 1; k++) if(m_bbp[k] < mn) mn = m_bbp[k];
      if(mn > 0.25) return 0.0;
      if(!(m_adx[i] > m_adx[i - 1])) return 0.0;
      const double body = XAbs(m_c[i] - m_o[i]);
      if(body < 0.5 * a) return 0.0;
      double s = 0.55;
      if(m_adx[i] > 20.0) s += 0.2;
      if(Spike(i)) s += 0.25;
      s = XMin(s, 1.0);
      if(m_c[i] > m_donh[i] && m_c[i] > m_o[i]) return s;
      if(m_c[i] < m_donl[i] && m_c[i] < m_o[i]) return -s;
      return 0.0;
   }

   double VoteVwap(const int i) const
   {
      const double a = m_atr[i];
      const double rng = m_h[i] - m_l[i];
      if(a <= 0.0 || rng <= 0.0 || m_daybars[i] < 15 || m_vsd[i] <= 0.0) return 0.0;
      if(m_adx[i] >= 20.0) return 0.0;
      const double up = m_vwap[i] + 2.0 * m_vsd[i];
      const double dn = m_vwap[i] - 2.0 * m_vsd[i];
      const double uw = m_h[i] - XMax(m_o[i], m_c[i]);
      const double lw = XMin(m_o[i], m_c[i]) - m_l[i];
      if(m_h[i] > up && m_c[i] < m_o[i] && uw >= 0.35 * rng)
      {
         double s = 0.6;
         if(m_rsi[i] > 65.0) s += 0.2;
         if(m_c[i] < up) s += 0.2;
         return -XMin(s, 1.0);
      }
      if(m_l[i] < dn && m_c[i] > m_o[i] && lw >= 0.35 * rng)
      {
         double s = 0.6;
         if(m_rsi[i] < 35.0) s += 0.2;
         if(m_c[i] > dn) s += 0.2;
         return XMin(s, 1.0);
      }
      return 0.0;
   }

   double VoteRound(const int i) const
   {
      const double a = m_atr[i];
      const double rng = m_h[i] - m_l[i];
      if(a <= 0.0 || rng <= 0.0 || cfg.round_step <= 0.0) return 0.0;
      const double lw = XMin(m_o[i], m_c[i]) - m_l[i];
      const double uw = m_h[i] - XMax(m_o[i], m_c[i]);
      // long: wick pierces a round number from above and closes back over it
      double lv = MathFloor(m_l[i] / cfg.round_step + 0.5) * cfg.round_step;
      if(m_l[i] <= lv + 0.1 * a && m_l[i] >= lv - 0.35 * a && m_c[i] > lv && m_c[i] > m_o[i] && lw >= 0.4 * rng)
         return (MathMod(lv, 50.0) < 1e-6) ? 0.6 : 0.4;
      lv = MathFloor(m_h[i] / cfg.round_step + 0.5) * cfg.round_step;
      if(m_h[i] >= lv - 0.1 * a && m_h[i] <= lv + 0.35 * a && m_c[i] < lv && m_c[i] < m_o[i] && uw >= 0.4 * rng)
         return (MathMod(lv, 50.0) < 1e-6) ? -0.6 : -0.4;
      return 0.0;
   }

   void ComputeVotes()
   {
      ArrayInitialize(m_vote, 0.0);
      const int sp = 3;
      // FVG zones
      double bt_top[6], bt_bot[6], br_top[6], br_bot[6];
      int bt_n = 0, br_n = 0;
      int bt_age[6], br_age[6];
      // pivots: [0] older, [1] newer
      int pl_idx[2], ph_idx[2];
      double pl_px[2], pl_rsi[2], ph_px[2], ph_rsi[2];
      int pl_cnt = 0, ph_cnt = 0;
      for(int q = 0; q < 2; q++) { pl_idx[q] = 0; ph_idx[q] = 0; pl_px[q] = 0.0; pl_rsi[q] = 0.0; ph_px[q] = 0.0; ph_rsi[q] = 0.0; }
      int bull_arm = -1, bear_arm = -1;
      double bull_str = 0.0, bear_str = 0.0, bull_px = 0.0, bear_px = 0.0;
      long prev_cal = -1;
      int bk_up_bar = -1, bk_dn_bar = -1;

      for(int i = 0; i < n; i++)
      {
         const bool live = (i >= cfg.warmup);
         const double a = m_atr[i];

         // Asian-range break state (reset each GMT calendar day)
         const long cal = ((long)m_t[i] - XOffsetAt(cfg, m_t[i])) / 86400;
         if(cal != prev_cal) { prev_cal = cal; bk_up_bar = -1; bk_dn_bar = -1; }
         if(m_asiaok[i] == 1)
         {
            if(bk_up_bar < 0 && m_c[i] > m_asiahi[i] + 0.1 * a) bk_up_bar = i;
            if(bk_dn_bar < 0 && m_c[i] < m_asialo[i] - 0.1 * a) bk_dn_bar = i;
         }

         // pivots confirmed sp bars after the fact
         const int k = i - sp;
         if(k >= sp + 1)
         {
            bool isPL = true, isPH = true;
            for(int q = 1; q <= sp; q++)
            {
               if(!(m_l[k] < m_l[k - q]))  isPL = false;
               if(!(m_l[k] <= m_l[k + q])) isPL = false;
               if(!(m_h[k] > m_h[k - q]))  isPH = false;
               if(!(m_h[k] >= m_h[k + q])) isPH = false;
            }
            if(isPL)
            {
               pl_idx[0] = pl_idx[1]; pl_px[0] = pl_px[1]; pl_rsi[0] = pl_rsi[1];
               pl_idx[1] = k; pl_px[1] = m_l[k]; pl_rsi[1] = m_rsi[k];
               if(pl_cnt < 2) pl_cnt++;
               if(live && pl_cnt >= 2)
               {
                  const int gap = pl_idx[1] - pl_idx[0];
                  if(pl_px[1] < pl_px[0] - 0.1 * a && pl_rsi[1] > pl_rsi[0] + 3.0 && pl_rsi[0] < 45.0 && gap >= 5 && gap <= 80)
                  {
                     bull_arm = i + 4;
                     bull_str = 0.55 + (((pl_rsi[1] - pl_rsi[0]) >= 8.0) ? 0.25 : 0.0);
                     bull_px = pl_px[1];
                  }
               }
            }
            if(isPH)
            {
               ph_idx[0] = ph_idx[1]; ph_px[0] = ph_px[1]; ph_rsi[0] = ph_rsi[1];
               ph_idx[1] = k; ph_px[1] = m_h[k]; ph_rsi[1] = m_rsi[k];
               if(ph_cnt < 2) ph_cnt++;
               if(live && ph_cnt >= 2)
               {
                  const int gap = ph_idx[1] - ph_idx[0];
                  if(ph_px[1] > ph_px[0] + 0.1 * a && ph_rsi[1] < ph_rsi[0] - 3.0 && ph_rsi[0] > 55.0 && gap >= 5 && gap <= 80)
                  {
                     bear_arm = i + 4;
                     bear_str = 0.55 + (((ph_rsi[0] - ph_rsi[1]) >= 8.0) ? 0.25 : 0.0);
                     bear_px = ph_px[1];
                  }
               }
            }
         }

         double vdiv = 0.0;
         if(live)
         {
            if(bull_arm >= i)
            {
               if(m_l[i] < bull_px - 0.25 * a) bull_arm = -1;
               else if(m_c[i] > m_o[i] && m_c[i] > m_c[i - 1]) { vdiv = bull_str; bull_arm = -1; }
            }
            if(bear_arm >= i)
            {
               if(m_h[i] > bear_px + 0.25 * a) bear_arm = -1;
               else if(m_c[i] < m_o[i] && m_c[i] < m_c[i - 1]) { if(bear_str > XAbs(vdiv)) vdiv = -bear_str; bear_arm = -1; }
            }
         }

         // FVG: test existing zones first, then register a new one created on this bar
         double vfvg = 0.0;
         for(int z = 0; z < bt_n; )
         {
            bt_age[z]++;
            if(m_c[i] < bt_bot[z] || bt_age[z] > 40) { bt_n--; bt_top[z] = bt_top[bt_n]; bt_bot[z] = bt_bot[bt_n]; bt_age[z] = bt_age[bt_n]; continue; }
            if(live && m_l[i] <= bt_top[z] && m_l[i] >= bt_bot[z] - 0.2 * a && m_c[i] > 0.5 * (bt_top[z] + bt_bot[z]) && m_c[i] > m_o[i])
            {
               double s = 0.5;
               if(bt_top[z] - bt_bot[z] >= 0.5 * a) s += 0.25;
               if(Spike(i)) s += 0.25;
               if(s > vfvg) vfvg = s;
               bt_n--; bt_top[z] = bt_top[bt_n]; bt_bot[z] = bt_bot[bt_n]; bt_age[z] = bt_age[bt_n];
               continue;
            }
            z++;
         }
         for(int z = 0; z < br_n; )
         {
            br_age[z]++;
            if(m_c[i] > br_top[z] || br_age[z] > 40) { br_n--; br_top[z] = br_top[br_n]; br_bot[z] = br_bot[br_n]; br_age[z] = br_age[br_n]; continue; }
            if(live && m_h[i] >= br_bot[z] && m_h[i] <= br_top[z] + 0.2 * a && m_c[i] < 0.5 * (br_top[z] + br_bot[z]) && m_c[i] < m_o[i])
            {
               double s = 0.5;
               if(br_top[z] - br_bot[z] >= 0.5 * a) s += 0.25;
               if(Spike(i)) s += 0.25;
               if(s > XAbs(vfvg)) vfvg = -s;
               br_n--; br_top[z] = br_top[br_n]; br_bot[z] = br_bot[br_n]; br_age[z] = br_age[br_n];
               continue;
            }
            z++;
         }
         if(i >= 2 && a > 0.0)
         {
            if(m_l[i] > m_h[i - 2] && (m_l[i] - m_h[i - 2]) >= 0.2 * a && (m_c[i - 1] - m_o[i - 1]) >= 0.5 * a)
            {
               if(bt_n == 6) { for(int z = 1; z < 6; z++) { bt_top[z - 1] = bt_top[z]; bt_bot[z - 1] = bt_bot[z]; bt_age[z - 1] = bt_age[z]; } bt_n = 5; }
               bt_top[bt_n] = m_l[i]; bt_bot[bt_n] = m_h[i - 2]; bt_age[bt_n] = 0; bt_n++;
            }
            if(m_h[i] < m_l[i - 2] && (m_l[i - 2] - m_h[i]) >= 0.2 * a && (m_o[i - 1] - m_c[i - 1]) >= 0.5 * a)
            {
               if(br_n == 6) { for(int z = 1; z < 6; z++) { br_top[z - 1] = br_top[z]; br_bot[z - 1] = br_bot[z]; br_age[z - 1] = br_age[z]; } br_n = 5; }
               br_top[br_n] = m_l[i - 2]; br_bot[br_n] = m_h[i]; br_age[br_n] = 0; br_n++;
            }
         }

         if(!live) continue;
         const int o = i * XM_COUNT;
         m_vote[o + XM_PULLBACK] = VotePullback(i);
         m_vote[o + XM_SWEEP]    = VoteSweep(i);
         m_vote[o + XM_BREAKOUT] = VoteBreakout(i, bk_up_bar, bk_dn_bar);
         m_vote[o + XM_SQUEEZE]  = VoteSqueeze(i);
         m_vote[o + XM_VWAP]     = VoteVwap(i);
         m_vote[o + XM_DIVERGE]  = vdiv;
         m_vote[o + XM_FVG]      = vfvg;
         m_vote[o + XM_ROUND]    = VoteRound(i);
         // late in the day, after most of the average daily range is spent, continuation setups are usually exhaustion
         if(cfg.adr_block > 0.0 && m_adru[i] >= cfg.adr_block)
         {
            m_vote[o + XM_PULLBACK] = 0.0;
            m_vote[o + XM_BREAKOUT] = 0.0;
            m_vote[o + XM_SQUEEZE]  = 0.0;
         }
      }
   }
};

#endif // XAU_CORE_MQH
