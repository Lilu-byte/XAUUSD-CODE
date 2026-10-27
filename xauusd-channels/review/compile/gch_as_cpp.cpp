#include "mql5_shim.h"  //+------------------------------------------------------------------+
//|                                                 GoldChannels.mq5 |
//| Ranges, uptrends and downtrends with their channels, for MT5     |
//| (any symbol and timeframe, made for XAUUSD)                      |
//|                                                                  |
//| The chart is cut into stretches. Each stretch gets a straight    |
//| line fitted through its closes (least squares) and a channel:    |
//|   - green channel: uptrend (the line rises more than the         |
//|     channel is wide, times "trend strength");                    |
//|   - red channel: downtrend (the same, falling);                  |
//|   - blue box: range (the line is too flat for a trend); the box  |
//|     runs from the stretch's highest high to its lowest low.      |
//| The channel lines touch the highest high and the lowest low of   |
//| the stretch, measured from the fitted line.                      |
//|                                                                  |
//| A stretch ends when 2 candles in a row CLOSE outside its band    |
//| on the same side (the fitted line +- 2 standard deviations of    |
//| the closes, plus 0.2 ATR). The new stretch starts at the swing   |
//| that led to the break: the lowest low of the last "min bars"     |
//| candles for a break up, the highest high for a break down. An    |
//| arrow marks the candle that confirmed the break.                 |
//|                                                                  |
//| Strong channels (both lines touched at least twice, and for a    |
//| trend a straight enough line) are drawn bright; weak ones faded. |
//| The higher timeframe's channels (H1 on M1-M5, H4 on M15-M30, D1  |
//| on H1-H4, W1 on D1) are drawn as thick unshaded lines on top.    |
//| Alerts when price reaches the live channel's upper or lower line |
//| (and optionally when a break is confirmed).                      |
//|                                                                  |
//| What can still change: only the newest stretch (dashed lines,    |
//| "live"). Its line, channel and label are refitted on every new   |
//| candle until a break ends it; at that moment its end moves back  |
//| to the swing and it is fixed for good. Every stretch before it   |
//| was decided with closed candles only and never changes. The same |
//| holds for the higher timeframe, whose live stretch changes with  |
//| each closed higher-timeframe candle.                             |
//|                                                                  |
//| A picture of trends and ranges, not a tested trading signal:     |
//| trading the breaks did not beat holding gold (see the README).   |
//+------------------------------------------------------------------+
//#property copyright   "Trading Agent project"
//#property version     "1.10"
//#property description "Ranges, uptrends and downtrends with their channels, plus the higher timeframe's. Only the newest (dashed) channels can still change."
//#property indicator_chart_window
//#property indicator_buffers 0
//#property indicator_plots   0

enum ENUM_GCH_WIDTH
{
   WIDTH_EXTREMES = 0,   // Touch the highest high and lowest low
   WIDTH_SIGMA    = 1    // Fitted line +- the band (standard deviations)
};

//--- inputs
//input group "Finding the stretches"
const int             InpMinBars      = 0;           // Shortest stretch in candles (0 = by timeframe: M1 60, M5 40, M15 30, M30 25, H1 and up 20)
const int             InpConfirm      = 2;           // Closes in a row outside the band to confirm a break
const double          InpBandSigma    = 2.0;         // Band: this many standard deviations of the closes...
const double          InpBufferATR    = 0.2;         // ...plus this many ATRs
const int             InpATRPeriod    = 14;          // ATR period
const double          InpTrendRatio   = 0.6;         // Trend strength: rise or fall over the stretch / channel width (below = range)
const int             InpMaxBars      = 3000;        // Candles of history to cut into stretches

//input group "Channel quality"
const bool            InpFadeWeak     = true;        // Fade weak channels
const int             InpMinTouches   = 2;           // Strong: each line touched at least this many separate times...
const double          InpTouchPct     = 20.0;        // ...a touch = within this % of the channel width from the line
const double          InpMinR2        = 0.6;         // ...and for a trend, R-squared of the closes around the line at least this

//input group "Higher timeframe"
const bool            InpShowHTF      = true;        // Draw the higher timeframe's channels
const ENUM_TIMEFRAMES InpHTF          = PERIOD_CURRENT; // Higher timeframe (current = automatic: H1 on M1-M5, H4 on M15-M30, D1 on H1-H4, W1 on D1)
const int             InpHTFProject   = 2;           // Extend its live channel this many of its candles to the right

