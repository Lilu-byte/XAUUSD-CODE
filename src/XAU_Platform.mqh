//+------------------------------------------------------------------+
//|                                                XAU_Platform.mqh  |
//|  MetaTrader 5 glue shared by XAU_Oracle (indicator) and          |
//|  XAU_Sniper_EA: data loading, symbol/lot maths, economic news    |
//|  filter and chart-drawing helpers.                               |
//+------------------------------------------------------------------+
#ifndef XAU_PLATFORM_MQH
#define XAU_PLATFORM_MQH

#include "XAU_Core.mqh"

#ifdef __MQL5__
   #define XSARR(name)      string name[]
   #define XRATESARR(name)  MqlRates name[]
   #define XRATESOUT(name)  MqlRates &name[]
   #define XCALARR(name)    MqlCalendarValue name[]
#endif

//+------------------------------------------------------------------+
//| timeframes                                                       |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES XAutoHTF(const ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1:  case PERIOD_M2:  case PERIOD_M3:  case PERIOD_M4:                    return PERIOD_M15;
      case PERIOD_M5:  case PERIOD_M6:  case PERIOD_M10: case PERIOD_M12:                   return PERIOD_H1;
      case PERIOD_M15: case PERIOD_M20:                                                     return PERIOD_H1;
      case PERIOD_M30:                                                                      return PERIOD_H4;
      case PERIOD_H1:  case PERIOD_H2:  case PERIOD_H3:                                     return PERIOD_H4;
      case PERIOD_H4:  case PERIOD_H6:  case PERIOD_H8:  case PERIOD_H12:                   return PERIOD_D1;
      case PERIOD_D1:                                                                       return PERIOD_W1;
      default: break;
   }
   return PERIOD_MN1;
}

string XTfName(const ENUM_TIMEFRAMES tf)
{
   return StringSubstr(EnumToString(tf), 7);
}

//+------------------------------------------------------------------+
//| data                                                             |
//+------------------------------------------------------------------+
enum ENUM_XAU_DST
{
   XAU_DST_FIXED = 0,   // server clock never changes
   XAU_DST_US    = 1,   // server follows US daylight time (typical "New York close" servers: GMT+2 / GMT+3)
   XAU_DST_EU    = 2    // server follows EU daylight time
};

// Server-time minus GMT in WINTER (standard) time, in seconds. With manual = true the value is the one you typed.
// Automatic: measure today's offset and, if the server is currently on summer time, remove the extra hour.
int XWinterOffsetSec(const bool manual, const double manual_hours, const int dst_mode)
{
   if(manual) return (int)MathRound(manual_hours * 3600.0);
   const double d = (double)(TimeTradeServer() - TimeGMT());
   int cur = (int)(MathRound(d / 1800.0) * 1800.0);
   const long g = (long)TimeGMT();
   if(dst_mode == XAU_DST_US && XUsDst(g)) cur -= 3600;
   if(dst_mode == XAU_DST_EU && XEuDst(g)) cur -= 3600;
   return cur;
}

// Loads the most recent `count` bars, oldest first (index count-1 = forming bar).
int XLoadRates(const string sym, const ENUM_TIMEFRAMES tf, const int count, XRATESOUT(out))
{
   ArraySetAsSeries(out, false);
   const int got = CopyRates(sym, tf, 0, count, out);
   return (got > 0) ? got : 0;
}

// Trend direction (+1/-1/0) and ADX on the last CLOSED bar of another timeframe.
int XTrendState(const string sym, const ENUM_TIMEFRAMES tf, double &adx_out)
{
   XRATESARR(r);
   adx_out = 0.0;
   const int got = XLoadRates(sym, tf, 450, r);
   if(got < 260) return 0;
   XDARR(c); XDARR(h); XDARR(l); XDARR(e50); XDARR(e200); XDARR(pdi); XDARR(mdi); XDARR(adx);
   ArrayResize(c, got); ArrayResize(h, got); ArrayResize(l, got);
   ArrayResize(e50, got); ArrayResize(e200, got); ArrayResize(pdi, got); ArrayResize(mdi, got); ArrayResize(adx, got);
   for(int i = 0; i < got; i++) { c[i] = r[i].close; h[i] = r[i].high; l[i] = r[i].low; }
   XCalcEMA(c, e50, got, 50);
   XCalcEMA(c, e200, got, 200);
   XCalcADX(h, l, c, pdi, mdi, adx, got, 14);
   const int k = got - 2;
   adx_out = adx[k];
   if(e50[k] > e200[k] && c[k] > e50[k]) return 1;
   if(e50[k] < e200[k] && c[k] < e50[k]) return -1;
   return 0;
}

