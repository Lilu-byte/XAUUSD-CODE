//+------------------------------------------------------------------+
//| GoldMicroScalp.mq5                                                |
//| Many small XAUUSD trades from M1 candle signals. No limit on the  |
//| number of trades a day; several positions can be open at once.    |
//| Four signal modules, each with its own target, stop, holding time |
//| and position cap:                                                 |
//|   PB  Pullback candle   strong 2-min candle against the H1 trend  |
//|                         -> trade WITH the trend                   |
//|   SF  Spike fade        1-min spike > 3x average range away from  |
//|                         the day's VWAP -> fade it                 |
//|   QB  Quarter-hour fade first minute of a 15-min candle breaks    |
//|                         the previous one (15:00-19:59, 15:00-18:59|
//|                         with the default session window) -> fade  |
//|   CP  Candle patterns   the strongest textbook patterns on M1     |
//|                         (engulfing, stars, three soldiers/crows)  |
//| v1.30 exits: take profit $0.25 per 0.01 lot, first stop $0.60     |
//| beyond the spread, and once a trade is +$0.08 its stop trails     |
//| $0.04 behind the best price (buys and sells).                     |
//| v1.30 filters: entries only 15:00-19:00 server time (the London/  |
//| New York overlap on this GMT+3 server), only while the spread is  |
//| at most 50% of the take profit, candle bodies at least 0.8 (PB)   |
//| and 0.5 (CP) of the average range, only the strongest CP patterns.|
//| NOTE: earlier tests of small targets on these signals, without    |
//| filters, lost money after the spread (M1, Sep-Oct 2026, not used  |
//| for tuning: $0.50-1 targets lost about $3.90 a day for PB+SF+QB;  |
//| $0.10 targets lost about $0.23 a trade and hit the $15 daily stop |
//| every day). This version puts selectivity, spread rejection and a |
//| trailing stop first: fewer trades, each paying less spread, and   |
//| the stop follows price so a clear reversal exits once in profit.  |
//| The first stop is wider than the target on purpose, so the spread |
//| and normal noise don't stop trades out the moment they open.      |
//| Estimate for v1.30 on the test weeks: about -$0.11 a trade, about |
//| 7 trades a day (-$0.75 a day). The directions beat 96% of random  |
//| ones, but that is worth about $0.04 a trade against about $0.15   |
//| of spread and slippage. Nearly every trade is decided inside its  |
//| first minute, which 1-minute candles can't show: only MT5's real- |
//| tick tester can measure it. DEMO ONLY.                            |
//| See REPORT.md. Defaults and rejection rules: end of this file.    |
//| Attach to one XAUUSD chart (any timeframe), Algo Trading on.      |
//| Needs a HEDGING account (refuses to start on a netting one).      |
//| Strategy Tester: "Every tick based on real ticks" (1-minute OHLC  |
//| can't show a $0.04 trailing stop).                                |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.30"

#include <Trade/Trade.mqh>

#define MOD_PB 0
#define MOD_SF 1
#define MOD_QB 2
#define MOD_CP 3
#define NMOD   4
string ModName[NMOD]  = {"Pullback candle", "Spike fade", "Quarter-hour fade", "Candle patterns"};
string ModShort[NMOD] = {"PB", "SF", "QB", "CP"};

input group "PB: Pullback candle (with the H1 trend)"
input bool   InpPB          = true;     // Use this module
input int    InpPBMinutes   = 2;        // Candle length in minutes (clock-aligned)
input double InpPBBodyMult  = 1.0;      // Body at least this x the average body of the last 20 candles
input double InpPBMaru      = 0.9;      // Body at least this share of the candle's range
input double InpPBMinBody   = 0.8;      // Body at least this x the average RANGE of the last 20 candles (0 = off; below ~0.6 the rules above already imply it)
input double InpPBTP        = 0.25;     // Take profit $ from the entry price (0.01 lot: $1 per $1)
input double InpPBSL        = 0.60;     // First stop $ beyond the spread (at least $0.20, wider than the TP)
input int    InpPBHold      = 20;       // Close after this many minutes
input int    InpPBMax       = 3;        // Max open positions for this module

input group "SF: Spike fade"
input bool   InpSF          = true;     // Use this module
input double InpSFMult      = 3.0;      // Spike at least this x the average 1-min range (240 bars)
input double InpSFTP        = 0.25;     // Take profit $ from the entry price
input double InpSFSL        = 0.60;     // First stop $ beyond the spread (at least $0.20, wider than the TP)
input int    InpSFHold      = 5;        // Close after this many minutes
input int    InpSFMax       = 3;        // Max open positions for this module

input group "QB: Quarter-hour break fade"
input bool   InpQB          = true;     // Use this module
input double InpQBK         = 0.1;      // Break beyond the previous 15-min high/low by k x average 15-min range
input int    InpQBFromHour  = 15;       // From server hour
input int    InpQBToHour    = 19;       // To server hour (inclusive; the session window ends at 19:00 by default)
input double InpQBTP        = 0.25;     // Take profit $ from the entry price
input double InpQBSL        = 0.60;     // First stop $ beyond the spread (at least $0.20, wider than the TP)
input int    InpQBHold      = 5;        // Close after this many minutes
input int    InpQBMax       = 3;        // Max open positions for this module

