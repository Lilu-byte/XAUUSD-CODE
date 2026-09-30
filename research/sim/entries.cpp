// More precise entries on short charts: does a better entry price or a confirmation candle improve the same signals?
// Every signal of all 32 strategy/exit combinations is simulated on its own, with:
//   MARKET      the next bar's open (what the EA does now)
//   LIMIT k     a limit order k ATR better than the signal close (buy lower / sell higher), valid 3 bars; unfilled = no trade
//   CONFIRM     wait for the next candle to close in the trade's direction, enter at the open after it
// Same stop price, targets in R from the actual entry (as the EA places them), cost 0.35, cost guard on the actual stop.
// Older 60% / newest 40% of each file. "per signal" = average R per signal including the ones that were not filled,
// the fair comparison of how much each rule earns from the same opportunities.
//
// Build:  g++ -std=c++17 -O2 -o entries research/sim/entries.cpp
// Run:    ./entries BASE.csv HIGHER.csv [aggregate_to_seconds=0]

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

struct Acc
{
   int sig = 0, n = 0, w = 0; double s = 0, s2 = 0;
   void add(double r) { n++; s += r; s2 += r * r; if(r > 0) w++; }
   double mean() const { return n ? s / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mean(); return std::sqrt(std::max(0.0, s2 / n - m * m) / n); }
   double win() const { return n ? 100.0 * w / n : 0.0; }
   double per_sig() const { return sig ? s / sig : 0.0; }
};

int main(int argc, char **argv)
{
   if(argc < 3) { std::printf("usage: entries BASE.csv HIGHER.csv [aggregate_to_seconds]\n"); return 2; }
   std::vector<MqlRates> base, htf;
   if(!load_csv(argv[1], base) || !load_csv(argv[2], htf)) return 2;
   base.pop_back(); htf.pop_back();
   const int agg = argc > 3 ? std::atoi(argv[3]) : 0;
   if(agg > 0) { base = aggregate(base, agg); base.pop_back(); }
   CXauEngine E;
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(base); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1; E.cfg.cost_price = 0.35;
   E.SetBase(base, (int)base.size()); E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) return 2;
   const int split = E.cfg.warmup + (int)(0.6 * (E.n - E.cfg.warmup));
   const int NV = 5;
   const char *vn[NV] = {"MARKET (next open)", "LIMIT 0.10 ATR better", "LIMIT 0.25 ATR better", "LIMIT 0.40 ATR better", "CONFIRM (next candle agrees)"};
   const double ks[NV] = {0, 0.10, 0.25, 0.40, 0};
   Acc all0[NV], all1[NV];
   Acc fam0[3][NV], fam1[3][NV];
   const char *fn[3] = {"dips (RSI-2, Double-7, weak close)", "breakouts (ORB, squeeze)", "others (confluence, stop-hunt, pullback)"};
   const double guard = E.cfg.min_stop_cost * E.cfg.cost_price;
   for(int c = 0; c < XLAB_CELLS; c++)
   {
      const int st = c / XP_COUNT;
      const int fam = (st == XS_DIP || st == XS_DOUBLE7 || st == XS_IBS) ? 0 : ((st == XS_ORB || st == XS_SQUEEZE) ? 1 : 2);
      XExit x; XMakeExit(c % XP_COUNT, E.cfg, x);
      for(int i = E.cfg.warmup + 10; i < E.n - 6; i++)
      {
         if(E.StrategyDir(st, i) == 0) continue;
         XSignal sg;
         if(!E.StrategySignal(st, i, x, sg)) continue;
         const int d = sg.dir;
         const double a = E.m_atr[i];
         for(int v = 0; v < NV; v++)
         {
            Acc &A = (i < split) ? all0[v] : all1[v];
            Acc &F = (i < split) ? fam0[fam][v] : fam1[fam][v];
            A.sig++; F.sig++;
            XTradeResult r;
            bool ok = false;
            if(v == 0) ok = E.SimulateTradeEx(i, d, sg.sl, E.n - 2, x, r);
            else if(v == 4)
            {
               const int k = i + 1;                                   // confirmation candle
               const bool agree = (d > 0) ? (E.m_c[k] > E.m_o[k]) : (E.m_c[k] < E.m_o[k]);
               const double risk = (d > 0) ? E.m_o[k + 1] - sg.sl : sg.sl - E.m_o[k + 1];
               if(agree && risk >= guard && risk >= 0.4 * a && risk <= x.sl_max_atr * a * 1.3)
                  ok = E.SimulateTradeAt(k, k + 1, E.m_o[k + 1], false, d, sg.sl, E.n - 2, x, r);
            }
            else
            {
               const double lim = E.m_c[i] - d * ks[v] * a;
               for(int f = i + 1; f <= i + 3 && f < E.n - 1; f++)
               {
                  const bool opened_through = (d > 0) ? (E.m_o[f] <= lim) : (E.m_o[f] >= lim);
                  const bool touched = (d > 0) ? (E.m_l[f] <= lim) : (E.m_h[f] >= lim);
                  if(!touched) continue;
                  const double px = opened_through ? E.m_o[f] : lim;
                  const double risk = (d > 0) ? px - sg.sl : sg.sl - px;
                  if(risk >= guard && risk > 0.0)
                     ok = E.SimulateTradeAt(i, f, px, !opened_through, d, sg.sl, E.n - 2, x, r);
                  break;
               }
            }
            if(ok && r.closed) { A.add(r.r_net); F.add(r.r_net); }
         }
      }
   }
   std::printf("== PRECISION ENTRIES: %s%s (%d bars of %d s), cost 0.35, guard 20 ==\n", argv[1], agg ? " aggregated" : "", E.n, E.cfg.base_sec);
   std::printf("   older part %s .. %s | newer part .. %s\n", TimeToString(E.m_t[E.cfg.warmup]).c_str(), TimeToString(E.m_t[split]).c_str(), TimeToString(E.m_t[E.n - 1]).c_str());
   auto show = [&](const char *title, Acc *a0, Acc *a1) {
      std::printf("\n  %s\n    %-30s | %-40s | %-40s\n", title, "entry", "older: filled  won  avgR (se)  per signal", "newer: filled  won  avgR (se)  per signal");
      for(int v = 0; v < NV; v++)
         std::printf("    %-30s | %5.1f%% %5.1f%% %+7.3f (%.3f) %+7.3f | %5.1f%% %5.1f%% %+7.3f (%.3f) %+7.3f\n", vn[v],
                     a0[v].sig ? 100.0 * a0[v].n / a0[v].sig : 0.0, a0[v].win(), a0[v].mean(), a0[v].se(), a0[v].per_sig(),
                     a1[v].sig ? 100.0 * a1[v].n / a1[v].sig : 0.0, a1[v].win(), a1[v].mean(), a1[v].se(), a1[v].per_sig());
   };
   show("ALL 32 combinations", all0, all1);
   for(int f = 0; f < 3; f++) show(fn[f], fam0[f], fam1[f]);
   return 0;
}
