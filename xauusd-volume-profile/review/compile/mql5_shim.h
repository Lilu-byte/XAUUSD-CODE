// Minimal C++ stand-ins for the MQL5 built-ins the indicator uses, with the
// documented MQL5 signatures (build 4000+). Only names that exist in MQL5 are
// declared, so a misspelt constant or a wrong argument list fails to compile.
#include <string>
#include <vector>
#include <cfloat>
typedef std::string string;
typedef long long datetime;            // MQL5: 8-byte integer type
typedef unsigned int color;            // MQL5: 4-byte integer type
typedef unsigned short ushort;
#define RGB_(r,g,b) ((color)((r) | ((g) << 8) | ((b) << 16)))
const color clrGold = RGB_(255,215,0), clrSilver = RGB_(192,192,192), clrDodgerBlue = RGB_(30,144,255);

template<class T> struct DynArr {      // MQL5 dynamic array T a[]
  std::vector<T> v;
  T &operator[](int i) { return v[i]; }
  const T &operator[](int i) const { return v[i]; }
};

enum ENUM_TIMEFRAMES { PERIOD_CURRENT = 0, PERIOD_M1 = 1, PERIOD_M2, PERIOD_M3, PERIOD_M4, PERIOD_M5, PERIOD_M6,
  PERIOD_M10 = 10, PERIOD_M12 = 12, PERIOD_M15 = 15, PERIOD_M20 = 20, PERIOD_M30 = 30, PERIOD_H1 = 16385,
  PERIOD_H2, PERIOD_H3, PERIOD_H4, PERIOD_H6 = 16390, PERIOD_H8 = 16392, PERIOD_H12 = 16396,
  PERIOD_D1 = 16408, PERIOD_W1 = 32769, PERIOD_MN1 = 49153 };
enum ENUM_APPLIED_VOLUME { VOLUME_TICK, VOLUME_REAL };
enum ENUM_OBJECT { OBJ_VLINE, OBJ_HLINE, OBJ_TREND, OBJ_TRENDBYANGLE, OBJ_CYCLES, OBJ_ARROWED_LINE, OBJ_CHANNEL,
  OBJ_STDDEVCHANNEL, OBJ_REGRESSION, OBJ_PITCHFORK, OBJ_RECTANGLE, OBJ_TRIANGLE, OBJ_ELLIPSE, OBJ_TEXT,
  OBJ_LABEL, OBJ_BUTTON, OBJ_CHART, OBJ_BITMAP, OBJ_BITMAP_LABEL, OBJ_EDIT, OBJ_EVENT, OBJ_RECTANGLE_LABEL };
enum ENUM_OBJECT_PROPERTY_INTEGER { OBJPROP_COLOR, OBJPROP_STYLE, OBJPROP_WIDTH, OBJPROP_BACK, OBJPROP_ZORDER,
  OBJPROP_FILL, OBJPROP_HIDDEN, OBJPROP_SELECTED, OBJPROP_READONLY, OBJPROP_TYPE, OBJPROP_TIME, OBJPROP_SELECTABLE,
  OBJPROP_CREATETIME, OBJPROP_LEVELS, OBJPROP_LEVELCOLOR, OBJPROP_LEVELSTYLE, OBJPROP_LEVELWIDTH, OBJPROP_ALIGN,
  OBJPROP_FONTSIZE, OBJPROP_RAY_LEFT, OBJPROP_RAY_RIGHT, OBJPROP_RAY, OBJPROP_ELLIPSE, OBJPROP_ARROWCODE,
  OBJPROP_TIMEFRAMES, OBJPROP_ANCHOR, OBJPROP_XDISTANCE, OBJPROP_YDISTANCE, OBJPROP_DIRECTION, OBJPROP_DEGREE,
  OBJPROP_DRAWLINES, OBJPROP_STATE, OBJPROP_CHART_ID, OBJPROP_XSIZE, OBJPROP_YSIZE, OBJPROP_XOFFSET,
  OBJPROP_YOFFSET, OBJPROP_PERIOD, OBJPROP_DATE_SCALE, OBJPROP_PRICE_SCALE, OBJPROP_CHART_SCALE,
  OBJPROP_BGCOLOR, OBJPROP_CORNER, OBJPROP_BORDER_TYPE, OBJPROP_BORDER_COLOR };
enum ENUM_OBJECT_PROPERTY_DOUBLE { OBJPROP_PRICE, OBJPROP_LEVELVALUE, OBJPROP_SCALE, OBJPROP_ANGLE, OBJPROP_DEVIATION };
enum ENUM_OBJECT_PROPERTY_STRING { OBJPROP_NAME, OBJPROP_TEXT, OBJPROP_TOOLTIP, OBJPROP_LEVELTEXT, OBJPROP_FONT,
  OBJPROP_BMPFILE, OBJPROP_SYMBOL };
enum ENUM_LINE_STYLE { STYLE_SOLID, STYLE_DASH, STYLE_DOT, STYLE_DASHDOT, STYLE_DASHDOTDOT };
enum ENUM_ANCHOR_POINT { ANCHOR_LEFT_UPPER, ANCHOR_LEFT, ANCHOR_LEFT_LOWER, ANCHOR_LOWER, ANCHOR_RIGHT_LOWER,
  ANCHOR_RIGHT, ANCHOR_RIGHT_UPPER, ANCHOR_UPPER, ANCHOR_CENTER };
