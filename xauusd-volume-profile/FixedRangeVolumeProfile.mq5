//+------------------------------------------------------------------+
//|                                     FixedRangeVolumeProfile.mq5  |
//| Fixed range volume profile for MT5 (any symbol, made for XAUUSD) |
//|                                                                  |
//| Two dashed vertical lines mark the range. Drag either one and    |
//| the profile is rebuilt for the candles between them:             |
//|   - rows of volume by price, split into up and down volume       |
//|     (volume of candles that closed up vs down);                  |
//|   - POC, the row with the most volume (gold line);               |
//|   - value area (default 70% of the volume, built outward from    |
//|     the POC), its top (VAH) and bottom (VAL) as dotted lines;    |
//|     rows inside it are drawn brighter.                           |
//| Each candle's volume is spread evenly over its high-low range.   |
//| By default the profile is built from M1 candles inside the range |
//| (more precise than the chart's own candles); a range too long    |
//| for that moves to a coarser timeframe on its own.                |
//|                                                                  |
//| Volume: brokers' XAUUSD is a CFD with no exchange volume. MT5    |
//| gives tick volume, the number of price updates in each candle,   |
//| which follows activity but is not contracts traded. If you pick  |
//| real volume and the broker has none, tick volume is used.        |
//|                                                                  |
//| Several profiles on one chart: add the indicator again with a    |
//| different "Name of this profile". The range lines stay where you |
//| left them when you change timeframe; removing the indicator      |
//| removes them.                                                    |
//|                                                                  |
//| A picture of where volume traded, not a tested trading signal.   |
//+------------------------------------------------------------------+
#property copyright   "Trading Agent project"
#property version     "1.00"
#property description "Fixed range volume profile: drag the two dashed lines to choose the range."
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

enum ENUM_FRVP_PLACE
{
   PLACE_LEFT  = 0,   // Left: rows grow from the range start
   PLACE_RIGHT = 1    // Right: rows end at the range end
};

//--- inputs
input group "Range"
input string              InpID            = "FRVP1";        // Name of this profile (another name = another profile)
input int                 InpStartBarsBack = 120;            // First range starts this many bars back (until you drag the lines)
input bool                InpLiveEnd       = false;          // Range always ends at the newest candle (no end line)

input group "Profile"
input int                 InpRows          = 60;             // Number of price rows (used when row size is 0)
input double              InpRowSize       = 0.0;            // Row size in price, e.g. 0.50 = $0.50 on XAUUSD (0 = use number of rows)
input double              InpValueAreaPct  = 70.0;           // Value area, % of the range's volume
input ENUM_APPLIED_VOLUME InpVolume        = VOLUME_TICK;    // Volume (gold CFDs only have tick volume)
input ENUM_TIMEFRAMES     InpSourceTF      = PERIOD_M1;      // Candles used to build the profile (never coarser than the chart)
input int                 InpMaxSourceBars = 200000;         // Above this many source candles, use a coarser timeframe
input bool                InpUpDown        = true;           // Split rows into up and down volume

input group "Look"
input ENUM_FRVP_PLACE     InpPlacement     = PLACE_LEFT;     // Where the rows sit in the range
input double              InpWidthPct      = 30.0;           // Longest row, % of the range's width
input int                 InpMinWidthBars  = 20;             // ...but at least this many candles wide (short ranges)
input color               InpUpColor       = C'38,166,154';  // Up volume, inside the value area
input color               InpDnColor       = C'239,83,80';   // Down volume, inside the value area
input color               InpUpColorOut    = C'56,110,105';  // Up volume, outside the value area
input color               InpDnColorOut    = C'140,72,72';   // Down volume, outside the value area
input color               InpTotalColor    = C'86,128,214';  // Rows when the up/down split is off, inside the value area
input color               InpTotalColorOut = C'62,80,120';   // Rows when the up/down split is off, outside the value area
input color               InpPOCColor      = clrGold;        // POC line
input color               InpVAColor       = clrSilver;      // VAH and VAL lines
input bool                InpExtendLines   = true;           // Extend POC, VAH and VAL to the right
input bool                InpShowLabels    = true;           // Price labels and a summary in the bottom-right corner
input color               InpLabelColor    = clrSilver;      // Text colour
input color               InpLineColor     = clrDodgerBlue;  // Range lines
input int                 InpSummaryRow    = 0;              // Summary position: 0 = bottom, 1 = above it... (one per profile)

