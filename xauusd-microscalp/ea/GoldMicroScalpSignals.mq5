//+------------------------------------------------------------------+
//| GoldMicroScalpSignals.mq5                                         |
//| Shows every signal GoldMicroScalp.mq5 would act on, on an M1      |
//| chart, using exactly the same rules, filters and entry hours:     |
//|   PB (blue)   pullback candle, trade with the H1 trend            |
//|   SF (orange) spike fade                                          |
//|   QB (violet) quarter-hour break fade                             |
//|   CP (grey)   the enabled textbook candle patterns (label = which)|
//| v1.30 filters, as in the EA: session window (15:00-19:00 server), |
//| minimum candle body for PB and CP, CP pattern selection, optional |
//| M5 alignment, and the spread limit (50% of the take profit). For  |
//| past bars the spread check uses the spread MT5 recorded on the    |
//| entry bar, which can differ from the live spread the EA sees; a   |
//| recorded spread of 0 (older history) is treated as unknown.       |
//| Not shown: the EA's daily loss stop and position caps.            |
//| Arrow under the candle = buy, over = sell, at the M1 bar whose    |
//| close triggers the trade (the EA enters on the next bar's first   |
//| tick). Bottom-left panel: H1 trend, live spread and its limit,    |
//| session state, today's signal count per module, signals skipped   |
//| for spread, and the spread the signals would pay. It can share a  |
//| chart with the EA, whose panel is top-left.                       |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.30"
#property indicator_chart_window
#property indicator_buffers 6
#property indicator_plots   2
#property indicator_label1  "Buy signal"
#property indicator_type1   DRAW_COLOR_ARROW
#property indicator_color1  clrDodgerBlue, clrOrange, clrViolet, clrDarkGray
#property indicator_width1  2
#property indicator_label2  "Sell signal"
#property indicator_type2   DRAW_COLOR_ARROW
#property indicator_color2  clrDodgerBlue, clrOrange, clrViolet, clrDarkGray
#property indicator_width2  2

enum ENUM_M5_ALIGN
{
   M5_OFF    = 0,                       // Off
   M5_CANDLE = 1,                       // Last closed M5 candle closed in the trade's direction
   M5_EMA    = 2                        // M5 EMA rose (buys) / fell (sells) over the last closed M5 candle
};

input group "Signals (same settings as the EA)"
input bool   InpPB          = true;     // Show PB: pullback candle
input int    InpPBMinutes   = 2;        // PB candle length in minutes
input double InpPBBodyMult  = 1.0;      // PB body vs average body of last 20 candles
input double InpPBMaru      = 0.9;      // PB body share of range
input double InpPBMinBody   = 0.8;      // PB body vs average RANGE of last 20 candles (0 = off)
input bool   InpSF          = true;     // Show SF: spike fade
input double InpSFMult      = 3.0;      // SF spike vs average 1-min range
input bool   InpQB          = true;     // Show QB: quarter-hour break fade
input double InpQBK         = 0.1;      // QB break size vs average 15-min range
input int    InpQBFromHour  = 15;       // QB from server hour
input int    InpQBToHour    = 19;       // QB to server hour (the session window ends at 19:00 by default)
input bool   InpCP          = true;     // Show CP: textbook candle patterns
input bool   InpCPTrend     = true;     // CP only with the H1 trend
input double InpCPMinBody   = 0.5;      // CP last candle's body vs average range of last 20 M1 bars (0 = off)
input bool   InpCPEngulf    = true;     // CP pattern: bullish / bearish engulfing
input bool   InpCPStar      = true;     // CP pattern: morning / evening star
input bool   InpCPThree     = true;     // CP pattern: three white soldiers / three black crows
input bool   InpCPHammer    = false;    // CP pattern: hammer / hanging man
input bool   InpCPInvHammer = false;    // CP pattern: inverted hammer / shooting star
input bool   InpCPHarami    = false;    // CP pattern: bullish / bearish harami
input bool   InpCPPiercing  = false;    // CP pattern: piercing line / dark cloud cover
input bool   InpCPDoji      = false;    // CP pattern: doji after a fall / rise