input group "CP: Textbook candle patterns on M1"
input bool   InpCP          = true;     // Use this module
input bool   InpCPTrend     = true;     // Only with the H1 trend
input double InpCPMinBody   = 0.5;      // Last candle's body at least this x the average range of the last 20 M1 bars (0 = off)
input bool   InpCPEngulf    = true;     // Pattern: bullish / bearish engulfing
input bool   InpCPStar      = true;     // Pattern: morning / evening star
input bool   InpCPThree     = true;     // Pattern: three white soldiers / three black crows
input bool   InpCPHammer    = false;    // Pattern: hammer / hanging man (small body: lower CP minimum body too)
input bool   InpCPInvHammer = false;    // Pattern: inverted hammer / shooting star (small body: lower CP minimum body too)
input bool   InpCPHarami    = false;    // Pattern: bullish / bearish harami (small body: lower CP minimum body too)
input bool   InpCPPiercing  = false;    // Pattern: piercing line / dark cloud cover
input bool   InpCPDoji      = false;    // Pattern: doji after a fall / rise (no body: set CP minimum body to 0)
input double InpCPTP        = 0.25;     // Take profit $ from the entry price
input double InpCPSL        = 0.60;     // First stop $ beyond the spread (at least $0.20, wider than the TP)
input int    InpCPHold      = 5;        // Close after this many minutes
input int    InpCPMax       = 5;        // Max open positions for this module

input group "Trailing stop (all modules)"
input double InpTrailStart  = 0.08;     // Start trailing once a trade is this much in profit, $ (0 = from entry)
input double InpTrailDist   = 0.04;     // Keep the stop this far behind the best price, $ (0 = no trailing)
input double InpTrailStep   = 0.01;     // Move the stop only when it improves by at least this much, $

enum ENUM_M5_ALIGN
{
   M5_OFF    = 0,                       // Off
   M5_CANDLE = 1,                       // Last closed M5 candle closed in the trade's direction
   M5_EMA    = 2                        // M5 EMA rose (buys) / fell (sells) over the last closed M5 candle
};

input group "Entry filters (all modules)"
input bool   InpSessionOn   = true;     // New entries only inside the session window below
input string InpSessionFrom = "15:00";  // Session start, server time (15:00 on this GMT+3 server = 12:00 GMT, London/New York overlap)
input string InpSessionTo   = "19:00";  // Session end, server time: no signals from bars opening at or after this minute
input double InpMaxSpreadPctTP = 50;    // Skip an entry while the spread is above this % of that module's take profit (0 = off)
input ENUM_M5_ALIGN InpM5Align = M5_OFF;// M5 alignment for PB and CP (tested: halves the trades, same result per trade)
input int    InpM5EMA       = 9;        // M5 EMA period (EMA option)
input bool   InpM5Fades     = false;    // Apply the M5 alignment to the fades (SF, QB) too

input group "Account and safety"
input double InpLots        = 0.01;     // Lots per trade
input int    InpMaxOpen     = 12;       // Max open positions in total
input int    InpMaxSpreadPts= 50;       // Skip entries while spread above this (points, 0 = off)
input double InpDailyLoss   = 15.0;     // Stop for the day at this closed loss in $ (0 = off)
input double InpDailyTarget = 0.0;      // Stop for the day at this closed profit in $ (0 = off, unlimited)
input string InpFirstEntry  = "01:05";  // No entries before (server time)
input string InpLastEntry   = "22:29";  // No entries after (server time)
input string InpCloseAll    = "22:58";  // Close everything at (server time)
input long   InpMagic       = 20261020; // Base magic number (module k uses base + k)

CTrade   trade;
int      hFast = INVALID_HANDLE, hSlow = INVALID_HANDLE, hM5 = INVALID_HANDLE;
datetime lastBar = 0;
int      firstTod, lastTod, closeTod, sessFrom, sessTo;
double   modTP[NMOD], modSL[NMOD];
int      modHold[NMOD], modMax[NMOD];
bool     modOn[NMOD];
int      sigCount[NMOD];
int      sprSkips = 0;                  // signals skipped today because the spread was too wide
int      sigDay = -1;

// Stops the EA keeps itself, per position ticket: the stop level, used when the broker took no TP/SL at the
// open or refused to move a trailing stop; the position is then closed at market when price reaches it.
ulong    vTk[];
double   vStop[];

int VFind(ulong tk) { for(int k = ArraySize(vTk) - 1; k >= 0; k--) if(vTk[k] == tk) return k; return -1; }

// Terminal global variable that keeps an EA-kept stop across an EA restart or recompile
string VName(ulong tk) { return "GMS_" + (string)AccountInfoInteger(ACCOUNT_LOGIN) + "_" + (string)tk; }

