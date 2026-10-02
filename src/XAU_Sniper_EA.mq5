//+------------------------------------------------------------------+
//|                                               XAU_Sniper_EA.mq5  |
//|  Automated XAUUSD trader. Uses the same engine and the same       |
//|  daily STRATEGY LAB as the XAU_Oracle indicator, so it trades     |
//|  exactly the strategy the indicator shows: the one that won at    |
//|  least the target share of trades (default 60%) with a positive   |
//|  average result, walk-forward, on this chart's own history.       |
//|                                                                  |
//|  Fixed-fractional risk sized with the broker's own profit formula,|
//|  hard account protection (daily / weekly loss, drawdown kill-     |
//|  switch), spread / session / news filters, per-strategy exits     |
//|  (partial, break-even, trail, mean-reversion exit, time stop).    |
//|                                                                  |
//|  NO strategy wins every trade and none can guarantee profit.     |
//|  Test on your broker's real ticks and start on a demo account.   |
//+------------------------------------------------------------------+
#property copyright   "XAU Sniper"
#property version     "2.00"
#property description "XAUUSD EA: trades only the strategy that passed the Strategy Lab on this chart"
#property description "(>= 60% winning trades with profit, walk-forward). Strict risk management. Not a guarantee of profit."

#include <Trade/Trade.mqh>
#include <XAU/XAU_Platform.mqh>

// Hard ceiling for risk per trade (percent of equity). Guard against typos and against chasing a
// "double every month" target: see docs/RISK_MATH.md before raising it.
#define XS_MAX_RISK_PCT 5.0

// How the EA behaves on a DEMO account. Real accounts always use the real-account rules.
enum ENUM_XAU_DEMO
{
   XAU_DEMO_REHEARSAL = 0,   // Rehearsal: exactly the real-account rules (the demo proves what a real account would do)
   XAU_DEMO_FREE      = 1    // Free run: protections only warn, more trades (not a preview of a real account)
};

//--- inputs -----------------------------------------------------------
input group "=== What to trade ==="
input ENUM_XAU_MODE  InpMode         = XAU_MODE_AUTO; // Mode (AUTO: TREND on H1/H4, STEADY elsewhere)
input double InpTrendWinTarget       = 50.0;   // TREND mode: Lab target (% winners); multi-day exits win less often but more
input int    InpTrendMaxPositions    = 3;      // TREND mode: open positions at once (one per passing strategy)
input double InpMaxOpenRiskPct       = 3.0;    // TREND mode: total risk of all open positions (% of equity)
input ENUM_XAU_STRAT InpStrategy     = XAU_ST_AUTO;  // Strategy (AUTO = the one that passed the Strategy Lab here)
input ENUM_XAU_EXIT  InpExit         = XAU_EX_AUTO;  // Exit style (AUTO = chosen together with the strategy)
input double InpWinTarget            = 60.0;   // Strategy Lab: minimum % of winning trades
input int    InpLabMinTrades         = 50;     // Strategy Lab: minimum trades before a strategy can qualify
input int    InpLabFolds             = 5;      // Strategy Lab: walk-forward folds
input int    InpHistoryBars          = 0;      // Bars the lab tests (0 = auto: 25,000 on H1, else 10,000; keep equal to the indicator)
input ENUM_XAU_D1 InpDailyTrend      = XAU_D1_AUTO;  // Daily trend filter (AUTO: H1 and above buy only in a daily uptrend)
input int    InpSignalBars           = 3000;   // Bars used for live signals (faster; same signals, tested)

input group "=== Risk ==="
input double InpRiskPct         = 1.0;    // Risk per trade, % of equity (hard ceiling 5)
input double InpStreakScale     = 0.5;    // Risk multiplier after 2+ consecutive losses
input bool   InpD1Scale         = true;   // Halve risk when the daily trend opposes the trade
input double InpMaxLots         = 0.0;    // Absolute lot cap (0 = none)
input double InpMarginUsePct    = 50.0;   // Max % of free margin one trade may use
input double InpMaxRiskOverrun  = 1.5;    // Refuse trade if min lot risks more than this x requested

input group "=== Demo accounts ==="
input ENUM_XAU_DEMO InpDemoMode = XAU_DEMO_REHEARSAL;  // REHEARSAL = real-account rules (recommended); FREE RUN = warnings only. Ignored on real accounts
input bool   InpDemoUnproven    = false;  // Free run only: also trade the closest strategy when none passed the lab (lost on real data)
input double InpDemoMaxRiskPct  = 10.0;   // Free run only: skip a trade when even the smallest lot risks more than this % of equity
input int    InpDemoMaxPositions = 5;     // Free run only: simultaneous EA trades

input group "=== Your own trades ==="
input bool   InpProtectManual   = false;  // Add a stop to ANY position on this symbol that has none (your manual trades too)
input double InpProtectPct      = 5.0;    // ...placed where that position would lose this % of equity (from now if it is already losing)

input group "=== Account protection ==="
input double InpDailyLossPct    = 3.0;    // Stop for the day at this equity loss (0 = off)
input double InpWeeklyLossPct   = 6.0;    // Stop for the week at this equity loss (0 = off)
input double InpMaxDDPct        = 15.0;   // Kill-switch: drawdown from peak equity (0 = off)
input bool   InpKillFlatten     = true;   // Kill-switch also closes open EA positions
input bool   InpResetKill       = false;  // Set true for one start to clear a kill-switch / reset peak
input int    InpMaxConsecLosses = 3;      // Pause after N losses in a row (until tomorrow or until paper trades recover)
input bool   InpPaperResume     = true;   // During that pause, paper-trade the signals and resume as soon as they recover
input int    InpMaxTradesPerDay = 6;      // Entries per day
input int    InpMaxPositions    = 1;      // Simultaneous EA positions
input int    InpCooldownBars    = 2;      // Bars to wait after a losing trade
input bool   InpOneTradePerSymbol = false;// true = never open while ANY position (manual trades too) exists on this symbol
input bool   InpDailyLossRealized = false;// Daily limit counts closed trades only (default: equity incl. floating)

input group "=== Filters (London local clock) ==="
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
input double InpGmtOffsetHrs  = 2.0;              // Broker server time minus GMT in WINTER (hours)
input ENUM_XAU_DST InpServerDst = XAU_DST_US;     // Server clock daylight-saving behaviour
input bool   InpLondonSessions = true;            // Session hours are London local time (follow UK DST)
input double InpOrbStartHour  = 1.0;              // Daily open on the SERVER clock (New-York-close brokers: 1)

