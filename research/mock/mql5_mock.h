// Minimal C++ stand-in for the slice of the MQL5 language/API used by this project.
//
// Purpose: (1) compile the MQL5 sources with g++ to catch typos, undeclared
// identifiers and type errors before MetaEditor sees them, and (2) run the
// platform-independent engine (XAU_Core.mqh) against test data.
//
// It is NOT a substitute for compiling in MetaEditor. It only knows the API
// surface this project touches, written from the public MQL5 reference.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
#include <vector>

typedef long long          datetime;
typedef unsigned int       color;
typedef unsigned char      uchar;
typedef std::string        string;

// ---- dynamic-array macros (see XAU_Core.mqh for the MQL5 side) --------------
typedef std::vector<double>   XVecD;
typedef std::vector<int>      XVecI;
typedef std::vector<datetime> XVecT;
typedef std::vector<string>   XVecS;

#define XCD(name)   const XVecD &name
#define XD(name)    XVecD &name
#define XCT(name)   const XVecT &name
#define XCI(name)   const XVecI &name
#define XI(name)    XVecI &name
#define XDARR(name) XVecD name
#define XIARR(name) XVecI name
#define XTARR(name) XVecT name
#define XSARR(name) XVecS name

// MQL5 keyword-ish things
#define input
#define sinput
#define NULL_STR ""

// ---- structs -----------------------------------------------------------------
struct MqlRates
{
   datetime time;
   double   open, high, low, close;
   long     tick_volume;
   int      spread;
   long     real_volume;
};
#define XCRATES(name) const std::vector<MqlRates> &name
#define XRATESARR(name) std::vector<MqlRates> name
#define XRATESOUT(name) std::vector<MqlRates> &name

// ---- arrays ------------------------------------------------------------------
template<typename T> inline int ArrayResize(std::vector<T> &a, int n) { a.resize((size_t)n); return n; }
template<typename T> inline int ArraySize(const std::vector<T> &a) { return (int)a.size(); }
template<typename T> inline void ArrayFree(std::vector<T> &a) { a.clear(); }
template<typename T> inline void ArrayInitialize(std::vector<T> &a, T v) { std::fill(a.begin(), a.end(), v); }
template<typename T, size_t N> inline void ArrayInitialize(T (&a)[N], T v) { for(size_t i = 0; i < N; i++) a[i] = v; }
inline void ArrayInitialize(XVecD &a, int v) { std::fill(a.begin(), a.end(), (double)v); }
template<typename T> inline int ArrayCopy(std::vector<T> &dst, const std::vector<T> &src) { dst = src; return (int)src.size(); }

// ---- math (MQL5 generic overloads) -------------------------------------------
inline double MathAbs(double x) { return std::fabs(x); }
inline double MathSqrt(double x) { return std::sqrt(x); }
inline double MathMax(double a, double b) { return a > b ? a : b; }
inline double MathMin(double a, double b) { return a < b ? a : b; }
inline double MathFloor(double x) { return std::floor(x); }
inline double MathCeil(double x) { return std::ceil(x); }
inline double MathRound(double x) { return std::round(x); }
inline double MathPow(double a, double b) { return std::pow(a, b); }
inline double MathLog(double x) { return std::log(x); }
inline double MathSin(double x) { return std::sin(x); }
inline double MathCos(double x) { return std::cos(x); }
inline double MathExp(double x) { return std::exp(x); }
inline double MathMod(double a, double b) { return std::fmod(a, b); }
inline bool   MathIsValidNumber(double x) { return std::isfinite(x); }
inline int    MathRand() { return std::rand() % 32768; }
inline void   MathSrand(int s) { std::srand((unsigned)s); }

#define DBL_MAX 1.7976931348623158e+308
#define EMPTY_VALUE DBL_MAX

