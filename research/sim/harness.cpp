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
enum World { W_NULL = 0, W_TREND = 1, W_MEANREV = 2, W_MIXED = 3, W_BULL = 4 };

struct Series
{
   std::vector<MqlRates> m15;
   std::vector<MqlRates> h1;
   std::vector<MqlRates> m1;        // minute bars (only with keep_m1)
   std::vector<int>      m15_first; // index of the first minute of each M15 bar
};

static double hour_profile(int h)
{
   static const double p[24] = {0.55, 0.55, 0.55, 0.6, 0.6, 0.65, 0.8, 1.1, 1.3, 1.3, 1.0, 1.0,
                                1.3,  1.9,  1.6,  1.5, 1.2, 0.95, 0.9, 0.85, 0.7, 0.6, 0.55, 0.5};
   return p[h];
}

static Series make_series(World w, int nbars_m15, unsigned seed, bool keep_m1 = false)
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
      if(ew == W_BULL) drift = 0.008 * sig1;          // steady bull market, roughly +70% a year
      else if(ew == W_TREND)
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
         if(keep_m1) S.m15_first.push_back((int)S.m1.size());
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
      if(keep_m1)
      {
         MqlRates m{};
         m.time = t; m.open = o1; m.high = hi1; m.low = lo1; m.close = price; m.tick_volume = vol1;
         S.m1.push_back(m);
      }
      t += 60;
   }
   if(keep_m1) { S.m15_first.resize(S.m15.size() + 1); S.m15_first[S.m15.size()] = (int)S.m1.size(); }
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

   // the bug seen on a live MetaQuotes-Demo screen: tick value reported 10x too small
   g_mock_tick_value = 0.1;
   XPlanLots("XAUUSD", 10000.0, 1.0, 10.0, true, 4000.0, 1.5, 0.0, 9000.0, 0.5, p);
   CHECK(p.ok && near(p.lots, 0.10) && near(p.risk_pct, 1.0, 1e-6) && p.src_note.size() > 0,
         "broker tick value 10x too small: sizing still 0.10 lot (broker profit formula), and the mismatch is reported");
   XPlanLots("XAUUSD", 53.93, 1.0, 14.18, false, 4191.60, 1000.0, 0.0, 100.0, 1.0, p);
   CHECK(p.ok && near(p.lots, 0.01) && near(p.risk_money, 14.18, 1e-6), "screenshot case: 0.01 lot with a $14.18 stop loses $14.18, not $1.42");
   XPlanLots("XAUUSD", 53.93, 1.0, 14.18, false, 4191.60, 1000.0, 0.0, -29.77, 1.0, p);
   CHECK(!p.ok && near(p.risk_money, 14.18, 1e-6) && p.note.find("margin") != std::string::npos,
         "negative free margin (screenshot: open trades use it all): size still reported, but the trade is refused");
   g_mock_calcprofit_ok = false;
   XPlanLots("XAUUSD", 10000.0, 1.0, 10.0, true, 4000.0, 1.5, 0.0, 9000.0, 0.5, p);
   CHECK(p.ok && near(p.lots, 0.10), "profit formula unavailable: falls back to contract size, still 0.10 lot");
   g_mock_calcprofit_ok = true;
   g_mock_tick_value = 1.0;

   // panel lines: MT5 cuts a label after 63 characters, so long lines must wrap
   {
      CXPanel pn;
      pn.Begin();
      pn.Line("RISK: 2 open trades have NO stop loss; margin level 79% (broker closes trades at 50%) and more words", 0);
      pn.Line("short line", 0);
      bool fit = true;
      for(int k = 0; k < pn.Rows(); k++) if(StringLen(pn.Text(k)) > 63) fit = false;
      CHECK(pn.Rows() == 3 && fit && pn.Text(1).find("  ") == 0 && pn.Text(2) == "short line",
            "panel wraps a 100-character line into rows of at most 63 characters (MT5 label limit)");
   }

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


static void merge_stats(XStats &a, const XStats &b)
{
   a.n += b.n; a.wins += b.wins; a.losses += b.losses; a.scratch += b.scratch; a.tp1_hits += b.tp1_hits;
   a.sum_r += b.sum_r; a.sum_r2 += b.sum_r2; a.sum_win += b.sum_win; a.sum_loss += b.sum_loss; a.sum_mfe += b.sum_mfe;
   for(int i = 0; i < b.nh_all && a.nh_all < XHOLD_MAX; i++) a.hold_all[a.nh_all++] = b.hold_all[i];
}

static void run_lab_world(World w, const char *label, int seeds, int nbars, bool print_cells)
{
   std::printf("\n== Strategy Lab on world %s (%d seeds x %d M15 bars, target 60%% wins, min 50 trades, 5 folds) ==\n", label, seeds, nbars);
   XStats cells[XLAB_CELLS], autoo;
   for(int c = 0; c < XLAB_CELLS; c++) cells[c].Reset();
   autoo.Reset();
   int qual = 0, folds = 0, picks[XLAB_CELLS];
   for(int c = 0; c < XLAB_CELLS; c++) picks[c] = 0;
   for(int sd = 1; sd <= seeds; sd++)
   {
      Series S = make_series(w, nbars, 9000 + sd);
      CXauEngine e; load(e, S, nbars);
      e.RunLab(e.cfg.warmup, nbars - 2, 60.0, 50, 5);
      for(int c = 0; c < XLAB_CELLS; c++) merge_stats(cells[c], e.lab[c].all);
      merge_stats(autoo, e.lab_auto);
      qual += e.lab_qualified; folds += e.lab_auto_folds;
      if(e.lab_pick_s >= 0) picks[e.lab_pick_s * XP_COUNT + e.lab_pick_p]++;
   }
   if(print_cells)
   {
      std::printf("  %-24s", "strategy \\ exit");
      for(int p = 0; p < XP_COUNT; p++) std::printf(" | %-22s", XExitName(p).c_str());
      std::printf("\n");
      for(int st = 0; st < XS_COUNT; st++)
      {
         std::printf("  %-24s", XStratName(st).c_str());
         for(int p = 0; p < XP_COUNT; p++)
         {
            const XStats &x = cells[st * XP_COUNT + p];
            const bool good = x.n >= 30 && x.WinRate() >= 60.0 && x.Expectancy() > 0.0;
            std::printf(" | %s%4.0f%% %+6.3fR n=%-5d", good ? "*" : " ", x.WinRate(), x.Expectancy(), x.n);
         }
         std::printf("\n");
      }
      std::printf("  (* = at least 60%% won AND positive average R on the whole history, all seeds pooled)\n");
   }
   std::printf("  qualified cells per seed: %.1f of %d | final pick counts:", (double)qual / seeds, XLAB_CELLS);
   for(int c = 0; c < XLAB_CELLS; c++) if(picks[c]) std::printf(" [%s + %s] x%d", XStratName(c / XP_COUNT).c_str(), XExitName(c % XP_COUNT).c_str(), picks[c]);
   std::printf("\n  AUTO-PICK walk-forward (out-of-sample, honest): traded in %d of %d folds;", folds, seeds * 4);
   print_stats("", autoo);
   if(w == W_NULL)
   {
      const double z = autoo.n > 1 ? autoo.Expectancy() / std::max(autoo.ExpStdErr(), 1e-9) : 0.0;
      CHECK(z < 2.5, "no-edge world: the auto-pick's out-of-sample record is not significantly profitable (selection bias contained)");
   }
   if(w == W_TREND)
      CHECK(autoo.n >= 200 && autoo.WinRate() >= 60.0 && autoo.Expectancy() > 0.0,
            "trending world (clear edge): the auto-pick holds >= 60% wins AND positive expectancy out-of-sample");
}


static void run_lab_variants()
{
   std::printf("\n== Strategy Lab selection rules compared (auto-pick walk-forward record, 4 seeds x 30000 M15 bars, target 60%%) ==\n");
   struct V { double buf; int win; int rec; const char *name; };
   const V vs[] = {{0.0, 0, 0, "A expanding, no buffer"}, {3.0, 0, 0, "B expanding, +3pt buffer"},
                   {3.0, 2, 0, "C last 2 folds, +3pt buffer"}, {3.0, 0, 1, "D expanding, +3pt, recent fold > 0"},
                   {3.0, 2, 1, "E last 2 folds, +3pt, recent > 0"}};
   struct W { World w; const char *n; };
   const W ws[] = {{W_NULL, "null"}, {W_BULL, "bull"}, {W_TREND, "trend"}, {W_MEANREV, "meanrev"}, {W_MIXED, "mixed"}};
   for(const V &v : vs)
   {
      std::printf("  %s\n", v.name);
      for(const W &w : ws)
      {
         XStats a; a.Reset();
         int folds = 0;
         for(int sd = 1; sd <= 4; sd++)
         {
            Series S = make_series(w.w, 30000, 9000 + sd);
            CXauEngine e; load(e, S, 30000);
            e.lab_buffer = v.buf; e.lab_window = v.win; e.lab_recent = v.rec;
            e.RunLab(e.cfg.warmup, 29998, 60.0, 30, 5);
            merge_stats(a, e.lab_auto);
            folds += e.lab_auto_folds;
         }
         std::printf("    %-8s traded %2d/16 folds", w.n, folds);
         print_stats("", a);
      }
   }
}


