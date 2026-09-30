// Can anything call the direction of the next M5 / M15 / M30 bars? Eleven ideas, written down before this was run,
// scored on the user's real XAUUSD history: older 60% vs newest 40% of each file.
// A call made after bar i closes is "traded" from the next open to the close k bars later; the report shows how often
// the direction was right and the average move in the call's direction in ATR and in price after a 0.35 round-trip cost.
// A call is only useful if the average move beats the cost in BOTH halves.
//
// Build:  g++ -std=c++17 -O2 -o shortfc research/sim/shortfc.cpp
// Run:    ./shortfc BASE.csv HIGHER.csv [aggregate_to_seconds=0]

#include "../mock/mql5_mock.h"
#include "../../src/XAU_Core.mqh"
#include "../../src/XAU_Platform.mqh"

#include <functional>

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

static std::vector<MqlRates> aggregate(const std::vector<MqlRates> &v, int sec)
{
   std::vector<MqlRates> out;
   for(const MqlRates &r : v)
   {
      const long long start = r.time - (r.time % sec);
      if(out.empty() || out.back().time != start) { MqlRates b = r; b.time = start; out.push_back(b); }
      else
      {
         MqlRates &b = out.back();
         b.high = std::max(b.high, r.high); b.low = std::min(b.low, r.low); b.close = r.close; b.tick_volume += r.tick_volume;
      }
   }
   return out;
}

static CXauEngine E;
static const double COST = 0.35;

struct Acc
{
   int n = 0, hit = 0; double sa = 0, sp = 0, sp2 = 0;
   void add(double mv_atr, double mv_px) { n++; if(mv_px > 0) hit++; sa += mv_atr; sp += mv_px - COST; sp2 += (mv_px - COST) * (mv_px - COST); }
   double hitp() const { return n ? 100.0 * hit / n : 0.0; }
   double net() const { return n ? sp / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = net(); return std::sqrt(std::max(0.0, sp2 / n - m * m) / n); }
};

// GMT hour and minute of bar i's close
static double gmt_hour_close(int i)
{
   double h = E.m_hour[i] + E.cfg.base_sec / 3600.0;
   if(h >= 24.0) h -= 24.0;
   return h;
}

