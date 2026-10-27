//+------------------------------------------------------------------+
//| GoldCandlePatternsInd.mq5                                         |
//| Marks the 16 classic candlestick patterns used by                 |
//| GoldCandlePatterns.mq5, with exactly the same definitions.        |
//| Arrow below the candle = bullish pattern, above = bearish.        |
//| Bright colour = the H1 trend agrees (the EA would trade it with   |
//| the trend filter on); grey = against the H1 trend (skipped).      |
//| Short label under/over the arrow names the pattern. Top-left      |
//| panel shows the last pattern and the H1 trend.                    |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots   2
#property indicator_label1  "Bullish pattern"
#property indicator_type1   DRAW_COLOR_ARROW
#property indicator_color1  clrLimeGreen, clrDarkGray
#property indicator_width1  2
#property indicator_label2  "Bearish pattern"
#property indicator_type2   DRAW_COLOR_ARROW
#property indicator_color2  clrTomato, clrDarkGray
#property indicator_width2  2

input bool   InpShowLabels   = true;    // Show pattern name labels
input int    InpLabelBars    = 300;     // Labels only on the most recent N bars
input bool   InpShowPanel    = true;    // Show the info panel
input bool   InpAlerts       = false;   // Alert when a pattern with the trend completes
input double InpOffsetUSD    = 0.0;     // Arrow distance from the candle ($, 0 = auto)

double BuyBuf[], BuyClr[], SellBuf[], SellClr[];
int    hFast = INVALID_HANDLE, hSlow = INVALID_HANDLE;
bool   enabled[];
datetime lastAlert = 0;
string PFX = "GCPI_";

//+------------------------------------------------------------------+
//| Pattern detection (same definitions as the Python backtest).     |
//| r[] is series-ordered (r[0] = forming bar). i = bar to test.     |
//| Needs r[i .. i+20]. Returns +1 bullish, -1 bearish, 0 none.       |
//+------------------------------------------------------------------+
#define NPAT 16
string PatName[NPAT] = {"Hammer", "Hanging man", "Inverted hammer", "Shooting star",
                        "Bullish engulfing", "Bearish engulfing", "Bullish harami", "Bearish harami",
                        "Piercing line", "Dark cloud cover", "Morning star", "Evening star",
                        "Three white soldiers", "Three black crows", "Doji after fall", "Doji after rise"};
string PatShort[NPAT] = {"H", "HM", "IH", "SS", "BE+", "BE-", "HR+", "HR-", "PL", "DC", "MS", "ES", "3WS", "3BC", "D+", "D-"};
int    PatDir[NPAT]   = {1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1};

double PBody(const MqlRates &r[], int k)  { return MathAbs(r[k].close - r[k].open); }
double PUp(const MqlRates &r[], int k)    { return r[k].high - MathMax(r[k].open, r[k].close); }
double PLo(const MqlRates &r[], int k)    { return MathMin(r[k].open, r[k].close) - r[k].low; }
bool   PBull(const MqlRates &r[], int k)  { return r[k].close > r[k].open; }
bool   PBear(const MqlRates &r[], int k)  { return r[k].close < r[k].open; }