//---------------------------------------------------------------------------
// LIVE REPLAY: what the EA would have done, day by day.
// Every server day the Strategy Lab is re-run on the previous `lab_bars` bars (exactly like the EA and the
// indicator), the pick is taken, and that day's signals of the pick are traded one at a time.
// Signals come from one engine over the whole series (tested: identical to a shorter live window).
//---------------------------------------------------------------------------
struct ReplayOut { XStats live, demo, multi, rnd; XStats multi_y[40], live_y[40]; XStats breadth[4], quoted[4]; int days, days_traded; int picks[XLAB_CELLS]; };
static int g_d1def = -1;      // env XAU_D1DEF: what "daily trend up" means (engine cfg.d1_def; -1 = engine default)
static int g_days = 0;        // env XAU_DAYS: 1 trade only while the daily trend is up, -1 only while it is not, 0 always
static int g_diag = 0;        // env XAU_DIAG=1: MULTI results by Lab breadth and by the win-rate the Lab quoted
static int g_rand_ctrl = 0;   // env XAU_RANDCTRL=1: control - random long entries (same exits) at the MULTI trade rate
static int g_multi_cap = 3;   // MULTI: every combination that passes today trades, at most this many positions at once
static double g_minstop = -1.0;   // cost-guard override for real-data runs (env XAU_MINSTOP; -1 = engine default)
static double g_target = 60.0;    // Strategy Lab win-rate target for real-data runs (env XAU_TARGET)
static double g_cost = -1.0;      // round-trip cost for real-data runs (env XAU_COST; -1 = engine default 0.30)
static double g_dip_lo = -2.0, g_dip_hi = 24.0;
static std::vector<MqlRates> g_d1;   // daily bars for the daily trend filter (env XAU_D1 = path to the D1 csv)
static int g_d1mode = -1;
static double g_swapl = 0.0, g_swaps = 0.0;  // env XAU_SWAPL / XAU_SWAPS: swap cost per oz per night            // env XAU_D1MODE (0 off, 1 with the trend, 2 buys only in an up trend; -1 = engine default)   // dip-strategy GMT window for real-data runs (env XAU_DIPWIN="17-21", "off"; -2 = default)
static double g_rp_se = 1.0, g_rp_buf = 3.0; static int g_rp_win = 0, g_rp_min = 50, g_rp_rec = 1;   // = engine defaults

static void live_replay(const std::vector<MqlRates> &base, const std::vector<MqlRates> &htf, int base_sec, int htf_sec,
                        int lab_bars, double target, int min_trades, int gmt_off, int dst, ReplayOut &o)
{
   o.live.Reset(); o.demo.Reset(); o.multi.Reset(); o.rnd.Reset(); o.days = 0; o.days_traded = 0;
   for(int y = 0; y < 40; y++) { o.multi_y[y].Reset(); o.live_y[y].Reset(); }
   for(int b = 0; b < 4; b++) { o.breadth[b].Reset(); o.quoted[b].Reset(); }
   int npass = 0;
   double quoted_win[XLAB_CELLS];
   for(int c = 0; c < XLAB_CELLS; c++) quoted_win[c] = 0.0;
   unsigned rng = 12345u;
   int busy_rnd = -1;
   bool pass_today[XLAB_CELLS];
   int busy_cell[XLAB_CELLS];
   for(int c = 0; c < XLAB_CELLS; c++) { pass_today[c] = false; busy_cell[c] = -1; }
   for(int c = 0; c < XLAB_CELLS; c++) o.picks[c] = 0;
   const int N = (int)base.size();
   CXauEngine E;
   E.cfg.Defaults(); E.cfg.base_sec = base_sec; E.cfg.htf_sec = htf_sec; E.cfg.gmt_offset_sec = gmt_off; E.cfg.dst_mode = dst;
   if(g_minstop >= 0.0) E.cfg.min_stop_cost = g_minstop;
   if(g_cost > 0.0) E.cfg.cost_price = g_cost;
   if(g_dip_lo > -2.0) { E.cfg.dip_gmt_lo = g_dip_lo; E.cfg.dip_gmt_hi = g_dip_hi; }
   if(g_d1mode >= 0) E.cfg.d1_mode = g_d1mode;
   if(g_d1def >= 0) E.cfg.d1_def = g_d1def;
   E.cfg.swap_long = g_swapl; E.cfg.swap_short = g_swaps;
   if(!g_d1.empty()) E.SetDaily(g_d1, (int)g_d1.size());
   E.SetBase(base, N);
   E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) return;
   int busy_live = -1, busy_demo = -1;
   long cur_day = -1;
   int pick_live = -1, pick_demo = -1;
   for(int i = lab_bars; i < N - 2; i++)
   {
      const long day = (long)base[i].time / 86400;
      if(day != cur_day)
      {
         cur_day = day;
         o.days++;
         // lab on the lab_bars bars that closed before today (same window rule as XRunDailyLab)
         std::vector<MqlRates> lb(base.begin() + (i - lab_bars), base.begin() + i);
         std::vector<MqlRates> lh;
         const long long upto = base[i].time;
         for(const MqlRates &h : htf) if(h.time + htf_sec <= upto && h.time >= lb.front().time - (long long)htf_sec * 400) lh.push_back(h);
         CXauEngine L;
         L.cfg = E.cfg;
         L.lab_se_k = g_rp_se; L.lab_buffer = g_rp_buf; L.lab_window = g_rp_win; L.lab_recent = g_rp_rec;
         L.SetBase(lb, (int)lb.size());
         L.SetHTF(lh, (int)lh.size());
         if(!g_d1.empty()) L.SetDaily(g_d1, (int)g_d1.size());
         pick_live = -1; pick_demo = -1;
         for(int c = 0; c < XLAB_CELLS; c++) pass_today[c] = false;
         if(L.Compute())
         {
            L.RunLab(L.cfg.warmup, L.n - 1, target, (g_rp_min > 0) ? g_rp_min : min_trades, 5);
            npass = 0;
            for(int c = 0; c < XLAB_CELLS; c++) { pass_today[c] = L.lab[c].qualified; quoted_win[c] = L.lab[c].all.WinRate(); if(pass_today[c]) npass++; }
            bool proven;
            const int c = L.LabActiveCell(min_trades, proven);
            pick_demo = c;
            if(proven) { pick_live = c; o.picks[c]++; o.days_traded++; }
         }
      }
      XSignal sg;
      XTradeResult r;
      // regime test: trade only on days of one kind (the Lab itself is unchanged)
      if((g_days > 0 && E.m_dreg[i] <= 0) || (g_days < 0 && E.m_dreg[i] > 0)) continue;
      if(pick_live >= 0 && i > busy_live)
      {
         XExit x; XMakeExit(pick_live % XP_COUNT, E.cfg, x);
         if(E.StrategySignal(pick_live / XP_COUNT, i, x, sg) && E.SimulateTradeEx(i, sg.dir, sg.sl, N - 2, x, r))
         { busy_live = r.exit_idx; if(r.closed) { o.live.Add(r); o.live_y[XClampI(XYearOfDays(base[i].time / 86400) - 2000, 0, 39)].Add(r); } }
      }
      // MULTI: every passing combination, own position each, at most g_multi_cap open at once
      {
         int open_now = 0;
         for(int c = 0; c < XLAB_CELLS; c++) if(busy_cell[c] >= i) open_now++;
         for(int c = 0; c < XLAB_CELLS && open_now < g_multi_cap; c++)
         {
            if(!pass_today[c] || i <= busy_cell[c]) continue;
            XExit x; XMakeExit(c % XP_COUNT, E.cfg, x);
            XSignal s2; XTradeResult r2;
            if(E.StrategySignal(c / XP_COUNT, i, x, s2) && E.SimulateTradeEx(i, s2.dir, s2.sl, N - 2, x, r2))
            {
               busy_cell[c] = r2.exit_idx; open_now++;
               if(r2.closed)
               {
                  o.multi.Add(r2); o.multi_y[XClampI(XYearOfDays(base[i].time / 86400) - 2000, 0, 39)].Add(r2);
                  o.breadth[(npass <= 2) ? 0 : ((npass <= 5) ? 1 : ((npass <= 10) ? 2 : 3))].Add(r2);
                  const double qw = quoted_win[c];
                  o.quoted[(qw < 55.0) ? 0 : ((qw < 60.0) ? 1 : ((qw < 65.0) ? 2 : 3))].Add(r2);
               }
            }
         }
      }
      // CONTROL: random long entries (daily trend filter applied the same way), the rider exit, ~1 per 2 days.
      // XAU_RANDCTRL=2: the same, but deterministic: the first bar at or after 08:00 GMT (London open) each day
      if(g_rand_ctrl && i > busy_rnd && E.FilterReason(i) == XR_OK && (E.cfg.d1_mode == 0 || E.m_dreg[i] > 0))
      {
         rng = rng * 1103515245u + 12345u;
         const double per_bar = 0.5 / std::max(1.0, 86400.0 / base_sec);
         const bool fire = (g_rand_ctrl == 2) ? (E.m_hour[i] >= 8.0 && (E.m_hour[i - 1] < 8.0 || E.m_hour[i - 1] > E.m_hour[i]))
                                              : ((rng >> 8) % 100000 < (unsigned)(per_bar * 100000));
         if(fire)
         {
            XExit x; XMakeExit(XP_RIDER, E.cfg, x);
            XSignal s3; s3.Reset();
            XTradeResult r3;
            if(E.BuildPlanEx(i, 1, s3, x.sl_min_atr, x.sl_max_atr, x.tp1_r, 0.0) && E.SimulateTradeEx(i, 1, s3.sl, N - 2, x, r3))
            { busy_rnd = r3.exit_idx; if(r3.closed) o.rnd.Add(r3); }
         }
      }
      if(pick_demo >= 0 && i > busy_demo)
      {
         XExit x; XMakeExit(pick_demo % XP_COUNT, E.cfg, x);
         if(E.StrategySignal(pick_demo / XP_COUNT, i, x, sg) && E.SimulateTradeEx(i, sg.dir, sg.sl, N - 2, x, r))
         { busy_demo = r.exit_idx; if(r.closed) o.demo.Add(r); }
      }
   }
}