void VSet(ulong tk, double level)
{
   int k = VFind(tk);
   if(k < 0) { k = ArraySize(vTk); ArrayResize(vTk, k + 1); ArrayResize(vStop, k + 1); vTk[k] = tk; }
   vStop[k] = level;
   GlobalVariableSet(VName(tk), level);
}

// Forget positions that are no longer open (open[] = tickets open now)
void VPrune(const ulong &open[], int nOpen)
{
   int w = 0;
   for(int k = 0; k < ArraySize(vTk); k++)
   {
      bool keep = false;
      for(int j = 0; j < nOpen && !keep; j++) keep = (open[j] == vTk[k]);
      if(!keep) { GlobalVariableDel(VName(vTk[k])); continue; }
      vTk[w] = vTk[k]; vStop[w] = vStop[k]; w++;
   }
   ArrayResize(vTk, w); ArrayResize(vStop, w);
}

// The more protective of two stop levels (0 = none): higher for a buy, lower for a sell
double Tighter(bool isBuy, double a, double b)
{
   if(a == 0) return b;
   if(b == 0) return a;
   return isBuy ? MathMax(a, b) : MathMin(a, b);
}

//+------------------------------------------------------------------+
//| Micro-scalp signal modules (same rules as ea_replica.py).         |
//| r[] is a series-ordered M1 array (r[k+1] is older than r[k]).     |
//| r[i] is the CLOSED M1 bar being evaluated; total = ArraySize(r). |
//| Each returns +1 buy, -1 sell, 0 nothing.                          |
//+------------------------------------------------------------------+

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

//+------------------------------------------------------------------+
int ParseTod(string s)
{
   string p[];
   if(StringSplit(s, ':', p) != 2) return -1;
   return (int)StringToInteger(p[0]) * 60 + (int)StringToInteger(p[1]);
}

// Signal bar opening at minute-of-day tod is inside the session window (wraps past midnight if from > to)
bool InSession(int tod)
{
   if(!InpSessionOn) return true;
   if(sessFrom <= sessTo) return tod >= sessFrom && tod < sessTo;
   return tod >= sessFrom || tod < sessTo;
}

// Direction of the last M5 candle that had closed by time t: +1 up, -1 down, 0 flat or unknown.
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

