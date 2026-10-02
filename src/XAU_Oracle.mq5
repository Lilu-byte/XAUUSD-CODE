//+------------------------------------------------------------------+
//|                                                  XAU_Oracle.mq5  |
//|  XAUUSD trading assistant.                                       |
//|                                                                  |
//|  Every day the STRATEGY LAB puts 8 strategies x 4 exit styles on  |
//|  trial on THIS chart's own history (walk-forward) and picks the   |
//|  one that won at least the target share of trades (default 60%)  |
//|  with a positive average result. The chart then shows only that  |
//|  strategy: when to enter, where the stop and targets are, how    |
//|  long to stay, how much to trade, and the next candles.          |
//|                                                                  |
//|  Signals use closed bars only and never repaint.                 |
//|  Past results do not guarantee future results.                   |
//+------------------------------------------------------------------+
#property copyright   "XAU Oracle"
#property version     "2.00"
#property description "XAUUSD assistant: a Strategy Lab tests 32 strategy/exit combinations on this chart"
#property description "and shows only the one that proved itself (>= 60% winning trades with profit, walk-forward)."
#property description "Entry, stop, targets, lot size, hold time and projected candles. No result is guaranteed."
#property indicator_chart_window
#property indicator_buffers 10
#property indicator_plots   8

#property indicator_label1  "EMA 21"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrDodgerBlue
#property indicator_style1  STYLE_SOLID
#property indicator_width1  1

#property indicator_label2  "EMA 50"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrGold
#property indicator_style2  STYLE_SOLID
#property indicator_width2  2

#property indicator_label3  "EMA 200"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrTomato
#property indicator_style3  STYLE_SOLID
#property indicator_width3  2

#property indicator_label4  "5-bar mean"
#property indicator_type4   DRAW_LINE
#property indicator_color4  clrMediumOrchid
#property indicator_style4  STYLE_DOT
#property indicator_width4  1

#property indicator_label5  "Buy"
#property indicator_type5   DRAW_COLOR_ARROW
#property indicator_color5  clrLimeGreen,clrDarkGray
#property indicator_width5  3

#property indicator_label6  "Sell"
#property indicator_type6   DRAW_COLOR_ARROW
#property indicator_color6  clrOrangeRed,clrDarkGray
#property indicator_width6  3

#property indicator_label7  "Trade ended in profit"
#property indicator_type7   DRAW_ARROW
#property indicator_color7  clrLimeGreen
#property indicator_width7  1

#property indicator_label8  "Trade ended in loss"
#property indicator_type8   DRAW_ARROW
#property indicator_color8  clrTomato
#property indicator_width8  1

#include <XAU/XAU_Platform.mqh>

//--- inputs -----------------------------------------------------------
input group "=== What to trade ==="
input ENUM_XAU_MODE   InpMode           = XAU_MODE_AUTO; // Mode (AUTO: TREND on H1/H4, STEADY elsewhere; keep equal to the EA)
input double          InpTrendWinTarget = 50.0;          // TREND mode: Lab target (% winners; keep equal to the EA)
input ENUM_XAU_STRAT  InpStrategy       = XAU_ST_AUTO;   // Strategy (AUTO = the one that passed the Strategy Lab here)
input ENUM_XAU_EXIT   InpExit           = XAU_EX_AUTO;   // Exit style (AUTO = chosen together with the strategy)
input double          InpWinTarget      = 60.0;          // Strategy Lab: minimum % of winning trades
input int             InpLabMinTrades   = 50;            // Strategy Lab: minimum trades before a strategy can qualify
input int             InpLabFolds       = 5;             // Strategy Lab: walk-forward folds
input int             InpHistoryBars    = 0;             // Bars tested (0 = auto: 25,000 on H1, else 10,000; keep equal to the EA)
input ENUM_XAU_D1     InpDailyTrend     = XAU_D1_AUTO;   // Daily trend filter (AUTO: H1 and above buy only in a daily uptrend)

input group "=== Money ==="
input double          InpRiskPct        = 1.0;           // Risk per trade, % of balance (for the lot size shown)
input double          InpBalanceOverride = 0.0;          // 0 = use account equity

input group "=== Screen ==="
input bool            InpShowPanel      = true;          // Main panel
input ENUM_XAU_PANEL_POS InpPanelPos    = XAU_PANEL_TOP_LEFT;     // Main panel position
input bool            InpShowLab        = true;          // Strategy Lab scoreboard
input ENUM_XAU_PANEL_POS InpLabPos      = XAU_PANEL_BOTTOM_RIGHT; // Scoreboard position
input int             InpFontSize       = 10;            // Font size
input bool            InpShowTradeBox   = true;          // Green (profit) / red (risk) box on a setup
input bool            InpShowForecast   = true;          // Projected next candles
input int             InpForecastBars   = 6;             // Candles to project (max 7)
input bool            InpShowCone       = true;          // Expected range cone
input bool            InpShowTfForecast = true;          // Next-candle direction for M15 / H1 / H4
input bool            InpShowLevels     = true;          // Yesterday's high/low and the Asian range
input bool            InpShowOrb        = true;          // Opening range box
input bool            InpShowHistory    = true;          // Past entries and how they ended
input bool            InpChartShift     = true;          // Leave room on the right for projections

input group "=== Alerts ==="
input bool            InpAlertPopup     = true;
input bool            InpAlertPush      = false;
input bool            InpAlertEmail     = false;
input bool            InpAlertSound     = true;

input group "=== Broker clock and sessions ==="
input bool            InpManualGmt      = false;         // Set broker GMT offset by hand
input double          InpGmtOffsetHrs   = 2.0;           // Broker server time minus GMT in WINTER (hours)
input ENUM_XAU_DST    InpServerDst      = XAU_DST_US;    // How the broker's server clock handles daylight saving
input bool            InpLondonSessions = true;          // Session hours are London local time (follow UK DST)
input bool            InpSessionFilter  = true;          // Only signal inside the trading window
input double          InpTradeStartGMT  = 7.0;           // Window start (London open)
input double          InpTradeEndGMT    = 20.0;          // Window end
input double          InpFridayCutGMT   = 19.0;          // No new signals after this on Fridays
input double          InpOrbStartHour   = 1.0;           // Daily open on the SERVER clock (New-York-close brokers: 1)

input group "=== Engine details (advanced) ==="
input ENUM_TIMEFRAMES InpHTF            = PERIOD_CURRENT; // Higher timeframe for the trend (CURRENT = automatic)
input double          InpScoreMin       = 1.7;           // Confluence strategy: score needed
input int             InpMinConfluence  = 2;             // Confluence strategy: agreeing modules needed
input double          InpAdrBlock       = 0.90;          // No trend-continuation setups after this share of the daily range
input int             InpOrbRangeMin    = 60;            // Opening range: minutes that form it
input int             InpOrbSettleMin   = 180;           // Opening range: quiet minutes before it is final
input bool            InpOrbSolo        = false;         // Force the opening-range strategy (GOLD_ORB mode)
input double          InpTP1_R          = 1.0;           // Classic exit: first target (R)
input double          InpTP2_R          = 2.5;           // Classic exit: runner target (R)
input double          InpPartialPct     = 50.0;          // Classic exit: % closed at the first target
input double          InpTrailATR       = 2.0;           // Classic exit: trail distance (ATR)
input double          InpSLMinATR       = 0.9;           // Minimum stop distance (ATR)
input double          InpSLMaxATR       = 2.6;           // Skip setups needing a wider stop (ATR)
input int             InpHoldMinutes    = 480;           // Time stop for trades that go nowhere
input double          InpCostPrice      = 0.35;          // Round-trip spread + slippage charged per tested trade (price units; keep equal to the EA)
input double          InpMinStopCosts   = 20.0;          // Skip setups whose stop is shorter than this many round-trip costs (0 = off; keep equal to the EA)
input bool            InpUseNews        = true;          // Warn around high-impact USD news
input int             InpNewsBefore     = 30;            // Minutes before
input int             InpNewsAfter      = 30;            // Minutes after
input string          InpInterSymbol    = "";            // DXY-like symbol (blank = auto, falls back to EURUSD)

