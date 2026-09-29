// Validation harness for the XAU engine (MQL5/Include/XAU/XAU_Core.mqh).
//
// Runs the REAL engine code (compiled as C++ through research/mock/mql5_mock.h)
// on synthetic gold-like data. What this can and cannot show:
//
//   CAN:   the engine never looks ahead (causality), the trade simulator and
//          position sizing behave as specified, signals fire at sensible
//          frequencies, and on a world with NO edge the strategy does not
//          invent one (a positive result there would indicate a bug).
//   CANNOT: prove profitability on real XAUUSD. Synthetic worlds only test
//          mechanics. Real validation = the indicator's built-in trial and the
//          MT5 Strategy Tester on real ticks (see docs/TESTING.md).
//
// Build:  g++ -std=c++17 -O2 -Wall -Wextra -o harness harness.cpp
// Run:    ./harness [units|causal|null|trend|meanrev|all]

#include "../mock/mql5_mock.h"
#include "../../src/XAU_Core.mqh"
#include "../../src/XAU_Platform.mqh"

#include <cstring>
#include <random>

//---------------------------------------------------------------------------
// synthetic data
//---------------------------------------------------------------------------
enum World { W_NULL = 0, W_TREND = 1, W_MEANREV = 2, W_MIXED = 3 };

struct Series
{
   std::vector<MqlRates> m15;
   std::vector<MqlRates> h1;
};

static double hour_profile(int h)
{
   static const double p[24] = {0.55, 0.55, 0.55, 0.6, 0.6, 0.65, 0.8, 1.1, 1.3, 1.3, 1.0, 1.0,
                                1.3,  1.9,  1.6,  1.5, 1.2, 0.95, 0.9, 0.85, 0.7, 0.6, 0.55, 0.5};
   return p[h];
}

static Series make_series(World w, int nbars_m15, unsigned seed)
{
   std::mt19937_64 rng(seed);
   std::normal_distribution<double> nd(0.0, 1.0);
   std::student_t_distribution<double> td(4.0);
   std::uniform_real_distribution<double> ud(0.0, 1.0);
   const double t4norm = 1.0 / std::sqrt(2.0);   // var of t(4) = 2

   Series S;
   double price = 4000.0, anchor = 4000.0;
   double lv = 0.0;       // log volatility regime
   int drift_state = 0;   // -1,0,+1 (trend world)
   long long t = 1704067200LL;   // Mon 2024-01-01 00:00 UTC
   const double sig1 = 0.00026;  // 1-minute return sigma (fraction of price)
   int produced = 0;
   long long mcount = 0;
   int last_reg = -1;

   MqlRates cur15{}, cur1h{};
   bool open15 = false, open1h = false;

   while(produced < nbars_m15)
   {
      // market hours: Sun 22:00 GMT .. Fri 21:00 GMT
      long long day = t / 86400;
      int wd = (int)((day + 4) % 7);   // 0=Sun
      int hr = (int)((t % 86400) / 3600);
      bool open = true;
      if(wd == 6) open = false;
      if(wd == 0 && hr < 22) open = false;
      if(wd == 5 && hr >= 21) open = false;
      if(!open) { t += 60; continue; }

      // volatility regime (slow AR(1) in log space), intraday seasonality
      lv = 0.9995 * lv + 0.012 * nd(rng);
      double sig = sig1 * std::exp(lv) * hour_profile(hr);

      mcount++;
      World ew = w;
      if(w == W_MIXED)
      {
         int reg = (int)((mcount / (15LL * 6000LL)) % 2);   // switch regime every 6000 M15 bars
         ew = (reg == 0) ? W_TREND : W_MEANREV;
         if(reg != last_reg) { anchor = price; last_reg = reg; }
      }
      double drift = 0.0;
      if(ew == W_TREND)
      {
         if(ud(rng) < 1.0 / 900.0) drift_state = (int)(ud(rng) * 3.0) - 1;
         drift = 0.05 * sig1 * drift_state;
      }
      else if(ew == W_MEANREV)
      {
         anchor += 0.00002 * price * nd(rng);
         drift = -0.004 * (price - anchor) / price;
      }
      double r = drift + sig * td(rng) * t4norm;
      double o1 = price;
      price *= std::exp(r);
      double hi1 = std::max(o1, price) * (1.0 + std::fabs(nd(rng)) * sig * 0.35);
      double lo1 = std::min(o1, price) * (1.0 - std::fabs(nd(rng)) * sig * 0.35);
      long long vol1 = (long long)(180.0 * hour_profile(hr) * std::exp(lv) * (1.0 + std::fabs(r) / sig1 * 0.5) * (0.6 + ud(rng) * 0.8));

      // aggregate to M15
      long long b15 = t - (t % 900);
      if(!open15 || cur15.time != b15)
      {
         if(open15) { S.m15.push_back(cur15); produced++; if(produced >= nbars_m15) break; }
         cur15.time = b15; cur15.open = o1; cur15.high = hi1; cur15.low = lo1; cur15.close = price;
         cur15.tick_volume = vol1; cur15.spread = 30; cur15.real_volume = 0;
         open15 = true;
      }
      else
      {
         cur15.high = std::max(cur15.high, hi1); cur15.low = std::min(cur15.low, lo1);
         cur15.close = price; cur15.tick_volume += vol1;
      }
      // aggregate to H1
      long long b1h = t - (t % 3600);
      if(!open1h || cur1h.time != b1h)
      {
         if(open1h) S.h1.push_back(cur1h);
         cur1h.time = b1h; cur1h.open = o1; cur1h.high = hi1; cur1h.low = lo1; cur1h.close = price;
         cur1h.tick_volume = vol1; cur1h.spread = 30; cur1h.real_volume = 0;
         open1h = true;
      }
      else
      {
         cur1h.high = std::max(cur1h.high, hi1); cur1h.low = std::min(cur1h.low, lo1);
         cur1h.close = price; cur1h.tick_volume += vol1;
      }
      t += 60;
   }
   return S;
}