int OnInit()
{
   firstTod = ParseTod(InpFirstEntry); lastTod = ParseTod(InpLastEntry); closeTod = ParseTod(InpCloseAll);
   sessFrom = ParseTod(InpSessionFrom); sessTo = ParseTod(InpSessionTo);
   if(firstTod < 0 || lastTod < 0 || closeTod < 0 || sessFrom < 0 || sessTo < 0 || sessFrom > 1440 || sessTo > 1440)
   {
      Print("Times must look like 01:05");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(sessFrom == 1440) sessFrom = 0;                              // a start of 24:00 is midnight
   if(InpSessionOn && sessFrom == sessTo)
   {
      Print("Session start and end are the same time: no entries would ever be allowed. Set a window, or switch the session filter off.");
      return INIT_PARAMETERS_INCORRECT;
   }
   bool anyMinute = false;
   for(int t = 0; t < 1440 && !anyMinute; t++) anyMinute = t >= firstTod && t <= lastTod && InSession(t) && t + 1 < closeTod;
   if(!anyMinute)                                                  // (a signal bar at t enters in the minute after it)
   {
      if(InpSessionOn)
         Print("The session window ", InpSessionFrom, "-", InpSessionTo, " doesn't overlap the entry hours ", InpFirstEntry, "-", InpLastEntry,
               " before the ", InpCloseAll, " close-all: no entries would ever be allowed");
      else
         Print("The entry hours ", InpFirstEntry, "-", InpLastEntry, " leave no minute before the ", InpCloseAll,
               " close-all (they can't wrap past midnight): no entries would ever be allowed");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(InpMaxSpreadPctTP < 0 || InpPBMinBody < 0 || InpCPMinBody < 0 || (InpM5Align == M5_EMA && InpM5EMA < 1))
   {
      Print("Spread %, minimum body and M5 EMA period can't be negative (EMA period at least 1)");
      return INIT_PARAMETERS_INCORRECT;
   }
   // pattern pairs in PatName[] order: bullish at 2k, bearish at 2k+1
   cpOn[0]  = InpCPHammer;    cpOn[1]  = InpCPHammer;
   cpOn[2]  = InpCPInvHammer; cpOn[3]  = InpCPInvHammer;
   cpOn[4]  = InpCPEngulf;    cpOn[5]  = InpCPEngulf;
   cpOn[6]  = InpCPHarami;    cpOn[7]  = InpCPHarami;
   cpOn[8]  = InpCPPiercing;  cpOn[9]  = InpCPPiercing;
   cpOn[10] = InpCPStar;      cpOn[11] = InpCPStar;
   cpOn[12] = InpCPThree;     cpOn[13] = InpCPThree;
   cpOn[14] = InpCPDoji;      cpOn[15] = InpCPDoji;
   if(InpCP && !InpCPHammer && !InpCPInvHammer && !InpCPEngulf && !InpCPHarami && !InpCPPiercing && !InpCPStar && !InpCPThree && !InpCPDoji)
      Print("Note: CP is on but no pattern is switched on, so CP takes no trades");
   modOn[MOD_PB] = InpPB; modTP[MOD_PB] = InpPBTP; modSL[MOD_PB] = InpPBSL; modHold[MOD_PB] = InpPBHold; modMax[MOD_PB] = InpPBMax;
   modOn[MOD_SF] = InpSF; modTP[MOD_SF] = InpSFTP; modSL[MOD_SF] = InpSFSL; modHold[MOD_SF] = InpSFHold; modMax[MOD_SF] = InpSFMax;
   modOn[MOD_QB] = InpQB; modTP[MOD_QB] = InpQBTP; modSL[MOD_QB] = InpQBSL; modHold[MOD_QB] = InpQBHold; modMax[MOD_QB] = InpQBMax;
   modOn[MOD_CP] = InpCP; modTP[MOD_CP] = InpCPTP; modSL[MOD_CP] = InpCPSL; modHold[MOD_CP] = InpCPHold; modMax[MOD_CP] = InpCPMax;
   for(int m = 0; m < NMOD; m++)
      if(modOn[m] && (modTP[m] <= 0 || modSL[m] <= 0 || modHold[m] < 1 || modMax[m] < 1))
      {
         Print(ModName[m], ": take profit, stop, hold and max positions must be above zero");
         return INIT_PARAMETERS_INCORRECT;
      }
   for(int m = 0; m < NMOD; m++)
      if(modOn[m] && modSL[m] < 0.20 - 1e-9)
      {
         Print(ModName[m], ": the first stop must be at least $0.20; tighter than that, spread and noise stop trades out at once");
         return INIT_PARAMETERS_INCORRECT;
      }
   for(int m = 0; m < NMOD; m++)
      if(modOn[m] && modSL[m] <= modTP[m])
      {
         Print(ModName[m], ": the first stop ($", DoubleToString(modSL[m], 2), ") must be wider than the take profit ($",
               DoubleToString(modTP[m], 2), "), so spread and noise don't stop trades out before they can reach it");
         return INIT_PARAMETERS_INCORRECT;
      }
   if(InpTrailStart < 0 || InpTrailDist < 0 || InpTrailStep < 0)
   {
      Print("Trailing stop inputs can't be negative");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(InpTrailDist > 0 && InpTrailStart < InpTrailDist)
      Print("Note: trailing starts at +$", DoubleToString(InpTrailStart, 2), ", less than the $", DoubleToString(InpTrailDist, 2),
            " trail distance, so its first stop is still below break-even");
   for(int m = 0; m < NMOD; m++)
      if(modOn[m] && InpTrailDist > 0 && InpTrailStart >= modTP[m])
         Print("Note: ", ModName[m], " trailing starts at +$", DoubleToString(InpTrailStart, 2), ", not below its $",
               DoubleToString(modTP[m], 2), " take profit, so its stop never trails");
   if(InpPB && (InpPBMinutes < 1 || InpPBMinutes > 60 || 1440 % InpPBMinutes != 0))
   {
      Print("PB: candle length must divide a day and be 1-60 minutes (1, 2, 3, 5, 10, 15, 30, 60...) to match the tests");
      return INIT_PARAMETERS_INCORRECT;
   }
   long otherMagic[] = {20261013, 20261014, 20261015};             // GoldAllAgree, GoldAsiaBreak, GoldCandlePatterns
   for(int k = 0; k < ArraySize(otherMagic); k++)
      if(otherMagic[k] >= InpMagic && otherMagic[k] < InpMagic + NMOD)
      {
         Print("Magic numbers ", InpMagic, "-", InpMagic + NMOD - 1, " include ", otherMagic[k], ", used by another of your EAs. Pick another base.");
         return INIT_PARAMETERS_INCORRECT;
      }
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {
      Print("GoldMicroScalp needs a HEDGING account: on a netting account its trades would merge with your other gold positions and overwrite their stop loss and take profit.");
      return INIT_FAILED;
   }
   hFast = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   hSlow = iMA(_Symbol, PERIOD_H1, 80, 0, MODE_EMA, PRICE_CLOSE);
   if(hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE) return INIT_FAILED;
   if(InpM5Align == M5_EMA)
   {
      hM5 = iMA(_Symbol, PERIOD_M5, InpM5EMA, 0, MODE_EMA, PRICE_CLOSE);
      if(hM5 == INVALID_HANDLE) return INIT_FAILED;
   }
   trade.SetDeviationInPoints(30);
   if(!trade.SetTypeFillingBySymbol(_Symbol)) trade.SetTypeFilling(ORDER_FILLING_RETURN);   // symbols without FOK/IOC take only RETURN
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("Warning: tested on XAUUSD only, attached to ", _Symbol);
   lastBar = iTime(_Symbol, PERIOD_M1, 0);                         // never act on a bar that closed before the EA started
   EventSetTimer(1);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(hFast != INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow != INVALID_HANDLE) IndicatorRelease(hSlow);
   if(hM5 != INVALID_HANDLE) IndicatorRelease(hM5);
   Comment("");
}

int ModuleOf(long magic) { long m = magic - InpMagic; return (m >= 0 && m < NMOD) ? (int)m : -1; }

int TodOf(datetime t) { MqlDateTime s; TimeToStruct(t, s); return s.hour * 60 + s.min; }

// H1 EMA20 vs EMA80 on the last closed H1 bar
int H1Trend()
{
   double f[1], s[1];
   if(CopyBuffer(hFast, 0, 1, 1, f) != 1 || CopyBuffer(hSlow, 0, 1, 1, s) != 1) return 0;
   return f[0] > s[0] ? 1 : (f[0] < s[0] ? -1 : 0);
}

// Closed P&L today for all modules (including trades of ours closed by hand), plus trade and win counts
double TodayClosed(int &trades, int &wins)
{
   static double lastSum = 0; static datetime lastDay = 0;
   datetime now = TimeCurrent();
   datetime dayStart = now - (now % 86400);
   double sum = 0; trades = 0; wins = 0;
   if(!HistorySelect(dayStart, now + 60)) return lastDay == dayStart ? lastSum : 0;   // a failed read must not lift today's stop
   long ours[]; int nOurs = 0;
   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)                                        // oldest first: a position's opening deal comes before its closes
   {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0 || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol) continue;
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      long pid   = HistoryDealGetInteger(d, DEAL_POSITION_ID);
      bool mine  = ModuleOf(HistoryDealGetInteger(d, DEAL_MAGIC)) >= 0;
      if(entry == DEAL_ENTRY_IN)
      {
         if(!mine) continue;
         ArrayResize(ours, nOurs + 1); ours[nOurs++] = pid;
      }
      else if(!mine)                                                  // closed by hand (magic 0) or a server close without our magic
      {
         for(int k = 0; k < nOurs && !mine; k++) mine = (ours[k] == pid);
         if(!mine) continue;
      }
      double p = HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
      sum += p;
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY) { trades++; if(p > 0) wins++; }
   }
   lastSum = sum; lastDay = dayStart;
   return sum;
}

