// Round 14: "give the stop a couple more pips". Every signal of all 48 strategy/exit combinations, simulated with
// the stop moved further away by 0, 0.1, 0.25 and 0.5 ATR:
//   SAME TARGETS   targets stay at the same prices (what a trader does when moving only the stop)
//   SCALED         targets keep their R multiples of the new, larger risk
// Compared in dollars per signal per 0.01 lot after the 0.35 cost (the risk changes, so R is not comparable), and
// winners. Older 60% / newer 40% of each file. Rules fixed before the run.
//
// Build:  g++ -std=c++17 -O2 -o stopbuf research/sim/stopbuf.cpp
// Run:    ./stopbuf BASE.csv HIGHER.csv

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

struct Acc
{
   int n = 0, w = 0; double s = 0, s2 = 0;
   void add(double usd) { n++; s += usd; s2 += usd * usd; if(usd > 0) w++; }
   double mean() const { return n ? s / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mean(); return std::sqrt(std::max(0.0, s2 / n - m * m) / n); }
   double win() const { return n ? 100.0 * w / n : 0.0; }
};

int main(int argc, char **argv)
{
   if(argc < 3) { std::printf("usage: stopbuf BASE.csv HIGHER.csv\n"); return 2; }
   std::vector<MqlRates> base, htf;
   if(!load_csv(argv[1], base) || !load_csv(argv[2], htf)) return 2;
   base.pop_back(); htf.pop_back();
   static CXauEngine E;
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(base); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1; E.cfg.cost_price = 0.35;
   E.SetBase(base, (int)base.size()); E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) return 2;
   const int split = E.cfg.warmup + (int)(0.6 * (E.n - E.cfg.warmup));
   const double bufs[4] = {0.0, 0.10, 0.25, 0.50};
   Acc same0[4], same1[4], scal0[4], scal1[4];
   for(int c = 0; c < XLAB_CELLS; c++)
   {
      const int st = c / XP_COUNT;
      XExit x0; XMakeExit(c % XP_COUNT, E.cfg, x0);
      for(int i = E.cfg.warmup + 10; i < E.n - 6; i++)
      {
         if(E.StrategyDir(st, i) == 0) continue;
         XSignal sg;
         if(!E.StrategySignal(st, i, x0, sg)) continue;
         const int d = sg.dir;
         const double a = E.m_atr[i];
         const double entry = E.m_o[i + 1];
         const double r0 = d * (entry - sg.sl);
         if(r0 <= 0.0) continue;
         for(int v = 0; v < 4; v++)
         {
            const double sl = sg.sl - d * bufs[v] * a;
            const double r1 = d * (entry - sl);
            for(int mode = 0; mode < 2; mode++)
            {
               XExit x = x0;
               if(mode == 0 && v > 0)
               {
                  // same target prices: the R multiples shrink by r0 / r1; the trail and the time stop are unchanged
                  x.tp1_r *= r0 / r1; x.tp2_r *= r0 / r1;
               }
               XTradeResult r;
               if(!E.SimulateTradeAt(i, i + 1, entry, false, d, sl, E.n - 2, x, r) || !r.closed) continue;
               const double usd = r.r_net * r.risk;
               if(mode == 0) ((i < split) ? same0[v] : same1[v]).add(usd);
               else          ((i < split) ? scal0[v] : scal1[v]).add(usd);
            }
         }
      }
   }
   std::printf("== WIDER STOPS: %s (%d bars of %d s), every signal of all 48 combinations, cost 0.35 ==\n", argv[1], E.n, E.cfg.base_sec);
   std::printf("   older .. %s | newer .. %s   ($ per trade per 0.01 lot after cost, winners)\n", TimeToString(E.m_t[split]).c_str(), TimeToString(E.m_t[E.n - 1]).c_str());
   for(int mode = 0; mode < 2; mode++)
   {
      std::printf("\n  %s\n", mode == 0 ? "SAME TARGET PRICES (only the stop moves)" : "TARGETS SCALED WITH THE NEW RISK");
      for(int v = 0; v < 4; v++)
      {
         const Acc &a0 = mode == 0 ? same0[v] : scal0[v], &a1 = mode == 0 ? same1[v] : scal1[v];
         std::printf("    stop +%.2f ATR | older %6d  %4.1f%% won  %+6.3f$ (%.3f) | newer %6d  %4.1f%% won  %+6.3f$ (%.3f)\n", bufs[v],
                     a0.n, a0.win(), a0.mean(), a0.se(), a1.n, a1.win(), a1.mean(), a1.se());
      }
   }
   return 0;
}