// ---- strings -----------------------------------------------------------------
inline string IntegerToString(long v) { return std::to_string(v); }
inline string DoubleToString(double v, int digits = 8)
{
   char buf[64];
   std::snprintf(buf, sizeof buf, "%.*f", digits, v);
   return string(buf);
}
inline int StringLen(const string &s) { return (int)s.size(); }
template<typename T> inline T fmtarg(T v) { return v; }
inline const char *fmtarg(const string &s) { return s.c_str(); }
inline const char *fmtarg(const char *s) { return s; }
inline long long fmtarg(long v) { return v; }
template<typename... A> inline string StringFormat(const char *f, A... a)
{
   char buf[1024];
   std::snprintf(buf, sizeof buf, f, fmtarg(a)...);
   return string(buf);
}
inline void Print(const string &s) { std::printf("%s\n", s.c_str()); }
inline string TimeToString(datetime t, int flags = 0)
{
   (void)flags;
   long long d = t / 86400, s = t % 86400;
   long long z = d + 719468, era = (z >= 0 ? z : z - 146096) / 146097;
   long long doe = z - era * 146097, yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
   long long y = yoe + era * 400, doy = doe - (365 * yoe + yoe / 4 - yoe / 100), mp = (5 * doy + 2) / 153;
   long long dd = doy - (153 * mp + 2) / 5 + 1, m = mp < 10 ? mp + 3 : mp - 9;
   if(m <= 2) y++;
   char buf[64];
   std::snprintf(buf, sizeof buf, "%04lld.%02lld.%02lld %02lld:%02lld", y, m, dd, s / 3600, (s % 3600) / 60);
   return string(buf);
}
#define TIME_DATE 1
#define TIME_MINUTES 2
#define TIME_SECONDS 4

// =============================================================================
// Platform API surface (indicator / EA / XAU_Platform.mqh)
// Signatures follow the public MQL5 reference. Bodies return neutral defaults.
// =============================================================================
#include <sstream>

typedef int ENUM_TIMEFRAMES;
typedef int ENUM_BASE_CORNER;
typedef int ENUM_LINE_STYLE;
typedef int ENUM_ORDER_TYPE;
typedef int ENUM_ANCHOR_POINT;
typedef int ENUM_OBJECT;

enum { PERIOD_CURRENT = 0, PERIOD_M1 = 1, PERIOD_M2 = 2, PERIOD_M3 = 3, PERIOD_M4 = 4, PERIOD_M5 = 5,
       PERIOD_M6 = 6, PERIOD_M10 = 10, PERIOD_M12 = 12, PERIOD_M15 = 15, PERIOD_M20 = 20, PERIOD_M30 = 30,
       PERIOD_H1 = 16385, PERIOD_H2 = 16386, PERIOD_H3 = 16387, PERIOD_H4 = 16388, PERIOD_H6 = 16390,
       PERIOD_H8 = 16392, PERIOD_H12 = 16396, PERIOD_D1 = 16408, PERIOD_W1 = 32769, PERIOD_MN1 = 49153 };