// DXY-like symbol (gold moves against it) or EURUSD fallback (gold moves with it).
string XResolveInterSymbol(const string user_symbol, bool &invert)
{
   invert = false;
   if(StringLen(user_symbol) > 0)
   {
      invert = (StringFind(user_symbol, "EUR") < 0 && StringFind(user_symbol, "GBP") < 0 && StringFind(user_symbol, "AUD") < 0);
      if(SymbolSelect(user_symbol, true)) return user_symbol;
      return "";
   }
   string cand[5];
   cand[0] = "USDX"; cand[1] = "DXY"; cand[2] = "DX"; cand[3] = "USDIDX"; cand[4] = "DXY.cash";
   for(int i = 0; i < 5; i++)
      if(SymbolSelect(cand[i], true)) { invert = true; return cand[i]; }
   if(SymbolSelect("EURUSD", true)) { invert = false; return "EURUSD"; }
   return "";
}

//+------------------------------------------------------------------+
//| lot sizing                                                       |
//+------------------------------------------------------------------+
struct XLotPlan
{
   bool   ok;
   double lots;
   double risk_money;        // money lost if the stop is hit at `lots`
   double risk_pct;          // of the supplied equity
   double margin;
   double min_lot_risk_pct;  // what the smallest tradable lot would risk
   string note;
};

double XTickValueLoss(const string sym)
{
   double v = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(v <= 0.0) v = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   return v;
}

// Sizes a trade so that hitting the stop costs `risk_pct` of equity. Never rounds UP past
// the requested risk; if even the minimum lot risks more than overrun_factor x the request,
// the trade is refused (ok=false) instead of silently over-risking a small account.
void XPlanLots(const string sym, const double equity, const double risk_pct, const double sl_dist,
               const bool is_buy, const double price, const double overrun_factor,
               const double lot_cap, const double free_margin, const double margin_use_frac,
               XLotPlan &p)
{
   p.ok = false; p.lots = 0.0; p.risk_money = 0.0; p.risk_pct = 0.0; p.margin = 0.0;
   p.min_lot_risk_pct = 0.0; p.note = "";
   const double tick_size = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   const double tick_val  = XTickValueLoss(sym);
   const double vmin  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   const double vmax  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   const double vstep = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(equity <= 0.0 || sl_dist <= 0.0 || tick_size <= 0.0 || tick_val <= 0.0 || vstep <= 0.0)
   {
      p.note = "symbol data unavailable";
      return;
   }
   const double risk_money = equity * risk_pct / 100.0;
   const double loss_per_lot = (sl_dist / tick_size) * tick_val;
   double lots = XNormLotsDown(XRawLots(risk_money, sl_dist, tick_size, tick_val), vmin, vmax, vstep);
   p.min_lot_risk_pct = 100.0 * vmin * loss_per_lot / equity;
   if(lots <= 0.0)
   {
      if(vmin * loss_per_lot <= risk_money * overrun_factor) lots = vmin;
      else
      {
         p.note = "account too small: min lot would risk " + DoubleToString(p.min_lot_risk_pct, 1) + "%";
         return;
      }
   }
   if(lot_cap > 0.0 && lots > lot_cap) lots = XNormLotsDown(lot_cap, vmin, vmax, vstep);
   if(lots <= 0.0) { p.note = "lot cap below minimum lot"; return; }

   double margin = 0.0;
   const ENUM_ORDER_TYPE ot = is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(OrderCalcMargin(ot, sym, lots, price, margin) && margin > 0.0 && free_margin > 0.0)
   {
      const double allowed = free_margin * margin_use_frac;
      if(margin > allowed)
      {
         const double lots_before = lots;
         lots = XNormLotsDown(lots * allowed / margin, vmin, vmax, vstep);
         if(lots <= 0.0) { p.note = "not enough free margin"; return; }
         double margin2 = 0.0;
         if(OrderCalcMargin(ot, sym, lots, price, margin2) && margin2 > 0.0) margin = margin2;
         else margin = margin * lots / lots_before;   // recalculation failed: scale the earlier figure proportionally
      }
   }
   p.lots = lots;
   p.margin = margin;
   p.risk_money = lots * loss_per_lot;
   p.risk_pct = 100.0 * p.risk_money / equity;
   p.ok = true;
}

//+------------------------------------------------------------------+
//| economic calendar filter                                         |
//+------------------------------------------------------------------+
class CXauNews
{
private:
   XTARR(m_t);
   XSARR(m_name);
   XIARR(m_imp);
   int      m_n;
   datetime m_last;
   bool     m_cal_ok;
public:
   int    before_min;
   int    after_min;
   int    min_importance;    // 1 low, 2 medium, 3 high
   bool   fallback_static;   // when the calendar is unavailable (e.g. Strategy Tester)
   int    gmt_offset_sec;
   string currency;

