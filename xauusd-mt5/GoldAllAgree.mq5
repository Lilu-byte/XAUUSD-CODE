//+------------------------------------------------------------------+
//| GoldAllAgree.mq5                                                  |
//| Long-only XAUUSD trend follower.                                  |
//| Rule: hold one long position while EMA(20) > EMA(80) on every     |
//| enabled timeframe (M5, M15, M30, H1, H4), using closed bars only. |
//| Flat otherwise. Never short.                                      |
//| Checked once per closed bar of InpCheckTF (default M5).           |
//| v1.10: $100 emergency stop on by default, hedging-account check,  |
//| pause after a stop-out kept across restarts, waits for the higher |
//| timeframes to sync at each new bar.                               |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.10"

#include <Trade/Trade.mqh>

//--- inputs
input group "Signal"
input int             InpFastEMA      = 20;          // Fast EMA period
input int             InpSlowEMA      = 80;          // Slow EMA period
input bool            InpUseM5        = true;        // Require M5 trend up
input bool            InpUseM15       = true;        // Require M15 trend up
input bool            InpUseM30       = true;        // Require M30 trend up
input bool            InpUseH1        = true;        // Require H1 trend up
input bool            InpUseH4        = true;        // Require H4 trend up
input ENUM_TIMEFRAMES InpCheckTF      = PERIOD_M5;   // Re-check signal at each close of

input group "Position size"
input double          InpLots         = 0.01;        // Fixed lots (used when auto is off)
input double          InpEquityPerLot = 0.0;         // Auto: 0.01 lot per this much equity (0 = off)
input double          InpMaxLots      = 1.0;         // Never open more than this

input group "Safety"
input int             InpMaxSpreadPts = 80;          // Skip entry while spread above this (points, 0 = off)
input double          InpStopUSD      = 100.0;       // Emergency stop distance in $ per oz (0 = off; no replay trade went $94 against)
input bool            InpCloseFriday  = false;       // Close before the weekend (not in the backtest)
input int             InpFridayHour   = 22;          // Server hour on Friday to close at
input bool            InpNeedHedging  = true;        // Don't trade on a netting account (other gold EAs' orders would merge with this one)
input long            InpMagic        = 20261013;    // Magic number

//--- state
CTrade   trade;
int      hFast[5], hSlow[5];
bool     use[5];
ENUM_TIMEFRAMES tfs[5] = {PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4};
string   names[5] = {"M5", "M15", "M30", "H1", "H4"};
int      trendState[5];          // +1 up, -1 down, 0 unknown
datetime lastBar   = 0;
int      wanted    = -1;         // -1 unknown, 0 flat, 1 long
datetime lastTry   = 0;
bool     hadPos    = false;      // we held a position on the previous tick
bool     weClosed  = false;      // the last close was ours
bool     blocked   = false;      // stopped out or closed by hand: wait for a FLAT signal before re-entering
datetime barSeenAt = 0;          // when this EA saw the first tick of the current check bar

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpFastEMA <= 0 || InpSlowEMA <= InpFastEMA)
   {
      Print("Slow EMA must be longer than fast EMA");
      return INIT_PARAMETERS_INCORRECT;
   }
   use[0] = InpUseM5; use[1] = InpUseM15; use[2] = InpUseM30; use[3] = InpUseH1; use[4] = InpUseH4;
   for(int i = 0; i < 5; i++)
   {
      hFast[i] = INVALID_HANDLE; hSlow[i] = INVALID_HANDLE; trendState[i] = 0;
      if(!use[i]) continue;
      hFast[i] = iMA(_Symbol, tfs[i], InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
      hSlow[i] = iMA(_Symbol, tfs[i], InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
      if(hFast[i] == INVALID_HANDLE || hSlow[i] == INVALID_HANDLE)
      {
         Print("Could not create EMA on ", names[i]);
         return INIT_FAILED;
      }
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("Warning: this EA was tested on XAUUSD only, attached to ", _Symbol);
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
   Comment("");
}

//+------------------------------------------------------------------+
//| Trend of the last CLOSED bar on timeframe i: +1, -1, or 0 if the |
//| data is not ready yet.                                           |
//+------------------------------------------------------------------+
int Trend(int i, datetime checkBar)
{
   double f[1], s[1];
   int need = 4 * InpSlowEMA;                                   // let the slow EMA settle
   if(BarsCalculated(hFast[i]) < need || BarsCalculated(hSlow[i]) < need) return 0;
   if(CopyBuffer(hFast[i], 0, 1, 1, f) != 1) return 0;
   if(CopyBuffer(hSlow[i], 0, 1, 1, s) != 1) return 0;
   // in the first minute after a new check bar's first tick, wait until this timeframe has its current bar and the EMAs include it
   if(TimeCurrent() - barSeenAt < 60)
   {
      int bars = iBars(_Symbol, tfs[i]);
      if(iTime(_Symbol, tfs[i], 0) < checkBar - checkBar % PeriodSeconds(tfs[i])
         || BarsCalculated(hFast[i]) < bars || BarsCalculated(hSlow[i]) < bars) return 0;
      if(CopyBuffer(hFast[i], 0, 1, 1, f) != 1 || CopyBuffer(hSlow[i], 0, 1, 1, s) != 1) return 0;   // re-read now that the EMAs include the new bar
   }
   if(f[0] > s[0]) return 1;
   return -1;
}

//+------------------------------------------------------------------+
//| Returns 1 = all enabled timeframes up, 0 = at least one down,    |
//| -1 = some data not ready (decide later).                         |
//+------------------------------------------------------------------+
int Signal(datetime checkBar)
{
   int result = 1;
   for(int i = 0; i < 5; i++)
   {
      if(!use[i]) continue;
      trendState[i] = Trend(i, checkBar);
      if(trendState[i] == 0) return -1;
      if(trendState[i] < 0) result = 0;
   }
   return result;
}

//+------------------------------------------------------------------+
double MyLongVolume()
{
   double v = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) v += PositionGetDouble(POSITION_VOLUME);
   }
   return v;
}