input group "Entry filters (same settings as the EA)"
input string InpFirstEntry  = "01:05";  // Mark only what the EA can trade: from (server time, signal bar open)
input string InpLastEntry   = "22:29";  // ... to (server time, signal bar open)
input bool   InpSessionOn   = true;     // Session window on
input string InpSessionFrom = "15:00";  // Session start, server time (15:00 on a GMT+3 server = London/New York overlap)
input string InpSessionTo   = "19:00";  // Session end, server time: no signals from bars opening at or after this minute
input ENUM_M5_ALIGN InpM5Align = M5_OFF;// M5 alignment for PB and CP
input int    InpM5EMA       = 9;        // M5 EMA period (EMA option)
input bool   InpM5Fades     = false;    // Apply the M5 alignment to SF and QB too
input double InpMaxSpreadPctTP = 50;    // Spread limit, % of the module's take profit (0 = off)
input int    InpMaxSpreadPts= 50;       // Spread limit in points (0 = off)
input double InpPBTP        = 0.25;     // PB take profit $ (for the spread limit)
input double InpSFTP        = 0.25;     // SF take profit $ (for the spread limit)
input double InpQBTP        = 0.25;     // QB take profit $ (for the spread limit)
input double InpCPTP        = 0.25;     // CP take profit $ (for the spread limit)
input bool   InpHistSpread  = true;     // Hide past signals whose entry bar's recorded spread was over the limit

input group "Display"
input int    InpBars        = 3000;     // Mark this many recent bars
input bool   InpLabels      = true;     // Write the module name next to each arrow
input bool   InpAlerts      = false;    // Alert on a new signal

double BuyBuf[], BuyClr[], SellBuf[], SellClr[];
double MaskBuf[], SkipBuf[];           // per bar: modules marked (bit m = buy, bit 4+m = sell), signals the spread limit skipped
int    hFast = INVALID_HANDLE, hSlow = INVALID_HANDLE, hM5 = INVALID_HANDLE;
string PFX = "GMSS_";
datetime lastAlert = 0;
int    firstTod = 65, lastTod = 1349, sessFrom = 900, sessTo = 1140;
bool   gDrawn = false;

//+------------------------------------------------------------------+
//| Micro-scalp signal modules (same rules as ea_replica.py).         |
//| r[] is a series-ordered M1 array (r[k+1] is older than r[k]).     |
//| r[i] is the CLOSED M1 bar being evaluated; total = ArraySize(r). |
//| Each returns +1 buy, -1 sell, 0 nothing.                          |
//+------------------------------------------------------------------+
#define MOD_PB 0
#define MOD_SF 1
#define MOD_QB 2
#define MOD_CP 3
#define NMOD   4
string ModName[NMOD]  = {"Pullback candle", "Spike fade", "Quarter-hour fade", "Candle patterns"};
string ModShort[NMOD] = {"PB", "SF", "QB", "CP"};

// PB: the n-minute candle (clock-aligned) that r[i] completes is a strong candle
// (body >= k x average body of the previous 20 such candles, >= maru x its range and
// >= minBody x the average range of the previous 20 such candles)
// running AGAINST the H1 trend -> enter WITH the H1 trend.
int SigPullback(const MqlRates &r[], int i, int total, int n, double k, double maru, double minBody, int trend)
{
   if(trend == 0 || n < 1) return 0;
   long sec = (long)n * 60;
   long t = (long)r[i].time;
   if((t + 60) % sec != 0) return 0;                 // r[i] is not the last minute of an n-minute candle
   double co[21], cc[21], ch[21], cl[21];
   int nc = 0; long key = -1;
   for(int j = i; j < total; j++)
   {
      long kj = (long)r[j].time - ((long)r[j].time % sec);
      if(kj != key)
      {
         if(nc == 21) break;
         key = kj;
         cc[nc] = r[j].close; ch[nc] = r[j].high; cl[nc] = r[j].low; co[nc] = r[j].open;
         nc++;
      }
      else
      {
         ch[nc-1] = MathMax(ch[nc-1], r[j].high);
         cl[nc-1] = MathMin(cl[nc-1], r[j].low);
         co[nc-1] = r[j].open;                         // older bar: its open becomes the candle open
      }
   }
   if(nc < 21) return 0;
   double body0 = MathAbs(cc[0] - co[0]), rng0 = ch[0] - cl[0];
   if(rng0 <= 0) return 0;
   double avg = 0, avgR = 0;
   for(int c = 1; c <= 20; c++) { avg += MathAbs(cc[c] - co[c]); avgR += ch[c] - cl[c]; }
   avg /= 20.0; avgR /= 20.0;
   if(body0 >= k * avg && body0 >= maru * rng0 && body0 >= minBody * avgR)
   {
      int dir = cc[0] > co[0] ? -1 : (cc[0] < co[0] ? 1 : 0);
      return dir == trend ? dir : 0;
   }
   return 0;
}

