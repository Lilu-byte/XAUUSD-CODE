//+------------------------------------------------------------------+
//|                                               XAU_Sniper_EA.mq5  |
//|  Automated XAUUSD trader driven by the same engine as the        |
//|  XAU_Oracle indicator (XAU_Core.mqh).                            |
//|                                                                  |
//|  One trade at a time by default, fixed-fractional risk, hard     |
//|  account protection (daily / weekly loss, drawdown kill-switch), |
//|  spread / session / news filters, partial + break-even + trail,  |
//|  time stop, Friday flatten.                                      |
//|                                                                  |
//|  NO strategy wins every trade and none can guarantee profit.     |
//|  Test on your broker's real ticks and start on a demo account.   |
//+------------------------------------------------------------------+
#property copyright   "XAU Sniper"
#property version     "1.00"
#property description "XAUUSD confluence EA with strict risk management."
#property description "Not a guarantee of profit. Validate in the Strategy Tester first."

#include <Trade/Trade.mqh>
#include <XAU/XAU_Platform.mqh>

// Hard ceiling for risk per trade (percent of equity), applied after grade scaling.
// Deliberate guard against typos and against chasing a "double every month" target:
// see docs/RISK_MATH.md before raising it.
#define XS_MAX_RISK_PCT 5.0

//--- inputs -----------------------------------------------------------
input group "=== Risk ==="
input double InpRiskPct         = 1.0;    // Risk per trade, % of equity (hard ceiling XS_MAX_RISK_PCT = 5)
input bool   InpGradeScaling    = false;  // Scale risk by setup grade (B x0.6, A x1.0, A+ x1.4). Off: no evidence grades predict outcome; enable only if YOUR trial shows A/A+ beat B
input double InpStreakScale     = 0.5;    // Risk multiplier after 2+ consecutive losses
input double InpMaxLots         = 0.0;    // Absolute lot cap (0 = none)
input double InpMarginUsePct    = 50.0;   // Max % of free margin one trade may use
input double InpMaxRiskOverrun  = 1.5;    // Refuse trade if min lot risks more than this x requested

input group "=== Account protection ==="
input double InpDailyLossPct    = 3.0;    // Stop for the day at this equity loss (0 = off)
input double InpWeeklyLossPct   = 6.0;    // Stop for the week at this equity loss (0 = off)
input double InpMaxDDPct        = 15.0;   // Kill-switch: drawdown from peak equity (0 = off)
input bool   InpKillFlatten     = true;   // Kill-switch also closes open EA positions
input bool   InpResetKill       = false;  // Set true for one start to clear a kill-switch / reset peak
input int    InpMaxConsecLosses = 3;      // Pause for the rest of the day after N losses in a row
input int    InpMaxTradesPerDay = 4;      // Entries per day
input int    InpMaxPositions    = 1;      // Simultaneous EA positions
input int    InpCooldownBars    = 4;      // Bars to wait after a losing trade

input group "=== Signal engine ==="
input int             InpHistoryBars   = 3000;
input ENUM_TIMEFRAMES InpHTF           = PERIOD_CURRENT;  // CURRENT = automatic
input double          InpScoreMin      = 1.7;
input int             InpMinConfluence = 2;
input int             InpMinGrade      = 1;               // 1=B 2=A 3=A+
input bool            InpModPullback   = true;
input bool            InpModSweep      = true;
input bool            InpModBreakout   = true;
input bool            InpModSqueeze    = true;
input bool            InpModVwap       = true;
input bool            InpModDiverge    = true;
input bool            InpModFvg        = true;
input bool            InpModRound      = true;
input bool            InpAdaptiveGate  = false;   // Switch off modules whose recent trial is clearly negative (see docs: can hurt)
input string          InpInterSymbol   = "";      // DXY-like symbol (blank = auto / EURUSD fallback)

input group "=== Trade plan ==="
input double InpTP1_R        = 1.0;
input double InpTP2_R        = 2.5;
input double InpPartialPct   = 50.0;
input double InpTrailATR     = 2.0;
input double InpSLMinATR     = 0.9;
input double InpSLMaxATR     = 2.6;
input int    InpHoldMinutes  = 480;

input group "=== Filters (GMT clock) ==="
input bool   InpSessionFilter = true;
input double InpTradeStartGMT = 7.0;
input double InpTradeEndGMT   = 20.0;
input double InpFridayCutGMT  = 19.0;     // No new entries after this on Fridays
input bool   InpFridayFlatten = true;
input double InpFlattenGMT    = 20.5;     // Friday: close everything at this time
input int    InpMaxSpreadPts  = 60;       // Points (XAUUSD 2-digit: 60 = 0.60)
input double InpMaxSpreadATR  = 12.0;     // ...and at most this % of ATR
input bool   InpUseNews       = true;
input int    InpNewsBefore    = 30;
input int    InpNewsAfter     = 30;
input bool   InpManualGmt     = false;
input double InpGmtOffsetHrs  = 2.0;

input group "=== Execution ==="
input long   InpMagic         = 20260901;
input int    InpSlippagePts   = 50;
input string InpComment       = "XAUS";

