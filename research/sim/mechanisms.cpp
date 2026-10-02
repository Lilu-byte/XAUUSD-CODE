// Round 10: structurally different mechanisms, not new settings on the same breakout.
// Every earlier strategy was "predict a direction from a price pattern, bracket it with a stop and a target".
// These change WHEN the market is held, WHAT is predicted, or WHO is on the other side:
//
//   CLOCK   time-of-day exposure: hold gold through the hours it has tended to rise (after the daily reopen:
//           Asian buyers) or short the hours it has tended to fall (New York). No pattern, a clock and a
//           catastrophic stop. Documented as "gold rises in Asia, falls in the West".
//   FIX     London benchmark fixes (10:30 and 15:00 London): flows into the auction
//   GAP     weekend gap: Monday's open vs Friday's close, fade back toward Friday's close
//   OVER    daily overreaction: what happens the day after a 2-sigma day
//   SEASON  month-of-year and day-of-week on 22 years of daily bars
//
// Every rule and window below was fixed before the run (hours are SERVER time; the server day opens at 01:00).
// Results: older 60% / newer 40% of the file, per year, in dollars per 0.01 lot (1 oz) after costs.
//
// Build:  g++ -std=c++17 -O2 -o mechanisms research/sim/mechanisms.cpp
// Run:    ./mechanisms BASE.csv HIGHER.csv D1.csv [cost=0.35] [swap_long_per_night=0.50] [swap_short_per_night=0.20]

#include "../mock/mql5_mock.h"
#include "../../src/XAU_Core.mqh"
#include "../../src/XAU_Platform.mqh"

#include <functional>
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
   int n = 0, w = 0; double s = 0, s2 = 0, peak = 0, eq = 0, dd = 0;
   void add(double x) { n++; s += x; s2 += x * x; if(x > 0) w++; eq += x; if(eq > peak) peak = eq; if(peak - eq > dd) dd = peak - eq; }
   double mean() const { return n ? s / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mean(); return std::sqrt(std::max(0.0, s2 / n - m * m) / n); }
   double win() const { return n ? 100.0 * w / n : 0.0; }
   double sharpe_yr(double per_year) const { if(n < 2) return 0; const double m = mean(); const double sd = std::sqrt(std::max(1e-12, s2 / n - m * m)); return m / sd * std::sqrt(per_year); }
};

static CXauEngine E;
static std::vector<MqlRates> B;
static double COST = 0.35, SWAP_L = 0.50, SWAP_S = 0.20;
static int SPLIT = 0;

static int server_min(int i) { return (int)((B[i].time % 86400) / 60); }   // minutes after server midnight
static int server_dow(int i) { return (int)(((B[i].time / 86400) + 4) % 7); } // 0 Sunday .. 6 Saturday
static int year_of(int i) { return XYearOfDays(B[i].time / 86400); }
static int month_of(long long t)
{
   const long z = (long)(t / 86400) + 719468;
   const long era = ((z >= 0) ? z : z - 146096) / 146097;
   const long doe = z - era * 146097;
   const long yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
   const long doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
   const long mp = (5 * doy + 2) / 153;
   return (int)((mp < 10) ? mp + 3 : mp - 9);
}

