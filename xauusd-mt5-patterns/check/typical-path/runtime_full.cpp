// Runs the translated indicator on a CSV and prints the kept patterns for comparison with detect_ref.py.
#include "gp_full.cpp"
#include <map>
#include <set>
std::map<std::string,int> SEEN; std::set<std::string> PREV; int vanishN = 0, edgeN = 0; int lateN = 0, lateSum = 0, confN = 0;
struct Ob { int type; long long t1, t2; double p1, p2; std::map<int,long> I; std::map<int,std::string> S; };
std::map<std::string, Ob> OBJ;
#include <cstdio>
#include <fstream>
#include <sstream>
#include <algorithm>
const string _Symbol = "XAUUSD"; const ENUM_TIMEFRAMES _Period = PERIOD_H1; const double _Point = 0.01; const int _Digits = 2;
int nObj = 0, nAlert = 0;
bool ObjectCreate(long, string nm, ENUM_OBJECT ty, int, datetime t1, double p1, datetime t2, double p2, datetime, double) { nObj++; Ob o; o.type = ty; o.t1 = t1; o.t2 = t2; o.p1 = p1; o.p2 = p2; OBJ[nm] = o; return true; }
bool ObjectSetInteger(long, string nm, ENUM_OBJECT_PROPERTY_INTEGER pr, long v) { OBJ[nm].I[pr] = v; return true; }
bool ObjectSetInteger(long, string nm, ENUM_OBJECT_PROPERTY_INTEGER pr, ENUM_ARROW_ANCHOR v) { OBJ[nm].I[pr] = v; return true; }
bool ObjectSetString(long, string nm, ENUM_OBJECT_PROPERTY_STRING pr, string v) { OBJ[nm].S[pr] = v; return true; }
int  ObjectsDeleteAll(long, const string, int, int) { nObj = 0; OBJ.clear(); return 0; }
void ChartRedraw(long) {}
long ChartGetInteger(long, ENUM_CHART_PROPERTY_INTEGER p, int) { return p == CHART_COLOR_FOREGROUND ? 0xFFFFFF : 0; }
int  PeriodSeconds(ENUM_TIMEFRAMES) { return 3600; }
bool SendNotification(string) { return true; }
string StringSubstr(string s, int st, int len) { return len < 0 ? s.substr(st) : s.substr(st, len); }
template<class E> string EnumToString(E) { return "PERIOD_H1"; }
template<class... A> void Alert(A... a) { nAlert++; if(getenv("SHOWALERT")) { ((std::fputs(a.c_str(), stderr)), ...); std::fputs("\n", stderr); } }
std::vector<std::string> TS;
string TimeToString(datetime v, int) { long long k = (v - 1000000) / 3600; return k >= 0 && k < (long long)TS.size() ? TS[k] : std::to_string(v); }
string DoubleToString(double v, int) { char b[64]; snprintf(b, 64, "%.2f", v); return b; }
string IntegerToString(long n, int, ushort) { return std::to_string(n); }
double MathRound(double v) { return std::round(v); }
template<class T> T MathAbs(T v) { return v < 0 ? -v : v; }
template<class A, class B> auto MathMin(A a, B b) -> decltype(a + b) { return a < b ? a : b; }
template<class A, class B> auto MathMax(A a, B b) -> decltype(a + b) { return a > b ? a : b; }
template<class T> bool ArraySetAsSeries(const DynArr<T> &, bool) { return true; }
bool TextSetFont(const string, int, unsigned int, int) { return true; }
bool TextGetSize(const string t, unsigned int &w, unsigned int &h) { w = (unsigned)(t.size() * 6.2); h = 14; return true; }

