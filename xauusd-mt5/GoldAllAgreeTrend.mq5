//+------------------------------------------------------------------+
//| GoldAllAgreeTrend.mq5                                             |
//| Chart companion to the GoldAllAgree EA. Shows the same signal:    |
//| LONG while EMA(20) > EMA(80) on every enabled timeframe           |
//| (M5, M15, M30, H1, H4, closed bars only), FLAT otherwise.         |
//|  - Ribbon between the chart's EMA20 and EMA80                     |
//|  - EMA20 line: green = LONG, grey = this timeframe up but not all,|
//|    red = this timeframe down                                      |
//|  - Arrows where the EA would buy and where it would exit          |
//|  - Panel with each timeframe's trend and the EMA gap in $         |
//| Best viewed on an M5 chart, where it matches the EA bar for bar.  |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.10"
#property indicator_chart_window
#property indicator_buffers 8
#property indicator_plots   5

#property indicator_label1  "Trend ribbon"
#property indicator_type1   DRAW_FILLING
#property indicator_color1  C'0,70,52',C'80,30,30'

#property indicator_label2  "EMA fast"
#property indicator_type2   DRAW_COLOR_LINE
#property indicator_color2  C'38,194,129',C'128,128,128',C'235,77,75'
#property indicator_width2  2

#property indicator_label3  "EMA slow"
#property indicator_type3   DRAW_LINE
#property indicator_color3  C'150,150,160'
#property indicator_width3  1

#property indicator_label4  "Buy"
#property indicator_type4   DRAW_ARROW
#property indicator_color4  C'38,194,129'
#property indicator_width4  2

#property indicator_label5  "Exit"
#property indicator_type5   DRAW_ARROW
#property indicator_color5  C'255,165,0'
#property indicator_width5  2

//--- inputs
input group "Signal (keep equal to the EA)"
input int    InpFastEMA     = 20;     // Fast EMA period
input int    InpSlowEMA     = 80;     // Slow EMA period
input bool   InpUseM5       = true;   // Require M5 trend up
input bool   InpUseM15      = true;   // Require M15 trend up
input bool   InpUseM30      = true;   // Require M30 trend up
input bool   InpUseH1       = true;   // Require H1 trend up
input bool   InpUseH4       = true;   // Require H4 trend up

input group "Display"
input int    InpHistoryBars = 3000;   // Bars of history to mark
input bool   InpRibbon      = true;   // Shade between the EMAs
input bool   InpArrows      = true;   // Buy / exit arrows
input bool   InpPanel       = true;   // Timeframe panel
input bool   InpPanelRight  = true;   // Panel in the top-right corner (false = top-left)
input bool   InpAlerts      = false;  // Pop-up alert on signal change
input bool   InpPush        = false;  // Phone notification on signal change

//--- buffers
double bRibFast[], bRibSlow[], bFast[], bFastClr[], bSlow[], bBuy[], bExit[], bState[];

//--- state
ENUM_TIMEFRAMES tfs[5] = {PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4};
string   names[5] = {"M5", "M15", "M30", "H1", "H4"};
bool     use[5];
int      hFast[5], hSlow[5];
int      hChartFast = INVALID_HANDLE, hChartSlow = INVALID_HANDLE;
datetime lastBarTime = 0;
int      lastSignal = -1;
datetime signalSince = 0;
string   PFX = "GAAT_";

color clrUp   = C'38,194,129';
color clrDown = C'235,77,75';
color clrNeut = C'128,128,128';