input group "=== Display ==="
input bool   InpShowPanel     = true;
input int    InpPanelX        = 12;
input int    InpPanelY        = 24;
input int    InpFontSize      = 9;

//--- position bookkeeping ----------------------------------------------
#define XS_MAXPOS 16
ulong   g_st_ticket[XS_MAXPOS];
double  g_st_r0[XS_MAXPOS];       // initial risk distance (price)
double  g_st_vol0[XS_MAXPOS];
int     g_st_stage[XS_MAXPOS];    // 0 = before TP1, 1 = after
double  g_st_ext[XS_MAXPOS];      // best favourable excursion (price distance)
double  g_st_atr[XS_MAXPOS];      // ATR at entry (trail distance)
int     g_st_n = 0;

//--- state ----------------------------------------------------------------
CXauEngine g_eng;
CXauNews   g_news;
CTrade     g_trade;
XRATESARR(g_rates);
XRATESARR(g_hrates);
XRATESARR(g_irates);
ENUM_TIMEFRAMES g_htf = PERIOD_H1;
string   g_inter_sym = "";
bool     g_inter_invert = false;
datetime g_last_bar = 0;
bool     g_engine_ok = false;
XSignal  g_last_sig;
int      g_last_reason = XR_WARMUP;
string   g_skip_note = "";
datetime g_last_loss_bar = 0;
int      g_gate_off = 0;
long     g_gate_day = -1;
int      g_gate_en[XM_COUNT];
int      g_rows_prev = 20;

void DrawPanel();

// risk state
double   g_day_start_eq = 0.0, g_week_start_eq = 0.0, g_peak_eq = 0.0;
long     g_day_id = -1, g_week_id = -1;
bool     g_kill = false, g_day_block = false, g_week_block = false;
string   g_block_note = "";

// stats from deal history
bool     g_stats_dirty = true;
int      g_consec_losses = 0, g_trades_today = 0;
int      g_tot_n = 0, g_tot_win = 0;
double   g_tot_gross_win = 0.0, g_tot_gross_loss = 0.0, g_tot_profit = 0.0;
double   g_day_pl = 0.0;

string   g_news_note = "";
bool     g_news_blocked = false;

//+------------------------------------------------------------------+
string GvName(const string tag)
{
   return "XS_" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN)) + "_" + IntegerToString(InpMagic) + "_" + tag;
}

string GvPos(const ulong ticket, const string tag)
{
   return "XSP_" + IntegerToString((long)ticket) + "_" + tag;
}

double RiskCapped()
{
   return XClamp(InpRiskPct, 0.05, XS_MAX_RISK_PCT);
}

//+------------------------------------------------------------------+
int InputModuleOn(const int m)
{
   switch(m)
   {
      case XM_PULLBACK: return InpModPullback ? 1 : 0;
      case XM_SWEEP:    return InpModSweep    ? 1 : 0;
      case XM_BREAKOUT: return InpModBreakout ? 1 : 0;
      case XM_SQUEEZE:  return InpModSqueeze  ? 1 : 0;
      case XM_VWAP:     return InpModVwap     ? 1 : 0;
      case XM_DIVERGE:  return InpModDiverge  ? 1 : 0;
      case XM_FVG:      return InpModFvg      ? 1 : 0;
      case XM_ROUND:    return InpModRound    ? 1 : 0;
   }
   return 0;
}

