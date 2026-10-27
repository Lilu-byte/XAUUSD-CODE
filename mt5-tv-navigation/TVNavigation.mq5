//+------------------------------------------------------------------+
//|                                                 TVNavigation.mq5 |
//| TradingView-style mouse navigation for MT5 charts.               |
//| A chart tool only: it draws no lines and never places orders.    |
//+------------------------------------------------------------------+
#property copyright   "FIS Agent project"
#property version     "1.00"
#property description "TradingView-style navigation: wheel zooms at the cursor, Shift+wheel scrolls,"
#property description "Ctrl+wheel zooms the price axis, dragging up/down pans the price axis,"
#property description "double-click the price axis, click A or press R to go back to auto scale."
#property indicator_chart_window
#property indicator_plots 0

input bool   InpWheelZoom      = true;   // Wheel zooms at the cursor (Shift+wheel scrolls)
input bool   InpCtrlWheelPrice = true;   // Ctrl+wheel zooms the price axis at the cursor
input bool   InpVerticalPan    = true;   // Drag up/down pans the price axis
input int    InpPanDeadZone    = 6;      // Pixels of up/down movement before vertical panning starts
input double InpPriceZoomStep  = 0.15;   // Price zoom per wheel notch (0.15 = 15%)
input int    InpScrollBars     = 0;      // Bars per Shift+wheel notch (0 = 10% of the screen)
input bool   InpRightMargin    = true;   // Leave empty space right of the last bar
input int    InpRightMarginPct = 20;     // Right margin, % of chart width (10-50, MT5 limit)
input bool   InpFollowLive     = true;   // Follow new bars only while the last bar is on screen
input bool   InpButtons        = true;   // Show "A" (auto scale) and ">>" (latest bar) buttons
input bool   InpResetKey       = true;   // Key R: auto scale + jump to the latest bar

#define BTN_AUTO  "TVNav_Auto"
#define BTN_LIVE  "TVNav_Live"
#define BTN_W     26
#define BTN_H     18
#define WHEEL_QUIET_MS 250   // after a wheel notch, ignore MT5's own scroll for this long

long   g_chart = 0;
int    g_total = 0;          // bars on the chart (from OnCalculate)

// settings to restore when the tool is removed
bool   g_origAutoscroll = true;
bool   g_origShift      = false;
double g_origShiftSize  = 10.0;

// the time view this tool last saw or set
int    g_vScale = 2, g_vFirst = 0, g_vWidth = 1;
uint   g_lastWheelMs = 0;

// left-button drag state
bool   g_down = false, g_panning = false, g_skipDrag = true;
int    g_downX = 0, g_downY = 0;
double g_downMax = 0, g_downMin = 0, g_ppp = 0;   // price range and price per pixel at the press

// double-click on the price axis
uint   g_lastClickMs = 0;
int    g_lastClickX = -100, g_lastClickY = -100;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_chart = ChartID();
   g_total = Bars(_Symbol, _Period);
   g_origAutoscroll = (bool)ChartGetInteger(g_chart, CHART_AUTOSCROLL);
   g_origShift      = (bool)ChartGetInteger(g_chart, CHART_SHIFT);
   g_origShiftSize  = ChartGetDouble(g_chart, CHART_SHIFT_SIZE);

   ChartSetInteger(g_chart, CHART_EVENT_MOUSE_MOVE, true);
   ChartSetInteger(g_chart, CHART_EVENT_MOUSE_WHEEL, true);
   ChartSetInteger(g_chart, CHART_MOUSE_SCROLL, true);
   if(InpRightMargin)
     {
      ChartSetInteger(g_chart, CHART_SHIFT, true);
      ChartSetDouble(g_chart, CHART_SHIFT_SIZE, (double)MathMax(10, MathMin(50, InpRightMarginPct)));
     }
   if(InpButtons)
     {
      MakeButton(BTN_AUTO, "A", "Auto scale (fit prices to the screen)");
      MakeButton(BTN_LIVE, ">>", "Jump to the latest bar");
     }
   CacheView();
   UpdateFollow();
   PlaceButtons();
   UpdateButtons();
   ChartRedraw(g_chart);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectDelete(g_chart, BTN_AUTO);
   ObjectDelete(g_chart, BTN_LIVE);
   ChartSetInteger(g_chart, CHART_AUTOSCROLL, g_origAutoscroll);
   ChartSetInteger(g_chart, CHART_SHIFT, g_origShift);
   ChartSetDouble(g_chart, CHART_SHIFT_SIZE, g_origShiftSize);
   ChartRedraw(g_chart);
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   g_total = rates_total;
   return(rates_total);
  }