//input group "Alerts"
const bool            InpAlertTouch   = true;        // Alert when price reaches the live channel's upper or lower line
const double          InpAlertPct     = 5.0;         // ...counting from this % of the channel width before the line
const bool            InpAlertBreak   = false;       // Alert when a break is confirmed
const bool            InpPush         = false;       // Also send alerts to the MT5 phone app

//input group "Look"
const ENUM_GCH_WIDTH  InpWidthMode    = WIDTH_EXTREMES; // Trend channel width
const bool            InpFlatRanges   = true;        // Draw ranges as flat boxes (false: as a flat-ish channel)
const bool            InpFill         = true;        // Shade the channels
const double          InpFillPct      = 22.0;        // Shade strength, % of the line colour over the chart background
const bool            InpMidLine      = true;        // Dotted middle line
const bool            InpLabels       = true;        // UP / DOWN / RANGE text at the start of each stretch
const bool            InpArrows       = true;        // Arrow on the candle that confirmed each break
const int             InpProjectBars  = 10;          // Extend the live channel this many candles to the right
const color           InpUpColor      = RGB_(38,166,154);  // Uptrend
const color           InpDnColor      = RGB_(239,83,80);   // Downtrend
const color           InpRangeColor   = RGB_(86,128,214);  // Range
const color           InpFormColor    = clrGray;     // Live stretch still shorter than the shortest stretch
const int             InpLineWidth    = 1;           // Line width (the higher timeframe's is one wider)
const int             InpFontSize     = 8;           // Text size
const bool            InpStatus       = true;        // Summary of the live stretches in the bottom-right corner
const color           InpTextColor    = clrSilver;   // Summary text colour
const string          InpID           = "GCH1";      // Name of this copy (another name = another copy on the same chart)

#define LAB_RANGE    0
#define LAB_UP       1
#define LAB_DOWN    -1
#define LAB_FORMING  2
#define LAB_AUTO    99

// One stretch's channel, as drawn
struct SChan
{
   double b, a, sd, up, lo;   // fitted line close ~ a + b*x (x = 0 at the first candle), sd of closes, highest high / lowest low from it
   double hh, ll;             // highest high, lowest low
   double du, dl;             // upper and lower line offsets from the fitted line (trend channels)
   int    n, lab;
   bool   flat;               // drawn as a flat box
   int    tu, tl;             // separate touches of the upper and lower line
   double r2;
   bool   strong;
};

class CSegmenter;
int MinBarsFor(const ENUM_TIMEFRAMES tf); ENUM_TIMEFRAMES PickHTF(); string TFName(const ENUM_TIMEFRAMES tf); void Fit(const int s, const int e, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close, double &b, double &a, double &sd, double &up, double &lo); int Classify(const double b, const int n, const double up, const double lo); void Chan(const int s, const int e, const int lab, const int minBars, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close, SChan &ch); void Rebuild(const int rates_total, const DynArr<datetime> &time, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close); void UpdateHTF(); bool LoadHTF(); void DrawHTF(); string LabelName(const int lab); string ShortName(const int lab); color LabelColor(const int lab); color Shade(const color c, const double pct); void Style(const string name, const color c, const int style, const int width, const bool back, const string tip); void Line(const string name, const datetime t1, const double p1, const datetime t2, const double p2, const color c, const int style, const int width, const string tip); void Triangle(const string name, const datetime t1, const double p1, const datetime t2, const double p2, const datetime t3, const double p3, const color c, const string tip); string ChanText(const SChan &ch, const int x); void DrawSeg(CSegmenter &sg, const int k, const bool live, const bool htf, const DynArr<datetime> &time, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close); void DrawBreak(const int k, const DynArr<datetime> &time, const DynArr<double> &high, const DynArr<double> &low); string MainStatus(const DynArr<datetime> &time); void StatusLine(const string nm, const int row, const string txt); void DrawStatus(); void Notify(const string msg); void CheckTouch(const datetime barTime, const double price, const int bar);
//--- state
string     gP;                       // prefix of every object of this copy
int        gRates   = 0;             // rates_total at the last call
datetime   gTime0   = 0;             // time of bar 0 at the last call (history reloaded if it changes)
datetime   gOldest  = 0;             // first candle the chart's stretches start from
string     gTxtMain = "", gTxtHTF = "";
SChan      gLive;                    // the chart's live stretch, for touch alerts
datetime   gTouchUp = 0, gTouchDn = 0; // candle of the last touch alert per line
ENUM_TIMEFRAMES gHtf = PERIOD_CURRENT; // higher timeframe in use (PERIOD_CURRENT = none)
bool       gHtfOK   = false;
datetime   gHtfLast = 0;             // newest higher-timeframe candle when it was last cut into stretches
DynArr<datetime> gHT;
DynArr<double> gHH, gHL, gHC;