// SF: one-bar move bigger than mult x the average M1 range of the last 240 bars (this one included),
// moving further away from the session VWAP on its own side -> fade it.
int SigSpikeFade(const MqlRates &r[], int i, int total, double mult, double vwap)
{
   if(i + 240 >= total || vwap <= 0) return 0;
   double atr = 0;
   for(int j = i; j < i + 240; j++) atr += r[j].high - r[j].low;
   atr /= 240.0;
   double r1 = r[i].close - r[i+1].close;
   if(r1 > mult * atr && r[i].close > vwap) return -1;
   if(r1 < -mult * atr && r[i].close < vwap) return 1;
   return 0;
}

// QB: r[i] is the first M1 bar of a new 15-minute candle, server hour h0..h1, and it closes more than
// k x (average range of the last 12 fifteen-minute candles) beyond the previous candle's high/low -> fade.
int SigQuarterFade(const MqlRates &r[], int i, int total, double k, int h0, int h1)
{
   long t = (long)r[i].time;
   if(t % 900 != 0) return 0;
   MqlDateTime s; TimeToStruct(r[i].time, s);
   if(s.hour < h0 || s.hour > h1) return 0;
   double qh[12], ql[12];
   long qk[12];
   int nq = 0; long key = -1;
   for(int j = i + 1; j < total; j++)
   {
      long kj = (long)r[j].time - ((long)r[j].time % 900);
      if(kj != key)
      {
         if(nq == 12) break;
         key = kj; qk[nq] = kj; qh[nq] = r[j].high; ql[nq] = r[j].low; nq++;
      }
      else
      {
         qh[nq-1] = MathMax(qh[nq-1], r[j].high);
         ql[nq-1] = MathMin(ql[nq-1], r[j].low);
      }
   }
   if(nq < 12 || qk[0] != t - 900) return 0;          // the previous candle must have just closed
   double ar = 0;
   for(int q = 0; q < 12; q++) ar += qh[q] - ql[q];
   ar /= 12.0;
   if(r[i].close > qh[0] + k * ar) return -1;
   if(r[i].close < ql[0] - k * ar) return 1;
   return 0;
}

// Session VWAP of the calendar day of r[i]: sum(typical x tick volume) / sum(tick volume), bars up to r[i].
double SessionVWAP(const MqlRates &r[], int i, int total)
{
   MqlDateTime s; TimeToStruct(r[i].time, s);
   datetime dayStart = r[i].time - (s.hour * 3600 + s.min * 60 + s.sec);
   double pv = 0, v = 0;
   for(int j = i; j < total && r[j].time >= dayStart; j++)
   {
      double tv = (double)r[j].tick_volume;
      pv += (r[j].high + r[j].low + r[j].close) / 3.0 * tv;
      v += tv;
   }
   return v > 0 ? pv / v : 0;
}

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

bool cpOn[NPAT];                        // patterns CP trades (set in OnInit from the pattern inputs)

// CP: net vote of the ENABLED patterns completed at bar i (+1, -1 or 0), only if bar i's body is at least
// minBody x the average range of the 20 bars before it, and (useTrend) only with the H1 trend.
// 'name' gets the short names of the enabled patterns that fired.
int CPVote(const MqlRates &r[], int i, int trend, bool useTrend, const bool &enabled[], double minBody, string &name)
{
   name = "";
   bool hit[NPAT];
   DetectPatterns(r, i, hit);
   int v = 0;
   for(int p = 0; p < NPAT; p++)
      if(hit[p] && enabled[p])
      {
         v += PatDir[p];
         name += (name == "" ? "" : ",") + PatShort[p];
      }
   int dir = v > 0 ? 1 : (v < 0 ? -1 : 0);
   if(dir == 0) return 0;
   if(minBody > 0)
   {
      double avgR = 0;
      for(int k = 1; k <= 20; k++) avgR += r[i + k].high - r[i + k].low;
      avgR /= 20.0;
      if(PBody(r, i) < minBody * avgR) return 0;
   }
   if(useTrend && dir != trend) return 0;
   return dir;
}