input group "=== Engine details (advanced) ==="
input ENUM_TIMEFRAMES InpHTF    = PERIOD_CURRENT; // Higher timeframe for the trend (CURRENT = automatic)
input double InpScoreMin        = 1.7;    // Confluence strategy: score needed
input int    InpMinConfluence   = 2;      // Confluence strategy: agreeing modules needed
input double InpAdrBlock        = 0.90;   // No trend-continuation setups after this share of the daily range
input int    InpOrbRangeMin     = 60;     // Opening range: minutes that form it
input int    InpOrbSettleMin    = 180;    // Opening range: quiet minutes before it is final
input bool   InpOrbSolo         = false;  // Force the opening-range strategy (GOLD_ORB mode)
input double InpTP1_R           = 1.0;    // Classic exit: first target (R)
input double InpTP2_R           = 2.5;    // Classic exit: runner target (R)
input double InpPartialPct      = 50.0;   // Classic exit: % closed at the first target
input double InpTrailATR        = 2.0;    // Classic exit: trail distance (ATR)
input double InpSLMinATR        = 0.9;    // Minimum stop distance (ATR)
input double InpSLMaxATR        = 2.6;    // Skip setups needing a wider stop (ATR)
input int    InpHoldMinutes     = 480;    // Time stop for trades that go nowhere
input double InpCostPrice       = 0.35;   // Round-trip spread + slippage charged per tested trade (price units; keep equal to the indicator)
input double InpMinStopCosts    = 20.0;   // Skip setups whose stop is shorter than this many round-trip costs (0 = off; keep equal to the indicator)
input string InpInterSymbol     = "";     // DXY-like symbol (blank = auto / EURUSD fallback)

input group "=== Execution ==="
input long   InpMagic         = 20260901;
input int    InpSlippagePts   = 50;
input string InpComment       = "XAUS";

input group "=== Display ==="
input bool   InpShowPanel     = true;
input ENUM_XAU_PANEL_POS InpPanelPos = XAU_PANEL_BOTTOM_LEFT;   // Panel position (the indicator uses the top left)
input int    InpFontSize      = 10;

//--- position bookkeeping ----------------------------------------------
#define XS_MAXPOS 16
ulong   g_st_ticket[XS_MAXPOS];
double  g_st_r0[XS_MAXPOS];       // initial risk distance (price)
double  g_st_vol0[XS_MAXPOS];
int     g_st_stage[XS_MAXPOS];    // 0 = before the first target, 1 = after
double  g_st_ext[XS_MAXPOS];      // best favourable excursion (price distance)
double  g_st_atr[XS_MAXPOS];      // ATR at entry (trail distance)
int     g_st_prof[XS_MAXPOS];     // exit profile the trade was opened with
int     g_st_n = 0;

//--- state ----------------------------------------------------------------
CXauEngine g_eng;        // live signals
CXauEngine g_lab;        // daily Strategy Lab (same window as the indicator)
CXauNews   g_news;
CTrade     g_trade;
CXPaper    g_paper;      // paper trades while a loss-streak pause is active
CXPanel    g_panel;
XRATESARR(g_rates);
XRATESARR(g_hrates);
XRATESARR(g_irates);
XRATESARR(g_drates);
int      g_hist = 10000;          // Strategy Lab window (resolved from InpHistoryBars)
int      g_mode = XAU_MODE_STEADY;  // resolved InpMode
int      g_pass[XLAB_CELLS];      // TREND mode: passing cells, best first
int      g_npass = 0;
ENUM_TIMEFRAMES g_htf = PERIOD_H1;
string   g_inter_sym = "";
bool     g_inter_invert = false;
datetime g_last_bar = 0;
bool     g_engine_ok = false;
XSignal  g_last_sig;
int      g_last_reason = XR_WARMUP;
string   g_skip_note = "";
bool     g_small = false;        // the last sized signal was refused: the account is too small for the smallest lot
string   g_small_note = "";
datetime g_last_loss_bar = 0;

// strategy in use
datetime g_lab_day = 0;
bool     g_lab_ok = false;
int      g_cell = -1;
bool     g_proven = false;
int      g_act_s = -1;
int      g_act_p = XP_CLASSIC;
XExit    g_act_x;

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

void DrawPanel();

//+------------------------------------------------------------------+
string GvName(const string tag)
{
   return "XS_" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN)) + "_" + IntegerToString(InpMagic) + "_" + tag;
}

string GvPos(const ulong ticket, const string tag)
{
   return "XSP_" + IntegerToString((long)ticket) + "_" + tag;
}

bool IsDemo()
{
   return AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO;
}

// True only on a DEMO account set to free run. Real accounts (and demo rehearsal) keep every protection.
bool DemoFree()
{
   return InpDemoMode == XAU_DEMO_FREE && IsDemo();
}

double LabTarget()
{
   return (g_mode == XAU_MODE_TREND) ? InpTrendWinTarget : InpWinTarget;
}

int MaxPositions()
{
   if(DemoFree()) return XMaxI(1, InpDemoMaxPositions);
   return (g_mode == XAU_MODE_TREND) ? XMaxI(1, InpTrendMaxPositions) : XMaxI(1, InpMaxPositions);
}

// exit profiles that hold for days: not closed by the Friday flatten (they were tested holding over weekends)
bool MultiDayProfile(const int p)
{
   return (p == XP_RIDER || p == XP_SWING);
}

// Risk still open in all EA positions, % of equity (distance from the open price to the current stop).
double OpenRiskPct()
{
   const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq <= 0.0) return 0.0;
   double money = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      const double sl = PositionGetDouble(POSITION_SL);
      const double op = PositionGetDouble(POSITION_PRICE_OPEN);
      const bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      const double dist = buy ? (op - sl) : (sl - op);
      if(sl <= 0.0 || dist <= 0.0) continue;                  // stop at or past entry: nothing left at risk
      string note = "";
      money += PositionGetDouble(POSITION_VOLUME) * XLossPerLot(_Symbol, buy, op, dist, note);
   }
   return 100.0 * money / eq;
}

// Is a position from this Lab combination already open?
bool CellOpen(const int cell)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      const string gv = GvPos(t, "C");
      if(GlobalVariableCheck(gv) && (int)GlobalVariableGet(gv) == cell) return true;
   }
   return false;
}

double RiskCapped()
{
   return XClamp(InpRiskPct, 0.05, XS_MAX_RISK_PCT);
}