//--- state
string   gP;                 // prefix of every object of this profile
string   gStart, gEnd;       // the two range lines
bool     gPending = true;    // a redraw is due
datetime gLastBar  = 0;      // newest chart candle seen
datetime gLastDraw = 0;      // local time of the last redraw
int      gMinSec   = 0;      // source timeframes finer than this failed to load for this range
datetime gFailSince = 0;     // local time the current source timeframe first failed to load
datetime gMinSecSet = 0;     // local time gMinSec was raised (finer data is tried again a minute later)
int      gRetryMin = 0;      // gMinSec before that retry, put back if the finer data still isn't there
datetime gLastA = 0, gLastB = 0;   // the range the lines last had (to restore a deleted line)
datetime gVolBar = 0;        // newest candle and its tick volume at the last redraw (live ranges)
long     gVolLast = -1;
double   gUp[], gDn[], gTot[];

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpRows < 2 || InpRows > 1000 || InpRowSize < 0 || (InpRowSize > 0 && InpRowSize < _Point) || InpValueAreaPct <= 0 ||
      InpValueAreaPct > 100 || InpWidthPct <= 0 || InpWidthPct > 100 || InpMinWidthBars < 1 || InpMaxSourceBars < 100 ||
      InpStartBarsBack < 1 || InpSummaryRow < 0 || StringLen(InpID) == 0 || StringFind(InpID, "]") >= 0)
   {
      Print("Check the inputs: rows 2-1000, row size 0 or at least one point, value area 1-100%, width 1-100%, minimum width at least 1 candle, ",
            "at least 100 source candles, start at least 1 bar back, summary position 0 or more, a name without ]");
      return INIT_PARAMETERS_INCORRECT;
   }
   gP     = "FRVP[" + InpID + "]";
   gStart = gP + "Start";
   gEnd   = gP + "End";
   if(InpLiveEnd && ObjectFind(0, gEnd) >= 0) ObjectDelete(0, gEnd);
   EnsureLines();
   if(ObjectFind(0, gStart) >= 0) ObjectSetInteger(0, gStart, OBJPROP_COLOR, InpLineColor);   // a new colour input reaches lines kept from before
   if(ObjectFind(0, gEnd)   >= 0) ObjectSetInteger(0, gEnd,   OBJPROP_COLOR, InpLineColor);
   EventSetTimer(1);
   gPending = true;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(gP == "") return;                         // OnInit stopped before anything was created
   ObjectsDeleteAll(0, gP + "P_");
   if(reason == REASON_REMOVE)                  // removed from the chart: take the range lines too
   {
      ObjectDelete(0, gStart);
      ObjectDelete(0, gEnd);
   }
   ChartRedraw();
}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   datetime last = iTime(_Symbol, _Period, 0);
   if(prev_calculated == 0) gPending = true;
   if(last != gLastBar)
   {
      if(gLastBar > 0 && RangeTouchesNewest(gLastBar)) gPending = true;   // also a range that ended on the candle that just closed
      gLastBar = last;
   }
   if(gPending && TimeLocal() != gLastDraw) Redraw();                   // at most once a second while history loads
   return rates_total;
}

void OnTimer()
{
   if(ObjectFind(0, gStart) < 0 || (!InpLiveEnd && ObjectFind(0, gEnd) < 0))
   {
      EnsureLines();                             // a line was deleted, or history wasn't ready at start
      gPending = true;
   }
   if(gMinSec > 0 && (long)(TimeLocal() - gMinSecSet) >= 60) { gRetryMin = gMinSec; gMinSec = 0; gPending = true; }   // try the finer candles again
   if(!gPending && RangeTouchesNewest() && (long)(TimeLocal() - gLastDraw) >= 5 &&
      (iTime(_Symbol, _Period, 0) != gVolBar || iVolume(_Symbol, _Period, 0) != gVolLast)) gPending = true;   // new volume on the forming candle
   if(gPending) Redraw();
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if((id == CHARTEVENT_OBJECT_DRAG || id == CHARTEVENT_OBJECT_CHANGE) && (sparam == gStart || sparam == gEnd))
   {
      gMinSec = 0; gFailSince = 0; gRetryMin = 0;   // a new range: try the finest source timeframe again
      Redraw();
   }
}

