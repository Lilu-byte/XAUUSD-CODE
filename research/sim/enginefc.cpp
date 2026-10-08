// Round 11: walk-forward test of the ENGINE's own forecast code (what the indicator runs), new vs old:
//   candle size  CXauEngine::NextRange with the HAR fit (fc_har) vs ATR x hour profile x median (old)
//   cone         3-bar 20-80% cone coverage per year (a self-correcting version was tested here and removed: M15 fell to 58%)
//   day range    CXauEngine::DayRangeForecast (fc_dayfit) vs the 14-day mean, 2 / 8 / 14 / 20 hours into the day
// The engine is recalibrated at the start of every day on the bars before it (as the indicator does on every bar).
// Scored on the newer 40% of the file.
//
// Build:  g++ -std=c++17 -O2 -o enginefc research/sim/enginefc.cpp
// Run:    ./enginefc BASE.csv HIGHER.csv D1.csv [bars_loaded_for_the_day_fit=all]

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

struct Err
{
   int n = 0, within = 0; double sae = 0;
   void add(double pred, double act) { n++; sae += std::fabs(pred - act); if(act > 0 && std::fabs(pred / act - 1.0) <= 0.25) within++; }
   double mae() const { return n ? sae / n : 0.0; }
   double win() const { return n ? 100.0 * within / n : 0.0; }
};