// keep only HTF bars that are complete at the close of base bar `last`
static std::vector<MqlRates> htf_upto(const Series &S, int last_base)
{
   std::vector<MqlRates> out;
   const long long close_t = S.m15[last_base].time + 900;
   for(const MqlRates &b : S.h1) if(b.time + 3600 <= close_t) out.push_back(b);
   return out;
}

static int    g_solo = 0;
static int    g_veto = 0;
static double g_score = -1.0;
static int    g_conf = -1;
static int    g_sess = -1;
static int    g_regime = 0;
static double g_adr = 0.90;

static void load(CXauEngine &e, const Series &S, int nbase)
{
   std::vector<MqlRates> base(S.m15.begin(), S.m15.begin() + nbase);
   std::vector<MqlRates> h = htf_upto(S, nbase - 1);
   e.cfg.Defaults();
   e.cfg.regime_on = g_regime;
   e.cfg.an_veto = g_veto;
   e.cfg.orb_solo = g_solo;
   if(g_score > 0.0) e.cfg.score_min = g_score;
   if(g_conf > 0) e.cfg.min_confluence = g_conf;
   if(g_sess >= 0) e.cfg.use_session_filter = (g_sess == 1);
   e.cfg.adr_block = g_adr;
   e.SetBase(base, nbase);
   e.SetHTF(h, (int)h.size());
   e.Compute();
}

//---------------------------------------------------------------------------
// tests
//---------------------------------------------------------------------------
static int g_fail = 0;
static void print_stats(const char *name, const XStats &s);
#define CHECK(cond, msg)                                                      \
   do { if(!(cond)) { std::printf("  FAIL: %s\n", msg); g_fail++; }            \
        else        { std::printf("  ok:   %s\n", msg); } } while(0)

static bool near(double a, double b, double tol = 1e-9) { return std::fabs(a - b) <= tol; }

// build a tiny engine with hand-made bars for simulator tests
static void tiny(CXauEngine &e, const std::vector<std::vector<double>> &ohlc)
{
   std::vector<MqlRates> v;
   long long t = 1704067200LL;
   for(const auto &b : ohlc)
   {
      MqlRates r{};
      r.time = t; r.open = b[0]; r.high = b[1]; r.low = b[2]; r.close = b[3]; r.tick_volume = 100;
      v.push_back(r);
      t += 900;
   }
   e.cfg.Defaults();
   e.cfg.cost_price = 0.0;
   e.cfg.max_hold_bars = 10;
   e.SetBase(v, (int)v.size());
   ArrayResize(e.m_atr, (int)v.size());
   for(size_t i = 0; i < v.size(); i++) e.m_atr[i] = 1.0;
}

static void test_units()
{
   std::printf("\n== unit tests: simulator + sizing ==\n");
   XTradeResult r;

   { // 1. stop first
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100.5,98.9,99.0},{99,99,99,99}});
      e.SimulateTrade(0, 1, 99.0, 2, r);
      CHECK(r.ok && r.closed && near(r.r_net, -1.0), "long: stop hit -> -1R");
   }
   { // 2. TP1 partial then breakeven
      CXauEngine e; tiny(e, {{100,100,100,100},{100,101.2,99.5,101},{101,101.1,99.9,100},{100,100,100,100}});
      e.SimulateTrade(0, 1, 99.0, 3, r);
      CHECK(r.closed && r.tp1_hit && near(r.r_net, 0.5), "long: TP1 (50% at 1R) then BE -> +0.5R");
   }
   { // 3. TP1 then TP2
      CXauEngine e; tiny(e, {{100,100,100,100},{100,101.1,100.2,101},{101,102.6,101.0,102.5},{102,102,102,102}});
      e.SimulateTrade(0, 1, 99.0, 3, r);
      CHECK(r.closed && near(r.r_net, 0.5 + 0.5 * 2.5), "long: TP1 then TP2 -> +1.75R");
   }
   { // 4. same bar touches SL and TP1 -> pessimistic stop
      CXauEngine e; tiny(e, {{100,100,100,100},{100,101.5,98.5,100},{100,100,100,100}});
      e.SimulateTrade(0, 1, 99.0, 2, r);
      CHECK(r.closed && near(r.r_net, -1.0), "long: bar touching SL and TP1 counts as stopped");
   }
   { // 5. time stop
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100.3,99.8,100.1},{100.1,100.3,99.8,100.2},{100.2,100.4,99.8,100.3},{100.3,100.4,99.9,100.3}});
      e.cfg.max_hold_bars = 3;
      e.SimulateTrade(0, 1, 99.0, 4, r);
      CHECK(r.closed && r.bars == 3 && near(r.r_net, 0.3), "long: time stop after 3 bars at the close");
   }
   { // 6. short mirror: stop
      CXauEngine e; tiny(e, {{100,100,100,100},{100,101.2,99.8,101.0},{101,101,101,101}});
      e.SimulateTrade(0, -1, 101.0, 2, r);
      CHECK(r.closed && near(r.r_net, -1.0), "short: stop hit -> -1R");
   }
   { // 7. short mirror: TP1 then TP2
      CXauEngine e; tiny(e, {{100,100,100,100},{100,99.9,98.9,99.0},{99,99.0,97.4,97.5},{97.5,97.5,97.5,97.5}});
      e.SimulateTrade(0, -1, 101.0, 3, r);
      CHECK(r.closed && near(r.r_net, 0.5 + 0.5 * 2.5), "short: TP1 then TP2 -> +1.75R");
   }
   { // 8. still open at last_idx
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100.4,99.9,100.3},{100.3,100.5,100.1,100.4}});
      e.SimulateTrade(0, 1, 99.0, 2, r);
      CHECK(r.ok && !r.closed && r.float_r > 0.0, "open trade reports floating R and stays unresolved");
   }
   { // 9. spread cost reduces R
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100,98.9,99.0},{99,99,99,99}});
      e.cfg.cost_price = 0.2;
      e.SimulateTrade(0, 1, 99.0, 2, r);
      CHECK(r.closed && near(r.r_net, -1.2), "cost 0.2 on 1.0 risk -> -1.2R");
   }
   // sizing
   CHECK(near(XRawLots(100.0, 10.0, 0.01, 1.0), 0.1), "sizing: $100 risk, $10 stop, XAUUSD tick -> 0.10 lot");
   CHECK(near(XNormLotsDown(0.137, 0.01, 50.0, 0.01), 0.13), "sizing: rounds DOWN to step");
   CHECK(XNormLotsDown(0.004, 0.01, 50.0, 0.01) == 0.0, "sizing: below min lot -> 0 (caller must refuse, not over-risk)");
   CHECK(near(XNormLotsDown(99.0, 0.01, 50.0, 0.01), 50.0), "sizing: clamps to max lot");
   CHECK(XWeekdayGmt(1704067200LL, 0) == 1, "weekday helper: 2024-01-01 is Monday");
}


