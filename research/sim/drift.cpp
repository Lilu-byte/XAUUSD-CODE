// Does trading WITH gold's daily trend, and holding long enough to ride it, turn the intraday strategies positive?
// Daily regime: the last completed D1 close above (below) its 200-day mean = up (down).
// Every strategy is traded only in the regime's direction ("both") or only long in an up regime ("long only"),
// with the four standard exits and two slower ones:
//   Rider   close a third at 1R, stop to entry, trail the rest 3 ATR, time stop 5 days
//   Swing   classic exit (half at 1R, runner to 2.5R, 2 ATR trail) with a 3-day time stop instead of 8 hours
// One trade at a time per strategy/exit; older 60% vs newest 40% of the file.
//
// Build:  g++ -std=c++17 -O2 -o drift research/sim/drift.cpp
// Run:    ./drift BASE.csv HIGHER.csv D1.csv [cost=0.35]

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
   void add(double r) { n++; s += r; s2 += r * r; if(r > 0) w++; }
   double mean() const { return n ? s / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mean(); return std::sqrt(std::max(0.0, s2 / n - m * m) / n); }
   double win() const { return n ? 100.0 * w / n : 0.0; }
};

int main(int argc, char **argv)
{
   if(argc < 4) { std::printf("usage: drift BASE.csv HIGHER.csv D1.csv [cost]\n"); return 2; }
   std::vector<MqlRates> base, htf, d1;
   if(!load_csv(argv[1], base) || !load_csv(argv[2], htf) || !load_csv(argv[3], d1)) return 2;
   base.pop_back(); htf.pop_back(); d1.pop_back();
   CXauEngine E;
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(base); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.cfg.cost_price = argc > 4 ? std::atof(argv[4]) : 0.35;
   E.SetBase(base, (int)base.size()); E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) return 2;
   // daily regime for every base bar: last D1 bar that closed before the base bar opened
   std::vector<int> reg(E.n, 0);
   {
      std::vector<double> sma(d1.size(), 0.0);
      double s = 0;
      for(size_t k = 0; k < d1.size(); k++)
      {
         s += d1[k].close;
         if(k >= 200) s -= d1[k - 200].close;
         if(k >= 199) sma[k] = s / 200.0;
      }
      size_t k = 0;
      for(int i = 0; i < E.n; i++)
      {
         while(k + 1 < d1.size() && d1[k + 1].time + 86400 <= base[i].time) k++;
         if(d1[k].time + 86400 <= base[i].time && sma[k] > 0) reg[i] = (d1[k].close > sma[k]) ? 1 : -1;
      }
   }
   const int bpd = std::max(1, 86400 / E.cfg.base_sec);
   const int NX = XP_COUNT + 2;
   XExit xs[NX];
   std::string xn[NX];
   for(int p = 0; p < XP_COUNT; p++) { XMakeExit(p, E.cfg, xs[p]); xn[p] = XExitName(p); }
   XMakeExit(XP_CLASSIC, E.cfg, xs[4]); xs[4].tp1_r = 1.0; xs[4].part = 0.33; xs[4].tp2_r = 0.0; xs[4].trail_atr = 3.0; xs[4].max_hold = std::max(8, 5 * bpd); xn[4] = "Rider (1/3 at 1R, trail 3 ATR, 5 days)";
   XMakeExit(XP_CLASSIC, E.cfg, xs[5]); xs[5].max_hold = std::max(8, 3 * bpd); xn[5] = "Swing (classic, 3 days)";
   const int split = E.cfg.warmup + (int)(0.6 * (E.n - E.cfg.warmup));
   int up = 0, dn = 0;
   for(int i = E.cfg.warmup; i < E.n; i++) { if(reg[i] > 0) up++; else if(reg[i] < 0) dn++; }
   std::printf("== TREND-ALIGNED strategies: %s (%d bars), cost %.2f, guard %.0f | daily regime up %.0f%% / down %.0f%% of bars ==\n",
               argv[1], E.n, E.cfg.cost_price, E.cfg.min_stop_cost, 100.0 * up / (E.n - E.cfg.warmup), 100.0 * dn / (E.n - E.cfg.warmup));
   std::printf("   older part %s .. %s | newer part .. %s\n", TimeToString(E.m_t[E.cfg.warmup]).c_str(), TimeToString(E.m_t[split]).c_str(), TimeToString(E.m_t[E.n - 1]).c_str());
   for(int mode = 0; mode < 3; mode++)
   {
      const char *mname = mode == 0 ? "no daily filter" : (mode == 1 ? "with the daily regime (both sides)" : "long only, daily regime up");
      std::printf("\n  %s\n    %-26s %-40s | %-30s | %-30s\n", mname, "strategy", "exit", "older: n  won  avgR (se)", "newer: n  won  avgR (se)");
      for(int st = 0; st < XS_COUNT; st++)
         for(int p = 0; p < NX; p++)
         {
            Acc a0, a1;
            int busy = -1;
            for(int i = E.cfg.warmup + 10; i < E.n - 2; i++)
            {
               if(i <= busy) continue;
               const int d = E.StrategyDir(st, i);
               if(d == 0) continue;
               if(mode == 1 && reg[i] != d) continue;
               if(mode == 2 && !(d > 0 && reg[i] > 0)) continue;
               XSignal sg;
               if(!E.StrategySignal(st, i, xs[p], sg)) continue;
               XTradeResult r;
               if(!E.SimulateTradeEx(i, sg.dir, sg.sl, E.n - 2, xs[p], r)) continue;
               busy = r.exit_idx;
               if(!r.closed) continue;
               (i < split ? a0 : a1).add(r.r_net);
            }
            if(a0.n + a1.n < 40) continue;
            const bool both = a0.n >= 20 && a1.n >= 20 && a0.mean() - a0.se() > 0 && a1.mean() - a1.se() > 0;
            std::printf("    %-26s %-40s | %5d %5.1f%% %+7.3f (%.3f) | %5d %5.1f%% %+7.3f (%.3f)%s\n", XStratName(st).c_str(), xn[p].c_str(),
                        a0.n, a0.win(), a0.mean(), a0.se(), a1.n, a1.win(), a1.mean(), a1.se(), both ? "  << positive in both" : "");
         }
   }
   return 0;
}