static void print_replay(const char *label, const ReplayOut &o, double days_per_bar)
{
   (void)days_per_bar;
   std::printf("  %-10s days %4d, a proven strategy existed on %4d (%3.0f%%)\n", label, o.days, o.days_traded, o.days ? 100.0 * o.days_traded / o.days : 0.0);
   std::printf("  %-10s LIVE (proven picks only)   %.2f trades/day", "", o.days ? (double)o.live.n / o.days : 0.0);
   print_stats("", o.live);
   std::printf("  %-10s DEMO (closest pick always) %.2f trades/day", "", o.days ? (double)o.demo.n / o.days : 0.0);
   print_stats("", o.demo);
   std::printf("  %-10s MULTI (all passing, <=%d)  %.2f trades/day", "", g_multi_cap, o.days ? (double)o.multi.n / o.days : 0.0);
   print_stats("", o.multi);
   if(g_rand_ctrl)
   {
      std::printf("  %-10s CONTROL random longs, rider %.2f trades/day", "", o.days ? (double)o.rnd.n / o.days : 0.0);
      print_stats("", o.rnd);
   }
   std::printf("  %-10s by year, MULTI / LIVE avg R (trades):", "");
   for(int y = 0; y < 40; y++)
      if(o.multi_y[y].n + o.live_y[y].n > 0)
         std::printf(" %d %+.2f(%d)/%+.2f(%d)", 2000 + y, o.multi_y[y].Expectancy(), o.multi_y[y].n, o.live_y[y].Expectancy(), o.live_y[y].n);
   std::printf("\n");
   if(g_diag)
   {
      const char *bn[4] = {"1-2", "3-5", "6-10", "11+"}, *qn[4] = {"<55%", "55-60%", "60-65%", "65%+"};
      std::printf("  %-10s MULTI by strategies passing that day:", "");
      for(int b = 0; b < 4; b++) std::printf("  %s: %+.3fR (%d, %.0f%% won)", bn[b], o.breadth[b].Expectancy(), o.breadth[b].n, o.breadth[b].WinRate());
      std::printf("\n  %-10s MULTI by win-rate the Lab quoted -> real win-rate:", "");
      for(int b = 0; b < 4; b++) std::printf("  %s -> %.0f%% (%d, %+.3fR)", qn[b], o.quoted[b].WinRate(), o.quoted[b].n, o.quoted[b].Expectancy());
      std::printf("\n");
   }
   std::printf("  %-10s most used picks:", "");
   for(int k = 0; k < 3; k++)
   {
      int best = -1;
      for(int c = 0; c < XLAB_CELLS; c++)
      {
         bool seen = false;
         (void)seen;
         if(o.picks[c] > 0 && (best < 0 || o.picks[c] > o.picks[best])) best = c;
      }
      if(best < 0) break;
      std::printf(" [%s / %s: %d days]", XStratName(best / XP_COUNT).c_str(), XExitName(best % XP_COUNT).c_str(), o.picks[best]);
      const_cast<ReplayOut &>(o).picks[best] = -o.picks[best];
   }
   for(int c = 0; c < XLAB_CELLS; c++) if(o.picks[c] < 0) const_cast<ReplayOut &>(o).picks[c] = -o.picks[c];
   std::printf("\n");
}


static void run_replay_variants()
{
   std::printf("\n== LIVE REPLAY: selection strictness compared (2 seeds x 30,000 M15 bars per world) ==\n");
   struct V { double se, buf; int win, mn, rec; const char *n; };
   const V vs[] = {{0.5, 3.0, 2, 30, 0, "default: E-0.5se, +3pt, last 2 folds, 30 trades"},
                   {1.0, 3.0, 2, 30, 0, "E-1.0se"},
                   {1.0, 3.0, 2, 50, 0, "E-1.0se, 50 trades"},
                   {0.5, 3.0, 0, 30, 0, "all folds"},
                   {1.0, 3.0, 0, 50, 1, "E-1.0se, all folds, 50 trades, recent fold > 0"}};
   struct W { World w; const char *n; };
   const W ws[] = {{W_NULL, "null"}, {W_BULL, "bull"}, {W_TREND, "trend"}, {W_MIXED, "mixed"}};
   for(const V &v : vs)
   {
      g_rp_se = v.se; g_rp_buf = v.buf; g_rp_win = v.win; g_rp_min = v.mn; g_rp_rec = v.rec;
      std::printf("  %s\n", v.n);
      for(const W &w : ws)
      {
         XStats a; a.Reset(); int days = 0, dt = 0;
         for(int sd = 1; sd <= 2; sd++)
         {
            Series S = make_series(w.w, 30000, 5100 + sd);
            ReplayOut o;
            live_replay(S.m15, S.h1, 900, 3600, 10000, 60.0, 30, 0, 0, o);
            merge_stats(a, o.live); days += o.days; dt += o.days_traded;
         }
         std::printf("    %-6s traded on %3.0f%% of days, %.2f/day", w.n, days ? 100.0 * dt / days : 0.0, days ? (double)a.n / days : 0.0);
         print_stats("", a);
      }
   }
   g_rp_se = 1.0; g_rp_buf = 3.0; g_rp_win = 0; g_rp_min = 50; g_rp_rec = 1;
}


static void run_replay_confirm()
{
   std::printf("\n== LIVE REPLAY confirmation on FRESH seeds (4 seeds x 30,000 M15 bars per world) ==\n");
   struct V { double se; int win, mn, rec; const char *n; };
   const V vs[] = {{0.5, 2, 30, 0, "previous default"}, {1.0, 0, 50, 1, "strict: E-1.0se, all folds, 50 trades, recent fold > 0"}};
   struct W { World w; const char *n; };
   const W ws[] = {{W_NULL, "null"}, {W_BULL, "bull"}, {W_TREND, "trend"}, {W_MEANREV, "meanrev"}, {W_MIXED, "mixed"}};
   for(const V &v : vs)
   {
      g_rp_se = v.se; g_rp_buf = 3.0; g_rp_win = v.win; g_rp_min = v.mn; g_rp_rec = v.rec;
      std::printf("  %s\n", v.n);
      for(const W &w : ws)
      {
         XStats a; a.Reset(); int days = 0, dt = 0;
         for(int sd = 11; sd <= 14; sd++)
         {
            Series S = make_series(w.w, 30000, 6200 + sd);
            ReplayOut o;
            live_replay(S.m15, S.h1, 900, 3600, 10000, 60.0, 30, 0, 0, o);
            merge_stats(a, o.live); days += o.days; dt += o.days_traded;
         }
         std::printf("    %-7s traded on %3.0f%% of days, %.2f/day", w.n, days ? 100.0 * dt / days : 0.0, days ? (double)a.n / days : 0.0);
         print_stats("", a);
      }
   }
   g_rp_se = 1.0; g_rp_buf = 3.0; g_rp_win = 0; g_rp_min = 50; g_rp_rec = 1;
}

static void run_replay_worlds()
{
   std::printf("\n== LIVE REPLAY on synthetic worlds: the daily Strategy Lab + trading, exactly as the EA does it ==\n");
   std::printf("   (M15, 10,000-bar lab window, target 60%% wins, 3 seeds x 30,000 bars each: about 200 trading days after warm-up)\n");
   struct W { World w; const char *n; };
   const W ws[] = {{W_NULL, "null"}, {W_BULL, "bull"}, {W_TREND, "trend"}, {W_MEANREV, "meanrev"}, {W_MIXED, "mixed"}};
   for(const W &w : ws)
   {
      ReplayOut agg; agg.live.Reset(); agg.demo.Reset(); agg.days = 0; agg.days_traded = 0;
      for(int c = 0; c < XLAB_CELLS; c++) agg.picks[c] = 0;
      for(int sd = 1; sd <= 3; sd++)
      {
         Series S = make_series(w.w, 30000, 5100 + sd);
         ReplayOut o;
         live_replay(S.m15, S.h1, 900, 3600, 10000, 60.0, 30, 0, 0, o);
         merge_stats(agg.live, o.live); merge_stats(agg.demo, o.demo);
         agg.days += o.days; agg.days_traded += o.days_traded;
         for(int c = 0; c < XLAB_CELLS; c++) agg.picks[c] += o.picks[c];
      }
      print_replay(w.n, agg, 0.0);
      if(w.w == W_NULL)
      {
         const double z = agg.live.n > 1 ? agg.live.Expectancy() / std::max(agg.live.ExpStdErr(), 1e-9) : 0.0;
         CHECK(z < 2.5, "live replay, no-edge world: not significantly profitable (the daily lab does not invent an edge)");
      }
      if(w.w == W_TREND)
         CHECK(agg.live.n >= 100 && agg.live.WinRate() >= 60.0 && agg.live.Expectancy() > 0.0,
               "live replay, trending world: >= 60% winning trades AND positive expectancy");
      if(w.w == W_BULL)
         CHECK(agg.live.n >= 100 && agg.live.WinRate() >= 60.0, "live replay, bull world: >= 60% winning trades");
   }
}