//+------------------------------------------------------------------+
//| Range lines                                                      |
//+------------------------------------------------------------------+
void MakeLine(const string name, const datetime t, const string tip)
{
   if(ObjectFind(0, name) >= 0 || t <= 0) return;
   if(!ObjectCreate(0, name, OBJ_VLINE, 0, t, 0)) return;
   ObjectSetInteger(0, name, OBJPROP_COLOR, InpLineColor);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, true);   // draggable straight away
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
}

void EnsureLines()
{
   int bars = Bars(_Symbol, _Period);
   if(bars < 2) return;
   int back = MathMin(InpStartBarsBack, bars - 1);
   // a deleted line comes back where it was; a new one starts at the defaults
   if(ObjectFind(0, gStart) < 0) MakeLine(gStart, gLastA > 0 ? gLastA : iTime(_Symbol, _Period, back), "Volume profile " + InpID + ": start (drag me)");
   if(!InpLiveEnd && ObjectFind(0, gEnd) < 0) MakeLine(gEnd, gLastB > 0 ? gLastB : iTime(_Symbol, _Period, 0), "Volume profile " + InpID + ": end (drag me)");
}

// True when the range reaches the candle at `newest` (default: the forming candle).
bool RangeTouchesNewest(const datetime newest = 0)
{
   if(InpLiveEnd) return true;
   if(ObjectFind(0, gStart) < 0 || ObjectFind(0, gEnd) < 0) return false;
   datetime a = (datetime)ObjectGetInteger(0, gStart, OBJPROP_TIME, 0);
   datetime b = (datetime)ObjectGetInteger(0, gEnd, OBJPROP_TIME, 0);
   datetime m = a > b ? a : b;
   return m >= (newest > 0 ? newest : iTime(_Symbol, _Period, 0));
}

// Chart-bar shifts of the range: sA = oldest candle, sB = newest candle (sA >= sB).
bool RangeShifts(int &sA, int &sB)
{
   if(ObjectFind(0, gStart) < 0) return false;
   datetime tA = (datetime)ObjectGetInteger(0, gStart, OBJPROP_TIME, 0);
   datetime tB;
   if(InpLiveEnd) tB = iTime(_Symbol, _Period, 0);
   else
   {
      if(ObjectFind(0, gEnd) < 0) return false;
      tB = (datetime)ObjectGetInteger(0, gEnd, OBJPROP_TIME, 0);
   }
   if(tA <= 0 || tB <= 0) return false;
   gLastA = (datetime)ObjectGetInteger(0, gStart, OBJPROP_TIME, 0);
   if(!InpLiveEnd) gLastB = (datetime)ObjectGetInteger(0, gEnd, OBJPROP_TIME, 0);
   if(tA > tB) { datetime x = tA; tA = tB; tB = x; }
   int bars = Bars(_Symbol, _Period);
   if(bars < 2) return false;
   sA = iBarShift(_Symbol, _Period, tA, false);   // the candle holding that time (or the one before it)
   sB = iBarShift(_Symbol, _Period, tB, false);
   if(sA < 0) sA = bars - 1;
   if(sB < 0) sB = bars - 1;
   if(sA < sB) { int x = sA; sA = sB; sB = x; }
   return true;
}

// Open time of the candle x candles after the range's first candle (x a whole number; negative = before the range,
// past the newest candle = MT5's empty area on the right). MT5 places object times at whole candles.
datetime TimeAt(const int sA, const int x)
{
   int  sh   = sA - x;
   int  last = Bars(_Symbol, _Period) - 1;
   long ps   = PeriodSeconds(_Period);
   if(sh > last) sh = last;
   if(sh >= 0) return iTime(_Symbol, _Period, sh);
   return (datetime)((long)iTime(_Symbol, _Period, 0) + (long)(-sh) * ps);
}