   CXauNews()
   {
      m_n = 0; m_last = 0; m_cal_ok = false;
      before_min = 30; after_min = 30; min_importance = 3;
      fallback_static = true; gmt_offset_sec = 0; currency = "USD";
   }
   bool CalendarAvailable() const { return m_cal_ok; }

   void Refresh(const datetime now)
   {
      if(m_last != 0 && now - m_last < 900 && now >= m_last) return;
      m_last = now;
      m_n = 0;
      m_cal_ok = false;
      XCALARR(vals);
      ResetLastError();
      if(!CalendarValueHistory(vals, now - 3 * 3600, now + 3 * 86400, NULL, currency)) return;
      const int got = ArraySize(vals);
      if(got <= 0) return;
      m_cal_ok = true;
      ArrayResize(m_t, got); ArrayResize(m_name, got); ArrayResize(m_imp, got);
      for(int i = 0; i < got; i++)
      {
         MqlCalendarEvent ev;
         if(!CalendarEventById(vals[i].event_id, ev)) continue;
         const int imp = (int)ev.importance;
         if(imp < min_importance) continue;
         m_t[m_n] = vals[i].time;
         m_name[m_n] = ev.name;
         m_imp[m_n] = imp;
         m_n++;
      }
   }

   // true when trading should pause; `why` explains
   bool Blocked(const datetime now, string &why) const
   {
      why = "";
      for(int i = 0; i < m_n; i++)
      {
         if(now >= m_t[i] - before_min * 60 && now <= m_t[i] + after_min * 60)
         {
            why = m_name[i] + " " + TimeToString(m_t[i], TIME_MINUTES);
            return true;
         }
      }
      if(!m_cal_ok && fallback_static)
      {
         // US data prints at 08:30 ET = 12:30 or 13:30 GMT. Without a calendar, stay out of both.
         const double hr = XHourGmt(now, gmt_offset_sec);
         const int wd = XWeekdayGmt(now, gmt_offset_sec);
         if(wd >= 1 && wd <= 5)
         {
            if((hr >= 12.25 && hr <= 12.75) || (hr >= 13.25 && hr <= 13.75))
            {
               why = "US data window (static)";
               return true;
            }
         }
      }
      return false;
   }

   // e.g. "NFP in 42m" for the panel; empty when nothing is near
   string NextText(const datetime now) const
   {
      datetime best = 0; int bi = -1;
      for(int i = 0; i < m_n; i++)
         if(m_t[i] >= now - after_min * 60 && (bi < 0 || m_t[i] < best)) { best = m_t[i]; bi = i; }
      if(bi < 0) return m_cal_ok ? "no high-impact USD news soon" : "calendar unavailable";
      const long mins = ((long)best - (long)now) / 60;
      string nm = m_name[bi];
      if(StringLen(nm) > 22) nm = StringSubstr(nm, 0, 22);
      if(mins >= 0) return nm + " in " + IntegerToString(mins) + "m";
      return nm + " " + IntegerToString(-mins) + "m ago";
   }
};

//+------------------------------------------------------------------+
//| drawing helpers                                                  |
//+------------------------------------------------------------------+
color XRGB(const int r, const int g, const int b)
{
   return (color)((b << 16) | (g << 8) | r);
}

void XObjLabel(const string name, const int x, const int y, const string text, const color clr,
               const int fsize, const string font, const ENUM_BASE_CORNER corner)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetString(0, name, OBJPROP_FONT, font);
   }
   ObjectSetInteger(0, name, OBJPROP_CORNER, corner);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fsize);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
}

void XObjRectLabel(const string name, const int x, const int y, const int w, const int h,
                   const color bg, const color border, const ENUM_BASE_CORNER corner)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   }
   ObjectSetInteger(0, name, OBJPROP_CORNER, corner);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, name, OBJPROP_COLOR, border);
}

void XObjTrend(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
               const color clr, const ENUM_LINE_STYLE style, const int width, const bool ray_right)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
   }
   else
   {
      ObjectMove(0, name, 0, t1, p1);
      ObjectMove(0, name, 1, t2, p2);
   }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, ray_right);
}

void XObjRect(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
              const color clr, const bool fill)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
   }
   else
   {
      ObjectMove(0, name, 0, t1, p1);
      ObjectMove(0, name, 1, t2, p2);
   }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FILL, fill);
}

void XObjText(const string name, const datetime t, const double p, const string text, const color clr, const int fsize)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
   }
   else ObjectMove(0, name, 0, t, p);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fsize);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
}

void XObjVLine(const string name, const datetime t, const color clr)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_VLINE, 0, t, 0.0);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
   }
   else ObjectMove(0, name, 0, t, 0.0);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
}

void XObjDelete(const string name)
{
   if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
}

#endif // XAU_PLATFORM_MQH
