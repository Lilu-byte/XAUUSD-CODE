//+------------------------------------------------------------------+
//|                                              XAU_DataExport.mq5  |
//|  Script: saves this symbol's price history (M5, M15, H1, H4, D1)  |
//|  and its contract details to CSV files, so the whole Strategy Lab |
//|  and every test in research/ can be re-run on YOUR broker's real  |
//|  data. Run it once from the Navigator (Scripts) on an XAUUSD      |
//|  chart; the files land in  <Data Folder>\MQL5\Files\XAU_Export\   |
//+------------------------------------------------------------------+
#property copyright   "XAU Oracle"
#property version     "1.10"
#property description "Exports XAUUSD history (M1..D1), related markets and the US economic calendar to CSV for offline testing."
#property script_show_inputs

input int InpBarsM5  = 200000;   // M5 bars (about 2.7 years)
input int InpBarsM15 = 100000;   // M15 bars (about 4 years)
input int InpBarsH1  = 60000;    // H1 bars (about 10 years)
input int InpBarsH4  = 20000;    // H4 bars
input int InpBarsD1  = 8000;     // D1 bars
input int InpBarsM1  = 100000;   // M1 bars of this symbol (about 3 months; exact candle paths for M5 tests; 0 = skip)
input string InpExtraSymbols = "EURUSD,XAGUSD,USDX,DXY,US500,USTEC,US30,UST10Y,XAUEUR"; // Related markets (M5 + M15) for lead-lag tests; missing ones are skipped
input int InpBarsExtra = 100000; // M5 / M15 bars per related market
input int InpCalendarYears = 4;  // Years of the US economic calendar (medium and high impact; 0 = skip)

string TfLabel(const ENUM_TIMEFRAMES tf)
{
   return StringSubstr(EnumToString(tf), 7);
}

int ExportTf(const string sym, const ENUM_TIMEFRAMES tf, const int count)
{
   MqlRates r[];
   ArraySetAsSeries(r, false);
   const int got = CopyRates(sym, tf, 0, count, r);
   if(got <= 0) { Print("XAU export: no ", TfLabel(tf), " data (", GetLastError(), ")"); return 0; }
   const string name = "XAU_Export\\" + sym + "_" + TfLabel(tf) + ".csv";
   const int h = FileOpen(name, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("XAU export: cannot write ", name, " (", GetLastError(), ")"); return 0; }
   FileWrite(h, "time", "open", "high", "low", "close", "tick_volume", "spread");
   const int dg = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   for(int i = 0; i < got; i++)
      FileWrite(h, TimeToString(r[i].time, TIME_DATE | TIME_MINUTES), DoubleToString(r[i].open, dg), DoubleToString(r[i].high, dg),
                DoubleToString(r[i].low, dg), DoubleToString(r[i].close, dg), IntegerToString(r[i].tick_volume), IntegerToString(r[i].spread));
   FileClose(h);
   Print("XAU export: ", name, "  ", got, " bars from ", TimeToString(r[0].time), " to ", TimeToString(r[got - 1].time));
   return got;
}

string CalNum(const long v)
{
   if(v == LONG_MIN) return "";
   return DoubleToString((double)v / 1000000.0, 6);
}

