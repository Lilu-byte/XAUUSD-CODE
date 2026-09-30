// How precise are the projected candles? Walk-forward check on the user's real XAUUSD history.
//
//  1. DIRECTION  next bar / 4 bars: pattern match (analog) vs "always up" vs the 21-EMA slope.
//  2. CONE       the analog cone (20th-80th percentile of 25 similar situations) should contain the real price 60% of
//                the time. Compared with a calibrated cone: ATR x hour-of-day profile x the empirical 20th/80th
//                percentile of past standardised moves (rolling, past data only).
//  3. CANDLE SIZE  next bar's high-low: analog's typical path vs ATR x hour profile vs a de-seasonalised EWMA of
//                recent ranges x hour profile ("HAR-style").
// Every model only uses bars before the one it predicts.
//
// Build:  g++ -std=c++17 -O2 -o forecast research/sim/forecast.cpp
// Run:    ./forecast BASE.csv HIGHER.csv [queries=3000]

#include "../mock/mql5_mock.h"
#include "../../src/XAU_Core.mqh"
#include "../../src/XAU_Platform.mqh"

static bool load_csv(const char *path, std::vector<MqlRates> &out)
{
   FILE *f = std::fopen(path, "r");
   if(!f) return false;
   char line[512];
   out.clear();
   while(std::fgets(line, sizeof line, f))
   {
      int Y, M, D, h, m;
      double o, hi, lo, c;
      long long tv = 0;
      int sp = 0;
      if(std::sscanf(line, "%d.%d.%d %d:%d,%lf,%lf,%lf,%lf,%lld,%d", &Y, &M, &D, &h, &m, &o, &hi, &lo, &c, &tv, &sp) < 9) continue;
      MqlRates r{};
      r.time = XDaysFromCivil(Y, M, D) * 86400LL + h * 3600 + m * 60;
      r.open = o; r.high = hi; r.low = lo; r.close = c; r.tick_volume = tv; r.spread = sp;
      out.push_back(r);
   }
   std::fclose(f);
   return out.size() > 100;
}

static int bar_seconds(const std::vector<MqlRates> &v)
{
   std::vector<long long> d;
   for(size_t i = 1; i < v.size() && i < 2000; i++) d.push_back(v[i].time - v[i - 1].time);
   std::sort(d.begin(), d.end());
   return d.empty() ? 0 : (int)d[d.size() / 2];
}

struct Err
{
   double sae = 0, sre = 0, sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0; int n = 0, within = 0;
   void add(double pred, double act)
   {
      if(act <= 0 || pred <= 0) return;
      n++; sae += std::fabs(pred - act); sre += pred / act;
      sx += pred; sy += act; sxx += pred * pred; syy += act * act; sxy += pred * act;
      if(std::fabs(pred - act) <= 0.25 * act) within++;
   }
   double corr() const
   {
      const double cx = sxx - sx * sx / n, cy = syy - sy * sy / n, cxy = sxy - sx * sy / n;
      return (cx > 0 && cy > 0) ? cxy / std::sqrt(cx * cy) : 0.0;
   }
};