// Close positions whose holding time is up, at the end of the session, or at a stop the EA keeps itself;
// move each position's stop behind price once it is in profit (trailing stop).
// Counts every position still open, including one whose close failed, so the caps stay honest.
void ManagePositions(int &openPer[], int &openTotal)
{
   ArrayInitialize(openPer, 0); openTotal = 0;
   bool tester = MQLInfoInteger(MQL_TESTER) != 0;
   datetime now = tester ? TimeCurrent() : TimeTradeServer();      // advances on the timer even without new quotes
   bool endOfDay = TodOf(now) >= closeTod;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   bool priced = bid > 0 && ask > 0;
   int    digits  = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pt      = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   // Send closes only while gold is quoting and trading is allowed; otherwise (holiday early close, weekend,
   // Algo Trading off) the timer would send a failing close request every second until the market reopens.
   bool canClose = priced && (tester ||
                   (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED) &&
                    (long)now - SymbolInfoInteger(_Symbol, SYMBOL_TIME) <= 60));
   ulong seen[]; int nSeen = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      int m = ModuleOf(PositionGetInteger(POSITION_MAGIC));
      if(m < 0) continue;
      ArrayResize(seen, nSeen + 1); seen[nSeen++] = tk;
      long opened = PositionGetInteger(POSITION_TIME);
      bool isBuy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double tpLvl = PositionGetDouble(POSITION_TP), slLvl = PositionGetDouble(POSITION_SL);
      int k = VFind(tk);
      if(k < 0 && GlobalVariableCheck(VName(tk))) { VSet(tk, GlobalVariableGet(VName(tk))); k = VFind(tk); }   // EA restarted: take back the stop it kept
      // the broker took no TP/SL at the open (TP 0 marks it) and the EA restarted: rebuild the first stop beyond today's spread
      if(k < 0 && tpLvl == 0 && priced)
      {
         VSet(tk, NormalizeDouble(isBuy ? open - (ask - bid) - modSL[m] : open + (ask - bid) + modSL[m], digits));
         k = VFind(tk);
      }
      // holding time in whole M1 bars from the bar the position opened in (the tests' timeout in bars)
      bool close = endOfDay || (long)now >= opened - opened % 60 + (long)modHold[m] * 60;
      if(!close && priced && tpLvl == 0 && (isBuy ? bid >= open + modTP[m] : ask <= open - modTP[m])) close = true;   // take profit the EA keeps itself
      // Trailing stop: once the trade is InpTrailStart in profit, keep its stop InpTrailDist behind the best price.
      // A buy's stop is hit by the bid and a sell's by the ask, so the stop follows that price.
      double gain = isBuy ? bid - open : open - ask;
      if(!close && priced && InpTrailDist > 0 && gain >= InpTrailStart - pt / 2)
      {
         double want = NormalizeDouble(isBuy ? bid - InpTrailDist : ask + InpTrailDist, digits);
         double cur  = Tighter(isBuy, slLvl, k >= 0 ? vStop[k] : 0);
         bool better = cur == 0 || (isBuy ? want >= cur + MathMax(InpTrailStep, pt) - pt / 2
                                          : want <= cur - MathMax(InpTrailStep, pt) + pt / 2);
         if(better)
         {
            bool fits = (isBuy ? bid - want : want - ask) >= minDist - pt / 2;   // the broker's minimum stop distance
            bool sent = false;
            if(k < 0 && fits && canClose)                                // stop still on the server: move it there
            {
               trade.SetExpertMagicNumber(InpMagic + m);
               sent = trade.PositionModify(tk, want, tpLvl) || trade.ResultRetcode() == TRADE_RETCODE_NO_CHANGES;   // no changes: the server already has this stop
               if(!sent) Print(ModShort[m], " trailing stop refused (", trade.ResultRetcodeDescription(), "): the EA keeps it and closes at market");
            }
            if(!sent) { VSet(tk, want); k = VFind(tk); }                 // broker refused or too close: the EA keeps the stop
         }
      }
      if(!close && priced && k >= 0 && (isBuy ? bid <= vStop[k] : ask >= vStop[k])) close = true;   // stop the EA keeps itself
      if(close && canClose)
      {
         trade.SetExpertMagicNumber(InpMagic + m);
         if(trade.PositionClose(tk)) continue;
         Print("Close failed: ", trade.ResultRetcodeDescription());
      }
      openPer[m]++; openTotal++;
   }
   VPrune(seen, nSeen);
}

