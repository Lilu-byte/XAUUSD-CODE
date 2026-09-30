// "One strategy that mixes everything": a walk-forward meta-model over every signal of all 32
// strategy/exit combinations, on the user's real XAUUSD history.
//
// At every closed bar, every combination that has a signal becomes a CANDIDATE trade. A model trained only on
// candidates that had already CLOSED before that bar predicts each candidate's result in R; the best one is
// taken if its prediction beats a threshold. This is "meta-labelling": the strategies propose, the model
// (trained on how similar setups ended) disposes. The model is refitted every trading day.
//
// Models
//   ALL     no model: the first candidate, always (how much trading is possible at all)
//   CELL    shrunk average result of the same combination over the training window (what the Lab does, continuously)
//   RIDGE   ridge regression on 22 situation features, separate weights per strategy family, plus a term per combination
//   RIDGE+  RIDGE, but a candidate also needs its combination's own average to be positive
// Thresholds and the ridge penalty were chosen on the older 60% of each file; the newest 40% is reported apart.
//
// Build:  g++ -std=c++17 -O2 -o meta research/sim/meta.cpp
// Run:    ./meta BASE.csv HIGHER.csv [cost=0.35] [train_bars=0 (all past)] [slots=1]

#include "../mock/mql5_mock.h"
#include "../../src/XAU_Core.mqh"
#include "../../src/XAU_Platform.mqh"

#include <cstring>

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

static CXauEngine E;
static int g_bpd = 24;

static const int NF = 22;          // situation features
static const int NFAM = 3;         // strategy families: dips, breakouts, others
static const int NP = 1 + NFAM * NF + XLAB_CELLS;   // intercept + family x feature + one term per combination

struct Cand
{
   int i, cell, dir, exit_idx;
   double r;
   float f[NF];
};

static int family(const int cell)
{
   const int s = cell / XP_COUNT;
   if(s == XS_DIP || s == XS_DOUBLE7 || s == XS_IBS) return 0;
   if(s == XS_ORB || s == XS_SQUEEZE) return 1;
   return 2;
}