// Hold from the open of bar e for `hold_min` minutes (exit at the open of the first bar at or after that time,
// or the last bar of the session), with a catastrophic stop `stop_atr` x H1-equivalent ATR away (0 = none).
// Returns the result in price units per 1 oz, after cost and swap.
static bool hold_trade(int e, int dir, int hold_min, double stop_atr, double cost, double &pnl, int &exit_i)
{
   if(e <= 0 || e >= E.n - 1) return false;
   const double entry = B[e].open;
   const double a = E.m_atr[e - 1] * std::sqrt(3600.0 / E.cfg.base_sec);   // ATR scaled to one hour
   const double stop = (stop_atr > 0) ? entry - dir * stop_atr * a : 0.0;
   const long long t_end = B[e].time + hold_min * 60LL;
   const long long day0 = B[e].time / 86400;
   int nights = 0;
   for(int j = e; j < E.n; j++)
   {
      if(B[j].time / 86400 != day0 + nights) nights = (int)(B[j].time / 86400 - day0);   // crossed server midnight
      if(stop_atr > 0)
      {
         const double adverse = (dir > 0) ? B[j].low : B[j].high;
         if((dir > 0 && adverse <= stop) || (dir < 0 && adverse >= stop))
         {
            const double fill = (dir > 0) ? std::min(stop, B[j].open) : std::max(stop, B[j].open);
            pnl = dir * (fill - entry) - cost - nights * (dir > 0 ? SWAP_L : SWAP_S);
            exit_i = j;
            return true;
         }
      }
      if(j + 1 < E.n && (B[j + 1].time >= t_end || B[j + 1].time - B[j].time > 4 * 3600))
      {
         // exit at the next bar's open (the time is reached, or a long break follows: close before it)
         const bool brk = (B[j + 1].time - B[j].time > 4 * 3600);
         const double px = brk ? B[j].close : B[j + 1].open;
         const int ex = brk ? j : j + 1;
         const int n2 = (int)(B[ex].time / 86400 - day0);
         pnl = dir * (px - entry) - cost - n2 * (dir > 0 ? SWAP_L : SWAP_S);
         exit_i = ex;
         return true;
      }
   }
   return false;
}

static void print_acc(const char *name, const Acc &a0, const Acc &a1, double per_year)
{
   const bool both = a0.n >= 30 && a1.n >= 20 && a0.mean() - a0.se() > 0 && a1.mean() - a1.se() > 0;
   std::printf("    %-58s | %5d %5.1f%% %+7.3f (%.3f) Sh %+5.2f | %5d %5.1f%% %+7.3f (%.3f) Sh %+5.2f DD %6.0f%s\n", name,
               a0.n, a0.win(), a0.mean(), a0.se(), a0.sharpe_yr(per_year), a1.n, a1.win(), a1.mean(), a1.se(), a1.sharpe_yr(per_year), a1.dd,
               both ? "  << positive in both" : "");
}

