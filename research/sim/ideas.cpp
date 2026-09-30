// Idea screen on the user's real XAUUSD history (files written by MQL5/Scripts/XAU_DataExport.mq5).
//
// Every idea below was written down BEFORE this program was first run on the data, and each file is split in two:
//   discovery = the older 60% of the bars, holdout = the newest 40%.
// An idea only counts if it helps in BOTH halves (and on more than one timeframe). Everything is printed,
// including the ideas that failed, so the selection itself is visible.
//
// Build:  g++ -std=c++17 -O2 -o ideas research/sim/ideas.cpp
// Run:    ./ideas BASE.csv HIGHER_TF.csv [gmt_winter_hours=2] [dst=1]
// Cost 0.30 per trade and the cost guard switched off, exactly as when these ideas were first screened
// (docs/REAL_DATA.md section 7). The adopted guard was then re-tested inside the full EA replay at 0.35.

#include "../mock/mql5_mock.h"
#include "../../src/XAU_Core.mqh"
#include "../../src/XAU_Platform.mqh"

#include <cstring>
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

// one simulated signal (signals are simulated independently here; overlapping is allowed for screening)
struct Sig
{
   int cell, i, dir;
   double r, risk;
   bool win;
};

struct Acc
{
   int n = 0, w = 0; double s = 0, s2 = 0;
   void add(double r) { n++; s += r; s2 += r * r; if(r > 0) w++; }
   double mean() const { return n ? s / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mean(); return std::sqrt(std::max(0.0, s2 / n - m * m) / n); }
   double win() const { return n ? 100.0 * w / n : 0.0; }
};

static CXauEngine E;
static int g_bs = 3600, g_split = 0, g_bpd = 24;
static const double COST = 0.30;

static double hour_entry(int i)
{
   double h = E.m_hour[i] + g_bs / 3600.0;
   if(h >= 24.0) h -= 24.0;
   return h;
}
static int dow(int i) { return XWeekdayGmt(E.m_t[i], XOffsetAt(E.cfg, E.m_t[i])); }
static double mom(int i, int bars) { return (i - bars >= 0) ? E.m_c[i] - E.m_c[i - bars] : 0.0; }

typedef std::function<bool(const Sig &)> Pred;
struct Filter { const char *name; Pred keep; };

static void screen(const std::vector<Sig> &all, const std::vector<Filter> &flt, const char *title, std::function<bool(int)> cell_ok)
{
   std::printf("\n  %s\n", title);
   std::printf("    %-44s | %-34s | %-34s | kept\n", "filter", "discovery: n  win%  avgR (se)", "holdout: n  win%  avgR (se)");
   Acc b0, b1;
   for(const Sig &s : all) { if(!cell_ok(s.cell)) continue; (s.i < g_split ? b0 : b1).add(s.r); }
   for(const Filter &f : flt)
   {
      Acc a0, a1;
      for(const Sig &s : all) { if(!cell_ok(s.cell) || !f.keep(s)) continue; (s.i < g_split ? a0 : a1).add(s.r); }
      const double d0 = a0.mean() - b0.mean(), d1 = a1.mean() - b1.mean();
      const bool both = (a0.n >= 30 && a1.n >= 20 && d0 > 0.0 && d1 > 0.0);
      std::printf("    %-44s | %6d %5.1f %+7.3f (%.3f) | %6d %5.1f %+7.3f (%.3f) | %3.0f%% %s\n", f.name,
                  a0.n, a0.win(), a0.mean(), a0.se(), a1.n, a1.win(), a1.mean(), a1.se(),
                  (b0.n + b1.n) ? 100.0 * (a0.n + a1.n) / (b0.n + b1.n) : 0.0,
                  both ? (d0 > 0.02 && d1 > 0.02 ? "<< helps in both halves" : "< slightly better in both") : "");
   }
}