static double clampd(double v, double lo, double hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Situation at closed bar i for a trade in direction d; every feature is direction-adjusted and roughly in [-1, 1].
static void features(const int i, const int d, const double risk, float *f)
{
   const double a = E.m_atr[i] > 0 ? E.m_atr[i] : 1.0;
   const double c = E.m_c[i];
   const double hr = E.m_hour[i] * 6.283185307179586 / 24.0;
   const double rng = E.m_h[i] - E.m_l[i];
   const double ibs = rng > 0 ? (c - E.m_l[i]) / rng : 0.5;
   const double pdr = E.m_pdh[i] - E.m_pdl[i];
   int k = 0;
   f[k++] = (float)clampd(d * (c - E.m_ema1[i]) / a / 3.0, -2, 2);
   f[k++] = (float)clampd(d * (c - E.m_ema2[i]) / a / 4.0, -2, 2);
   f[k++] = (float)clampd(d * (c - E.m_ema3[i]) / a / 8.0, -2, 2);
   f[k++] = (float)(d * (E.m_rsi[i] - 50.0) / 50.0);
   f[k++] = (float)(d * (E.m_rsi2[i] - 50.0) / 50.0);
   f[k++] = (float)clampd(E.m_adx[i] / 50.0 - 0.5, -1, 1);
   f[k++] = (float)(E.m_atrref[i] > 0 ? clampd(E.m_atr[i] / E.m_atrref[i] - 1.0, -1, 2) : 0.0);
   f[k++] = (float)clampd((E.m_er[i] - 0.3) * 2.0, -1, 1.5);
   f[k++] = (float)clampd(E.m_adru[i] - 0.7, -1, 1.5);
   f[k++] = (float)(d * E.m_bias[i]);
   f[k++] = (float)std::sin(hr);
   f[k++] = (float)std::cos(hr);
   f[k++] = (float)(E.m_vavg[i] > 0 ? clampd((E.m_v[i] / E.m_vavg[i] - 1.0) / 2.0, -1, 2) : 0.0);
   f[k++] = (float)(i - g_bpd >= 0 ? clampd(d * (c - E.m_c[i - g_bpd]) / a / 5.0, -2, 2) : 0.0);
   f[k++] = (float)(i - 5 * g_bpd >= 0 ? clampd(d * (c - E.m_c[i - 5 * g_bpd]) / a / 12.0, -2, 2) : 0.0);
   f[k++] = (float)clampd(risk / a - 1.5, -1, 2);
   f[k++] = (float)clampd(E.cfg.cost_price / std::max(risk, 1e-9) * 10.0, 0, 2);
   f[k++] = (float)(E.m_vwap[i] > 0 ? clampd(d * (c - E.m_vwap[i]) / a / 3.0, -2, 2) : 0.0);
   f[k++] = (float)(d > 0 ? ibs - 0.5 : 0.5 - ibs);
   f[k++] = (float)(d * (E.m_bbp[i] - 0.5));
   f[k++] = (float)(pdr > 0 ? clampd(d * ((c - E.m_pdl[i]) / pdr - 0.5), -1.5, 1.5) : 0.0);
   f[k++] = (float)(XWeekdayGmt(E.m_t[i], XOffsetAt(E.cfg, E.m_t[i])) == 5 ? 1.0 : 0.0);
}

static void design(const Cand &c, double *x)
{
   for(int p = 0; p < NP; p++) x[p] = 0.0;
   x[0] = 1.0;
   const int fb = 1 + family(c.cell) * NF;
   for(int k = 0; k < NF; k++) x[fb + k] = c.f[k];
   x[1 + NFAM * NF + c.cell] = 1.0;
}

// running sums for ridge regression (add / remove one observation)
struct Ridge
{
   std::vector<double> xtx, xty, beta;
   int n = 0;
   void init() { xtx.assign(NP * NP, 0.0); xty.assign(NP, 0.0); beta.assign(NP, 0.0); n = 0; }
   void add(const Cand &c, const double w)
   {
      double x[NP];
      design(c, x);
      for(int a = 0; a < NP; a++)
      {
         if(x[a] == 0.0) continue;
         xty[a] += w * x[a] * c.r;
         for(int b = 0; b < NP; b++) if(x[b] != 0.0) xtx[a * NP + b] += w * x[a] * x[b];
      }
      n += (w > 0 ? 1 : -1);
   }
   bool fit(const double lam)
   {
      if(n < 60) return false;
      std::vector<double> A(xtx), y(xty);
      for(int a = 1; a < NP; a++) A[a * NP + a] += lam;
      A[0] += 1e-6;
      // Gaussian elimination with partial pivoting
      std::vector<int> piv(NP);
      for(int col = 0; col < NP; col++)
      {
         int best = col;
         for(int r = col + 1; r < NP; r++) if(std::fabs(A[r * NP + col]) > std::fabs(A[best * NP + col])) best = r;
         if(std::fabs(A[best * NP + col]) < 1e-12) return false;
         if(best != col) { for(int k = 0; k < NP; k++) std::swap(A[col * NP + k], A[best * NP + k]); std::swap(y[col], y[best]); }
         for(int r = col + 1; r < NP; r++)
         {
            const double m = A[r * NP + col] / A[col * NP + col];
            if(m == 0.0) continue;
            for(int k = col; k < NP; k++) A[r * NP + k] -= m * A[col * NP + k];
            y[r] -= m * y[col];
         }
      }
      for(int r = NP - 1; r >= 0; r--)
      {
         double s = y[r];
         for(int k = r + 1; k < NP; k++) s -= A[r * NP + k] * beta[k];
         beta[r] = s / A[r * NP + r];
      }
      return true;
   }
   double predict(const Cand &c) const
   {
      double x[NP];
      design(c, x);
      double s = 0.0;
      for(int p = 0; p < NP; p++) s += beta[p] * x[p];
      return s;
   }
};

struct Acc
{
   int n = 0, w = 0; double s = 0, s2 = 0, gw = 0, gl = 0;
   void add(double r) { n++; s += r; s2 += r * r; if(r > 0) { w++; gw += r; } else gl -= r; }
   double mean() const { return n ? s / n : 0.0; }
   double se() const { if(n < 2) return 0.0; const double m = mean(); return std::sqrt(std::max(0.0, s2 / n - m * m) / n); }
   double win() const { return n ? 100.0 * w / n : 0.0; }
   double pf() const { return gl > 1e-12 ? gw / gl : 0.0; }
};

enum { M_ALL = 0, M_CELL = 1, M_RIDGE = 2, M_RIDGEP = 3, M_COUNT = 4 };
static const char *MNAME[M_COUNT] = {"ALL (no model)", "CELL average", "RIDGE", "RIDGE+ (cell also positive)"};

struct RunOut { Acc disc, hold; int days_d = 0, days_h = 0; };

// One walk-forward pass. train_bars = 0: all past candidates. slots = simultaneous positions.
static RunOut run(const std::vector<Cand> &cand, const int model, const double thr, const double lam, const int train_bars,
                  const int slots, const int split, const int start_bar)
{
   RunOut o;
   Ridge rg; rg.init();
   double csum[XLAB_CELLS] = {0}; int ccnt[XLAB_CELLS] = {0};
   // candidates enter training in order of exit; expire in order of entry (rolling window)
   std::vector<int> by_exit(cand.size());
   for(size_t k = 0; k < cand.size(); k++) by_exit[k] = (int)k;
   std::sort(by_exit.begin(), by_exit.end(), [&](int a, int b) { return cand[a].exit_idx < cand[b].exit_idx; });
   size_t add_ptr = 0;
   std::vector<char> added(cand.size(), 0);
   size_t exp_ptr = 0;                          // cand is sorted by i
   std::vector<int> slot_busy(slots, -1), slot_dir(slots, 0), slot_cell(slots, -1);
   long cur_day = -1;
   size_t k = 0;
   while(k < cand.size() && cand[k].i < start_bar) k++;
   for(int i = start_bar; i < E.n - 2; i++)
   {
      const long day = (long)E.m_t[i] / 86400;
      if(day != cur_day)
      {
         cur_day = day;
         if(i < split) o.days_d++; else o.days_h++;
         // bring the training set up to date: candidates that closed before this bar
         while(add_ptr < by_exit.size() && cand[by_exit[add_ptr]].exit_idx < i)
         {
            const int q = by_exit[add_ptr++];
            if(train_bars > 0 && cand[q].i < i - train_bars) continue;
            added[q] = 1;
            rg.add(cand[q], 1.0);
            csum[cand[q].cell] += cand[q].r; ccnt[cand[q].cell]++;
         }
         if(train_bars > 0)
            while(exp_ptr < cand.size() && cand[exp_ptr].i < i - train_bars)
            {
               if(added[exp_ptr]) { rg.add(cand[exp_ptr], -1.0); csum[cand[exp_ptr].cell] -= cand[exp_ptr].r; ccnt[cand[exp_ptr].cell]--; added[exp_ptr] = 0; }
               exp_ptr++;
            }
         if(model >= M_RIDGE) rg.fit(lam * std::max(1, rg.n) / 1000.0);
      }
      // candidates of this bar
      size_t k0 = k;
      while(k < cand.size() && cand[k].i == i) k++;
      if(k0 == k) continue;
      int free_slot = -1;
      for(int s = 0; s < slots; s++) if(slot_busy[s] < i) { free_slot = s; break; }
      if(free_slot < 0) continue;
      int best = -1; double best_p = -1e9;
      for(size_t q = k0; q < k; q++)
      {
         const Cand &c = cand[q];
         bool clash = false;
         for(int s = 0; s < slots; s++) if(slot_busy[s] >= i && (slot_dir[s] != c.dir || slot_cell[s] == c.cell)) clash = true;
         if(clash) continue;
         double p;
         const double cm = csum[c.cell] / (ccnt[c.cell] + 20.0);
         if(model == M_ALL) p = 1.0;
         else if(model == M_CELL) p = (ccnt[c.cell] >= 30) ? cm : -1e9;
         else
         {
            if(rg.n < 60) continue;
            p = rg.predict(c);
            if(model == M_RIDGEP && !(ccnt[c.cell] >= 30 && cm > 0.0)) continue;
         }
         if(p > best_p) { best_p = p; best = (int)q; }
      }
      if(best < 0 || best_p <= thr) continue;
      const Cand &c = cand[best];
      slot_busy[free_slot] = c.exit_idx; slot_dir[free_slot] = c.dir; slot_cell[free_slot] = c.cell;
      (i < split ? o.disc : o.hold).add(c.r);
   }
   return o;
}

static void print_run(const char *label, const RunOut &o)
{
   std::printf("    %-34s | %5d %5.2f/d %5.1f%% %+7.3f (%.3f) PF %4.2f | %5d %5.2f/d %5.1f%% %+7.3f (%.3f) PF %4.2f\n", label,
               o.disc.n, o.days_d ? (double)o.disc.n / o.days_d : 0.0, o.disc.win(), o.disc.mean(), o.disc.se(), o.disc.pf(),
               o.hold.n, o.days_h ? (double)o.hold.n / o.days_h : 0.0, o.hold.win(), o.hold.mean(), o.hold.se(), o.hold.pf());
}

int main(int argc, char **argv)
{
   if(argc < 3) { std::printf("usage: meta BASE.csv HIGHER.csv [cost=0.35] [train_bars=0] [slots=1]\n"); return 2; }
   std::vector<MqlRates> base, htf;
   if(!load_csv(argv[1], base) || !load_csv(argv[2], htf)) { std::printf("cannot read input\n"); return 2; }
   base.pop_back(); htf.pop_back();
   const int bs = bar_seconds(base);
   g_bpd = std::max(1, 86400 / bs);
   E.cfg.Defaults();
   E.cfg.base_sec = bs; E.cfg.htf_sec = bar_seconds(htf);
   E.cfg.gmt_offset_sec = 7200; E.cfg.dst_mode = 1;
   E.cfg.cost_price = argc > 3 ? std::atof(argv[3]) : 0.35;
   const int train_bars = argc > 4 ? std::atoi(argv[4]) : 0;
   const int slots = argc > 5 ? std::max(1, std::atoi(argv[5])) : 1;
   E.SetBase(base, (int)base.size()); E.SetHTF(htf, (int)htf.size());
   if(!E.Compute()) return 2;

   std::vector<Cand> cand;
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
         Cand cd; cd.i = i; cd.cell = c; cd.dir = sg.dir; cd.exit_idx = r.exit_idx; cd.r = r.r_net;
         features(i, sg.dir, r.risk, cd.f);
         cand.push_back(cd);
      }
   }
   std::sort(cand.begin(), cand.end(), [](const Cand &a, const Cand &b) { return a.i < b.i || (a.i == b.i && a.cell < b.cell); });
   const int start_bar = E.cfg.warmup + std::min(10000, (E.n - E.cfg.warmup) / 5);     // first training period
   const int split = start_bar + (int)(0.6 * (E.n - 2 - start_bar));
   std::printf("== META-MODEL over all 32 combinations: %s (%d bars of %d s), cost %.2f, guard %.0f costs ==\n", argv[1], E.n, bs,
               E.cfg.cost_price, E.cfg.min_stop_cost);
   std::printf("   %zu candidate trades | trading from %s | older part to %s | newer part to %s\n", cand.size(),
               TimeToString(E.m_t[start_bar]).c_str(), TimeToString(E.m_t[split]).c_str(), TimeToString(E.m_t[E.n - 1]).c_str());
   std::printf("   training window: %s | positions at once: %d\n", train_bars > 0 ? (std::to_string(train_bars) + " bars").c_str() : "all past", slots);
   std::printf("    %-34s | %-44s | %-44s\n", "model / threshold (R)", "older 60%: n  per day  won  avgR (se)  PF", "newer 40%: n  per day  won  avgR (se)  PF");
   const double thrs[4] = {0.0, 0.03, 0.06, 0.10};
   const double lams[2] = {3.0, 30.0};
   for(int m = 0; m < M_COUNT; m++)
   {
      for(int li = 0; li < ((m >= M_RIDGE) ? 2 : 1); li++)
         for(int t = 0; t < ((m == M_ALL) ? 1 : 4); t++)
         {
            RunOut o = run(cand, m, (m == M_ALL) ? -1e9 : thrs[t], lams[li], train_bars, slots, split, start_bar);
            char lb[96];
            if(m >= M_RIDGE) std::snprintf(lb, sizeof lb, "%s lam %.0f  > %+.2f", MNAME[m], lams[li], thrs[t]);
            else if(m == M_CELL) std::snprintf(lb, sizeof lb, "%s  > %+.2f", MNAME[m], thrs[t]);
            else std::snprintf(lb, sizeof lb, "%s", MNAME[m]);
            print_run(lb, o);
         }
   }
   return 0;
}