//---------------------------------------------------------------------------
// REAL DATA: CSV files written by MQL5/Scripts/XAU_DataExport.mq5
//---------------------------------------------------------------------------
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

// daily trend filter: no look-ahead, and the modes do what they say
static std::vector<MqlRates> aggregate(const std::vector<MqlRates> &v, int htf_sec);

static void test_daily_filter()
{
   std::printf("\n== unit tests: daily trend filter ==\n");
   Series S = make_series(W_TREND, 40000, 21);
   std::vector<MqlRates> d1 = aggregate(S.m15, 86400);
   CXauEngine e;
   load(e, S, (int)S.m15.size());
   e.cfg.d1_sma = 50;
   e.SetDaily(d1, (int)d1.size());
   e.Compute();
   int known = 0, up = 0;
   for(int i = 0; i < e.n; i++) if(e.m_dreg[i] != 0) { known++; if(e.m_dreg[i] > 0) up++; }
   CHECK(known > e.n / 2 && up > 0 && up < known, "daily trend known for most bars, both up and down phases present");
   // truncating the daily series at each bar's close changes nothing (no look-ahead)
   bool same = true;
   for(int t = 0; t < 40 && same; t++)
   {
      const int i = e.cfg.warmup + (int)((long long)t * (e.n - e.cfg.warmup - 1) / 40);
      std::vector<MqlRates> cut;
      for(const MqlRates &r : d1) if(r.time + 86400 <= e.m_t[i] + e.cfg.base_sec) cut.push_back(r);
      CXauEngine f;
      load(f, S, (int)S.m15.size());
      f.cfg.d1_sma = 50;
      f.SetDaily(cut, (int)cut.size());
      f.Compute();
      if(f.m_dreg[i] != e.m_dreg[i]) same = false;
   }
   CHECK(same, "daily trend at a bar uses only daily bars completed by that bar's close");
   int sells2 = 0, buys_down2 = 0, against1 = 0, sig0 = 0, sig2 = 0;
   for(int mode = 0; mode <= 2; mode++)
   {
      e.cfg.d1_mode = mode;
      for(int st = 0; st < XS_COUNT; st++)
         for(int i = e.cfg.warmup + 10; i < e.n - 2; i++)
         {
            const int d = e.StrategyDir(st, i);
            if(d == 0) continue;
            if(mode == 0) sig0++;
            if(mode == 2) { sig2++; if(d < 0) sells2++; if(d > 0 && e.m_dreg[i] <= 0) buys_down2++; }
            if(mode == 1 && d != e.m_dreg[i]) against1++;
         }
   }
   CHECK(sells2 == 0 && buys_down2 == 0 && sig2 > 0 && sig2 < sig0, "BUYS ONLY: no sells, no buys in a daily downtrend, fewer signals than unfiltered");
   CHECK(against1 == 0, "WITH THE TREND: no signal against the daily trend");
   e.cfg.d1_mode = 2;
   int d1_reason = 0;
   for(int i = e.cfg.warmup + 10; i < e.n - 2 && d1_reason == 0; i++)
   {
      XExit x; XMakeExit(XP_CLASSIC, e.cfg, x);
      XSignal sg;
      if(!e.StrategySignal(XS_DIP, i, x, sg) && sg.reason == XR_D1) d1_reason++;
   }
   CHECK(d1_reason > 0, "a filtered signal reports the reason 'against the daily trend'");
}

// calibrated projection: the 20-80% cone should hold the later price about 60% of the time
static void test_forecast_calibration()
{
   std::printf("\n== unit tests: calibrated forecast cone ==\n");
   Series S = make_series(W_NULL, 30000, 5);
   CXauEngine e;
   load(e, S, (int)S.m15.size());
   const int cal = e.n - 4000;
   e.CalibrateForecast(cal, 3000);
   CHECK(e.fc_cal_ok && e.fcz_lo[0] < e.fcz_md[0] && e.fcz_md[0] < e.fcz_hi[0] && e.fc_krange > 0.3, "calibration produced ordered percentiles and a size factor");
   int in1 = 0, in3 = 0, tot = 0;
   bool widening = true;
   for(int i = cal; i < e.n - 10; i++)
   {
      e.ForecastRange(i, e.m_c[i], e.m_t[i + 1], 4);
      if(e.rg_n < 4) continue;
      tot++;
      if(e.m_c[i + 1] >= e.rg_dn[0] && e.m_c[i + 1] <= e.rg_up[0]) in1++;
      if(e.m_c[i + 3] >= e.rg_dn[2] && e.m_c[i + 3] <= e.rg_up[2]) in3++;
      if(e.rg_up[3] - e.rg_dn[3] < e.rg_up[0] - e.rg_dn[0]) widening = false;
   }
   const double c1 = 100.0 * in1 / std::max(tot, 1), c3 = 100.0 * in3 / std::max(tot, 1);
   std::printf("  held-out bars %d: cone held the price %.1f%% (1 bar) and %.1f%% (3 bars), target 60%%\n", tot, c1, c3);
   CHECK(tot > 3000 && c1 > 54.0 && c1 < 66.0 && c3 > 54.0 && c3 < 66.0, "calibrated cone holds the price 54-66% of the time on bars it never saw");
   CHECK(widening, "the cone widens with the horizon");
}

static void test_csv_roundtrip()
{
   std::printf("\n== real-data loader: CSV round trip (the format XAU_DataExport.mq5 writes) ==\n");
   Series S = make_series(W_TREND, 3000, 3);
   const char *path = "/tmp/xau_roundtrip_M15.csv";
   FILE *f = std::fopen(path, "w");
   std::fprintf(f, "time,open,high,low,close,tick_volume,spread\n");
   for(const MqlRates &r : S.m15)
      std::fprintf(f, "%s,%.2f,%.2f,%.2f,%.2f,%lld,%d\n", TimeToString(r.time).c_str(), r.open, r.high, r.low, r.close, (long long)r.tick_volume, r.spread);
   std::fclose(f);
   std::vector<MqlRates> back;
   const bool ok = load_csv(path, back);
   CHECK(ok && back.size() == S.m15.size() && back[100].time == S.m15[100].time && std::fabs(back[100].close - S.m15[100].close) < 0.006,
         "CSV written in the export format loads back with identical times and prices");
   CHECK(bar_seconds(back) == 900, "bar size detected as M15");
   std::remove(path);
}

// Higher-timeframe bars built from the base bars (weeks start on Sunday, like MT5's W1).
static std::vector<MqlRates> aggregate(const std::vector<MqlRates> &v, int htf_sec)
{
   std::vector<MqlRates> out;
   for(const MqlRates &r : v)
   {
      long long start;
      if(htf_sec == 604800) { const long long d = r.time / 86400; start = (d - ((d + 4) % 7)) * 86400LL; }
      else start = r.time - (r.time % htf_sec);
      if(out.empty() || out.back().time != start)
      {
         MqlRates b = r; b.time = start; out.push_back(b);
      }
      else
      {
         MqlRates &b = out.back();
         b.high = std::max(b.high, r.high); b.low = std::min(b.low, r.low); b.close = r.close; b.tick_volume += r.tick_volume;
      }
   }
   return out;
}