// Fills hit[NPAT] with true for each pattern completed at bar i
void DetectPatterns(const MqlRates &r[], int i, bool &hit[])
{
   for(int p = 0; p < NPAT; p++) hit[p] = false;
   double avg = 0;
   for(int k = 1; k <= 20; k++) avg += PBody(r, i + k);
   avg /= 20.0;
   double body = PBody(r, i), rng = r[i].high - r[i].low, up = PUp(r, i), lo = PLo(r, i);
   if(rng <= 0) return;
   double c = r[i].close, o = r[i].open, c1 = r[i+1].close, o1 = r[i+1].open, b1 = PBody(r, i+1);
   double c2 = r[i+2].close, o2 = r[i+2].open, b2 = PBody(r, i+2);
   bool down = r[i+1].close < r[i+6].close, upt = r[i+1].close > r[i+6].close;
   bool long1 = b1 > avg, long2 = b2 > avg;

   bool hammerShape = lo >= 2 * body && up <= 0.5 * body + 0.05 * rng && body <= 0.35 * rng;
   bool invShape    = up >= 2 * body && lo <= 0.5 * body + 0.05 * rng && body <= 0.35 * rng;
   hit[0] = hammerShape && down;
   hit[1] = hammerShape && upt;
   hit[2] = invShape && down;
   hit[3] = invShape && upt;
   hit[4] = PBear(r, i+1) && PBull(r, i) && o <= c1 && c >= o1 && body > b1 && down;
   hit[5] = PBull(r, i+1) && PBear(r, i) && o >= c1 && c <= o1 && body > b1 && upt;
   hit[6] = PBear(r, i+1) && long1 && PBull(r, i) && o >= c1 && c <= o1 && body < 0.5 * b1 && down;
   hit[7] = PBull(r, i+1) && long1 && PBear(r, i) && o <= c1 && c >= o1 && body < 0.5 * b1 && upt;
   hit[8] = PBear(r, i+1) && long1 && PBull(r, i) && o <= c1 && c > (o1 + c1) / 2 && c < o1 && down;
   hit[9] = PBull(r, i+1) && long1 && PBear(r, i) && o >= c1 && c < (o1 + c1) / 2 && c > o1 && upt;
   bool star = PBody(r, i+1) <= 0.3 * b2;
   hit[10] = PBear(r, i+2) && long2 && star && PBull(r, i) && c > (o2 + c2) / 2 && r[i+3].close < r[i+8].close;
   hit[11] = PBull(r, i+2) && long2 && star && PBear(r, i) && c < (o2 + c2) / 2 && r[i+3].close > r[i+8].close;
   bool s0 = PBull(r, i) && body > 0.6 * avg && up < 0.3 * body;
   bool s1 = PBull(r, i+1) && b1 > 0.6 * avg && PUp(r, i+1) < 0.3 * b1;
   bool s2 = PBull(r, i+2) && b2 > 0.6 * avg && PUp(r, i+2) < 0.3 * b2;
   hit[12] = s0 && s1 && s2 && c > c1 && c1 > c2 && o > o1 && o < c1 && o1 > o2 && o1 < c2;
   bool k0 = PBear(r, i) && body > 0.6 * avg && lo < 0.3 * body;
   bool k1 = PBear(r, i+1) && b1 > 0.6 * avg && PLo(r, i+1) < 0.3 * b1;
   bool k2 = PBear(r, i+2) && b2 > 0.6 * avg && PLo(r, i+2) < 0.3 * b2;
   hit[13] = k0 && k1 && k2 && c < c1 && c1 < c2 && o < o1 && o > c1 && o1 < o2 && o1 > c2;
   bool doji = body <= 0.1 * rng;
   hit[14] = doji && down;
   hit[15] = doji && upt;
}

// Net vote of the enabled patterns: +1, -1 or 0; first enabled pattern name in 'name'
int PatternVote(const MqlRates &r[], int i, const bool &enabled[], string &name)
{
   bool hit[NPAT];
   DetectPatterns(r, i, hit);
   int v = 0; name = "";
   for(int p = 0; p < NPAT; p++)
      if(hit[p] && enabled[p])
      {
         v += PatDir[p];
         name += (name == "" ? "" : ", ") + PatName[p];
      }
   return v > 0 ? 1 : (v < 0 ? -1 : 0);
}

//+------------------------------------------------------------------+
int OnInit()
{
   ArrayResize(enabled, NPAT);
   for(int p = 0; p < NPAT; p++) enabled[p] = true;
   SetIndexBuffer(0, BuyBuf, INDICATOR_DATA);
   SetIndexBuffer(1, BuyClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(2, SellBuf, INDICATOR_DATA);
   SetIndexBuffer(3, SellClr, INDICATOR_COLOR_INDEX);
   PlotIndexSetInteger(0, PLOT_ARROW, 233);
   PlotIndexSetInteger(1, PLOT_ARROW, 234);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   ArraySetAsSeries(BuyBuf, true); ArraySetAsSeries(BuyClr, true);
   ArraySetAsSeries(SellBuf, true); ArraySetAsSeries(SellClr, true);
   hFast = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   hSlow = iMA(_Symbol, PERIOD_H1, 80, 0, MODE_EMA, PRICE_CLOSE);
   if(hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE) return INIT_FAILED;
   IndicatorSetString(INDICATOR_SHORTNAME, "Gold Candle Patterns");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, PFX);
   if(hFast != INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow != INVALID_HANDLE) IndicatorRelease(hSlow);
   Comment("");
}

// H1 trend known when the bar opened at t closes: +1 up, -1 down, 0 unknown
int TrendAt(datetime barClose)
{
   int sh = iBarShift(_Symbol, PERIOD_H1, barClose - 1, false);
   if(sh < 0) return 0;
   double f[1], s[1];
   if(CopyBuffer(hFast, 0, sh + 1, 1, f) != 1 || CopyBuffer(hSlow, 0, sh + 1, 1, s) != 1) return 0;
   return f[0] > s[0] ? 1 : (f[0] < s[0] ? -1 : 0);
}