// Cuts one series of candles (oldest first) into stretches
class CSegmenter
{
public:
   int    minBars;
   DynArr<int> segS, segE, segLab;  // fixed stretches: first bar, last bar, label
   int    n;
   DynArr<int> brkT, brkD;            // confirmed breaks: bar, direction
   int    nb;
   int    cur;                       // first bar of the live stretch
   int    done;                      // newest closed bar processed
   int    first;
   DynArr<double> atr;

   CSegmenter() { minBars = 20; n = 0; nb = 0; cur = 0; done = -1; first = 0; }

   // Cut bars fst..last (all closed) from scratch
   void Run(const int fst, const int last, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close)
   {
      n = 0; nb = 0;
      ArrayResize(segS, 0, 512); ArrayResize(segE, 0, 512); ArrayResize(segLab, 0, 512);
      ArrayResize(brkT, 0, 512); ArrayResize(brkD, 0, 512);
      ArrayResize(atr, last + 2, 1024);
      ArrayInitialize(atr, 0.0);
      first = fst; cur = fst;
      atr[fst] = high[fst] - low[fst];
      for(int t = fst + 1; t <= last; t++)
      {
         atr[t] = NextAtr(t, high, low, close);
         Step(t, high, low, close);
      }
      done = last;
   }

   // One more closed candle t (= done + 1)
   void Add(const int t, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close)
   {
      ArrayResize(atr, t + 2, 1024);
      atr[t] = NextAtr(t, high, low, close);
      Step(t, high, low, close);
      done = t;
   }

   // Wilder's ATR of bar t from the ATR of bar t-1
   double NextAtr(const int t, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close)
   {
      double pc = close[t - 1];
      double tr = MathMax(high[t] - low[t], MathMax(MathAbs(high[t] - pc), MathAbs(low[t] - pc)));
      return atr[t - 1] + (tr - atr[t - 1]) / InpATRPeriod;
   }

   // Do the last InpConfirm closes (up to t) all break out of the live stretch's band on the same side?
   void Step(const int t, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close)
   {
      int nc = InpConfirm;
      if(t - cur < minBars + nc - 1) return;   // the band is fitted on at least minBars candles before the confirming closes
      double b = 0, a = 0, sd = 0, up = 0, lo = 0;
      Fit(cur, t - nc, high, low, close, b, a, sd, up, lo);
      int ups = 0, dns = 0;
      for(int j = 0; j < nc; j++)
      {
         double line = a + b * (t - j - cur);
         double gap  = InpBandSigma * sd + InpBufferATR * atr[t - j];
         if(close[t - j] > line + gap)      ups++;
         else if(close[t - j] < line - gap) dns++;
      }
      int d = ups == nc ? 1 : (dns == nc ? -1 : 0);
      if(d == 0) return;
      // the new stretch starts at the swing that led to the break
      int w0 = MathMax(cur + minBars / 2, t - minBars + 1);
      int p = w0;
      for(int i = w0 + 1; i <= t; i++)
      {
         if(d > 0 && low[i]  < low[p])  p = i;
         if(d < 0 && high[i] > high[p]) p = i;
      }
      Fit(cur, p, high, low, close, b, a, sd, up, lo);
      ArrayResize(segS, n + 1, 512); ArrayResize(segE, n + 1, 512); ArrayResize(segLab, n + 1, 512);
      segS[n] = cur; segE[n] = p; segLab[n] = Classify(b, p - cur + 1, up, lo);
      n++;
      ArrayResize(brkT, nb + 1, 512); ArrayResize(brkD, nb + 1, 512);
      brkT[nb] = t; brkD[nb] = d;
      nb++;
      cur = p;
   }
};