static void test_platform()
{
   std::printf("\n== unit tests: platform layer (lot planning, news fallback) ==\n");
   XLotPlan p;
   // mock symbol: tick 0.01, tick value 1.0 (=$1 per 0.01 move per lot => 100 oz contract), min lot 0.01
   XPlanLots("XAUUSD", 10000.0, 1.0, 10.0, true, 4000.0, 1.5, 0.0, 9000.0, 0.5, p);
   CHECK(p.ok && near(p.lots, 0.10) && near(p.risk_pct, 1.0, 1e-6), "$10k, 1% risk, $10 stop -> 0.10 lot risking exactly 1%");
   XPlanLots("XAUUSD", 1000.0, 1.0, 10.0, true, 4000.0, 1.5, 0.0, 900.0, 0.5, p);
   CHECK(p.ok && near(p.lots, 0.01), "$1k account -> 0.01 lot (exactly the min lot, 1% risk)");
   XPlanLots("XAUUSD", 100.0, 1.0, 10.0, true, 4000.0, 1.5, 0.0, 90.0, 0.5, p);
   CHECK(!p.ok && p.note.size() > 0, "$100 account, $10 stop: min lot would risk 10% -> REFUSED, not silently over-risked");
   XPlanLots("XAUUSD", 100.0, 5.0, 10.0, true, 4000.0, 1.5, 0.0, 90.0, 0.5, p);
   CHECK(!p.ok, "$100 account even at 5% risk: min lot risks 10% (> 1.5x requested) -> refused");
   XPlanLots("XAUUSD", 10000.0, 1.0, 10.0, true, 4000.0, 1.5, 0.05, 9000.0, 0.5, p);
   CHECK(p.ok && near(p.lots, 0.05), "absolute lot cap is respected");
   XPlanLots("XAUUSD", 100000.0, 1.0, 10.0, true, 4000.0, 1.5, 0.0, 300.0, 0.5, p);
   CHECK(p.ok && p.lots < 1.0, "free-margin cap scales the lot down");

   CXauNews nw;
   nw.gmt_offset_sec = 0;
   nw.fallback_static = true;
   string why;
   datetime mon_1230 = 1704067200LL + (datetime)(12.5 * 3600);
   datetime mon_0900 = 1704067200LL + 9 * 3600;
   datetime sat_1230 = 1704067200LL + 5 * 86400 + (datetime)(12.5 * 3600);
   CHECK(nw.Blocked(mon_1230, why), "static fallback blocks the 12:30 GMT US-data window on weekdays");
   CHECK(!nw.Blocked(mon_0900, why), "static fallback leaves the London morning open");
   CHECK(!nw.Blocked(sat_1230, why), "static fallback ignores weekends");
   CHECK(XAutoHTF(PERIOD_M15) == PERIOD_H1 && XAutoHTF(PERIOD_H1) == PERIOD_H4 && XAutoHTF(PERIOD_M1) == PERIOD_M15, "automatic higher-timeframe map");
}


static void test_time_and_filters()
{
   std::printf("\n== unit tests: daylight-saving maths, ADR block, efficiency ratio ==\n");
   auto ts = [](int y, int m, int d, int hh, int mm, int ss) { return XDaysFromCivil(y, m, d) * 86400LL + hh * 3600 + mm * 60 + ss; };
   CHECK(XYearOfDays(XDaysFromCivil(2024, 2, 29)) == 2024 && XYearOfDays(XDaysFromCivil(2026, 12, 31)) == 2026, "civil date round-trip");
   CHECK(XUsDst(ts(2024, 3, 10, 6, 59, 59)) == false && XUsDst(ts(2024, 3, 10, 7, 0, 0)) == true,  "US DST starts 2024-03-10 07:00 UTC");
   CHECK(XUsDst(ts(2024, 11, 3, 5, 59, 59)) == true  && XUsDst(ts(2024, 11, 3, 6, 0, 0)) == false, "US DST ends 2024-11-03 06:00 UTC");
   CHECK(XEuDst(ts(2024, 3, 31, 0, 59, 59)) == false && XEuDst(ts(2024, 3, 31, 1, 0, 0)) == true,  "EU DST starts 2024-03-31 01:00 UTC");
   CHECK(XEuDst(ts(2024, 10, 27, 0, 59, 59)) == true && XEuDst(ts(2024, 10, 27, 1, 0, 0)) == false, "EU DST ends 2024-10-27 01:00 UTC");
   CHECK(XUsDst(ts(2026, 3, 8, 7, 0, 0)) == true && XUsDst(ts(2026, 3, 8, 6, 59, 59)) == false, "US DST 2026 start (2026-03-08)");
   XConfig c; c.Defaults();
   c.gmt_offset_sec = 7200; c.dst_mode = 1;
   CHECK(XOffsetAt(c, (datetime)ts(2024, 1, 15, 12, 0, 0)) == 7200 && XOffsetAt(c, (datetime)ts(2024, 7, 15, 12, 0, 0)) == 10800, "NY-close server: GMT+2 winter, GMT+3 summer");
   c.dst_mode = 0;
   CHECK(XOffsetAt(c, (datetime)ts(2024, 7, 15, 12, 0, 0)) == 7200, "fixed-offset server ignores DST");

   Series S = make_series(W_TREND, 20000, 5);
   CXauEngine e; load(e, S, 20000);
   int bad_er = 0, blocked_leak = 0, adr_hits = 0;
   for(int i = e.cfg.warmup; i < 20000; i++)
   {
      if(e.m_er[i] < -1e-12 || e.m_er[i] > 1.0 + 1e-12) bad_er++;
      if(e.m_adru[i] >= 0.9) { adr_hits++; if(e.m_vote[i * XM_COUNT + XM_PULLBACK] != 0.0 || e.m_vote[i * XM_COUNT + XM_BREAKOUT] != 0.0 || e.m_vote[i * XM_COUNT + XM_SQUEEZE] != 0.0) blocked_leak++; }
   }
   CHECK(bad_er == 0, "efficiency ratio always within [0,1]");
   CHECK(adr_hits > 100 && blocked_leak == 0, "no trend-continuation vote survives when >=90% of the daily range is used");
}