enum ENUM_BASE_CORNER { CORNER_LEFT_UPPER, CORNER_LEFT_LOWER, CORNER_RIGHT_LOWER, CORNER_RIGHT_UPPER };
enum ENUM_CHART_EVENT { CHARTEVENT_KEYDOWN, CHARTEVENT_MOUSE_MOVE, CHARTEVENT_OBJECT_CREATE, CHARTEVENT_OBJECT_CHANGE,
  CHARTEVENT_OBJECT_DELETE, CHARTEVENT_CLICK, CHARTEVENT_OBJECT_CLICK, CHARTEVENT_OBJECT_DRAG,
  CHARTEVENT_OBJECT_ENDEDIT, CHARTEVENT_CHART_CHANGE, CHARTEVENT_CUSTOM = 1000 };
enum ENUM_INIT_RETCODE { INIT_SUCCEEDED, INIT_FAILED, INIT_PARAMETERS_INCORRECT, INIT_AGENT_NOT_SUITABLE };
const int REASON_PROGRAM = 0, REASON_REMOVE = 1, REASON_RECOMPILE = 2, REASON_CHARTCHANGE = 3, REASON_CHARTCLOSE = 4,
  REASON_PARAMETERS = 5, REASON_ACCOUNT = 6, REASON_TEMPLATE = 7, REASON_INITFAILED = 8, REASON_CLOSE = 9;
const int TIME_DATE = 1, TIME_MINUTES = 2, TIME_SECONDS = 4;

struct MqlRates { datetime time; double open, high, low, close; long tick_volume; int spread; long real_volume; };

extern const string _Symbol; extern const ENUM_TIMEFRAMES _Period; extern const double _Point; extern const int _Digits;

bool ObjectCreate(long chart_id, string object_name, ENUM_OBJECT object_type, int sub_window,
                  datetime time1, double price1, datetime time2 = 0, double price2 = 0, datetime time3 = 0, double price3 = 0);
bool ObjectSetInteger(long chart_id, string name, ENUM_OBJECT_PROPERTY_INTEGER prop_id, long prop_value);
bool ObjectSetInteger(long chart_id, string name, ENUM_OBJECT_PROPERTY_INTEGER prop_id, int prop_modifier, long prop_value);
bool ObjectSetString(long chart_id, string name, ENUM_OBJECT_PROPERTY_STRING prop_id, string prop_value);
bool ObjectSetString(long chart_id, string name, ENUM_OBJECT_PROPERTY_STRING prop_id, int prop_modifier, string prop_value);
long ObjectGetInteger(long chart_id, string name, ENUM_OBJECT_PROPERTY_INTEGER prop_id, int prop_modifier = 0);
bool ObjectGetInteger(long chart_id, string name, ENUM_OBJECT_PROPERTY_INTEGER prop_id, int prop_modifier, long &long_var);
int  ObjectFind(long chart_id, string name);
bool ObjectDelete(long chart_id, string name);
int  ObjectsDeleteAll(long chart_id, int sub_window = -1, int type = -1);
int  ObjectsDeleteAll(long chart_id, const string prefix, int sub_window = -1, int object_type = -1);
void ChartRedraw(long chart_id = 0);
datetime iTime(const string symbol, ENUM_TIMEFRAMES timeframe, int shift);
int  iBarShift(const string symbol, ENUM_TIMEFRAMES timeframe, datetime time, bool exact = false);
int  Bars(const string symbol_name, ENUM_TIMEFRAMES timeframe);
int  Bars(const string symbol_name, ENUM_TIMEFRAMES timeframe, datetime start_time, datetime stop_time);
int  CopyRates(const string symbol_name, ENUM_TIMEFRAMES timeframe, int start_pos, int count, DynArr<MqlRates> &rates_array);
int  CopyRates(const string symbol_name, ENUM_TIMEFRAMES timeframe, datetime start_time, int count, DynArr<MqlRates> &rates_array);
int  CopyRates(const string symbol_name, ENUM_TIMEFRAMES timeframe, datetime start_time, datetime stop_time, DynArr<MqlRates> &rates_array);
int  PeriodSeconds(ENUM_TIMEFRAMES period = PERIOD_CURRENT);
template<class E> string EnumToString(E value);
string StringSubstr(string string_value, int start_pos, int length = -1);
int    StringLen(string string_value);
template<class... A> string StringFormat(string format, A... args);
template<class... A> void Print(A... args);
string TimeToString(datetime value, int mode = TIME_DATE | TIME_MINUTES);
string DoubleToString(double value, int digits = 8);
string IntegerToString(long number, int str_len = 0, ushort fill_symbol = ' ');
bool EventSetTimer(int seconds);
void EventKillTimer();
datetime TimeLocal();
double MathFloor(double val);
double MathCeil(double val);
double MathRound(double value);
template<class T> T MathAbs(T value);
template<class A, class B> auto MathMin(A a, B b) -> decltype(a + b);
template<class A, class B> auto MathMax(A a, B b) -> decltype(a + b);
template<class T> int ArrayResize(DynArr<T> &array, int new_size, int reserve_size = 0);
int ArrayInitialize(DynArr<double> &array, double value);
template<class T, int N> int ArraySize(const T (&array)[N]);
template<class T> int ArraySize(const DynArr<T> &array);