// Signal bar opening at minute-of-day tod is inside the session window (wraps past midnight if from > to)
bool InSession(int tod)
{
   if(!InpSessionOn) return true;
   if(sessFrom <= sessTo) return tod >= sessFrom && tod < sessTo;
   return tod >= sessFrom || tod < sessTo;
}

// Direction of the last M5 candle that had closed by time t: +1 up, -1 down, 0 flat or unknown (same as the EA).
// M5_CANDLE: its close vs its open. M5_EMA: the M5 EMA at its close vs one candle earlier.
int M5Dir(datetime t)
{
   int sh = iBarShift(_Symbol, PERIOD_M5, t - 1, false);       // M5 bar holding the second before t
   if(sh < 0) return 0;
   if(iTime(_Symbol, PERIOD_M5, sh) + 300 > t) sh++;           // still open at t: use the one before
   if(InpM5Align == M5_CANDLE)
   {
      double o = iOpen(_Symbol, PERIOD_M5, sh), c = iClose(_Symbol, PERIOD_M5, sh);
      if(o <= 0 || c <= 0) return 0;
      return c > o ? 1 : (c < o ? -1 : 0);
   }
   double e[2];
   datetime t5 = iTime(_Symbol, PERIOD_M5, sh);
   if(hM5 == INVALID_HANDLE || t5 == 0 || CopyBuffer(hM5, 0, t5, 2, e) != 2) return 0;   // by time: e[0] = one candle earlier, e[1] = that candle
   return e[1] > e[0] ? 1 : (e[1] < e[0] ? -1 : 0);
}

int ParseTod(string s)
{
   string p[];
   if(StringSplit(s, ':', p) != 2) return -1;
   return (int)StringToInteger(p[0]) * 60 + (int)StringToInteger(p[1]);
}

color ModColor(int m) { return m == MOD_PB ? clrDodgerBlue : (m == MOD_SF ? clrOrange : (m == MOD_QB ? clrViolet : clrDarkGray)); }