string StratCode(const int s)
{
   switch(s)
   {
      case XS_CONFLUENCE: return "CONF";
      case XS_ORB:        return "ORB";
      case XS_DIP:        return "DIP";
      case XS_DOUBLE7:    return "D7";
      case XS_IBS:        return "IBS";
      case XS_SWEEP:      return "SWP";
      case XS_PULLBACK:   return "PB";
      case XS_SQUEEZE:    return "SQZ";
   }
   return "?";
}

//+------------------------------------------------------------------+
void FillConfig(XConfig &c, const ENUM_TIMEFRAMES tf)
{
   c.Defaults();
   c.base_sec = PeriodSeconds(tf);
   c.htf_sec = PeriodSeconds(g_htf);
   c.dst_mode = (int)InpServerDst;
   c.gmt_offset_sec = XWinterOffsetSec(InpManualGmt, InpGmtOffsetHrs, c.dst_mode);
   c.london_sessions = InpLondonSessions;
   c.use_session_filter = InpSessionFilter;
   c.trade_start = InpTradeStartGMT;
   c.trade_end = InpTradeEndGMT;
   c.fri_cutoff = InpFridayCutGMT;
   c.score_min = InpScoreMin;
   c.min_confluence = InpMinConfluence;
   c.adr_block = InpAdrBlock;
   c.orb_start_hour = InpOrbStartHour;
   c.orb_range_min = InpOrbRangeMin;
   c.orb_settle_min = InpOrbSettleMin;
   c.tp1_r = InpTP1_R;
   c.tp2_r = XMax(InpTP2_R, InpTP1_R + 0.1);
   c.partial_pct = XClamp(InpPartialPct / 100.0, 0.0, 1.0);
   c.trail_atr = InpTrailATR;
   c.sl_atr_min = InpSLMinATR;
   c.sl_atr_max = XMax(InpSLMaxATR, InpSLMinATR + 0.1);
   c.hold_minutes = InpHoldMinutes;
   // a fixed cost (not the spread of the moment) so the EA and the indicator test and choose alike
   c.cost_price = XMax(InpCostPrice, 0.01);
   c.min_stop_cost = XMax(InpMinStopCosts, 0.0);
   c.d1_mode = XResolveD1Mode((int)InpDailyTrend, tf);
   // the broker's real overnight swap, so multi-day exits are tested with what holding really costs
   c.swap_long = XSwapCostPerUnit(_Symbol, true);
   c.swap_short = XSwapCostPerUnit(_Symbol, false);
}

//+------------------------------------------------------------------+
// MT5 keeps an EA's global variables when the chart's timeframe or symbol changes (OnDeinit + OnInit without
// unloading). Everything that belongs to the old timeframe must be cleared, or the EA keeps trading the old
// timeframe's Strategy Lab result.
void ResetState()
{
   g_lab_ok = false; g_lab_day = 0; g_cell = -1; g_proven = false; g_act_s = -1; g_act_p = XP_CLASSIC;
   g_last_bar = 0; g_engine_ok = false; g_last_reason = XR_WARMUP; g_skip_note = "";
   g_small = false; g_small_note = ""; g_stats_dirty = true; g_npass = 0;
   g_last_sig.Reset();
   g_paper.Reset();
}

int OnInit()
{
   ResetState();
   g_hist = XResolveHistoryBars(InpHistoryBars, (ENUM_TIMEFRAMES)_Period);
   g_mode = XResolveMode((int)InpMode, (ENUM_TIMEFRAMES)_Period);
   Print("XAU Sniper: mode ", (g_mode == XAU_MODE_TREND) ? "TREND (all passing strategies, trend-riding exits)" : "STEADY (one strategy, 60%+ winners)");
   g_htf = (InpHTF == PERIOD_CURRENT) ? XAutoHTF((ENUM_TIMEFRAMES)_Period) : InpHTF;
   if(PeriodSeconds(g_htf) <= PeriodSeconds((ENUM_TIMEFRAMES)_Period)) g_htf = XAutoHTF((ENUM_TIMEFRAMES)_Period);

   string up = _Symbol;
   StringToUpper(up);
   if(StringFind(up, "XAU") < 0 && StringFind(up, "GOLD") < 0)
      Print("XAU Sniper: WARNING - ", _Symbol, " does not look like gold. The engine is tuned for XAUUSD.");
   if(InpRiskPct > XS_MAX_RISK_PCT) Print("XAU Sniper: risk per trade capped at ", DoubleToString(XS_MAX_RISK_PCT, 1), "% (requested ", DoubleToString(InpRiskPct, 2), "%).");
   if(InpRiskPct > 2.0) Print("XAU Sniper: WARNING - risk above 2% per trade makes a losing streak very costly.");

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
   if(DemoFree())
   {
      GlobalVariableDel(GvName("KILL"));
      GlobalVariableDel(GvName("PEAK"));
      Print("XAU Sniper: DEMO free run - guardrails are warnings only. This is not a preview of a real account.");
   }
   else if(IsDemo()) Print("XAU Sniper: DEMO rehearsal - the same rules as a real account (InpDemoMode).");
   g_kill = GlobalVariableCheck(GvName("KILL"));
   g_peak_eq = GlobalVariableCheck(GvName("PEAK")) ? GlobalVariableGet(GvName("PEAK")) : eq;
   if(g_peak_eq < eq) g_peak_eq = eq;
   g_day_start_eq = eq; g_week_start_eq = eq;
   g_day_id = -1; g_week_id = -1;
   g_last_sig.Reset();
   g_st_n = 0;
   FillConfig(g_eng.cfg, (ENUM_TIMEFRAMES)_Period);
   XMakeExit(XP_CLASSIC, g_eng.cfg, g_act_x);

   g_panel.prefix = "XS_PN_"; g_panel.fs = InpFontSize; g_panel.pos = InpPanelPos; g_panel.x = 12; g_panel.y = 30; g_panel.min_w = 330;

   EventSetTimer(2);
   g_stats_dirty = true;
   if(!MQLInfoInteger(MQL_TESTER))
   {
      // one EA instance per symbol + magic: a second chart would double every trade
      const string lock = GvName("LOCK_" + _Symbol);
      if(GlobalVariableCheck(lock) && (double)TimeLocal() - GlobalVariableGet(lock) < 15.0)
      {
         Print("XAU Sniper: another instance is already running on ", _Symbol, " with magic ", InpMagic, ". Refusing to start.");
         return INIT_FAILED;
      }
      GlobalVariableSet(lock, (double)TimeLocal());
   }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(!MQLInfoInteger(MQL_TESTER)) GlobalVariableDel(GvName("LOCK_" + _Symbol));
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
   GlobalVariableSet(GvPos(t, "X"), (double)g_st_prof[k]);
}