static int run_real(int argc, char **argv)
{
   // harness real <base.csv> <higher_tf.csv | auto> [gmt_winter_hours=2] [dst 0 fixed / 1 US / 2 EU = 1] [lab_bars=10000]
   if(argc < 4) { std::printf("usage: harness real BASE.csv HIGHER_TF.csv|auto [gmt_winter_hours] [dst 0/1/2] [lab_bars]\n"); return 2; }
   std::vector<MqlRates> base, htf;
   if(!load_csv(argv[2], base)) { std::printf("cannot read %s\n", argv[2]); return 2; }
   base.pop_back();                                  // the export ends with the still-forming bar
   if(std::getenv("XAU_AGG") && std::atoi(std::getenv("XAU_AGG")) > 0)
   {
      // build a longer timeframe from the file (e.g. M30 from M15); the last aggregated bar may be incomplete
      base = aggregate(base, std::atoi(std::getenv("XAU_AGG")));
      base.pop_back();
   }
   const int bs = bar_seconds(base);
   int hs;
   if(!std::strcmp(argv[3], "auto"))
   {
      hs = (bs >= 86400) ? 604800 : ((bs >= 3600) ? 14400 : 3600);
      htf = aggregate(base, hs);
      htf.pop_back();                                // last higher-timeframe bar is incomplete
   }
   else
   {
      if(!load_csv(argv[3], htf)) { std::printf("cannot read %s\n", argv[3]); return 2; }
      htf.pop_back();
      hs = bar_seconds(htf);
   }
   const int gmt = (int)((argc > 4 ? std::atof(argv[4]) : 2.0) * 3600);
   const int dst = argc > 5 ? std::atoi(argv[5]) : 1;
   const int lab_bars = argc > 6 ? std::atoi(argv[6]) : 10000;
   std::printf("\n== REAL DATA: %s (%zu bars of %d s), higher timeframe %d s (%zu bars) ==\n", argv[2], base.size(), bs, hs, htf.size());
   std::printf("   from %s to %s | cost per trade %.2f (price units) | cost guard %.0f costs | lab window %d bars\n",
               TimeToString(base.front().time).c_str(), TimeToString(base.back().time).c_str(), g_cost > 0.0 ? g_cost : 0.30,
               g_minstop >= 0.0 ? g_minstop : 20.0, lab_bars);
   // 1) the Strategy Lab exactly as the indicator shows it today (newest lab_bars bars)
   const int NL = std::min<int>((int)base.size(), lab_bars);
   std::vector<MqlRates> lb(base.end() - NL, base.end());
   CXauEngine L;
   L.cfg.Defaults(); L.cfg.base_sec = bs; L.cfg.htf_sec = hs; L.cfg.gmt_offset_sec = gmt; L.cfg.dst_mode = dst;
   if(g_minstop >= 0.0) L.cfg.min_stop_cost = g_minstop;
   if(g_cost > 0.0) L.cfg.cost_price = g_cost;
   if(g_dip_lo > -2.0) { L.cfg.dip_gmt_lo = g_dip_lo; L.cfg.dip_gmt_hi = g_dip_hi; }
   if(g_d1mode >= 0) L.cfg.d1_mode = g_d1mode;
   L.cfg.swap_long = g_swapl; L.cfg.swap_short = g_swaps;
   L.SetBase(lb, NL); L.SetHTF(htf, (int)htf.size());
   if(!g_d1.empty()) L.SetDaily(g_d1, (int)g_d1.size());
   if(!L.Compute()) { std::printf("not enough bars\n"); return 2; }
   L.RunLab(L.cfg.warmup, NL - 1, g_target, 50, 5);
   std::printf("  STRATEGY LAB on the newest %d bars (what the indicator shows today), all 32 combinations:\n", NL);
   for(int k = 0; k < XLAB_CELLS; k++)
   {
      const int c = L.LabRanked(k);
      if(c < 0) break;
      const XStats &x = L.lab[c].all;
      const XStats &rc = L.lab[c].recent;
      std::printf("   %s %-24s %-18s won %5.1f%%  avg %+6.3fR  PF %5.2f  n=%4d | last 40%%: won %5.1f%% avg %+6.3fR n=%d\n",
                  L.lab[c].qualified ? "PASS" : "    ", XStratName(c / XP_COUNT).c_str(), XExitName(c % XP_COUNT).c_str(),
                  x.WinRate(), x.Expectancy(), x.ProfitFactor(), x.n, rc.WinRate(), rc.Expectancy(), rc.n);
   }
   bool proven;
   const int pick = L.LabActiveCell(50, proven);
   if(pick >= 0) std::printf("  pick today: %s / %s %s\n", XStratName(pick / XP_COUNT).c_str(), XExitName(pick % XP_COUNT).c_str(), proven ? "[PROVEN]" : "[UNPROVEN]");
   std::printf("  auto-pick walk-forward (%d folds traded):", L.lab_auto_folds);
   print_stats("", L.lab_auto);
   // the old v1 composite, for comparison with the terminal screenshots (v1 used the pessimistic fill rule)
   {
      XTrial tr;
      L.cfg.path_mode = 0; L.RunTrial(L.cfg.warmup, NL - 1, tr);
      std::printf("  v1 confluence + classic exit, v1 fill rule:");
      print_stats("", tr.all);
      L.cfg.path_mode = 1; L.RunTrial(L.cfg.warmup, NL - 1, tr);
      std::printf("  v1 confluence + classic exit, v2 fill rule:");
      print_stats("", tr.all);
   }
   // 2) forecaster audit
   XAnalogAudit au;
   L.AnalogAudit(NL - 1, std::min(NL - 600, 4000), 2, au);
   std::printf("  pattern-match forecast (walk-forward): next bar %.1f%% right (n=%d), 4 bars %.1f%% (n=%d); confident 4-bar calls %.1f%% (n=%d)\n",
               100.0 * au.Rate(au.hit1, au.n1), au.n1, 100.0 * au.Rate(au.hit4, au.n4), au.n4, 100.0 * au.Rate(au.hitc4, au.nc4), au.nc4);
   // 3) live replay over the file
   if((int)base.size() > lab_bars + 200)
   {
      ReplayOut o;
      live_replay(base, htf, bs, hs, lab_bars, g_target, 50, gmt, dst, o);
      std::printf("  LIVE REPLAY from %s (daily Lab on the previous %d bars, trading its pick, as the EA does):\n",
                  TimeToString(base[lab_bars].time).c_str(), lab_bars);
      print_replay("real", o, 0.0);
   }
   return 0;
}


// Fixed strategies on real data, split into time blocks: is an edge stable or one lucky stretch?
static int run_real_blocks(int argc, char **argv)
{
   if(argc < 3) { std::printf("usage: harness realblocks BASE.csv [years_per_block=4]\n"); return 2; }
   std::vector<MqlRates> base;
   if(!load_csv(argv[2], base)) return 2;
   base.pop_back();
   const int yrs = argc > 3 ? std::atoi(argv[3]) : 4;
   const int bs = bar_seconds(base);
   const int hs = (bs >= 86400) ? 604800 : ((bs >= 3600) ? 14400 : 3600);
   std::vector<MqlRates> htf = aggregate(base, hs);
   htf.pop_back();
   CXauEngine L;
   L.cfg.Defaults(); L.cfg.base_sec = bs; L.cfg.htf_sec = hs; L.cfg.gmt_offset_sec = 7200; L.cfg.dst_mode = 1;
   if(g_minstop >= 0.0) L.cfg.min_stop_cost = g_minstop;
   if(g_cost > 0.0) L.cfg.cost_price = g_cost;
   if(g_dip_lo > -2.0) { L.cfg.dip_gmt_lo = g_dip_lo; L.cfg.dip_gmt_hi = g_dip_hi; }
   if(g_d1mode >= 0) L.cfg.d1_mode = g_d1mode;
   L.cfg.swap_long = g_swapl; L.cfg.swap_short = g_swaps;
   L.SetBase(base, (int)base.size()); L.SetHTF(htf, (int)htf.size());
   if(!g_d1.empty()) L.SetDaily(g_d1, (int)g_d1.size());
   if(!L.Compute()) return 2;
   L.RunLab(L.cfg.warmup, (int)base.size() - 1, 60.0, 50, 5);
   const int y0 = XYearOfDays(base[L.cfg.warmup].time / 86400), y1 = XYearOfDays(base.back().time / 86400);
   std::printf("\n== REAL DATA by period: %s, blocks of %d years (won%% / avg R / trades) ==\n", argv[2], yrs);
   std::printf("  %-26s %-18s", "strategy", "exit");
   for(int y = y0; y <= y1; y += yrs) std::printf(" | %4d-%-4d          ", y, std::min(y + yrs - 1, y1));
   std::printf(" | all\n");
   for(int c = 0; c < XLAB_CELLS; c++)
   {
      if(L.lab[c].all.n < 40) continue;
      std::printf("  %-26s %-18s", XStratName(c / XP_COUNT).c_str(), XExitName(c % XP_COUNT).c_str());
      int pos_blocks = 0, blocks = 0;
      for(int y = y0; y <= y1; y += yrs)
      {
         XStats st; st.Reset();
         for(int q = 0; q < L.m_lt_cnt[c]; q++)
         {
            const int kk = c * XLAB_MAXTR + q;
            const int yy = XYearOfDays(base[L.m_lt_e[kk]].time / 86400);
            if(yy < y || yy > y + yrs - 1) continue;
            XTradeResult t; t.Reset(); t.r_net = L.m_lt_r[kk]; st.Add(t);
         }
         if(st.n >= 5) { blocks++; if(st.Expectancy() > 0.0) pos_blocks++; }
         std::printf(" | %3.0f%% %+6.3f %4d", st.WinRate(), st.Expectancy(), st.n);
      }
      std::printf(" | %3.0f%% %+6.3f %4d  (%d/%d blocks positive)\n", L.lab[c].all.WinRate(), L.lab[c].all.Expectancy(), L.lab[c].all.n, pos_blocks, blocks);
   }
   return 0;
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
      XExit qx; XMakeExit(XP_CLASSIC, e.cfg, qx);
      q.Update(e, qx);
      CHECK(q.pn == 0 && q.rn == 1 && q.res[0] > 0.0, "paper long that runs to target is resolved as a winner and removed from the pending list");
   }
}