static XStats composite_stats(World w, int regime, double adr, int seeds, int nbars)
{
   XStats agg; agg.Reset();
   g_regime = regime; g_adr = adr;
   for(int sd = 1; sd <= seeds; sd++)
   {
      Series S = make_series(w, nbars, 3000 + sd);
      CXauEngine e; load(e, S, nbars);
      XTrial tr; e.RunTrial(e.cfg.warmup, nbars - 2, tr);
      agg.n += tr.all.n; agg.wins += tr.all.wins; agg.losses += tr.all.losses; agg.scratch += tr.all.scratch; agg.tp1_hits += tr.all.tp1_hits;
      agg.sum_r += tr.all.sum_r; agg.sum_r2 += tr.all.sum_r2; agg.sum_win += tr.all.sum_win; agg.sum_loss += tr.all.sum_loss;
      for(int q = 0; q < tr.all.nh_all && agg.nh_all < XHOLD_MAX; q++) agg.hold_all[agg.nh_all++] = tr.all.hold_all[q];
   }
   g_regime = 0; g_adr = 0.90;
   return agg;
}


static void run_veto_ab()
{
   std::printf("\n== A/B: pattern-match veto of setups (composite, 6 seeds x 20000 bars) ==\n");
   struct W { World w; const char *n; };
   const W worlds[] = {{W_NULL, "null"}, {W_TREND, "trend"}, {W_MEANREV, "meanrev"}, {W_MIXED, "mixed"}};
   for(const W &x : worlds)
   {
      g_veto = 0; XStats base = composite_stats(x.w, 0, 0.90, 6, 20000);
      g_veto = 1; XStats vet  = composite_stats(x.w, 0, 0.90, 6, 20000);
      g_veto = 0;
      print_stats((std::string(x.n) + ": without veto").c_str(), base);
      print_stats((std::string(x.n) + ": with veto").c_str(), vet);
   }
}


static void run_turbo()
{
   std::printf("\n== trade frequency vs quality: default thresholds vs demo-turbo (6 seeds x 20000 bars, veto on) ==\n");
   struct W { World w; const char *n; };
   const W worlds[] = {{W_NULL, "null"}, {W_TREND, "trend"}, {W_MIXED, "mixed"}};
   const double days = 6.0 * (20000 - 250) / 96.0 * 5.0 / 7.0;
   for(const W &x : worlds)
   {
      g_veto = 1;
      XStats d = composite_stats(x.w, 0, 0.90, 6, 20000);
      g_score = 1.2; g_conf = 1; g_sess = 0;
      XStats t = composite_stats(x.w, 0, 0.90, 6, 20000);
      g_score = -1.0; g_conf = -1; g_sess = -1; g_veto = 0;
      std::printf("  %-6s default: %.2f trades/day", x.n, d.n / days);
      print_stats("", d);
      std::printf("  %-6s turbo:   %.2f trades/day", x.n, t.n / days);
      print_stats("", t);
   }
}


static void run_orb_worlds()
{
   std::printf("\n== ORB (GOLD_ORB port) on synthetic M15 worlds: 8 seeds x 30000 bars ==\n");
   struct W { World w; const char *n; };
   const W worlds[] = {{W_NULL, "null"}, {W_TREND, "trend"}, {W_MEANREV, "meanrev"}, {W_MIXED, "mixed"}};
   const double days = 8.0 * (30000 - 250) / 96.0 * 5.0 / 7.0;
   for(const W &x : worlds)
   {
      g_solo = 1; g_sess = 0;
      XStats solo = composite_stats(x.w, 0, 0.0, 8, 30000);
      g_solo = 0; g_sess = -1;
      std::printf("  %-8s ORB solo (no other rules) %.2f trades/day", x.n, solo.n / days);
      print_stats("", solo);
      if(x.w == W_NULL)
      {
         const double z = solo.Expectancy() / std::max(solo.ExpStdErr(), 1e-9);
         CHECK(z < 3.0, "no-edge world: ORB solo is not significantly profitable (no look-ahead in the range logic)");
      }
   }
}

static void run_filter_ab()
{
   std::printf("\n== A/B on synthetic worlds: efficiency-ratio regime weighting and ADR block (composite, 8 seeds x 40000 bars) ==\n");
   struct W { World w; const char *n; };
   const W worlds[] = {{W_NULL, "null"}, {W_TREND, "trend"}, {W_MEANREV, "meanrev"}, {W_MIXED, "mixed"}};
   for(const W &x : worlds)
   {
      print_stats((std::string(x.n) + ": baseline (adr0,reg0)").c_str(), composite_stats(x.w, 0, 0.0, 8, 40000));
      print_stats((std::string(x.n) + ": ADR block 0.90").c_str(),     composite_stats(x.w, 0, 0.90, 8, 40000));
      print_stats((std::string(x.n) + ": regime weights").c_str(),      composite_stats(x.w, 1, 0.0, 8, 40000));
      print_stats((std::string(x.n) + ": both").c_str(),               composite_stats(x.w, 1, 0.90, 8, 40000));
   }
}