//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id == CHARTEVENT_MOUSE_MOVE)
     {
      OnMouse((int)lparam, (int)dparam, (uint)StringToInteger(sparam));
      return;
     }
   if(id == CHARTEVENT_MOUSE_WHEEL)
     {
      int flags = (int)(lparam >> 32);           // 4 = Shift, 8 = Ctrl
      int x     = (int)(short)lparam;
      int y     = (int)(short)(lparam >> 16);
      OnWheel(x, y, flags, (int)dparam);
      return;
     }
   if(id == CHARTEVENT_CHART_CHANGE)
     {
      if(GetTickCount() - g_lastWheelMs > WHEEL_QUIET_MS)
        {
         CacheView();
         UpdateFollow();
        }
      PlaceButtons();
      UpdateButtons();
      return;
     }
   if(id == CHARTEVENT_OBJECT_CLICK)
     {
      if(sparam == BTN_AUTO)
        {
         if((bool)ChartGetInteger(g_chart, CHART_SCALEFIX))
            AutoScale();
         else
            SetFixed(ChartGetDouble(g_chart, CHART_PRICE_MAX, 0), ChartGetDouble(g_chart, CHART_PRICE_MIN, 0));
         ObjectSetInteger(g_chart, BTN_AUTO, OBJPROP_STATE, false);
        }
      else if(sparam == BTN_LIVE)
        {
         GoLive();
         ObjectSetInteger(g_chart, BTN_LIVE, OBJPROP_STATE, false);
        }
      else
         return;
      UpdateButtons();
      ChartRedraw(g_chart);
      return;
     }
   if(id == CHARTEVENT_KEYDOWN && InpResetKey && lparam == 'R')
     {
      AutoScale();
      GoLive();
      UpdateButtons();
      ChartRedraw(g_chart);
     }
  }

//+------------------------------------------------------------------+
//| Mouse wheel: zoom, scroll or price zoom                          |
//+------------------------------------------------------------------+
void OnWheel(int x, int y, int flags, int delta)
  {
   int steps = delta / 120;
   if(steps == 0)
      steps = (delta > 0) ? 1 : ((delta < 0) ? -1 : 0);
   if(steps == 0)
      return;
   bool ctrl  = (flags & 8) != 0;
   bool shift = (flags & 4) != 0;

   if(ctrl)
     {
      if(!InpCtrlWheelPrice)
         return;
      ApplyTimeView(g_vScale, g_vFirst);        // undo whatever MT5 did with the notch
      PriceZoom(y, steps);
     }
   else
     {
      if(!InpWheelZoom)
         return;                                 // MT5's own wheel scrolling
      if(shift)
         ScrollBars(steps);
      else
         Zoom(x, steps);
     }
   g_lastWheelMs = GetTickCount();
   UpdateButtons();
   ChartRedraw(g_chart);
  }

//+------------------------------------------------------------------+
//| Zoom in/out keeping the bar under the cursor in place            |
//| (or keeping the latest bar in view when it is on screen)         |
//+------------------------------------------------------------------+
void Zoom(int x, int steps)
  {
   int newScale = (int)MathMax(0, MathMin(5, g_vScale + steps));
   if(newScale == g_vScale)
     {
      ApplyTimeView(g_vScale, g_vFirst);         // at the zoom limit: just undo MT5's scroll
      return;
     }
   int wpx = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_PIXELS);
   if(wpx <= 0)
      return;
   if(IsLive(g_vFirst, g_vWidth))
     {
      ApplyTimeView(newScale, 0);                // stays pinned to the latest bar
      return;
     }
   double spOld = (double)wpx / MathMax(1, g_vWidth);
   int cursorBar = g_vFirst - (int)(x / spOld);
   ChartSetInteger(g_chart, CHART_SCALE, newScale);
   int newWidth = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_BARS);
   double spNew = (double)wpx / MathMax(1, newWidth);
   ApplyTimeView(newScale, cursorBar + (int)(x / spNew));
  }

