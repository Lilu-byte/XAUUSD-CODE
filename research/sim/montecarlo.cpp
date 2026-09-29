// Monte Carlo of what "double the account every month" requires.
//
// No market data involved: this is pure risk arithmetic. Each trade is one of three
// outcomes, matching the engine's trade plan (50% closed at 1R, stop to break-even, runner to 2.5R):
//     stop-loss       -1.00 R   probability 1 - p1
//     break-even runner +0.50 R   probability p1 * (1 - q)
//     runner to TP2   +1.75 R   probability p1 * q          (q = 0.4)
// so expectancy E = 2*p1 - 1 and the "win rate" (net R > 0) is p1.
//
// Risk is fixed-fractional on CURRENT equity (compounding), as the EA does.
//
// Build: g++ -std=c++17 -O2 -o montecarlo montecarlo.cpp && ./montecarlo

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

struct Res
{
   double p_double, p_up20, p_down20, p_dd30, p_dd50, med_ret, p10, p90;
};

static Res run(double p1, int trades, double risk, int paths, unsigned seed)
{
   std::mt19937_64 rng(seed);
   std::uniform_real_distribution<double> u(0.0, 1.0);
   const double q = 0.4;
   int dbl = 0, up20 = 0, dn20 = 0, dd30 = 0, dd50 = 0;
   std::vector<double> fin;
   fin.reserve(paths);
   for(int k = 0; k < paths; k++)
   {
      double eq = 1.0, peak = 1.0, mdd = 0.0;
      for(int t = 0; t < trades; t++)
      {
         double r;
         const double x = u(rng);
         if(x < 1.0 - p1)               r = -1.0;
         else if(x < 1.0 - p1 + p1 * (1.0 - q)) r = 0.5;
         else                            r = 1.75;
         eq *= (1.0 + risk * r);
         if(eq <= 0.0) { eq = 0.0; mdd = 1.0; break; }
         peak = std::max(peak, eq);
         mdd = std::max(mdd, 1.0 - eq / peak);
      }
      fin.push_back(eq);
      if(eq >= 2.0) dbl++;
      if(eq >= 1.2) up20++;
      if(eq <= 0.8) dn20++;
      if(mdd >= 0.30) dd30++;
      if(mdd >= 0.50) dd50++;
   }
   std::sort(fin.begin(), fin.end());
   Res r;
   r.p_double = 100.0 * dbl / paths;
   r.p_up20 = 100.0 * up20 / paths;
   r.p_down20 = 100.0 * dn20 / paths;
   r.p_dd30 = 100.0 * dd30 / paths;
   r.p_dd50 = 100.0 * dd50 / paths;
   r.med_ret = 100.0 * (fin[paths / 2] - 1.0);
   r.p10 = 100.0 * (fin[paths / 10] - 1.0);
   r.p90 = 100.0 * (fin[paths * 9 / 10] - 1.0);
   return r;
}

int main()
{
   const int paths = 40000;
   struct Sc { const char *name; double p1; };
   const Sc scen[] = {
      {"no edge after costs   (E=-0.10R, win 45%)", 0.45},
      {"modest edge           (E=+0.10R, win 55%)", 0.55},
      {"good edge             (E=+0.25R, win 62%)", 0.625},
      {"exceptional edge      (E=+0.50R, win 75%)", 0.75},
   };
   const int tr_opts[] = {12, 24, 48};
   const double risks[] = {0.005, 0.01, 0.02, 0.03, 0.05, 0.10, 0.20};

   std::printf("# Monte Carlo: one month of trading, %d simulated months per cell\n", paths);
   std::printf("# columns: risk/trade | P(>=2x) | P(>=+20%%) | P(<=-20%%) | P(maxDD>=30%%) | P(maxDD>=50%%) | median | 10th pct | 90th pct\n");
   for(const Sc &s : scen)
   {
      for(int trades : tr_opts)
      {
         std::printf("\n## %s, %d trades/month\n", s.name, trades);
         std::printf("| risk/trade | P(double) | P(>=+20%%) | P(<=-20%%) | P(DD>=30%%) | P(DD>=50%%) | median | 10th pct | 90th pct |\n");
         std::printf("|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n");
         for(double rk : risks)
         {
            Res r = run(s.p1, trades, rk, paths, 12345u + (unsigned)(rk * 1000) + (unsigned)trades);
            std::printf("| %.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %+6.1f%% | %+6.1f%% | %+7.1f%% |\n",
                        rk * 100.0, r.p_double, r.p_up20, r.p_down20, r.p_dd30, r.p_dd50, r.med_ret, r.p10, r.p90);
         }
      }
   }
   return 0;
}