inline int PeriodSeconds(int tf)
{
   switch(tf)
   {
      case PERIOD_M1: return 60; case PERIOD_M2: return 120; case PERIOD_M3: return 180; case PERIOD_M4: return 240;
      case PERIOD_M5: return 300; case PERIOD_M6: return 360; case PERIOD_M10: return 600; case PERIOD_M12: return 720;
      case PERIOD_M15: return 900; case PERIOD_M20: return 1200; case PERIOD_M30: return 1800;
      case PERIOD_H1: return 3600; case PERIOD_H2: return 7200; case PERIOD_H3: return 10800; case PERIOD_H4: return 14400;
      case PERIOD_H6: return 21600; case PERIOD_H8: return 28800; case PERIOD_H12: return 43200;
      case PERIOD_D1: return 86400; case PERIOD_W1: return 604800; case PERIOD_MN1: return 2592000;
   }
   return 900;
}
inline string EnumToString(int tf)
{
   switch(tf)
   {
      case PERIOD_M1: return "PERIOD_M1"; case PERIOD_M5: return "PERIOD_M5"; case PERIOD_M15: return "PERIOD_M15";
      case PERIOD_M30: return "PERIOD_M30"; case PERIOD_H1: return "PERIOD_H1"; case PERIOD_H4: return "PERIOD_H4";
      case PERIOD_D1: return "PERIOD_D1"; case PERIOD_W1: return "PERIOD_W1"; case PERIOD_MN1: return "PERIOD_MN1";
   }
   return "PERIOD_X";
}
inline string StringSubstr(const string &s, int pos, int len = -1)
{
   if(pos >= (int)s.size()) return "";
   return len < 0 ? s.substr((size_t)pos) : s.substr((size_t)pos, (size_t)len);
}
inline int StringFind(const string &s, const string &sub, int start = 0)
{
   size_t p = s.find(sub, (size_t)start);
   return p == string::npos ? -1 : (int)p;
}
inline bool StringToUpper(string &s) { for(auto &c : s) c = (char)std::toupper((unsigned char)c); return true; }

template<typename... A> inline void Print(A... a)
{
   std::ostringstream os;
   int dummy[] = {0, ((void)(os << a), 0)...};
   (void)dummy;
   std::printf("%s\n", os.str().c_str());
}
template<typename T> inline void ArraySetAsSeries(std::vector<T> &, bool) {}
inline bool PlaySound(const string &) { return true; }
inline bool SendNotification(const string &) { return true; }
inline bool SendMail(const string &, const string &) { return true; }
inline void Sleep(int) {}
inline void ResetLastError() {}
inline unsigned long long GetTickCount64() { return 0; }

// ---- globals -------------------------------------------------------------------
[[maybe_unused]] static string _Symbol = "XAUUSD";
[[maybe_unused]] static int _Period = PERIOD_M15;
[[maybe_unused]] static int _Digits = 2;
static datetime g_mock_now = 1704067200LL;
inline datetime TimeCurrent() { return g_mock_now; }
inline datetime TimeTradeServer() { return g_mock_now; }
inline datetime TimeLocal() { return g_mock_now; }
inline datetime TimeGMT() { return g_mock_now - 7200; }
inline datetime iTime(const string &, int, int) { return g_mock_now; }
inline double NormalizeDouble(double v, int d) { double m = std::pow(10.0, d); return std::round(v * m) / m; }

// ---- symbol / account ------------------------------------------------------------
enum { SYMBOL_TRADE_TICK_VALUE = 1, SYMBOL_TRADE_TICK_VALUE_LOSS, SYMBOL_TRADE_TICK_SIZE, SYMBOL_VOLUME_MIN,
       SYMBOL_VOLUME_MAX, SYMBOL_VOLUME_STEP, SYMBOL_POINT, SYMBOL_BID, SYMBOL_ASK,
       SYMBOL_SPREAD, SYMBOL_TRADE_STOPS_LEVEL, SYMBOL_TRADE_MODE, SYMBOL_DIGITS, SYMBOL_TRADE_CONTRACT_SIZE,
       SYMBOL_CURRENCY_PROFIT };
// mock broker settings that tests can change (e.g. a broker reporting a tick value 10x too small)
static double g_mock_tick_value = 1.0;
static bool   g_mock_calcprofit_ok = true;
enum { SYMBOL_TRADE_MODE_FULL = 4 };
enum { ORDER_TYPE_BUY = 0, ORDER_TYPE_SELL = 1 };
enum { ACCOUNT_TRADE_MODE = 50, ACCOUNT_TRADE_MODE_DEMO = 0 };
enum { ACCOUNT_LOGIN = 1, ACCOUNT_MARGIN_MODE, ACCOUNT_EQUITY, ACCOUNT_MARGIN_FREE, ACCOUNT_BALANCE, ACCOUNT_MARGIN_LEVEL,
       ACCOUNT_MARGIN_SO_SO, ACCOUNT_MARGIN, ACCOUNT_CURRENCY, ACCOUNT_MARGIN_SO_MODE };