CSegmenter gM;                       // the chart's own candles
CSegmenter gH;                       // the higher timeframe's

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpMinBars < 0 || (InpMinBars > 0 && InpMinBars < 5) || InpMinBars > 1000 || InpConfirm < 1 || InpConfirm > 10 ||
      InpBandSigma <= 0 || InpBufferATR < 0 || InpATRPeriod < 1 || InpTrendRatio < 0 || InpMaxBars < 100 ||
      InpProjectBars < 0 || InpHTFProject < 0 || InpFillPct < 0 || InpFillPct > 100 || InpMinTouches < 0 ||
      InpTouchPct < 0 || InpTouchPct > 100 || InpMinR2 < 0 || InpMinR2 > 1 || InpAlertPct < 0 || InpAlertPct > 50 ||
      InpLineWidth < 1 || InpFontSize < 4 || StringLen(InpID) == 0)
   {
      Print("Check the inputs: shortest stretch 0 (automatic) or 5-1000 candles, 1-10 confirming closes, band above 0, buffer 0 or more, ",
            "ATR period 1 or more, trend strength 0 or more, at least 100 candles of history, projections 0 or more, shade 0-100%, ",
            "touches 0 or more, touch distance 0-100%, R-squared 0-1, alert distance 0-50%, a name");
      return INIT_PARAMETERS_INCORRECT;
   }
   gP = "GCH[" + InpID + "]";
   gRates = 0;
   gHtf = PickHTF();
   gHtfOK = false; gHtfLast = 0;
   gH.minBars = MinBarsFor(gHtf == PERIOD_CURRENT ? _Period : gHtf);
   gM.minBars = MinBarsFor(_Period);
   EventSetTimer(2);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(gP != "") ObjectsDeleteAll(0, gP);
   ChartRedraw();
}

int OnCalculate(const int rates_total, const int prev_calculated, const DynArr<datetime> &time, const DynArr<double> &open,
                const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close, const DynArr<long> &tick_volume,
                const DynArr<long> &volume, const DynArr<int> &spread)
{
   if(rates_total < gM.minBars + InpConfirm + 3) return 0;
   // OnCalculate arrays run oldest (0) to newest (rates_total-1) unless set otherwise; make sure
   ArraySetAsSeries(time, false);
   ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);
   ArraySetAsSeries(close, false);

   if(prev_calculated == 0 || gRates == 0 || rates_total < gRates || rates_total - gRates > 1 || time[0] != gTime0)
      Rebuild(rates_total, time, high, low, close);
   else if(rates_total == gRates + 1)
   {
      // one new candle: the one before it has just closed
      int t = rates_total - 2;
      int nBefore = gM.n;
      gM.Add(t, high, low, close);
      if(gM.n > nBefore)
      {
         DrawSeg(gM, gM.n - 1, false, false, time, high, low, close);   // the live stretch just became fixed (it keeps its number)
         DrawBreak(gM.nb - 1, time, high, low);
         if(InpAlertBreak)
         {
            string dir = gM.brkD[gM.nb - 1] > 0 ? "UP" : "DOWN";
            Notify("channel break " + dir + ", the stretch before it was " + LabelName(gM.segLab[gM.n - 1]));
         }
      }
      DrawSeg(gM, gM.n, true, false, time, high, low, close);
      gTxtMain = MainStatus(time);
      DrawStatus();
      ChartRedraw();
   }
   gRates = rates_total;
   gTime0 = time[0];

   // the higher timeframe: cut again whenever it has a new candle
   if(gHtf != PERIOD_CURRENT)
   {
      datetime h0 = iTime(_Symbol, gHtf, 0);
      if(h0 > 0 && h0 != gHtfLast) UpdateHTF();
   }
   CheckTouch(time[rates_total - 1], close[rates_total - 1], rates_total - 1);
   return rates_total;
}

void OnTimer()
{
   // the higher timeframe's history may still be downloading when the indicator starts
   if(gHtf != PERIOD_CURRENT && !gHtfOK && gRates > 0) UpdateHTF();
}

//+------------------------------------------------------------------+
//| Settings by timeframe                                            |
//+------------------------------------------------------------------+
int MinBarsFor(const ENUM_TIMEFRAMES tf)
{
   if(InpMinBars > 0) return InpMinBars;
   int sec = PeriodSeconds(tf);
   if(sec <= 60)   return 60;
   if(sec <= 300)  return 40;
   if(sec <= 900)  return 30;
   if(sec <= 1800) return 25;
   return 20;
}