// Finest allowed timeframe at or above InpSourceTF that needs at most InpMaxSourceBars candles; never coarser than the chart.
ENUM_TIMEFRAMES SourceTF(const datetime from, const datetime to)
{
   ENUM_TIMEFRAMES ladder[] = {PERIOD_M1, PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1};
   int chartSec = PeriodSeconds(_Period);
   int wantSec  = PeriodSeconds(InpSourceTF == PERIOD_CURRENT ? _Period : InpSourceTF);
   if(gMinSec > wantSec) wantSec = gMinSec;
   for(int i = 0; i < ArraySize(ladder); i++)
   {
      int s = PeriodSeconds(ladder[i]);
      if(s < wantSec) continue;
      if(s >= chartSec) break;
      int need = Bars(_Symbol, ladder[i], from, to);   // 0 while that history is still loading: try it anyway
      if(need <= InpMaxSourceBars) return ladder[i];
   }
   return _Period;
}

int RowOf(const double p, const double base, const double step, const int rows)
{
   int k = (int)MathFloor((p - base) / step);
   if(k < 0) k = 0;
   if(k > rows - 1) k = rows - 1;
   return k;
}

//+------------------------------------------------------------------+
//| Build and draw                                                   |
//+------------------------------------------------------------------+
void Redraw()
{
   gPending  = false;
   gLastDraw = TimeLocal();

   int sA, sB;
   if(!RangeShifts(sA, sB)) { ObjectsDeleteAll(0, gP + "P_"); gPending = true; return; }
   datetime from = iTime(_Symbol, _Period, sA);
   datetime to   = sB > 0 ? (datetime)((long)iTime(_Symbol, _Period, sB - 1) - 1)    // up to the next chart candle (exact for MN1 too)
                          : (datetime)((long)TimeCurrent() + 40 * 86400);           // forming candle: everything so far
   if(from <= 0 || to <= from) { ObjectsDeleteAll(0, gP + "P_"); gPending = true; return; }

   ENUM_TIMEFRAMES src = SourceTF(from, to);
   MqlRates r[];
   int n = CopyRates(_Symbol, src, from, to, r);
   datetime first2 = sA > 0 ? iTime(_Symbol, _Period, sA - 1) : to;   // open of the range's second chart candle
   bool     notReady = n <= 0 || r[0].time >= first2;                   // nothing yet, or the history doesn't reach back to the range start
   if(notReady && gRetryMin > 0)                    // the once-a-minute retry of finer candles failed: keep the profile already drawn
   {
      gMinSec = gRetryMin; gRetryMin = 0; gMinSecSet = TimeLocal();
      return;
   }
   gRetryMin = 0;
   ObjectsDeleteAll(0, gP + "P_");
   if(notReady)
   {
      if(src != _Period)
      {
         if(gFailSince == 0) gFailSince = TimeLocal();
         else if((long)(TimeLocal() - gFailSince) >= 10)   // after 10 seconds, use coarser candles for now
         {
            gMinSec    = PeriodSeconds(src) + 1;
            gMinSecSet = TimeLocal();
            gFailSince = 0;
         }
      }
      Status("Volume profile " + InpID + ": loading " + StringSubstr(EnumToString(src), 7) + " history...", "");
      gPending = true;                            // try again on the next timer tick
      ChartRedraw();
      if(n <= 0 || src != _Period) return;        // the chart's own candles: draw what there is
   }
   gFailSince = 0;
   gVolBar  = iTime(_Symbol, _Period, 0);
   gVolLast = iVolume(_Symbol, _Period, 0);

   // volume source: real volume only if the broker supplies it
   bool useReal = false;
   if(InpVolume == VOLUME_REAL)
      for(int i = 0; i < n && !useReal; i++) if(r[i].real_volume > 0) useReal = true;

   // price grid
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = 0; i < n; i++) { if(r[i].high > hi) hi = r[i].high; if(r[i].low < lo) lo = r[i].low; }
   if(hi - lo < _Point) hi = lo + _Point;
   int    rows = 1;
   double base = lo, step = _Point;              // set below (a starting value keeps MetaEditor from warning)
   if(InpRowSize > 0)                             // rows on round prices; past 2000 rows, a whole multiple of the row size
   {
      double m = 1, nr = 1;
      while(true)
      {
         step = InpRowSize * m;
         base = MathFloor(lo / step + 1e-9) * step;
         nr   = MathCeil((hi - base) / step - 1e-9);
         if(nr <= 2000) break;
         m = MathMax(m + 1, MathCeil(m * nr / 2000.0));
      }
      rows = (int)MathMax(1, nr);
   }
   else
   {
      rows = InpRows;
      base = lo;
      step = (hi - lo) / rows;
   }

   // spread each candle's volume evenly over its high-low range
   ArrayResize(gUp, rows); ArrayResize(gDn, rows); ArrayResize(gTot, rows);
   ArrayInitialize(gUp, 0.0); ArrayInitialize(gDn, 0.0); ArrayInitialize(gTot, 0.0);
   for(int i = 0; i < n; i++)
   {
      double v = useReal ? (double)r[i].real_volume : (double)r[i].tick_volume;
      if(v <= 0) continue;
      bool   up = r[i].close >= r[i].open;
      double h  = r[i].high, l = r[i].low;
      int    a  = RowOf(l, base, step, rows), b = RowOf(h, base, step, rows);
      if(a == b || h - l < _Point * 0.5) { AddVol(a, v, up); continue; }
      double pl = (l - base) / step, ph = (h - base) / step;   // in row units, so a fully covered row gets exactly 1
      for(int k = a; k <= b; k++)
      {
         double rl = k, rh = k + 1;
         if(k == rows - 1) rh = MathMax(rh, ph);  // top row also holds the range high
         if(k == 0) rl = MathMin(rl, pl);
         double ov = MathMin(ph, rh) - MathMax(pl, rl);
         if(ov > 0) AddVol(k, v * ov / (ph - pl), up);
      }
   }

   // POC: the row with the most volume (a tie goes to the row nearest the middle)
   double sum = 0, maxv = 0, mid = (rows - 1) / 2.0;
   int    poc = 0;
   for(int k = 0; k < rows; k++)
   {
      gTot[k] = gUp[k] + gDn[k];
      sum += gTot[k];
      if(gTot[k] > maxv * (1 + 1e-12) || (gTot[k] >= maxv * (1 - 1e-12) && gTot[k] > 0 && MathAbs(k - mid) < MathAbs(poc - mid)))
      {
         maxv = gTot[k];
         poc  = k;
      }
   }
   if(sum <= 0 || maxv <= 0)
   {
      Status("Volume profile " + InpID + ": no volume in this range", "");
      ChartRedraw();
      return;
   }

   // value area: from the POC, add the bigger neighbouring row (above or below) until it holds InpValueAreaPct of the volume
   double target = sum * InpValueAreaPct / 100.0, acc = gTot[poc];
   int    vaLo = poc, vaHi = poc;
   while(acc < target - sum * 1e-12 && (vaLo > 0 || vaHi < rows - 1))
   {
      double above = vaHi < rows - 1 ? gTot[vaHi + 1] : -1.0;
      double below = vaLo > 0        ? gTot[vaLo - 1] : -1.0;
      bool goUp = above > below * (1 + 1e-9) || (above >= below * (1 - 1e-9) && vaHi - poc <= poc - vaLo);   // a tie keeps it centred
      if(goUp) { vaHi++; acc += gTot[vaHi]; }
      else     { vaLo--; acc += gTot[vaLo]; }
   }
   double pocPx = base + (poc + 0.5) * step;
   double vah   = base + (vaHi + 1) * step;
   double val   = base + vaLo * step;

   // rows
   int    nb   = sA - sB + 1;                      // chart candles in the range
   double maxW = MathMax(nb * InpWidthPct / 100.0, (double)InpMinWidthBars);   // longest row, in candles
   double gap  = step * 0.08;
   for(int k = 0; k < rows; k++)
   {
      if(gTot[k] <= 0) continue;
      bool   inVA = k >= vaLo && k <= vaHi;
      int    w    = MathMax(1, (int)MathRound(gTot[k] / maxv * maxW));  // whole candles: MT5 draws objects at candle opens
      int    wu   = InpUpDown ? (int)MathRound(gUp[k] / maxv * maxW) : w;
      double y1   = base + k * step + gap, y2 = base + (k + 1) * step - gap;
      color  c1   = InpUpDown ? (inVA ? InpUpColor : InpUpColorOut) : (inVA ? InpTotalColor : InpTotalColorOut);
      color  c2   = inVA ? InpDnColor : InpDnColorOut;
      int    x0, x1, x2;                           // first segment x0..x1 (up, or all), second x1..x2 (down)
      if(InpPlacement == PLACE_LEFT) { x0 = 0;  x1 = wu;      x2 = w;      }
      else                           { x0 = nb; x1 = nb - wu; x2 = nb - w; }
      string id = IntegerToString(k);
      if(x1 != x0) Box(gP + "P_U" + id, TimeAt(sA, MathMin(x0, x1)), TimeAt(sA, MathMax(x0, x1)), y1, y2, c1);
      if(InpUpDown && x2 != x1) Box(gP + "P_D" + id, TimeAt(sA, MathMin(x1, x2)), TimeAt(sA, MathMax(x1, x2)), y1, y2, c2);
   }

   // POC, VAH, VAL
   datetime tL = TimeAt(sA, 0), tR = TimeAt(sA, nb);
   HLine(gP + "P_POC", tL, tR, pocPx, InpPOCColor, STYLE_SOLID, 2);
   HLine(gP + "P_VAH", tL, tR, vah, InpVAColor, STYLE_DOT, 1);
   HLine(gP + "P_VAL", tL, tR, val, InpVAColor, STYLE_DOT, 1);
   if(InpShowLabels)
   {
      Text(gP + "P_tPOC", tR, pocPx, " POC " + DoubleToString(pocPx, _Digits), InpPOCColor);
      Text(gP + "P_tVAH", tR, vah,   " VAH " + DoubleToString(vah, _Digits), InpVAColor);
      Text(gP + "P_tVAL", tR, val,   " VAL " + DoubleToString(val, _Digits), InpVAColor);
      string vol = useReal ? "real volume" : (InpVolume == VOLUME_REAL ? "tick volume (no real volume here)" : "tick volume");
      Status(StringFormat("Volume profile %s: %s to %s, %d candles, built from %d %s candles, %s",
                          InpID, TimeToString(from, TIME_DATE | TIME_MINUTES), TimeToString(iTime(_Symbol, _Period, sB), TIME_DATE | TIME_MINUTES),
                          nb, n, StringSubstr(EnumToString(src), 7), vol),
             StringFormat("POC %s   value area %s - %s (%.0f%% of the volume)   %d rows of %s",
                          DoubleToString(pocPx, _Digits), DoubleToString(val, _Digits), DoubleToString(vah, _Digits),
                          InpValueAreaPct, rows, DoubleToString(step, _Digits)));
   }
   ChartRedraw();
}