int main(int argc, char **argv)
{
   if(argc < 3) { std::printf("usage: shortfc BASE.csv HIGHER.csv [aggregate_to_seconds]\n"); return 2; }
   std::vector<MqlRates> base, htf;
   if(!load_csv(argv[1], base) || !load_csv(argv[2], htf)) return 2;
   base.pop_back(); htf.pop_back();
   const int agg = argc > 3 ? std::atoi(argv[3]) : 0;
   if(agg > 0) { base = aggregate(base, agg); base.pop_back(); }
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(base); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.SetBase(base, (int)base.size()); E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) return 2;
   const int n = E.n;
   const int split = E.cfg.warmup + (int)(0.6 * (n - E.cfg.warmup));
   const int bs = E.cfg.base_sec;
   const int b30 = std::max(1, 1800 / bs);        // bars in 30 minutes

   // variance ratio over the last 300 bars (6-bar vs 1-bar returns), rolling
   std::vector<double> vr(n, 1.0);
   for(int i = 320; i < n; i++)
   {
      double s1 = 0, s6 = 0; int c1 = 0, c6 = 0;
      for(int k = i - 299; k <= i; k++) { const double r = E.m_c[k] - E.m_c[k - 1]; s1 += r * r; c1++; }
      for(int k = i - 299; k <= i; k += 6) { const double r = E.m_c[k] - E.m_c[k - 6]; s6 += r * r; c6++; }
      vr[i] = (s1 > 0 && c6 > 0) ? (s6 / c6) / (6.0 * s1 / c1) : 1.0;
   }

   typedef std::function<int(int)> Pred;
   std::vector<std::pair<std::string, Pred>> P = {
      {"1  big candle (>1.5 ATR body) -> reversal", [](int i) {
          const double b = E.m_c[i] - E.m_o[i]; return (std::fabs(b) > 1.5 * E.m_atr[i]) ? (b > 0 ? -1 : 1) : 0; }},
      {"2  big candle + volume > 2x -> continuation", [](int i) {
          const double b = E.m_c[i] - E.m_o[i];
          return (std::fabs(b) > 1.0 * E.m_atr[i] && E.m_vavg[i] > 0 && E.m_v[i] > 2.0 * E.m_vavg[i]) ? (b > 0 ? 1 : -1) : 0; }},
      {"3  volume flow of the last 12 bars", [](int i) {
          double sv = 0, sw = 0;
          for(int k = i - 11; k <= i; k++) { const double b = E.m_c[k] - E.m_o[k]; sw += E.m_v[k]; sv += (b > 0 ? 1 : (b < 0 ? -1 : 0)) * E.m_v[k]; }
          const double f = sw > 0 ? sv / sw : 0; return f > 0.35 ? 1 : (f < -0.35 ? -1 : 0); }},
      {"4  regime: trending -> momentum, choppy -> reversal", [&vr](int i) {
          const double m = E.m_c[i] - E.m_c[i - 6];
          if(vr[i] > 1.15) return m > 0 ? 1 : -1;
          if(vr[i] < 0.85) return m > 0 ? -1 : 1;
          return 0; }},
      {"5  timeframes agree (21-EMA slope = higher trend)", [](int i) {
          const int s = E.m_ema1[i] > E.m_ema1[i - 3] ? 1 : -1; return (E.m_bias[i] == s) ? s : 0; }},
      {"6  London open: follow 07:00-07:30 GMT move", [b30](int i) {
          const double h = gmt_hour_close(i);
          if(std::fabs(h - 7.5) > 1e-6 || i - b30 < 0) return 0;
          const double m = E.m_c[i] - E.m_c[i - b30]; return m > 0 ? 1 : (m < 0 ? -1 : 0); }},
      {"7  New York open: follow first 30 min after 13:30 GMT", [b30](int i) {
          const double h = gmt_hour_close(i);
          if(std::fabs(h - 14.0) > 1e-6 || i - b30 < 0) return 0;
          const double m = E.m_c[i] - E.m_c[i - b30]; return m > 0 ? 1 : (m < 0 ? -1 : 0); }},
      {"8  rejection of yesterday's high / low", [](int i) {
          if(E.m_pdh[i] <= 0) return 0;
          if(E.m_h[i] > E.m_pdh[i] && E.m_c[i] < E.m_pdh[i]) return -1;
          if(E.m_l[i] < E.m_pdl[i] && E.m_c[i] > E.m_pdl[i]) return 1;
          return 0; }},
      {"9  rejection of a $10 round number", [](int i) {
          const double rng = E.m_h[i] - E.m_l[i]; if(rng <= 0) return 0;
          const double up = std::floor(E.m_h[i] / 10.0) * 10.0;           // highest round level touched
          const double dnl = std::ceil(E.m_l[i] / 10.0) * 10.0;           // lowest round level touched
          const double top = std::max(E.m_o[i], E.m_c[i]), bot = std::min(E.m_o[i], E.m_c[i]);
          if(up > top && (E.m_h[i] - top) > 0.5 * rng) return -1;
          if(dnl < bot && (bot - E.m_l[i]) > 0.5 * rng) return 1;
          return 0; }},
      {"10 inside bar, then close beyond the mother bar", [](int i) {
          const bool inside = E.m_h[i - 1] <= E.m_h[i - 2] && E.m_l[i - 1] >= E.m_l[i - 2];
          if(!inside) return 0;
          if(E.m_c[i] > E.m_h[i - 2]) return 1;
          if(E.m_c[i] < E.m_l[i - 2]) return -1;
          return 0; }},
      {"   (baseline) always up", [](int) { return 1; }},
   };

   // 11: logistic regression, refitted daily on the past 20,000 bars, 3-bar horizon, calls only when p > 0.55 / < 0.45
   const int NFL = 10;
   auto feat = [&](int i, double *x) {
      const double a = std::max(E.m_atr[i], 1e-9);
      x[0] = 1.0;
      x[1] = XClamp((E.m_c[i] - E.m_c[i - 1]) / a, -3, 3);
      x[2] = XClamp((E.m_c[i] - E.m_c[i - 3]) / a / 2, -3, 3);
      x[3] = XClamp((E.m_c[i] - E.m_c[i - 12]) / a / 3, -3, 3);
      x[4] = (E.m_rsi[i] - 50) / 25;
      x[5] = (E.m_rsi2[i] - 50) / 50;
      x[6] = XClamp((E.m_c[i] - E.m_ema1[i]) / a / 2, -3, 3);
      x[7] = E.m_bias[i];
      x[8] = E.m_vavg[i] > 0 ? XClamp(E.m_v[i] / E.m_vavg[i] - 1, -1, 3) : 0;
      x[9] = XClamp(vr[i] - 1, -1, 1);
   };
   std::vector<double> w(NFL, 0.0);
   std::vector<int> lcall(n, 0);
   {
      long cur_day = -1;
      for(int i = 400; i < n - 4; i++)
      {
         const long day = (long)E.m_t[i] / 86400;
         if(day != cur_day)
         {
            cur_day = day;
            // refit on bars [i-20000, i-4): labels known before bar i
            std::fill(w.begin(), w.end(), 0.0);
            const int a0 = std::max(400, i - 20000), a1 = i - 4;
            if(a1 - a0 > 2000)
               for(int it = 0; it < 3; it++)
                  for(int t = a0; t < a1; t++)
                  {
                     double x[NFL]; feat(t, x);
                     double z = 0; for(int k = 0; k < NFL; k++) z += w[k] * x[k];
                     const double p = 1.0 / (1.0 + std::exp(-z));
                     const double y = (E.m_c[t + 3] > E.m_c[t]) ? 1.0 : 0.0;
                     for(int k = 0; k < NFL; k++) w[k] += 0.01 * ((y - p) * x[k] - 1e-3 * w[k]);
                  }
         }
         double x[NFL]; feat(i, x);
         double z = 0; for(int k = 0; k < NFL; k++) z += w[k] * x[k];
         const double p = 1.0 / (1.0 + std::exp(-z));
         lcall[i] = (p > 0.55) ? 1 : (p < 0.45 ? -1 : 0);
      }
   }
   P.push_back({"11 learning model (logistic, refitted daily)", [&lcall](int i) { return lcall[i]; }});

   const int H[3] = {1, 3, 6};
   std::printf("== SHORT-TERM DIRECTION: %s%s (%d bars of %d s) ==\n", argv[1], agg ? " aggregated" : "", n, bs);
   std::printf("   older part %s .. %s | newer part .. %s | cost %.2f per call\n", TimeToString(E.m_t[E.cfg.warmup]).c_str(),
               TimeToString(E.m_t[split]).c_str(), TimeToString(E.m_t[n - 1]).c_str(), COST);
   std::printf("    %-52s %4s | %-34s | %-34s\n", "idea", "bars", "older: calls  right  net per call", "newer: calls  right  net per call");
   for(auto &pr : P)
   {
      for(int hk = 0; hk < 3; hk++)
      {
         const int k = H[hk];
         Acc a0, a1;
         for(int i = 400; i < n - k - 1; i++)
         {
            const int d = pr.second(i);
            if(d == 0) continue;
            const double mv = d * (E.m_c[i + k] - E.m_o[i + 1]);
            (i < split ? a0 : a1).add(mv / std::max(E.m_atr[i], 1e-9), mv);
         }
         const bool both = a0.n >= 50 && a1.n >= 30 && a0.net() - a0.se() > 0 && a1.net() - a1.se() > 0;
         std::printf("    %-52s %4d | %6d %5.1f%% %+7.3f (%.3f) | %6d %5.1f%% %+7.3f (%.3f)%s\n", hk == 0 ? pr.first.c_str() : "", k,
                     a0.n, a0.hitp(), a0.net(), a0.se(), a1.n, a1.hitp(), a1.net(), a1.se(), both ? "  << beats the cost in both" : "");
      }
   }
   return 0;
}