// Why module m may not enter at the current quote, "" if it may: the spread is above InpMaxSpreadPts points, or above
// InpMaxSpreadPctTP % of the module's take profit. The tolerance is far below one point, so a $0.125 limit lets
// 12 points through and stops 13, whatever the rounding of ask - bid.
string SpreadVeto(int m)
{
   MqlTick q;
   if(!SymbolInfoTick(_Symbol, q) || q.bid <= 0 || q.ask < q.bid) return "no valid quote";
   double pt  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double spr = q.ask - q.bid;
   int    pts = (int)MathRound(spr / pt);
   if(InpMaxSpreadPts > 0 && pts > InpMaxSpreadPts)
      return StringFormat("spread %d points is above the %d-point limit", pts, InpMaxSpreadPts);
   double lim = InpMaxSpreadPctTP / 100.0 * modTP[m];
   if(InpMaxSpreadPctTP > 0 && spr > lim + pt * 0.001)
      return StringFormat("spread $%.2f is above $%.3f (%.0f%% of the $%.2f take profit)", spr, lim, InpMaxSpreadPctTP, modTP[m]);
   return "";
}

void Open(int m, int dir)
{
   int    digits  = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pt      = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist = MathMax((double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
                            (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL)) * pt;
   bool   forceVirtual = false;
   trade.SetExpertMagicNumber(InpMagic + m);
   for(int attempt = 0; attempt < 3; attempt++)
   {
      if(attempt > 0)                                          // retry after a requote: the spread may have widened since
      {
         string veto = SpreadVeto(m);
         if(veto != "") { if(StringFind(veto, "spread") == 0) sprSkips++; Print(ModShort[m], " retry cancelled: ", veto); return; }
      }
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double spr = ask - bid;
      bool   server = !forceVirtual && modTP[m] > minDist && modSL[m] > minDist;
      double tp = 0, sl = 0;
      // Take profit is measured from the entry price, so a TP closes the trade $modTP in profit. The first stop is
      // measured from the price that triggers it (bid for a buy, ask for a sell), so the spread alone can't hit it:
      // a full stop costs about modSL plus the spread.
      if(server)
      {
         tp = NormalizeDouble(dir == 1 ? ask + modTP[m] : bid - modTP[m], digits);
         sl = NormalizeDouble(dir == 1 ? bid - modSL[m] : ask + modSL[m], digits);
      }
      else
      {
         // TP and first stop kept by the EA: ManagePositions closes at them. This far stop only protects the position
         // if the EA, terminal or connection stops. TP stays 0, which is what marks the position as EA-managed.
         double far = MathMax(2.0 * modSL[m], minDist + 50 * pt);
         sl = NormalizeDouble(dir == 1 ? bid - far : ask + far, digits);
      }
      bool ok = dir == 1 ? trade.Buy(InpLots, _Symbol, ask, sl, tp, ModShort[m])
                         : trade.Sell(InpLots, _Symbol, bid, sl, tp, ModShort[m]);
      uint rc = trade.ResultRetcode();
      if(ok)
      {
         ulong pos = trade.ResultOrder();                       // hedging: position ticket = opening order ticket
         double fill = trade.ResultPrice(), quote = dir == 1 ? ask : bid;
         if(fill <= 0) fill = quote;
         double stop1 = NormalizeDouble(dir == 1 ? fill - spr - modSL[m] : fill + spr + modSL[m], digits);   // first stop, from the fill
         if(!server)
            VSet(pos, stop1);                                   // the EA keeps the first stop
         else if(MathAbs(fill - quote) >= pt)
         {
            // server TP/SL were priced off the quote; the fill slipped, so move them onto the fill
            double ntp = NormalizeDouble(dir == 1 ? fill + modTP[m] : fill - modTP[m], digits);
            if(!trade.PositionModify(pos, stop1, ntp))
               Print(ModShort[m], " filled ", DoubleToString(fill - quote, digits), " off the quote; moving TP/SL failed: ", trade.ResultRetcodeDescription());
         }
         return;
      }
      Print(ModShort[m], " order failed: ", trade.ResultRetcodeDescription());
      if(rc == TRADE_RETCODE_INVALID_STOPS && server) { forceVirtual = true; continue; }   // levels refused: open with virtual TP/SL
      if(rc != TRADE_RETCODE_REQUOTE && rc != TRADE_RETCODE_PRICE_CHANGED && rc != TRADE_RETCODE_PRICE_OFF) return;  // retry only when nothing was filled
   }
}

void ShowPanel(double pnl, int trades, int wins, bool halted, int openTotal)
{
   string s = "GoldMicroScalp   " + TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES) + "\n";
   s += StringFormat("Today: %d trades, %d wins (%.0f%%), closed P&L %+.2f   open %d%s\n",
                     trades, wins, trades > 0 ? 100.0 * wins / trades : 0, pnl, openTotal, halted ? "   STOPPED FOR TODAY" : "");
   double spr = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   s += StringFormat("Spread now: %d points ($%.2f per trade at %.2f lot)\n", (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD),
                     spr * InpLots * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE), InpLots);
   string lim = ""; bool wide = false, same = true; double l0 = -1;
   for(int m = 0; m < NMOD; m++)
      if(modOn[m])
      {
         double l = InpMaxSpreadPctTP / 100.0 * modTP[m];
         lim += StringFormat("%s %s $%.3f", lim == "" ? "" : ",", ModShort[m], l);
         if(l0 < 0) l0 = l; else if(MathAbs(l - l0) > 1e-9) same = false;
         if(StringFind(SpreadVeto(m), "spread") == 0) wide = true;     // a missing quote is not a wide spread
      }
   if(same && l0 >= 0) lim = StringFormat(" $%.3f", l0);
   string pctTxt = InpMaxSpreadPctTP > 0 ? StringFormat(" %.0f%% of TP =%s", InpMaxSpreadPctTP, lim) : "";
   string ptsTxt = InpMaxSpreadPts > 0 ? StringFormat("%s at most %d points", pctTxt == "" ? "" : ",", InpMaxSpreadPts) : "";
   s += "Spread limit:" + ((pctTxt + ptsTxt) == "" ? " off" : pctTxt + ptsTxt) + (wide ? "   SPREAD TOO WIDE NOW" : "") + "\n";
   if(InpSessionOn)
      s += StringFormat("Session %s-%s server time (signal bars): %s\n", InpSessionFrom, InpSessionTo,
                        InSession(TodOf(TimeCurrent())) ? "open" : "closed, no new signals");
   if(InpTrailDist > 0)
      s += StringFormat("Trailing: from +$%.2f, $%.2f behind price (%d stops kept by the EA)\n", InpTrailStart, InpTrailDist, ArraySize(vTk));
   s += "Signals today:";
   for(int m = 0; m < NMOD; m++) if(modOn[m]) s += StringFormat("  %s %d", ModShort[m], sigCount[m]);
   s += StringFormat("   skipped for spread %d", sprSkips);
   Comment(s);
}

