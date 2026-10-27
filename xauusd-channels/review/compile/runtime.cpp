// Runs the translated indicator on a CSV: first call = full rebuild, then one candle at a time (incremental path).
// Prints every fixed stretch and break so they can be compared with the Python prototype.
#include "gch_as_cpp.cpp"
#include <cstdio>
#include <fstream>
#include <sstream>
const string _Symbol = "XAUUSD"; const ENUM_TIMEFRAMES _Period = PERIOD_H1; const double _Point = 0.01; const int _Digits = 2;
int nObj = 0;
bool ObjectCreate(long, string, ENUM_OBJECT, int, datetime, double, datetime, double, datetime, double) { nObj++; return true; }
bool ObjectSetInteger(long, string, ENUM_OBJECT_PROPERTY_INTEGER, long) { return true; }
bool ObjectSetInteger(long, string, ENUM_OBJECT_PROPERTY_INTEGER, ENUM_ARROW_ANCHOR) { return true; }
bool ObjectSetString(long, string, ENUM_OBJECT_PROPERTY_STRING, string) { return true; }
bool ObjectDelete(long, string) { return true; }
int  ObjectsDeleteAll(long, const string, int, int) { return 0; }
void ChartRedraw(long) {}
long ChartGetInteger(long, ENUM_CHART_PROPERTY_INTEGER, int) { return 0; }
int  PeriodSeconds(ENUM_TIMEFRAMES tf) { switch(tf) { case PERIOD_M1: return 60; case PERIOD_H4: return 14400; case PERIOD_D1: return 86400; case PERIOD_W1: return 604800; default: return 3600; } }
// higher timeframe (D1 for an H1 chart) read from a second CSV
std::vector<double> DH, DL, DC; std::vector<datetime> DT;
int Bars(const string, ENUM_TIMEFRAMES) { return (int)DC.size(); }
datetime iTime(const string, ENUM_TIMEFRAMES, int) { return DT.empty() ? 0 : DT.back(); }
template<class T> int cp(const std::vector<T> &src, int start, int count, DynArr<T> &dst) { dst.v.assign(src.end() - start - count, src.end() - start); return count; }
int CopyTime(const string, ENUM_TIMEFRAMES, int st, int n, DynArr<datetime> &a) { return cp(DT, st, n, a); }
int CopyHigh(const string, ENUM_TIMEFRAMES, int st, int n, DynArr<double> &a) { return cp(DH, st, n, a); }
int CopyLow(const string, ENUM_TIMEFRAMES, int st, int n, DynArr<double> &a) { return cp(DL, st, n, a); }
int CopyClose(const string, ENUM_TIMEFRAMES, int st, int n, DynArr<double> &a) { return cp(DC, st, n, a); }
bool SendNotification(string) { return true; }
string StringSubstr(string s, int st, int len) { return len < 0 ? s.substr(st) : s.substr(st, len); }
template<class E> string EnumToString(E) { return "PERIOD_H1"; }
bool EventSetTimer(int) { return true; }
void EventKillTimer() {}
int StringLen(string s) { return (int)s.size(); }
template<class... A> void Print(A...) {}
template<class... A> void Alert(A...) {}
string TimeToString(datetime v, int) { return std::to_string(v); }
string DoubleToString(double v, int) { return std::to_string(v); }
string IntegerToString(long n, int, ushort) { return std::to_string(n); }
double MathRound(double v) { return std::round(v); }
double MathSqrt(double v) { return std::sqrt(v); }
template<class T> T MathAbs(T v) { return v < 0 ? -v : v; }
template<class A, class B> auto MathMin(A a, B b) -> decltype(a + b) { return a < b ? a : b; }
template<class A, class B> auto MathMax(A a, B b) -> decltype(a + b) { return a > b ? a : b; }
int ArrayInitialize(DynArr<double> &a, double v) { for(auto &x : a.v) x = v; return (int)a.v.size(); }
template<class T> bool ArraySetAsSeries(const DynArr<T> &, bool) { return true; }

int main(int argc, char **argv)
{
   std::ifstream f(argv[1]); std::string line; std::getline(f, line);
   DynArr<datetime> T; DynArr<double> O, H, L, C; DynArr<long> V; DynArr<int> S;
   int k = 0;
   while(std::getline(f, line)) { std::stringstream ss(line); std::string tok; std::getline(ss, tok, ',');
      T.v.push_back(k++); double x[4]; for(int j = 0; j < 4; j++) { std::getline(ss, tok, ','); x[j] = std::stod(tok); }
      O.v.push_back(x[0]); H.v.push_back(x[1]); L.v.push_back(x[2]); C.v.push_back(x[3]); V.v.push_back(0); S.v.push_back(0); }
   int n0 = atoi(argv[2]), n1 = atoi(argv[3]);
   if(argc > 4) { std::ifstream g(argv[4]); std::getline(g, line); int q = 0;
      while(std::getline(g, line)) { std::stringstream ss(line); std::string tok; std::getline(ss, tok, ','); DT.push_back(1000000 + q++);
         double x[4]; for(int j = 0; j < 4; j++) { std::getline(ss, tok, ','); x[j] = std::stod(tok); } DH.push_back(x[1]); DL.push_back(x[2]); DC.push_back(x[3]); } }
   OnInit();
   int prev = 0;
   for(int rt = n0; rt <= n1; rt++)
   {
      DynArr<datetime> t; DynArr<double> o, h, l, c; DynArr<long> v; DynArr<int> s;
      t.v.assign(T.v.begin(), T.v.begin() + rt); o.v.assign(O.v.begin(), O.v.begin() + rt); h.v.assign(H.v.begin(), H.v.begin() + rt);
      l.v.assign(L.v.begin(), L.v.begin() + rt); c.v.assign(C.v.begin(), C.v.begin() + rt); v.v.assign(rt, 0); s.v.assign(rt, 0);
      prev = OnCalculate(rt, prev, t, o, h, l, c, v, v, s);
   }
   for(int i = 0; i < gM.n; i++) printf("S %d %d %d\n", gM.segS[i], gM.segE[i], gM.segLab[i]);
   printf("LIVE %d %d\n", gM.cur, gM.done);
   for(int i = 0; i < gM.nb; i++) printf("B %d %d\n", gM.brkT[i], gM.brkD[i]);
   for(int i = 0; i < gH.n; i++) printf("HS %d %d %d\n", gH.segS[i], gH.segE[i], gH.segLab[i]);
   printf("HTF ok %d bars %d minBars %d status: %s\nMAIN status: %s\n", (int)gHtfOK, (int)DC.size(), gH.minBars, gTxtHTF.c_str(), gTxtMain.c_str());
   fprintf(stderr, "objects created: %d\n", nObj);
}