//+------------------------------------------------------------------+
int OnInit()
{
   SetIndexBuffer(0, BuyBuf, INDICATOR_DATA);
   SetIndexBuffer(1, BuyClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(2, SellBuf, INDICATOR_DATA);
   SetIndexBuffer(3, SellClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(4, MaskBuf, INDICATOR_CALCULATIONS);
   SetIndexBuffer(5, SkipBuf, INDICATOR_CALCULATIONS);
   PlotIndexSetInteger(0, PLOT_ARROW, 233);
   PlotIndexSetInteger(1, PLOT_ARROW, 234);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   ArraySetAsSeries(BuyBuf, true); ArraySetAsSeries(BuyClr, true);
   ArraySetAsSeries(SellBuf, true); ArraySetAsSeries(SellClr, true);
   ArraySetAsSeries(MaskBuf, true); ArraySetAsSeries(SkipBuf, true);
   hFast = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   hSlow = iMA(_Symbol, PERIOD_H1, 80, 0, MODE_EMA, PRICE_CLOSE);
   if(hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE) return INIT_FAILED;
   if(InpPB && (InpPBMinutes < 1 || InpPBMinutes > 60 || 1440 % InpPBMinutes != 0))
   {
      Print("PB: candle length must divide a day and be 1-60 minutes (1, 2, 3, 5, 10, 15, 30, 60...) to match the tests");
      return INIT_PARAMETERS_INCORRECT;
   }
   firstTod = ParseTod(InpFirstEntry); lastTod = ParseTod(InpLastEntry);
   sessFrom = ParseTod(InpSessionFrom); sessTo = ParseTod(InpSessionTo);
   if(firstTod < 0 || lastTod < 0 || sessFrom < 0 || sessTo < 0 || sessFrom > 1440 || sessTo > 1440)
   {
      Print("Times must look like 01:05");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(sessFrom == 1440) sessFrom = 0;                              // a start of 24:00 is midnight
   if(InpSessionOn && sessFrom == sessTo) Print("Session start and end are the same time: the EA refuses this, so nothing is marked");
   // pattern pairs in PatName[] order: bullish at 2k, bearish at 2k+1
   cpOn[0]  = InpCPHammer;    cpOn[1]  = InpCPHammer;
   cpOn[2]  = InpCPInvHammer; cpOn[3]  = InpCPInvHammer;
   cpOn[4]  = InpCPEngulf;    cpOn[5]  = InpCPEngulf;
   cpOn[6]  = InpCPHarami;    cpOn[7]  = InpCPHarami;
   cpOn[8]  = InpCPPiercing;  cpOn[9]  = InpCPPiercing;
   cpOn[10] = InpCPStar;      cpOn[11] = InpCPStar;
   cpOn[12] = InpCPThree;     cpOn[13] = InpCPThree;
   cpOn[14] = InpCPDoji;      cpOn[15] = InpCPDoji;
   if(InpM5Align == M5_EMA)
   {
      hM5 = iMA(_Symbol, PERIOD_M5, InpM5EMA < 1 ? 1 : InpM5EMA, 0, MODE_EMA, PRICE_CLOSE);
      if(hM5 == INVALID_HANDLE) return INIT_FAILED;
   }
   IndicatorSetString(INDICATOR_SHORTNAME, "Gold Micro Scalp Signals");
   if(_Period != PERIOD_M1) Print("Gold Micro Scalp Signals: put this on an M1 chart; the EA's signals are M1 bars.");
   EventSetTimer(1);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, PFX);
   if(hFast != INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow != INVALID_HANDLE) IndicatorRelease(hSlow);
   if(hM5 != INVALID_HANDLE) IndicatorRelease(hM5);
}

// True once every average this indicator reads has been calculated
bool HandlesReady()
{
   if(BarsCalculated(hFast) <= 0 || BarsCalculated(hSlow) <= 0) return false;
   if(InpM5Align == M5_CANDLE && (Bars(_Symbol, PERIOD_M5) <= 0 || iTime(_Symbol, PERIOD_M5, 0) == 0)) return false;   // M5 history still building
   return hM5 == INVALID_HANDLE || BarsCalculated(hM5) > 0;
}

// The H1 averages are often still calculating on the first pass, which then draws nothing. On a quiet or
// closed market no tick comes to retry, so ask the chart to recalculate once they are ready.
void OnTimer()
{
   if(gDrawn || _Period != PERIOD_M1 || Bars(_Symbol, PERIOD_M1) < 1700) return;   // nothing to draw on this chart yet
   if(HandlesReady()) ChartSetSymbolPeriod(0, _Symbol, _Period);
}

// Spread limit for module m in price units ($ per 0.01 lot), 0 = no % limit
double SpreadLimit(int m)
{
   if(InpMaxSpreadPctTP <= 0) return 0;
   double tp = m == MOD_PB ? InpPBTP : (m == MOD_SF ? InpSFTP : (m == MOD_QB ? InpQBTP : InpCPTP));
   return InpMaxSpreadPctTP / 100.0 * tp;
}

// The EA would skip module m's entry at spread s (price units) or sPts (points)
bool SpreadTooWide(int m, double s, long sPts)
{
   if(InpMaxSpreadPts > 0 && sPts > InpMaxSpreadPts) return true;
   double l = SpreadLimit(m);
   return l > 0 && s > l + _Point * 0.001;                      // as the EA: a $0.125 limit passes 12 points, not 13
}

// H1 EMA20 vs EMA80 on the last H1 bar that had CLOSED by time t (same bar the EA reads)
int TrendAt(datetime t)
{
   int sh = iBarShift(_Symbol, PERIOD_H1, t - 1, false);      // H1 bar holding the second before t
   if(sh < 0) return 0;
   if(iTime(_Symbol, PERIOD_H1, sh) + 3600 > t) sh++;         // still open at t: use the one before
   double f[1], s[1];
   if(CopyBuffer(hFast, 0, sh, 1, f) != 1 || CopyBuffer(hSlow, 0, sh, 1, s) != 1) return 0;
   return f[0] > s[0] ? 1 : (f[0] < s[0] ? -1 : 0);
}

// One line of the panel, bottom-left corner (the EA writes its own panel top-left)
void PanelLine(int line, string text)
{
   string name = PFX + "panel" + IntegerToString(line);
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_LOWER);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 8);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 20 + 15 * (5 - line));   // six lines, line 0 on top
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, name, OBJPROP_COLOR, (color)ChartGetInteger(0, CHART_COLOR_FOREGROUND));
   ObjectSetString(0, name, OBJPROP_TEXT, text);
}