int StIndex(const ulong ticket, const bool create)
{
   for(int i = 0; i < g_st_n; i++) if(g_st_ticket[i] == ticket) return i;
   if(!create || g_st_n >= XS_MAXPOS) return -1;
   const int k = g_st_n++;
   g_st_ticket[k] = ticket;
   g_st_prof[k] = GlobalVariableCheck(GvPos(ticket, "X")) ? (int)GlobalVariableGet(GvPos(ticket, "X")) : g_act_p;
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
   GlobalVariableDel(GvPos(t, "E")); GlobalVariableDel(GvPos(t, "A")); GlobalVariableDel(GvPos(t, "X"));
   g_st_n--;
   if(k < g_st_n)
   {
      g_st_ticket[k] = g_st_ticket[g_st_n]; g_st_r0[k] = g_st_r0[g_st_n]; g_st_vol0[k] = g_st_vol0[g_st_n];
      g_st_stage[k] = g_st_stage[g_st_n]; g_st_ext[k] = g_st_ext[g_st_n]; g_st_atr[k] = g_st_atr[g_st_n];
      g_st_prof[k] = g_st_prof[g_st_n];
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
//| per-tick position management (each trade follows its exit style)  |
//+------------------------------------------------------------------+
void ManagePositions()
{
   if(PositionsTotal() == 0) { while(g_st_n > 0) StDrop(g_st_n - 1); return; }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;
   const double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   const double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   const double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   const double stops = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   const double spread_px = tick.ask - tick.bid;
   const int period_sec = PeriodSeconds((ENUM_TIMEFRAMES)_Period);
   const datetime now = TimeCurrent();
   const int gmt_off = XOffsetAt(g_eng.cfg, now);

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
      XExit x;
      XMakeExit(g_st_prof[k], g_eng.cfg, x);

      const bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      const int dir = buy ? 1 : -1;
      const double open = PositionGetDouble(POSITION_PRICE_OPEN);
      const double cur_sl = PositionGetDouble(POSITION_SL);
      const double cur_tp = PositionGetDouble(POSITION_TP);
      const double vol = PositionGetDouble(POSITION_VOLUME);
      const double px = buy ? tick.bid : tick.ask;
      const double fav = dir * (px - open);
      const double r0 = g_st_r0[k];
      if(fav > g_st_ext[k]) g_st_ext[k] = fav;

      // --- time stop and Friday flatten
      const int maxh = (x.max_hold > 0) ? x.max_hold : g_eng.MaxHold();
      const datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      // count bars (as the tests do), not calendar time, so weekends do not shorten multi-day holds
      const int held = iBarShift(_Symbol, (ENUM_TIMEFRAMES)_Period, opened, false);
      if((held >= 0 && held >= maxh) || (held < 0 && now - opened >= (datetime)(maxh * period_sec)))
      {
         Print("XAU Sniper: time stop on ", (long)ticket);
         ClosePart(ticket, 0.0);
         continue;
      }
      if(InpFridayFlatten && !MultiDayProfile(g_st_prof[k]) && XWeekdayGmt(now, gmt_off) == 5 && XHourGmt(now, gmt_off) + ((InpLondonSessions && XEuDst((long)now - gmt_off)) ? 1.0 : 0.0) >= InpFlattenGMT)
      {
         Print("XAU Sniper: Friday flatten on ", (long)ticket);
         ClosePart(ticket, 0.0);
         continue;
      }
      if(r0 <= 0.0) continue;

      // --- first target: bank the planned share, stop to break-even (or the profile's lock)
      if(g_st_stage[k] == 0 && x.tp1_r > 0.0 && x.part > 0.0 && fav >= x.tp1_r * r0)
      {
         const double vc = MathFloor(g_st_vol0[k] * x.part / vstep + 1e-9) * vstep;
         const bool close_all = (x.part >= 0.999) || (vc > 0.0 && (vol - vc) < vmin - 1e-9);
         if(close_all) { ClosePart(ticket, 0.0); continue; }
         if(vc >= vmin - 1e-9)
         {
            if(!ClosePart(ticket, vc)) continue;
         }
         const double be = NormalizeDouble(open + dir * (x.be_lock_r * r0 + spread_px), _Digits);
         const bool sl_ok = buy ? (be > cur_sl && (tick.bid - be) > stops)
                                : ((cur_sl == 0.0 || be < cur_sl) && (be - tick.ask) > stops);
         if(sl_ok) g_trade.PositionModify(ticket, be, cur_tp);
         g_st_stage[k] = 1;
         StSave(k);
         continue;
      }

      // --- after the first target: ATR trail on the best excursion
      if(g_st_stage[k] == 1 && x.trail_atr > 0.0 && g_st_atr[k] > 0.0)
      {
         double tsl = open + dir * (g_st_ext[k] - x.trail_atr * g_st_atr[k]);
         tsl = NormalizeDouble(tsl, _Digits);
         const double step = 2.0 * pt;
         const bool better = buy ? (tsl > cur_sl + step) : (cur_sl == 0.0 || tsl < cur_sl - step);
         const bool room = buy ? ((tick.bid - tsl) > stops) : ((tsl - tick.ask) > stops);
         if(better && room)
         {
            if(g_trade.PositionModify(ticket, tsl, cur_tp)) StSave(k);
         }
      }
   }
   for(int k = g_st_n - 1; k >= 0; k--) if(!seen[k]) StDrop(k);
}

// Mean-reversion exit, checked when a bar closes: price closed back across the 5-bar mean.
void CheckMeanExits()
{
   if(!g_engine_ok) return;
   const int i = g_eng.n - 2;
   for(int p = PositionsTotal() - 1; p >= 0; p--)
   {
      const ulong ticket = PositionGetTicket(p);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      const int k = StIndex(ticket, true);
      if(k < 0) continue;
      XExit x;
      XMakeExit(g_st_prof[k], g_eng.cfg, x);
      if(x.mr_exit != 1) continue;
      const bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      if((buy && g_eng.m_c[i] > g_eng.m_sma5[i]) || (!buy && g_eng.m_c[i] < g_eng.m_sma5[i]))
      {
         Print("XAU Sniper: mean-reversion exit on ", (long)ticket, " (close ", DoubleToString(g_eng.m_c[i], _Digits),
               " past the 5-bar mean ", DoubleToString(g_eng.m_sma5[i], _Digits), ")");
         ClosePart(ticket, 0.0);
      }
   }
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
   if(DemoFree()) g_kill = false;
   if(!g_kill && !DemoFree() && InpMaxDDPct > 0.0 && g_peak_eq > 0.0 && 100.0 * (g_peak_eq - eq) / g_peak_eq >= InpMaxDDPct)
   {
      g_kill = true;
      GlobalVariableSet(GvName("KILL"), 1.0);
      Print("XAU Sniper: KILL-SWITCH - drawdown ", DoubleToString(100.0 * (g_peak_eq - eq) / g_peak_eq, 1), "% from peak. Trading stopped.");
      if(InpKillFlatten) CloseAllOurs("kill-switch");
   }
   const double day_loss_pct = InpDailyLossRealized ? (-100.0 * g_day_pl / MathMax(g_day_start_eq, 1.0))
                                                     : (100.0 * (g_day_start_eq - eq) / MathMax(g_day_start_eq, 1.0));
   if(!g_day_block && !DemoFree() && InpDailyLossPct > 0.0 && g_day_start_eq > 0.0 && day_loss_pct >= InpDailyLossPct)
   {
      g_day_block = true;
      Print("XAU Sniper: daily loss limit reached - no new trades today.");
   }
   if(!g_week_block && !DemoFree() && InpWeeklyLossPct > 0.0 && g_week_start_eq > 0.0 && 100.0 * (g_week_start_eq - eq) / g_week_start_eq >= InpWeeklyLossPct)
   {
      g_week_block = true;
      Print("XAU Sniper: weekly loss limit reached - no new trades this week.");
   }
   if(g_kill)            g_block_note = "KILL-SWITCH: drawdown limit hit (set InpResetKill to clear)";
   else if(g_week_block) g_block_note = "paused: weekly loss limit";
   else if(g_day_block)  g_block_note = "paused: daily loss limit";
}

// A loss streak pauses trading for the rest of that day, or until the paper-traded signals recover.
// (The earlier version counted the streak over 45 days of history, so once paused the EA could never
// win a trade to end it.)
bool StreakPauseActive()
{
   if(InpMaxConsecLosses <= 0 || g_consec_losses < InpMaxConsecLosses) return false;
   if(g_last_loss_bar == 0 || (long)g_last_loss_bar / 86400 != (long)TimeTradeServer() / 86400) return false;   // a new day clears it
   if(InpPaperResume && g_paper.Recovered()) return false;
   return true;
}

// Checks that hold in every mode, demo free run included: they protect the account from a margin call
// and from paying more spread than the Strategy Lab assumed.
string TechnicalBlock()
{
   if(AccountInfoDouble(ACCOUNT_MARGIN_FREE) <= 0.0) return "no free margin: open trades are using all of it";
   const double ml = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   if(ml > 0.0 && ml < 300.0) return "margin level " + DoubleToString(ml, 0) + "% is too low for another trade";
   MqlTick tk;
   if(SymbolInfoTick(_Symbol, tk) && InpCostPrice > 0.0 && tk.ask - tk.bid > 1.5 * InpCostPrice)
      return "spread " + DoubleToString(tk.ask - tk.bid, 2) + " is above 1.5x the tested cost (" + DoubleToString(InpCostPrice, 2) + ")";
   return "";
}

// returns "" when a new entry is allowed
string EntryBlocked(const XSignal &s)
{
   const string tb = TechnicalBlock();
   if(StringLen(tb) > 0) return tb;
   if(DemoFree())
   {
      // demo: only hard technical limits apply; every risk rule is a warning
      if(CountPositions() >= MaxPositions()) return "demo position limit (" + IntegerToString(MaxPositions()) + ") reached";
      if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return "auto-trading disabled";
      if(SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL) return "symbol not fully tradable now";
      const double dpt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      const double dsp = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
      if(InpMaxSpreadPts > 0 && dsp > InpMaxSpreadPts) return "spread " + DoubleToString(dsp * dpt, 2) + " too wide";
      if(InpUseNews && g_news_blocked) return "news: " + g_news_note;
      return "";
   }
   if(g_kill) return "kill-switch active";
   if(g_week_block) return "weekly loss limit";
   if(g_day_block) return "daily loss limit";
   if(StreakPauseActive())
      return "paused after " + IntegerToString(g_consec_losses) + " losses in a row" +
             (InpPaperResume ? " (paper trades so far: " + IntegerToString(g_paper.rn) + ", resumes when they recover)" : " (until tomorrow)");
   if(InpMaxTradesPerDay > 0 && g_trades_today >= InpMaxTradesPerDay) return "max trades today";
   if(CountPositions() >= MaxPositions()) return (MaxPositions() > 1) ? "position limit reached" : "position already open";
   if(g_mode == XAU_MODE_TREND && InpMaxOpenRiskPct > 0.0 && OpenRiskPct() + RiskCapped() > InpMaxOpenRiskPct + 1e-9)
      return "open risk would exceed " + DoubleToString(InpMaxOpenRiskPct, 1) + "%";
   if(InpOneTradePerSymbol && AnyPositionOnSymbol()) return "another position already open on this symbol";
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

// Some brokers refuse SL/TP on the market request itself. Open, attach the stops, and if they cannot be
// attached close the position at once: this EA never leaves a naked position open.
bool SendOrderThenProtect(const bool buy, const double lots, const double sl, const double tp, const string cmt)
{
   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk)) return false;
   const double price = buy ? tk.ask : tk.bid;
   const bool ok = buy ? g_trade.Buy(lots, _Symbol, price, 0.0, 0.0, cmt) : g_trade.Sell(lots, _Symbol, price, 0.0, 0.0, cmt);
   if(!ok || !RetOk(g_trade.ResultRetcode())) return false;
   Sleep(200);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetDouble(POSITION_SL) > 0.0) continue;
      if(g_trade.PositionModify(t, sl, tp) && RetOk(g_trade.ResultRetcode())) return true;
      Print("XAU Sniper: could not attach stops, closing position ", (long)t);
      ClosePart(t, 0.0);
      return false;
   }
   return false;
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
      if(rc == TRADE_RETCODE_INVALID_STOPS) return SendOrderThenProtect(buy, lots, sl, tp, cmt);
      if(!RetRetry(rc)) break;
      Sleep(150);
   }
   Print("XAU Sniper: order failed, retcode ", (int)g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
   return false;
}