//+------------------------------------------------------------------+
//| Shift+wheel: scroll through time (wheel up = back in time)       |
//+------------------------------------------------------------------+
void ScrollBars(int steps)
  {
   int step = (InpScrollBars > 0) ? InpScrollBars : MathMax(1, g_vWidth / 10);
   ApplyTimeView(g_vScale, g_vFirst + steps * step);
  }

//+------------------------------------------------------------------+
//| Ctrl+wheel: zoom the price axis around the cursor price          |
//+------------------------------------------------------------------+
void PriceZoom(int y, int steps)
  {
   int h = (int)ChartGetInteger(g_chart, CHART_HEIGHT_IN_PIXELS, 0);
   if(h <= 0 || y < 0 || y > h)
      return;                                    // only over the price chart, not sub-windows
   double mx = ChartGetDouble(g_chart, CHART_PRICE_MAX, 0);
   double mn = ChartGetDouble(g_chart, CHART_PRICE_MIN, 0);
   if(mx <= mn)
      return;
   double p = mx - (mx - mn) * y / h;
   double zs = MathMax(0.01, MathMin(0.9, InpPriceZoomStep));
   double f = MathPow(1.0 - zs, steps);         // wheel up = zoom in = smaller range
   SetFixed(p + (mx - p) * f, p - (p - mn) * f);
  }

//+------------------------------------------------------------------+
//| Set the time view: scale and leftmost visible bar                |
//+------------------------------------------------------------------+
void ApplyTimeView(int scale, int first)
  {
   if((int)ChartGetInteger(g_chart, CHART_SCALE) != scale)
      ChartSetInteger(g_chart, CHART_SCALE, scale);
   int width = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_BARS);
   if(g_total > 0 && first > g_total - 1)
      first = g_total - 1;
   if(IsLive(first, width))
     {
      ChartNavigate(g_chart, CHART_END, 0);
      if(InpFollowLive && !(bool)ChartGetInteger(g_chart, CHART_AUTOSCROLL))
         ChartSetInteger(g_chart, CHART_AUTOSCROLL, true);
     }
   else
     {
      if((bool)ChartGetInteger(g_chart, CHART_AUTOSCROLL))
         ChartSetInteger(g_chart, CHART_AUTOSCROLL, false);
      for(int i = 0; i < 3; i++)
        {
         int now = (int)ChartGetInteger(g_chart, CHART_FIRST_VISIBLE_BAR);
         if(now == first)
            break;
         ChartNavigate(g_chart, CHART_CURRENT_POS, now - first);   // + = towards the latest bar
        }
     }
   CacheView();
  }

//+------------------------------------------------------------------+
//| Left-button drag: vertical panning while the price axis is auto  |
//| (once the axis is fixed, MT5 pans both ways by itself)           |
//+------------------------------------------------------------------+
void OnMouse(int x, int y, uint flags)
  {
   bool left = (flags & 1) != 0;
   uint now  = GetTickCount();

   if(left && !g_down)                            // button pressed
     {
      g_down = true;
      g_panning = false;
      g_downX = x;
      g_downY = y;
      g_skipDrag = !InpVerticalPan || !InPriceArea(x, y) || OverButtons(x, y)
                   || (bool)ChartGetInteger(g_chart, CHART_SCALEFIX)
                   || AnyObjectSelected() || NearTradeLevel(y);
      if(!g_skipDrag)
        {
         int h = (int)ChartGetInteger(g_chart, CHART_HEIGHT_IN_PIXELS, 0);
         g_downMax = ChartGetDouble(g_chart, CHART_PRICE_MAX, 0);
         g_downMin = ChartGetDouble(g_chart, CHART_PRICE_MIN, 0);
         g_ppp = (h > 0) ? (g_downMax - g_downMin) / h : 0;
         if(g_ppp <= 0)
            g_skipDrag = true;
        }
     }
   else if(left && g_down)                        // dragging
     {
      if(!g_skipDrag)
        {
         int dy = y - g_downY;
         if(!g_panning && MathAbs(dy) >= MathMax(1, InpPanDeadZone))
            g_panning = true;
         if(g_panning)
           {
            double s = dy * g_ppp;                // drag down = candles move down
            SetFixed(g_downMax + s, g_downMin + s);
            ChartRedraw(g_chart);
           }
        }
     }
   else if(!left && g_down)                       // button released
     {
      g_down = false;
      bool click = !g_panning && MathAbs(x - g_downX) <= 3 && MathAbs(y - g_downY) <= 3;
      g_panning = false;
      if(click)
         CheckPriceAxisDoubleClick(x, y, now);
      UpdateFollow();
      UpdateButtons();
     }

   if(now - g_lastWheelMs > WHEEL_QUIET_MS)
      CacheView();
  }