//+------------------------------------------------------------------+
void ApplyConfig()
{
   XConfig c;
   c.Defaults();
   c.base_sec = PeriodSeconds((ENUM_TIMEFRAMES)_Period);
   c.htf_sec = PeriodSeconds(g_htf);
   c.gmt_offset_sec = XGmtOffsetSec(InpManualGmt, InpGmtOffsetHrs);
   c.use_session_filter = InpSessionFilter;
   c.trade_start = InpTradeStartGMT;
   c.trade_end = InpTradeEndGMT;
   c.fri_cutoff = InpFridayCutGMT;
   c.score_min = InpScoreMin;
   c.min_confluence = InpMinConfluence;
   c.min_grade = InpMinGrade;
   for(int m = 0; m < XM_COUNT; m++) c.en[m] = InputModuleOn(m) & g_gate_en[m];
   c.tp1_r = InpTP1_R;
   c.tp2_r = XMax(InpTP2_R, InpTP1_R + 0.1);
   c.partial_pct = XClamp(InpPartialPct / 100.0, 0.0, 1.0);
   c.trail_atr = InpTrailATR;
   c.sl_atr_min = InpSLMinATR;
   c.sl_atr_max = XMax(InpSLMaxATR, InpSLMinATR + 0.1);
   c.hold_minutes = InpHoldMinutes;
   const double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   const double sp = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * pt;
   c.cost_price = XMax(sp * 1.5, 0.10);
   g_eng.cfg = c;
   g_news.gmt_offset_sec = c.gmt_offset_sec;
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_htf = (InpHTF == PERIOD_CURRENT) ? XAutoHTF((ENUM_TIMEFRAMES)_Period) : InpHTF;
   if(PeriodSeconds(g_htf) <= PeriodSeconds((ENUM_TIMEFRAMES)_Period)) g_htf = XAutoHTF((ENUM_TIMEFRAMES)_Period);

   string up = _Symbol;
   StringToUpper(up);
   if(StringFind(up, "XAU") < 0 && StringFind(up, "GOLD") < 0)
      Print("XAU Sniper: WARNING - ", _Symbol, " does not look like gold. The engine is tuned for XAUUSD.");
   if(InpRiskPct > XS_MAX_RISK_PCT) Print("XAU Sniper: risk per trade capped at ", DoubleToString(XS_MAX_RISK_PCT, 1), "% (requested ", DoubleToString(InpRiskPct, 2), "%).");
   if(InpRiskPct > 2.0) Print("XAU Sniper: WARNING - risk above 2% per trade makes a losing streak very costly.");

   for(int m = 0; m < XM_COUNT; m++) g_gate_en[m] = 1;
   if(MQLInfoInteger(MQL_TESTER)) { GlobalVariablesDeleteAll("XS_"); GlobalVariablesDeleteAll("XSP_"); }
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetAsyncMode(false);

   g_inter_sym = XResolveInterSymbol(InpInterSymbol, g_inter_invert);
   g_news.before_min = InpNewsBefore;
   g_news.after_min = InpNewsAfter;
   g_news.min_importance = 3;

   const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(InpResetKill)
   {
      GlobalVariableDel(GvName("KILL"));
      GlobalVariableDel(GvName("PEAK"));
      Print("XAU Sniper: kill-switch and peak equity reset.");
   }
   g_kill = GlobalVariableCheck(GvName("KILL"));
   g_peak_eq = GlobalVariableCheck(GvName("PEAK")) ? GlobalVariableGet(GvName("PEAK")) : eq;
   if(g_peak_eq < eq) g_peak_eq = eq;
   g_day_start_eq = eq; g_week_start_eq = eq;
   g_day_id = -1; g_week_id = -1;
   g_last_sig.Reset();

   // recover management state of positions that were open when the EA was restarted
   g_st_n = 0;
   ApplyConfig();
   EventSetTimer(2);
   g_stats_dirty = true;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(MQLInfoInteger(MQL_TESTER)) { GlobalVariablesDeleteAll("XS_"); GlobalVariablesDeleteAll("XSP_"); }
   ObjectsDeleteAll(0, "XS_");
}

//+------------------------------------------------------------------+
//| position state                                                    |
//+------------------------------------------------------------------+
void StSave(const int k)
{
   const ulong t = g_st_ticket[k];
   GlobalVariableSet(GvPos(t, "R"), g_st_r0[k]);
   GlobalVariableSet(GvPos(t, "V"), g_st_vol0[k]);
   GlobalVariableSet(GvPos(t, "S"), (double)g_st_stage[k]);
   GlobalVariableSet(GvPos(t, "E"), g_st_ext[k]);
   GlobalVariableSet(GvPos(t, "A"), g_st_atr[k]);
}

int StIndex(const ulong ticket, const bool create)
{
   for(int i = 0; i < g_st_n; i++) if(g_st_ticket[i] == ticket) return i;
   if(!create || g_st_n >= XS_MAXPOS) return -1;
   const int k = g_st_n++;
   g_st_ticket[k] = ticket;
   if(GlobalVariableCheck(GvPos(ticket, "R")))
   {
      g_st_r0[k]    = GlobalVariableGet(GvPos(ticket, "R"));
      g_st_vol0[k]  = GlobalVariableGet(GvPos(ticket, "V"));
      g_st_stage[k] = (int)GlobalVariableGet(GvPos(ticket, "S"));
      g_st_ext[k]   = GlobalVariableGet(GvPos(ticket, "E"));
      g_st_atr[k]   = GlobalVariableGet(GvPos(ticket, "A"));
   }
   else
   {
      const double open = PositionGetDouble(POSITION_PRICE_OPEN);
      const double sl = PositionGetDouble(POSITION_SL);
      g_st_r0[k] = (sl > 0.0) ? MathAbs(open - sl) : 0.0;
      g_st_vol0[k] = PositionGetDouble(POSITION_VOLUME);
      g_st_stage[k] = 0;
      g_st_ext[k] = 0.0;
      g_st_atr[k] = (g_engine_ok && g_eng.n > 2) ? g_eng.m_atr[g_eng.n - 2] : 0.0;
      StSave(k);
   }
   return k;
}

void StDrop(const int k)
{
   const ulong t = g_st_ticket[k];
   GlobalVariableDel(GvPos(t, "R")); GlobalVariableDel(GvPos(t, "V")); GlobalVariableDel(GvPos(t, "S"));
   GlobalVariableDel(GvPos(t, "E")); GlobalVariableDel(GvPos(t, "A"));
   g_st_n--;
   if(k < g_st_n)
   {
      g_st_ticket[k] = g_st_ticket[g_st_n]; g_st_r0[k] = g_st_r0[g_st_n]; g_st_vol0[k] = g_st_vol0[g_st_n];
      g_st_stage[k] = g_st_stage[g_st_n]; g_st_ext[k] = g_st_ext[g_st_n]; g_st_atr[k] = g_st_atr[g_st_n];
   }
}