// The higher timeframe to draw, PERIOD_CURRENT for none
ENUM_TIMEFRAMES PickHTF()
{
   if(!InpShowHTF) return PERIOD_CURRENT;
   int sec = PeriodSeconds(_Period);
   if(InpHTF != PERIOD_CURRENT) return PeriodSeconds(InpHTF) > sec ? InpHTF : PERIOD_CURRENT;
   if(sec <= 300)   return PERIOD_H1;
   if(sec <= 1800)  return PERIOD_H4;
   if(sec <= 14400) return PERIOD_D1;
   if(sec <= 86400) return PERIOD_W1;
   return PERIOD_CURRENT;
}

string TFName(const ENUM_TIMEFRAMES tf)
{
   return StringSubstr(EnumToString(tf), 7);   // PERIOD_H4 -> H4
}

//+------------------------------------------------------------------+
//| Channel maths                                                    |
//+------------------------------------------------------------------+
// Least-squares line through the closes of bars s..e (x = 0 at s): close ~ a + b*x.
// sd: standard deviation of the closes around the line; up/lo: highest high and lowest low measured from it.
void Fit(const int s, const int e, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close,
         double &b, double &a, double &sd, double &up, double &lo)
{
   int n = e - s + 1;
   b = 0; a = close[s]; sd = 0; up = high[s] - close[s]; lo = low[s] - close[s];
   if(n < 2) return;
   double sx = 0, sy = 0, sxx = 0, sxy = 0;
   for(int i = s; i <= e; i++)
   {
      double x = i - s;
      sx += x; sy += close[i]; sxx += x * x; sxy += x * close[i];
   }
   double den = n * sxx - sx * sx;
   b = (n * sxy - sx * sy) / den;
   a = (sy - b * sx) / n;
   double ss = 0;
   up = -DBL_MAX; lo = DBL_MAX;
   for(int i = s; i <= e; i++)
   {
      double line = a + b * (i - s);
      double r = close[i] - line;
      ss += r * r;
      up = MathMax(up, high[i] - line);
      lo = MathMin(lo, low[i] - line);
   }
   sd = MathSqrt(ss / n);
}

// Trend when the line's rise or fall over the stretch is at least InpTrendRatio times the channel's width
int Classify(const double b, const int n, const double up, const double lo)
{
   double move = b * (n - 1);
   double width = up - lo;
   if(MathAbs(move) < InpTrendRatio * width) return LAB_RANGE;
   return move > 0 ? LAB_UP : LAB_DOWN;
}

double ChUpper(const SChan &ch, const double x) { return ch.flat ? ch.hh : ch.a + ch.b * x + ch.du; }
double ChLower(const SChan &ch, const double x) { return ch.flat ? ch.ll : ch.a + ch.b * x + ch.dl; }

// The channel of bars s..e as drawn, with its quality. lab = LAB_AUTO for a live stretch (classified now).
void Chan(const int s, const int e, const int lab, const int minBars, const DynArr<double> &high, const DynArr<double> &low,
          const DynArr<double> &close, SChan &ch)
{
   ch.n = e - s + 1;
   Fit(s, e, high, low, close, ch.b, ch.a, ch.sd, ch.up, ch.lo);
   ch.lab = lab;
   if(lab == LAB_AUTO) ch.lab = ch.n < minBars ? LAB_FORMING : Classify(ch.b, ch.n, ch.up, ch.lo);
   ch.hh = high[s]; ch.ll = low[s];
   for(int i = s + 1; i <= e; i++) { ch.hh = MathMax(ch.hh, high[i]); ch.ll = MathMin(ch.ll, low[i]); }
   ch.flat = (ch.lab == LAB_RANGE || ch.lab == LAB_FORMING) && InpFlatRanges;
   ch.du = ch.up; ch.dl = ch.lo;
   if(InpWidthMode == WIDTH_SIGMA) { ch.du = InpBandSigma * ch.sd; ch.dl = -InpBandSigma * ch.sd; }

   // quality: separate touches of each line (a run of touching candles counts once), and R-squared
   double w = ChUpper(ch, 0) - ChLower(ch, 0);
   double tol = InpTouchPct / 100.0 * w;
   ch.tu = 0; ch.tl = 0;
   bool inU = false, inL = false;
   double my = 0;
   for(int i = s; i <= e; i++) my += close[i];
   my /= ch.n;
   double ssr = 0, sst = 0;
   for(int i = s; i <= e; i++)
   {
      double x = i - s;
      bool tU = high[i] >= ChUpper(ch, x) - tol;
      bool tL = low[i]  <= ChLower(ch, x) + tol;
      if(tU && !inU) ch.tu++;
      if(tL && !inL) ch.tl++;
      inU = tU; inL = tL;
      double r = close[i] - (ch.a + ch.b * x);
      ssr += r * r;
      sst += (close[i] - my) * (close[i] - my);
   }
   ch.r2 = sst > 0 ? 1 - ssr / sst : 0;
   bool trend = ch.lab == LAB_UP || ch.lab == LAB_DOWN;
   ch.strong = ch.tu >= InpMinTouches && ch.tl >= InpMinTouches && (!trend || ch.r2 >= InpMinR2);
}