//+------------------------------------------------------------------+
color Blend(color a, color b, double k)   // k of a, (1-k) of b
{
   uint ua = (uint)a, ub = (uint)b;
   uint r  = (uint)MathRound((ua & 0xFF) * k + (ub & 0xFF) * (1 - k));
   uint g  = (uint)MathRound(((ua >> 8) & 0xFF) * k + ((ub >> 8) & 0xFF) * (1 - k));
   uint bl = (uint)MathRound(((ua >> 16) & 0xFF) * k + ((ub >> 16) & 0xFF) * (1 - k));
   return (color)(r | (g << 8) | (bl << 16));
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpFastEMA <= 0 || InpSlowEMA <= InpFastEMA) return INIT_PARAMETERS_INCORRECT;
   use[0] = InpUseM5; use[1] = InpUseM15; use[2] = InpUseM30; use[3] = InpUseH1; use[4] = InpUseH4;

   SetIndexBuffer(0, bRibFast, INDICATOR_DATA);
   SetIndexBuffer(1, bRibSlow, INDICATOR_DATA);
   SetIndexBuffer(2, bFast,    INDICATOR_DATA);
   SetIndexBuffer(3, bFastClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(4, bSlow,    INDICATOR_DATA);
   SetIndexBuffer(5, bBuy,     INDICATOR_DATA);
   SetIndexBuffer(6, bExit,    INDICATOR_DATA);
   SetIndexBuffer(7, bState,   INDICATOR_CALCULATIONS);
   for(int p = 0; p < 5; p++) PlotIndexSetDouble(p, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetInteger(3, PLOT_ARROW, 233);
   PlotIndexSetInteger(4, PLOT_ARROW, 234);
   PlotIndexSetInteger(3, PLOT_ARROW_SHIFT, 12);
   PlotIndexSetInteger(4, PLOT_ARROW_SHIFT, -12);
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, InpRibbon ? DRAW_FILLING : DRAW_NONE);
   PlotIndexSetInteger(3, PLOT_DRAW_TYPE, InpArrows ? DRAW_ARROW : DRAW_NONE);
   PlotIndexSetInteger(4, PLOT_DRAW_TYPE, InpArrows ? DRAW_ARROW : DRAW_NONE);

   //--- soft ribbon colours that suit the chart's background
   color bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, 0, Blend(clrUp,   bg, 0.22));
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, 1, Blend(clrDown, bg, 0.22));

   for(int i = 0; i < 5; i++)
   {
      hFast[i] = INVALID_HANDLE; hSlow[i] = INVALID_HANDLE;
      if(!use[i]) continue;
      hFast[i] = iMA(_Symbol, tfs[i], InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
      hSlow[i] = iMA(_Symbol, tfs[i], InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
      if(hFast[i] == INVALID_HANDLE || hSlow[i] == INVALID_HANDLE) return INIT_FAILED;
   }
   hChartFast = iMA(_Symbol, _Period, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hChartSlow = iMA(_Symbol, _Period, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(hChartFast == INVALID_HANDLE || hChartSlow == INVALID_HANDLE) return INIT_FAILED;

   IndicatorSetString(INDICATOR_SHORTNAME, "GoldAllAgree Trend");
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   for(int i = 0; i < 5; i++)
   {
      if(hFast[i] != INVALID_HANDLE) IndicatorRelease(hFast[i]);
      if(hSlow[i] != INVALID_HANDLE) IndicatorRelease(hSlow[i]);
   }
   if(hChartFast != INVALID_HANDLE) IndicatorRelease(hChartFast);
   if(hChartSlow != INVALID_HANDLE) IndicatorRelease(hChartSlow);
   ObjectsDeleteAll(0, PFX);
}

//+------------------------------------------------------------------+
//| Copy the last `count` values of a handle into dst[rates_total-count..] |
//+------------------------------------------------------------------+
bool CopyTail(int handle, int rates_total, int count, double &dst[])
{
   double tmp[];
   if(CopyBuffer(handle, 0, 0, count, tmp) != count) return false;   // tmp[0] = oldest
   for(int k = 0; k < count; k++) dst[rates_total - count + k] = tmp[k];
   return true;
}

//+------------------------------------------------------------------+
//| For chart bars [start, rates_total-2], set trend[] of timeframe tf |
//| using only that timeframe's bars closed by the chart bar's close. |
//| +1 up, -1 down, 0 unknown.                                        |
//+------------------------------------------------------------------+
bool TrendOnChart(int i, int start, int rates_total, const datetime &time[], int &trend[])
{
   int    P    = PeriodSeconds(tfs[i]);
   int    CP   = PeriodSeconds(_Period);
   datetime from = time[start] - 2 * P;
   int n = iBarShift(_Symbol, tfs[i], from, false) + 1;           // bars from `from` to now
   n = MathMin(n, MathMin(BarsCalculated(hFast[i]), BarsCalculated(hSlow[i])));
   if(n <= 0) return false;
   datetime t[]; double f[], s[];
   if(CopyTime(_Symbol, tfs[i], 0, n, t) != n) return false;      // oldest first
   if(CopyBuffer(hFast[i], 0, 0, n, f) != n) return false;
   if(CopyBuffer(hSlow[i], 0, 0, n, s) != n) return false;
   int j = -1;
   for(int b = start; b < rates_total; b++)
   {
      datetime closeT = time[b] + CP;
      while(j + 1 < n && t[j + 1] + P <= closeT) j++;
      trend[b] = (j < 0) ? 0 : (f[j] > s[j] ? 1 : -1);
   }
   return true;
}

//+------------------------------------------------------------------+
//| Panel layout: offsets are measured from the panel's left edge and |
//| mirrored when the panel sits in the right corner.                 |
//+------------------------------------------------------------------+
const int PX = 12, PY = 22, PW = 200;

int XL(int off) { return InpPanelRight ? PX + PW - off : PX + off; }   // a left edge at `off`

void Label(string name, int off, int y, string text, color c, int size, string font, bool alignRight)
{
   string n = PFX + name;
   if(ObjectFind(0, n) < 0)
   {
      ObjectCreate(0, n, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, n, OBJPROP_CORNER, InpPanelRight ? CORNER_RIGHT_UPPER : CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_ANCHOR, alignRight ? ANCHOR_RIGHT_UPPER : ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, XL(off));
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetString (0, n, OBJPROP_TEXT, text);
   ObjectSetString (0, n, OBJPROP_FONT, font);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, n, OBJPROP_COLOR, c);
}

void Box(string name, int off, int y, int w, int h, color fill, color border)
{
   string n = PFX + name;
   if(ObjectFind(0, n) < 0)
   {
      ObjectCreate(0, n, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, n, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   }
   ObjectSetInteger(0, n, OBJPROP_CORNER, InpPanelRight ? CORNER_RIGHT_UPPER : CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, XL(off));      // top-left point of the box
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, fill);
   ObjectSetInteger(0, n, OBJPROP_COLOR, border);
}

//+------------------------------------------------------------------+
//| Panel: live state of each timeframe (last closed bar) + signal    |
//+------------------------------------------------------------------+
void DrawPanel()
{
   if(!InpPanel) return;
   color bg   = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   color fg   = (color)ChartGetInteger(0, CHART_COLOR_FOREGROUND);
   color pnl  = Blend(fg, bg, 0.07);
   color line = Blend(fg, bg, 0.18);
   color dim  = Blend(fg, bg, 0.55);
   int rows = 0; for(int i = 0; i < 5; i++) if(use[i]) rows++;
   int row = 20;

   Box("bg", 0, PY, PW, 40 + rows * row + 62, pnl, line);
   Label("title", 14, PY + 10, "GOLD  ALL-AGREE TREND", dim, 8, "Segoe UI Semibold", false);

   int yy = PY + 34;
   for(int i = 0; i < 5; i++)
   {
      if(!use[i]) continue;
      double f[1], s[1]; int st = 0;
      if(CopyBuffer(hFast[i], 0, 1, 1, f) == 1 && CopyBuffer(hSlow[i], 0, 1, 1, s) == 1)
         st = f[0] > s[0] ? 1 : -1;
      color c = st > 0 ? clrUp : st < 0 ? clrDown : clrNeut;
      Box("dot" + names[i], 14, yy + 4, 9, 9, c, c);
      Label("tf" + names[i], 32, yy, names[i], fg, 9, "Segoe UI Semibold", false);
      string val = (st == 0) ? "loading" :
                   (st > 0 ? "UP  " : "DOWN  ") + (f[0] - s[0] >= 0 ? "+" : "") + DoubleToString(f[0] - s[0], 2);
      Label("val" + names[i], PW - 14, yy, val, c, 9, "Consolas", true);
      yy += row;
   }

   yy += 6;
   Box("sep", 14, yy, PW - 28, 1, line, line);
   yy += 10;
   string sig = lastSignal == 1 ? "LONG" : lastSignal == 0 ? "FLAT" : "...";
   Label("sig", 14, yy, sig, lastSignal == 1 ? clrUp : fg, 14, "Segoe UI Semibold", false);
   Label("since", 14, yy + 26, signalSince > 0 ? "since " + TimeToString(signalSince, TIME_DATE | TIME_MINUTES) : "",
         dim, 8, "Segoe UI", false);
   Label("hint", PW - 14, yy + 6, "EMA gap $", dim, 8, "Segoe UI", true);
   ChartRedraw();
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   if(rates_total < InpSlowEMA + 2) return 0;
   for(int i = 0; i < 5; i++)
      if(use[i] && (BarsCalculated(hFast[i]) <= 0 || BarsCalculated(hSlow[i]) <= 0)) return 0;
   if(BarsCalculated(hChartFast) < rates_total || BarsCalculated(hChartSlow) < rates_total) return 0;

   int start = MathMax(1, rates_total - InpHistoryBars);
   bool newBar = (time[rates_total - 1] != lastBarTime) || prev_calculated == 0;

   //--- on a new bar, give the higher-timeframe EMAs up to a minute (from the bar's first tick) to include their newest bar
   static datetime seenBar = 0, seenAt = 0;
   if(time[rates_total - 1] != seenBar) { seenBar = time[rates_total - 1]; seenAt = TimeCurrent(); }
   if(newBar && prev_calculated > 0 && TimeCurrent() - seenAt < 60)
      for(int i = 0; i < 5; i++)
         if(use[i] && (BarsCalculated(hFast[i]) < iBars(_Symbol, tfs[i]) || BarsCalculated(hSlow[i]) < iBars(_Symbol, tfs[i])))
            return prev_calculated;   // redo on the next tick (lastBarTime is unchanged, so newBar stays true)

   //--- chart EMAs: whole window on a new bar, last two values otherwise
   int cnt = newBar ? rates_total - start + 1 : 2;
   if(newBar && prev_calculated == 0)
   {
      ArrayInitialize(bRibFast, EMPTY_VALUE); ArrayInitialize(bRibSlow, EMPTY_VALUE);
      ArrayInitialize(bFast, EMPTY_VALUE);    ArrayInitialize(bSlow, EMPTY_VALUE);
      ArrayInitialize(bBuy, EMPTY_VALUE);     ArrayInitialize(bExit, EMPTY_VALUE);
      ArrayInitialize(bState, 0);             ArrayInitialize(bFastClr, 1);
   }
   if(!CopyTail(hChartFast, rates_total, cnt, bFast)) return 0;
   if(!CopyTail(hChartSlow, rates_total, cnt, bSlow)) return 0;
   for(int b = rates_total - cnt; b < rates_total; b++)
   {
      bRibFast[b] = InpRibbon ? bFast[b] : EMPTY_VALUE;
      bRibSlow[b] = InpRibbon ? bSlow[b] : EMPTY_VALUE;
   }

   if(newBar)
   {
      //--- all-agree state for every closed chart bar in the window
      int all[]; ArrayResize(all, rates_total); ArrayInitialize(all, 1);
      int tr[];  ArrayResize(tr, rates_total);
      for(int i = 0; i < 5; i++)
      {
         if(!use[i]) continue;
         ArrayInitialize(tr, 0);
         if(!TrendOnChart(i, start, rates_total, time, tr)) return 0;
         for(int b = start; b < rates_total; b++)
         {
            if(tr[b] == 0) all[b] = -1;
            else if(tr[b] < 0 && all[b] != -1) all[b] = 0;
         }
      }
      all[rates_total - 1] = all[rates_total - 2];          // forming bar keeps the last closed signal

      int prevSig = lastSignal;
      for(int b = start; b < rates_total; b++)
      {
         int st = all[b] < 0 ? 0 : all[b];
         bState[b] = st;
         // colour of the fast line: LONG / chart timeframe up only / down
         bFastClr[b] = (st == 1) ? 0 : (bFast[b] > bSlow[b] ? 1 : 2);
         bBuy[b] = EMPTY_VALUE; bExit[b] = EMPTY_VALUE;
      }
      // the EA acts right after bar b closes, so mark the following bar
      for(int b = start + 1; b < rates_total - 1; b++)
      {
         if(bState[b] == 1 && bState[b - 1] == 0) bBuy[b + 1]  = low[b + 1];
         if(bState[b] == 0 && bState[b - 1] == 1) bExit[b + 1] = high[b + 1];
      }
      //--- when the current signal began
      int cur = (int)bState[rates_total - 2];
      signalSince = 0;
      for(int b = rates_total - 2; b > start; b--)
         if(bState[b - 1] != cur) { signalSince = time[b] + PeriodSeconds(_Period); break; }
      lastSignal = cur;

      if(prevSig >= 0 && prevSig != lastSignal && prev_calculated > 0)
      {
         string msg = _Symbol + " all-agree trend: " + (lastSignal == 1 ? "LONG" : "FLAT");
         if(InpAlerts) Alert(msg);
         if(InpPush) SendNotification(msg);
      }
      lastBarTime = time[rates_total - 1];
   }
   else
   {
      bFastClr[rates_total - 1] = (bState[rates_total - 1] == 1) ? 0 : (bFast[rates_total - 1] > bSlow[rates_total - 1] ? 1 : 2);
   }

   DrawPanel();
   return rates_total;
}
//+------------------------------------------------------------------+