//+------------------------------------------------------------------+
void CheckPriceAxisDoubleClick(int x, int y, uint now)
  {
   int wpx = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_PIXELS);
   int h   = (int)ChartGetInteger(g_chart, CHART_HEIGHT_IN_PIXELS, 0);
   if(x < wpx || y < 0 || y > h)
      return;                                    // not on the price axis
   if(now - g_lastClickMs < 450 && MathAbs(x - g_lastClickX) < 6 && MathAbs(y - g_lastClickY) < 6)
     {
      AutoScale();
      g_lastClickMs = 0;
      ChartRedraw(g_chart);
      return;
     }
   g_lastClickMs = now;
   g_lastClickX = x;
   g_lastClickY = y;
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
bool IsLive(int first, int width)
  {
   return(first - width + 1 <= 0);               // rightmost slot is at or past the latest bar
  }

void CacheView()
  {
   g_vScale = (int)ChartGetInteger(g_chart, CHART_SCALE);
   g_vFirst = (int)ChartGetInteger(g_chart, CHART_FIRST_VISIBLE_BAR);
   g_vWidth = MathMax(1, (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_BARS));
  }

void UpdateFollow()
  {
   if(!InpFollowLive)
      return;
   int first = (int)ChartGetInteger(g_chart, CHART_FIRST_VISIBLE_BAR);
   int width = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_BARS);
   bool live = IsLive(first, width);
   if((bool)ChartGetInteger(g_chart, CHART_AUTOSCROLL) != live)
      ChartSetInteger(g_chart, CHART_AUTOSCROLL, live);
  }

void SetFixed(double mx, double mn)
  {
   if(mx <= mn)
      return;
   // set the bounds in an order that never makes min > max
   if(mn >= ChartGetDouble(g_chart, CHART_FIXED_MAX))
     {
      ChartSetDouble(g_chart, CHART_FIXED_MAX, mx);
      ChartSetDouble(g_chart, CHART_FIXED_MIN, mn);
     }
   else
     {
      ChartSetDouble(g_chart, CHART_FIXED_MIN, mn);
      ChartSetDouble(g_chart, CHART_FIXED_MAX, mx);
     }
   if(!(bool)ChartGetInteger(g_chart, CHART_SCALEFIX))
     {
      ChartSetInteger(g_chart, CHART_SCALEFIX, true);
      UpdateButtons();
     }
  }

void AutoScale()
  {
   ChartSetInteger(g_chart, CHART_SCALEFIX, false);
   UpdateButtons();
  }

void GoLive()
  {
   ChartNavigate(g_chart, CHART_END, 0);
   if(InpFollowLive)
      ChartSetInteger(g_chart, CHART_AUTOSCROLL, true);
   CacheView();
  }

bool InPriceArea(int x, int y)
  {
   int wpx = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_PIXELS);
   int h   = (int)ChartGetInteger(g_chart, CHART_HEIGHT_IN_PIXELS, 0);
   return(x >= 0 && x < wpx && y >= 0 && y < h);
  }

bool AnyObjectSelected()
  {
   int n = ObjectsTotal(g_chart, -1, -1);
   for(int i = 0; i < n; i++)
     {
      string name = ObjectName(g_chart, i, -1, -1);
      if((bool)ObjectGetInteger(g_chart, name, OBJPROP_SELECTED))
         return(true);
     }
   return(false);
  }