// US economic calendar (medium and high impact) with actual / forecast / previous values, in SERVER time,
// so news-surprise ideas can be tested offline. Needs a connected terminal (the calendar is not in the tester).
void ExportCalendar()
{
   if(InpCalendarYears <= 0) return;
   MqlCalendarValue vals[];
   const datetime to = TimeTradeServer();
   const datetime from = to - (datetime)((long)InpCalendarYears * 365 * 86400);
   if(!CalendarValueHistory(vals, from, to, NULL, "USD")) { Print("XAU export: economic calendar not available (", GetLastError(), ")"); return; }
   const int h = FileOpen("XAU_Export\\USD_calendar.csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("XAU export: cannot write the calendar file (", GetLastError(), ")"); return; }
   FileWrite(h, "time", "event", "importance", "actual", "forecast", "previous");
   int rows = 0;
   for(int i = 0; i < ArraySize(vals); i++)
   {
      MqlCalendarEvent ev;
      if(!CalendarEventById(vals[i].event_id, ev)) continue;
      const int imp = (int)ev.importance;                     // 2 = moderate, 3 = high
      if(imp < 2) continue;
      FileWrite(h, TimeToString(vals[i].time, TIME_DATE | TIME_MINUTES), ev.name, IntegerToString(imp),
                CalNum(vals[i].actual_value), CalNum(vals[i].forecast_value), CalNum(vals[i].prev_value));
      rows++;
   }
   FileClose(h);
   Print("XAU export: USD_calendar.csv  ", rows, " events");
}

void OnStart()
{
   const string sym = _Symbol;
   ENUM_TIMEFRAMES tfs[5];
   int cnt[5];
   tfs[0] = PERIOD_M5;  cnt[0] = InpBarsM5;
   tfs[1] = PERIOD_M15; cnt[1] = InpBarsM15;
   tfs[2] = PERIOD_H1;  cnt[2] = InpBarsH1;
   tfs[3] = PERIOD_H4;  cnt[3] = InpBarsH4;
   tfs[4] = PERIOD_D1;  cnt[4] = InpBarsD1;
   int total = 0;
   for(int k = 0; k < 5; k++) total += ExportTf(sym, tfs[k], cnt[k]);
   if(InpBarsM1 > 0) total += ExportTf(sym, PERIOD_M1, InpBarsM1);

   // related markets (does the dollar, silver, stocks or yields move before gold?)
   string extra[];
   const int ne = StringSplit(InpExtraSymbols, ',', extra);
   for(int k = 0; k < ne; k++)
   {
      string es = extra[k];
      StringTrimLeft(es);
      StringTrimRight(es);
      if(StringLen(es) == 0 || es == sym) continue;
      if(!SymbolSelect(es, true)) { Print("XAU export: ", es, " is not offered by this broker, skipped"); continue; }
      total += ExportTf(es, PERIOD_M5, InpBarsExtra);
      total += ExportTf(es, PERIOD_M15, InpBarsExtra);
   }
   ExportCalendar();

   // contract details and the broker clock, so sizes and sessions can be reproduced exactly
   const int h = FileOpen("XAU_Export\\" + sym + "_info.txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      FileWrite(h, "symbol=" + sym);
      FileWrite(h, "digits=" + IntegerToString(SymbolInfoInteger(sym, SYMBOL_DIGITS)));
      FileWrite(h, "point=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_POINT), 8));
      FileWrite(h, "contract_size=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE), 2));
      FileWrite(h, "tick_size=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE), 8));
      FileWrite(h, "tick_value=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE), 8));
      FileWrite(h, "tick_value_loss=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS), 8));
      double prof = 0.0;
      const double px = SymbolInfoDouble(sym, SYMBOL_BID);
      if(OrderCalcProfit(ORDER_TYPE_BUY, sym, 1.0, px, px - 10.0, prof)) FileWrite(h, "loss_1lot_10usd_move=" + DoubleToString(prof, 2));
      FileWrite(h, "volume_min=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), 2));
      FileWrite(h, "volume_step=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), 2));
      FileWrite(h, "spread_points_now=" + IntegerToString(SymbolInfoInteger(sym, SYMBOL_SPREAD)));
      FileWrite(h, "swap_mode=" + IntegerToString(SymbolInfoInteger(sym, SYMBOL_SWAP_MODE)));
      FileWrite(h, "swap_long=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_SWAP_LONG), 4));
      FileWrite(h, "swap_short=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_SWAP_SHORT), 4));
      FileWrite(h, "server_minus_gmt_seconds_now=" + IntegerToString((long)(TimeTradeServer() - TimeGMT())));
      FileWrite(h, "account_currency=" + AccountInfoString(ACCOUNT_CURRENCY));
      FileClose(h);
   }
   const string where = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL5\\Files\\XAU_Export";
   Print("XAU export: done, ", total, " bars in ", where);
   Alert("XAU export finished: ", total, " bars saved in ", where, ". Zip that folder and share it for a real-data test.");
}