//+------------------------------------------------------------------+
//| engine refresh, daily Strategy Lab and entry                       |
//+------------------------------------------------------------------+
bool RefreshEngine()
{
   const int want = XMaxI(InpSignalBars, 900);
   const int got = XLoadRates(_Symbol, (ENUM_TIMEFRAMES)_Period, want, g_rates);
   if(got < 700) { g_engine_ok = false; return false; }
   FillConfig(g_eng.cfg, (ENUM_TIMEFRAMES)_Period);
   const int need_h = (int)((double)got * g_eng.cfg.base_sec / g_eng.cfg.htf_sec) + 320;
   const int gh = XLoadRates(_Symbol, g_htf, need_h, g_hrates);
   if(gh < 300) { g_engine_ok = false; return false; }   // never trade without the higher-timeframe trend
   g_eng.SetBase(g_rates, got);
   g_eng.SetHTF(g_hrates, gh);
   int gd = 0;
   if(g_eng.cfg.d1_mode > 0)
   {
      gd = XLoadRates(_Symbol, PERIOD_D1, XDailyBarsNeeded(got, (ENUM_TIMEFRAMES)_Period), g_drates);
      if(gd < 210) { g_engine_ok = false; return false; }      // never trade the daily filter blind
   }
   g_eng.SetDaily(g_drates, gd);
   if(StringLen(g_inter_sym) > 0)
   {
      const int gi = XLoadRates(g_inter_sym, (ENUM_TIMEFRAMES)_Period, got + 50, g_irates);
      if(gi > 100) g_eng.SetInter(g_irates, gi, g_inter_invert);
   }
   if(!g_eng.Compute()) { g_engine_ok = false; return false; }
   g_engine_ok = true;
   return true;
}