int CountPositions()
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      c++;
   }
   return c;
}

// any position on this symbol at all (netting accounts merge positions)
bool AnyPositionOnSymbol()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol) return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| order helpers                                                     |
//+------------------------------------------------------------------+
bool RetOk(const uint rc)
{
   return (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED || rc == TRADE_RETCODE_DONE_PARTIAL);
}

bool RetRetry(const uint rc)
{
   return (rc == TRADE_RETCODE_REQUOTE || rc == TRADE_RETCODE_PRICE_CHANGED || rc == TRADE_RETCODE_PRICE_OFF);
}

bool ClosePart(const ulong ticket, const double volume)
{
   for(int a = 0; a < 3; a++)
   {
      bool ok;
      if(volume <= 0.0) ok = g_trade.PositionClose(ticket);
      else              ok = g_trade.PositionClosePartial(ticket, volume);
      const uint rc = g_trade.ResultRetcode();
      if(ok && RetOk(rc)) return true;
      if(!RetRetry(rc)) break;
      Sleep(150);
   }
   Print("XAU Sniper: close failed, retcode ", (int)g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
   return false;
}

void CloseAllOurs(const string why)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      Print("XAU Sniper: closing position ", (long)t, " - ", why);
      ClosePart(t, 0.0);
   }
}

//+------------------------------------------------------------------+
//| per-tick position management                                      |
//+------------------------------------------------------------------+
void ManagePositions()
{
   if(PositionsTotal() == 0) { if(g_st_n > 0) { while(g_st_n > 0) StDrop(g_st_n - 1); } return; }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;
   const double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   const double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   const double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   const double stops = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   const double spread_px = tick.ask - tick.bid;
   const int period_sec = PeriodSeconds((ENUM_TIMEFRAMES)_Period);
   const int maxh = g_eng.MaxHold();
   const datetime now = TimeCurrent();
   const int gmt_off = XGmtOffsetSec(InpManualGmt, InpGmtOffsetHrs);

   bool seen[XS_MAXPOS];
   for(int q = 0; q < XS_MAXPOS; q++) seen[q] = false;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      const int k = StIndex(ticket, true);
      if(k < 0) continue;
      seen[k] = true;

      const bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      const int dir = buy ? 1 : -1;
      const double open = PositionGetDouble(POSITION_PRICE_OPEN);
      const double cur_sl = PositionGetDouble(POSITION_SL);
      const double cur_tp = PositionGetDouble(POSITION_TP);
      const double vol = PositionGetDouble(POSITION_VOLUME);
      const double px = buy ? tick.bid : tick.ask;              // price we would close at
      const double fav = dir * (px - open);
      const double r0 = g_st_r0[k];
      if(fav > g_st_ext[k]) { g_st_ext[k] = fav; }

      // --- time stop and Friday flatten
      const datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      if(now - opened >= (datetime)(maxh * period_sec))
      {
         Print("XAU Sniper: time stop on ", (long)ticket);
         ClosePart(ticket, 0.0);
         continue;
      }
      if(InpFridayFlatten && XWeekdayGmt(now, gmt_off) == 5 && XHourGmt(now, gmt_off) >= InpFlattenGMT)
      {
         Print("XAU Sniper: Friday flatten on ", (long)ticket);
         ClosePart(ticket, 0.0);
         continue;
      }
      if(r0 <= 0.0) continue;

      // --- first target: partial close, stop to break-even
      if(g_st_stage[k] == 0 && fav >= InpTP1_R * r0)
      {
         const double want = XClamp(InpPartialPct / 100.0, 0.0, 1.0);
         const double vc = MathFloor(g_st_vol0[k] * want / vstep + 1e-9) * vstep;
         const bool close_all = (want >= 0.999) || (vc > 0.0 && (vol - vc) < vmin - 1e-9);
         if(close_all) { ClosePart(ticket, 0.0); continue; }
         if(vc >= vmin - 1e-9)
         {
            if(!ClosePart(ticket, vc)) continue;
         }
         const double be = NormalizeDouble(open + dir * spread_px, _Digits);
         const bool sl_ok = buy ? (be > cur_sl && (tick.bid - be) > stops)
                                : ((cur_sl == 0.0 || be < cur_sl) && (be - tick.ask) > stops);
         if(sl_ok) g_trade.PositionModify(ticket, be, cur_tp);
         g_st_stage[k] = 1;
         StSave(k);
         continue;
      }

      // --- runner: ATR chandelier trail on the best excursion
      if(g_st_stage[k] == 1 && g_st_atr[k] > 0.0)
      {
         double tsl = open + dir * (g_st_ext[k] - InpTrailATR * g_st_atr[k]);
         tsl = NormalizeDouble(tsl, _Digits);
         const double step = 2.0 * pt;
         bool better = buy ? (tsl > cur_sl + step) : (cur_sl == 0.0 || tsl < cur_sl - step);
         bool room = buy ? ((tick.bid - tsl) > stops) : ((tsl - tick.ask) > stops);
         if(better && room)
         {
            if(g_trade.PositionModify(ticket, tsl, cur_tp)) StSave(k);
         }
      }
   }
   // forget state of positions that no longer exist
   for(int k = g_st_n - 1; k >= 0; k--) if(!seen[k]) StDrop(k);
}

