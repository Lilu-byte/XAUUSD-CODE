// Round 11: supply / demand zones and the three entry styles from the popular "different types of entries" picture,
// plus the volume-profile "point of control" magnet. Every rule below was fixed before the run.
//
// ZONE   a quiet base (1-3 bars, each no bigger than 1 ATR) followed by an impulse (1-3 bars in one direction that move
//        at least 2 ATR from the base). Rally after the base = DEMAND zone (buy), drop = SUPPLY zone (sell).
//        Zone = high/low of the base, 0.3-1.5 ATR tall, valid for 200 bars, traded at its FIRST return only.
// Entries (mirror for supply):
//   LIMIT    buy limit at the top of the zone (fills on the first touch)
//   ENGULF   after the touch, wait up to 6 bars for a bullish engulfing candle in the zone, buy at the next open
//   RETEST   after the touch, price must close above the last local high (break of structure) within 12 bars;
//            then buy limit back at that broken level within 12 bars (the "pullback structure" entry)
// Every trade: stop 0.1 ATR beyond the zone (or beyond the lowest low since the touch for RETEST), target 2R, at most
// 48 bars. Worst case when stop and target are inside the same bar; a limit fill cannot also reach its target in the
// bar it filled. Gross R = before costs (is the direction right at all?), net R = after 0.35 per trade.
// Also each entry with the daily trend only (demand while the daily close is above its 200-day mean, supply below).
//
// POC    yesterday's volume-profile point of control (price with the most tick volume). When price is at least one
//        hourly ATR away from it and has not touched it today, trade back toward it: target = the POC, stop = the
//        same distance on the other side (1:1), out at the end of the day. A magnet would win clearly more than 50%.
//
// Older 60% / newer 40% of each file.
// Build:  g++ -std=c++17 -O2 -o zones research/sim/zones.cpp
// Run:    ./zones BASE.csv HIGHER.csv D1.csv [cost=0.35]

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
   int n = 0, w = 0; double g = 0, s = 0, s2 = 0;
   void add(double gross, double net) { n++; g += gross; s += net; s2 += net * net; if(net > 0) w++; }
   double mean() const { return n ? s / n : 0.0; }
   double gmean() const { return n ? g / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mean(); return std::sqrt(std::max(0.0, s2 / n - m * m) / n); }
   double win() const { return n ? 100.0 * w / n : 0.0; }
};

static CXauEngine E;
static std::vector<MqlRates> B;
static double COST = 0.35;
static int SPLIT = 0;

// Bracket trade. Entry at price `px` in bar e; `limit_fill` = filled inside bar e by a limit order (the target cannot
// be reached in that bar, the stop can). Returns gross R; false if the trade is not possible.
static bool bracket(int e, int dir, double px, double stop, double target, int max_bars, bool limit_fill, double &gross_r, double &risk)
{
   risk = dir * (px - stop);
   if(risk <= 0.0 || e >= E.n) return false;
   for(int j = e; j < E.n && j < e + max_bars; j++)
   {
      const double adv = (dir > 0) ? B[j].low : B[j].high, fav = (dir > 0) ? B[j].high : B[j].low;
      if(dir * (adv - stop) <= 0)
      {
         const double fill = (j > e || !limit_fill) ? ((dir > 0) ? std::min(stop, B[j].open) : std::max(stop, B[j].open)) : stop;
         gross_r = dir * (fill - px) / risk;
         return true;
      }
      if(!(limit_fill && j == e) && dir * (fav - target) >= 0) { gross_r = dir * (target - px) / risk; return true; }
      gross_r = dir * (B[j].close - px) / risk;
   }
   return true;
}

static void print_row(const char *name, const Acc &a0, const Acc &a1, int signals0, int signals1)
{
   const bool both = a0.n >= 30 && a1.n >= 20 && a0.mean() - a0.se() > 0 && a1.mean() - a1.se() > 0;
   std::printf("    %-34s | %5d %4.0f%% fill %3.0f%% gross %+6.3f net %+6.3f (%.3f) | %5d %4.0f%% fill %3.0f%% gross %+6.3f net %+6.3f (%.3f)%s\n", name,
               a0.n, a0.win(), signals0 ? 100.0 * a0.n / signals0 : 0.0, a0.gmean(), a0.mean(), a0.se(),
               a1.n, a1.win(), signals1 ? 100.0 * a1.n / signals1 : 0.0, a1.gmean(), a1.mean(), a1.se(), both ? "  << positive in both" : "");
}