// Once per server day on the same fixed window as the indicator, so both choose the same strategy.
void RunLabIfNeeded()
{
   const datetime ds = XServerDayStart(TimeCurrent());
   if(g_lab_ok && ds == g_lab_day) return;
   FillConfig(g_lab.cfg, (ENUM_TIMEFRAMES)_Period);
   const bool ok = XRunDailyLab(g_lab, _Symbol, (ENUM_TIMEFRAMES)_Period, g_htf, g_hist, g_inter_sym, g_inter_invert,
                                LabTarget(), InpLabMinTrades, InpLabFolds, ds);
   if(!ok) return;                       // try again on the next bar
   g_lab_ok = true;
   g_lab_day = ds;
   // TREND mode: every passing combination may trade, best first
   g_npass = 0;
   for(int k = 0; k < XLAB_CELLS; k++)
   {
      const int c = g_lab.LabRanked(k);
      if(c < 0) break;
      if(g_lab.lab[c].qualified) g_pass[g_npass++] = c;
   }
   int us = (int)InpStrategy;
   if(InpOrbSolo) us = XS_ORB;
   g_cell = XResolveCell(g_lab, us, (int)InpExit, InpLabMinTrades, g_proven);
   if(g_cell < 0) { g_act_s = -1; return; }
   g_act_s = g_cell / XP_COUNT;
   g_act_p = g_cell % XP_COUNT;
   XMakeExit(g_act_p, g_eng.cfg, g_act_x);
   if(g_mode == XAU_MODE_TREND) Print("XAU Sniper: TREND mode - ", g_npass, " combinations passed the Lab (target ", DoubleToString(LabTarget(), 0), "% winners)");
   Print("XAU Sniper: Strategy Lab -> ", XStratName(g_act_s), " + ", XExitName(g_act_p), (g_proven ? " [PROVEN]" : " [UNPROVEN]"),
         ": ", DoubleToString(g_lab.lab[g_cell].all.WinRate(), 1), "% won, avg ", DoubleToString(g_lab.lab[g_cell].all.Expectancy(), 3),
         "R over ", g_lab.lab[g_cell].all.n, " trades; auto-pick walk-forward ", DoubleToString(g_lab.lab_auto.WinRate(), 1), "% / ",
         DoubleToString(g_lab.lab_auto.Expectancy(), 3), "R (", g_lab.lab_auto.n, " trades)");
}

bool TryEnterCell(const int st, const int pr, const bool proven);

void TryEnter()
{
   g_skip_note = "";
   if(g_act_s < 0) { g_last_reason = XR_WARMUP; return; }
   if(g_mode != XAU_MODE_TREND || g_npass == 0)
   {
      TryEnterCell(g_act_s, g_act_p, g_proven);
      return;
   }
   // TREND mode: every passing combination may trade, each with its own position, best first
   int last_reason = XR_NOSETUP;
   string note = "";
   for(int k = 0; k < g_npass; k++)
   {
      const int c = g_pass[k];
      if(CellOpen(c)) continue;
      g_skip_note = "";
      TryEnterCell(c / XP_COUNT, c % XP_COUNT, true);
      if(k == 0 || g_last_reason == XR_OK) last_reason = g_last_reason;
      if(StringLen(g_skip_note) > 0) note = g_skip_note;
   }
   g_last_reason = last_reason;
   g_skip_note = note;
}