// ---------------------------------------------------------------------------
// GOLD_ORB port: scripted H1 days
// ---------------------------------------------------------------------------
struct ScriptBar { int hour; double o, h, l, c; };

// 20 filler days of quiet H1 bars, then a scripted day starting at 01:00 server time.
static void orb_engine(CXauEngine &e, const std::vector<ScriptBar> &day, int &first_script_idx)
{
   std::vector<MqlRates> v;
   long long base = 1704067200LL + 86400LL * 7;   // a Monday, server clock == "GMT" in the harness
   std::mt19937_64 rng(4);
   std::normal_distribution<double> nd(0.0, 1.0);
   double px = 4000.0;
   for(int d = 0; d < 20; d++)
      for(int h = 0; h < 24; h++)
      {
         MqlRates r{};
         r.time = base + d * 86400LL + h * 3600LL;
         r.open = px; px += nd(rng) * 3.0;
         r.close = px; r.high = std::max(r.open, r.close) + 1.5; r.low = std::min(r.open, r.close) - 1.5; r.tick_volume = 100;
         v.push_back(r);
      }
   first_script_idx = (int)v.size();
   for(const ScriptBar &b : day)
   {
      MqlRates r{};
      r.time = base + 20 * 86400LL + b.hour * 3600LL;
      r.open = b.o; r.high = b.h; r.low = b.l; r.close = b.c; r.tick_volume = 100;
      v.push_back(r);
   }
   // a few closing bars so the last scripted bar is "closed" for the engine
   for(int k = 0; k < 3; k++)
   {
      MqlRates r{};
      r.time = v.back().time + 3600; r.open = r.close = r.high = r.low = v.back().close; r.tick_volume = 100;
      v.push_back(r);
   }
   e.cfg.Defaults();
   e.cfg.base_sec = 3600; e.cfg.htf_sec = 14400;
   e.cfg.orb_start_hour = 1.0; e.cfg.orb_range_min = 60; e.cfg.orb_settle_min = 180;
   e.SetBase(v, (int)v.size());
   e.Compute();
}

static void test_orb()
{
   std::printf("\n== GOLD_ORB port: opening-range breakout rules on scripted H1 days ==\n");
   {  // A: range 01:00 (4000..4010 body 4000->4005), quiet 02-04, long breakout 05, no second long at 06, short breakout at 07
      std::vector<ScriptBar> d = {
         {1, 4000, 4010, 3996, 4005},
         {2, 4004, 4008, 3998, 4003},
         {3, 4003, 4008, 3999, 4004},
         {4, 4004, 4007, 3998, 4002},
         {5, 4003, 4016, 4002, 4015},     // bullish close above the 4010 high -> LONG
         {6, 4015, 4020, 4013, 4018},     // another bullish break: must NOT signal again
         {7, 4016, 4017, 3990, 3992}};    // bearish close below the 3996 low -> SHORT
      CXauEngine e; int f0;
      orb_engine(e, d, f0);
      const int i1 = f0 + 4, i2 = f0 + 5, i3 = f0 + 6, ib = f0 + 2;
      CHECK(e.m_orbst[f0] == 1 && near(e.m_orbhi[f0], 4010.0) && near(e.m_orblo[f0], 3996.0), "range is building on the first candle (4010 / 3996)");
      CHECK(e.m_orbv[ib] == 0.0 && e.m_orbv[f0 + 3] == 0.0, "no signal while the range is still settling");
      CHECK(e.m_orbv[i1] > 0.0, "settled range + bullish close above the high -> LONG");
      CHECK(e.m_orbv[i2] == 0.0, "second bullish break the same day is ignored (one long per day)");
      CHECK(e.m_orbv[i3] < 0.0, "bearish close below the low -> SHORT (one short per day allowed)");
      CHECK(near(e.m_orbhi[i1], 4010.0), "final high level unchanged by the breakout candle");
   }
   {  // B: a breakout BEFORE the range has settled extends the range instead of signalling
      std::vector<ScriptBar> d = {
         {1, 4000, 4010, 3996, 4005},
         {2, 4005, 4016, 4004, 4015},     // bullish new high while unsettled -> EXTENDS the range to 4016
         {3, 4014, 4015, 4008, 4010},
         {4, 4010, 4014, 4006, 4011},
         {5, 4011, 4015, 4007, 4012},
         {6, 4012, 4015, 4008, 4013},     // 4 quiet candles after the extension -> high side final at 4016
         {7, 4013, 4022, 4012, 4020}};    // bullish close above 4016 -> LONG
      CXauEngine e; int f0;
      orb_engine(e, d, f0);
      CHECK(near(e.m_orbhi[f0 + 2], 4016.0), "unsettled breakout extends the range high to 4016");
      bool early = false;
      for(int k = 1; k <= 5; k++) if(e.m_orbv[f0 + k] != 0.0) early = true;
      CHECK(!early, "no signal until the extended range has been quiet long enough");
      CHECK(e.m_orbv[f0 + 6] > 0.0, "signal once the extended range is final and price closes above 4016");
   }
   {  // C: spike-wick guard: a huge upper wick on the first candle is ignored (body edge used)
      std::vector<ScriptBar> d = {
         {1, 4000, 4030, 3996, 4005},     // wick to 4030 (25 above the body): far more than 0.5 ATR
         {2, 4004, 4008, 3998, 4003},
         {3, 4003, 4008, 3999, 4004},
         {4, 4004, 4007, 3998, 4002},
         {5, 4003, 4014, 4002, 4013}};    // close 4013: above the body high 4005, below the wick 4030
      CXauEngine e; int f0;
      orb_engine(e, d, f0);
      CHECK(near(e.m_orbhi[f0 + 2], 4005.0), "spike wick ignored: range high = body high 4005, not 4030");
      CHECK(e.m_orbv[f0 + 4] > 0.0, "breakout is measured from the body edge, so 4013 breaks out");
   }
   {  // D: solo mode turns the vote into a tradable signal with a full plan
      std::vector<ScriptBar> d = {
         {1, 4000, 4010, 3996, 4005}, {2, 4004, 4008, 3998, 4003}, {3, 4003, 4008, 3999, 4004},
         {4, 4004, 4007, 3998, 4002}, {5, 4003, 4016, 4002, 4015}};
      CXauEngine e; int f0;
      orb_engine(e, d, f0);
      e.cfg.orb_solo = 1; e.cfg.use_session_filter = false; e.cfg.min_grade = 1;
      XSignal sg;
      const bool ok = e.Evaluate(f0 + 4, sg);
      CHECK(ok && sg.dir > 0 && sg.primary == XM_ORB && sg.risk > 0.0 && sg.sl < sg.entry && sg.tp2 > sg.tp1, "solo mode: ORB long becomes a signal with stop below and targets above");
      e.cfg.orb_need_bias = 1;
      CHECK(!e.Evaluate(f0 + 4, sg), "solo mode with 'need trend bias' rejects it when the higher timeframe is neutral");
   }
   {  // E: paper ledger resolves signals and reports recovery
      CXPaper pl;
      CHECK(!pl.Recovered(), "empty ledger has not recovered");
      pl.rn = 3; pl.res[0] = -1.0; pl.res[1] = 0.5; pl.res[2] = 1.75;
      CHECK(pl.Recovered(), "last three paper trades -1, +0.5, +1.75 -> recovered");
      pl.res[0] = -1.0; pl.res[1] = -1.0; pl.res[2] = 0.5;
      CHECK(!pl.Recovered(), "last three -1, -1, +0.5 -> not recovered");
      // end-to-end: add a signal to the ledger and let a rising market resolve it
      std::vector<ScriptBar> d = {{1, 4000, 4010, 3996, 4005}, {2, 4004, 4008, 3998, 4003}, {3, 4003, 4008, 3999, 4004},
                                  {4, 4004, 4007, 3998, 4002}, {5, 4003, 4016, 4002, 4015}, {6, 4015, 4060, 4014, 4058}, {7, 4058, 4090, 4055, 4085}};
      CXauEngine e; int f0;
      orb_engine(e, d, f0);
      CXPaper q;
      q.Add(e.m_t[f0 + 4], 1, 4008.0);
      q.Update(e);
      CHECK(q.pn == 0 && q.rn == 1 && q.res[0] > 0.0, "paper long that runs to target is resolved as a winner and removed from the pending list");
   }
}