//--- buffers ------------------------------------------------------------
double BufEma1[], BufEma2[], BufEma3[], BufMean[];
double BufBuy[], BufBuyClr[], BufSell[], BufSellClr[];
double BufExitWin[], BufExitLoss[];

//--- state --------------------------------------------------------------
CXauEngine g_eng;            // signals on the chart's newest bars
CXauEngine g_lab;            // daily Strategy Lab (fixed data window, same as the EA)
CXauNews   g_news;
CXPanel    g_pm;             // main panel
CXPanel    g_pl;             // scoreboard
XRATESARR(g_rates);
XRATESARR(g_hrates);
XRATESARR(g_irates);
XRATESARR(g_drates);
int        g_gh = 0, g_gi = 0;
int        g_hist = 10000;          // Strategy Lab window (resolved from InpHistoryBars)
int        g_mode = XAU_MODE_STEADY;
int        g_pass[XLAB_CELLS];      // TREND mode: passing combinations, best first
int        g_npass = 0;
int        g_best_s = -1, g_best_p = XP_CLASSIC;
string     g_inter_sym    = "";
bool       g_inter_invert = false;
datetime   g_last_bar     = 0;
ulong      g_last_ui      = 0;
datetime   g_last_alert   = 0;
int        g_start        = 0;      // chart index of engine bar 0
int        g_n            = 0;      // engine bars
ENUM_TIMEFRAMES g_htf     = PERIOD_H1;
bool       g_ready        = false;
bool       g_htf_missing  = false;
ulong      g_last_try     = 0;

// the strategy in use
datetime   g_lab_day = 0;
bool       g_lab_ok  = false;
int        g_cell    = -1;          // strategy * XP_COUNT + exit, -1 = still learning
bool       g_proven  = false;
int        g_act_s   = -1;
int        g_act_p   = XP_CLASSIC;
XExit      g_act_x;

// latest signal + its live simulation
int          g_sig_i   = -1;
XSignal      g_sig;
XTradeResult g_live;
bool         g_live_ok = false;
int          g_reason  = XR_WARMUP;
int          g_opp_dir = 0;
string       g_news_text = "";
string       g_news_block = "";
bool         g_news_blocked = false;

// forecast
XAnalog      g_an;
XAnalogAudit g_aud;
bool         g_an_show = false;
int          g_an_state = 0;           // 0 learning, 1 no clear direction, 2 leaning but unproven, 3 shown
int          g_an_up = 0, g_an_dn = 0;
CXauEngine   g_tfe[3];                 // M15 / H1 / H4 forecasters
ENUM_TIMEFRAMES g_tfs[3];
datetime     g_tf_bar[3];
string       g_tf_txt[3];

//+------------------------------------------------------------------+
color ClrText()  { return XRGB(214, 222, 235); }
color ClrDim()   { return XRGB(140, 150, 166); }
color ClrGreen() { return XRGB(0, 222, 132); }
color ClrRed()   { return XRGB(255, 92, 92); }
color ClrGold()  { return XRGB(255, 200, 64); }
color ClrCyan()  { return XRGB(64, 200, 255); }

string Px(const double v) { return DoubleToString(v, _Digits); }
string Money(const double v) { return DoubleToString(v, 2) + " " + AccountInfoString(ACCOUNT_CURRENCY); }

string DurText(const int bars)
{
   const int mins = bars * PeriodSeconds((ENUM_TIMEFRAMES)_Period) / 60;
   if(mins >= 14 * 1440) return IntegerToString((mins + 5040) / 10080) + " weeks";
   if(mins >= 2 * 1440) return IntegerToString((mins + 720) / 1440) + " days";
   if(mins >= 120) return IntegerToString(mins / 60) + "h" + ((mins % 60) > 0 ? IntegerToString(mins % 60) + "m" : "");
   return IntegerToString(mins) + "m";
}

// "close by" time: clock time for intraday holds, a date for holds of a day or more
string CloseByText(const datetime t, const int hold_bars)
{
   if((long)hold_bars * PeriodSeconds((ENUM_TIMEFRAMES)_Period) >= 86400) return TimeToString(t, TIME_DATE);
   return TimeToString(t, TIME_MINUTES);
}

// Size of the current signal for this account. fits = the smallest tradable lot stays within 1.5x the chosen
// risk, the rule the EA applies on a real account (it refuses the trade otherwise).
bool SignalSize(XLotPlan &lp, bool &fits)
{
   const double equity = (InpBalanceOverride > 0.0) ? InpBalanceOverride : AccountInfoDouble(ACCOUNT_EQUITY);
   const double freeM = (InpBalanceOverride > 0.0) ? InpBalanceOverride : AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   XPlanLots(_Symbol, equity, InpRiskPct, g_sig.risk, g_sig.dir > 0, g_sig.entry, 1000.0, 0.0, freeM, 1.0, lp);
   fits = lp.ok && lp.risk_pct <= InpRiskPct * 1.5 + 1e-9;
   return lp.risk_money > 0.0;
}