// One Lab combination: signal on the last closed bar, checks, size, order. Returns true when an order was sent.
bool TryEnterCell(const int st, const int pr, const bool proven)
{
   const int i = g_eng.n - 2;                       // last CLOSED bar
   XExit xx;
   XMakeExit(pr, g_eng.cfg, xx);
   XSignal s;
   const bool has = g_eng.StrategySignal(st, i, xx, s);
   g_last_reason = s.reason;
   if(!has) return false;
   g_last_sig = s;

   if(!proven && !(DemoFree() && InpDemoUnproven))
   {
      g_skip_note = "signal skipped: no strategy has passed the Strategy Lab on this chart";
      Print("XAU Sniper: ", g_skip_note);
      return false;
   }
   // while a loss-streak pause is active, follow the signals on paper so we know when to resume
   if(!DemoFree() && InpPaperResume && StreakPauseActive()) g_paper.Add(g_eng.m_t[i], s.dir, s.sl);

   const string blocked = EntryBlocked(s);
   if(StringLen(blocked) > 0) { g_skip_note = "signal skipped: " + blocked; Print("XAU Sniper: ", g_skip_note); return false; }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk)) return false;
   const bool buy = (s.dir > 0);
   const double entry = buy ? tk.ask : tk.bid;
   const double dist = buy ? (entry - s.sl) : (s.sl - entry);
   if(dist < 0.4 * s.atr || dist > xx.sl_max_atr * s.atr * 1.3)
   {
      g_skip_note = "signal skipped: price moved, stop distance no longer valid";
      Print("XAU Sniper: ", g_skip_note);
      return false;
   }
   const double stops = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(dist <= stops) { g_skip_note = "signal skipped: stop inside broker minimum distance"; return false; }

   double risk = RiskCapped();
   if(g_consec_losses >= 2) risk *= XClamp(InpStreakScale, 0.1, 1.0);
   if(InpD1Scale)
   {
      double d1adx;
      const int d1 = XTrendState(_Symbol, PERIOD_D1, d1adx);
      if(d1 != 0 && d1 != s.dir) risk *= 0.5;
   }
   risk = XMin(risk, XS_MAX_RISK_PCT);

   XLotPlan lp;
   const bool demo = DemoFree();
   // free run may exceed the chosen risk with the smallest lot, but never beyond InpDemoMaxRiskPct of equity
   const double overrun = demo ? XMax(InpMaxRiskOverrun, XClamp(InpDemoMaxRiskPct, 0.5, 50.0) / XMax(risk, 0.01)) : InpMaxRiskOverrun;
   XPlanLots(_Symbol, AccountInfoDouble(ACCOUNT_EQUITY), risk, dist, buy, entry, overrun,
             InpMaxLots, AccountInfoDouble(ACCOUNT_MARGIN_FREE), XClamp(InpMarginUsePct, 5.0, 95.0) / 100.0, lp);
   if(!lp.ok)
   {
      g_skip_note = "signal skipped: " + lp.note;
      if(StringFind(lp.note, "account too small") >= 0)
      {
         // tell the user what balance this trade needs at the chosen risk
         string snote = "";
         const double per_lot = XLossPerLot(_Symbol, buy, entry, dist, snote);
         const double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
         if(per_lot > 0.0 && vmin > 0.0)
            g_skip_note += "; this trade needs about " + DoubleToString(vmin * per_lot * 100.0 / XMax(risk, 0.01), 0) + " " +
                           AccountInfoString(ACCOUNT_CURRENCY) + " at " + DoubleToString(risk, 1) + "% risk";
         g_small = true;
         g_small_note = g_skip_note;
      }
      Print("XAU Sniper: ", g_skip_note);
      return false;
   }
   if(StringLen(lp.src_note) > 0) Print("XAU Sniper: sizing note - ", lp.src_note);
   // targets in price from the ACTUAL entry, using the profile's multiples
   const double sl = NormalizeDouble(s.sl, _Digits);
   double tp = 0.0;
   if(xx.tp2_r > 0.0)                                  tp = entry + s.dir * xx.tp2_r * dist;
   else if(xx.tp1_r > 0.0 && xx.part >= 0.999)   tp = entry + s.dir * xx.tp1_r * dist;
   tp = (tp > 0.0) ? NormalizeDouble(tp, _Digits) : 0.0;
   const string cmt = InpComment + " " + StratCode(st) + "/" + IntegerToString(pr);
   g_small = false;
   if(SendOrder(buy, lp.lots, sl, tp, cmt))
   {
      const ulong ord = g_trade.ResultOrder();
      if(ord > 0) { GlobalVariableSet(GvPos(ord, "X"), (double)pr); GlobalVariableSet(GvPos(ord, "C"), (double)(st * XP_COUNT + pr)); }
      if(demo && lp.risk_pct > risk * 1.5)
         Print("XAU Sniper: DEMO note - minimum lot risks ", DoubleToString(lp.risk_pct, 1), "% (target ", DoubleToString(risk, 2), "%). A live account would have refused this trade.");
      Print("XAU Sniper: ", (buy ? "BUY " : "SELL "), DoubleToString(lp.lots, 2), " ", _Symbol, " [", XStratName(st), " + ", XExitName(pr), "]",
            " entry ", DoubleToString(entry, _Digits), " SL ", DoubleToString(sl, _Digits), " TP ", DoubleToString(tp, _Digits),
            " risk ", DoubleToString(lp.risk_pct, 2), "% (", DoubleToString(lp.risk_money, 2), ")");
      g_stats_dirty = true;
      g_paper.Reset();
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
// Optional (InpProtectManual): give every position on this symbol that has no stop loss one, manual trades
// included. The stop sits where the position would lose InpProtectPct of equity; a position that is already
// losing more than that gets its stop InpProtectPct of equity beyond the current price, so the damage is
// capped from here on instead of being closed at once.
void ProtectManual()
{
   if(!InpProtectManual || InpProtectPct <= 0.0) return;
   static datetime s_last = 0;
   if(TimeCurrent() - s_last < 30) return;
   s_last = TimeCurrent();
   const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq <= 0.0) return;
   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk)) return;
   const double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   const double stops = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetDouble(POSITION_SL) > 0.0) continue;
      const bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      const double vol = PositionGetDouble(POSITION_VOLUME);
      const double open = PositionGetDouble(POSITION_PRICE_OPEN);
      const double tp = PositionGetDouble(POSITION_TP);
      string note = "";
      const double per_unit = XLossPerLot(_Symbol, buy, open, 1.0, note);   // money per lot for a 1.0 price move
      if(per_unit <= 0.0 || vol <= 0.0) continue;
      const double dist = eq * InpProtectPct / 100.0 / (vol * per_unit);
      const double px = buy ? tk.bid : tk.ask;
      double sl = buy ? open - dist : open + dist;
      const bool beyond = buy ? (sl >= px - stops) : (sl <= px + stops);
      if(beyond) sl = buy ? px - XMax(dist, stops + pt) : px + XMax(dist, stops + pt);
      sl = NormalizeDouble(sl, _Digits);
      if(g_trade.PositionModify(t, sl, tp) && RetOk(g_trade.ResultRetcode()))
         Print("XAU Sniper: added a stop at ", DoubleToString(sl, _Digits), " to position ", (long)t, " (it had none; InpProtectManual)");
      else
         Print("XAU Sniper: could not add a stop to position ", (long)t, ": ", g_trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
void RefreshNews()
{
   if(!InpUseNews) { g_news_blocked = false; g_news_note = ""; return; }
   g_news.Refresh(TimeCurrent());
   g_news.gmt_offset_sec = XOffsetAt(g_eng.cfg, TimeCurrent());
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
   RunLabIfNeeded();
   CheckMeanExits();
   if(!DemoFree() && InpPaperResume && g_paper.pn > 0) g_paper.Update(g_eng, g_act_x);
   TryEnter();
   DrawPanel();
}

void OnTimer()
{
   if(!MQLInfoInteger(MQL_TESTER)) GlobalVariableSet(GvName("LOCK_" + _Symbol), (double)TimeLocal());
   ProtectManual();
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
//| panel (bottom left by default, so it never covers the indicator)  |
//+------------------------------------------------------------------+
void DrawPanel()
{
   if(!InpShowPanel || (MQLInfoInteger(MQL_TESTER) && !MQLInfoInteger(MQL_VISUAL_MODE))) { g_panel.Clear(); return; }
   const color cText = XRGB(214, 222, 235), cDim = XRGB(140, 150, 166), cGreen = XRGB(0, 222, 132);
   const color cRed = XRGB(255, 92, 92), cGold = XRGB(255, 200, 64), cCyan = XRGB(64, 200, 255);
   const double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   const int np = CountPositions();

   string mode = (g_mode == XAU_MODE_TREND) ? "  TREND" : "  STEADY";
   mode += "   [LIVE rules]";
   if(DemoFree()) mode = ((g_mode == XAU_MODE_TREND) ? "  TREND" : "  STEADY") + string("   [DEMO free run]");
   else if(IsDemo()) mode = ((g_mode == XAU_MODE_TREND) ? "  TREND" : "  STEADY") + string("   [DEMO rehearsal]");
   string status = "LOOKING FOR A SETUP";
   color sc = cCyan;
   string sub = StringLen(g_skip_note) > 0 ? g_skip_note : XReasonText(g_last_reason);
   if(g_kill)                           { status = "STOPPED - loss limit hit"; sc = cRed; sub = "set InpResetKill = true for one start to resume"; }
   else if(g_week_block || g_day_block) { status = "PAUSED"; sc = cGold; sub = g_block_note; }
   else if(np > 0)                      { status = "IN " + IntegerToString(np) + " TRADE"; if(np > 1) status += "S"; sc = cGreen; sub = "managing the exit: " + XExitName(g_act_p); }
   else if(g_news_blocked)              { status = "PAUSED - NEWS"; sc = cGold; sub = g_news_note; }
   else if(!g_lab_ok)                   { status = "LEARNING"; sub = "Strategy Lab is testing this chart's history"; }
   else if(g_act_s < 0)                 { status = "NO STRATEGY YET"; sc = cGold; sub = "not enough trades in the history to judge"; }
   else if(!g_proven && !(DemoFree() && InpDemoUnproven) && !(g_mode == XAU_MODE_TREND && g_npass > 0)) { status = "STANDING ASIDE"; sc = cGold; sub = "nothing passed the Strategy Lab here"; }
   else if(g_small)                     { status = "ACCOUNT TOO SMALL HERE"; sc = cGold; sub = g_small_note; }

   g_panel.Begin();
   g_panel.Line("XAU SNIPER  " + XTfName((ENUM_TIMEFRAMES)_Period) + mode, cGold);
   g_panel.Line(status, sc, 3);
   g_panel.Line(sub, cDim);
   if(g_mode == XAU_MODE_TREND && g_npass > 0)
   {
      g_panel.Line("TREND mode: " + IntegerToString(g_npass) + " strateg" + (g_npass > 1 ? "ies" : "y") + " passed today, each may trade (max "
                   + IntegerToString(MaxPositions()) + " at once)", cGreen);
      for(int k = 0; k < g_npass && k < 3; k++)
      {
         const int c = g_pass[k];
         const XStats st = g_lab.lab[c].all;
         g_panel.Line("  " + XStratName(c / XP_COUNT) + " / " + XExitShort(c % XP_COUNT) + ": " + DoubleToString(st.WinRate(), 0) + "% won, "
                      + StringFormat("%+.2f", st.Expectancy()) + "R, " + IntegerToString(st.n) + " trades", cDim);
      }
   }
   else if(g_act_s >= 0)
   {
      string badge = "  [PROVEN]";
      if(!g_proven) badge = "  [UNPROVEN]";
      string mtag = "";
      if(g_mode == XAU_MODE_TREND) mtag = "TREND mode, nothing passed: ";
      g_panel.Line(mtag + "Trading: " + XStratName(g_act_s) + " + " + XExitName(g_act_p) + badge, g_proven ? cGreen : cGold);
      const XStats st = g_lab.lab[g_cell].all;
      g_panel.Line("Lab here: " + DoubleToString(st.WinRate(), 0) + "% won, avg " + StringFormat("%+.2f", st.Expectancy()) + "R, "
                   + IntegerToString(st.n) + " trades", cDim);
   }
   // open positions in plain words
   for(int pi = PositionsTotal() - 1; pi >= 0; pi--)
   {
      const ulong t = PositionGetTicket(pi);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      const bool b = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      const int kk = StIndex(t, false);
      string plan = "";
      if(kk >= 0) plan = "  [" + XExitShort(g_st_prof[kk]) + "]";
      g_panel.Line((b ? "  BUY " : "  SELL ") + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + " @" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), _Digits)
                   + "  stop " + DoubleToString(PositionGetDouble(POSITION_SL), _Digits) + "  P/L " + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2) + plan,
                   PositionGetDouble(POSITION_PROFIT) >= 0.0 ? cGreen : cRed);
   }
   const double dpl = (g_day_start_eq > 0.0) ? 100.0 * (eq - g_day_start_eq) / g_day_start_eq : 0.0;
   g_panel.Line("Equity " + DoubleToString(eq, 2) + "   today " + StringFormat("%+.2f%%", dpl) + "   trades today " + IntegerToString(g_trades_today), cText);
   if(g_tot_n > 0)
   {
      const double pf = (g_tot_gross_loss > 1e-9) ? g_tot_gross_win / g_tot_gross_loss : 99.0;
      g_panel.Line("Live results (45 days): " + IntegerToString(g_tot_n) + " trades, " + DoubleToString(100.0 * g_tot_win / g_tot_n, 0) + "% won, P/L "
                   + DoubleToString(g_tot_profit, 2) + ", profit factor " + DoubleToString(pf, 2), g_tot_profit >= 0.0 ? cGreen : cRed);
   }
   else g_panel.Line("Live results: no closed trades yet", cDim);
   const string warn = XAccountWarning(_Symbol);
   if(StringLen(warn) > 0) g_panel.Line("RISK: " + warn, cRed);
   if(StringFind(warn, "NO stop") >= 0 && !InpProtectManual) g_panel.Line("Tip: InpProtectManual = true lets the EA put a stop on them", cDim);
   if(InpUseNews && StringFind(g_news_note, " in ") >= 0) g_panel.Line("News: " + g_news_note, g_news_blocked ? cRed : cDim);
   g_panel.End();
}