int main(int argc, char **argv)
{
   if(argc < 3) { std::printf("usage: forecast BASE.csv HIGHER.csv [queries]\n"); return 2; }
   std::vector<MqlRates> base, htf;
   if(!load_csv(argv[1], base) || !load_csv(argv[2], htf)) return 2;
   base.pop_back(); htf.pop_back();
   const int Q = argc > 3 ? std::atoi(argv[3]) : 3000;
   CXauEngine E;
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(base); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.SetBase(base, (int)base.size()); E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) return 2;
   const int n = E.n;
   const int H = 6;
   const int q0 = n - Q - H - 1;
   // hour-of-day range profile from the bars BEFORE the evaluation period (range / ATR per GMT hour)
   double hs[24] = {0}; int hc[24] = {0}; double all = 0; int allc = 0;
   for(int i = E.cfg.warmup; i < q0; i++)
   {
      const int h = XClampI((int)E.m_hour[i], 0, 23);
      const double r = (E.m_h[i] - E.m_l[i]) / std::max(E.m_atr[i], 1e-9);
      hs[h] += r; hc[h]++; all += r; allc++;
   }
   double prof[24];
   for(int h = 0; h < 24; h++) prof[h] = (hc[h] > 20 && allc > 0) ? (hs[h] / hc[h]) / (all / allc) : 1.0;
   auto hour_of = [&](int i) { return XClampI((int)E.m_hour[i], 0, 23); };

   // de-seasonalised EWMA of ranges (walk-forward state)
   double ew = 0; bool ew_ok = false;
   for(int i = E.cfg.warmup; i < q0; i++)
   {
      const double x = (E.m_h[i] - E.m_l[i]) / prof[hour_of(i)];
      ew = ew_ok ? ew + 0.1 * (x - ew) : x; ew_ok = true;
   }
   // rolling standardised moves for the calibrated cone
   std::vector<std::vector<double>> zs(H + 1);
   auto z_of = [&](int i, int s) {
      double v = 0;
      for(int k = 1; k <= s; k++) v += prof[hour_of(i + k)] * prof[hour_of(i + k)];
      return (E.m_c[i + s] - E.m_c[i]) / (std::max(E.m_atr[i], 1e-9) * std::sqrt(v));
   };
   for(int i = std::max(E.cfg.warmup, q0 - 3000); i < q0 - H; i++)
      for(int s = 1; s <= H; s++) zs[s].push_back(z_of(i, s));

   int d1n = 0, d1a = 0, d1u = 0, d1e = 0, d4n = 0, d4a = 0, d4u = 0, d4e = 0, c4n = 0, c4a = 0;
   int covA[H + 1] = {0}, covC[H + 1] = {0}, covN[H + 1] = {0};
   double widA[H + 1] = {0}, widC[H + 1] = {0};
   Err eA, eS, eH, eK;
   std::vector<double> ratio;          // actual / (ATR x profile), rolling past values, for the median correction
   for(int i = std::max(E.cfg.warmup, q0 - 2000); i < q0; i++) ratio.push_back((E.m_h[i + 1] - E.m_l[i + 1]) / (std::max(E.m_atr[i], 1e-9) * prof[hour_of(i + 1)]));
   for(int i = q0; i < n - H - 1; i++)
   {
      XAnalog a;
      const bool ok = E.AnalogQuery(i, a);
      const double atr = E.m_atr[i];
      const double mv1 = E.m_c[i + 1] - E.m_c[i], mv4 = E.m_c[i + 4] - E.m_c[i];
      const int slope = (E.m_ema1[i] > E.m_ema1[i - 3]) ? 1 : -1;
      if(ok && mv1 != 0)
      {
         d1n++; if((a.dir1 > 0) == (mv1 > 0)) d1a++; if(mv1 > 0) d1u++; if((slope > 0) == (mv1 > 0)) d1e++;
      }
      if(ok && mv4 != 0)
      {
         d4n++; if((a.dir4 > 0) == (mv4 > 0)) d4a++; if(mv4 > 0) d4u++; if((slope > 0) == (mv4 > 0)) d4e++;
         if(E.AnalogConfident(a)) { c4n++; if((a.dir4 > 0) == (mv4 > 0)) c4a++; }
      }
      // cones
      for(int s = 1; s <= H; s++)
      {
         const double mv = E.m_c[i + s] - E.m_c[i];
         std::vector<double> v = zs[s];
         std::sort(v.begin(), v.end());
         double pv = 0;
         for(int k = 1; k <= s; k++) pv += prof[hour_of(i + k)] * prof[hour_of(i + k)];
         const double sc = atr * std::sqrt(pv);
         const double lo = v[(size_t)(0.2 * (v.size() - 1))] * sc, hi = v[(size_t)(0.8 * (v.size() - 1))] * sc;
         covN[s]++;
         if(mv >= lo && mv <= hi) covC[s]++;
         widC[s] += (hi - lo) / atr;
         if(ok)
         {
            const double alo = a.cq_lo[s - 1] * atr, ahi = a.cq_hi[s - 1] * atr;
            if(mv >= alo && mv <= ahi) covA[s]++;
            widA[s] += (ahi - alo) / atr;
         }
      }
      // next candle size
      const double act = E.m_h[i + 1] - E.m_l[i + 1];
      if(ok && a.medoid >= 0)
      {
         const int o = (a.medoid * XA_H + 0) * 4;
         eA.add((E.m_fut[o + 1] - E.m_fut[o + 2]) * atr, act);
      }
      eS.add(atr * prof[hour_of(i + 1)], act);
      {
         std::vector<double> rs = ratio;
         std::nth_element(rs.begin(), rs.begin() + rs.size() / 2, rs.end());
         eK.add(atr * prof[hour_of(i + 1)] * rs[rs.size() / 2], act);
         ratio.push_back((E.m_h[i] - E.m_l[i]) / (std::max(E.m_atr[i - 1], 1e-9) * prof[hour_of(i)]));
         if(ratio.size() > 2000) ratio.erase(ratio.begin());
      }
      eH.add(ew * prof[hour_of(i + 1)], act);
      // walk forward the EWMA and the standardised-move sample with bar i (all of it is in the past for bar i+1)
      ew += 0.1 * ((E.m_h[i] - E.m_l[i]) / prof[hour_of(i)] - ew);
      if(i - H >= 0) for(int s = 1; s <= H; s++) { zs[s].push_back(z_of(i - H, s)); if(zs[s].size() > 3000) zs[s].erase(zs[s].begin()); }
   }
   std::printf("== FORECAST PRECISION: %s, last %d bars (%s .. %s) ==\n", argv[1], Q, TimeToString(E.m_t[q0]).c_str(), TimeToString(E.m_t[n - 1]).c_str());
   std::printf("  DIRECTION  next bar: pattern match %.1f%% | always up %.1f%% | 21-EMA slope %.1f%%  (n %d)\n",
               100.0 * d1a / std::max(d1n, 1), 100.0 * d1u / std::max(d1n, 1), 100.0 * d1e / std::max(d1n, 1), d1n);
   std::printf("             4 bars:   pattern match %.1f%% | always up %.1f%% | 21-EMA slope %.1f%%  | confident pattern calls %.1f%% (n %d)\n",
               100.0 * d4a / std::max(d4n, 1), 100.0 * d4u / std::max(d4n, 1), 100.0 * d4e / std::max(d4n, 1), 100.0 * c4a / std::max(c4n, 1), c4n);
   std::printf("  CONE (should contain the real close 60%% of the time)\n    step | pattern-match cone: inside  width(ATR) | calibrated cone: inside  width(ATR)\n");
   for(int s = 1; s <= H; s++)
      std::printf("     %d   |                 %5.1f%%   %5.2f     |              %5.1f%%   %5.2f\n", s,
                  100.0 * covA[s] / std::max(covN[s], 1), widA[s] / std::max(covN[s], 1), 100.0 * covC[s] / std::max(covN[s], 1), widC[s] / std::max(covN[s], 1));
   std::printf("  NEXT CANDLE SIZE (high-low)      mean abs error  avg pred/actual  correlation  within +-25%%\n");
   const Err *es[4] = {&eA, &eS, &eH, &eK};
   const char *nm[4] = {"pattern match (typical path)", "ATR x hour profile", "recent ranges x hour profile", "ATR x hour profile, median-corrected"};
   for(int k = 0; k < 4; k++)
      std::printf("    %-36s %8.3f        %6.2f          %5.2f        %5.1f%%\n", nm[k], es[k]->sae / std::max(es[k]->n, 1),
                  es[k]->sre / std::max(es[k]->n, 1), es[k]->corr(), 100.0 * es[k]->within / std::max(es[k]->n, 1));
   return 0;
}