int main(int argc, char **argv)
{
   std::ifstream f(argv[1]); std::string line; std::getline(f, line);
   DynArr<datetime> T; DynArr<double> O, H, L, C; DynArr<long> V; DynArr<int> S;
   int k = 0;
   while(std::getline(f, line)) { std::stringstream ss(line); std::string tok; std::getline(ss, tok, ','); TS.push_back(tok);
      T.v.push_back(1000000 + 3600LL * k++); double x[4]; for(int j = 0; j < 4; j++) { std::getline(ss, tok, ','); x[j] = std::stod(tok); }
      O.v.push_back(x[0]); H.v.push_back(x[1]); L.v.push_back(x[2]); C.v.push_back(x[3]); V.v.push_back(0); S.v.push_back(0); }
   int n0 = atoi(argv[2]), n1 = atoi(argv[3]);   // rates_total from n0 to n1, one new candle at a time
   OnInit();
   int prev = 0;
   for(int rt = n0; rt <= n1; rt++)
   {
      DynArr<datetime> t; DynArr<double> o, h, l, c; DynArr<long> v, vv; DynArr<int> s;
      int b0 = getenv("SLICE") ? std::max(0, rt - 3400) : 0, nn = rt - b0;
      t.v.assign(T.v.begin() + b0, T.v.begin() + rt); o.v.assign(O.v.begin() + b0, O.v.begin() + rt); h.v.assign(H.v.begin() + b0, H.v.begin() + rt);
      l.v.assign(L.v.begin() + b0, L.v.begin() + rt); c.v.assign(C.v.begin() + b0, C.v.begin() + rt); v.v.assign(nn, 0); vv.v.assign(nn, 0); s.v.assign(nn, 0);
      prev = OnCalculate(nn, prev, t, o, h, l, c, v, vv, s);
      if(getenv("REPAINT")) { int st0 = rt - 1 - gN; std::set<std::string> NOWS;
         for(int x = 0; x < gNPat; x++) if(gP[x].keep && !gP[x].forming) {
            char kb[96]; snprintf(kb, 96, "%d %lld %lld", gP[x].kind, (long long)gT[gP[x].s], (long long)gT[gP[x].brk]);
            NOWS.insert(kb);
            if(!SEEN.count(kb)) { SEEN[kb] = rt; if(rt > n0 && gP[x].s > 300) { confN++; int lag = gN - 1 - gP[x].brk; if(lag > 0) { lateN++; lateSum += lag; if(getenv("SHOWLATE")) fprintf(stderr, "LATE %d by %d (conf-brk %d)\n", gP[x].kind, lag, gP[x].conf - gP[x].brk); } } } }
         for(auto &k2 : PREV) if(!NOWS.count(k2)) { long long ts; int kd; long long tb; sscanf(k2.c_str(), "%d %lld %lld", &kd, &ts, &tb);
            if(ts >= gT[300]) { vanishN++; fprintf(stderr, "VANISH step %d: %s\n", rt, k2.c_str()); } else edgeN++; }
         PREV = NOWS; }
   }
   int start = std::max(0, n1 - 1 - std::max(200, InpMaxBars) - WARMUP);
   fprintf(stderr, "window %d..%d warm %d objects %d alerts %d\n", start, n1 - 2, gWarm, nObj, nAlert);
   if(getenv("DUMP")) { FILE *q = fopen(getenv("DUMP"), "w");
      for(auto &kv : OBJ) { auto &o = kv.second; fprintf(q, "%s\t%d\t%lld\t%.3f\t%lld\t%.3f\t%ld\t%ld\t%ld\t%ld\t%ld\t%ld\t%ld\t%s\t%ld\t%ld\t%ld\t%ld\t%ld\n", kv.first.c_str(), o.type, o.t1, o.p1, o.t2, o.p2,
         o.I[OBJPROP_COLOR], o.I[OBJPROP_STYLE], o.I[OBJPROP_WIDTH], o.I[OBJPROP_FILL], o.I[OBJPROP_ANCHOR], o.I[OBJPROP_YDISTANCE], o.I[OBJPROP_FONTSIZE], o.S[OBJPROP_TEXT].c_str(), o.I[OBJPROP_CORNER], o.I[OBJPROP_XDISTANCE], o.I[OBJPROP_XSIZE], o.I[OBJPROP_YSIZE], o.I[OBJPROP_BGCOLOR]); }
      fclose(q); }
   if(getenv("REPAINT")) { std::set<std::string> now; int gone = 0, old = 0;
      for(int x = 0; x < gNPat; x++) if(gP[x].keep && !gP[x].forming) { char kb[96]; snprintf(kb, 96, "%d %lld %lld", gP[x].kind, (long long)gT[gP[x].s], (long long)gT[gP[x].brk]); now.insert(kb); }
      for(auto &kv : SEEN) { long long ts; int kd; long long tb; sscanf(kv.first.c_str(), "%d %lld %lld", &kd, &ts, &tb);
         if(!now.count(kv.first)) { if(ts >= gT[300]) { gone++; fprintf(stderr, "GONE %s first seen at %d\n", kv.first.c_str(), kv.second); } else old++; } }
      fprintf(stderr, "repaint: new confirmed %d, appeared after breakout candle %d (avg %.1f candles late), vanished %d (edge %d); per-step vanished in view %d, at left edge %d\n", confN, lateN, lateN ? (double)lateSum / lateN : 0.0, gone, old, vanishN, edgeN); }
   std::vector<int> idx; for(int x = 0; x < gNPat; x++) if(gP[x].keep) idx.push_back(x);
   std::sort(idx.begin(), idx.end(), [](int a, int b) { if(gP[a].s != gP[b].s) return gP[a].s < gP[b].s; if(gP[a].kind != gP[b].kind) return gP[a].kind < gP[b].kind; return gP[a].e < gP[b].e; });
   static const char *KS[] = { "double_top", "double_bottom", "triple_top", "triple_bottom", "head_shoulders", "inv_head_shoulders", "asc_triangle", "desc_triangle", "sym_triangle", "rising_wedge", "falling_wedge", "rectangle", "broadening", "channel_up", "channel_down", "bull_flag", "bear_flag", "bull_pennant", "bear_pennant", "cup_handle", "inv_cup_handle", "rounding_bottom", "rounding_top" };
   if(getenv("DUMPPAT")) { for(int x = 0; x < gNPat; x++) if(gP[x].keep && !gP[x].forming) printf("%d %d %d %d %d %d %.5f %.5f %.5f\n", gP[x].kind, gP[x].s, gP[x].e, gP[x].brk, gP[x].conf, gP[x].dir, gP[x].entry, gP[x].stop, gP[x].target); return 0; }
   for(int x : idx) printf("P %s %d %d %d %d %d %.2f\n", KS[gP[x].kind], gP[x].s, gP[x].e, gP[x].brk, gP[x].dir, gP[x].forming, gP[x].target);
}
