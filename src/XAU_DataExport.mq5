//+------------------------------------------------------------------+
//|                                              XAU_DataExport.mq5  |
//|  Script: saves this symbol's price history (M5, M15, H1, H4, D1)  |
//|  and its contract details to CSV files, so the whole Strategy Lab |
//|  and every test in research/ can be re-run on YOUR broker's real  |
//|  data. Run it once from the Navigator (Scripts) on an XAUUSD      |
//|  chart; the files land in  <Data Folder>\MQL5\Files\XAU_Export\   |
//+------------------------------------------------------------------+
#property copyright   "XAU Oracle"
#property version     "1.00"
#property description "Exports XAUUSD history (M5..D1) and contract details to CSV for offline testing."
#property script_show_inputs

input int InpBarsM5  = 200000;   // M5 bars (about 2.7 years)
input int InpBarsM15 = 100000;   // M15 bars (about 4 years)
input int InpBarsH1  = 60000;    // H1 bars (about 10 years)
input int InpBarsH4  = 20000;    // H4 bars
input int InpBarsD1  = 8000;     // D1 bars

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
      FileWrite(h, "server_minus_gmt_seconds_now=" + IntegerToString((long)(TimeTradeServer() - TimeGMT())));
      FileWrite(h, "account_currency=" + AccountInfoString(ACCOUNT_CURRENCY));
      FileClose(h);
   }
   const string where = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL5\\Files\\XAU_Export";
   Print("XAU export: done, ", total, " bars in ", where);
   Alert("XAU export finished: ", total, " bars saved in ", where, ". Zip that folder and share it for a real-data test.");
}