static void test_causality()
{
   std::printf("\n== causality: signals on truncated data must equal signals on full data ==\n");
   Series S = make_series(W_TREND, 24000, 7);
   CXauEngine full, part;
   load(full, S, 24000);
   const int M = 17000;
   load(part, S, M);
   int nsig = 0, mism = 0, vmis = 0;
   for(int i = full.cfg.warmup; i < M; i++)
   {
      for(int m = 0; m < XM_COUNT; m++)
         if(!near(full.m_vote[i * XM_COUNT + m], part.m_vote[i * XM_COUNT + m], 1e-12)) vmis++;
      XSignal a, b;
      const bool sa = full.Evaluate(i, a), sb = part.Evaluate(i, b);
      if(sa) nsig++;
      if(sa != sb || a.dir != b.dir || a.grade != b.grade || !near(a.sl, b.sl, 1e-9)) mism++;
   }
   std::printf("  bars compared: %d, signals: %d\n", M - full.cfg.warmup, nsig);
   CHECK(nsig > 20, "enough signals to make the comparison meaningful");
   CHECK(vmis == 0, "every module vote identical on truncated vs full history");
   CHECK(mism == 0, "every signal (dir/grade/SL) identical on truncated vs full history");
}


// The indicator analyses 6000 bars, the EA 3000. Recursive indicators (EMA, ATR, ADX) start at different
// points, so verify the signals on the recent bars are the same regardless of the window length.
static void test_window_consistency()
{
   std::printf("\n== window consistency: same signals whether 3000, 6000 or all bars are loaded ==\n");
   const int N = 24000;
   int cmp = 0, sig = 0, m6 = 0, m3 = 0;
   for(unsigned seed = 11; seed < 21; seed++)
   {
      Series S = make_series(W_TREND, N, seed);
      CXauEngine full, w6, w3;
      load(full, S, N);
      auto load_window = [&](CXauEngine &e, int win)
      {
         std::vector<MqlRates> base(S.m15.begin() + (N - win), S.m15.begin() + N);
         const int need_h = (int)((double)win * 900 / 3600) + 320;
         std::vector<MqlRates> h = htf_upto(S, N - 1);
         if((int)h.size() > need_h) h.erase(h.begin(), h.end() - need_h);
         e.cfg.Defaults();
         e.SetBase(base, win);
         e.SetHTF(h, (int)h.size());
         e.Compute();
      };
      load_window(w6, 6000);
      load_window(w3, 3000);
      for(int back = 1; back <= 2600; back++)
      {
         XSignal a, b, c;
         const bool sa = full.Evaluate(N - back, a);
         const bool sb = w6.Evaluate(6000 - back, b);
         const bool sc = (back <= 1500) ? w3.Evaluate(3000 - back, c) : sa;   // EA only acts on the newest bars
         if(back > 1500) c = a;
         cmp++;
         if(sa) sig++;
         if(sa != sb || (sa && (a.dir != b.dir || a.grade != b.grade))) m6++;
         if(sa != sc || (sa && (a.dir != c.dir || a.grade != c.grade))) m3++;
      }
   }
   std::printf("  %d closed bars compared over 10 seeds (EA window: newest 1500 bars), %d signals in the full runs\n", cmp, sig);
   std::printf("  mismatches: 6000-bar window %d, 3000-bar window %d\n", m6, m3);
   CHECK(sig >= 40, "enough signals for the comparison to mean something");
   CHECK(m6 == 0, "6000-bar window (indicator) gives identical signals to full history");
   CHECK(m3 == 0, "3000-bar window (EA) gives identical signals over the newest 1500 bars (15 trading days)");
}