//+------------------------------------------------------------------+
//| deal history: streaks, trades today, live statistics              |
//+------------------------------------------------------------------+
void RecomputeStats()
{
   g_stats_dirty = false;
   const datetime now = TimeCurrent();
   const long day_now = (long)TimeTradeServer() / 86400;
   if(!HistorySelect(now - 45 * 86400, now + 3600)) return;
   const int total = HistoryDealsTotal();

   ulong    pid[256];
   double   pl[256];
   datetime tlast[256];
   datetime tfirst[256];
   bool     has_out[256];
   int      cnt = 0;

   for(int i = 0; i < total; i++)
   {
      const ulong tk = HistoryDealGetTicket(i);
      if(tk == 0) continue;
      if(HistoryDealGetInteger(tk, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetString(tk, DEAL_SYMBOL) != _Symbol) continue;
      const long entry = HistoryDealGetInteger(tk, DEAL_ENTRY);
      const long typ = HistoryDealGetInteger(tk, DEAL_TYPE);
      if(typ != DEAL_TYPE_BUY && typ != DEAL_TYPE_SELL) continue;
      const ulong id = (ulong)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      const datetime dt = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      const double p = HistoryDealGetDouble(tk, DEAL_PROFIT) + HistoryDealGetDouble(tk, DEAL_SWAP) + HistoryDealGetDouble(tk, DEAL_COMMISSION);
      int k = -1;
      for(int j = 0; j < cnt; j++) if(pid[j] == id) { k = j; break; }
      if(k < 0)
      {
         if(cnt >= 256) continue;
         k = cnt++;
         pid[k] = id; pl[k] = 0.0; tlast[k] = dt; tfirst[k] = dt; has_out[k] = false;
      }
      pl[k] += p;
      if(dt < tfirst[k]) tfirst[k] = dt;
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY || entry == DEAL_ENTRY_INOUT)
      {
         has_out[k] = true;
         if(dt > tlast[k]) tlast[k] = dt;
      }
   }
   // positions still open are not "closed trades"
   ulong open_ids[XS_MAXPOS];
   int no = 0;
   for(int i = PositionsTotal() - 1; i >= 0 && no < XS_MAXPOS; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      open_ids[no++] = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
   }
   // order closed trades by close time (insertion sort on index list)
   int order[256];
   int nc = 0;
   for(int j = 0; j < cnt; j++)
   {
      bool is_open = false;
      for(int q = 0; q < no; q++) if(open_ids[q] == pid[j]) is_open = true;
      if(!has_out[j] || is_open) continue;
      int pos = nc;
      while(pos > 0 && tlast[order[pos - 1]] > tlast[j]) { order[pos] = order[pos - 1]; pos--; }
      order[pos] = j;
      nc++;
   }
   g_tot_n = nc; g_tot_win = 0; g_tot_gross_win = 0.0; g_tot_gross_loss = 0.0; g_tot_profit = 0.0;
   for(int a = 0; a < nc; a++)
   {
      const double p = pl[order[a]];
      g_tot_profit += p;
      if(p > 0.0) { g_tot_win++; g_tot_gross_win += p; }
      else        { g_tot_gross_loss += -p; }
   }
   g_consec_losses = 0;
   for(int a = nc - 1; a >= 0; a--)
   {
      if(pl[order[a]] < 0.0) g_consec_losses++;
      else break;
   }
   // last losing trade bar (for cooldown)
   g_last_loss_bar = 0;
   if(nc > 0 && pl[order[nc - 1]] < 0.0) g_last_loss_bar = tlast[order[nc - 1]];

   g_trades_today = 0;
   g_day_pl = 0.0;
   for(int j = 0; j < cnt; j++)
   {
      if((long)tfirst[j] / 86400 == day_now) g_trades_today++;
      if(has_out[j] && (long)tlast[j] / 86400 == day_now) g_day_pl += pl[j];
   }
}