static void test_exits()
{
   std::printf("\n== unit tests: exit profiles and candle-path fills ==\n");
   XTradeResult r;
   XExit x;
   { // bearish bar touching both: long path is O-H-L-C, so TP1 comes first, then break-even
      CXauEngine e; tiny(e, {{100,100,100,100},{100,101.5,98.5,99.0},{99,99,99,99}});
      XMakeExit(XP_CLASSIC, e.cfg, x);
      e.cfg.path_mode = 1; e.SimulateTradeEx(0, 1, 99.0, 2, x, r);
      CHECK(r.closed && near(r.r_net, 0.5), "path mode: bearish bar hits TP1 before the low -> +0.5R (half banked, rest at break-even)");
      e.cfg.path_mode = 0; e.SimulateTradeEx(0, 1, 99.0, 2, x, r);
      CHECK(r.closed && near(r.r_net, -1.0), "pessimistic mode: same bar counts as a full stop");
   }
   { // high-hit profile: 70% at 0.5R then break-even
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100.6,99.9,100.5},{100.5,100.6,99.8,99.9}});
      XMakeExit(XP_HIGHHIT, e.cfg, x);
      e.SimulateTradeEx(0, 1, 99.0, 2, x, r);
      CHECK(r.closed && near(r.r_net, 0.35), "high-hit: 70% closed at +0.5R, rest stopped at entry -> +0.35R");
   }
   { // quick profile: everything out at 0.6R
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100.7,99.9,100.6},{100.6,100.6,100.6,100.6}});
      XMakeExit(XP_QUICK, e.cfg, x);
      e.SimulateTradeEx(0, 1, 99.0, 2, x, r);
      CHECK(r.closed && near(r.r_net, 0.6) && r.exit_kind == XE_TP1_FULL, "quick: all out at +0.6R");
   }
   { // mean-reversion exit: close back above the 5-bar mean
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100.2,99.4,99.5},{99.5,100.4,99.4,100.3},{100.3,100.3,100.3,100.3}});
      ArrayResize(e.m_sma5, 4);
      e.m_sma5[0] = 100.5; e.m_sma5[1] = 100.2; e.m_sma5[2] = 100.1; e.m_sma5[3] = 100.1;
      XMakeExit(XP_MEANREV, e.cfg, x);
      e.SimulateTradeEx(0, 1, 98.0, 3, x, r);
      CHECK(r.closed && r.exit_kind == XE_MR && near(r.r_net, 0.15) && r.exit_idx == 2, "mean-revert: exits at the close that crosses the 5-bar mean (+0.3 on a 2.0 stop = +0.15R)");
   }
   { // gap through the stop fills at the open, not at the stop
      CXauEngine e; tiny(e, {{100,100,100,100},{100,100.2,99.8,100.0},{98.5,98.8,98.2,98.6}});
      XMakeExit(XP_CLASSIC, e.cfg, x);
      e.SimulateTradeEx(0, 1, 99.0, 2, x, r);
      CHECK(r.closed && near(r.r_net, -1.5), "gap below the stop fills at the open: -1.5R, not -1R");
   }
}

// Replay a trade on the underlying 1-minute bars: the "truth" the bar simulator approximates.
// Same rules as SimulateTradeEx (trail and exits at M15 closes); only the order of prices inside a bar is exact.
// entry at a given bar and price: a market entry must equal the standard simulator; a limit fill only counts the
// part of the fill bar after the fill (stop yes, targets no)
static void test_entry_at()
{
   std::printf("\n== unit tests: entry at a chosen price (limit orders) ==\n");
   Series S = make_series(W_TREND, 6000, 13);
   CXauEngine e;
   load(e, S, (int)S.m15.size());
   int same = 0, total = 0;
   for(int i = e.cfg.warmup + 10; i < e.n - 40 && total < 400; i++)
   {
      XExit x; XMakeExit(XP_CLASSIC, e.cfg, x);
      XSignal sg;
      if(!e.StrategySignal(XS_DIP, i, x, sg)) continue;
      XTradeResult a, b;
      const bool oa = e.SimulateTradeEx(i, sg.dir, sg.sl, e.n - 2, x, a);
      const bool ob = e.SimulateTradeAt(i, i + 1, e.m_o[i + 1], false, sg.dir, sg.sl, e.n - 2, x, b);
      total++;
      if(oa == ob && a.exit_idx == b.exit_idx && near(a.r_net, b.r_net, 1e-12)) same++;
   }
   CHECK(total > 20 && same == total, "a market entry through the new entry function gives exactly the old result");
   // hand-made fill bar: buy limit filled at 100, bar low 98 = stop -> stopped in the fill bar
   CXauEngine f;
   std::vector<std::vector<double>> ohlc;
   for(int k = 0; k < 400; k++) ohlc.push_back({100.0, 101.0, 99.5, 100.0});
   ohlc.push_back({101.0, 101.5, 97.5, 98.5});      // fill bar: opens above the limit, falls through 100 and the stop 98
   ohlc.push_back({98.5, 110.0, 98.0, 109.0});
   tiny(f, ohlc);
   XExit x; XMakeExit(XP_CLASSIC, f.cfg, x);
   XTradeResult r;
   const bool ok = f.SimulateTradeAt(399, 400, 100.0, true, 1, 98.0, f.n - 1, x, r);
   CHECK(ok && r.closed && r.exit_idx == 400 && r.r_net < -0.99, "a limit buy filled at 100 is stopped at 98 inside the fill bar");
   // fill bar that never reaches the stop and closes higher: no target is taken inside the fill bar
   CXauEngine g;
   std::vector<std::vector<double>> o2(ohlc.begin(), ohlc.begin() + 400);
   o2.push_back({101.0, 104.0, 99.9, 100.5});       // bearish fill bar (open-high-low-close): the high 104 came BEFORE the fill at 100
   o2.push_back({100.5, 101.0, 100.2, 100.8});      // later bars stay below the 1R target (102)
   o2.push_back({100.8, 101.2, 100.4, 101.0});
   tiny(g, o2);
   XTradeResult r2;
   g.SimulateTradeAt(399, 400, 100.0, true, 1, 98.0, g.n - 1, x, r2);
   CHECK(r2.ok && !r2.tp1_hit, "a high made before the limit fill is not counted as a target hit");
   // bullish fill bar (open-low-high-close): the high came after the fill and counts
   CXauEngine h2;
   std::vector<std::vector<double>> o3(ohlc.begin(), ohlc.begin() + 400);
   o3.push_back({101.0, 104.0, 99.9, 103.5});
   o3.push_back({103.5, 103.6, 103.0, 103.2});
   tiny(h2, o3);
   XTradeResult r3;
   h2.SimulateTradeAt(399, 400, 100.0, true, 1, 98.0, h2.n - 1, x, r3);
   CHECK(r3.ok && r3.tp1_hit && r3.bars_to_tp1 == 1, "a high made after the fill (bullish bar path) reaches the first target");
}

// cost guard: no setup may carry a stop shorter than min_stop_cost round-trip costs
static void test_today_plan()
{
   std::printf("\n== unit tests: today's plan line ==\n");
   bool go;
   std::string s = XTodayPlan(XAU_MODE_TREND, 2, true, false, 2, 1, 40.0, 20.0, go);
   CHECK(go && s.find("buys only") != std::string::npos && s.find("2 strategies armed") != std::string::npos && s.find("about 40 expected, 20 so far") != std::string::npos,
         "TREND, daily up: wait for a signal, buys only, 2 strategies armed, expected range and so far");
   s = XTodayPlan(XAU_MODE_TREND, 2, true, false, 2, -1, 40.0, 0.5, go);
   CHECK(!go && s.find("daily trend is down") != std::string::npos, "daily trend down on a buys-only chart: stand aside");
   s = XTodayPlan(XAU_MODE_STEADY, 0, false, false, 0, 0, 40.0, 38.0, go);
   CHECK(!go && s.find("no strategy passed") != std::string::npos && s.find("most of today's move is done") != std::string::npos,
         "STEADY, nothing proven: stand aside, and a used-up day is flagged");
   s = XTodayPlan(XAU_MODE_STEADY, 0, true, true, 0, 0, 0.0, 0.0, go);
   CHECK(!go && s.find("too big for the account") != std::string::npos && s.find("Today's range") == std::string::npos,
         "account too small: watch only (no range on D1+)");
   s = XTodayPlan(XAU_MODE_STEADY, 0, true, false, 0, 0, 40.0, 12.0, go);
   CHECK(go && s.find("both directions") != std::string::npos, "STEADY, proven, no daily filter: both directions");
   CHECK(s.size() < 120, "fits in two panel lines");
}