//+------------------------------------------------------------------+
int OnInit()
{
   // start clean after a timeframe or symbol change
   g_ready = false; g_n = 0; g_last_bar = 0; g_last_alert = 0; g_last_try = 0;
   g_lab_ok = false; g_lab_day = 0; g_cell = -1; g_proven = false; g_act_s = -1; g_act_p = XP_CLASSIC;
   g_sig_i = -1; g_live_ok = false; g_reason = XR_WARMUP; g_opp_dir = 0;
   SetIndexBuffer(0, BufEma1, INDICATOR_DATA);
   SetIndexBuffer(1, BufEma2, INDICATOR_DATA);
   SetIndexBuffer(2, BufEma3, INDICATOR_DATA);
   SetIndexBuffer(3, BufMean, INDICATOR_DATA);
   SetIndexBuffer(4, BufBuy, INDICATOR_DATA);
   SetIndexBuffer(5, BufBuyClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(6, BufSell, INDICATOR_DATA);
   SetIndexBuffer(7, BufSellClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(8, BufExitWin, INDICATOR_DATA);
   SetIndexBuffer(9, BufExitLoss, INDICATOR_DATA);

   for(int p = 0; p < 8; p++) PlotIndexSetDouble(p, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetInteger(4, PLOT_ARROW, 233);
   PlotIndexSetInteger(5, PLOT_ARROW, 234);
   PlotIndexSetInteger(6, PLOT_ARROW, 252);
   PlotIndexSetInteger(7, PLOT_ARROW, 251);
   IndicatorSetString(INDICATOR_SHORTNAME, "XAU Oracle");
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);

   g_hist = XResolveHistoryBars(InpHistoryBars, (ENUM_TIMEFRAMES)_Period);
   g_mode = XResolveMode((int)InpMode, (ENUM_TIMEFRAMES)_Period);
   g_npass = 0; g_best_s = -1;
   g_htf = (InpHTF == PERIOD_CURRENT) ? XAutoHTF((ENUM_TIMEFRAMES)_Period) : InpHTF;
   if(PeriodSeconds(g_htf) <= PeriodSeconds((ENUM_TIMEFRAMES)_Period)) g_htf = XAutoHTF((ENUM_TIMEFRAMES)_Period);
   g_inter_sym = XResolveInterSymbol(InpInterSymbol, g_inter_invert);

   g_news.before_min = InpNewsBefore;
   g_news.after_min = InpNewsAfter;
   g_news.min_importance = 3;

   g_pm.prefix = "XO_PM_"; g_pm.fs = InpFontSize; g_pm.pos = InpPanelPos; g_pm.x = 12; g_pm.y = 24; g_pm.min_w = 330;
   g_pl.prefix = "XO_PL_"; g_pl.fs = XMaxI(InpFontSize - 1, 7); g_pl.pos = InpLabPos; g_pl.x = 12; g_pl.y = 24; g_pl.min_w = 300;

   g_tfs[0] = PERIOD_M15; g_tfs[1] = PERIOD_H1; g_tfs[2] = PERIOD_H4;
   for(int k = 0; k < 3; k++) { g_tf_bar[k] = 0; g_tf_txt[k] = "..."; }

   if(InpChartShift)
   {
      ChartSetInteger(0, CHART_SHIFT, true);
      ChartSetDouble(0, CHART_SHIFT_SIZE, 22.0);
   }
   XMakeExit(XP_CLASSIC, g_eng.cfg, g_act_x);
   EventSetTimer(2);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, "XO_");
}

//+------------------------------------------------------------------+
//| configuration shared by every engine                              |
//+------------------------------------------------------------------+
void FillConfig(XConfig &c, const ENUM_TIMEFRAMES tf, const ENUM_TIMEFRAMES htf)
{
   c.Defaults();
   c.base_sec = PeriodSeconds(tf);
   c.htf_sec = PeriodSeconds(htf);
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
   // a fixed cost (not the spread of the moment) so the indicator and the EA test and choose alike
   c.cost_price = XMax(InpCostPrice, 0.01);
   c.min_stop_cost = XMax(InpMinStopCosts, 0.0);
   c.d1_mode = XResolveD1Mode((int)InpDailyTrend, tf);
   // the broker's real overnight swap, so multi-day exits are tested with what holding really costs
   c.swap_long = XSwapCostPerUnit(_Symbol, true);
   c.swap_short = XSwapCostPerUnit(_Symbol, false);
}

//+------------------------------------------------------------------+
//| Strategy Lab: once a day on a fixed window, then choose           |
//+------------------------------------------------------------------+
void SelectStrategy();
double LabTarget();

void RunLabIfNeeded(const datetime now_bar)
{
   const datetime ds = XServerDayStart(now_bar);
   if(g_lab_ok && ds == g_lab_day) return;
   FillConfig(g_lab.cfg, (ENUM_TIMEFRAMES)_Period, g_htf);
   // the fixed window (same bars as the EA): retried on every new bar until the history is there
   if(XRunDailyLab(g_lab, _Symbol, (ENUM_TIMEFRAMES)_Period, g_htf, g_hist, g_inter_sym, g_inter_invert,
                   LabTarget(), InpLabMinTrades, InpLabFolds, ds))
   {
      g_lab_ok = true;
      g_lab_day = ds;
      SelectStrategy();
      return;
   }
   if(g_lab_ok) return;                  // keep the previous result while waiting for history
   // nothing yet: use the chart's own bars so the screen is useful at once
   g_lab.SetBase(g_rates, g_n);
   g_lab.SetHTF(g_hrates, g_gh);
   g_lab.SetDaily(g_drates, ArraySize(g_drates));
   if(g_gi > 100) g_lab.SetInter(g_irates, g_gi, g_inter_invert);
   g_lab_ok = g_lab.Compute();
   if(g_lab_ok) g_lab.RunLab(g_lab.cfg.warmup, g_n - 2, LabTarget(), InpLabMinTrades, InpLabFolds);
   SelectStrategy();
}

double LabTarget()
{
   return (g_mode == XAU_MODE_TREND) ? InpTrendWinTarget : InpWinTarget;
}

void SelectStrategy()
{
   g_cell = -1;
   g_proven = false;
   g_npass = 0;
   g_best_s = -1;
   if(!g_lab_ok) return;
   for(int k = 0; k < XLAB_CELLS; k++)
   {
      const int c = g_lab.LabRanked(k);
      if(c < 0) break;
      if(g_lab.lab[c].qualified) g_pass[g_npass++] = c;
   }
   int us = (int)InpStrategy;
   const int up = (int)InpExit;
   if(InpOrbSolo) us = XS_ORB;
   g_cell = XResolveCell(g_lab, us, up, InpLabMinTrades, g_proven);
   if(g_cell < 0) { g_act_s = -1; return; }
   g_act_s = g_cell / XP_COUNT;
   g_act_p = g_cell % XP_COUNT;
   g_best_s = g_act_s; g_best_p = g_act_p;
   XMakeExit(g_act_p, g_eng.cfg, g_act_x);
}

// TREND mode: if another passing combination has a fresh signal on the last closed bar (and the best one has not),
// show that one (plan, box, alert). The history arrows stay those of the best combination.
void TrendOverlay()
{
   if(g_mode != XAU_MODE_TREND || g_npass < 2 || !g_ready) return;
   const int i = g_n - 2;
   if(g_sig_i == i) return;
   for(int k = 0; k < g_npass; k++)
   {
      const int c = g_pass[k];
      const int st = c / XP_COUNT, pr = c % XP_COUNT;
      if(st == g_best_s && pr == g_best_p) continue;
      XExit x;
      XMakeExit(pr, g_eng.cfg, x);
      XSignal s;
      if(!g_eng.StrategySignal(st, i, x, s)) continue;
      g_act_s = st; g_act_p = pr; g_act_x = x;
      g_cell = c; g_proven = true;
      g_sig = s; g_sig_i = i;
      return;
   }
}

//+------------------------------------------------------------------+
//| full rebuild on every new bar                                     |
//+------------------------------------------------------------------+
void FillBuffers(const int rates_total);
void AnalogRefresh();

bool Rebuild(const int rates_total, const datetime &time[], const double &open[], const double &high[],
             const double &low[], const double &close[], const long &tick_volume[], const int &spread[])
{
   const int n = XMinI(rates_total, g_hist);
   if(n < 400) return false;
   g_start = rates_total - n;
   g_n = n;
   ArrayResize(g_rates, n);
   for(int k = 0; k < n; k++)
   {
      const int idx = g_start + k;
      g_rates[k].time = time[idx];
      g_rates[k].open = open[idx];
      g_rates[k].high = high[idx];
      g_rates[k].low = low[idx];
      g_rates[k].close = close[idx];
      g_rates[k].tick_volume = tick_volume[idx];
      g_rates[k].spread = spread[idx];
      g_rates[k].real_volume = 0;
   }
   FillConfig(g_eng.cfg, (ENUM_TIMEFRAMES)_Period, g_htf);
   const int need_h = (int)((double)n * g_eng.cfg.base_sec / g_eng.cfg.htf_sec) + 320;
   g_gh = XLoadRates(_Symbol, g_htf, need_h, g_hrates);
   g_htf_missing = (g_gh < 300);
   g_eng.SetBase(g_rates, n);
   g_eng.SetHTF(g_hrates, g_gh);
   int gd = 0;
   if(g_eng.cfg.d1_mode > 0)
   {
      gd = XLoadRates(_Symbol, PERIOD_D1, XDailyBarsNeeded(n, (ENUM_TIMEFRAMES)_Period), g_drates);
      if(gd < 0) gd = 0;
   }
   g_eng.SetDaily(g_drates, gd);
   g_gi = 0;
   if(StringLen(g_inter_sym) > 0)
   {
      g_gi = XLoadRates(g_inter_sym, (ENUM_TIMEFRAMES)_Period, n + 50, g_irates);
      if(g_gi > 100) g_eng.SetInter(g_irates, g_gi, g_inter_invert);
   }
   if(!g_eng.Compute()) return false;
   g_ready = true;
   RunLabIfNeeded(time[rates_total - 1]);
   if(g_best_s >= 0)
   {
      // back to the Lab's best combination (TrendOverlay may have shown another one on the previous bar)
      g_act_s = g_best_s; g_act_p = g_best_p; g_cell = g_best_s * XP_COUNT + g_best_p; g_proven = g_lab.lab[g_cell].qualified;
   }
   XMakeExit(g_act_p, g_eng.cfg, g_act_x);
   FillBuffers(rates_total);
   TrendOverlay();
   AnalogRefresh();
   return true;
}

// One trade at a time through the history with the strategy in use: arrows + how each trade ended.
void FillBuffers(const int rates_total)
{
   const int n = g_n;
   for(int idx = 0; idx < rates_total; idx++)
   {
      BufEma1[idx] = 0.0; BufEma2[idx] = 0.0; BufEma3[idx] = 0.0; BufMean[idx] = 0.0;
      BufBuy[idx] = 0.0; BufSell[idx] = 0.0; BufBuyClr[idx] = 0.0; BufSellClr[idx] = 0.0;
      BufExitWin[idx] = 0.0; BufExitLoss[idx] = 0.0;
   }
   for(int k = g_eng.cfg.warmup; k < n; k++)
   {
      const int idx = g_start + k;
      BufEma1[idx] = g_eng.m_ema1[k];
      BufEma2[idx] = g_eng.m_ema2[k];
      BufEma3[idx] = g_eng.m_ema3[k];
      if(g_act_p == XP_MEANREV) BufMean[idx] = g_eng.m_sma5[k];
   }
   g_sig_i = -1;
   if(g_act_s < 0) return;
   const double clr = g_proven ? 0.0 : 1.0;
   int busy = -1;
   XSignal s;
   XTradeResult r;
   for(int i = g_eng.cfg.warmup + 10; i <= n - 2; i++)
   {
      if(i <= busy) continue;
      if(g_eng.StrategyDir(g_act_s, i) == 0) continue;
      if(!g_eng.StrategySignal(g_act_s, i, g_act_x, s)) continue;
      const int idx = g_start + i;
      const double a = g_eng.m_atr[i];
      if(InpShowHistory || i == n - 2)
      {
         if(s.dir > 0) { BufBuy[idx] = g_eng.m_l[i] - 0.7 * a;  BufBuyClr[idx] = clr; }
         else          { BufSell[idx] = g_eng.m_h[i] + 0.7 * a; BufSellClr[idx] = clr; }
      }
      g_sig_i = i;
      g_sig = s;
      busy = i;
      if(g_eng.SimulateTradeEx(i, s.dir, s.sl, n - 2, g_act_x, r))
      {
         busy = r.closed ? r.exit_idx : n;
         if(r.closed && InpShowHistory)
         {
            const int xi = g_start + r.exit_idx;
            if(r.r_net > 0.05) BufExitWin[xi] = g_eng.m_h[r.exit_idx] + 0.3 * a;
            else               BufExitLoss[xi] = g_eng.m_l[r.exit_idx] - 0.3 * a;
         }
      }
   }
}

void RefreshLive()
{
   if(!g_ready) return;
   const int n = g_n;
   g_live_ok = false;
   g_opp_dir = 0;
   if(g_act_s < 0) { g_reason = XR_WARMUP; return; }
   if(g_sig_i >= 0 && g_eng.SimulateTradeEx(g_sig_i, g_sig.dir, g_sig.sl, n - 1, g_act_x, g_live)) g_live_ok = true;
   XSignal t;
   g_eng.StrategySignal(g_act_s, n - 2, g_act_x, t);
   g_reason = t.reason;
   if(t.dir != 0 && g_sig_i >= 0 && g_sig_i != n - 2 && g_live_ok && !g_live.closed && t.dir != g_sig.dir) g_opp_dir = t.dir;
}

void UpdateForming(const int rates_total, const double &high[], const double &low[], const double &close[])
{
   if(!g_ready) return;
   const int k = g_n - 1;
   g_eng.m_h[k] = high[rates_total - 1];
   g_eng.m_l[k] = low[rates_total - 1];
   g_eng.m_c[k] = close[rates_total - 1];
}

//+------------------------------------------------------------------+
//| pattern-matching forecast                                          |
//+------------------------------------------------------------------+
void AnalogRefresh()
{
   g_an_show = false;
   g_an_state = 0;
   g_an_up = 0; g_an_dn = 0;
   if(!g_ready) return;
   const int n = g_n;
   g_eng.CalibrateForecast(n - 2, 3000);
   g_eng.AnalogQuery(n - 2, g_an);
   g_eng.AnalogAudit(n - 2, 1000, 4, g_aud);
   if(!g_an.ok) return;
   const int agree = (int)MathRound(g_an.conf4 * g_an.k);
   g_an_up = (g_an.dir4 > 0) ? agree : g_an.k - agree;
   g_an_dn = g_an.k - g_an_up;
   const bool confident = g_eng.AnalogConfident(g_an);
   const bool proven = (g_aud.nc4 >= 25 && g_aud.LowerBound(g_aud.hitc4, g_aud.nc4, g_eng.cfg.an_z) >= 0.5);
   if(!confident)   g_an_state = 1;
   else if(!proven) g_an_state = 2;
   else             { g_an_state = 3; g_an_show = true; }
}

string AnalogLine()
{
   if(!g_an.ok) return "Next candles: still learning from history";
   string dir = "DOWN";
   if(g_an.dir4 > 0) dir = "UP";
   const int agree = (g_an.dir4 > 0) ? g_an_up : g_an_dn;
   if(g_an_state == 3)
      return "Next candles: " + dir + " (" + IntegerToString(agree) + " of " + IntegerToString(g_an.k) + " similar cases; such calls right "
             + DoubleToString(100.0 * g_aud.Rate(g_aud.hitc4, g_aud.nc4), 0) + "%)";
   if(g_an_state == 2)
      return "Next candles: leaning " + dir + ", not proven here (such calls right " + DoubleToString(100.0 * g_aud.Rate(g_aud.hitc4, g_aud.nc4), 0) + "%)";
   return "Next candles: no clear direction (" + IntegerToString(g_an_up) + " up / " + IntegerToString(g_an_dn) + " down of " + IntegerToString(g_an.k) + ")";
}

// Next-candle call for M15 / H1 / H4, recomputed when that timeframe starts a new bar.
void RefreshTfForecasts()
{
   if(!InpShowTfForecast) return;
   for(int k = 0; k < 3; k++)
   {
      const datetime bt = iTime(_Symbol, g_tfs[k], 0);
      if(bt == 0 || bt == g_tf_bar[k]) continue;
      g_tf_bar[k] = bt;
      XRATESARR(b);
      XRATESARR(h);
      const ENUM_TIMEFRAMES htf = XAutoHTF(g_tfs[k]);
      const int gb = XLoadRates(_Symbol, g_tfs[k], 3000, b);
      const int gh = XLoadRates(_Symbol, htf, (int)(3000.0 * PeriodSeconds(g_tfs[k]) / PeriodSeconds(htf)) + 320, h);
      g_tf_txt[k] = "...";
      if(gb < 800 || gh < 300) continue;
      FillConfig(g_tfe[k].cfg, g_tfs[k], htf);
      g_tfe[k].SetBase(b, gb);
      g_tfe[k].SetHTF(h, gh);
      if(!g_tfe[k].Compute()) continue;
      // expected size of that timeframe's next candle (calibrated), then a direction only if it is proven there
      g_tfe[k].CalibrateForecast(gb - 2, 2000);
      string sz = "";
      if(g_tfe[k].fc_cal_ok)
         sz = "~" + DoubleToString(g_tfe[k].m_atr[gb - 2] * g_tfe[k].SeasonAt(bt + (datetime)PeriodSeconds(g_tfs[k])) * g_tfe[k].fc_krange, 1);
      g_tf_txt[k] = sz;
      XAnalog a;
      XAnalogAudit au;
      if(!g_tfe[k].AnalogQuery(gb - 2, a)) continue;
      g_tfe[k].AnalogAudit(gb - 2, 800, 4, au);
      const bool conf = g_tfe[k].AnalogConfident(a);
      const bool prov = (au.nc4 >= 25 && au.LowerBound(au.hitc4, au.nc4, g_tfe[k].cfg.an_z) >= 0.5);
      if(conf && prov)
      {
         string d = "down";
         if(a.dir4 > 0) d = "up";
         StringToUpper(d);
         g_tf_txt[k] = sz + " " + d + " " + DoubleToString(100.0 * au.Rate(au.hitc4, au.nc4), 0) + "%";
      }
   }
}

//+------------------------------------------------------------------+
//| projected candles + cone (re-anchored on the live price)          |
//+------------------------------------------------------------------+
void DrawForecast()
{
   for(int j = 0; j < 12; j++)
   {
      XObjDelete("XO_FB" + IntegerToString(j));
      XObjDelete("XO_FW" + IntegerToString(j));
      XObjDelete("XO_FU" + IntegerToString(j));
      XObjDelete("XO_FD" + IntegerToString(j));
   }
   XObjDelete("XO_FT");
   if(!InpShowForecast || !g_ready) return;
   const int n = g_n;
   const int period = g_eng.cfg.base_sec;
   const int steps = XMinI(XMaxI(InpForecastBars, 1), 7);
   const double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   const double live = (bid > 0.0) ? bid : g_eng.m_c[n - 1];
   const datetime t_first = g_eng.m_t[n - 1] + period;
   // calibrated range: cone and candle size (always); the pattern-match path only when it has proven itself here
   g_eng.ForecastRange(n - 2, live, t_first, steps);
   if(g_an_show && g_an.ok) g_eng.ForecastAnalog(g_an, live, t_first, steps);
   const bool path = g_an_show && g_eng.fc_n > 0;
   const int cnt = path ? XMinI(g_eng.fc_n, g_eng.rg_n > 0 ? g_eng.rg_n : g_eng.fc_n) : g_eng.rg_n;
   if(cnt < 1) return;
   const color cu = XRGB(70, 175, 130), cd = XRGB(215, 95, 95), cc = XRGB(140, 150, 175);
   for(int j = 0; j < cnt; j++)
   {
      const string sj = IntegerToString(j);
      const datetime t0 = path ? g_eng.fc_t[j] : g_eng.rg_t[j];
      if(path)
      {
         const color cl = (g_eng.fc_c[j] >= g_eng.fc_o[j]) ? cu : cd;
         XObjRect("XO_FB" + sj, t0 + (datetime)(period * 0.12), g_eng.fc_o[j], t0 + (datetime)(period * 0.88), g_eng.fc_c[j], cl, true);
         XObjTrend("XO_FW" + sj, t0 + (datetime)(period * 0.5), g_eng.fc_l[j], t0 + (datetime)(period * 0.5), g_eng.fc_h[j], cl, STYLE_SOLID, 1, false);
      }
      else
      {
         // no direction: a grey outline as tall as the next candle is expected to be (median-corrected size)
         const double half = 0.5 * g_eng.rg_size[j];
         XObjRect("XO_FB" + sj, t0 + (datetime)(period * 0.2), g_eng.rg_mid[j] - half, t0 + (datetime)(period * 0.8), g_eng.rg_mid[j] + half, cc, false);
      }
      if(InpShowCone && g_eng.rg_n > j + 1)
      {
         const datetime t1 = g_eng.rg_t[j + 1];
         XObjTrend("XO_FU" + sj, t0 + (datetime)(period * 0.5), g_eng.rg_up[j], t1 + (datetime)(period * 0.5), g_eng.rg_up[j + 1], cc, STYLE_SOLID, 1, false);
         XObjTrend("XO_FD" + sj, t0 + (datetime)(period * 0.5), g_eng.rg_dn[j], t1 + (datetime)(period * 0.5), g_eng.rg_dn[j + 1], cc, STYLE_SOLID, 1, false);
      }
   }
   string lab = "expected size and 60% range (direction unknown)";
   color lc = cc;
   if(path) { lab = (g_an.dir4 > 0) ? "PREDICTED: UP" : "PREDICTED: DOWN"; lc = (g_an.dir4 > 0) ? cu : cd; }
   const double top = (g_eng.rg_n > 0) ? g_eng.rg_up[g_eng.rg_n - 1] : g_eng.fc_up[g_eng.fc_n - 1];
   XObjText("XO_FT", t_first, top, lab, lc, 8);
}

// "Next 3 bars: 60% between A and B, candles about X high" (calibrated on this chart's history)
string RangeLine()
{
   if(!g_eng.fc_cal_ok || g_eng.rg_n < 3) return "";
   return "Next 3 candles: about " + DoubleToString(g_eng.rg_size[0], _Digits > 2 ? 2 : _Digits) + " high each; price 60% likely between "
          + Px(g_eng.rg_dn[2]) + " and " + Px(g_eng.rg_up[2]);
}

//+------------------------------------------------------------------+
//| the green / red trade box                                         |
//+------------------------------------------------------------------+
// price the trade is aiming for (for the mean-reversion exit: today's 5-bar mean)
// Average winning trade of the strategy in use, in R (the mean-revert exit has no fixed target).
double TypicalWinR()
{
   if(g_cell >= 0 && g_lab.lab[g_cell].all.wins >= 5) return XClamp(g_lab.lab[g_cell].all.sum_win / g_lab.lab[g_cell].all.wins, 0.2, 3.0);
   return 0.8;
}

// Where the green box ends: the fixed target, or for the mean-revert exit the typical winning exit.
// (The mean-revert exit itself is a moving level, the 5-bar mean; drawing it as the target put the "profit"
// box under a buy whenever price had fallen since the signal.)
double TargetPrice()
{
   if(g_sig.tp2 > 0.0) return g_sig.tp2;
   if(g_sig.tp1 > 0.0) return g_sig.tp1;
   return g_sig.entry + g_sig.dir * TypicalWinR() * g_sig.risk;
}

// Mean-revert exit trigger right now: close the trade when a candle closes beyond this 5-bar mean.
double MeanTrigger()
{
   return g_eng.m_sma5[g_n - 2];
}

bool TradeActive()
{
   if(!g_ready || g_sig_i < 0 || g_act_s < 0) return false;
   return (g_sig_i == g_n - 2) || (g_live_ok && !g_live.closed);
}

void DrawTradeBox()
{
   const string nm[12] = {"XO_BX_R", "XO_BX_G1", "XO_BX_G2", "XO_BX_E", "XO_BX_TR", "XO_BX_T0", "XO_BX_T1", "XO_BX_T2", "XO_BX_T3", "XO_BX_T4",
                          "XO_BX_MR", "XO_BX_T5"};
   for(int k = 0; k < 12; k++) XObjDelete(nm[k]);
   if(!InpShowTradeBox || !TradeActive()) return;
   const int period = g_eng.cfg.base_sec;
   const datetime t0 = g_eng.m_t[g_sig_i + 1];
   const int hold = (g_act_x.max_hold > 0) ? g_act_x.max_hold : g_eng.MaxHold();
   const datetime t_end = t0 + (datetime)(XMinI(hold, 30) * period);
   const bool buy = (g_sig.dir > 0);
   const double entry = g_sig.entry;
   const double tgt = TargetPrice();
   const double tp1 = g_sig.tp1;

   XObjRect("XO_BX_R", t0, entry, t_end, g_sig.sl, XRGB(110, 34, 38), true);
   if(tp1 > 0.0 && g_sig.tp2 > 0.0 && MathAbs(g_sig.tp2 - tp1) > 1e-9)
   {
      XObjRect("XO_BX_G1", t0, entry, t_end, tp1, XRGB(28, 110, 72), true);
      XObjRect("XO_BX_G2", t0, tp1, t_end, g_sig.tp2, XRGB(20, 84, 56), true);
   }
   else XObjRect("XO_BX_G1", t0, entry, t_end, tgt, XRGB(28, 110, 72), true);
   XObjTrend("XO_BX_E", t0, entry, t_end, entry, XRGB(235, 235, 245), STYLE_SOLID, 1, false);
   if(g_live_ok && !g_live.closed && g_live.stage == 1)
      XObjTrend("XO_BX_TR", t0, g_live.cur_sl, t_end, g_live.cur_sl, XRGB(255, 170, 60), STYLE_SOLID, 1, false);

   const datetime tl = t_end + (datetime)period;
   const string side = buy ? "BUY " : "SELL ";
   XObjText("XO_BX_T0", tl, entry, side + Px(entry), XRGB(235, 235, 245), 9);
   XObjText("XO_BX_T1", tl, g_sig.sl, "STOP " + Px(g_sig.sl), XRGB(255, 120, 120), 9);
   if(g_act_x.mr_exit == 1)
   {
      const double trg = MeanTrigger();
      XObjText("XO_BX_T2", tl, tgt, "TYPICAL EXIT " + Px(tgt), XRGB(90, 230, 160), 9);
      XObjTrend("XO_BX_MR", t0, trg, t_end, trg, XRGB(90, 230, 160), STYLE_DOT, 1, false);
      const bool loss_side = (g_sig.dir > 0) ? (trg <= entry) : (trg >= entry);
      const string ex_txt = buy ? "exit on a close above " : "exit on a close below ";
      const string ls_txt = loss_side ? " (past the entry: small loss)" : "";
      XObjText("XO_BX_T5", tl, trg, ex_txt + Px(trg) + ls_txt,
               loss_side ? XRGB(255, 170, 60) : XRGB(90, 230, 160), 8);
   }
   else if(tp1 > 0.0 && g_sig.tp2 > 0.0 && MathAbs(g_sig.tp2 - tp1) > 1e-9)
   {
      XObjText("XO_BX_T2", tl, tp1, "TAKE " + DoubleToString(g_act_x.part * 100.0, 0) + "% " + Px(tp1), XRGB(90, 230, 160), 9);
      XObjText("XO_BX_T3", tl, g_sig.tp2, "TARGET " + Px(g_sig.tp2), XRGB(90, 230, 160), 9);
   }
   else XObjText("XO_BX_T2", tl, tgt, "TARGET " + Px(tgt), XRGB(90, 230, 160), 9);
   XObjText("XO_BX_T4", t0, g_sig.sl, "close by " + CloseByText(t0 + (datetime)(hold * period), hold), XRGB(255, 200, 64), 8);
}

//+------------------------------------------------------------------+
//| opening range box and key levels                                  |
//+------------------------------------------------------------------+
void DrawOrb()
{
   XObjDelete("XO_OR_BOX"); XObjDelete("XO_OR_H"); XObjDelete("XO_OR_L");
   if(!InpShowOrb || !g_ready) return;
   const int last = g_n - 1;
   const int st = g_eng.m_orbst[last];
   if(st <= 0 || g_eng.m_orbt0[last] == 0) return;
   const int period = g_eng.cfg.base_sec;
   const datetime t1 = g_eng.m_t[last] + (datetime)(period * 3);
   const color cc = (st == 3) ? XRGB(70, 140, 255) : ((st == 2) ? XRGB(110, 150, 210) : XRGB(150, 160, 175));
   XObjRect("XO_OR_BOX", g_eng.m_orbt0[last], g_eng.m_orblo[last], t1, g_eng.m_orbhi[last], cc, false);
   string fin = "";
   if(st == 3) fin = " (final)";
   XObjText("XO_OR_H", t1, g_eng.m_orbhi[last], " opening range high " + Px(g_eng.m_orbhi[last]) + fin, cc, 8);
   XObjText("XO_OR_L", t1, g_eng.m_orblo[last], " opening range low " + Px(g_eng.m_orblo[last]), cc, 8);
}

void DrawLevels()
{
   XObjDelete("XO_LV_PDH"); XObjDelete("XO_LV_PDL"); XObjDelete("XO_LV_ASIA");
   XObjDelete("XO_LV_T1"); XObjDelete("XO_LV_T2");
   if(!InpShowLevels || !g_ready) return;
   const int last = g_n - 1;
   const int period = g_eng.cfg.base_sec;
   const datetime t_right = g_eng.m_t[last] + (datetime)(period * 3);
   const int d0 = XMaxI(0, last - g_eng.m_daybars[last] + 1);
   if(g_eng.m_pdh[last] > 0.0)
   {
      XObjTrend("XO_LV_PDH", g_eng.m_t[d0], g_eng.m_pdh[last], t_right, g_eng.m_pdh[last], XRGB(255, 160, 40), STYLE_DASH, 1, false);
      XObjTrend("XO_LV_PDL", g_eng.m_t[d0], g_eng.m_pdl[last], t_right, g_eng.m_pdl[last], XRGB(255, 160, 40), STYLE_DASH, 1, false);
      XObjText("XO_LV_T1", t_right, g_eng.m_pdh[last], " yesterday high", XRGB(255, 160, 40), 8);
      XObjText("XO_LV_T2", t_right, g_eng.m_pdl[last], " yesterday low", XRGB(255, 160, 40), 8);
   }
   if(g_eng.m_asiaok[last] == 1 && period <= 7200)
   {
      int k = last;
      while(k > 0 && g_eng.m_hour[k] >= g_eng.cfg.asia_end) k--;
      while(k > 0 && g_eng.m_hour[k - 1] < g_eng.m_hour[k] && g_eng.m_hour[k - 1] >= g_eng.cfg.asia_start) k--;
      XObjRect("XO_LV_ASIA", g_eng.m_t[k], g_eng.m_asialo[last], t_right, g_eng.m_asiahi[last], XRGB(90, 100, 140), false);
   }
}

//+------------------------------------------------------------------+
//| panels                                                             |
//+------------------------------------------------------------------+
// the record to quote for the strategy in use: honest walk-forward record in AUTO mode
void QuoteRecord(XStats &st, bool &walkforward)
{
   walkforward = false;
   st.Reset();
   if(g_cell < 0) return;
   if(InpStrategy == XAU_ST_AUTO && InpExit == XAU_EX_AUTO && !InpOrbSolo && g_lab.lab_auto.n >= 10)
   {
      st = g_lab.lab_auto;
      walkforward = true;
      return;
   }
   st = g_lab.lab[g_cell].all;
}

void DrawMainPanel()
{
   if(!InpShowPanel || !g_ready) { g_pm.Clear(); return; }
   // MT5's One Click Trading buttons sit in the top-left corner and hid the status lines: start below them
   g_pm.y = (InpPanelPos == XAU_PANEL_TOP_LEFT && ChartGetInteger(0, CHART_SHOW_ONE_CLICK)) ? 104 : 24;
   const int n = g_n;
   const double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   const bool fresh = (g_sig_i == n - 2);
   const bool running = (g_live_ok && !g_live.closed && g_sig_i >= 0);
   const bool ended = (g_live_ok && g_live.closed && g_live.exit_idx == n - 1 && g_sig_i >= 0);
   const bool buy = (g_sig_i >= 0 && g_sig.dir > 0);

   string status = "WAIT";
   color  sc = ClrDim();
   string sub = XReasonText(g_reason);
   color  bg = XRGB(16, 20, 28);
   bool   plan = false;
   if(g_act_s < 0) { status = "LEARNING"; sub = "testing strategies on this chart's history"; }
   else if(g_news_blocked) { status = "STAY OUT - NEWS"; sc = ClrRed(); sub = g_news_block; }
   else if(fresh && g_live_ok)
   {
      const double dist = buy ? (bid - g_sig.entry) : (g_sig.entry - bid);
      if(dist > 0.35 * g_sig.atr) { status = "MISSED - don't chase"; sc = ClrGold(); sub = "price already ran away from the entry"; }
      else
      {
         XLotPlan fp;
         bool fits = false;
         SignalSize(fp, fits);
         if(fits)
         {
            status = buy ? "BUY NOW" : "SELL NOW";
            sc = buy ? ClrGreen() : ClrRed();
            bg = buy ? XRGB(10, 46, 32) : XRGB(56, 20, 24);
            sub = g_proven ? "tested strategy, see plan below" : "UNPROVEN strategy: demo / small size only";
         }
         else if(StringFind(fp.note, "margin") >= 0)
         {
            status = buy ? "BUY SIGNAL - NO FREE MARGIN" : "SELL SIGNAL - NO FREE MARGIN";
            sc = ClrGold(); bg = XRGB(46, 40, 16);
            sub = "your open trades use all the margin: close or protect them first";
         }
         else
         {
            status = buy ? "BUY SIGNAL - TOO BIG, SKIP" : "SELL SIGNAL - TOO BIG, SKIP";
            sc = ClrGold(); bg = XRGB(46, 40, 16);
            sub = "even the smallest lot risks " + DoubleToString(fp.risk_pct, 1) + "% of this account here";
         }
         plan = true;
      }
   }
   else if(running)
   {
      status = buy ? "HOLD BUY  " : "HOLD SELL  ";
      status += StringFormat("%+.1fR", g_live.float_r);
      sc = ClrCyan();
      sub = "trade in progress";
      plan = true;
   }
   else if(ended)
   {
      status = "EXIT NOW";
      sc = ClrGold();
      if(g_live.exit_kind == XE_STOP)          sub = "stop level was hit";
      else if(g_live.exit_kind == XE_TRAIL)    sub = "protective stop was hit";
      else if(g_live.exit_kind == XE_MR)       sub = "price is back at the mean: take the profit";
      else if(g_live.exit_kind == XE_TIME)     sub = "trade went nowhere: close it";
      else                                     sub = "target reached: take the profit";
   }
   if(g_opp_dir != 0) sub = "warning: opposite setup appeared, consider closing";

   g_pm.bg = bg;
   g_pm.Begin();
   g_pm.Line("XAU ORACLE  " + XTfName((ENUM_TIMEFRAMES)_Period) + "   " + Px(bid), ClrGold());
   g_pm.Line(status, sc, 4);
   g_pm.Line(sub, ClrDim());
   {
      bool go;
      const bool intraday = PeriodSeconds((ENUM_TIMEFRAMES)_Period) < 86400;
      const string today = XTodayPlan(g_mode, g_npass, g_proven, false, g_eng.cfg.d1_mode, (g_eng.d1n > 0) ? g_eng.m_dreg[n - 1] : 0,
                                      intraday ? g_eng.m_adr[n - 1] : 0.0, intraday ? g_eng.m_adru[n - 1] : 0.0, go);
      g_pm.Line(today, go ? ClrGreen() : ClrGold());
   }

   if(plan)
   {
      const double tgt = TargetPrice();
      if(g_act_x.mr_exit == 1)
      {
         g_pm.Line((buy ? "Buy " : "Sell ") + Px(g_sig.entry) + "   Stop " + Px(g_sig.sl) + "   Typical exit " + Px(tgt), ClrText());
         const string side = buy ? "above " : "below ";
         g_pm.Line("Exit rule: close when a candle closes " + side + Px(MeanTrigger()) + " (the 5-bar mean, it moves)", ClrDim());
      }
      else
         g_pm.Line((buy ? "Buy " : "Sell ") + Px(g_sig.entry) + "   Stop " + Px(g_sig.sl) + "   Target " + Px(tgt), ClrText());
      XLotPlan lp;
      bool fits = false;
      if(SignalSize(lp, fits))
      {
         double avg_win_r = 0.0;
         if(g_cell >= 0 && g_lab.lab[g_cell].all.wins > 0) avg_win_r = g_lab.lab[g_cell].all.sum_win / g_lab.lab[g_cell].all.wins;
         string ln = "Trade " + DoubleToString(lp.lots, 2) + " lot: risk " + Money(lp.risk_money);
         if(avg_win_r > 0.0) ln += ", typical win " + Money(lp.risk_money * avg_win_r);
         g_pm.Line(ln, fits ? ClrGreen() : ClrGold());
         if(!fits && lp.ok)
         {
            const double need = lp.risk_money * 100.0 / XMax(InpRiskPct, 0.01);
            g_pm.Line("That is " + DoubleToString(lp.risk_pct, 1) + "% of the account (your limit " + DoubleToString(InpRiskPct, 1)
                      + "%). This trade needs about " + DoubleToString(need, 0) + " " + AccountInfoString(ACCOUNT_CURRENCY)
                      + ", or use a lower timeframe.", ClrGold());
         }
         else if(!lp.ok) g_pm.Line("Size: " + lp.note, ClrRed());
      }
      else g_pm.Line("Size: " + lp.note, ClrRed());
      const int hold = (g_act_x.max_hold > 0) ? g_act_x.max_hold : g_eng.MaxHold();
      const int typ = g_lab.LabHoldMedian(g_cell);
      const datetime close_by = g_eng.m_t[g_sig_i + 1] + (datetime)(hold * g_eng.cfg.base_sec);
      string hl = "Stay about " + DurText(XMaxI(typ, 1)) + " (typical); close by " + CloseByText(close_by, hold) + " at the latest";
      g_pm.Line(hl, ClrText());
      if(running && g_act_x.tp1_r > 0.0 && g_act_x.part < 0.999)
      {
         if(g_live.stage == 0) g_pm.Line("At " + Px(g_sig.tp1) + " close " + DoubleToString(g_act_x.part * 100.0, 0) + "% and move the stop to your entry.", ClrDim());
         else                  g_pm.Line("Part banked. Stop now " + Px(g_live.cur_sl) + ". Let the rest run.", ClrDim());
      }
   }

   if(g_mode == XAU_MODE_TREND)
   {
      string mline = "TREND mode: ";
      if(g_npass > 0) mline += IntegerToString(g_npass) + " strateg" + (g_npass > 1 ? "ies" : "y") + " passed today; any of them can signal";
      else mline += "nothing passed today";
      if(g_eng.cfg.d1_mode == 2 && g_eng.d1n > 0 && g_eng.m_dreg[n - 1] <= 0) mline += " - daily trend not up: no buys";
      g_pm.Line(mline, (g_npass > 0) ? ClrGreen() : ClrGold());
   }
   if(g_act_s >= 0)
   {
      string badge = "  [PROVEN]";
      if(!g_proven) badge = "  [UNPROVEN]";
      g_pm.Line("Strategy: " + XStratName(g_act_s) + " + " + XExitName(g_act_p) + badge, g_proven ? ClrGreen() : ClrGold());
      XStats rec;
      bool wf;
      QuoteRecord(rec, wf);
      if(rec.n > 0)
      {
         string how = " (in-sample)";
         if(wf) how = " (walk-forward)";
         g_pm.Line("Tested here" + how + ": " + DoubleToString(rec.WinRate(), 0) + "% won, avg " + StringFormat("%+.2f", rec.Expectancy())
                   + "R, " + IntegerToString(rec.n) + " trades", (rec.Expectancy() > 0.0 && rec.WinRate() >= InpWinTarget) ? ClrGreen() : ClrGold());
      }
      if(!g_proven) g_pm.Line("Nothing reached " + DoubleToString(InpWinTarget, 0) + "% wins with profit here yet: showing the closest.", ClrGold());
   }
   const int tb = g_eng.m_bias[n - 1];
   string tr = "SIDEWAYS";
   if(tb > 0) tr = "UP";
   if(tb < 0) tr = "DOWN";
   string trl = "Trend " + XTfName(g_htf) + ": " + tr;
   if(g_eng.cfg.d1_mode > 0 && g_eng.d1n > 0)
   {
      const int dr = g_eng.m_dreg[n - 1];
      string dtx = "Daily: ?";
      if(dr > 0) dtx = "Daily: UP";
      if(dr < 0) dtx = (g_eng.cfg.d1_mode == 2) ? "Daily: DOWN (no buys)" : "Daily: DOWN";
      trl += "   " + dtx;
   }
   if(PeriodSeconds((ENUM_TIMEFRAMES)_Period) < 86400) trl += "   Day range used " + DoubleToString(100.0 * g_eng.m_adru[n - 1], 0) + "%";
   g_pm.Line(trl, ClrText());
   g_pm.Line(XSessionLine(g_eng.cfg, TimeTradeServer()), ClrDim());
   g_pm.Line(AnalogLine(), (g_an_state == 3) ? ((g_an.dir4 > 0) ? ClrGreen() : ClrRed()) : ClrDim());
   const string rl = RangeLine();
   if(StringLen(rl) > 0) g_pm.Line(rl, ClrText());
   if(InpShowTfForecast)
      g_pm.Line("Next candle size:  M15 " + g_tf_txt[0] + "   H1 " + g_tf_txt[1] + "   H4 " + g_tf_txt[2], ClrDim());
   const string warn = XAccountWarning(_Symbol);
   if(StringLen(warn) > 0) g_pm.Line("RISK: " + warn, ClrRed());
   if(InpUseNews && !g_news_blocked && StringFind(g_news_text, " in ") >= 0) g_pm.Line("News: " + g_news_text, ClrDim());
   g_pm.End();
}

void DrawLabPanel()
{
   if(!InpShowLab || !g_lab_ok) { g_pl.Clear(); return; }
   g_pl.Begin();
   const int days = (g_lab.n > 0 && g_lab.lab_first < g_lab.n) ? (int)((g_lab.m_t[g_lab.n - 1] - g_lab.m_t[g_lab.lab_first]) / 86400) : 0;
   g_pl.Line("STRATEGY LAB  " + IntegerToString(days) + " days tested here, target " + DoubleToString(InpWinTarget, 0) + "% wins", ClrGold());
   g_pl.Line(StringFormat("%-2s%-34s %5s %6s %6s", "", "strategy / exit", "won", "avg R", "trades"), ClrDim());
   for(int k = 0; k < 6; k++)
   {
      const int c = g_lab.LabRanked(k);
      if(c < 0) break;
      const XStats st = g_lab.lab[c].all;
      string mark = "  ";
      if(c == g_cell) mark = "> ";
      string pass = "";
      if(g_lab.lab[c].qualified) pass = " PASS";
      const string name = XStratName(c / XP_COUNT) + " / " + XExitShort(c % XP_COUNT);   // at most 34 characters
      g_pl.Line(StringFormat("%-2s%-34s %4.0f%% %+6.2f %6d", mark, name, st.WinRate(), st.Expectancy(), st.n) + pass,
                g_lab.lab[c].qualified ? ClrGreen() : ClrText());
   }
   if(g_lab.lab_auto.n > 0)
      g_pl.Line("Auto-pick, walk-forward: " + DoubleToString(g_lab.lab_auto.WinRate(), 0) + "% won, avg "
                + StringFormat("%+.2f", g_lab.lab_auto.Expectancy()) + "R over " + IntegerToString(g_lab.lab_auto.n) + " trades", ClrCyan());
   else g_pl.Line("Auto-pick, walk-forward: no strategy qualified in the test folds", ClrDim());
   g_pl.Line(IntegerToString(g_lab.lab_qualified) + " of " + IntegerToString(XLAB_CELLS) + " combinations pass. Re-tested every day.", ClrDim());
   g_pl.End();
}

//+------------------------------------------------------------------+
//| alerts and news                                                   |
//+------------------------------------------------------------------+
void MaybeAlert()
{
   if(!g_ready || g_act_s < 0 || g_sig_i != g_n - 2) return;
   const datetime bt = g_eng.m_t[g_n - 1];
   if(g_last_alert == bt) return;
   g_last_alert = bt;
   XLotPlan fp;
   bool fits = false;
   SignalSize(fp, fits);
   if(!fits) { Print("XAU Oracle: signal not alerted, too big for this account (", fp.note, " ", DoubleToString(fp.risk_pct, 1), "%)"); return; }
   string msg = "XAU Oracle " + _Symbol + " " + XTfName((ENUM_TIMEFRAMES)_Period) + ": ";
   msg += (g_sig.dir > 0) ? "BUY " : "SELL ";
   msg += Px(g_sig.entry) + " stop " + Px(g_sig.sl) + " target " + Px(TargetPrice()) + " [" + XStratName(g_act_s) + "]";
   if(!g_proven) msg += " UNPROVEN";
   if(InpAlertPopup) Alert(msg);
   if(InpAlertSound) PlaySound("alert.wav");
   if(InpAlertPush)  SendNotification(msg);
   if(InpAlertEmail) SendMail("XAU Oracle signal", msg);
}

void RefreshNews()
{
   if(!InpUseNews) { g_news_blocked = false; g_news_text = ""; return; }
   g_news.Refresh(TimeCurrent());
   g_news.gmt_offset_sec = XOffsetAt(g_eng.cfg, TimeCurrent());
   g_news_blocked = g_news.Blocked(TimeCurrent(), g_news_block);
   g_news_text = g_news.NextText(TimeCurrent());
}

void RedrawAll()
{
   DrawTradeBox();
   DrawForecast();
   DrawMainPanel();
   DrawLabPanel();
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   if(rates_total < 420) return 0;
   const datetime bt = time[rates_total - 1];
   bool retry = false;
   if(g_htf_missing && GetTickCount64() - g_last_try > 5000) { retry = true; g_last_try = GetTickCount64(); }
   const bool newbar = (bt != g_last_bar) || (prev_calculated == 0) || retry;
   if(newbar)
   {
      g_last_bar = bt;
      if(Rebuild(rates_total, time, open, high, low, close, tick_volume, spread))
      {
         RefreshNews();
         RefreshTfForecasts();
         RefreshLive();
         DrawLevels();
         DrawOrb();
         RedrawAll();
         MaybeAlert();
         ChartRedraw(0);
      }
      g_last_ui = GetTickCount64();
      return rates_total;
   }
   if(!g_ready) return rates_total;
   // intrabar: keep the forming bar and the live price current, at most once a second
   const ulong now_ms = GetTickCount64();
   if(now_ms - g_last_ui >= 1000)
   {
      g_last_ui = now_ms;
      UpdateForming(rates_total, high, low, close);
      RefreshLive();
      RedrawAll();
      ChartRedraw(0);
   }
   return rates_total;
}

void OnTimer()
{
   if(!g_ready) return;
   RefreshNews();
   RefreshTfForecasts();
   DrawMainPanel();
   DrawLabPanel();
}