void Label(string name, datetime t, double price, string text, color clr, bool above)
{
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_TEXT, 0, t, price);
   ObjectSetInteger(0, name, OBJPROP_TIME, t);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 7);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, above ? ANCHOR_LOWER : ANCHOR_UPPER);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   if(rates_total < 40) return 0;
   if(BarsCalculated(hFast) <= 0 || BarsCalculated(hSlow) <= 0) return 0;
   ArraySetAsSeries(time, true); ArraySetAsSeries(open, true); ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true); ArraySetAsSeries(close, true);

   int limit;
   if(prev_calculated <= 0)
   {
      ArrayInitialize(BuyBuf, EMPTY_VALUE); ArrayInitialize(SellBuf, EMPTY_VALUE);
      ArrayInitialize(BuyClr, 0); ArrayInitialize(SellClr, 0);
      ObjectsDeleteAll(0, PFX);
      limit = MathMin(rates_total - 25, 5000);          // mark the last 5,000 bars on load
   }
   else
      limit = MathMin(rates_total - prev_calculated + 1, rates_total - 25);

   BuyBuf[0] = EMPTY_VALUE; SellBuf[0] = EMPTY_VALUE;     // forming bar never marked
   int need = limit + 22;
   MqlRates r[];
   ArrayResize(r, need);
   for(int k = 0; k < need; k++)
   {
      r[k].time = time[k]; r[k].open = open[k]; r[k].high = high[k]; r[k].low = low[k]; r[k].close = close[k];
   }
   int ps = PeriodSeconds();
   string lastName = ""; datetime lastTime = 0; int lastDir = 0, lastTrend = 0;

   for(int i = limit; i >= 1; i--)
   {
      BuyBuf[i] = EMPTY_VALUE; SellBuf[i] = EMPTY_VALUE;
      bool hit[NPAT];
      DetectPatterns(r, i, hit);
      int v = 0; string shortTxt = "", longTxt = "";
      for(int p = 0; p < NPAT; p++)
         if(hit[p])
         {
            v += PatDir[p];
            shortTxt += (shortTxt == "" ? "" : " ") + PatShort[p];
            longTxt  += (longTxt == "" ? "" : ", ") + PatName[p];
         }
      int dir = v > 0 ? 1 : (v < 0 ? -1 : 0);
      if(dir == 0) continue;
      int trend = TrendAt(time[i] + ps);
      double off = InpOffsetUSD > 0 ? InpOffsetUSD : (high[i] - low[i]) * 0.3 + 10 * _Point;
      string nm = PFX + IntegerToString((long)time[i]);
      if(dir == 1)
      {
         BuyBuf[i] = low[i] - off; BuyClr[i] = trend == 1 ? 0 : 1;
         if(InpShowLabels && i <= InpLabelBars) Label(nm, time[i], low[i] - 2.5 * off, shortTxt, trend == 1 ? clrLimeGreen : clrDarkGray, false);
      }
      else
      {
         SellBuf[i] = high[i] + off; SellClr[i] = trend == -1 ? 0 : 1;
         if(InpShowLabels && i <= InpLabelBars) Label(nm, time[i], high[i] + 2.5 * off, shortTxt, trend == -1 ? clrTomato : clrDarkGray, true);
      }
      { lastName = longTxt; lastTime = time[i]; lastDir = dir; lastTrend = trend; }
   }

   if(lastTime > 0 && lastDir == lastTrend && InpAlerts && prev_calculated > 0 && lastTime == time[1] && lastAlert != time[1])
   {
      lastAlert = time[1];
      Alert(_Symbol, " ", EnumToString((ENUM_TIMEFRAMES)_Period), ": ", lastDir == 1 ? "BUY " : "SELL ", lastName, " with the H1 trend");
   }
   if(InpShowPanel)
   {
      static string lastPanel = "";
      static datetime panelTime = 0; static int panelDir = 0, panelTrend = 0;
      if(lastTime > 0 && lastTime >= panelTime) { lastPanel = lastName; panelTime = lastTime; panelDir = lastDir; panelTrend = lastTrend; }
      int tNow = TrendAt(TimeCurrent());
      string txt = "Gold Candle Patterns\n"
                 + "H1 trend: " + (tNow == 1 ? "UP" : (tNow == -1 ? "DOWN" : "-")) + "\n"
                 + "Last pattern: " + (panelTime > 0 ? (panelDir == 1 ? "BUY  " : "SELL  ") + lastPanel + "  at " + TimeToString(panelTime, TIME_DATE | TIME_MINUTES)
                                                     + (panelDir == panelTrend ? "  (with trend)" : "  (against trend, skipped)") : "none yet");
      Comment(txt);
   }
   return rates_total;
}
//+------------------------------------------------------------------+