//+------------------------------------------------------------------+
//| The chart's stretches                                            |
//+------------------------------------------------------------------+
void Rebuild(const int rates_total, const DynArr<datetime> &time, const DynArr<double> &high, const DynArr<double> &low, const DynArr<double> &close)
{
   ObjectsDeleteAll(0, gP);
   int first = MathMax(1, rates_total - 1 - InpMaxBars);
   gM.Run(first, rates_total - 2, high, low, close);
   gOldest = time[first];
   for(int k = 0; k < gM.n; k++) DrawSeg(gM, k, false, false, time, high, low, close);
   for(int k = 0; k < gM.nb; k++) DrawBreak(k, time, high, low);
   DrawSeg(gM, gM.n, true, false, time, high, low, close);
   gTxtMain = MainStatus(time);
   if(gHtfOK) DrawHTF();
   DrawStatus();
   ChartRedraw();
}

//+------------------------------------------------------------------+
//| The higher timeframe                                             |
//+------------------------------------------------------------------+
void UpdateHTF()
{
   gHtfOK = LoadHTF();
   ObjectsDeleteAll(0, gP + "H");
   gTxtHTF = gHtfOK ? "" : TFName(gHtf) + ": loading history...";
   if(gHtfOK) DrawHTF();
   DrawStatus();
   ChartRedraw();
}

bool LoadHTF()
{
   int avail = Bars(_Symbol, gHtf);
   if(avail < gH.minBars + InpConfirm + 3) return false;
   int cnt = MathMin(avail, InpMaxBars + 1);
   if(CopyTime(_Symbol, gHtf, 0, cnt, gHT) != cnt || CopyHigh(_Symbol, gHtf, 0, cnt, gHH) != cnt ||
      CopyLow(_Symbol, gHtf, 0, cnt, gHL) != cnt || CopyClose(_Symbol, gHtf, 0, cnt, gHC) != cnt) return false;
   gH.Run(1, cnt - 2, gHH, gHL, gHC);         // closed higher-timeframe candles only
   gHtfLast = gHT[cnt - 1];
   return true;
}

void DrawHTF()
{
   for(int k = 0; k <= gH.n; k++)
   {
      bool live = k == gH.n;
      int e = live ? gH.done : gH.segE[k];
      if(!live && gHT[e] < gOldest) continue;    // ends before the chart's own stretches begin
      DrawSeg(gH, k, live, true, gHT, gHH, gHL, gHC);
   }
   SChan ch;
   int s = gH.cur, e = gH.done;
   Chan(s, e, LAB_AUTO, gH.minBars, gHH, gHL, gHC, ch);
   gTxtHTF = TFName(gHtf) + ": " + LabelName(ch.lab) + " (live) since " + TimeToString(gHT[s]) + ", " + ChanText(ch, e - s);
}

//+------------------------------------------------------------------+
//| Drawing                                                          |
//+------------------------------------------------------------------+
string LabelName(const int lab)
{
   if(lab == LAB_UP)   return "UPTREND";
   if(lab == LAB_DOWN) return "DOWNTREND";
   if(lab == LAB_FORMING) return "FORMING";
   return "RANGE";
}

string ShortName(const int lab)
{
   if(lab == LAB_UP)   return "UP";
   if(lab == LAB_DOWN) return "DOWN";
   return LabelName(lab);
}

color LabelColor(const int lab)
{
   if(lab == LAB_UP)   return InpUpColor;
   if(lab == LAB_DOWN) return InpDnColor;
   if(lab == LAB_FORMING) return InpFormColor;
   return InpRangeColor;
}

