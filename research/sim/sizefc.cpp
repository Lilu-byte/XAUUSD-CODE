// Round 11: sharper SIZE forecasts (the one kind of prediction that has worked on gold) and a better cone.
// Every model below only uses data from before the bar or day it predicts. Fit on the past, scored on the newer 40%.
//
// CANDLE SIZE (high-low of the next bar)
//   NOW     ATR x hour-of-day profile x rolling median correction (what the indicator does since round 8)
//   WEEK    same with a weekday x hour profile (US jobs Fridays, Fed Wednesdays), shrunk toward the hour profile
//   HAR     log-range regression on the last bar, the last 6, 48 and 480 bars (de-seasonalised), refitted on the past
//   HAR+WK  HAR with the weekday x hour profile
// DAY RANGE (server day high-low)
//   ADR     mean of the last 14 days (the TODAY line since round 10)
//   HARd    log regression on yesterday, the last 5 and the last 22 days, refitted every day on the previous 1,000
//   +SOFAR  HARd updated during the day with the range already made (checked 8 and 14 hours after the day opens)
// CONE (where price is 3 bars ahead, 20% / 50% / 80% quantiles)
//   NOW     quantiles of the last 3,000 standardised 3-bar moves
//   ACI     the same with self-correcting quantile levels (adaptive conformal inference): every miss widens it,
//           every hit narrows it a little, so coverage stays at 60% in every regime
//   TREND   quantiles taken only from past situations with the same daily trend (up / down)
// Scored with mean absolute error, share within +-25%, coverage per year and the pinball (quantile) loss.
//
// Build:  g++ -std=c++17 -O2 -o sizefc research/sim/sizefc.cpp
// Run:    ./sizefc BASE.csv HIGHER.csv D1.csv

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

// least squares with k regressors (x[0] = 1); returns false when singular
static bool ols(const std::vector<std::vector<double>> &X, const std::vector<double> &y, std::vector<double> &b)
{
   const int k = (int)X[0].size();
   std::vector<std::vector<double>> A(k, std::vector<double>(k + 1, 0.0));
   for(size_t r = 0; r < X.size(); r++)
      for(int i = 0; i < k; i++)
      {
         for(int j = 0; j < k; j++) A[i][j] += X[r][i] * X[r][j];
         A[i][k] += X[r][i] * y[r];
      }
   for(int i = 0; i < k; i++) A[i][i] += 1e-6;
   for(int c = 0; c < k; c++)
   {
      int p = c;
      for(int r = c + 1; r < k; r++) if(std::fabs(A[r][c]) > std::fabs(A[p][c])) p = r;
      if(std::fabs(A[p][c]) < 1e-12) return false;
      std::swap(A[p], A[c]);
      for(int r = 0; r < k; r++)
      {
         if(r == c) continue;
         const double f = A[r][c] / A[c][c];
         for(int j = c; j <= k; j++) A[r][j] -= f * A[c][j];
      }
   }
   b.assign(k, 0.0);
   for(int i = 0; i < k; i++) b[i] = A[i][k] / A[i][i];
   return true;
}

// fixed-length window of values kept sorted, for fast quantiles
struct RollQ
{
   std::vector<double> fifo, sorted; size_t head = 0; size_t cap;
   explicit RollQ(size_t c) : cap(c) {}
   void add(double v)
   {
      if(fifo.size() - head >= cap) { const double old = fifo[head++]; sorted.erase(std::lower_bound(sorted.begin(), sorted.end(), old)); }
      fifo.push_back(v);
      sorted.insert(std::upper_bound(sorted.begin(), sorted.end(), v), v);
      if(head > 100000) { fifo.erase(fifo.begin(), fifo.begin() + head); head = 0; }
   }
   size_t size() const { return sorted.size(); }
   double q(double p) const { return sorted[(size_t)(XClamp(p, 0.0, 1.0) * (sorted.size() - 1))]; }
};

static double pinball(double q, double pred, double act) { const double u = act - pred; return (u >= 0) ? q * u : (q - 1.0) * u; }

static CXauEngine E;
static std::vector<MqlRates> B;