int main(int argc, char **argv)
{
   if(argc < 4) { std::printf("usage: zones BASE.csv HIGHER.csv D1.csv [cost]\n"); return 2; }
   std::vector<MqlRates> htf, d1;
   if(!load_csv(argv[1], B) || !load_csv(argv[2], htf) || !load_csv(argv[3], d1)) return 2;
   B.pop_back(); htf.pop_back(); d1.pop_back();
   if(argc > 4) COST = std::atof(argv[4]);
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(B); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.cfg.d1_sma = 200;
   E.SetBase(B, (int)B.size()); E.SetHTF(htf, (int)htf.size()); E.SetDaily(d1, (int)d1.size());
   if(!E.Compute()) return 2;
   SPLIT = E.cfg.warmup + (int)(0.6 * (E.n - E.cfg.warmup));
   std::printf("== SUPPLY/DEMAND ZONES and POC: %s (%d bars of %d s), cost %.2f ==\n", argv[1], E.n, E.cfg.base_sec, COST);
   std::printf("   older %s .. %s | newer .. %s\n", TimeToString(B[E.cfg.warmup].time).c_str(), TimeToString(B[SPLIT].time).c_str(),
               TimeToString(B[E.n - 1].time).c_str());
   std::printf("   columns: trades, won (net), fill = trades per zone, gross R per trade (before cost), net R per trade (se)\n");

   // ---------------- zones ----------------
   // [entry type][0 all, 1 with daily trend][half]
   Acc acc[3][2][2];
   int zones[2][2] = {{0, 0}, {0, 0}};
   int nz = 0, last_first = -1;
   for(int i = E.cfg.warmup + 5; i < E.n - 60; i++)
   {
      const double a = E.m_atr[i - 1];
      if(a <= 0) continue;
      // impulse of 1-3 bars ending at i, all in one direction
      int dir = 0, first = -1;
      for(int len = 1; len <= 3 && dir == 0; len++)
      {
         const int f = i - len + 1;
         const int d = (B[f].close > B[f].open) ? 1 : -1;
         bool same = true;
         for(int k = f; k <= i; k++) if(((B[k].close > B[k].open) ? 1 : -1) != d || B[k].close == B[k].open) { same = false; break; }
         if(!same) continue;
         if(d * (B[i].close - B[f].open) >= 2.0 * a) { dir = d; first = f; }
      }
      if(dir == 0 || first == last_first) continue;      // the same impulse seen again one bar later
      // base: 1-3 quiet bars right before the impulse
      int nb = 0;
      double top = -1e18, bot = 1e18;
      for(int k = first - 1; k >= first - 3 && k > 0; k--)
      {
         if(B[k].high - B[k].low > a) break;
         nb++; top = std::max(top, B[k].high); bot = std::min(bot, B[k].low);
      }
      if(nb == 0) continue;
      const double h = top - bot;
      if(h < 0.3 * a || h > 1.5 * a) continue;
      // the impulse must leave the zone: close beyond the far side by 1 ATR
      if(dir > 0 && B[i].close < top + a) continue;
      if(dir < 0 && B[i].close > bot - a) continue;
      nz++;
      last_first = first;
      const int half = (i < SPLIT) ? 0 : 1;
      const bool with_trend = (E.m_dreg[i] == dir);
      zones[0][half]++;
      if(with_trend) zones[1][half]++;
      const double prox = (dir > 0) ? top : bot, dist = (dir > 0) ? bot : top;   // proximal and distal lines
      // first return to the zone
      int t = -1;
      for(int k = i + 1; k < E.n - 50 && k <= i + 200; k++)
         if((dir > 0 && B[k].low <= prox) || (dir < 0 && B[k].high >= prox)) { t = k; break; }
      if(t < 0) continue;
      const double at = E.m_atr[t - 1];
      double gross, risk;
      auto record = [&](int type, double g, double rk) {
         const double net = g - COST / rk;
         acc[type][0][half].add(g, net);
         if(with_trend) acc[type][1][half].add(g, net);
      };
      // A. LIMIT at the proximal line
      {
         const double px = (dir > 0) ? std::min(prox, B[t].open) : std::max(prox, B[t].open);
         const double stop = dist - dir * 0.1 * at;
         if(dir * (px - stop) > 0.2 * at && bracket(t, dir, px, stop, px + dir * 2.0 * (dir * (px - stop)), 48, true, gross, risk)) record(0, gross, risk);
      }
      // B. ENGULF confirmation within 6 bars of the touch
      for(int j = std::max(t, 1); j <= t + 6 && j < E.n - 50; j++)
      {
         if(dir * (B[j].close - dist) < 0) break;                                  // closed through the zone: invalid
         const bool engulf = (dir > 0)
            ? (B[j].close > B[j].open && B[j - 1].close < B[j - 1].open && B[j].close >= B[j - 1].open && B[j].open <= B[j - 1].close)
            : (B[j].close < B[j].open && B[j - 1].close > B[j - 1].open && B[j].close <= B[j - 1].open && B[j].open >= B[j - 1].close);
         const double ext = (dir > 0) ? std::min(B[j].low, B[j - 1].low) : std::max(B[j].high, B[j - 1].high);
         if(!engulf || dir * (ext - prox) > 0.2 * at) continue;
         const double stop = ((dir > 0) ? std::min(dist, ext) : std::max(dist, ext)) - dir * 0.1 * at;
         const double px = B[j + 1].open;
         if(dir * (px - stop) > 0.2 * at && bracket(j + 1, dir, px, stop, px + dir * 2.0 * (dir * (px - stop)), 48, false, gross, risk)) record(1, gross, risk);
         break;
      }
      // C. RETEST of the broken local high (low for supply)
      {
         double L = (dir > 0) ? -1e18 : 1e18, ext = (dir > 0) ? 1e18 : -1e18;
         for(int k = std::max(0, t - 5); k <= t; k++) L = (dir > 0) ? std::max(L, B[k].high) : std::min(L, B[k].low);
         int brk = -1;
         for(int j = t; j <= t + 12 && j < E.n - 50; j++)
         {
            ext = (dir > 0) ? std::min(ext, B[j].low) : std::max(ext, B[j].high);
            if(dir * (B[j].close - dist) < 0) break;
            if(j > t && dir * (B[j].close - L) > 0) { brk = j; break; }
         }
         if(brk > 0)
            for(int q = brk + 1; q <= brk + 12 && q < E.n - 50; q++)
            {
               if((dir > 0 && B[q].low <= L) || (dir < 0 && B[q].high >= L))
               {
                  const double px = (dir > 0) ? std::min(L, B[q].open) : std::max(L, B[q].open);
                  const double stop = ext - dir * 0.1 * at;
                  if(dir * (px - stop) > 0.2 * at && bracket(q, dir, px, stop, px + dir * 2.0 * (dir * (px - stop)), 48, true, gross, risk)) record(2, gross, risk);
                  break;
               }
            }
      }
   }
   std::printf("\n  ZONES: %d found (older %d, newer %d; with the daily trend %d / %d)\n", nz, zones[0][0], zones[0][1], zones[1][0], zones[1][1]);
   std::printf("    %-34s | %-60s | %-60s\n", "entry", "older", "newer");
   const char *names[3] = {"LIMIT at the zone", "ENGULFING confirmation", "RETEST after a break of structure"};
   for(int ty = 0; ty < 3; ty++)
   {
      print_row(names[ty], acc[ty][0][0], acc[ty][0][1], zones[0][0], zones[0][1]);
      char nm[64];
      std::snprintf(nm, sizeof nm, "  same, with the daily trend only");
      print_row(nm, acc[ty][1][0], acc[ty][1][1], zones[1][0], zones[1][1]);
   }

   // ---------------- POC magnet ----------------
   if(E.cfg.base_sec <= 3600)
   {
      Acc p[2];
      int days = 0;
      int i = E.cfg.warmup + 1;
      double poc_prev = 0.0;
      while(i < E.n - 2)
      {
         // one server day [i, j)
         const long long d = B[i].time / 86400;
         int j = i;
         while(j < E.n && B[j].time / 86400 == d) j++;
         // trade today toward yesterday's POC
         if(poc_prev > 0.0)
         {
            bool touched = false;
            for(int k = i; k < j - 1; k++)
            {
               if(B[k].low <= poc_prev && B[k].high >= poc_prev) { touched = true; break; }
               const int sm = (int)((B[k].time % 86400) / 60);
               if(sm < 3 * 60 || sm > 20 * 60) continue;
               const double ah = E.m_atr[k] * std::sqrt(3600.0 / E.cfg.base_sec);
               const double dist = std::fabs(B[k].close - poc_prev);
               if(dist < ah) continue;
               const int dir = (poc_prev > B[k].close) ? 1 : -1;
               const double px = B[k + 1].open;
               const double stop = px - dir * dist;
               double g, rk;
               if(bracket(k + 1, dir, px, stop, poc_prev, j - (k + 1), false, g, rk) && rk > 0)
               {
                  p[(k < SPLIT) ? 0 : 1].add(g, g - COST / rk);
                  days++;
               }
               break;
            }
            (void)touched;
         }
         // yesterday's POC for tomorrow: tick volume spread evenly over each bar's range, bins of 0.25 ATR
         double lo = 1e18, hi = -1e18;
         for(int k = i; k < j; k++) { lo = std::min(lo, B[k].low); hi = std::max(hi, B[k].high); }
         const double bin = std::max(0.01, 0.25 * E.m_atr[j - 1]);
         const int nb = std::min(2000, (int)((hi - lo) / bin) + 1);
         std::vector<double> vol(nb, 0.0);
         for(int k = i; k < j; k++)
         {
            const int b0 = (int)((B[k].low - lo) / bin), b1 = std::min(nb - 1, (int)((B[k].high - lo) / bin));
            for(int b = b0; b <= b1; b++) vol[b] += (double)B[k].tick_volume / (b1 - b0 + 1);
         }
         int best = 0;
         for(int b = 1; b < nb; b++) if(vol[b] > vol[best]) best = b;
         poc_prev = (j - i >= 6) ? lo + (best + 0.5) * bin : 0.0;
         i = j;
      }
      std::printf("\n  POC: trade back to yesterday's point of control (1:1, first chance of the day, %d days)\n", days);
      print_row("toward yesterday's POC", p[0], p[1], 0, 0);
   }
   return 0;
}