static void test_size_forecasts()
{
   std::printf("\n== unit tests: HAR candle size and today's range (round 11) ==\n");
   Series S = make_series(W_NULL, 30000, 9);
   CXauEngine e;
   load(e, S, (int)S.m15.size());
   const int cal = e.n - 4000;
   e.CalibrateForecast(cal, 3000);
   CHECK(e.har_ok && e.har_b[1] + e.har_b[2] + e.har_b[3] + e.har_b[4] > 0.2, "HAR fit found: recent ranges carry over to the next bar");
   const double nr = e.NextRange(cal, e.m_t[cal + 1]);
   CHECK(nr > 0.2 * e.m_atr[cal] && nr < 5.0 * e.m_atr[cal], "next candle size is a sensible multiple of the ATR");
   CHECK(e.dr_ok, "day-range model fitted on the past days");
   const double dfc = e.DayRangeForecast(cal), sofar = e.m_adru[cal] * e.m_adr[cal];
   CHECK(dfc >= sofar - 1e-9 && dfc > 0.0, "today's expected range is never less than what the day already made");
   // no look-ahead: change every bar after `cal` and refit at `cal`; the forecasts must not move
   Series S2 = S;
   for(size_t i = (size_t)cal + 1; i < S2.m15.size(); i++) { S2.m15[i].high += 7.0; S2.m15[i].low -= 7.0; }
   // (the hour-of-day profile is built from every loaded bar, which live are never future ones: hold it fixed here)
   CXauEngine e2;
   load(e2, S2, (int)S2.m15.size());
   for(int h = 0; h < 24; h++) e2.season[h] = e.season[h];
   e2.CalibrateForecast(cal, 3000);
   CHECK(near(e2.NextRange(cal, e2.m_t[cal + 1]), nr, 1e-9) && near(e2.DayRangeForecast(cal), dfc, 1e-9), "forecasts made at a bar ignore every later bar");
}

static void test_panel_helpers()
{
   std::printf("\n== unit tests: check row, drawdown chance, live-vs-tested alarm (round 11) ==\n");
   const std::string row = XCheckRow(true, true, true, true, true, false, true);
   CHECK(row.find("Size NO") != std::string::npos && row.find("Lab ok") != std::string::npos && row.find("Limits ok") != std::string::npos, "check row names the failing check");
   const double lo = XDrawdownChance(0.5, 0.5, 1.0, 1.0, 1.0, 100, 20.0, 4000);
   const double hi = XDrawdownChance(0.5, 0.5, 1.0, 1.0, 5.0, 100, 20.0, 4000);
   std::printf("  coin flip at 1R:1R, 100 trades: 20%% drawdown chance %.1f%% at 1%% risk, %.1f%% at 5%% risk\n", 100.0 * lo, 100.0 * hi);
   CHECK(lo > 0.01 && lo < 0.08 && hi > 0.9, "coin flip: about 4-6% at 1% risk (theory for a random walk), over 90% at 5%");
   CHECK(XDrawdownChance(1.0, 0.0, 1.0, 1.0, 5.0, 100, 20.0, 1000) == 0.0, "no losses, no drawdown");
   CHECK(XDrawdownChance(0.5, 0.5, 1.0, 1.0, 2.0, 100, 20.0, 1000) == XDrawdownChance(0.5, 0.5, 1.0, 1.0, 2.0, 100, 20.0, 1000), "same inputs, same answer");
   CHECK(XLiveDrift(20, 5, 60.0) == "", "no alarm before 30 live trades");
   CHECK(XLiveDrift(50, 28, 60.0) == "", "56% live vs 60% tested over 50 trades: within luck");
   CHECK(XLiveDrift(50, 18, 60.0) != "", "36% live vs 60% tested over 50 trades: alarm");
}

static void test_cost_guard()
{
   std::printf("\n== unit tests: cost guard (stop must be >= 20 round-trip costs) ==\n");
   Series S = make_series(W_TREND, 6000, 11);
   CXauEngine e;
   load(e, S, (int)S.m15.size());
   e.cfg.cost_price = 0.30; e.cfg.min_stop_cost = 20.0;
   int n_ok = 0, n_cost = 0, n_short = 0;
   for(int st = 0; st < XS_COUNT; st++)
      for(int i = e.cfg.warmup + 10; i < e.n - 2; i++)
      {
         XExit x; XMakeExit(XP_CLASSIC, e.cfg, x);
         XSignal sg;
         if(e.StrategySignal(st, i, x, sg)) { n_ok++; if(sg.risk < 20.0 * 0.30 - 1e-9) n_short++; }
         else if(sg.reason == XR_COST) n_cost++;
      }
   CHECK(n_ok > 0 && n_short == 0, "every accepted setup has a stop of at least 20 x 0.30 = 6.00");
   CHECK(n_cost > 0, "setups with shorter stops are refused with the reason 'stop too short for the spread'");
   e.cfg.min_stop_cost = 0.0;
   int n_off = 0;
   for(int st = 0; st < XS_COUNT; st++)
      for(int i = e.cfg.warmup + 10; i < e.n - 2; i++)
      {
         XExit x; XMakeExit(XP_CLASSIC, e.cfg, x);
         XSignal sg;
         if(e.StrategySignal(st, i, x, sg)) n_off++;
      }
   CHECK(n_off == n_ok + n_cost, "with the guard off exactly those setups come back");
}

static bool truth_trade(const Series &S, const CXauEngine &e, int i, int dir, double sl_price, const XExit &x, double &r_net)
{
   const int eidx = i + 1;
   if(eidx >= (int)S.m15.size() - 1) return false;
   const double a = e.m_atr[i];
   const double entry = S.m15[eidx].open;
   const double risk = (dir > 0) ? entry - sl_price : sl_price - entry;
   if(risk < 0.4 * a || risk <= 0.0) return false;
   const int maxh = (x.max_hold > 0) ? x.max_hold : e.MaxHold();
   const int jend = std::min((int)S.m15.size() - 2, eidx + maxh - 1);
   const bool has_tp1 = (x.tp1_r > 0.0 && x.part > 0.0);
   const double tp1f = x.tp1_r * risk, tp2f = (x.tp2_r > 0.0) ? x.tp2_r * risk : 1e300;
   double stopf = -risk, rem = 1.0, real = 0.0, ext = 0.0;
   int stage = 0;
   for(int j = eidx; j <= jend; j++)
   {
      double fhi_bar = -1e300;
      for(int m = S.m15_first[j]; m < S.m15_first[j + 1]; m++)
      {
         const MqlRates &b = S.m1[m];
         const double fo = dir * (b.open - entry);
         const double fh = (dir > 0) ? b.high - entry : entry - b.low;
         const double fl = (dir > 0) ? b.low - entry : entry - b.high;
         const double fc = dir * (b.close - entry);
         if(fh > fhi_bar) fhi_bar = fh;
         if(fo <= stopf) { real += rem * fo / risk; r_net = real - e.cfg.cost_price / risk; return true; }
         const bool bull = ((b.close >= b.open) == (dir > 0));
         double pf[4] = {fo, bull ? fl : fh, bull ? fh : fl, fc};
         for(int k = 1; k <= 3; k++)
         {
            const double fa = pf[k - 1], fb = pf[k];
            if(fb < fa && fb <= stopf) { real += rem * stopf / risk; r_net = real - e.cfg.cost_price / risk; return true; }
            if(fb > fa)
            {
               if(stage == 0 && has_tp1 && fb >= tp1f)
               {
                  real += x.part * std::max(tp1f, fa) / risk; rem = 1.0 - x.part; stage = 1; stopf = x.be_lock_r * risk; ext = fb;
                  if(rem <= 1e-9) { r_net = real - e.cfg.cost_price / risk; return true; }
               }
               if((stage == 1 || !has_tp1) && fb >= tp2f) { real += rem * std::max(tp2f, fa) / risk; r_net = real - e.cfg.cost_price / risk; return true; }
            }
         }
      }
      const double fcl = dir * (S.m15[j].close - entry);
      if(stage == 1)
      {
         if(fhi_bar > ext) ext = fhi_bar;
         if(x.trail_atr > 0.0) stopf = std::max(stopf, ext - x.trail_atr * a);
      }
      if(x.mr_exit == 1 && ((dir > 0 && S.m15[j].close > e.m_sma5[j]) || (dir < 0 && S.m15[j].close < e.m_sma5[j])))
      { real += rem * fcl / risk; r_net = real - e.cfg.cost_price / risk; return true; }
      if(j - eidx + 1 >= maxh || j == jend) { real += rem * fcl / risk; r_net = real - e.cfg.cost_price / risk; return true; }
   }
   return false;
}

