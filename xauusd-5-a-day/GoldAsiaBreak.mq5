//+------------------------------------------------------------------+
//| GoldAsiaBreak.mq5                                                 |
//| One trade a day on XAUUSD: the first break of the Asian range.    |
//| Asian range = high/low of today's M5 bars from 00:00 to 08:59     |
//| server time. From 09:00, the FIRST closed M5 bar outside it sets  |
//| the trade: close above the high = buy, below the low = sell. If   |
//| that first break can't be traded, there is no trade that day.     |
//| Take profit $5, stop $50, per 0.01 lot. Anything open is closed   |
//| at 22:45, or 10 minutes before the session ends if earlier; a     |
//| trade left from an earlier day is closed at the next open.        |
//| Needs a hedging account to run beside GoldAllAgree.               |
//| Server times match the MT5 export the rule was tested on.         |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.10"

#include <Trade/Trade.mqh>

input group "Rule"
input int    InpRangeEndHour  = 9;          // Asian range ends / trading starts (server hour)
input int    InpCloseHour     = 22;         // Close any open trade at this server hour (sessions end 23:00)...
input int    InpCloseMinute   = 45;         // ...and minute (also closes 10 min before the session end)
input int    InpLastEntryMin  = 15;         // No new entry within this many minutes of the close time
input double InpTakeProfitUSD = 5.0;        // Take profit, $ per oz (0.01 lot: $1 per $1)
input double InpStopUSD       = 50.0;       // Stop loss, $ per oz
input bool   InpAllowShort    = true;       // Trade downside breaks too (tested with both)

input group "Position size"
input double InpLots          = 0.01;       // Lots
input int    InpMaxSpreadPts  = 80;         // Skip a signal tick while spread is above this (points, 0 = off)
input bool   InpNeedHedging   = true;       // Don't trade on a netting account (orders would merge with GoldAllAgree's)
input long   InpMagic         = 20261014;   // Magic number (different from GoldAllAgree)

CTrade   trade;
datetime lastBar    = 0;
int      tradedDay  = -1;                   // day-of-year of the last entry (or of a skipped day)
int      tradedYear = -1;
datetime failBar    = 0;                    // bar of the last failed order
int      fails      = 0;                    // failed orders on that bar

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpStopUSD <= 0 || InpTakeProfitUSD <= 0 || InpRangeEndHour < 1 || InpRangeEndHour > 20)
   {
      Print("Check the take profit, stop and range hour inputs");
      return INIT_PARAMETERS_INCORRECT;
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("Warning: this EA was tested on XAUUSD only, attached to ", _Symbol);
   // Today's trade, if any, is looked up in the deal history from OnTick (EnteredToday):
   // after a terminal restart OnInit can run before login, with the history still empty.
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void MarkTraded(datetime t)
{
   MqlDateTime s; TimeToStruct(t, s);
   tradedDay = s.day_of_year; tradedYear = s.year;
}

bool TradedToday(datetime t)
{
   MqlDateTime s; TimeToStruct(t, s);
   return s.day_of_year == tradedDay && s.year == tradedYear;
}

// Ticket of our open position on this symbol (and selects it), 0 if none
ulong OurPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      return t;
   }
   return 0;
}

// 1 if this EA opened a trade on this symbol since dayStart, 0 if not, -1 if the history can't be read right now
int EnteredToday(datetime dayStart)
{
   if(!HistorySelect(dayStart, TimeCurrent() + 3600)) return -1;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0) continue;
      if(HistoryDealGetInteger(d, DEAL_MAGIC) == InpMagic && HistoryDealGetString(d, DEAL_SYMBOL) == _Symbol
         && HistoryDealGetInteger(d, DEAL_ENTRY) == DEAL_ENTRY_IN
         && (datetime)HistoryDealGetInteger(d, DEAL_TIME) >= dayStart) return 1;
   }
   return 0;
}