enum { ACCOUNT_STOPOUT_MODE_PERCENT = 0, ACCOUNT_STOPOUT_MODE_MONEY = 1 };
enum { ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2 };
enum { TERMINAL_TRADE_ALLOWED = 1 };
enum { MQL_TRADE_ALLOWED = 1, MQL_TESTER = 2, MQL_VISUAL_MODE = 3 };
enum { INIT_FAILED = 1 };
inline double SymbolInfoDouble(const string &, int p)
{
   switch(p) { case SYMBOL_TRADE_TICK_VALUE: case SYMBOL_TRADE_TICK_VALUE_LOSS: return g_mock_tick_value; case SYMBOL_TRADE_CONTRACT_SIZE: return 100.0; case SYMBOL_TRADE_TICK_SIZE: return 0.01;
      case SYMBOL_VOLUME_MIN: return 0.01; case SYMBOL_VOLUME_MAX: return 100.0; case SYMBOL_VOLUME_STEP: return 0.01;
      case SYMBOL_POINT: return 0.01; case SYMBOL_BID: return 4000.0; case SYMBOL_ASK: return 4000.3; }
   return 0.0;
}
inline long SymbolInfoInteger(const string &, int p) { return p == SYMBOL_SPREAD ? 30 : (p == SYMBOL_TRADE_MODE ? 4 : (p == SYMBOL_DIGITS ? 2 : 0)); }
inline bool SymbolSelect(const string &, bool) { return true; }
inline double AccountInfoDouble(int p) { return p == ACCOUNT_MARGIN_FREE ? 9000.0 : (p == ACCOUNT_MARGIN_SO_SO ? 50.0 : (p == ACCOUNT_MARGIN_LEVEL ? 1200.0 : 10000.0)); }
inline string AccountInfoString(int) { return "USD"; }
inline string SymbolInfoString(const string &, int) { return "USD"; }
inline long AccountInfoInteger(int p) { return p == ACCOUNT_MARGIN_MODE ? ACCOUNT_MARGIN_MODE_RETAIL_HEDGING : (p == ACCOUNT_TRADE_MODE ? 0 : (p == ACCOUNT_MARGIN_SO_MODE ? 0 : 1)); }
inline long TerminalInfoInteger(int) { return 1; }
inline long MQLInfoInteger(int) { return 1; }
inline bool OrderCalcMargin(int, const string &, double v, double px, double &m) { m = v * px * 100.0 / 100.0; return true; }
// the broker's own profit formula: contract 100 oz, USD profit currency
inline bool OrderCalcProfit(int type, const string &, double v, double open, double close, double &pr)
{
   if(!g_mock_calcprofit_ok) return false;
   pr = (type == 0 ? (close - open) : (open - close)) * 100.0 * v;
   return true;
}
struct MqlTick { datetime time; double bid, ask, last; long volume; };
inline bool SymbolInfoTick(const string &, MqlTick &t) { t.bid = 4000.0; t.ask = 4000.3; t.time = g_mock_now; return true; }
template<typename T> inline int CopyRates(const string &, int, int, int, std::vector<T> &) { return 0; }
template<typename T> inline int CopyRates(const string &, int, datetime, int, std::vector<T> &) { return 0; }

// ---- calendar -------------------------------------------------------------------
struct MqlCalendarValue { ulong id, event_id; datetime time; };
struct MqlCalendarEvent { int importance; string name; };
#define XCALARR(name) std::vector<MqlCalendarValue> name
inline bool CalendarValueHistory(std::vector<MqlCalendarValue> &, datetime, datetime, const char *, const string &) { return false; }
inline bool CalendarEventById(ulong, MqlCalendarEvent &) { return false; }