static void run_calibration()
{
   std::printf("\n== simulator calibration: bar-level fills vs minute-level truth (4 seeds x 16000 M15 bars, entries every 7th bar) ==\n");
   std::printf("  %-18s %-8s %9s %9s %9s | %9s %9s %9s | %s\n", "exit profile", "world", "truthR", "pathR", "pessR", "truthW%", "pathW%", "pessW%", "mean |error| per trade: path / pessimistic");
   const World ws[2] = {W_NULL, W_TREND};
   const char *wn[2] = {"null", "trend"};
   double worst_path_bias = 0.0;
   for(int p = 0; p < XP_COUNT; p++)
      for(int wi = 0; wi < 2; wi++)
      {
         double st = 0, sp = 0, ss = 0, ep = 0, es = 0; long wt = 0, wp = 0, wsum = 0, n = 0;
         for(int sd = 1; sd <= 4; sd++)
         {
            Series S = make_series(ws[wi], 16000, 7000 + sd, true);
            CXauEngine e; load(e, S, 16000);
            XExit x; XMakeExit(p, e.cfg, x);
            for(int i = e.cfg.warmup; i < 15900; i += 7)
            {
               const int dir = (e.m_ema1[i] >= e.m_ema2[i]) ? 1 : -1;
               XSignal sg; sg.Reset();
               e.cfg.sl_atr_min = x.sl_min_atr; e.cfg.sl_atr_max = x.sl_max_atr;
               if(!e.BuildPlan(i, dir, sg)) continue;
               double rt;
               if(!truth_trade(S, e, i, dir, sg.sl, x, rt)) continue;
               XTradeResult r1, r0;
               e.cfg.path_mode = 1; const bool ok1 = e.SimulateTradeEx(i, dir, sg.sl, 15998, x, r1);
               e.cfg.path_mode = 0; const bool ok0 = e.SimulateTradeEx(i, dir, sg.sl, 15998, x, r0);
               e.cfg.path_mode = 1;
               if(!ok1 || !ok0 || !r1.closed || !r0.closed) continue;
               n++; st += rt; sp += r1.r_net; ss += r0.r_net;
               ep += std::fabs(r1.r_net - rt); es += std::fabs(r0.r_net - rt);
               if(rt > 0.05) wt++;
               if(r1.r_net > 0.05) wp++;
               if(r0.r_net > 0.05) wsum++;
            }
         }
         std::printf("  %-18s %-8s %+9.3f %+9.3f %+9.3f | %8.1f%% %8.1f%% %8.1f%% | %.3f / %.3f  (n=%ld)\n",
                     XExitName(p).c_str(), wn[wi], st / n, sp / n, ss / n, 100.0 * wt / n, 100.0 * wp / n, 100.0 * wsum / n, ep / n, es / n, n);
         worst_path_bias = std::max(worst_path_bias, std::fabs(sp / n - st / n));
      }
   CHECK(worst_path_bias < 0.05, "candle-path fills are within 0.05R of minute-level truth on average for every exit profile");
}


// The EA computes live signals on 3,000 bars, the indicator on 10,000: every strategy and exit must agree.
static void test_strategy_windows()
{
   std::printf("\n== strategy signals: 3,000-bar (EA) vs 10,000-bar (indicator) window, every strategy x exit ==\n");
   const int N = 10000;
   int cmp = 0, sig = 0, mism = 0;
   for(unsigned seed = 31; seed < 35; seed++)
   {
      Series S = make_series(W_TREND, N, seed);
      CXauEngine big, small;
      load(big, S, N);
      std::vector<MqlRates> base(S.m15.begin() + (N - 3000), S.m15.begin() + N);
      std::vector<MqlRates> h = htf_upto(S, N - 1);
      const int need_h = 3000 * 900 / 3600 + 320;
      if((int)h.size() > need_h) h.erase(h.begin(), h.end() - need_h);
      small.cfg.Defaults();
      small.SetBase(base, 3000);
      small.SetHTF(h, (int)h.size());
      small.Compute();
      for(int st = 0; st < XS_COUNT; st++)
         for(int p = 0; p < XP_COUNT; p++)
         {
            XExit x; XMakeExit(p, big.cfg, x);
            for(int back = 2; back <= 1500; back++)
            {
               XSignal a, b;
               const bool sa = big.StrategySignal(st, N - back, x, a);
               const bool sb = small.StrategySignal(st, 3000 - back, x, b);
               cmp++;
               if(sa) sig++;
               if(sa != sb || (sa && (a.dir != b.dir || std::fabs(a.sl - b.sl) > 1e-9))) mism++;
            }
         }
   }
   std::printf("  %d comparisons, %d signals, %d differences\n", cmp, sig, mism);
   CHECK(sig > 1000 && mism == 0, "EA (3,000 bars) and indicator (10,000 bars) produce identical signals for every strategy and exit");
}

static void test_resolve()
{
   std::printf("\n== choosing the strategy in use ==\n");
   Series S = make_series(W_TREND, 20000, 77);
   CXauEngine e; load(e, S, 20000);
   e.RunLab(e.cfg.warmup, 19998, 60.0, 30, 5);
   bool proven;
   const int c_auto = XResolveCell(e, -1, -1, 30, proven);
   CHECK(c_auto >= 0 && (e.lab_pick_s < 0 || (c_auto == e.lab_pick_s * XP_COUNT + e.lab_pick_p && proven)), "AUTO uses the lab's pick and marks it proven");
   const int c_dip = XResolveCell(e, XS_DIP, -1, 30, proven);
   CHECK(c_dip / XP_COUNT == XS_DIP && proven == e.lab[c_dip].qualified, "a fixed strategy with AUTO exit keeps the strategy and picks its best exit");
   const int c_fix = XResolveCell(e, XS_ORB, XP_QUICK, 30, proven);
   CHECK(c_fix == XS_ORB * XP_COUNT + XP_QUICK, "a fixed strategy and exit are used exactly as chosen");
   CHECK(e.LabRanked(0) >= 0 && (e.lab_pick_s < 0 || e.LabRanked(0) == e.lab_pick_s * XP_COUNT + e.lab_pick_p), "scoreboard shows the pick first");
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
   if(std::getenv("XAU_MINSTOP")) g_minstop = std::atof(std::getenv("XAU_MINSTOP"));
   if(std::getenv("XAU_TARGET")) g_target = std::atof(std::getenv("XAU_TARGET"));
   if(std::getenv("XAU_COST")) g_cost = std::atof(std::getenv("XAU_COST"));
   if(std::getenv("XAU_D1MODE")) g_d1mode = std::atoi(std::getenv("XAU_D1MODE"));
   if(std::getenv("XAU_D1DEF")) g_d1def = std::atoi(std::getenv("XAU_D1DEF"));
   if(std::getenv("XAU_DAYS")) g_days = std::atoi(std::getenv("XAU_DAYS"));
   if(std::getenv("XAU_DIAG")) g_diag = std::atoi(std::getenv("XAU_DIAG"));
   if(std::getenv("XAU_RANDCTRL")) g_rand_ctrl = std::atoi(std::getenv("XAU_RANDCTRL"));
   if(std::getenv("XAU_MULTICAP")) g_multi_cap = std::atoi(std::getenv("XAU_MULTICAP"));
   if(std::getenv("XAU_SWAPL")) g_swapl = std::atof(std::getenv("XAU_SWAPL"));
   if(std::getenv("XAU_SWAPS")) g_swaps = std::atof(std::getenv("XAU_SWAPS"));
   if(std::getenv("XAU_D1") && load_csv(std::getenv("XAU_D1"), g_d1)) g_d1.pop_back();
   if(std::getenv("XAU_DIPWIN"))
   {
      const char *w = std::getenv("XAU_DIPWIN");
      if(!std::strcmp(w, "off")) { g_dip_lo = -1.0; g_dip_hi = 24.0; }
      else if(std::sscanf(w, "%lf-%lf", &g_dip_lo, &g_dip_hi) != 2) { g_dip_lo = -2.0; }
   }
   const bool all = !std::strcmp(mode, "all");
   if(all || !std::strcmp(mode, "units"))   { test_units(); test_exits(); test_platform(); test_time_and_filters(); test_orb(); test_csv_roundtrip(); test_cost_guard(); test_daily_filter(); test_forecast_calibration(); test_entry_at(); test_today_plan(); test_size_forecasts(); test_panel_helpers(); }
   if(all || !std::strcmp(mode, "calib"))   run_calibration();
   if(all || !std::strcmp(mode, "causal"))  { test_causality(); test_window_consistency(); test_strategy_windows(); test_resolve(); }
   if(all || !std::strcmp(mode, "null"))    run_world(W_NULL,    "NULL - random walk, no edge exists", 6, 40000);
   if(all || !std::strcmp(mode, "trend"))   run_world(W_TREND,   "TREND - persistent drift regimes (edge planted)", 6, 40000);
   if(all || !std::strcmp(mode, "meanrev")) run_world(W_MEANREV, "MEANREV - price pulled back to a moving anchor", 6, 40000);
   if(all || !std::strcmp(mode, "analog"))  test_analog();
   if(all || !std::strcmp(mode, "lab"))
   {
      run_lab_world(W_NULL, "NULL (no edge)", 4, 30000, true);
      run_lab_world(W_BULL, "BULL (steady uptrend, gold 2024-26 style)", 4, 30000, true);
      run_lab_world(W_TREND, "TREND (drift regimes)", 4, 30000, true);
      run_lab_world(W_MEANREV, "MEANREV", 4, 30000, true);
      run_lab_world(W_MIXED, "MIXED (alternating)", 4, 30000, true);
   }
   if(all || !std::strcmp(mode, "labrules")) run_lab_variants();
   if(!std::strcmp(mode, "replayrules"))    run_replay_variants();
   if(!std::strcmp(mode, "replayconfirm"))  run_replay_confirm();
   if(all || !std::strcmp(mode, "replay"))  run_replay_worlds();
   if(!std::strcmp(mode, "real"))           return run_real(argc, argv);
   if(!std::strcmp(mode, "realblocks"))     return run_real_blocks(argc, argv);
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