#include <chrono>

static double zscore(int hit, int n) { return n > 0 ? (hit - 0.5 * n) / std::sqrt(0.25 * n) : 0.0; }

static void test_analog()
{
   std::printf("\n== analog (pattern-matching) forecaster ==\n");
   // causality: the forecast at bar q must not change when later bars are added
   {
      Series S = make_series(W_TREND, 24000, 9);
      CXauEngine full, part;
      load(full, S, 24000);
      load(part, S, 17000);
      int diff = 0, tested = 0;
      for(int q = 12000; q < 16990; q += 331)
      {
         XAnalog a, b;
         full.AnalogQuery(q, a); part.AnalogQuery(q, b);
         tested++;
         if(a.ok != b.ok || a.medoid != b.medoid || std::fabs(a.med4 - b.med4) > 1e-12 || a.dir4 != b.dir4) diff++;
      }
      std::printf("  causality: %d queries compared on truncated vs full history, %d differ\n", tested, diff);
      CHECK(diff == 0, "analog forecast identical on truncated vs full history (no look-ahead)");
   }
   // speed at indicator scale (6000 bars, audit over the last 1000 bars every 4th bar)
   {
      Series S = make_series(W_TREND, 6000, 3);
      CXauEngine e; load(e, S, 6000);
      XAnalogAudit r;
      auto t0 = std::chrono::steady_clock::now();
      e.AnalogAudit(5998, 1000, 4, r);
      XAnalog a; e.AnalogQuery(5998, a);
      auto t1 = std::chrono::steady_clock::now();
      std::printf("  audit + live query on 6000 bars: %.0f ms\n", std::chrono::duration<double, std::milli>(t1 - t0).count());
   }
   struct W { World w; const char *n; };
   const W worlds[] = {{W_NULL, "NULL (no edge: must be ~50%)"}, {W_TREND, "TREND"}, {W_MEANREV, "MEANREV"}, {W_MIXED, "MIXED"}};
   for(const W &x : worlds)
   {
      long n1 = 0, h1 = 0, nc1 = 0, hc1 = 0, n4 = 0, h4 = 0, nc4 = 0, hc4 = 0, bn4 = 0, bh4 = 0, bn1 = 0, bh1 = 0;
      for(int sd = 1; sd <= 5; sd++)
      {
         Series S = make_series(x.w, 14000, 500 + sd);
         CXauEngine e; load(e, S, 14000);
         XAnalogAudit r;
         e.AnalogAudit(13990, 12000, 3, r);
         n1 += r.n1; h1 += r.hit1; nc1 += r.nc1; hc1 += r.hitc1; n4 += r.n4; h4 += r.hit4; nc4 += r.nc4; hc4 += r.hitc4;
         int tn, th;
         e.ForecastAudit(4, 1.0, 2000, 13990, tn, th); bn4 += tn; bh4 += th;
         e.ForecastAudit(1, 1.0, 2000, 13990, tn, th); bn1 += tn; bh1 += th;
      }
      std::printf("  %-32s next bar: all %.1f%% (n=%ld) confident %.1f%% (n=%ld) | +4 bars: all %.1f%% confident %.1f%% (n=%ld, z=%+.1f) | old drift model: next %.1f%%, +4 %.1f%%\n",
                  x.n, 100.0 * h1 / std::max(1L, n1), n1, 100.0 * hc1 / std::max(1L, nc1), nc1,
                  100.0 * h4 / std::max(1L, n4), 100.0 * hc4 / std::max(1L, nc4), nc4, zscore((int)hc4, (int)nc4),
                  100.0 * bh1 / std::max(1L, bn1), 100.0 * bh4 / std::max(1L, bn4));
      if(x.w == W_NULL)
      {
         CHECK(std::fabs(zscore((int)h4, (int)n4)) < 3.5 && std::fabs(zscore((int)h1, (int)n1)) < 3.5, "no-edge world: analog hit-rate is a coin flip (no leakage)");
         CHECK(zscore((int)hc4, (int)nc4) < 3.5, "no-edge world: even the 'confident' calls do not beat a coin flip");
      }
   }
}

static void print_stats(const char *name, const XStats &s)
{
   std::printf("  %-18s n=%4d  win%%=%5.1f  TP1%%=%5.1f  expR=%+6.3f (se %.3f)  PF=%5.2f  holdMed=%3d bars\n",
               name, s.n, s.WinRate(), s.Tp1Rate(), s.Expectancy(), s.ExpStdErr(), s.ProfitFactor(), s.HoldPct(false, 0.5));
}