// ---- objects / chart --------------------------------------------------------------
enum { OBJ_LABEL = 1, OBJ_RECTANGLE_LABEL, OBJ_TREND, OBJ_RECTANGLE, OBJ_TEXT, OBJ_VLINE };
enum { OBJPROP_SELECTABLE = 1, OBJPROP_HIDDEN, OBJPROP_ANCHOR, OBJPROP_FONT, OBJPROP_CORNER, OBJPROP_XDISTANCE,
       OBJPROP_YDISTANCE, OBJPROP_FONTSIZE, OBJPROP_COLOR, OBJPROP_TEXT, OBJPROP_XSIZE, OBJPROP_YSIZE,
       OBJPROP_BGCOLOR, OBJPROP_BORDER_TYPE, OBJPROP_BACK, OBJPROP_STYLE, OBJPROP_WIDTH, OBJPROP_RAY_RIGHT, OBJPROP_FILL };
enum { ANCHOR_LEFT_UPPER = 1, ANCHOR_LEFT };
enum { CORNER_LEFT_UPPER = 0, CORNER_LEFT_LOWER = 2 };
enum { BORDER_FLAT = 1 };
enum { STYLE_SOLID = 0, STYLE_DASH, STYLE_DOT, STYLE_DASHDOT };
enum { CHART_SHIFT = 1, CHART_SHIFT_SIZE };
inline int  ObjectFind(long, const string &) { return -1; }
inline bool ObjectCreate(long, const string &, int, int, datetime, double, datetime = 0, double = 0.0) { return true; }
inline bool ObjectSetInteger(long, const string &, int, long) { return true; }
inline bool ObjectSetString(long, const string &, int, const string &) { return true; }
inline bool ObjectMove(long, const string &, int, datetime, double) { return true; }
inline bool ObjectDelete(long, const string &) { return true; }
inline int  ObjectsDeleteAll(long, const string &, int = -1, int = -1) { return 0; }
inline bool ChartSetInteger(long, int, long) { return true; }
inline bool ChartSetDouble(long, int, double) { return true; }
inline void ChartRedraw(long = 0) {}
enum { CHART_HEIGHT_IN_PIXELS = 100, CHART_WIDTH_IN_PIXELS = 101 };
inline long ChartGetInteger(long, int p, int = 0) { return p == CHART_HEIGHT_IN_PIXELS ? 800 : 1400; }
inline bool TextSetFont(const string &, int, uint = 0, int = 0) { return true; }
inline bool TextGetSize(const string &t, uint &w, uint &h) { w = (uint)(t.size() * 7); h = 14; return true; }

// ---- indicator plumbing --------------------------------------------------------
enum { INIT_SUCCEEDED = 0, INDICATOR_DATA = 0, INDICATOR_COLOR_INDEX = 1, INDICATOR_SHORTNAME = 1, INDICATOR_DIGITS = 2,
       PLOT_EMPTY_VALUE = 1, PLOT_ARROW = 2 };
template<typename T> inline bool SetIndexBuffer(int, std::vector<T> &, int) { return true; }
inline bool PlotIndexSetDouble(int, int, double) { return true; }
inline bool PlotIndexSetInteger(int, int, int) { return true; }
inline bool IndicatorSetString(int, const string &) { return true; }
inline bool IndicatorSetInteger(int, int) { return true; }
inline bool EventSetTimer(int) { return true; }
inline void EventKillTimer() {}

// ---- global variables --------------------------------------------------------------
inline bool GlobalVariableCheck(const string &) { return false; }
inline double GlobalVariableGet(const string &) { return 0.0; }
inline datetime GlobalVariableSet(const string &, double) { return 0; }
inline bool GlobalVariableDel(const string &) { return true; }
inline int GlobalVariablesDeleteAll(const string & = "", datetime = 0) { return 0; }