// pct% of c over the chart background (MT5 has no transparency, so the shade is mixed by hand)
color Shade(const color c, const double pct)
{
   int fg = (int)c;
   int bg = (int)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   double w = pct / 100.0;
   int r  = (int)MathRound(( fg        & 0xFF) * w + ( bg        & 0xFF) * (1 - w));
   int g  = (int)MathRound(((fg >> 8)  & 0xFF) * w + ((bg >> 8)  & 0xFF) * (1 - w));
   int bl = (int)MathRound(((fg >> 16) & 0xFF) * w + ((bg >> 16) & 0xFF) * (1 - w));
   return (color)(r | (g << 8) | (bl << 16));
}

void Style(const string name, const color c, const int style, const int width, const bool back, const string tip)
{
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_BACK, back);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
}

void Line(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
          const color c, const int style, const int width, const string tip)
{
   if(!ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2)) return;
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_RAY_LEFT, false);
   Style(name, c, style, width, false, tip);
}

void Triangle(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
              const datetime t3, const double p3, const color c, const string tip)
{
   if(!ObjectCreate(0, name, OBJ_TRIANGLE, 0, t1, p1, t2, p2, t3, p3)) return;
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   Style(name, c, STYLE_SOLID, 1, true, tip);
}

// "channel 4185.20 - 4201.70, +0.45 per candle, strong (upper line touched 3 times, lower 2, R2 0.84)" at x candles from the start
string ChanText(const SChan &ch, const int x)
{
   string t;
   if(ch.flat) t = "box " + DoubleToString(ch.ll, _Digits) + " - " + DoubleToString(ch.hh, _Digits);
   else        t = "channel " + DoubleToString(ChLower(ch, x), _Digits) + " - " + DoubleToString(ChUpper(ch, x), _Digits) +
                   ", " + (ch.b >= 0 ? "+" : "") + DoubleToString(ch.b, _Digits) + " per candle";
   if(ch.lab == LAB_FORMING) return t;
   return t + ", " + (ch.strong ? "strong" : "weak") + " (upper line touched " + IntegerToString(ch.tu) + "x, lower " +
          IntegerToString(ch.tl) + "x, R2 " + DoubleToString(ch.r2, 2) + ")";
}

// Stretch k of sg (k == sg.n: the live one, from sg.cur to the newest closed candle).
// htf: the higher timeframe's, drawn as thicker unshaded lines with the timeframe in its label.
void DrawSeg(CSegmenter &sg, const int k, const bool live, const bool htf, const DynArr<datetime> &time, const DynArr<double> &high,
             const DynArr<double> &low, const DynArr<double> &close)
{
   string nm = gP + (htf ? "H" : "S") + IntegerToString(k) + "_";
   ObjectsDeleteAll(0, nm);
   int s = live ? sg.cur  : sg.segS[k];
   int e = live ? sg.done : sg.segE[k];
   if(e < s) return;
   SChan ch;
   Chan(s, e, live ? LAB_AUTO : sg.segLab[k], sg.minBars, high, low, close, ch);
   if(live && !htf) gLive = ch;

   ENUM_TIMEFRAMES tf = htf ? gHtf : _Period;
   int proj = live ? (htf ? InpHTFProject : InpProjectBars) : 0;
   int xEnd = e - s + proj;                    // live: carry the lines proj candles to the right
   datetime t1 = time[s];
   datetime t2 = time[e] + (datetime)(proj * PeriodSeconds(tf));
   if(t2 <= t1) t2 = t1 + PeriodSeconds(tf);

   bool faded = InpFadeWeak && !ch.strong && ch.lab != LAB_FORMING;
   color c = LabelColor(ch.lab);
   color lc = faded ? Shade(c, 55) : c;
   int style = live ? STYLE_DASH : STYLE_SOLID;
   int width = InpLineWidth + (htf ? 1 : 0);
   string tip = (htf ? TFName(tf) + " " : "") + LabelName(ch.lab) + (live ? " (live, can still change)" : "") + ", " +
                IntegerToString(ch.n) + " candles from " + TimeToString(time[s]) + ", line " + (ch.b >= 0 ? "+" : "") +
                DoubleToString(ch.b * (ch.n - 1), _Digits) + ", high " + DoubleToString(ch.hh, _Digits) + ", low " +
                DoubleToString(ch.ll, _Digits) + "; " + ChanText(ch, e - s);

   double u1 = ChUpper(ch, 0), u2 = ChUpper(ch, xEnd);
   double l1 = ChLower(ch, 0), l2 = ChLower(ch, xEnd);
   if(InpFill && !htf)
   {
      color f = Shade(c, faded ? InpFillPct * 0.45 : InpFillPct);
      Triangle(nm + "F1", t1, u1, t2, u2, t2, l2, f, tip);
      Triangle(nm + "F2", t1, u1, t1, l1, t2, l2, f, tip);
   }
   Line(nm + "U", t1, u1, t2, u2, lc, style, width, tip);
   Line(nm + "L", t1, l1, t2, l2, lc, style, width, tip);
   if(InpMidLine && !htf) Line(nm + "M", t1, (u1 + l1) / 2, t2, (u2 + l2) / 2, lc, STYLE_DOT, 1, tip);
   if(InpLabels)
   {
      string tn = nm + "T";
      if(ObjectCreate(0, tn, OBJ_TEXT, 0, t1, u1))
      {
         ObjectSetString(0, tn, OBJPROP_TEXT, (htf ? TFName(tf) + " " : "") + ShortName(ch.lab) + (live ? " (live)" : ""));
         ObjectSetString(0, tn, OBJPROP_FONT, htf ? "Arial Bold" : "Arial");
         ObjectSetInteger(0, tn, OBJPROP_FONTSIZE, InpFontSize);
         ObjectSetInteger(0, tn, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
         Style(tn, lc, STYLE_SOLID, 1, false, tip);
      }
   }
}

void DrawBreak(const int k, const DynArr<datetime> &time, const DynArr<double> &high, const DynArr<double> &low)
{
   if(!InpArrows) return;
   string nm = gP + "B" + IntegerToString(k);
   int t = gM.brkT[k];
   bool upB = gM.brkD[k] > 0;
   if(!ObjectCreate(0, nm, upB ? OBJ_ARROW_UP : OBJ_ARROW_DOWN, 0, time[t], upB ? low[t] : high[t])) return;
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, upB ? ANCHOR_TOP : ANCHOR_BOTTOM);
   string dir = upB ? "up" : "down";
   Style(nm, upB ? InpUpColor : InpDnColor, STYLE_SOLID, 1, false,
         "Break " + dir + " confirmed at the close of " + TimeToString(time[t]) + "; everything before the new stretch is now fixed");
}

