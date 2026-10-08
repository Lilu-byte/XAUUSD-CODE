// Round 12: the TradingView "Adaptive ST [FXC]" indicator traded on its own, as its Buy/Sell labels suggest.
// Line = (high + low) / 2 -+ factor x ATR(10), ratcheting; factor = 1.5 + (5 - 1.5) x percentile rank of the ATR among
// the previous 100 bars (the user's panel: volatility 98 -> factor 4.93). Signal on a close through the line, entry at
// the next bar's open, exit at the open after the opposite signal. Classic Supertrend (10, 3) for comparison.
// Rules fixed before the run. Cost 0.35 per trade, swap 0.50 / 0.20 per night (long / short).
//   BOTH        stop and reverse: always in the market, long or short
//   LONG        buy on a Buy label, flat on a Sell label
//   LONG+TREND  the same, buys only while the daily close is above a rising 200-day mean (the EA's filter)
// R = distance from the entry to the line at the signal (where the indicator would have you wrong).
// Older 60% / newer 40% of each file, and by year.
//
// Build:  g++ -std=c++17 -O2 -o supertrend research/sim/supertrend.cpp
// Run:    ./supertrend BASE.csv HIGHER.csv D1.csv

#include "../mock/mql5_mock.h"
#include "../../src/XAU_Core.mqh"
#include "../../src/XAU_Platform.mqh"

#include <map>

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

struct Acc
{
   int n = 0, w = 0; double usd = 0, r = 0, r2 = 0;
   void add(double d, double rr) { n++; usd += d; r += rr; r2 += rr * rr; if(d > 0) w++; }
   double mr() const { return n ? r / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mr(); return std::sqrt(std::max(0.0, r2 / n - m * m) / n); }
};

int main(int argc, char **argv)
{
   if(argc < 4) { std::printf("usage: supertrend BASE.csv HIGHER.csv D1.csv\n"); return 2; }
   std::vector<MqlRates> B, htf, d1;
   if(!load_csv(argv[1], B) || !load_csv(argv[2], htf) || !load_csv(argv[3], d1)) return 2;
   B.pop_back(); htf.pop_back(); d1.pop_back();
   static CXauEngine E;
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(B); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.SetBase(B, (int)B.size()); E.SetHTF(htf, (int)htf.size()); E.SetDaily(d1, (int)d1.size());
   if(!E.Compute()) return 2;
   const int n = E.n;
   const int SPLIT = E.cfg.warmup + (int)(0.6 * (n - E.cfg.warmup));
   const double COST = 0.35, SWL = 0.50, SWS = 0.20;
   const double days = (double)(B[n - 1].time - B[E.cfg.warmup].time) / 86400.0 * 5.0 / 7.0;
   std::printf("== ADAPTIVE SUPERTREND traded on its own: %s (%d bars of %d s), older .. %s | newer .. %s ==\n", argv[1], n, E.cfg.base_sec,
               TimeToString(B[SPLIT].time).c_str(), TimeToString(B[n - 1].time).c_str());
   std::printf("   per trade: n, won, $ per 0.01 lot, R (se)  | older half | newer half | trades per trading day\n");

   struct Var { const char *name; double fmin, fmax; int look; };
   const Var vars[2] = {{"Adaptive ST (10, 1.5-5, 100)", 1.5, 5.0, 100}, {"Classic ST (10, 3)", 3.0, 3.0, 0}};
   for(const Var &v : vars)
   {
      std::vector<double> line; std::vector<int> dv;
      E.ComputeSupertrend(line, dv, 10, v.fmin, v.fmax, v.look);
      std::printf("\n  %s\n", v.name);
      for(int mode = 0; mode < 3; mode++)
      {
         Acc a[2];
         std::map<int, Acc> by_year;
         int pos = 0, e = -1; double risk = 0.0;
         for(int i = E.cfg.warmup + 110; i < n - 1; i++)
         {
            const bool flip = (dv[i] != dv[i - 1]);
            if(!flip) continue;
            // close the open position at the next open
            if(pos != 0)
            {
               const int x = i + 1;
               const long nights = (long)(B[x].time / 86400 - B[e].time / 86400);
               const double usd = pos * (B[x].open - B[e].open) - COST - nights * (pos > 0 ? SWL : SWS);
               a[(e < SPLIT) ? 0 : 1].add(usd, usd / std::max(risk, 1e-6));
               by_year[XYearOfDays(B[e].time / 86400)].add(usd, usd / std::max(risk, 1e-6));
               pos = 0;
            }
            const int d = dv[i];
            const bool take = (mode == 0) || (mode == 1 && d > 0) || (mode == 2 && d > 0 && E.m_dreg[i] > 0);
            if(take)
            {
               pos = d; e = i + 1;
               risk = std::fabs(B[e].open - line[i]);
            }
         }
         const char *mn[3] = {"BOTH (stop and reverse)", "LONG only", "LONG + daily trend (EA filter)"};
         const int tot = a[0].n + a[1].n;
         std::printf("    %-32s | %5d %3.0f%% %+7.2f$ %+6.3fR (%.3f) | %5d %3.0f%% %+7.2f$ %+6.3fR (%.3f) | %.2f/day\n", mn[mode],
                     a[0].n, a[0].n ? 100.0 * a[0].w / a[0].n : 0.0, a[0].n ? a[0].usd / a[0].n : 0.0, a[0].mr(), a[0].se(),
                     a[1].n, a[1].n ? 100.0 * a[1].w / a[1].n : 0.0, a[1].n ? a[1].usd / a[1].n : 0.0, a[1].mr(), a[1].se(), tot / std::max(days, 1.0));
         std::printf("      by year (R/trade):");
         for(auto &kv : by_year) std::printf(" %d %+.3f(%d)", kv.first, kv.second.mr(), kv.second.n);
         std::printf("\n");
      }
   }
   return 0;
}