//+------------------------------------------------------------------+
//| account protection                                                |
//+------------------------------------------------------------------+
void UpdateRisk()
{
   const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq <= 0.0) return;
   const long day = (long)TimeTradeServer() / 86400;
   const long week = (day + 3) / 7;
   if(day != g_day_id)
   {
      g_day_id = day;
      g_day_start_eq = eq;
      g_day_block = false;
      g_stats_dirty = true;
   }
   if(week != g_week_id)
   {
      g_week_id = week;
      g_week_start_eq = eq;
      g_week_block = false;
   }
   if(eq > g_peak_eq)
   {
      g_peak_eq = eq;
      GlobalVariableSet(GvName("PEAK"), g_peak_eq);
   }
   g_block_note = "";
   if(!g_kill && InpMaxDDPct > 0.0 && g_peak_eq > 0.0 && 100.0 * (g_peak_eq - eq) / g_peak_eq >= InpMaxDDPct)
   {
      g_kill = true;
      GlobalVariableSet(GvName("KILL"), 1.0);
      Print("XAU Sniper: KILL-SWITCH - drawdown ", DoubleToString(100.0 * (g_peak_eq - eq) / g_peak_eq, 1), "% from peak. Trading stopped.");
      if(InpKillFlatten) CloseAllOurs("kill-switch");
   }
   if(!g_day_block && InpDailyLossPct > 0.0 && g_day_start_eq > 0.0 && 100.0 * (g_day_start_eq - eq) / g_day_start_eq >= InpDailyLossPct)
   {
      g_day_block = true;
      Print("XAU Sniper: daily loss limit reached - no new trades today.");
   }
   if(!g_week_block && InpWeeklyLossPct > 0.0 && g_week_start_eq > 0.0 && 100.0 * (g_week_start_eq - eq) / g_week_start_eq >= InpWeeklyLossPct)
   {
      g_week_block = true;
      Print("XAU Sniper: weekly loss limit reached - no new trades this week.");
   }
   if(g_kill)            g_block_note = "KILL-SWITCH: drawdown limit hit (set InpResetKill to clear)";
   else if(g_week_block) g_block_note = "paused: weekly loss limit";
   else if(g_day_block)  g_block_note = "paused: daily loss limit";
}

// returns "" when a new entry is allowed
string EntryBlocked(const XSignal &s)
{
   if(g_kill) return "kill-switch active";
   if(g_week_block) return "weekly loss limit";
   if(g_day_block) return "daily loss limit";
   if(InpMaxConsecLosses > 0 && g_consec_losses >= InpMaxConsecLosses) return "paused after " + IntegerToString(g_consec_losses) + " losses in a row";
   if(InpMaxTradesPerDay > 0 && g_trades_today >= InpMaxTradesPerDay) return "max trades today";
   if(CountPositions() >= XMaxI(1, InpMaxPositions)) return "position already open";
   if(AnyPositionOnSymbol() && AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) return "netting account: symbol already in use";
   if(InpCooldownBars > 0 && g_last_loss_bar > 0 &&
      TimeCurrent() - g_last_loss_bar < (datetime)(InpCooldownBars * PeriodSeconds((ENUM_TIMEFRAMES)_Period))) return "cooldown after loss";
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return "auto-trading disabled";
   if(SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL) return "symbol not fully tradable now";
   const double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   const double sp_pts = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPts > 0 && sp_pts > InpMaxSpreadPts) return "spread " + DoubleToString(sp_pts * pt, 2) + " too wide";
   if(InpMaxSpreadATR > 0.0 && s.atr > 0.0 && sp_pts * pt > InpMaxSpreadATR / 100.0 * s.atr) return "spread too large vs ATR";
   if(InpUseNews && g_news_blocked) return "news: " + g_news_note;
   return "";
}

//+------------------------------------------------------------------+
//| engine refresh + entry                                            |
//+------------------------------------------------------------------+
bool RefreshEngine()
{
   const int want = XMaxI(InpHistoryBars, 900);
   const int got = XLoadRates(_Symbol, (ENUM_TIMEFRAMES)_Period, want, g_rates);
   if(got < 700) { g_engine_ok = false; return false; }
   ApplyConfig();
   const int need_h = (int)((double)got * g_eng.cfg.base_sec / g_eng.cfg.htf_sec) + 320;
   const int gh = XLoadRates(_Symbol, g_htf, need_h, g_hrates);
   if(gh < 300) { g_engine_ok = false; return false; }   // never trade without the higher-timeframe bias
   g_eng.SetBase(g_rates, got);
   g_eng.SetHTF(g_hrates, gh);
   if(StringLen(g_inter_sym) > 0)
   {
      const int gi = XLoadRates(g_inter_sym, (ENUM_TIMEFRAMES)_Period, got + 50, g_irates);
      if(gi > 100) g_eng.SetInter(g_irates, gi, g_inter_invert);
   }
   if(!g_eng.Compute()) { g_engine_ok = false; return false; }
   g_engine_ok = true;

   if(InpAdaptiveGate)
   {
      const long day = (long)TimeTradeServer() / 86400;
      if(day != g_gate_day)
      {
         g_gate_day = day;
         XTrial tr;
         g_eng.RunTrial(g_eng.cfg.warmup, g_eng.n - 2, tr);
         g_gate_off = g_eng.ApplyGating(tr, 20, -0.25);
         for(int m = 0; m < XM_COUNT; m++) g_gate_en[m] = g_eng.cfg.en[m];
      }
      for(int m = 0; m < XM_COUNT; m++) g_eng.cfg.en[m] = InputModuleOn(m) & g_gate_en[m];
      g_eng.ComputeScores();
   }
   return true;
}

double GradeMult(const int grade)
{
   if(!InpGradeScaling) return 1.0;
   if(grade >= 3) return 1.4;
   if(grade == 2) return 1.0;
   return 0.6;
}