// A plain time-based rule: enter at the open of GMT hour h_in in direction dir, exit at the open of GMT hour h_out
// (same or next day). Returns net R using a stop of 1.5 ATR as the unit (no stop is placed; this is a drift test).
static void session_drift(const std::vector<MqlRates> &b)
{
   if(g_bs > 3600) return;
   std::printf("\n  SESSION DRIFT: average close-open move per base bar by GMT hour, in ATR, discovery vs holdout\n");
   std::printf("    hour | disc: n  meanATR t    up%% | hold: n  meanATR t    up%%\n");
   double sum0[24] = {0}, ss0[24] = {0}, sum1[24] = {0}, ss1[24] = {0};
   int n0[24] = {0}, n1[24] = {0}, u0[24] = {0}, u1[24] = {0};
   // group base bars by GMT clock hour; per hour the move is close - open summed over the bars of that hour
   for(int i = E.cfg.warmup; i < E.n - 1; i++)
   {
      const int h = (int)E.m_hour[i];
      if(h < 0 || h > 23) continue;
      const double a = E.m_atr[i] > 0 ? E.m_atr[i] : 1.0;
      const double mv = (b[i].close - b[i].open) / a;
      if(i < g_split) { sum0[h] += mv; ss0[h] += mv * mv; n0[h]++; if(mv > 0) u0[h]++; }
      else { sum1[h] += mv; ss1[h] += mv * mv; n1[h]++; if(mv > 0) u1[h]++; }
   }
   for(int h = 0; h < 24; h++)
   {
      if(n0[h] < 50 || n1[h] < 50) continue;
      const double m0 = sum0[h] / n0[h], m1 = sum1[h] / n1[h];
      const double t0 = m0 / std::sqrt(std::max(1e-12, ss0[h] / n0[h] - m0 * m0) / n0[h]);
      const double t1 = m1 / std::sqrt(std::max(1e-12, ss1[h] / n1[h] - m1 * m1) / n1[h]);
      std::printf("    %02d   | %6d %+6.3f %+5.1f %4.1f | %6d %+6.3f %+5.1f %4.1f %s\n", h, n0[h], m0, t0, 100.0 * u0[h] / n0[h],
                  n1[h], m1, t1, 100.0 * u1[h] / n1[h], (t0 > 2 && t1 > 2) ? "<< up in both" : ((t0 < -2 && t1 < -2) ? "<< down in both" : ""));
   }
}

// New entry rule candidates, simulated through the engine's own trade simulator (same costs, same fills).
typedef std::function<int(int)> Entry;
static void new_rules(const std::vector<std::pair<const char *, Entry>> &rules)
{
   std::printf("\n  NEW ENTRY RULES (one trade at a time, engine simulator, cost %.2f per trade)\n", COST);
   std::printf("    %-46s %-18s | %-30s | %-30s\n", "rule", "exit", "discovery: n  win%  avgR", "holdout: n  win%  avgR");
   for(const auto &ru : rules)
   {
      for(int p = 0; p < XP_COUNT; p++)
      {
         XExit x; XMakeExit(p, E.cfg, x);
         Acc a0, a1;
         int busy = -1;
         for(int i = E.cfg.warmup + 30; i < E.n - 2; i++)
         {
            if(i <= busy) continue;
            const int d = ru.second(i);
            if(d == 0) continue;
            XSignal sg;
            sg.Reset();
            if(!E.BuildPlanEx(i, d, sg, x.sl_min_atr, x.sl_max_atr, x.tp1_r, (x.tp2_r > 0.0) ? x.tp2_r : ((x.part >= 0.999) ? x.tp1_r : 0.0))) continue;
            XTradeResult r;
            if(!E.SimulateTradeEx(i, d, sg.sl, E.n - 2, x, r)) continue;
            busy = r.exit_idx;
            if(!r.closed) continue;
            (i < g_split ? a0 : a1).add(r.r_net);
         }
         std::printf("    %-46s %-18s | %6d %5.1f %+7.3f (%.3f) | %6d %5.1f %+7.3f (%.3f) %s\n", ru.first, XExitName(p).c_str(),
                     a0.n, a0.win(), a0.mean(), a0.se(), a1.n, a1.win(), a1.mean(), a1.se(),
                     (a0.n >= 30 && a1.n >= 20 && a0.mean() - a0.se() > 0 && a1.mean() - a1.se() > 0) ? "<< positive in both" : "");
      }
   }
}