int main(int argc, char **argv)
{
   if(argc < 4) { std::printf("usage: enginefc BASE.csv HIGHER.csv D1.csv\n"); return 2; }
   std::vector<MqlRates> B, htf, d1;
   if(!load_csv(argv[1], B) || !load_csv(argv[2], htf) || !load_csv(argv[3], d1)) return 2;
   B.pop_back(); htf.pop_back(); d1.pop_back();
   static CXauEngine E;
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(B); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.cfg.d1_sma = 200;
   E.SetBase(B, (int)B.size()); E.SetHTF(htf, (int)htf.size()); E.SetDaily(d1, (int)d1.size());
   if(!E.Compute()) return 2;
   if(argc > 4) E.cfg.fc_daybars = std::atoi(argv[4]);     // emulate a chart with only this many bars loaded
   const int n = E.n;
   const int SPLIT = E.cfg.warmup + (int)(0.6 * (n - E.cfg.warmup));
   std::printf("== ENGINE FORECASTS, new vs old: %s (%d bars of %d s), scored %s .. %s, day fit on %s ==\n", argv[1], n, E.cfg.base_sec,
               TimeToString(B[SPLIT].time).c_str(), TimeToString(B[n - 1].time).c_str(), E.cfg.fc_daybars > 0 ? (std::to_string(E.cfg.fc_daybars) + " bars").c_str() : "all bars");

   // final range of every engine day
   std::map<int, std::pair<double, double>> dayhl;
   for(int i = 0; i < n; i++)
   {
      auto it = dayhl.find(E.m_dkey[i]);
      if(it == dayhl.end()) dayhl[E.m_dkey[i]] = {B[i].high, B[i].low};
      else { it->second.first = std::max(it->second.first, B[i].high); it->second.second = std::min(it->second.second, B[i].low); }
   }
   auto final_range = [&](int i) { const auto &p = dayhl[E.m_dkey[i]]; return p.first - p.second; };

   Err cs_new, cs_old;
   std::map<int, Err> ys_new, ys_old;
   std::map<int, int> cn, cin_new, cin_old;
   double wid_new = 0, wid_old = 0; int wn = 0;
   const double cps[4] = {2, 8, 14, 20};
   Err d_adr[4], d_max[4], d_fit[4];
   double fz_lo_old = 0, fz_hi_old = 0, fz_lo_new = 0, fz_hi_new = 0;
   double kr_old = 1.0;
   long long day = -1;
   int last_key = E.m_dkey[SPLIT];
   int cp_done[4] = {-1, -1, -1, -1};
   const int last_day_key = E.m_dkey[n - 1];
   for(int i = SPLIT; i < n - 4; i++)
   {
      if(B[i].time / 86400 != day)
      {
         day = B[i].time / 86400;
         // old: everything off
         E.cfg.fc_har = false; E.cfg.fc_dayfit = false;
         E.CalibrateForecast(i - 1, 3000);
         fz_lo_old = E.fcz_lo[2]; fz_hi_old = E.fcz_hi[2]; kr_old = E.fc_krange;
         // new: as shipped
         E.cfg.fc_har = true; E.cfg.fc_dayfit = true;
         E.CalibrateForecast(i - 1, 3000);
         fz_lo_new = E.fcz_lo[2]; fz_hi_new = E.fcz_hi[2];
      }
      if(!E.fc_cal_ok) continue;
      // candle size of bar i+1, forecast after bar i closed
      const double act = B[i + 1].high - B[i + 1].low;
      const double pn = E.NextRange(i, B[i + 1].time);
      const double po = E.m_atr[i] * E.SeasonAt(B[i + 1].time) * kr_old;
      cs_new.add(pn, act); cs_old.add(po, act);
      const int yr = XYearOfDays(B[i].time / 86400);
      ys_new[yr].add(pn, act); ys_old[yr].add(po, act);
      // 3-bar cone
      double pv = 0; for(int k = 1; k <= 3; k++) { const double se = E.SeasonAt(B[i + k].time); pv += se * se; }
      const double sc = E.m_atr[i] * std::sqrt(pv);
      const double mv = B[i + 3].close - B[i].close;
      cn[yr]++;
      if(mv >= fz_lo_old * sc && mv <= fz_hi_old * sc) cin_old[yr]++;
      if(mv >= fz_lo_new * sc && mv <= fz_hi_new * sc) cin_new[yr]++;
      wid_new += (fz_hi_new - fz_lo_new) * sc / E.m_atr[i]; wid_old += (fz_hi_old - fz_lo_old) * sc / E.m_atr[i]; wn++;
      // day range at the checkpoints (the fit is made for the time of day of the bar, as the indicator does)
      if(E.cfg.base_sec <= 14400 && E.m_dkey[i] != last_day_key)
      {
         if(E.m_dkey[i] != last_key) { last_key = E.m_dkey[i]; for(int c = 0; c < 4; c++) cp_done[c] = -1; }
         for(int c = 0; c < 4; c++)
         {
            if(cp_done[c] == last_key || E.DayHours(i) < cps[c] || E.m_adr[i] <= 0) continue;
            cp_done[c] = last_key;
            E.FitDayRange(i);
            const double fr = final_range(i), adr = E.m_adr[i], sofar = E.m_adru[i] * adr;
            d_adr[c].add(adr, fr); d_max[c].add(std::max(adr, sofar), fr); d_fit[c].add(E.DayRangeForecast(i), fr);
         }
      }
   }
   std::printf("\n  NEXT CANDLE SIZE   mean abs error   within +-25%%\n");
   std::printf("    old (ATR x profile x median) %8.3f       %5.1f%%\n", cs_old.mae(), cs_old.win());
   std::printf("    new (HAR)                    %8.3f       %5.1f%%   (%+.1f%%)\n", cs_new.mae(), cs_new.win(), 100.0 * (cs_new.mae() / cs_old.mae() - 1.0));
   std::printf("    by year (new vs old):");
   for(auto &kv : ys_old) std::printf(" %d %+.1f%%", kv.first, 100.0 * (ys_new[kv.first].mae() / kv.second.mae() - 1.0));
   std::printf("\n\n  CONE 3 bars ahead (should hold 60%%)   year: old | new\n");
   int tn = 0, to = 0, tw = 0;
   for(auto &kv : cn)
   {
      std::printf("    %d: %5.1f%% | %5.1f%%  (%d)\n", kv.first, 100.0 * cin_old[kv.first] / kv.second, 100.0 * cin_new[kv.first] / kv.second, kv.second);
      tn += kv.second; to += cin_old[kv.first]; tw += cin_new[kv.first];
   }
   std::printf("    all : %5.1f%% | %5.1f%%   width old %.2f ATR, new %.2f ATR\n", 100.0 * to / std::max(tn, 1), 100.0 * tw / std::max(tn, 1),
               wid_old / std::max(wn, 1), wid_new / std::max(wn, 1));
   if(E.cfg.base_sec <= 14400)
   {
      std::printf("\n  DAY RANGE (final high-low of the day)  mean abs error: 14-day mean | max(mean, so far) | engine forecast\n");
      for(int c = 0; c < 4; c++)
         std::printf("    %2.0f h into the day (%d days): %7.2f | %7.2f | %7.2f (%+.1f%% vs 14-day mean), within +-25%%: %.0f%% vs %.0f%%\n", cps[c], d_fit[c].n,
                     d_adr[c].mae(), d_max[c].mae(), d_fit[c].mae(), 100.0 * (d_fit[c].mae() / std::max(d_adr[c].mae(), 1e-9) - 1.0), d_fit[c].win(), d_adr[c].win());
   }
   return 0;
}