int main(int argc, char **argv)
{
   if(argc < 4) { std::printf("usage: sizefc BASE.csv HIGHER.csv D1.csv\n"); return 2; }
   std::vector<MqlRates> htf, d1;
   if(!load_csv(argv[1], B) || !load_csv(argv[2], htf) || !load_csv(argv[3], d1)) return 2;
   B.pop_back(); htf.pop_back(); d1.pop_back();
   E.cfg.Defaults();
   E.cfg.base_sec = bar_seconds(B); E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.cfg.d1_sma = 200;
   E.SetBase(B, (int)B.size()); E.SetHTF(htf, (int)htf.size()); E.SetDaily(d1, (int)d1.size());
   if(!E.Compute()) return 2;
   const int n = E.n;
   const int SPLIT = E.cfg.warmup + (int)(0.6 * (n - E.cfg.warmup));
   std::printf("== SIZE FORECASTS: %s (%d bars of %d s), scored %s .. %s ==\n", argv[1], n, E.cfg.base_sec,
               TimeToString(B[SPLIT].time).c_str(), TimeToString(B[n - 1].time).c_str());

   // GMT hour and weekday of each bar
   std::vector<int> hr(n), dw(n);
   for(int i = 0; i < n; i++)
   {
      const long long g = (long long)B[i].time - XOffsetAt(E.cfg, B[i].time);
      hr[i] = (int)((g % 86400) / 3600);
      dw[i] = (int)(((g / 86400) + 4) % 7);
   }
   // profiles from the bars before the scored part only: range / ATR by hour, and by weekday x hour (shrunk)
   double hs[24] = {0}, all = 0; int hc[24] = {0}, allc = 0;
   double ws[7][24] = {{0}}; int wc[7][24] = {{0}};
   for(int i = E.cfg.warmup; i < SPLIT; i++)
   {
      const double r = (B[i].high - B[i].low) / std::max(E.m_atr[i - 1], 1e-9);
      hs[hr[i]] += r; hc[hr[i]]++; ws[dw[i]][hr[i]] += r; wc[dw[i]][hr[i]]++; all += r; allc++;
   }
   double prof[24], profw[7][24];
   const double mean_all = all / std::max(allc, 1);
   for(int h = 0; h < 24; h++) prof[h] = (hc[h] > 20) ? (hs[h] / hc[h]) / mean_all : 1.0;
   const double K = 30.0;                                                 // shrinkage toward the hour profile
   for(int d = 0; d < 7; d++)
      for(int h = 0; h < 24; h++)
         profw[d][h] = ((ws[d][h] / mean_all) + K * prof[h]) / (wc[d][h] + K);
   auto P = [&](int i) { return prof[hr[i]]; };
   auto PW = [&](int i) { return profw[dw[i]][hr[i]]; };

   // ---------------- candle size ----------------
   // de-seasonalised ranges and their rolling means
   std::vector<double> ds(n, 0.0), dsw(n, 0.0);
   for(int i = 0; i < n; i++) { ds[i] = std::max(B[i].high - B[i].low, 1e-6) / P(i); dsw[i] = std::max(B[i].high - B[i].low, 1e-6) / PW(i); }
   std::vector<double> cs(n + 1, 0.0), csw(n + 1, 0.0);
   for(int i = 0; i < n; i++) { cs[i + 1] = cs[i] + ds[i]; csw[i + 1] = csw[i] + dsw[i]; }
   auto feats = [&](const std::vector<double> &v, int i, std::vector<double> &x) {
      const std::vector<double> &c = (&v == &ds) ? cs : csw;
      auto mb = [&](int len) { const int a = std::max(0, i - len + 1); return (c[i + 1] - c[a]) / (i + 1 - a); };
      x.assign(5, 1.0);
      x[1] = std::log(v[i]); x[2] = std::log(mb(6)); x[3] = std::log(mb(48)); x[4] = std::log(mb(480));
   };
   Err e0, e1, e2, e3;
   std::map<int, Err> y0, y2, y3;
   std::vector<double> rat0, rat1;                                         // rolling actual / prediction, for the median correction
   for(int i = std::max(E.cfg.warmup + 500, SPLIT - 2000); i < SPLIT; i++)
   {
      rat0.push_back((B[i + 1].high - B[i + 1].low) / (E.m_atr[i] * P(i + 1)));
      rat1.push_back((B[i + 1].high - B[i + 1].low) / (E.m_atr[i] * PW(i + 1)));
   }
   std::vector<double> bh, bhw;
   int last_fit = -1000000;
   for(int i = SPLIT; i < n - 1; i++)
   {
      if(i - last_fit >= 500)
      {
         std::vector<std::vector<double>> X, XW; std::vector<double> y, yw;
         for(int j = std::max(E.cfg.warmup + 500, i - 20000); j < i - 1; j++)
         {
            std::vector<double> x; feats(ds, j, x); X.push_back(x); y.push_back(std::log(ds[j + 1]));
            feats(dsw, j, x); XW.push_back(x); yw.push_back(std::log(dsw[j + 1]));
         }
         ols(X, y, bh); ols(XW, yw, bhw);
         last_fit = i;
      }
      const double act = B[i + 1].high - B[i + 1].low;
      std::vector<double> r0 = rat0, r1 = rat1;
      std::nth_element(r0.begin(), r0.begin() + r0.size() / 2, r0.end());
      std::nth_element(r1.begin(), r1.begin() + r1.size() / 2, r1.end());
      const double p0 = E.m_atr[i] * P(i + 1) * r0[r0.size() / 2];
      const double p1 = E.m_atr[i] * PW(i + 1) * r1[r1.size() / 2];
      std::vector<double> x;
      feats(ds, i, x);
      double lp = 0; for(int k = 0; k < 5; k++) lp += bh[k] * x[k];
      const double p2 = std::exp(lp) * P(i + 1);
      feats(dsw, i, x);
      lp = 0; for(int k = 0; k < 5; k++) lp += bhw[k] * x[k];
      const double p3 = std::exp(lp) * PW(i + 1);
      e0.add(p0, act); e1.add(p1, act); e2.add(p2, act); e3.add(p3, act);
      const int yr = XYearOfDays(B[i].time / 86400);
      y0[yr].add(p0, act); y2[yr].add(p2, act); y3[yr].add(p3, act);
      rat0.push_back(act / (E.m_atr[i] * P(i + 1))); rat1.push_back(act / (E.m_atr[i] * PW(i + 1)));
      if(rat0.size() > 2000) { rat0.erase(rat0.begin()); rat1.erase(rat1.begin()); }
   }
   std::printf("\n  NEXT CANDLE SIZE          mean abs error   vs NOW   within +-25%%\n");
   const Err *es[4] = {&e0, &e1, &e2, &e3};
   const char *nm[4] = {"NOW  ATR x hour x median", "WEEK weekday x hour profile", "HAR  fitted 1/6/48/480 bars", "HAR + weekday x hour"};
   for(int k = 0; k < 4; k++)
      std::printf("    %-28s %8.3f      %+5.1f%%     %5.1f%%\n", nm[k], es[k]->mae(), 100.0 * (es[k]->mae() / e0.mae() - 1.0), es[k]->win());
   std::printf("    by year, error vs NOW (HAR / HAR+WK):");
   for(auto &kv : y0) std::printf(" %d %+.1f%%/%+.1f%%", kv.first, 100.0 * (y2[kv.first].mae() / kv.second.mae() - 1.0), 100.0 * (y3[kv.first].mae() / kv.second.mae() - 1.0));
   std::printf("\n");

   // ---------------- cone, 3 bars ahead ----------------
   {
      const int S = 3;
      auto zmove = [&](int i) { double pv = 0; for(int k = 1; k <= S; k++) pv += P(i + k) * P(i + k); return (B[i + S].close - B[i].close) / (E.m_atr[i] * std::sqrt(pv)); };
      RollQ pool(3000), up(3000), dn(3000);                                  // past standardised moves (all, daily trend up, down)
      for(int i = std::max(E.cfg.warmup, SPLIT - 3000 - S); i < SPLIT - S; i++)
      {
         pool.add(zmove(i));
         (E.m_dreg[i] > 0 ? up : dn).add(zmove(i));
      }
      double delta = 0.0;                                                   // ACI widening (quantile levels 0.2 - delta, 0.8 + delta)
      std::map<int, int> cn, c0, c1, c2;
      double pl0 = 0, pl2 = 0; int pn = 0;
      double w0 = 0, w1 = 0;
      std::vector<char> miss1(n, 0);
      for(int i = SPLIT; i < n - S; i++)
      {
         // ACI update with the outcome that became known at bar i (the forecast made at i - S)
         if(i - S >= SPLIT) delta = XClamp(delta + 0.005 * ((miss1[i - S] ? 1.0 : 0.0) - 0.4), -0.15, 0.15);
         double pv = 0; for(int k = 1; k <= S; k++) pv += P(i + k) * P(i + k);
         const double sc = E.m_atr[i] * std::sqrt(pv);
         const double mv = B[i + S].close - B[i].close;
         const double lo = pool.q(0.2) * sc, md = pool.q(0.5) * sc, hi = pool.q(0.8) * sc;
         const double lo1 = pool.q(0.2 - delta) * sc, hi1 = pool.q(0.8 + delta) * sc;
         const RollQ &rg = (E.m_dreg[i] > 0) ? up : dn;
         const bool rg_ok = rg.size() > 300;
         const double lo2 = rg_ok ? rg.q(0.2) * sc : lo, md2 = rg_ok ? rg.q(0.5) * sc : md, hi2 = rg_ok ? rg.q(0.8) * sc : hi;
         const int yr = XYearOfDays(B[i].time / 86400);
         cn[yr]++;
         if(mv >= lo && mv <= hi) c0[yr]++;
         const bool in1 = (mv >= lo1 && mv <= hi1);
         if(in1) c1[yr]++;
         miss1[i] = in1 ? 0 : 1;
         if(mv >= lo2 && mv <= hi2) c2[yr]++;
         pl0 += pinball(0.2, lo, mv) + pinball(0.5, md, mv) + pinball(0.8, hi, mv);
         pl2 += pinball(0.2, lo2, mv) + pinball(0.5, md2, mv) + pinball(0.8, hi2, mv);
         pn++;
         w0 += (hi - lo) / E.m_atr[i]; w1 += (hi1 - lo1) / E.m_atr[i];
         // the move that started S bars ago is now known: add it to the past samples
         if(i - S >= 0)
         {
            const double z = zmove(i - S);
            pool.add(z);
            ((E.m_dreg[i - S] > 0) ? up : dn).add(z);
         }
      }
      std::printf("\n  CONE 3 bars ahead (should hold the close 60%% of the time)\n    year : NOW inside | ACI inside | TREND inside\n");
      int tn = 0, t0 = 0, t1 = 0, t2 = 0;
      for(auto &kv : cn)
      {
         const int y = kv.first;
         std::printf("    %d :  %5.1f%%     |  %5.1f%%    |  %5.1f%%   (%d)\n", y, 100.0 * c0[y] / kv.second, 100.0 * c1[y] / kv.second, 100.0 * c2[y] / kv.second, kv.second);
         tn += kv.second; t0 += c0[y]; t1 += c1[y]; t2 += c2[y];
      }
      std::printf("    all  :  %5.1f%%     |  %5.1f%%    |  %5.1f%%   width NOW %.2f ATR, ACI %.2f ATR\n", 100.0 * t0 / tn, 100.0 * t1 / tn, 100.0 * t2 / tn, w0 / pn, w1 / pn);
      std::printf("    pinball loss (20/50/80%%, lower is better): NOW %.4f  TREND %.4f  (%+.2f%%)\n", pl0 / pn, pl2 / pn, 100.0 * (pl2 / pl0 - 1.0));
   }

   // ---------------- day range ----------------
   // server days from the base file, and from the daily file for 22 years
   auto day_test = [&](const std::vector<MqlRates> &days, const char *label) {
      const int N = (int)days.size();
      std::vector<double> R(N);
      for(int k = 0; k < N; k++) R[k] = std::max(days[k].high - days[k].low, 1e-6);
      const int start = std::max(60, (int)(0.6 * N));
      Err ea, eh;
      std::map<int, Err> ya, yh;
      for(int k = start; k < N; k++)
      {
         double adr = 0; for(int q = k - 14; q < k; q++) adr += R[q]; adr /= 14.0;
         std::vector<std::vector<double>> X; std::vector<double> y;
         for(int j = std::max(23, k - 1000); j < k; j++)
         {
            double m5 = 0, m22 = 0; for(int q = j - 5; q < j; q++) m5 += R[q]; for(int q = j - 22; q < j; q++) m22 += R[q];
            X.push_back({1.0, std::log(R[j - 1]), std::log(m5 / 5), std::log(m22 / 22)}); y.push_back(std::log(R[j]));
         }
         std::vector<double> b;
         if(X.size() < 100 || !ols(X, y, b)) continue;
         double m5 = 0, m22 = 0; for(int q = k - 5; q < k; q++) m5 += R[q]; for(int q = k - 22; q < k; q++) m22 += R[q];
         const double ph = std::exp(b[0] + b[1] * std::log(R[k - 1]) + b[2] * std::log(m5 / 5) + b[3] * std::log(m22 / 22));
         ea.add(adr, R[k]); eh.add(ph, R[k]);
         const int yr = XYearOfDays(days[k].time / 86400);
         ya[yr].add(adr, R[k]); yh[yr].add(ph, R[k]);
      }
      std::printf("\n  DAY RANGE (%s, %d days scored)   mean abs error   within +-25%%\n", label, ea.n);
      std::printf("    ADR  mean of 14 days            %8.2f          %5.1f%%\n", ea.mae(), ea.win());
      std::printf("    HARd fitted 1/5/22 days         %8.2f (%+.1f%%)  %5.1f%%\n", eh.mae(), 100.0 * (eh.mae() / ea.mae() - 1.0), eh.win());
      int better = 0, years = 0;
      for(auto &kv : ya) { years++; if(yh[kv.first].mae() < kv.second.mae()) better++; }
      std::printf("    HARd better than ADR in %d of %d years\n", better, years);
   };
   if(d1.size() > 500) day_test(d1, "daily file");

   // intraday update: forecast the day's final range 8 and 14 hours after the server day opens
   if(E.cfg.base_sec <= 3600)
   {
      std::vector<MqlRates> days;
      std::vector<int> d_first;
      for(int i = 0; i < n; i++)
      {
         if(days.empty() || B[i].time / 86400 != days.back().time / 86400)
         {
            MqlRates r = B[i]; r.time = B[i].time - (B[i].time % 86400); days.push_back(r); d_first.push_back(i);
         }
         else { days.back().high = std::max(days.back().high, B[i].high); days.back().low = std::min(days.back().low, B[i].low); days.back().close = B[i].close; }
      }
      day_test(days, "server days of this file");
      const int N = (int)days.size();
      std::vector<double> R(N); for(int k = 0; k < N; k++) R[k] = std::max(days[k].high - days[k].low, 1e-6);
      for(int hcut : {8, 14})
      {
         // so-far range at the checkpoint for every day
         std::vector<double> sofar(N, 0.0); std::vector<char> ok(N, 0);
         for(int k = 0; k < N; k++)
         {
            const int f = d_first[k], l = (k + 1 < N) ? d_first[k + 1] : n;
            double h = -1e18, lo = 1e18; bool any = false;
            for(int i = f; i < l; i++) { if((B[i].time % 86400) >= hcut * 3600) break; h = std::max(h, B[i].high); lo = std::min(lo, B[i].low); any = true; }
            if(any && l - f >= 6) { sofar[k] = h - lo; ok[k] = 1; }
         }
         Err ea, ec, ef;
         const int start = std::max(60, (int)(0.6 * N));
         for(int k = start; k < N; k++)
         {
            if(!ok[k]) continue;
            double adr = 0; for(int q = k - 14; q < k; q++) adr += R[q]; adr /= 14.0;
            // fitted: log R = a + b log ADR + c log(sofar / ADR), on the previous 500 days
            std::vector<std::vector<double>> X; std::vector<double> y;
            for(int j = std::max(15, k - 500); j < k; j++)
            {
               if(!ok[j] || sofar[j] <= 0) continue;
               double a2 = 0; for(int q = j - 14; q < j; q++) a2 += R[q]; a2 /= 14.0;
               X.push_back({1.0, std::log(a2), std::log(std::max(sofar[j], 1e-6) / a2)}); y.push_back(std::log(R[j]));
            }
            std::vector<double> b;
            if(X.size() < 100 || !ols(X, y, b)) continue;
            const double pf = std::max(sofar[k], std::exp(b[0] + b[1] * std::log(adr) + b[2] * std::log(std::max(sofar[k], 1e-6) / adr)));
            ea.add(adr, R[k]); ec.add(std::max(adr, sofar[k]), R[k]); ef.add(pf, R[k]);
         }
         std::printf("    %2d h into the day:  ADR %.2f | max(ADR, so far) %.2f | fitted with so far %.2f (%+.1f%% vs ADR), within +-25%% %.0f%% vs %.0f%%\n", hcut,
                     ea.mae(), ec.mae(), ef.mae(), 100.0 * (ef.mae() / ea.mae() - 1.0), ef.win(), ea.win());
      }
   }
   return 0;
}