void OnTimer() { OnTick(); }      // keeps holding-time exits working on quiet ticks

void OnTick()
{
   int openPer[NMOD]; int openTotal = 0;
   ManagePositions(openPer, openTotal);
   int trades = 0, wins = 0;
   double pnl = TodayClosed(trades, wins);
   bool halted = (InpDailyLoss > 0 && pnl <= -InpDailyLoss) || (InpDailyTarget > 0 && pnl >= InpDailyTarget);

   datetime bar = iTime(_Symbol, PERIOD_M1, 0);
   if(bar == 0 || bar == lastBar) { ShowPanel(pnl, trades, wins, halted, openTotal); return; }

   MqlRates r[];
   ArraySetAsSeries(r, true);
   int total = CopyRates(_Symbol, PERIOD_M1, 1, 1500, r);       // r[0] = the M1 bar that just closed
   if(total < 1500)                                             // M1 history still loading: try again on the next tick/timer
   {
      static datetime warned = 0;
      if(warned != bar) { warned = bar; Print("Waiting for M1 history (", total, " of 1500 bars)"); }
      ShowPanel(pnl, trades, wins, halted, openTotal);
      return;
   }
   lastBar = bar;

   MqlDateTime s; TimeToStruct(bar, s);
   if(s.day_of_year != sigDay) { sigDay = s.day_of_year; ArrayInitialize(sigCount, 0); sprSkips = 0; }

   int trend = H1Trend();
   int sig[NMOD];
   string cpName = "";
   sig[MOD_PB] = modOn[MOD_PB] ? SigPullback(r, 0, total, InpPBMinutes, InpPBBodyMult, InpPBMaru, InpPBMinBody, trend) : 0;
   sig[MOD_SF] = modOn[MOD_SF] ? SigSpikeFade(r, 0, total, InpSFMult, SessionVWAP(r, 0, total)) : 0;
   sig[MOD_QB] = modOn[MOD_QB] ? SigQuarterFade(r, 0, total, InpQBK, InpQBFromHour, InpQBToHour) : 0;
   sig[MOD_CP] = modOn[MOD_CP] ? CPVote(r, 0, trend, InpCPTrend, cpOn, InpCPMinBody, cpName) : 0;
   if(InpM5Align != M5_OFF)                                      // optional: the last closed M5 candle must agree
   {
      int d5 = M5Dir(r[0].time + 60);                            // as known when the signal bar closed
      for(int m = 0; m < NMOD; m++)
         if(sig[m] != 0 && (m == MOD_PB || m == MOD_CP || InpM5Fades) && sig[m] != d5) sig[m] = 0;
   }

   int  tod   = TodOf(r[0].time);                                // the signal bar's open time, as in the tests
   bool inHours = tod >= firstTod && tod <= lastTod && InSession(tod);
   if(!inHours) ArrayInitialize(sig, 0);                         // outside the entry hours or the session window: no signal
   for(int m = 0; m < NMOD; m++) if(sig[m] != 0) sigCount[m]++;

   bool fresh = (long)TimeCurrent() - ((long)r[0].time + 60) <= 60;   // signal bar closed under a minute ago (not before a market close)
   bool window = fresh && TodOf(TimeCurrent()) < closeTod;
   if(window && !halted)
      for(int m = 0; m < NMOD; m++)
      {
         if(sig[m] == 0 || openPer[m] >= modMax[m] || openTotal >= InpMaxOpen) continue;
         string veto = SpreadVeto(m);                            // live quote, read again for each module
         if(veto != "")
         {
            if(StringFind(veto, "spread") == 0) sprSkips++;     // count spread vetoes, not a missing quote
            PrintFormat("%s %s skipped: %s", ModShort[m], sig[m] > 0 ? "buy" : "sell", veto);
            continue;
         }
         if(m == MOD_CP && cpName != "") PrintFormat("CP %s: %s", sig[m] > 0 ? "buy" : "sell", cpName);
         Open(m, sig[m]);
         openPer[m]++; openTotal++;
      }
   ShowPanel(pnl, trades, wins, halted, openTotal);
}
//+------------------------------------------------------------------+
//| v1.30 DEFAULTS AND REJECTION RULES (summary)                      |
//| Exits, every module: take profit $0.25 from the entry price;      |
//|   first stop $0.60 beyond the spread; from +$0.08 the stop trails |
//|   $0.04 behind the best price, moved in steps of $0.01 or more;   |
//|   PB closes after 20 minutes, SF, QB and CP after 5; everything   |
//|   closes at 22:58 server time.                                    |
//| Caps: PB 3, SF 3, QB 3, CP 5 open positions, 12 in total.         |
//| A signal is not traded when:                                      |
//|   - its M1 bar opened outside 15:00-18:59 server time (session    |
//|     window; the 18:59 bar's entry goes out in the 19:00 minute)   |
//|     or outside 01:05-22:29;                                       |
//|   - the live spread is above 50% of that module's take profit     |
//|     ($0.125 with the defaults: 12 points pass, 13 don't) or above |
//|     50 points; the quote is read again before each order and      |
//|     before a retry;                                               |
//|   - today's closed loss has reached $15 (daily stop);             |
//|   - its module or the account is at its position cap;             |
//|   - PB: the 2-minute candle's body is under 0.8 x the average     |
//|     range of the 20 candles before it (and the v1.10 rules: body  |
//|     at least the average body and 90% of its own range, against   |
//|     the H1 trend, trade with the trend);                          |
//|   - CP: no enabled pattern fired (default: engulfing, morning/    |
//|     evening star, three white soldiers/black crows), the last     |
//|     candle's body is under 0.5 x the average M1 range of the 20   |
//|     bars before it, or the pattern runs against the H1 trend;     |
//|   - optional, off by default: the last closed M5 candle (or the   |
//|     M5 EMA 9) doesn't point the trade's way (a flat one counts    |
//|     as no; PB and CP only by default).                            |
//| Refuses to start: netting account, a first stop under $0.20 or    |
//|   not wider than the take profit, malformed times, a session      |
//|   window that is empty or misses the entry hours, or magic        |
//|   numbers used by your other EAs.                                 |
//+------------------------------------------------------------------+
