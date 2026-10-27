//+------------------------------------------------------------------+
//| GoldCandlePatterns.mq5                                            |
//| Trades the classic candlestick patterns on XAUUSD.                |
//| At each closed bar of InpTF: if the enabled patterns vote buy or  |
//| sell (and the H1 trend agrees, if the filter is on), open one     |
//| trade with a fixed $ take profit and stop. Stop for the day once  |
//| today's closed P&L reaches the target or the loss limit. Closes   |
//| anything open at 23:30 server time. One trade open at a time.     |
//| Tested defaults (M5, 2026): hits +$5 on ~78% of days but LOSES    |
//| about $1.35 a day on average. Run on demo only. See REPORT.md.    |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.00"

#include <Trade/Trade.mqh>

input group "Signal"
input ENUM_TIMEFRAMES InpTF          = PERIOD_M5;  // Candle timeframe
input bool   InpTrendFilter          = true;       // Only trade with the H1 trend (EMA20 vs EMA80)
input bool   InpHammer               = true;       // Hammer (buy)
input bool   InpHangingMan           = true;       // Hanging man (sell)
input bool   InpInvHammer            = true;       // Inverted hammer (buy)
input bool   InpShootingStar         = true;       // Shooting star (sell)
input bool   InpBullEngulf           = true;       // Bullish engulfing (buy)
input bool   InpBearEngulf           = true;       // Bearish engulfing (sell)
input bool   InpBullHarami           = true;       // Bullish harami (buy)
input bool   InpBearHarami           = true;       // Bearish harami (sell)
input bool   InpPiercing             = true;       // Piercing line (buy)
input bool   InpDarkCloud            = true;       // Dark cloud cover (sell)
input bool   InpMorningStar          = true;       // Morning star (buy)
input bool   InpEveningStar          = true;       // Evening star (sell)
input bool   InpThreeSoldiers        = true;       // Three white soldiers (buy)
input bool   InpThreeCrows           = true;       // Three black crows (sell)
input bool   InpDojiFall             = true;       // Doji after a fall (buy)
input bool   InpDojiRise             = true;       // Doji after a rise (sell)

input group "Trade"
input double InpLots                 = 0.01;       // Lots
input double InpTakeProfitUSD        = 5.0;        // Take profit, $ per oz (0.01 lot: $1 per $1)
input double InpStopUSD              = 12.0;       // Stop loss, $ per oz
input double InpDailyTarget          = 5.0;        // Stop for the day at this closed profit ($)
input double InpDailyLossLimit       = 20.0;       // Stop for the day at this closed loss ($, 0 = off)
input int    InpStartHour            = 1;          // First entry hour (server)
input int    InpStartMinute          = 15;         // ...and minute
input int    InpCloseHour            = 23;         // Close everything at (server hour)
input int    InpCloseMinute          = 30;         // ...and minute
input int    InpMaxSpreadPts         = 80;         // Skip entry while spread above this (points, 0 = off)
input long   InpMagic                = 20261015;   // Magic number

CTrade   trade;
int      hFast = INVALID_HANDLE, hSlow = INVALID_HANDLE;
bool     enabled[];
datetime lastBar = 0;

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
   enabled[0] = InpHammer;        enabled[1] = InpHangingMan;   enabled[2] = InpInvHammer;     enabled[3] = InpShootingStar;
   enabled[4] = InpBullEngulf;    enabled[5] = InpBearEngulf;   enabled[6] = InpBullHarami;    enabled[7] = InpBearHarami;
   enabled[8] = InpPiercing;      enabled[9] = InpDarkCloud;    enabled[10] = InpMorningStar;  enabled[11] = InpEveningStar;
   enabled[12] = InpThreeSoldiers; enabled[13] = InpThreeCrows; enabled[14] = InpDojiFall;     enabled[15] = InpDojiRise;
   if(InpTakeProfitUSD <= 0 || InpStopUSD <= 0)
   {
      Print("Take profit and stop must be above zero");
      return INIT_PARAMETERS_INCORRECT;
   }
   hFast = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   hSlow = iMA(_Symbol, PERIOD_H1, 80, 0, MODE_EMA, PRICE_CLOSE);
   if(hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("Warning: this EA was tested on XAUUSD only, attached to ", _Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(hFast != INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow != INVALID_HANDLE) IndicatorRelease(hSlow);
}

// H1 trend from the last closed H1 bar: +1 up, -1 down, 0 unknown
int H1Trend()
{
   double f[1], s[1];
   if(CopyBuffer(hFast, 0, 1, 1, f) != 1 || CopyBuffer(hSlow, 0, 1, 1, s) != 1) return 0;
   return f[0] > s[0] ? 1 : (f[0] < s[0] ? -1 : 0);
}

ulong OurPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagic) return t;
   }
   return 0;
}

// Today's closed P&L of this EA (profit + swap + commission)
double TodayPnL(datetime now)
{
   datetime dayStart = now - (now % 86400);
   double sum = 0;
   if(!HistorySelect(dayStart, now + 60)) return 0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong d = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol) continue;
      sum += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
   }
   return sum;
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime now = TimeCurrent();
   MqlDateTime s; TimeToStruct(now, s);
   int tod = s.hour * 60 + s.min;
   int closeTod = InpCloseHour * 60 + InpCloseMinute;

   ulong pos = OurPosition();
   if(pos > 0 && tod >= closeTod)
   {
      if(!trade.PositionClose(pos)) Print("End-of-day close failed: ", trade.ResultRetcodeDescription());
      return;
   }

   datetime bar = iTime(_Symbol, InpTF, 0);
   if(bar == lastBar) return;
   lastBar = bar;

   if(pos > 0) return;
   if(tod < InpStartHour * 60 + InpStartMinute || tod >= closeTod - 15) return;

   double pnl = TodayPnL(now);
   if(pnl >= InpDailyTarget - 0.005) return;
   if(InpDailyLossLimit > 0 && pnl <= -InpDailyLossLimit) return;

   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, InpTF, 0, 30, r) < 30) return;
   string name;
   int dir = PatternVote(r, 1, enabled, name);
   if(dir == 0) return;
   if(InpTrendFilter && H1Trend() != dir) return;
   if(InpMaxSpreadPts > 0 && SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   bool ok = dir == 1
      ? trade.Buy(InpLots, _Symbol, ask, NormalizeDouble(ask - InpStopUSD, digits), NormalizeDouble(ask + InpTakeProfitUSD, digits), "Candle buy")
      : trade.Sell(InpLots, _Symbol, bid, NormalizeDouble(bid + InpStopUSD, digits), NormalizeDouble(bid - InpTakeProfitUSD, digits), "Candle sell");
   if(ok) PrintFormat("%s: %s (today so far %.2f)", dir == 1 ? "BUY" : "SELL", name, pnl);
   else   Print("Order failed: ", trade.ResultRetcodeDescription());
}
//+------------------------------------------------------------------+