void Label(datetime t, double price, string text, color clr, bool above)
{
   string name = PFX + IntegerToString((long)t) + (above ? "s" : "b");
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
   if(_Period != PERIOD_M1 || rates_total < 1700) return 0;
   if(!HandlesReady()) { gDrawn = false; return 0; }           // the timer retries
   ArraySetAsSeries(time, true); ArraySetAsSeries(open, true); ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true); ArraySetAsSeries(close, true); ArraySetAsSeries(tick_volume, true);
   ArraySetAsSeries(spread, true);

   int limit;
   if(prev_calculated <= 0)
   {
      ArrayInitialize(BuyBuf, EMPTY_VALUE); ArrayInitialize(SellBuf, EMPTY_VALUE);
      ArrayInitialize(BuyClr, 0); ArrayInitialize(SellClr, 0); ArrayInitialize(MaskBuf, 0); ArrayInitialize(SkipBuf, 0);
      ObjectsDeleteAll(0, PFX);
      limit = MathMin(InpBars, rates_total - 1600);
   }
   else
   {
      if(rates_total == prev_calculated) { BuyBuf[0] = EMPTY_VALUE; SellBuf[0] = EMPTY_VALUE; return rates_total; }
      limit = MathMin(rates_total - prev_calculated + 1, rates_total - 1600);
   }
   BuyBuf[0] = EMPTY_VALUE; SellBuf[0] = EMPTY_VALUE; MaskBuf[0] = 0; SkipBuf[0] = 0;   // the forming bar is never marked

   int need = limit + 1500;
   MqlRates r[];
   ArrayResize(r, need);
   for(int k = 0; k < need; k++)
   {
      r[k].time = time[k]; r[k].open = open[k]; r[k].high = high[k]; r[k].low = low[k]; r[k].close = close[k];
      r[k].tick_volume = tick_volume[k];
   }
   bool on[NMOD];
   on[MOD_PB] = InpPB; on[MOD_SF] = InpSF; on[MOD_QB] = InpQB; on[MOD_CP] = InpCP;

   for(int i = limit; i >= 1; i--)
   {
      BuyBuf[i] = EMPTY_VALUE; SellBuf[i] = EMPTY_VALUE; MaskBuf[i] = 0; SkipBuf[i] = 0;
      if(prev_calculated > 0)                                      // a recalculated bar loses its old labels
      {
         ObjectDelete(0, PFX + IntegerToString((long)time[i]) + "b");
         ObjectDelete(0, PFX + IntegerToString((long)time[i]) + "s");
      }
      int tod = (int)(((long)time[i] % 86400) / 60);
      if(tod < firstTod || tod > lastTod || !InSession(tod) || time[i-1] - time[i] > 60) continue;   // the EA would not enter on this bar
      int trend = TrendAt(time[i] + 60);
      int sig[NMOD];
      string cpName = "";
      sig[MOD_PB] = InpPB ? SigPullback(r, i, need, InpPBMinutes, InpPBBodyMult, InpPBMaru, InpPBMinBody, trend) : 0;
      sig[MOD_SF] = InpSF ? SigSpikeFade(r, i, need, InpSFMult, SessionVWAP(r, i, need)) : 0;
      sig[MOD_QB] = InpQB ? SigQuarterFade(r, i, need, InpQBK, InpQBFromHour, InpQBToHour) : 0;
      sig[MOD_CP] = InpCP ? CPVote(r, i, trend, InpCPTrend, cpOn, InpCPMinBody, cpName) : 0;
      if(InpM5Align != M5_OFF)                                     // optional M5 alignment, as in the EA
      {
         int d5 = M5Dir(time[i] + 60);
         for(int m = 0; m < NMOD; m++)
            if(sig[m] != 0 && (m == MOD_PB || m == MOD_CP || InpM5Fades) && sig[m] != d5) sig[m] = 0;
      }
      if(InpHistSpread && spread[i-1] > 0)                         // spread recorded on the entry bar (i-1) vs the EA's limit (0 = not recorded)
         for(int m = 0; m < NMOD; m++)
            if(sig[m] != 0 && SpreadTooWide(m, spread[i-1] * _Point, spread[i-1])) { sig[m] = 0; SkipBuf[i]++; }
      double off = (high[i] - low[i]) * 0.3 + 20 * _Point;
      string bTxt = "", sTxt = ""; int bMod = -1, sMod = -1; int mask = 0;
      for(int m = 0; m < NMOD; m++)
      {
         string nm = ModShort[m] + (m == MOD_CP && cpName != "" ? ":" + cpName : "");
         if(sig[m] == 1)  { bTxt += (bTxt == "" ? "" : "+") + nm; if(bMod < 0) bMod = m; mask |= 1 << m; }
         if(sig[m] == -1) { sTxt += (sTxt == "" ? "" : "+") + nm; if(sMod < 0) sMod = m; mask |= 1 << (4 + m); }
      }
      MaskBuf[i] = mask;
      if(bMod >= 0)
      {
         BuyBuf[i] = low[i] - off; BuyClr[i] = bMod;
         if(InpLabels) Label(time[i], low[i] - 2.5 * off, bTxt, ModColor(bMod), false);
      }
      if(sMod >= 0)
      {
         SellBuf[i] = high[i] + off; SellClr[i] = sMod;
         if(InpLabels) Label(time[i], high[i] + 2.5 * off, sTxt, ModColor(sMod), true);
      }
      if(i == 1 && InpAlerts && prev_calculated > 0 && lastAlert != time[1] && (bMod >= 0 || sMod >= 0))
      {
         lastAlert = time[1];
         Alert(_Symbol, " M1: ", bMod >= 0 ? "BUY " + bTxt : "", sMod >= 0 ? " SELL " + sTxt : "");
      }
   }

   // panel: today's signals, the ones the spread limit skipped, and the spread the signals would pay
   MqlDateTime s; TimeToStruct(time[0], s);
   datetime dayStart = time[0] - (s.hour * 3600 + s.min * 60 + s.sec);
   int cnt[NMOD]; ArrayInitialize(cnt, 0); int all = 0, skipped = 0;
   for(int i = 1; i < rates_total && time[i] >= dayStart; i++)
   {
      int mask = (int)MaskBuf[i];
      for(int m = 0; m < NMOD; m++)
      {
         if((mask & (1 << m)) != 0)       { cnt[m]++; all++; }
         if((mask & (1 << (4 + m))) != 0) { cnt[m]++; all++; }
      }
      skipped += (int)SkipBuf[i];
   }
   double spr = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   long   sprPts = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   int tNow = TrendAt(TimeCurrent());
   double cs = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE) * 0.01;   // $ per $1 move at 0.01 lot
   string sigs = "Today's signals:";
   for(int m = 0; m < NMOD; m++) if(on[m]) sigs += StringFormat("  %s %d", ModShort[m], cnt[m]);
   string lim = ""; bool wide = false, same = true; double l0 = -1;
   for(int m = 0; m < NMOD; m++)
      if(on[m])
      {
         double l = SpreadLimit(m) * cs;
         if(l > 0) lim += StringFormat("%s %s $%.3f", lim == "" ? "" : ",", ModShort[m], l);
         if(l0 < 0) l0 = l; else if(MathAbs(l - l0) > 1e-9) same = false;
         if(SpreadTooWide(m, spr, sprPts)) wide = true;
      }
   if(same && l0 > 0) lim = StringFormat(" $%.3f", l0);
   int todNow = (int)(((long)TimeCurrent() % 86400) / 60);
   PanelLine(0, "Gold Micro Scalp Signals");
   PanelLine(1, "H1 trend: " + (tNow == 1 ? "UP" : (tNow == -1 ? "DOWN" : "-")) + StringFormat("   Spread now: $%.2f per 0.01 lot", spr * cs)
                + (wide ? "   TOO WIDE: the EA skips entries" : ""));
   string ptsTxt = InpMaxSpreadPts > 0 ? StringFormat("%d points", InpMaxSpreadPts) : "";
   PanelLine(2, (lim == "" ? "Spread limit: " + (ptsTxt == "" ? "off" : ptsTxt)
                           : StringFormat("Spread limit (%.0f%% of TP):", InpMaxSpreadPctTP) + lim + (ptsTxt == "" ? "" : ", " + ptsTxt))
                + (InpSessionOn ? "   Session " + InpSessionFrom + "-" + InpSessionTo + (InSession(todNow) ? " open" : " closed") : ""));
   PanelLine(3, sigs);
   PanelLine(4, StringFormat("Skipped for spread today: %d%s", skipped, InpHistSpread ? " (recorded spread)" : " (check off)"));
   PanelLine(5, StringFormat("Spread those trades pay at today's spread: about $%.2f", all * spr * cs));
   gDrawn = true;
   return rates_total;
}
//+------------------------------------------------------------------+