int main(int argc, char **argv)
{
   if(argc < 4) { std::printf("usage: mechanisms BASE.csv HIGHER.csv D1.csv [cost] [swap_long] [swap_short]\n"); return 2; }
   std::vector<MqlRates> htf, d1;
   if(!load_csv(argv[1], B) || !load_csv(argv[2], htf) || !load_csv(argv[3], d1)) return 2;
   B.pop_back(); htf.pop_back(); d1.pop_back();
   if(argc > 4) COST = std::atof(argv[4]);
   if(argc > 5) SWAP_L = std::atof(argv[5]);
   if(argc > 6) SWAP_S = std::atof(argv[6]);
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(B); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.cfg.d1_sma = 200;
   E.SetBase(B, (int)B.size()); E.SetHTF(htf, (int)htf.size()); E.SetDaily(d1, (int)d1.size());
   if(!E.Compute()) return 2;
   SPLIT = E.cfg.warmup + (int)(0.6 * (E.n - E.cfg.warmup));
   const double bars_per_year = 252.0;
   std::printf("== NEW MECHANISMS: %s (%d bars of %d s) | cost %.2f, swap long %.2f / short %.2f per night (per 0.01 lot) ==\n", argv[1], E.n,
               E.cfg.base_sec, COST, SWAP_L, SWAP_S);
   std::printf("   older %s .. %s | newer .. %s | results in $ per 0.01 lot per trade, Sh = yearly Sharpe at one trade a day\n",
               TimeToString(B[E.cfg.warmup].time).c_str(), TimeToString(B[SPLIT].time).c_str(), TimeToString(B[E.n - 1].time).c_str());

   // ---------------- CLOCK -------------------------------------------------------------------------------
   std::printf("\n  CLOCK: hold gold at fixed server hours (server day opens 01:00), stop 3 x hourly ATR\n");
   std::printf("    %-58s | %-38s | %-38s\n", "rule", "older: n  won  $/trade (se)  Sharpe", "newer: n  won  $/trade (se)  Sharpe  maxDD$");
   struct ClockRule { const char *name; int dir; int start_min; int hold_min; int filter; double cost_extra; };
   // filter: 0 none, 1 daily trend up (long) / down (short), 2 skip Mondays
   const ClockRule rules[] = {
      {"LONG after the reopen 01:30-03:30", 1, 90, 120, 0, 0.10},
      {"LONG after the reopen 01:30-05:30", 1, 90, 240, 0, 0.10},
      {"LONG after the reopen 01:30-08:30 (to London)", 1, 90, 420, 0, 0.10},
      {"LONG after the reopen 02:00-06:00", 1, 120, 240, 0, 0.05},
      {"LONG 01:30-05:30, daily trend up only", 1, 90, 240, 1, 0.10},
      {"LONG 01:30-08:30, daily trend up only", 1, 90, 420, 1, 0.10},
      {"LONG through the break 23:30-03:30 (pays swap)", 1, 23 * 60 + 30, 240, 0, 0.0},
      {"LONG Asia 02:00-10:00 (to London open)", 1, 120, 480, 0, 0.05},
      {"SHORT New York 16:30-22:00 (US cash session)", -1, 16 * 60 + 30, 330, 0, 0.0},
      {"SHORT New York 16:30-22:00, daily trend down only", -1, 16 * 60 + 30, 330, 1, 0.0},
      {"SHORT London 10:00-15:00", -1, 10 * 60, 300, 0, 0.0},
      {"LONG London 10:00-15:00", 1, 10 * 60, 300, 0, 0.0},
      {"LONG late 20:00-23:30", 1, 20 * 60, 210, 0, 0.0},
   };
   for(const ClockRule &cr : rules)
   {
      Acc a0, a1;
      std::map<int, Acc> by_year;
      for(int i = E.cfg.warmup + 1; i < E.n - 2; i++)
      {
         const int sm = server_min(i), pm = server_min(i - 1);
         const bool day_change = (B[i].time / 86400 != B[i - 1].time / 86400);
         // first bar at or after the start minute of this server day
         if(!(sm >= cr.start_min && (pm < cr.start_min || day_change))) continue;
         if(sm - cr.start_min > 60) continue;                                   // data gap: skip the day
         const int dw = server_dow(i);
         if(dw == 0 || dw == 6) continue;
         if(cr.filter == 1 && E.m_dreg[i - 1] != cr.dir) continue;
         double pnl; int ex;
         if(!hold_trade(i, cr.dir, cr.hold_min, 3.0, COST + cr.cost_extra, pnl, ex)) continue;
         (i < SPLIT ? a0 : a1).add(pnl);
         by_year[year_of(i)].add(pnl);
      }
      print_acc(cr.name, a0, a1, bars_per_year);
      std::printf("      by year ($/trade):");
      for(auto &kv : by_year) std::printf(" %d %+.2f", kv.first, kv.second.mean());
      std::printf("\n");
   }

   // ---------------- FIX ---------------------------------------------------------------------------------
   // London fixes at 10:30 and 15:00 London time = 12:30 and 17:00 server (server = London + 2 all year on
   // New-York-close servers, except in the few weeks when US and UK daylight saving differ).
   std::printf("\n  FIX: 30 minutes before / after the London fixes (12:30 and 17:00 server); direction chosen on the older part\n");
   if(E.cfg.base_sec <= 1800)
   {
      const int fixes[2] = {12 * 60 + 30, 17 * 60};
      for(int f = 0; f < 2; f++)
         for(int side = 0; side < 2; side++)
         {
            const int start = fixes[f] - (side == 0 ? 30 : 0);
            Acc l0, l1;
            for(int i = E.cfg.warmup + 1; i < E.n - 2; i++)
            {
               const int sm = server_min(i), pm = server_min(i - 1);
               if(!(sm >= start && pm < start) || sm - start > 15) continue;
               const int dw = server_dow(i);
               if(dw == 0 || dw == 6) continue;
               double pnl; int ex;
               if(!hold_trade(i, 1, 30, 0.0, 0.0, pnl, ex)) continue;
               (i < SPLIT ? l0 : l1).add(pnl);
            }
            const int dir = (l0.mean() >= 0) ? 1 : -1;
            Acc t0, t1;
            for(int i = E.cfg.warmup + 1; i < E.n - 2; i++)
            {
               const int sm = server_min(i), pm = server_min(i - 1);
               if(!(sm >= start && pm < start) || sm - start > 15) continue;
               const int dw = server_dow(i);
               if(dw == 0 || dw == 6) continue;
               double pnl; int ex;
               if(!hold_trade(i, dir, 30, 0.0, COST, pnl, ex)) continue;
               (i < SPLIT ? t0 : t1).add(pnl);
            }
            char nm[96];
            std::snprintf(nm, sizeof nm, "%s the %s fix, %s (picked on older)", side == 0 ? "30 min BEFORE" : "30 min AFTER", f == 0 ? "AM" : "PM", dir > 0 ? "LONG" : "SHORT");
            print_acc(nm, t0, t1, bars_per_year);
         }
   }
   else std::printf("    (needs M30 or shorter bars)\n");

   // ---------------- GAP ---------------------------------------------------------------------------------
   std::printf("\n  GAP: Monday open vs Friday close; fade toward Friday's close (target = Friday close, stop = gap size beyond the open, 8 h)\n");
   {
      Acc g0, g1, f0, f1;
      int fills0 = 0, fills1 = 0, nn0 = 0, nn1 = 0;
      for(int i = E.cfg.warmup + 1; i < E.n - 2; i++)
      {
         if(B[i].time - B[i - 1].time < 36 * 3600) continue;                    // weekend (or holiday) break
         const double gap = B[i].open - B[i - 1].close;
         const double a = E.m_atr[i - 1] * std::sqrt(3600.0 / E.cfg.base_sec);
         if(std::fabs(gap) < 0.3 * a) continue;
         const int dir = (gap > 0) ? -1 : 1;
         const double entry = B[i].open, target = B[i - 1].close, stop = entry - dir * std::fabs(gap);
         double pnl = 0; bool done = false; bool filled = false;
         for(int j = i; j < E.n && B[j].time - B[i].time < 8 * 3600; j++)
         {
            const double adv = (dir > 0) ? B[j].low : B[j].high;
            const double fav = (dir > 0) ? B[j].high : B[j].low;
            if((dir > 0 && adv <= stop) || (dir < 0 && adv >= stop)) { pnl = -std::fabs(gap); done = true; break; }
            if((dir > 0 && fav >= target) || (dir < 0 && fav <= target)) { pnl = std::fabs(gap); done = true; filled = true; break; }
            pnl = dir * (B[j].close - entry);
         }
         (void)done;
         pnl -= COST + 0.3;                                                      // Monday-open spreads are wide
         if(i < SPLIT) { g0.add(pnl); nn0++; if(filled) fills0++; } else { g1.add(pnl); nn1++; if(filled) fills1++; }
      }
      print_acc("fade weekend gaps over 0.3 hourly ATR", g0, g1, 52);
      std::printf("      gap filled within 8 h: older %.0f%% of %d, newer %.0f%% of %d\n", nn0 ? 100.0 * fills0 / nn0 : 0.0, nn0, nn1 ? 100.0 * fills1 / nn1 : 0.0, nn1);
      (void)f0; (void)f1;
   }

   // ---------------- CONE and SQUEEZE: trade the SIZE forecast, the one thing found to be predictable --------
   // CONE: the calibrated cone (refitted every day on the previous 3,000 bars) says where price should be 3 bars
   // after an anchor 80% of the time. When the close escapes it by k x its own half-width, either fade back to the
   // cone's median or follow the escape. Target = distance back to the median, stop = the same distance, 6 bars.
   // SQUEEZE: the last 6 bars' high-low is in the lowest 20% of its own history (rank from the previous 3,000 bars).
   // Stop orders 0.05 ATR beyond both sides of that box for the next 6 bars, first one filled wins (one-cancels-other).
   // Stop = the other side of the box, target = 2 box heights, 12 bars.
   {
      std::printf("\n  CONE: fade / follow a close that escapes the 3-bar cone (k = escape beyond the 80%% edge, in half-widths)\n");
      // bracket trade from the open of bar e; worst case when both levels are inside one bar
      auto bracket = [&](int e, int dir, double stop, double target, int max_bars, double &pnl) -> bool {
         if(e >= E.n - 1) return false;
         const double entry = B[e].open;
         if(dir * (target - entry) <= 0 || dir * (entry - stop) <= 0) return false;
         for(int j = e; j < E.n && j < e + max_bars; j++)
         {
            const double adv = (dir > 0) ? B[j].low : B[j].high, fav = (dir > 0) ? B[j].high : B[j].low;
            if(dir * (adv - stop) <= 0)
            {
               const double fill = (dir > 0) ? std::min(stop, B[j].open) : std::max(stop, B[j].open);   // a gap fills worse
               pnl = dir * (fill - entry) - COST;
               return true;
            }
            if(dir * (fav - target) >= 0) { pnl = dir * (target - entry) - COST; return true; }
            pnl = dir * (B[j].close - entry) - COST;
         }
         return true;
      };
      const double ks[3] = {0.0, 0.5, 1.0};
      Acc fade0[3], fade1[3], fol0[3], fol1[3];
      Acc folL0, folL1, folS0, folS1;                                            // k = 1.0 follow, split by side
      std::map<int, Acc> fol_year, fol_year_r;                                   // $ and R (stop distance = 1R)
      long long cal_day = -1;
      for(int i = E.cfg.warmup + 3200; i < E.n - 8; i++)
      {
         const long long d = B[i].time / 86400;
         if(d != cal_day) { E.CalibrateForecast(i - 3, 3000); cal_day = d; }
         if(!E.fc_cal_ok) continue;
         const int a = i - 3;
         double pv = 0.0;
         for(int k = 1; k <= 3; k++) { const double se = E.SeasonAt(B[a + k].time); pv += se * se; }
         const double sc = E.m_atr[a] * std::sqrt(pv);
         const double up = B[a].close + E.fcz_hi[2] * sc, dn = B[a].close + E.fcz_lo[2] * sc, md = B[a].close + E.fcz_md[2] * sc;
         const double half = 0.5 * (up - dn);
         if(half <= 0) continue;
         const double c = B[i].close;
         for(int q = 0; q < 3; q++)
         {
            const bool hi = c > up + ks[q] * half, lo = c < dn - ks[q] * half;
            if(!hi && !lo) continue;
            const double dist = std::fabs(c - md);
            if(dist < 20 * COST * 0.25) continue;                               // too small to pay the spread
            const int fdir = hi ? -1 : 1;
            double p;
            if(bracket(i + 1, fdir, c - fdir * dist, md, 6, p)) (i < SPLIT ? fade0[q] : fade1[q]).add(p);
            if(bracket(i + 1, -fdir, c + fdir * dist, c - fdir * dist, 6, p))
            {
               (i < SPLIT ? fol0[q] : fol1[q]).add(p);
               if(q == 2)
               {
                  if(hi) (i < SPLIT ? folL0 : folL1).add(p); else (i < SPLIT ? folS0 : folS1).add(p);
                  fol_year[year_of(i)].add(p);
                  fol_year_r[year_of(i)].add(p / dist);
               }
            }
         }
      }
      for(int q = 0; q < 3; q++)
      {
         char nm[96];
         std::snprintf(nm, sizeof nm, "FADE an escape beyond the cone edge + %.1f half-widths", ks[q]);
         print_acc(nm, fade0[q], fade1[q], bars_per_year);
         std::snprintf(nm, sizeof nm, "FOLLOW an escape beyond the cone edge + %.1f half-widths", ks[q]);
         print_acc(nm, fol0[q], fol1[q], bars_per_year);
      }
      print_acc("  FOLLOW +1.0, upward escapes only (buy)", folL0, folL1, bars_per_year);
      print_acc("  FOLLOW +1.0, downward escapes only (sell)", folS0, folS1, bars_per_year);
      std::printf("      FOLLOW +1.0 by year ($/trade, trades):");
      for(auto &kv : fol_year) std::printf(" %d %+.2f(%d)", kv.first, kv.second.mean(), kv.second.n);
      std::printf("\n      FOLLOW +1.0 by year (R/trade):");
      for(auto &kv : fol_year_r) std::printf(" %d %+.3f", kv.first, kv.second.mean());
      std::printf("\n");

      std::printf("\n  SQUEEZE: two-way stop orders around a quiet 6-bar box (box in the lowest 20%% of its own history)\n");
      Acc s0, s1, sl0, sl1;
      std::vector<double> hist;
      for(int i = E.cfg.warmup + 3200; i < E.n - 14; i++)
      {
         double bh = -1e18, bl = 1e18;
         for(int k = i - 5; k <= i; k++) { bh = std::max(bh, B[k].high); bl = std::min(bl, B[k].low); }
         const double a = std::max(E.m_atr[i], 1e-9);
         const double rel = (bh - bl) / a;
         // rank against the previous 3,000 bars (rebuilt every 250 bars to keep it fast)
         if(hist.empty() || i % 250 == 0)
         {
            hist.clear();
            for(int j = i - 3000; j < i; j += 3)
            {
               double h2 = -1e18, l2 = 1e18;
               for(int k = j - 5; k <= j; k++) { h2 = std::max(h2, B[k].high); l2 = std::min(l2, B[k].low); }
               hist.push_back((h2 - l2) / std::max(E.m_atr[j], 1e-9));
            }
            std::sort(hist.begin(), hist.end());
         }
         if(rel > hist[hist.size() / 5]) continue;
         const double box = bh - bl;
         if(box < 20 * COST * 0.25) continue;
         const double bs = bh + 0.05 * a, ss = bl - 0.05 * a;
         // first stop order touched in the next 6 bars; if both inside the same bar, count it as the loser
         int dir = 0, e = -1;
         for(int j = i + 1; j <= i + 6 && j < E.n; j++)
         {
            const bool hb = B[j].high >= bs, hs = B[j].low <= ss;
            if(hb && hs) { dir = 0; e = j; break; }
            if(hb) { dir = 1; e = j; break; }
            if(hs) { dir = -1; e = j; break; }
         }
         if(e < 0) continue;
         double pnl;
         if(dir == 0) pnl = -(bs - ss) - COST;                                  // whipsawed in one bar
         else
         {
            const double entry = (dir > 0) ? std::max(bs, B[e].open) : std::min(ss, B[e].open);
            const double stop = (dir > 0) ? bl : bh, target = entry + dir * 2.0 * box;
            pnl = 0.0;
            bool done = false;
            for(int j = e; j < E.n && j < e + 12 && !done; j++)
            {
               const double adv = (dir > 0) ? B[j].low : B[j].high, fav = (dir > 0) ? B[j].high : B[j].low;
               if(dir * (adv - stop) <= 0) { pnl = dir * (stop - entry) - COST; done = true; }
               else if(j > e && dir * (fav - target) >= 0) { pnl = dir * (target - entry) - COST; done = true; }
               else pnl = dir * (B[j].close - entry) - COST;
            }
         }
         (i < SPLIT ? s0 : s1).add(pnl);
         // upside only (a single buy stop), daily trend up: its own fill, the sell side does not exist
         if(E.m_dreg[i] > 0)
         {
            int eu = -1;
            for(int j = i + 1; j <= i + 6 && j < E.n; j++) if(B[j].high >= bs) { eu = j; break; }
            if(eu > 0)
            {
               const double entry = std::max(bs, B[eu].open), target = entry + 2.0 * box;
               double pu = 0.0;
               bool done = false;
               for(int j = eu; j < E.n && j < eu + 12 && !done; j++)
               {
                  if(B[j].low <= bl) { pu = std::min(bl, j > eu ? B[j].open : bl) - entry - COST; done = true; }
                  else if(j > eu && B[j].high >= target) { pu = target - entry - COST; done = true; }
                  else pu = B[j].close - entry - COST;
               }
               (i < SPLIT ? sl0 : sl1).add(pu);
            }
         }
         i += 6;                                                                // one box at a time
      }
      print_acc("SQUEEZE both ways (one-cancels-other)", s0, s1, bars_per_year);
      print_acc("SQUEEZE upside only, daily trend up", sl0, sl1, bars_per_year);
   }

   // ---------------- OVER and SEASON (daily file) ----------------------------------------------------------
   if(d1.size() > 1000)
   {
      const int N = (int)d1.size();
      const int sp = (int)(0.5 * N);
      std::printf("\n  OVER: day after a 2-sigma day (sigma = 20-day stdev of daily returns), daily file %s .. %s, halves split %s\n",
                  TimeToString(d1[21].time).c_str(), TimeToString(d1[N - 1].time).c_str(), TimeToString(d1[sp].time).c_str());
      Acc up0, up1, dn0, dn1;
      for(int k = 22; k < N - 1; k++)
      {
         double s = 0, s2 = 0;
         for(int q = k - 20; q < k; q++) { const double r = std::log(d1[q].close / d1[q - 1].close); s += r; s2 += r * r; }
         const double sd = std::sqrt(std::max(1e-12, s2 / 20 - (s / 20) * (s / 20)));
         const double r0 = std::log(d1[k].close / d1[k - 1].close);
         const double nxt = (d1[k + 1].close - d1[k].close);                   // next day, $ per oz, close to close
         if(r0 > 2 * sd) (k < sp ? up0 : up1).add(nxt - COST);
         if(r0 < -2 * sd) (k < sp ? dn0 : dn1).add(nxt - COST);
      }
      print_acc("after a +2 sigma day: BUY the next day (follow)", up0, up1, 252);
      print_acc("after a -2 sigma day: BUY the next day (rebound)", dn0, dn1, 252);

      std::printf("\n  SEASON: months / weekdays chosen on 2004-2015, traded long 2015-2026 (daily close to close, $ per oz, cost per day held)\n");
      double mm0[12] = {0}; int mc0[12] = {0};
      for(int k = 1; k < sp; k++)
      {
         const int mo = month_of(d1[k].time);
         mm0[mo - 1] += std::log(d1[k].close / d1[k - 1].close); mc0[mo - 1]++;
      }
      bool good[12];
      std::printf("    month mean log return x 1e4 (older):");
      for(int m = 0; m < 12; m++) { good[m] = mc0[m] > 0 && mm0[m] / mc0[m] > 0; std::printf(" %d:%+.1f", m + 1, mc0[m] ? 1e4 * mm0[m] / mc0[m] : 0.0); }
      std::printf("\n");
      Acc in1, out1;
      for(int k = sp; k < N; k++)
      {
         const double r = 1e4 * std::log(d1[k].close / d1[k - 1].close);
         (good[month_of(d1[k].time) - 1] ? in1 : out1).add(r);
      }
      std::printf("    newer half: days in the 'good' months %+.2f bps/day (n %d, se %.2f) vs other months %+.2f bps/day (n %d, se %.2f)\n",
                  in1.mean(), in1.n, in1.se(), out1.mean(), out1.n, out1.se());
      double dw0[7] = {0}; int dc0[7] = {0}; double dw1[7] = {0}; int dc1[7] = {0};
      for(int k = 1; k < N; k++)
      {
         const int dw = (int)(((d1[k].time / 86400) + 4) % 7);
         const double r = 1e4 * std::log(d1[k].close / d1[k - 1].close);
         if(k < sp) { dw0[dw] += r; dc0[dw]++; } else { dw1[dw] += r; dc1[dw]++; }
      }
      std::printf("    weekday mean bps (older | newer):");
      const char *wn[7] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};
      for(int d = 1; d <= 5; d++) std::printf("  %s %+.1f | %+.1f", wn[d], dc0[d] ? dw0[d] / dc0[d] : 0.0, dc1[d] ? dw1[d] / dc1[d] : 0.0);
      std::printf("\n");
   }
   return 0;
}