// ---- trading ---------------------------------------------------------------------
enum { TRADE_RETCODE_INVALID_STOPS = 10016, TRADE_RETCODE_REQUOTE = 10004, TRADE_RETCODE_PLACED = 10008, TRADE_RETCODE_DONE = 10009, TRADE_RETCODE_DONE_PARTIAL = 10010,
       TRADE_RETCODE_PRICE_CHANGED = 10020, TRADE_RETCODE_PRICE_OFF = 10021 };
class CTrade
{
public:
   void SetExpertMagicNumber(ulong) {}
   void SetDeviationInPoints(ulong) {}
   bool SetTypeFillingBySymbol(const string &) { return true; }
   void SetAsyncMode(bool) {}
   bool Buy(double, const string &, double, double, double, const string & = "") { return true; }
   bool Sell(double, const string &, double, double, double, const string & = "") { return true; }
   bool PositionClose(ulong) { return true; }
   bool PositionClosePartial(ulong, double) { return true; }
   bool PositionModify(ulong, double, double) { return true; }
   uint ResultRetcode() const { return TRADE_RETCODE_DONE; }
   ulong ResultOrder() const { return 1; }
   string ResultRetcodeDescription() const { return "done"; }
};
enum { POSITION_TYPE_BUY = 0, POSITION_TYPE_SELL = 1 };
enum { POSITION_SYMBOL = 1, POSITION_MAGIC, POSITION_TYPE, POSITION_PRICE_OPEN, POSITION_SL, POSITION_TP, POSITION_VOLUME,
       POSITION_TIME, POSITION_IDENTIFIER };
inline int PositionsTotal() { return 0; }
inline ulong PositionGetTicket(int) { return 0; }
inline string PositionGetString(int) { return ""; }
inline long PositionGetInteger(int) { return 0; }
inline double PositionGetDouble(int) { return 0.0; }
enum { DEAL_MAGIC = 1, DEAL_SYMBOL, DEAL_ENTRY, DEAL_TYPE, DEAL_POSITION_ID, DEAL_TIME, DEAL_PROFIT, DEAL_SWAP, DEAL_COMMISSION };
enum { DEAL_ENTRY_IN = 0, DEAL_ENTRY_OUT = 1, DEAL_ENTRY_INOUT = 2, DEAL_ENTRY_OUT_BY = 3 };
enum { DEAL_TYPE_BUY = 0, DEAL_TYPE_SELL = 1 };
inline bool HistorySelect(datetime, datetime) { return true; }
inline int HistoryDealsTotal() { return 0; }
inline ulong HistoryDealGetTicket(int) { return 0; }
inline long HistoryDealGetInteger(ulong, int) { return 0; }
inline double HistoryDealGetDouble(ulong, int) { return 0.0; }
inline string HistoryDealGetString(ulong, int) { return ""; }
struct MqlTradeTransaction { int type; ulong deal; };
struct MqlTradeRequest { int dummy; };
struct MqlTradeResult { int dummy; };
enum { TRADE_TRANSACTION_DEAL_ADD = 6 };
enum { STAT_PROFIT = 1, STAT_TRADES, STAT_PROFIT_FACTOR, STAT_RECOVERY_FACTOR };
inline double TesterStatistics(int) { return 0.0; }

// ---- files / terminal (data export script) -------------------------------------
enum { FILE_WRITE = 2, FILE_CSV = 8, FILE_ANSI = 32, FILE_TXT = 16, INVALID_HANDLE = -1 };
enum { TERMINAL_DATA_PATH = 1 };
inline int FileOpen(const string &, int, int = 0) { return 1; }
inline int FileOpen(const string &, int, char) { return 1; }
template<typename... A> inline unsigned FileWrite(int, A...) { return 0; }
inline void FileClose(int) {}
inline string TerminalInfoString(int) { return "C:\\data"; }
inline int GetLastError() { return 0; }
template<typename... A> inline void Alert(A...) {}