bool SendOrder(const bool buy, const double lots, const double sl, const double tp, const string cmt)
{
   for(int a = 0; a < 3; a++)
   {
      MqlTick tk;
      if(!SymbolInfoTick(_Symbol, tk)) return false;
      const double price = buy ? tk.ask : tk.bid;
      bool ok = buy ? g_trade.Buy(lots, _Symbol, price, sl, tp, cmt) : g_trade.Sell(lots, _Symbol, price, sl, tp, cmt);
      const uint rc = g_trade.ResultRetcode();
      if(ok && RetOk(rc)) return true;
      if(!RetRetry(rc)) break;
      Sleep(150);
   }
   Print("XAU Sniper: order failed, retcode ", (int)g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
   return false;
}

void TryEnter()
{
   g_skip_note = "";
   const int i = g_eng.n - 2;                       // last CLOSED bar
   XSignal s;
   const bool has = g_eng.Evaluate(i, s);
   g_last_reason = s.reason;
   if(!has) return;
   g_last_sig = s;

   const string blocked = EntryBlocked(s);
   if(StringLen(blocked) > 0) { g_skip_note = "signal skipped: " + blocked; Print("XAU Sniper: ", g_skip_note); return; }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk)) return;
   const bool buy = (s.dir > 0);
   const double entry = buy ? tk.ask : tk.bid;
   const double dist = buy ? (entry - s.sl) : (s.sl - entry);
   if(dist < 0.4 * s.atr || dist > g_eng.cfg.sl_atr_max * s.atr * 1.3)
   {
      g_skip_note = "signal skipped: price moved, stop distance no longer valid";
      Print("XAU Sniper: ", g_skip_note);
      return;
   }
   const double stops = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(dist <= stops) { g_skip_note = "signal skipped: stop inside broker minimum distance"; return; }

   double risk = RiskCapped() * GradeMult(s.grade);
   if(g_consec_losses >= 2) risk *= XClamp(InpStreakScale, 0.1, 1.0);
   risk = XMin(risk, XS_MAX_RISK_PCT);

   XLotPlan lp;
   XPlanLots(_Symbol, AccountInfoDouble(ACCOUNT_EQUITY), risk, dist, buy, entry, InpMaxRiskOverrun,
             InpMaxLots, AccountInfoDouble(ACCOUNT_MARGIN_FREE), XClamp(InpMarginUsePct, 5.0, 95.0) / 100.0, lp);
   if(!lp.ok)
   {
      g_skip_note = "signal skipped: " + lp.note;
      Print("XAU Sniper: ", g_skip_note);
      return;
   }
   const double sl = NormalizeDouble(s.sl, _Digits);
   const double tp = NormalizeDouble(entry + s.dir * g_eng.cfg.tp2_r * dist, _Digits);
   const string cmt = InpComment + " " + XGradeName(s.grade) + " " + (s.primary >= 0 ? XModuleShort(s.primary) : "-");
   if(SendOrder(buy, lp.lots, sl, tp, cmt))
   {
      Print("XAU Sniper: ", (buy ? "BUY " : "SELL "), DoubleToString(lp.lots, 2), " ", _Symbol, " grade ", XGradeName(s.grade),
            " entry ", DoubleToString(entry, _Digits), " SL ", DoubleToString(sl, _Digits), " TP2 ", DoubleToString(tp, _Digits),
            " risk ", DoubleToString(lp.risk_pct, 2), "% (", DoubleToString(lp.risk_money, 2), ")");
      g_stats_dirty = true;
   }
}

//+------------------------------------------------------------------+
void RefreshNews()
{
   if(!InpUseNews) { g_news_blocked = false; g_news_note = ""; return; }
   g_news.Refresh(TimeCurrent());
   string why;
   g_news_blocked = g_news.Blocked(TimeCurrent(), why);
   g_news_note = g_news_blocked ? why : g_news.NextText(TimeCurrent());
}

//+------------------------------------------------------------------+
void OnTick()
{
   UpdateRisk();
   ManagePositions();

   const datetime bt = iTime(_Symbol, (ENUM_TIMEFRAMES)_Period, 0);
   if(bt == g_last_bar || bt == 0) return;
   g_last_bar = bt;

   RefreshNews();
   if(g_stats_dirty) RecomputeStats();
   if(!RefreshEngine()) return;
   TryEnter();
   DrawPanel();
}

void OnTimer()
{
   if(g_stats_dirty) RecomputeStats();
   RefreshNews();
   DrawPanel();
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD) g_stats_dirty = true;
}

//+------------------------------------------------------------------+
//| custom optimisation criterion: rewards steadiness, not just profit|
//+------------------------------------------------------------------+
double OnTester()
{
   const double trades = TesterStatistics(STAT_TRADES);
   if(trades < 40.0) return 0.0;
   const double rf = TesterStatistics(STAT_RECOVERY_FACTOR);
   const double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   const double np = TesterStatistics(STAT_PROFIT);
   if(np <= 0.0) return np;
   return rf * XMin(pf, 3.0) * MathSqrt(trades);
}

//+------------------------------------------------------------------+
//| panel                                                             |
//+------------------------------------------------------------------+
void PutLine(const int row, const string text, const color clr, const int extra = 0)
{
   const int lh = InpFontSize + 6;
   XObjLabel("XS_P_" + IntegerToString(row), InpPanelX + 10, InpPanelY + 8 + row * lh, text, clr, InpFontSize + extra, "Consolas", CORNER_LEFT_UPPER);
}