void AddVol(const int k, const double v, const bool up)
{
   if(up) gUp[k] += v;
   else   gDn[k] += v;
}

void Box(const string name, const datetime t1, datetime t2, const double p1, const double p2, const color c)
{
   if(t2 <= t1) t2 = t1 + 1;
   if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2)) return;
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
}

void HLine(const string name, const datetime t1, const datetime t2, const double p, const color c, const ENUM_LINE_STYLE st, const int width)
{
   if(!ObjectCreate(0, name, OBJ_TREND, 0, t1, p, t2, p)) return;
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, InpExtendLines);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
}

void Text(const string name, const datetime t, const double p, const string s, const color c)
{
   if(!ObjectCreate(0, name, OBJ_TEXT, 0, t, p)) return;
   ObjectSetString(0, name, OBJPROP_TEXT, s);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);   // text sits just above its line
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
}

// Two summary lines in the bottom-right corner.
void Status(const string line1, const string line2)
{
   if(!InpShowLabels) return;
   string s[2];
   s[0] = line1; s[1] = line2;
   for(int i = 0; i < 2; i++)
   {
      string name = gP + "P_S" + IntegerToString(i);
      if(s[i] == "") continue;
      if(!ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0)) continue;
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_RIGHT_LOWER);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_RIGHT_LOWER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 10);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 10 + 15 * (1 - i) + 35 * InpSummaryRow);
      ObjectSetString(0, name, OBJPROP_TEXT, s[i]);
      ObjectSetString(0, name, OBJPROP_FONT, "Arial");
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, name, OBJPROP_COLOR, InpLabelColor);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   }
}
//+------------------------------------------------------------------+