string MainStatus(const DynArr<datetime> &time)
{
   return TFName(_Period) + ": " + LabelName(gLive.lab) + " (live, can still change) since " + TimeToString(time[gM.cur]) + ", " +
          IntegerToString(gLive.n) + " candles, " + ChanText(gLive, gM.done - gM.cur);
}

void StatusLine(const string nm, const int row, const string txt)
{
   ObjectDelete(0, nm);
   if(!InpStatus || txt == "") return;
   if(!ObjectCreate(0, nm, OBJ_LABEL, 0, 0, 0)) return;
   ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_RIGHT_LOWER);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_RIGHT_LOWER);
   ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, 10 + row * (InpFontSize * 2 + 4));
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetString(0, nm, OBJPROP_FONT, "Arial");
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, InpFontSize);
   Style(nm, InpTextColor, STYLE_SOLID, 1, false, txt);
}

void DrawStatus()
{
   StatusLine(gP + "Txt0", 0, gTxtMain);
   StatusLine(gP + "Txt1", 1, gTxtHTF);
}

//+------------------------------------------------------------------+
//| Alerts                                                           |
//+------------------------------------------------------------------+
void Notify(const string msg)
{
   string full = _Symbol + " " + TFName(_Period) + ": " + msg;
   Alert(full);
   if(InpPush) SendNotification(full);
}

// Price reaching the live channel's upper or lower line, at most once per candle per line
void CheckTouch(const datetime barTime, const double price, const int bar)
{
   if(!InpAlertTouch || gLive.lab == LAB_FORMING || gLive.n < 2 || bar <= gM.cur) return;
   double x = bar - gM.cur;
   double u = ChUpper(gLive, x), l = ChLower(gLive, x);
   double zone = InpAlertPct / 100.0 * (u - l);
   string what = LabelName(gLive.lab) + (gLive.flat ? " box" : " channel");
   if(price >= u - zone && gTouchUp != barTime)
   {
      gTouchUp = barTime;
      Notify("price " + DoubleToString(price, _Digits) + " at the upper line (" + DoubleToString(u, _Digits) + ") of the live " + what);
   }
   if(price <= l + zone && gTouchDn != barTime)
   {
      gTouchDn = barTime;
      Notify("price " + DoubleToString(price, _Digits) + " at the lower line (" + DoubleToString(l, _Digits) + ") of the live " + what);
   }
}
//+------------------------------------------------------------------+