int main(int argc, char **argv)
{
   if(argc < 3) { std::printf("usage: ideas BASE.csv HIGHER.csv [gmt_winter_hours] [dst]\n"); return 2; }
   std::vector<MqlRates> base, htf;
   if(!load_csv(argv[1], base) || !load_csv(argv[2], htf)) { std::printf("cannot read input\n"); return 2; }
   base.pop_back(); htf.pop_back();
   g_bs = bar_seconds(base);
   g_bpd = std::max(1, 86400 / g_bs);
   E.cfg.Defaults();
   E.cfg.base_sec = g_bs; E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = (int)((argc > 3 ? std::atof(argv[3]) : 2.0) * 3600);
   E.cfg.dst_mode = argc > 4 ? std::atoi(argv[4]) : 1;
   E.cfg.cost_price = COST;
   E.cfg.min_stop_cost = 0.0;        // the screen starts from every signal: the cost guard is idea 17 itself
   E.SetBase(base, (int)base.size()); E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) { std::printf("compute failed\n"); return 2; }
   g_split = E.cfg.warmup + (int)(0.6 * (E.n - E.cfg.warmup));
   std::printf("== IDEA SCREEN: %s (%d bars of %d s) ==\n", argv[1], E.n, g_bs);
   std::printf("   discovery %s .. %s | holdout %s .. %s\n", TimeToString(E.m_t[E.cfg.warmup]).c_str(), TimeToString(E.m_t[g_split - 1]).c_str(),
               TimeToString(E.m_t[g_split]).c_str(), TimeToString(E.m_t[E.n - 1]).c_str());

   // all signals of all 32 cells, simulated independently
   std::vector<Sig> all;
   for(int c = 0; c < XLAB_CELLS; c++)
   {
      XExit x; XMakeExit(c % XP_COUNT, E.cfg, x);
      for(int i = E.cfg.warmup + 10; i < E.n - 2; i++)
      {
         if(E.StrategyDir(c / XP_COUNT, i) == 0) continue;
         XSignal sg;
         if(!E.StrategySignal(c / XP_COUNT, i, x, sg)) continue;
         XTradeResult r;
         if(!E.SimulateTradeEx(i, sg.dir, sg.sl, E.n - 2, x, r) || !r.closed) continue;
         Sig s; s.cell = c; s.i = i; s.dir = sg.dir; s.r = r.r_net; s.risk = r.risk; s.win = r.r_net > 0;
         all.push_back(s);
      }
   }

   const int D = g_bpd;
   std::vector<Filter> flt = {
      {"(none: all signals)",                       [](const Sig &) { return true; }},
      {"1  buys only",                               [](const Sig &s) { return s.dir > 0; }},
      {"2  sells only",                              [](const Sig &s) { return s.dir < 0; }},
      {"3  higher timeframe agrees (not just neutral)", [](const Sig &s) { return E.m_bias[s.i] * s.dir > 0; }},
      {"4  calm: ATR below its reference",           [](const Sig &s) { return E.m_atrref[s.i] > 0 && E.m_atr[s.i] < E.m_atrref[s.i]; }},
      {"5  busy: ATR above its reference",           [](const Sig &s) { return E.m_atrref[s.i] > 0 && E.m_atr[s.i] >= E.m_atrref[s.i]; }},
      {"6  day range used < 60%",                     [](const Sig &s) { return E.m_adru[s.i] < 0.6; }},
      {"7  day range used >= 60%",                    [](const Sig &s) { return E.m_adru[s.i] >= 0.6; }},
      {"8  trending (efficiency ratio >= 0.3)",       [](const Sig &s) { return E.m_er[s.i] >= 0.3; }},
      {"9  choppy (efficiency ratio < 0.3)",          [](const Sig &s) { return E.m_er[s.i] < 0.3; }},
      {"10 entry 07-12 GMT (London)",                 [](const Sig &s) { const double h = hour_entry(s.i); return h >= 7 && h < 12; }},
      {"11 entry 12-17 GMT (London/New York overlap)", [](const Sig &s) { const double h = hour_entry(s.i); return h >= 12 && h < 17; }},
      {"12 entry 17-21 GMT (New York afternoon)",     [](const Sig &s) { const double h = hour_entry(s.i); return h >= 17 && h < 21; }},
      {"13 not Monday",                               [](const Sig &s) { return dow(s.i) != 1; }},
      {"14 not Friday",                               [](const Sig &s) { return dow(s.i) != 5; }},
      {"15 volume spike on the signal bar",           [](const Sig &s) { return E.m_vavg[s.i] > 0 && E.m_v[s.i] >= 1.3 * E.m_vavg[s.i]; }},
      {"16 no volume spike",                          [](const Sig &s) { return !(E.m_vavg[s.i] > 0 && E.m_v[s.i] >= 1.3 * E.m_vavg[s.i]); }},
      {"17 cost <= 5% of the stop",                   [](const Sig &s) { return s.risk > 0 && COST / s.risk <= 0.05; }},
      {"18 cost > 5% of the stop",                    [](const Sig &s) { return s.risk > 0 && COST / s.risk > 0.05; }},
      {"19 5-day move agrees with the trade",         [D](const Sig &s) { return mom(s.i, 5 * D) * s.dir > 0; }},
      {"20 20-day move agrees with the trade",        [D](const Sig &s) { return mom(s.i, 20 * D) * s.dir > 0; }},
      {"21 1-day move against the trade (a real dip)", [D](const Sig &s) { return mom(s.i, D) * s.dir < 0; }},
      {"22 buys only AND 20-day move up",             [D](const Sig &s) { return s.dir > 0 && mom(s.i, 20 * D) > 0; }},
      // second stage, added after the first screen: the two filters that helped in both halves, combined
      {"23 (2nd stage) cost <= 5% AND entry 17-21 GMT", [](const Sig &s) { const double h = hour_entry(s.i); return s.risk > 0 && COST / s.risk <= 0.05 && h >= 17 && h < 21; }},
      {"24 (2nd stage) cost <= 5% AND NOT 17-21 GMT",   [](const Sig &s) { const double h = hour_entry(s.i); return s.risk > 0 && COST / s.risk <= 0.05 && !(h >= 17 && h < 21); }},
   };
   auto any = [](int) { return true; };
   screen(all, flt, "FILTERS over all 32 strategy/exit combinations (each signal simulated on its own)", any);
   screen(all, flt, "FILTERS on the dip strategies only (RSI-2, Double-7, Weak-close)",
          [](int c) { const int s = c / XP_COUNT; return s == XS_DIP || s == XS_DOUBLE7 || s == XS_IBS; });
   screen(all, flt, "FILTERS on the breakout strategies only (ORB, Squeeze)",
          [](int c) { const int s = c / XP_COUNT; return s == XS_ORB || s == XS_SQUEEZE; });

   // finer look: entry hour and cost share, by strategy family
   {
      const char *fam[3] = {"dips", "breakouts", "all"};
      for(int f = 0; f < 3; f++)
      {
         std::printf("\n  BY ENTRY HOUR (GMT), %s: discovery n / avgR | holdout n / avgR\n", fam[f]);
         for(int h0 = 0; h0 < 24; h0 += 2)
         {
            Acc a0, a1;
            for(const Sig &s : all)
            {
               const int st = s.cell / XP_COUNT;
               const bool dip = (st == XS_DIP || st == XS_DOUBLE7 || st == XS_IBS), bo = (st == XS_ORB || st == XS_SQUEEZE);
               if((f == 0 && !dip) || (f == 1 && !bo)) continue;
               const double h = hour_entry(s.i);
               if(h < h0 || h >= h0 + 2) continue;
               (s.i < g_split ? a0 : a1).add(s.r);
            }
            if(a0.n + a1.n < 50) continue;
            std::printf("    %02d-%02d | %6d %+7.3f | %6d %+7.3f\n", h0, h0 + 2, a0.n, a0.mean(), a1.n, a1.mean());
         }
      }
      std::printf("\n  BY COST SHARE OF THE STOP (cost / stop distance), all strategies: discovery n / win%% / avgR | holdout\n");
      const double edges[7] = {0.0, 0.02, 0.03, 0.05, 0.08, 0.12, 1e9};
      for(int k = 0; k < 6; k++)
      {
         Acc a0, a1;
         for(const Sig &s : all) { if(s.risk <= 0) continue; const double cs = COST / s.risk; if(cs < edges[k] || cs >= edges[k + 1]) continue; (s.i < g_split ? a0 : a1).add(s.r); }
         std::printf("    %4.0f%% - %4.0f%% | %6d %5.1f %+7.3f | %6d %5.1f %+7.3f   (gross of cost: %+7.3f | %+7.3f)\n", 100 * edges[k], std::min(100.0, 100 * edges[k + 1]),
                     a0.n, a0.win(), a0.mean(), a1.n, a1.win(), a1.mean(), a0.mean() + (edges[k] + std::min(0.2, edges[k + 1])) / 2, a1.mean() + (edges[k] + std::min(0.2, edges[k + 1])) / 2);
      }
   }
   session_drift(base);

   // new entry rules
   std::vector<std::pair<const char *, Entry>> rules = {
      {"A  prev-day high/low breakout close, with trend", [](int i) {
          if(E.m_pdh[i] <= 0) return 0;
          const int t = E.TrendDir(i);
          if(t > 0 && E.m_c[i] > E.m_pdh[i] && E.m_c[i - 1] <= E.m_pdh[i]) return 1;
          if(t < 0 && E.m_c[i] < E.m_pdl[i] && E.m_c[i - 1] >= E.m_pdl[i]) return -1;
          return 0; }},
      {"B  prev-day low sweep + close back inside, buy", [](int i) {
          if(E.m_pdl[i] <= 0) return 0;
          if(E.m_l[i] < E.m_pdl[i] && E.m_c[i] > E.m_pdl[i] && E.TrendDir(i) >= 0) return 1;
          if(E.m_h[i] > E.m_pdh[i] && E.m_c[i] < E.m_pdh[i] && E.TrendDir(i) <= 0) return -1;
          return 0; }},
      {"C  3 lower closes in uptrend (buy), mirror", [](int i) {
          const int t = E.TrendDir(i);
          if(t > 0 && E.m_c[i] < E.m_c[i - 1] && E.m_c[i - 1] < E.m_c[i - 2] && E.m_c[i - 2] < E.m_c[i - 3]) return 1;
          if(t < 0 && E.m_c[i] > E.m_c[i - 1] && E.m_c[i - 1] > E.m_c[i - 2] && E.m_c[i - 2] > E.m_c[i - 3]) return -1;
          return 0; }},
      {"D  close below lower Bollinger in uptrend", [](int i) {
          const int t = E.TrendDir(i);
          if(t > 0 && E.m_bbp[i] < 0.0) return 1;
          if(t < 0 && E.m_bbp[i] > 1.0) return -1;
          return 0; }},
      {"E  20-bar Donchian breakout with trend", [](int i) {
          const int t = E.TrendDir(i);
          if(t > 0 && E.m_c[i] > E.m_donh[i - 1] && E.m_c[i - 1] <= E.m_donh[i - 2]) return 1;
          if(t < 0 && E.m_c[i] < E.m_donl[i - 1] && E.m_c[i - 1] >= E.m_donl[i - 2]) return -1;
          return 0; }},
      {"F  touch of 50 EMA in trend, bullish close", [](int i) {
          const int t = E.TrendDir(i);
          if(t > 0 && E.m_l[i] <= E.m_ema2[i] && E.m_c[i] > E.m_ema2[i] && E.m_c[i] > E.m_o[i]) return 1;
          if(t < 0 && E.m_h[i] >= E.m_ema2[i] && E.m_c[i] < E.m_ema2[i] && E.m_c[i] < E.m_o[i]) return -1;
          return 0; }},
      {"G  RSI-2 dip, trend AND higher TF agree", [](int i) {
          if(E.TrendDir(i) > 0 && E.m_bias[i] > 0 && E.m_rsi2[i] < 10) return 1;
          if(E.TrendDir(i) < 0 && E.m_bias[i] < 0 && E.m_rsi2[i] > 90) return -1;
          return 0; }},
      {"H  weak close + day range used < 60%", [](int i) {
          const double rng = E.m_h[i] - E.m_l[i];
          if(rng <= 0 || rng < 0.5 * E.m_atr[i] || E.m_adru[i] >= 0.6) return 0;
          const double ibs = (E.m_c[i] - E.m_l[i]) / rng; const int t = E.TrendDir(i);
          if(t > 0 && ibs < 0.15 && E.m_c[i] < E.m_c[i - 1]) return 1;
          if(t < 0 && ibs > 0.85 && E.m_c[i] > E.m_c[i - 1]) return -1;
          return 0; }},
   };
   for(auto &r : rules) { Entry f = r.second; r.second = [f](int i) { return (E.FilterReason(i) == XR_OK) ? f(i) : 0; }; }
   new_rules(rules);
   return 0;
}