void DrawPanel()
{
   if(!InpShowPanel) { ObjectsDeleteAll(0, "XS_"); return; }
   const color cText = XRGB(214, 222, 235), cDim = XRGB(132, 142, 158), cGreen = XRGB(0, 222, 132);
   const color cRed = XRGB(255, 92, 92), cGold = XRGB(255, 200, 64), cCyan = XRGB(64, 200, 255);
   const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   const int lh0 = InpFontSize + 6;
   XObjRectLabel("XS_PB", InpPanelX, InpPanelY, 470 + (InpFontSize - 9) * 30, g_rows_prev * lh0 + 18, XRGB(16, 20, 28), XRGB(58, 68, 88), CORNER_LEFT_UPPER);
   int row = 0;
   PutLine(row++, "XAU SNIPER   " + _Symbol + " " + XTfName((ENUM_TIMEFRAMES)_Period) + "   magic " + IntegerToString(InpMagic), cGold);

   string status = "SCANNING";
   color sc = cCyan;
   string sub = "waiting for a graded setup";
   const int np = CountPositions();
   if(g_kill)            { status = "STOPPED - KILL-SWITCH"; sc = cRed; sub = g_block_note; }
   else if(g_week_block || g_day_block) { status = "PAUSED"; sc = cGold; sub = g_block_note; }
   else if(np > 0)       { status = "IN TRADE (" + IntegerToString(np) + ")"; sc = cGreen; sub = "managing: partial, break-even, trail, time stop"; }
   else if(g_news_blocked) { status = "PAUSED - NEWS"; sc = cGold; sub = g_news_note; }
   else if(g_engine_ok)  sub = StringLen(g_skip_note) > 0 ? g_skip_note : XReasonText(g_last_reason);
   PutLine(row++, status, sc, 2);
   PutLine(row++, sub, cDim);

   PutLine(row++, "----------------------------------------", cDim);
   const double dd = (g_peak_eq > 0.0) ? 100.0 * (g_peak_eq - eq) / g_peak_eq : 0.0;
   const double dpl = (g_day_start_eq > 0.0) ? 100.0 * (eq - g_day_start_eq) / g_day_start_eq : 0.0;
   PutLine(row++, "Equity " + DoubleToString(eq, 2) + "   today " + StringFormat("%+.2f%%", dpl) + "   DD " + DoubleToString(dd, 1) + "%", cText);
   PutLine(row++, "Risk/trade " + DoubleToString(RiskCapped(), 2) + "%   limits: day " + DoubleToString(InpDailyLossPct, 1) + "%  week "
                  + DoubleToString(InpWeeklyLossPct, 1) + "%  DD " + DoubleToString(InpMaxDDPct, 0) + "%", cDim);
   PutLine(row++, "Trades today " + IntegerToString(g_trades_today) + "/" + IntegerToString(InpMaxTradesPerDay) + "   loss streak " + IntegerToString(g_consec_losses), cText);

   if(g_tot_n > 0)
   {
      const double pf = (g_tot_gross_loss > 1e-9) ? g_tot_gross_win / g_tot_gross_loss : 99.0;
      PutLine(row++, "Live (45d): " + IntegerToString(g_tot_n) + " trades  win " + DoubleToString(100.0 * g_tot_win / g_tot_n, 0) + "%  PF "
                     + DoubleToString(pf, 2) + "  P/L " + DoubleToString(g_tot_profit, 2), g_tot_profit >= 0.0 ? cGreen : cRed);
   }
   else PutLine(row++, "Live (45d): no closed trades yet", cDim);

   if(g_engine_ok)
   {
      const int n = g_eng.n;
      const int tb = g_eng.m_bias[n - 1];
      PutLine(row++, "Bias " + XTfName(g_htf) + ": " + (tb > 0 ? "BULL" : (tb < 0 ? "BEAR" : "NEUTRAL")) + "   ATR " + DoubleToString(g_eng.m_atr[n - 2], 2)
                     + "   spread " + DoubleToString((double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * SymbolInfoDouble(_Symbol, SYMBOL_POINT), 2), cText);
      string cl = "Votes:";
      for(int m = 0; m < XM_COUNT; m++)
      {
         const double v = g_eng.m_vote[(n - 2) * XM_COUNT + m];
         cl += " " + XModuleShort(m) + (v > 0.0 ? "+" : (v < 0.0 ? "-" : "."));
      }
      PutLine(row++, cl, cDim);
      if(InpAdaptiveGate) PutLine(row++, "Adaptive gate: " + IntegerToString(g_gate_off) + " module(s) off today", cDim);
   }
   if(InpUseNews) PutLine(row++, "News: " + g_news_note, g_news_blocked ? cRed : cDim);

   g_rows_prev = row;
   XObjRectLabel("XS_PB", InpPanelX, InpPanelY, 470 + (InpFontSize - 9) * 30, row * lh0 + 18, XRGB(16, 20, 28), XRGB(58, 68, 88), CORNER_LEFT_UPPER);
   for(int k = row; k < row + 6; k++) XObjDelete("XS_P_" + IntegerToString(k));
}