// Minute of the day when this weekday's trading session ends (symbol specification), -1 if unknown
int SessionEndTod(int dow)
{
   datetime from, to; int best = -1;
   for(uint k = 0; k < 10 && SymbolInfoSessionTrade(_Symbol, (ENUM_DAY_OF_WEEK)dow, k, from, to); k++)
   {
      int e = (int)((long)to / 60);              // 'to' = seconds after 00:00; 86400 = 24:00
      if(e > best) best = e;
   }
   return best > 1440 ? 1440 : best;
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpNeedHedging && AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {
      static bool warned = false;
      if(!warned) { Alert("GoldAsiaBreak needs a HEDGING account: on netting its orders merge with GoldAllAgree's position. Not trading."); warned = true; }
      return;
   }

   datetime now = TimeCurrent();
   MqlDateTime s; TimeToStruct(now, s);
   int tod = s.hour * 60 + s.min;
   int closeTod = InpCloseHour * 60 + InpCloseMinute;
   int sessEnd  = SessionEndTod(s.day_of_week);       // 23:00 on the tested server since March 2026
   if(sessEnd > 0 && sessEnd - 10 < closeTod) closeTod = sessEnd - 10;
   datetime dayStart = now - (now % 86400);

   // End-of-day close; also close a position left from an earlier day (holiday early close, outage)
   ulong pos = OurPosition();                          // also selects it
   bool stale = pos > 0 && (datetime)PositionGetInteger(POSITION_TIME) < dayStart;
   bool spreadOK = InpMaxSpreadPts <= 0 || SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) <= InpMaxSpreadPts;
   if(pos > 0 && (tod >= closeTod || (stale && (spreadOK || tod >= 120))))
   {
      if(!trade.PositionClose(pos))
         Print("End-of-day close failed: ", trade.ResultRetcodeDescription());
      return;
   }

   // Work once per closed M5 bar
   datetime bar = iTime(_Symbol, PERIOD_M5, 0);
   if(bar == 0 || bar == lastBar) return;
   lastBar = bar;

   if(pos > 0)
   {
      if(PositionSelectByTicket(pos) && (datetime)PositionGetInteger(POSITION_TIME) >= dayStart) MarkTraded(now);   // today's trade is open
      return;
   }
   if(TradedToday(now)) return;
   if(tod < InpRangeEndHour * 60 || tod >= closeTod - InpLastEntryMin) return;

   datetime rangeEnd = dayStart + InpRangeEndHour * 3600;
   if(bar <= rangeEnd) return;                         // the first bar after the range hasn't closed yet
   int entered = EnteredToday(dayStart);
   if(entered < 0) { lastBar = 0; return; }           // history not readable yet: try again on the next tick
   if(entered > 0) { MarkTraded(now); return; }       // today's trade already happened (restart, lost reply)

   // Asian range from today's M5 bars between 00:00 and the range end hour
   if(!SeriesInfoInteger(_Symbol, PERIOD_M5, SERIES_SYNCHRONIZED)) { lastBar = 0; return; }   // history still loading: retry next tick
   MqlRates r[];
   int n = CopyRates(_Symbol, PERIOD_M5, dayStart, rangeEnd - 1, r);
   int minBars = MathMax(12, (InpRangeEndHour - 1) * 9);   // 72 of the usual 96-108 bars for a 09:00 range end
   if(n < minBars || r[n - 1].time != rangeEnd - PeriodSeconds(PERIOD_M5)) return;   // incomplete Asian session (late open, holiday, gap): no trade
   double hi = r[0].high, lo = r[0].low;
   for(int i = 1; i < n; i++) { hi = MathMax(hi, r[i].high); lo = MathMin(lo, r[i].low); }

   // Trade only the FIRST close outside the range: check every closed bar since the range end
   MqlRates a[];
   int m = CopyRates(_Symbol, PERIOD_M5, rangeEnd, bar - 1, a);
   if(m < 1 || a[m - 1].time != bar - PeriodSeconds(PERIOD_M5))
   {
      if(now - bar < 60) lastBar = 0;                  // last closed bar not loaded yet: retry for up to a minute
      return;
   }
   int first = -1;
   for(int k = 0; k < m && first < 0; k++)
      if(a[k].close > hi || a[k].close < lo) first = k;
   if(first < 0) return;                               // no break yet
   if(first < m - 1)                                   // the first break was on an earlier bar and was not traded
   {
      MarkTraded(now);
      Print("First break of the Asian range was at ", TimeToString(a[first].time), " and was not traded: no trade today");
      return;
   }
   double close1 = a[m - 1].close;
   int dir = close1 > hi ? 1 : -1;
   if(dir < 0 && !InpAllowShort) { MarkTraded(now); return; }   // long-only mode: first break was down, skip the day

   if(!spreadOK) { lastBar = 0; return; }              // spread too wide: retry on the next tick of this bar

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   bool ok;
   if(dir == 1)
      ok = trade.Buy(InpLots, _Symbol, ask, NormalizeDouble(ask - InpStopUSD, digits), NormalizeDouble(ask + InpTakeProfitUSD, digits), "AsiaBreak buy");
   else
      ok = trade.Sell(InpLots, _Symbol, bid, NormalizeDouble(bid + InpStopUSD, digits), NormalizeDouble(bid - InpTakeProfitUSD, digits), "AsiaBreak sell");
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
   {
      MarkTraded(now);
      PrintFormat("Asian range %.2f-%.2f, close %.2f: %s", lo, hi, close1, dir == 1 ? "BUY" : "SELL");
   }
   else
   {
      if(failBar != bar) { failBar = bar; fails = 0; }
      fails++;
      PrintFormat("Order failed (try %d): %u %s", fails, trade.ResultRetcode(), trade.ResultRetcodeDescription());
      uint rc = trade.ResultRetcode();
      bool unfilled = rc == TRADE_RETCODE_REQUOTE || rc == TRADE_RETCODE_PRICE_CHANGED || rc == TRADE_RETCODE_PRICE_OFF
                      || rc == TRADE_RETCODE_INVALID_PRICE || rc == TRADE_RETCODE_REJECT;
      if(fails < 3 && unfilled) lastBar = 0;           // retry only replies that say nothing was filled; after a lost reply the next bar sees the position or skips the day
   }
}
//+------------------------------------------------------------------+