// true when the press is within 6 px of a position or order line (entry, SL, TP),
// so dragging a stop or target never pans the chart
bool NearTradeLevel(int y)
  {
   if(!(bool)ChartGetInteger(g_chart, CHART_SHOW_TRADE_LEVELS))
      return(false);
   int h = (int)ChartGetInteger(g_chart, CHART_HEIGHT_IN_PIXELS, 0);
   double mx = ChartGetDouble(g_chart, CHART_PRICE_MAX, 0);
   double mn = ChartGetDouble(g_chart, CHART_PRICE_MIN, 0);
   if(h <= 0 || mx <= mn)
      return(false);
   double lv[3];
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetSymbol(i) != _Symbol)
         continue;
      lv[0] = PositionGetDouble(POSITION_PRICE_OPEN);
      lv[1] = PositionGetDouble(POSITION_SL);
      lv[2] = PositionGetDouble(POSITION_TP);
      if(NearAny(lv, y, h, mx, mn))
         return(true);
     }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      lv[0] = OrderGetDouble(ORDER_PRICE_OPEN);
      lv[1] = OrderGetDouble(ORDER_SL);
      lv[2] = OrderGetDouble(ORDER_TP);
      if(NearAny(lv, y, h, mx, mn))
         return(true);
     }
   return(false);
  }

bool NearAny(const double &lv[], int y, int h, double mx, double mn)
  {
   for(int k = 0; k < 3; k++)
     {
      if(lv[k] <= 0)
         continue;
      double ly = (mx - lv[k]) / (mx - mn) * h;
      if(MathAbs(ly - y) <= 6)
         return(true);
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Buttons, bottom-right of the price chart (like TradingView's A)  |
//+------------------------------------------------------------------+
void MakeButton(string name, string text, string tip)
  {
   if(ObjectFind(g_chart, name) < 0)
      ObjectCreate(g_chart, name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(g_chart, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(g_chart, name, OBJPROP_XSIZE, BTN_W);
   ObjectSetInteger(g_chart, name, OBJPROP_YSIZE, BTN_H);
   ObjectSetInteger(g_chart, name, OBJPROP_FONTSIZE, 8);
   ObjectSetString(g_chart, name, OBJPROP_FONT, "Arial Bold");
   ObjectSetString(g_chart, name, OBJPROP_TEXT, text);
   ObjectSetString(g_chart, name, OBJPROP_TOOLTIP, tip);
   ObjectSetInteger(g_chart, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(g_chart, name, OBJPROP_HIDDEN, true);
   ObjectSetInteger(g_chart, name, OBJPROP_BACK, false);
   ObjectSetInteger(g_chart, name, OBJPROP_ZORDER, 10);
   ObjectSetInteger(g_chart, name, OBJPROP_STATE, false);
  }

void PlaceButtons()
  {
   if(!InpButtons)
      return;
   int wpx = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_PIXELS);
   int h   = (int)ChartGetInteger(g_chart, CHART_HEIGHT_IN_PIXELS, 0);
   int y   = MathMax(0, h - BTN_H - 6);
   ObjectSetInteger(g_chart, BTN_AUTO, OBJPROP_XDISTANCE, MathMax(0, wpx - BTN_W - 4));
   ObjectSetInteger(g_chart, BTN_AUTO, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(g_chart, BTN_LIVE, OBJPROP_XDISTANCE, MathMax(0, wpx - 2 * BTN_W - 8));
   ObjectSetInteger(g_chart, BTN_LIVE, OBJPROP_YDISTANCE, y);
  }

bool OverButtons(int x, int y)
  {
   if(!InpButtons)
      return(false);
   int wpx = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_PIXELS);
   int h   = (int)ChartGetInteger(g_chart, CHART_HEIGHT_IN_PIXELS, 0);
   return(x >= wpx - 2 * BTN_W - 8 && y >= h - BTN_H - 6);
  }

void UpdateButtons()
  {
   if(!InpButtons)
      return;
   bool autoOn = !(bool)ChartGetInteger(g_chart, CHART_SCALEFIX);
   ObjectSetInteger(g_chart, BTN_AUTO, OBJPROP_BGCOLOR, autoOn ? clrDodgerBlue : C'70,70,70');
   ObjectSetInteger(g_chart, BTN_AUTO, OBJPROP_COLOR, autoOn ? clrWhite : clrSilver);
   int first = (int)ChartGetInteger(g_chart, CHART_FIRST_VISIBLE_BAR);
   int width = (int)ChartGetInteger(g_chart, CHART_WIDTH_IN_BARS);
   bool live = IsLive(first, width);
   ObjectSetInteger(g_chart, BTN_LIVE, OBJPROP_BGCOLOR, live ? C'70,70,70' : clrDodgerBlue);
   ObjectSetInteger(g_chart, BTN_LIVE, OBJPROP_COLOR, live ? clrSilver : clrWhite);
  }
//+------------------------------------------------------------------+