//+------------------------------------------------------------------+
bool CloseAll()
{
   bool ok = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(!trade.PositionClose(t))
      {
         Print("Close failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
         ok = false;
      }
   }
   return ok;
}

//+------------------------------------------------------------------+
double LotSize()
{
   double lots = InpLots;
   if(InpEquityPerLot > 0)
      lots = 0.01 * MathFloor(AccountInfoDouble(ACCOUNT_EQUITY) / InpEquityPerLot);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = MathMin(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), InpMaxLots);
   if(step > 0) lots = MathFloor(lots / step + 1e-9) * step;
   if(lots < vmin) lots = vmin;
   if(lots > vmax) lots = vmax;
   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
bool OpenLong()
{
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPts > 0 && spread > InpMaxSpreadPts) return false;   // wait for a normal spread
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl  = 0;
   if(InpStopUSD > 0) sl = NormalizeDouble(ask - InpStopUSD, _Digits);
   if(!trade.Buy(LotSize(), _Symbol, 0, sl, 0, "all-agree long"))
   {
      Print("Buy failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
      return false;
   }
   return true;
}

//+------------------------------------------------------------------+
bool FridayCutoff()
{
   if(!InpCloseFriday) return false;
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   return t.day_of_week == 5 && t.hour >= InpFridayHour;
}

//+------------------------------------------------------------------+
void ShowState(double held)
{
   string s = "GoldAllAgree   EMA" + IntegerToString(InpFastEMA) + "/" + IntegerToString(InpSlowEMA) + "\n";
   for(int i = 0; i < 5; i++)
   {
      if(!use[i]) continue;
      s += names[i] + ": " + (trendState[i] > 0 ? "UP" : trendState[i] < 0 ? "down" : "loading") + "\n";
   }
   s += "Signal: " + (wanted == 1 ? "LONG" : wanted == 0 ? "FLAT" : "waiting for data") + "\n";
   if(blocked) s += "Paused after outside close; resumes after a FLAT signal\n";
   s += "Holding: " + DoubleToString(held, 2) + " lots";
   Comment(s);
}