static void run_world(World w, const char *label, int seeds, int nbars)
{
   std::printf("\n== world: %s  (%d seeds x %d M15 bars ~ %.1f years each) ==\n", label, seeds, nbars, nbars / 96.0 / 252.0 * 1.0);
   XTrial agg;
   agg.Reset();
   long long sig = 0, days = 0;
   for(int sd = 1; sd <= seeds; sd++)
   {
      Series S = make_series(w, nbars, 1000 + sd);
      CXauEngine e;
      load(e, S, nbars);
      XTrial tr;
      e.RunTrial(e.cfg.warmup, nbars - 2, tr);
      auto merge = [](XStats &a, const XStats &b)
      {
         a.n += b.n; a.wins += b.wins; a.losses += b.losses; a.scratch += b.scratch; a.tp1_hits += b.tp1_hits;
         a.sum_r += b.sum_r; a.sum_r2 += b.sum_r2; a.sum_win += b.sum_win; a.sum_loss += b.sum_loss; a.sum_mfe += b.sum_mfe;
         for(int i = 0; i < b.nh_all && a.nh_all < XHOLD_MAX; i++) a.hold_all[a.nh_all++] = b.hold_all[i];
         for(int i = 0; i < b.nh_win && a.nh_win < XHOLD_MAX; i++) a.hold_win[a.nh_win++] = b.hold_win[i];
      };
      merge(agg.all, tr.all);
      for(int m = 0; m < XM_COUNT; m++) merge(agg.mod[m], tr.mod[m]);
      for(int g = 0; g < 4; g++) merge(agg.grade[g], tr.grade[g]);
      sig += tr.all.n;
      days += (nbars - e.cfg.warmup) / 96 * 5 / 7;
   }
   print_stats("COMPOSITE", agg.all);
   for(int g = 1; g <= 3; g++)
   {
      char nm[32]; std::snprintf(nm, sizeof nm, "  grade %s", XGradeName(g).c_str());
      print_stats(nm, agg.grade[g]);
   }
   for(int m = 0; m < XM_COUNT; m++) print_stats(XModuleName(m).c_str(), agg.mod[m]);
   std::printf("  composite trades per trading day: %.2f\n", agg.all.n / (double)std::max<long long>(1, days * 7 / 5 * 5 / 7));
   if(w == W_NULL)
   {
      // A no-edge world must not show a significantly positive expectancy.
      const double z = agg.all.Expectancy() / std::max(agg.all.ExpStdErr(), 1e-9);
      std::printf("  composite z-score of expectancy vs 0: %+.2f\n", z);
      CHECK(z < 3.0, "no-edge world: composite expectancy is NOT significantly positive (no look-ahead leak)");
      for(int m = 0; m < XM_COUNT; m++)
      {
         if(agg.mod[m].n < 50) continue;
         const double zm = agg.mod[m].Expectancy() / std::max(agg.mod[m].ExpStdErr(), 1e-9);
         char msg[96]; std::snprintf(msg, sizeof msg, "no-edge world: module %s not significantly positive (z=%+.2f)", XModuleShort(m).c_str(), zm);
         CHECK(zm < 3.5, msg);
      }
   }
}


// Walk-forward gating: trial on the previous segment switches modules off for the next one.
static void run_gating(World w, const char *label, int seeds, int nbars, int seg, double min_exp, int min_trades)
{
   std::printf("\n== walk-forward gating on %s (segment=%d bars, gate: n>=%d & expR<%.2f) ==\n", label, seg, min_trades, min_exp);
   XStats plain, gated;
   plain.Reset(); gated.Reset();
   double off_total = 0.0; int nseg = 0;
   for(int sd = 1; sd <= seeds; sd++)
   {
      Series S = make_series(w, nbars, 2000 + sd);
      CXauEngine e;
      load(e, S, nbars);
      for(int k = 1; (k + 1) * seg <= nbars - 2; k++)
      {
         XTrial prev, oos_plain, oos_gated;
         for(int m = 0; m < XM_COUNT; m++) e.cfg.en[m] = 1;
         e.ComputeScores();
         e.RunTrial(k * seg - seg, k * seg, prev);              // in-sample: previous segment
         e.RunTrial(k * seg, (k + 1) * seg, oos_plain);         // out-of-sample, no gating
         off_total += e.ApplyGating(prev, min_trades, min_exp);
         e.RunTrial(k * seg, (k + 1) * seg, oos_gated);         // out-of-sample, gated
         nseg++;
         auto add = [](XStats &a, const XStats &b) { a.n += b.n; a.wins += b.wins; a.losses += b.losses; a.scratch += b.scratch; a.tp1_hits += b.tp1_hits; a.sum_r += b.sum_r; a.sum_r2 += b.sum_r2; a.sum_win += b.sum_win; a.sum_loss += b.sum_loss; for(int q = 0; q < b.nh_all && a.nh_all < XHOLD_MAX; q++) a.hold_all[a.nh_all++] = b.hold_all[q]; };
         add(plain, oos_plain.all);
         add(gated, oos_gated.all);
      }
   }
   print_stats("no gating (OOS)", plain);
   print_stats("gated (OOS)", gated);
   std::printf("  avg modules switched off per segment: %.2f\n", off_total / std::max(1, nseg));
}

int main(int argc, char **argv)
{
   const char *mode = (argc > 1) ? argv[1] : "all";
   const bool all = !std::strcmp(mode, "all");
   if(all || !std::strcmp(mode, "units"))   { test_units(); test_platform(); test_time_and_filters(); test_orb(); }
   if(all || !std::strcmp(mode, "causal"))  { test_causality(); test_window_consistency(); }
   if(all || !std::strcmp(mode, "null"))    run_world(W_NULL,    "NULL - random walk, no edge exists", 6, 40000);
   if(all || !std::strcmp(mode, "trend"))   run_world(W_TREND,   "TREND - persistent drift regimes (edge planted)", 6, 40000);
   if(all || !std::strcmp(mode, "meanrev")) run_world(W_MEANREV, "MEANREV - price pulled back to a moving anchor", 6, 40000);
   if(all || !std::strcmp(mode, "analog"))  test_analog();
   if(all || !std::strcmp(mode, "orb"))     run_orb_worlds();
   if(all || !std::strcmp(mode, "veto"))    run_veto_ab();
   if(all || !std::strcmp(mode, "turbo"))   run_turbo();
   if(all || !std::strcmp(mode, "filters")) run_filter_ab();
   if(all || !std::strcmp(mode, "gating"))
   {
      run_gating(W_NULL,  "NULL",  6, 40000, 6000, -0.25, 20);
      run_gating(W_MIXED, "MIXED (trend/mean-revert alternating)", 6, 40000, 6000, -0.25, 20);
   }
   std::printf("\n%s (%d failed checks)\n", g_fail ? "FAILURES" : "ALL CHECKS PASSED", g_fail);
   return g_fail ? 1 : 0;
}