//+------------------------------------------------------------------+
//| True if a signal check after time t would have seen FLAT: some   |
//| enabled timeframe closed a bar with fast EMA <= slow EMA since.  |
//+------------------------------------------------------------------+
bool FlatSince(datetime t)
{
   int C = PeriodSeconds(InpCheckTF);
   datetime tc = t - t % C + C;                                         // first check after t
   for(int i = 0; i < 5; i++)
   {
      if(!use[i]) continue;
      int P = PeriodSeconds(tfs[i]);
      datetime from = tc - tc % P - P, to = iTime(_Symbol, tfs[i], 1);   // last closed bar at that check .. last closed bar now
      if(to < from) continue;
      double f[], s[];
      int n = CopyBuffer(hFast[i], 0, from, to, f);
      if(n <= 0 || CopyBuffer(hSlow[i], 0, from, to, s) != n) continue;
      for(int k = 0; k < n; k++) if(f[k] <= s[k]) return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| After a restart: if our last position was closed by its stop, by |
//| hand or by a stop-out, keep the pause until a FLAT signal.       |
//+------------------------------------------------------------------+
void RestoreBlocked()
{
   if(!HistorySelect(TimeCurrent() - 90 * 86400, TimeCurrent() + 3600)) return;
   long pid = -1;
   for(int k = HistoryDealsTotal() - 1; k >= 0 && pid < 0; k--)
   {
      ulong d = HistoryDealGetTicket(k);
      if(d > 0 && HistoryDealGetString(d, DEAL_SYMBOL) == _Symbol && HistoryDealGetInteger(d, DEAL_MAGIC) == InpMagic
         && HistoryDealGetInteger(d, DEAL_ENTRY) == DEAL_ENTRY_IN) pid = HistoryDealGetInteger(d, DEAL_POSITION_ID);
   }
   if(pid < 0 || !HistorySelectByPosition(pid)) return;
   for(int k = HistoryDealsTotal() - 1; k >= 0; k--)
   {
      ulong d = HistoryDealGetTicket(k);
      if(d > 0 && HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_IN
         && (HistoryDealGetInteger(d, DEAL_REASON) != DEAL_REASON_EXPERT || HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic))
      {
         if(FlatSince((datetime)HistoryDealGetInteger(d, DEAL_TIME))) return;   // a FLAT already came after that close: the pause is over
         blocked = true; Print("Last position was closed outside the EA; waiting for a FLAT signal"); return;
      }
   }
}

//+------------------------------------------------------------------+
void OnTick()
{
   //--- on a netting account another gold EA's orders would merge with this position
   if(InpNeedHedging && AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {
      static bool warned = false;
      if(!warned) { Alert("GoldAllAgree needs a HEDGING account when other gold EAs run: on netting their orders merge with this position. Not trading (set 'Need hedging' to false to run it alone)."); warned = true; }
      return;
   }

   //--- re-evaluate the signal once per closed bar of the check timeframe
   datetime bar = iTime(_Symbol, InpCheckTF, 0);
   static datetime seenBar = 0;
   if(bar != seenBar) { seenBar = bar; barSeenAt = TimeCurrent(); }   // the higher-timeframe wait runs from this bar's first tick
   if(bar != lastBar)
   {
      int sig = Signal(bar);
      if(sig >= 0) { wanted = sig; lastBar = bar; }   // not ready: try again next tick
   }
   if(wanted < 0) return;

   //--- a position that vanished without us closing it (emergency stop, manual close)
   static bool restored = false;
   if(!restored) { RestoreBlocked(); restored = true; }
   double held = MyLongVolume();
   if(hadPos && held <= 0 && !weClosed)
   {
      blocked = true;
      Print("Position closed outside the EA; waiting for the signal to turn FLAT before re-entering");
   }
   if(wanted == 0) blocked = false;

   int target = wanted;
   if(FridayCutoff() || blocked) target = 0;

   //--- bring the position in line with the target (retry on every tick, at most once per 10 s)
   bool aligned = (target == 1) == (held > 0);
   if(!aligned && TimeCurrent() - lastTry >= 10)
   {
      lastTry = TimeCurrent();
      if(target == 1) { if(OpenLong()) weClosed = false; }
      else if(CloseAll()) weClosed = true;
      held = MyLongVolume();
   }
   hadPos = held > 0;
   ShowState(held);
}
//+------------------------------------------------------------------+
