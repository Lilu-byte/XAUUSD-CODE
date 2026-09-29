//+------------------------------------------------------------------+
//|                                                  XAU_Oracle.mq5  |
//|  XAUUSD confluence indicator: entries, stops, targets, position  |
//|  size, expected hold time, projected candles and an on-chart     |
//|  trial of its own signals on YOUR broker's history.              |
//|                                                                  |
//|  Signals are computed on closed bars only and never repaint.     |
//|  The projection is a statistical expectation, not a promise.     |
//+------------------------------------------------------------------+
#property copyright   "XAU Oracle"
#property version     "1.00"
#property description "XAUUSD multi-strategy confluence indicator with trade plan,"
#property description "position sizing, hold-time estimate, projected candles and a"
#property description "built-in trial of its own signals. No signal is a guarantee."
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

#property indicator_label4  "Session VWAP"
#property indicator_type4   DRAW_LINE
#property indicator_color4  clrMediumOrchid
#property indicator_style4  STYLE_DOT
#property indicator_width4  1

#property indicator_label5  "Buy"
#property indicator_type5   DRAW_COLOR_ARROW
#property indicator_color5  clrLimeGreen,clrSpringGreen,clrAqua
#property indicator_width5  3

#property indicator_label6  "Sell"
#property indicator_type6   DRAW_COLOR_ARROW
#property indicator_color6  clrOrangeRed,clrRed,clrMagenta
#property indicator_width6  3

#property indicator_label7  "Exit (profit)"
#property indicator_type7   DRAW_ARROW
#property indicator_color7  clrLimeGreen
#property indicator_width7  1

#property indicator_label8  "Exit (loss)"
#property indicator_type8   DRAW_ARROW
#property indicator_color8  clrTomato
#property indicator_width8  1

#include <XAU/XAU_Platform.mqh>

//--- inputs -----------------------------------------------------------
input group "=== Core ==="
input int             InpHistoryBars    = 6000;          // Bars analysed (signals, trial, stats)
input ENUM_TIMEFRAMES InpHTF            = PERIOD_CURRENT; // Higher timeframe for bias (CURRENT = automatic)
input bool            InpManualGmt      = false;         // Set broker GMT offset by hand
input double          InpGmtOffsetHrs   = 2.0;           // Broker server time minus GMT (hours)

input group "=== Signal engine ==="
input double          InpScoreMin       = 1.7;           // Confluence score needed for a signal
input int             InpMinConfluence  = 2;             // Minimum agreeing strategy modules
input int             InpMinGrade       = 1;             // Lowest grade shown: 1=B, 2=A, 3=A+
input bool            InpModPullback    = true;          // Module: trend pullback
input bool            InpModSweep       = true;          // Module: liquidity sweep reversal
input bool            InpModBreakout    = true;          // Module: Asian-range session breakout
input bool            InpModSqueeze     = true;          // Module: volatility squeeze break
input bool            InpModVwap        = true;          // Module: VWAP extreme fade
input bool            InpModDiverge     = true;          // Module: RSI divergence
input bool            InpModFvg         = true;          // Module: fair value gap retest
input bool            InpModRound       = true;          // Module: round-number rejection

input group "=== Trade plan ==="
input double          InpTP1_R          = 1.0;           // First target (multiples of risk)
input double          InpTP2_R          = 2.5;           // Runner target (multiples of risk)
input double          InpPartialPct     = 50.0;          // % of position closed at TP1
input double          InpTrailATR       = 2.0;           // Trailing stop distance after TP1 (ATR)
input double          InpSLMinATR       = 0.9;           // Minimum stop distance (ATR)
input double          InpSLMaxATR       = 2.6;           // Skip setups needing a wider stop (ATR)
input int             InpHoldMinutes    = 480;           // Time stop for a trade that goes nowhere

input group "=== Session (GMT clock) ==="
input bool            InpSessionFilter  = true;          // Only signal inside the trading window
input double          InpTradeStartGMT  = 7.0;           // Window start (London open)
input double          InpTradeEndGMT    = 20.0;          // Window end
input double          InpFridayCutGMT   = 19.0;          // No new signals after this on Fridays

input group "=== Money ==="
input double          InpBalanceOverride = 0.0;          // 0 = use account equity
input double          InpRiskPct        = 1.0;           // Risk per trade, % of balance

input group "=== Visuals ==="
input bool            InpShowPanel      = true;          // Dashboard
input int             InpPanelX         = 12;            // Panel X offset
input int             InpPanelY         = 24;            // Panel Y offset
input int             InpFontSize       = 9;             // Panel font size
input bool            InpShowForecast   = true;          // Projected candles
input int             InpForecastBars   = 8;             // Bars to project
input bool            InpShowCone       = true;          // Expected range cone
input bool            InpShowLevels     = true;          // Prev-day high/low + Asian range
input bool            InpShowExits      = true;          // Mark where past trades would have ended
input bool            InpShowMTF        = true;          // Multi-timeframe trend strip
input bool            InpChartShift     = true;          // Leave room on the right for projections

input group "=== Alerts ==="
input bool            InpAlertPopup     = true;
input bool            InpAlertPush      = false;
input bool            InpAlertEmail     = false;
input bool            InpAlertSound     = true;

input group "=== News & intermarket ==="
input bool            InpUseNews        = true;          // Warn around high-impact USD news
input int             InpNewsBefore     = 30;            // Minutes before
input int             InpNewsAfter      = 30;            // Minutes after
input string          InpInterSymbol    = "";            // DXY-like symbol (blank = auto, falls back to EURUSD)

//--- buffers ------------------------------------------------------------
double BufEma1[], BufEma2[], BufEma3[], BufVwap[];
double BufBuy[], BufBuyClr[], BufSell[], BufSellClr[];
double BufExitWin[], BufExitLoss[];

//--- state --------------------------------------------------------------
CXauEngine g_eng;
CXauNews   g_news;
XTrial     g_trial;
XRATESARR(g_rates);
XRATESARR(g_hrates);
XRATESARR(g_irates);
string     g_inter_sym    = "";
bool       g_inter_invert = false;
datetime   g_last_bar     = 0;
ulong      g_last_ui      = 0;
datetime   g_last_alert   = 0;
int        g_start        = 0;      // chart index of engine bar 0
int        g_n            = 0;      // engine bars
ENUM_TIMEFRAMES g_htf     = PERIOD_H1;
bool       g_ready        = false;
int        g_rows_prev    = 34;     // panel rows drawn last time (background is created first)
bool       g_htf_missing  = false;  // higher-TF history not loaded yet -> retry
ulong      g_last_try     = 0;

// latest taken signal + its live simulation
int          g_sig_i   = -1;
XSignal      g_sig;
XTradeResult g_live;
bool         g_live_ok = false;
int          g_reason  = XR_WARMUP;   // why the newest closed bar is not a signal
int          g_opp_dir = 0;           // opposite-direction warning while in a trade
double       g_mtf_dir[5];
double       g_mtf_adx[5];
datetime     g_mtf_time = 0;
string       g_news_text = "";
string       g_news_block = "";
bool         g_news_blocked = false;
int          g_trial_days = 0;
int          g_fa_n = 0, g_fa_hit = 0;

//+------------------------------------------------------------------+
color CText()  { return XRGB(214, 222, 235); }
color CDim()   { return XRGB(132, 142, 158); }
color CGreen() { return XRGB(0, 222, 132); }
color CRed()   { return XRGB(255, 92, 92); }
color CGold()  { return XRGB(255, 200, 64); }
color CCyan()  { return XRGB(64, 200, 255); }

//+------------------------------------------------------------------+
int OnInit()
{
   SetIndexBuffer(0, BufEma1, INDICATOR_DATA);
   SetIndexBuffer(1, BufEma2, INDICATOR_DATA);
   SetIndexBuffer(2, BufEma3, INDICATOR_DATA);
   SetIndexBuffer(3, BufVwap, INDICATOR_DATA);
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

   g_htf = (InpHTF == PERIOD_CURRENT) ? XAutoHTF((ENUM_TIMEFRAMES)_Period) : InpHTF;
   if(PeriodSeconds(g_htf) <= PeriodSeconds((ENUM_TIMEFRAMES)_Period)) g_htf = XAutoHTF((ENUM_TIMEFRAMES)_Period);

   g_inter_sym = XResolveInterSymbol(InpInterSymbol, g_inter_invert);

   g_news.before_min = InpNewsBefore;
   g_news.after_min = InpNewsAfter;
   g_news.min_importance = 3;

   if(InpChartShift)
   {
      ChartSetInteger(0, CHART_SHIFT, true);
      ChartSetDouble(0, CHART_SHIFT_SIZE, 22.0);
   }
   for(int k = 0; k < 5; k++) { g_mtf_dir[k] = 0.0; g_mtf_adx[k] = 0.0; }
   EventSetTimer(2);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, "XO_");
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
   c.en[XM_PULLBACK] = InpModPullback ? 1 : 0;
   c.en[XM_SWEEP]    = InpModSweep    ? 1 : 0;
   c.en[XM_BREAKOUT] = InpModBreakout ? 1 : 0;
   c.en[XM_SQUEEZE]  = InpModSqueeze  ? 1 : 0;
   c.en[XM_VWAP]     = InpModVwap     ? 1 : 0;
   c.en[XM_DIVERGE]  = InpModDiverge  ? 1 : 0;
   c.en[XM_FVG]      = InpModFvg      ? 1 : 0;
   c.en[XM_ROUND]    = InpModRound    ? 1 : 0;
   c.tp1_r = InpTP1_R;
   c.tp2_r = XMax(InpTP2_R, InpTP1_R + 0.1);
   c.partial_pct = XClamp(InpPartialPct / 100.0, 0.0, 1.0);
   c.trail_atr = InpTrailATR;
   c.sl_atr_min = InpSLMinATR;
   c.sl_atr_max = XMax(InpSLMaxATR, InpSLMinATR + 0.1);
   c.hold_minutes = InpHoldMinutes;
   // typical XAUUSD round-turn cost for the simulation: spread + slippage
   const double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   const double sp = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * pt;
   c.cost_price = XMax(sp * 1.5, 0.10);
   g_eng.cfg = c;
   g_news.gmt_offset_sec = c.gmt_offset_sec;
}

//+------------------------------------------------------------------+
//| full rebuild: engine, buffers, trial, plan, projection            |
//+------------------------------------------------------------------+
void FillBuffers(const int rates_total);

bool Rebuild(const int rates_total, const datetime &time[], const double &open[], const double &high[],
             const double &low[], const double &close[], const long &tick_volume[], const int &spread[])
{
   int n = XMinI(rates_total, InpHistoryBars);
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

   ApplyConfig();
   const int base_sec = g_eng.cfg.base_sec;
   const int htf_sec = g_eng.cfg.htf_sec;
   const int need_h = (int)((double)n * base_sec / htf_sec) + 320;
   const int gh = XLoadRates(_Symbol, g_htf, need_h, g_hrates);
   g_htf_missing = (gh < 300);

   g_eng.SetBase(g_rates, n);
   g_eng.SetHTF(g_hrates, gh);
   if(StringLen(g_inter_sym) > 0)
   {
      const int gi = XLoadRates(g_inter_sym, (ENUM_TIMEFRAMES)_Period, n + 50, g_irates);
      if(gi > 100) g_eng.SetInter(g_irates, gi, g_inter_invert);
   }
   if(!g_eng.Compute()) return false;
   g_ready = true;

   FillBuffers(rates_total);
   g_eng.RunTrial(g_eng.cfg.warmup, n - 2, g_trial);
   g_eng.ForecastAudit(4, 1.0, g_eng.cfg.warmup, n - 2, g_fa_n, g_fa_hit);
   g_trial_days = (int)((g_eng.m_t[n - 1] - g_eng.m_t[g_eng.cfg.warmup]) / 86400);
   return true;
}

//+------------------------------------------------------------------+
void FillBuffers(const int rates_total)
{
   const int n = g_n;
   for(int idx = 0; idx < rates_total; idx++)
   {
      BufEma1[idx] = 0.0; BufEma2[idx] = 0.0; BufEma3[idx] = 0.0; BufVwap[idx] = 0.0;
      BufBuy[idx] = 0.0; BufSell[idx] = 0.0; BufBuyClr[idx] = 0.0; BufSellClr[idx] = 0.0;
      BufExitWin[idx] = 0.0; BufExitLoss[idx] = 0.0;
   }
   for(int k = g_eng.cfg.warmup; k < n; k++)
   {
      const int idx = g_start + k;
      BufEma1[idx] = g_eng.m_ema1[k];
      BufEma2[idx] = g_eng.m_ema2[k];
      BufEma3[idx] = g_eng.m_ema3[k];
      if(g_eng.m_daybars[k] >= 15) BufVwap[idx] = g_eng.m_vwap[k];
   }

   // walk the history one trade at a time (same rule as the trial and the EA)
   g_sig_i = -1;
   int busy = -1;
   XSignal s;
   XTradeResult r;
   for(int i = g_eng.cfg.warmup; i <= n - 2; i++)
   {
      if(i <= busy) continue;
      if(!g_eng.Evaluate(i, s)) continue;
      const int idx = g_start + i;
      const double a = g_eng.m_atr[i];
      if(s.dir > 0) { BufBuy[idx] = g_eng.m_l[i] - 0.7 * a;  BufBuyClr[idx] = (double)(s.grade - 1); }
      else          { BufSell[idx] = g_eng.m_h[i] + 0.7 * a; BufSellClr[idx] = (double)(s.grade - 1); }
      g_sig_i = i;
      g_sig = s;
      busy = i;
      if(g_eng.SimulateTrade(i, s.dir, s.sl, n - 2, r))
      {
         busy = r.closed ? r.exit_idx : n;
         if(r.closed && InpShowExits)
         {
            const int xi = g_start + r.exit_idx;
            if(r.r_net > 0.05) BufExitWin[xi] = g_eng.m_h[r.exit_idx] + 0.3 * a;
            else               BufExitLoss[xi] = g_eng.m_l[r.exit_idx] - 0.3 * a;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| live status of the newest trade + reason text                     |
//+------------------------------------------------------------------+
void RefreshLive()
{
   if(!g_ready) return;
   const int n = g_n;
   g_live_ok = false;
   g_opp_dir = 0;
   if(g_sig_i >= 0 && g_eng.SimulateTrade(g_sig_i, g_sig.dir, g_sig.sl, n - 1, g_live)) g_live_ok = true;

   XSignal t;
   g_eng.Evaluate(n - 2, t);
   g_reason = t.reason;
   if(t.dir != 0 && g_sig_i >= 0 && g_sig_i != n - 2 && g_live_ok && !g_live.closed && t.dir != g_sig.dir) g_opp_dir = t.dir;
}

//+------------------------------------------------------------------+
//| helpers for text                                                  |
//+------------------------------------------------------------------+
string Px(const double v) { return DoubleToString(v, _Digits); }

string DurText(const int bars)
{
   const int mins = bars * PeriodSeconds((ENUM_TIMEFRAMES)_Period) / 60;
   if(mins >= 120) return IntegerToString(mins / 60) + "h" + IntegerToString(mins % 60) + "m";
   return IntegerToString(mins) + "m";
}

string SessionName(const datetime t)
{
   const double h = XHourGmt(t, g_eng.cfg.gmt_offset_sec);
   if(h >= 0.0 && h < 7.0)   return "Asia";
   if(h >= 7.0 && h < 12.5)  return "London";
   if(h >= 12.5 && h < 16.0) return "London/NY overlap";
   if(h >= 16.0 && h < 21.0) return "New York";
   return "Rollover";
}

//+------------------------------------------------------------------+
//| projected candles + cone                                          |
//+------------------------------------------------------------------+
void DrawForecast()
{
   for(int j = 0; j < 40; j++)
   {
      XObjDelete("XO_FB" + IntegerToString(j));
      XObjDelete("XO_FW" + IntegerToString(j));
      XObjDelete("XO_FU" + IntegerToString(j));
      XObjDelete("XO_FD" + IntegerToString(j));
   }
   if(!InpShowForecast || !g_ready) return;
   const int n = g_n;
   const int period = g_eng.cfg.base_sec;
   const int steps = XMinI(XMaxI(InpForecastBars, 1), 30);
   g_eng.Forecast(n - 2, g_eng.m_c[n - 1], g_eng.m_t[n - 1] + period, steps);
   const bool up = (g_eng.fc_c[g_eng.fc_n - 1] >= g_eng.fc_o[0]);
   const color cu = XRGB(60, 190, 130), cd = XRGB(230, 90, 90);
   for(int j = 0; j < g_eng.fc_n; j++)
   {
      const string sj = IntegerToString(j);
      const bool bull = (g_eng.fc_c[j] >= g_eng.fc_o[j]);
      const color cl = bull ? cu : cd;
      const datetime t0 = g_eng.fc_t[j];
      XObjRect("XO_FB" + sj, t0 + (datetime)(period * 0.15), g_eng.fc_o[j], t0 + (datetime)(period * 0.85), g_eng.fc_c[j], cl, false);
      XObjTrend("XO_FW" + sj, t0 + (datetime)(period * 0.5), g_eng.fc_l[j], t0 + (datetime)(period * 0.5), g_eng.fc_h[j], cl, STYLE_SOLID, 1, false);
      if(InpShowCone && j + 1 < g_eng.fc_n)
      {
         const datetime t1 = g_eng.fc_t[j + 1];
         const color cc = up ? XRGB(70, 130, 110) : XRGB(140, 80, 80);
         XObjTrend("XO_FU" + sj, t0 + (datetime)(period * 0.5), g_eng.fc_up[j], t1 + (datetime)(period * 0.5), g_eng.fc_up[j + 1], cc, STYLE_DOT, 1, false);
         XObjTrend("XO_FD" + sj, t0 + (datetime)(period * 0.5), g_eng.fc_dn[j], t1 + (datetime)(period * 0.5), g_eng.fc_dn[j + 1], cc, STYLE_DOT, 1, false);
      }
   }
}

//+------------------------------------------------------------------+
//| trade plan lines                                                  |
//+------------------------------------------------------------------+
void DrawPlan()
{
   const string nm[7] = {"XO_PL_E", "XO_PL_S", "XO_PL_T1", "XO_PL_T2", "XO_PL_TR", "XO_PL_X", "XO_PL_TX"};
   for(int k = 0; k < 7; k++) XObjDelete(nm[k]);
   for(int k = 0; k < 5; k++) XObjDelete("XO_PL_L" + IntegerToString(k));
   if(!g_ready || g_sig_i < 0) return;
   const int n = g_n;
   const int period = g_eng.cfg.base_sec;

   bool show = false;
   if(g_sig_i == n - 2) show = true;                          // fresh setup
   else if(g_live_ok && !g_live.closed) show = true;          // trade still running
   if(!show) return;

   const datetime t0 = g_eng.m_t[g_sig_i + 1];
   const int maxh = g_eng.MaxHold();
   const datetime t_end = t0 + (datetime)(maxh * period);
   const datetime t_lbl = g_eng.m_t[n - 1] + (datetime)(period * 1);
   const bool buy = (g_sig.dir > 0);
   const double entry = g_sig.entry;
   const double risk = g_sig.risk;
   const double tp1 = entry + g_sig.dir * g_eng.cfg.tp1_r * risk;
   const double tp2 = entry + g_sig.dir * g_eng.cfg.tp2_r * risk;

   XObjTrend("XO_PL_E", t0, entry, t_end, entry, XRGB(230, 230, 240), STYLE_SOLID, 1, false);
   XObjTrend("XO_PL_S", t0, g_sig.sl, t_end, g_sig.sl, XRGB(255, 92, 92), STYLE_SOLID, 2, false);
   XObjTrend("XO_PL_T1", t0, tp1, t_end, tp1, XRGB(0, 222, 132), STYLE_DASH, 1, false);
   XObjTrend("XO_PL_T2", t0, tp2, t_end, tp2, XRGB(0, 180, 110), STYLE_DASH, 1, false);
   XObjVLine("XO_PL_X", t_end, XRGB(255, 200, 64));

   const string side = buy ? "BUY " : "SELL ";
   XObjText("XO_PL_L0", t_lbl, entry, side + XGradeName(g_sig.grade) + "  entry " + Px(entry), XRGB(230, 230, 240), 8);
   XObjText("XO_PL_L1", t_lbl, g_sig.sl, "STOP " + Px(g_sig.sl), XRGB(255, 92, 92), 8);
   XObjText("XO_PL_L2", t_lbl, tp1, "TP1 " + Px(tp1) + "  take " + DoubleToString(g_eng.cfg.partial_pct * 100.0, 0) + "%", XRGB(0, 222, 132), 8);
   XObjText("XO_PL_L3", t_lbl, tp2, "TP2 " + Px(tp2), XRGB(0, 180, 110), 8);
   XObjText("XO_PL_L4", t_end, entry, " time stop " + TimeToString(t_end, TIME_MINUTES), XRGB(255, 200, 64), 8);
   if(g_live_ok && !g_live.closed && g_live.stage == 1)
      XObjTrend("XO_PL_TR", t0, g_live.cur_sl, t_end, g_live.cur_sl, XRGB(255, 160, 40), STYLE_DASHDOT, 1, false);
}

//+------------------------------------------------------------------+
//| key levels                                                        |
//+------------------------------------------------------------------+
void DrawLevels()
{
   XObjDelete("XO_LV_PDH"); XObjDelete("XO_LV_PDL"); XObjDelete("XO_LV_ASIA");
   XObjDelete("XO_LV_T1"); XObjDelete("XO_LV_T2");
   if(!InpShowLevels || !g_ready) return;
   const int n = g_n;
   const int last = n - 1;
   const int period = g_eng.cfg.base_sec;
   const datetime t_right = g_eng.m_t[last] + (datetime)(period * 3);
   const int db = g_eng.m_daybars[last];
   const int d0 = XMaxI(0, last - db + 1);
   if(g_eng.m_pdh[last] > 0.0)
   {
      XObjTrend("XO_LV_PDH", g_eng.m_t[d0], g_eng.m_pdh[last], t_right, g_eng.m_pdh[last], XRGB(255, 160, 40), STYLE_DASH, 1, false);
      XObjTrend("XO_LV_PDL", g_eng.m_t[d0], g_eng.m_pdl[last], t_right, g_eng.m_pdl[last], XRGB(255, 160, 40), STYLE_DASH, 1, false);
      XObjText("XO_LV_T1", t_right, g_eng.m_pdh[last], " PDH", XRGB(255, 160, 40), 8);
      XObjText("XO_LV_T2", t_right, g_eng.m_pdl[last], " PDL", XRGB(255, 160, 40), 8);
   }
   if(g_eng.m_asiaok[last] == 1 && period <= 7200)
   {
      // find first bar of today's Asian window
      int k = last;
      while(k > 0 && g_eng.m_hour[k] >= g_eng.cfg.asia_end) k--;
      while(k > 0 && g_eng.m_hour[k - 1] < g_eng.m_hour[k] && g_eng.m_hour[k - 1] >= g_eng.cfg.asia_start) k--;
      XObjRect("XO_LV_ASIA", g_eng.m_t[k], g_eng.m_asialo[last], t_right, g_eng.m_asiahi[last], XRGB(90, 100, 140), false);
   }
}

//+------------------------------------------------------------------+
//| multi-timeframe strip                                             |
//+------------------------------------------------------------------+
void RefreshMTF()
{
   if(!InpShowMTF) return;
   const datetime now = TimeCurrent();
   if(g_mtf_time != 0 && now - g_mtf_time < 60) return;
   g_mtf_time = now;
   ENUM_TIMEFRAMES tfs[5];
   tfs[0] = PERIOD_M5; tfs[1] = PERIOD_M15; tfs[2] = PERIOD_H1; tfs[3] = PERIOD_H4; tfs[4] = PERIOD_D1;
   for(int k = 0; k < 5; k++)
   {
      double adx = 0.0;
      g_mtf_dir[k] = (double)XTrendState(_Symbol, tfs[k], adx);
      g_mtf_adx[k] = adx;
   }
}

string MtfChar(const double d) { return (d > 0.0) ? "UP" : ((d < 0.0) ? "DN" : "--"); }

//+------------------------------------------------------------------+
//| dashboard                                                         |
//+------------------------------------------------------------------+
void PutLine(const int row, const string text, const color clr, const int extra = 0)
{
   const int fs = InpFontSize + extra;
   const int lh = InpFontSize + 6;
   XObjLabel("XO_P_" + IntegerToString(row), InpPanelX + 10, InpPanelY + 8 + row * lh, text, clr, fs, "Consolas", CORNER_LEFT_UPPER);
}

void DrawPanel()
{
   if(!InpShowPanel || !g_ready)
   {
      ObjectsDeleteAll(0, "XO_P_");
      ObjectsDeleteAll(0, "XO_PB");
      return;
   }
   const int lh0 = InpFontSize + 6;
   // background first so it sits UNDER the text (objects draw in creation order)
   XObjRectLabel("XO_PB", InpPanelX, InpPanelY, 470 + (InpFontSize - 9) * 30, g_rows_prev * lh0 + 18,
                 XRGB(16, 20, 28), XRGB(58, 68, 88), CORNER_LEFT_UPPER);
   const int n = g_n;
   const datetime now = TimeCurrent();
   const double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   const double a = g_eng.m_atr[n - 2];
   const double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   const double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * pt;
   const double equity = (InpBalanceOverride > 0.0) ? InpBalanceOverride : AccountInfoDouble(ACCOUNT_EQUITY);
   const int tb = g_eng.m_bias[n - 1];

   int row = 0;
   PutLine(row++, "XAU ORACLE   " + _Symbol + " " + XTfName((ENUM_TIMEFRAMES)_Period) + " | bias TF " + XTfName(g_htf), CGold());

   // ---- status ----
   string status = "WAIT";
   color  sc = CDim();
   string sub = XReasonText(g_reason);
   const bool fresh = (g_sig_i == n - 2);
   const bool running = (g_live_ok && !g_live.closed && g_sig_i >= 0);
   if(g_news_blocked) { status = "AVOID - NEWS"; sc = CRed(); sub = g_news_block; }
   else if(fresh && g_live_ok)
   {
      const bool buy = (g_sig.dir > 0);
      const double dist = buy ? (bid - g_sig.entry) : (g_sig.entry - bid);
      if(dist > 0.35 * g_sig.atr) { status = "MISSED - do not chase"; sc = CGold(); sub = "price ran " + DoubleToString(dist, 2) + " past entry"; }
      else { status = (buy ? "BUY NOW  grade " : "SELL NOW  grade ") + XGradeName(g_sig.grade); sc = buy ? CGreen() : CRed(); sub = "enter at market, stop and targets below"; }
   }
   else if(running)
   {
      status = (g_sig.dir > 0) ? "IN BUY " : "IN SELL ";
      status += (g_live.stage == 1) ? "(half banked)" : "(hold)";
      sc = CCyan();
      sub = "float " + DoubleToString(g_live.float_r, 2) + "R  bar " + IntegerToString(g_live.bars) + "/" + IntegerToString(g_eng.MaxHold());
   }
   else if(g_live_ok && g_live.closed && g_live.exit_idx == n - 1 && g_sig_i >= 0)
   {
      status = "EXIT NOW";
      sc = CGold();
      if(g_live.exit_kind == XE_STOP)      sub = "stop level was hit";
      else if(g_live.exit_kind == XE_TRAIL) sub = "trailing/break-even stop hit";
      else if(g_live.exit_kind == XE_TP2)   sub = "runner target reached";
      else if(g_live.exit_kind == XE_TIME)  sub = "time stop - trade went nowhere";
      else                                  sub = "target reached";
   }
   else if(g_reason == XR_SESSION || g_reason == XR_FRIDAY || g_reason == XR_VOL_HIGH || g_reason == XR_VOL_LOW) sc = CGold();
   PutLine(row++, status, sc, 2);
   PutLine(row++, sub, CDim());
   if(g_opp_dir != 0) PutLine(row++, "!! opposite setup appeared - consider exiting", CRed());

   // ---- market snapshot ----
   PutLine(row++, "----------------------------------------", CDim());
   PutLine(row++, "Bias " + XTfName(g_htf) + ": " + (tb > 0 ? "BULL" : (tb < 0 ? "BEAR" : "NEUTRAL")) + "  ADX " + DoubleToString(g_eng.m_hadx[n - 1], 0)
                  + "   Session: " + SessionName(now), CText());
   PutLine(row++, "ATR " + DoubleToString(a, 2) + "  Spread " + DoubleToString(spread, 2) + "  Price " + Px(bid), CText());

   // ---- plan ----
   const bool plan = (fresh || running) && g_sig_i >= 0;
   if(plan)
   {
      PutLine(row++, "----------------------------------------", CDim());
      const double risk = g_sig.risk;
      const double tp1 = g_sig.entry + g_sig.dir * g_eng.cfg.tp1_r * risk;
      const double tp2 = g_sig.entry + g_sig.dir * g_eng.cfg.tp2_r * risk;
      PutLine(row++, "Entry " + Px(g_sig.entry) + "   Stop " + Px(g_sig.sl) + " (" + DoubleToString(risk, 2) + ")", CText());
      PutLine(row++, "TP1 " + Px(tp1) + " (" + DoubleToString(g_eng.cfg.tp1_r, 1) + "R)   TP2 " + Px(tp2) + " (" + DoubleToString(g_eng.cfg.tp2_r, 1) + "R)", CText());
      XLotPlan lp;
      double freeM = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if(InpBalanceOverride > 0.0) freeM = InpBalanceOverride;
      XPlanLots(_Symbol, equity, InpRiskPct, risk, g_sig.dir > 0, g_sig.entry, 1.5, 0.0, freeM, 0.5, lp);
      if(lp.ok)
         PutLine(row++, "Size " + DoubleToString(lp.lots, 2) + " lots | risk " + DoubleToString(lp.risk_pct, 2) + "% = " + DoubleToString(lp.risk_money, 2)
                        + " | margin " + DoubleToString(lp.margin, 0), CGreen());
      else
         PutLine(row++, "Size: " + lp.note, CRed());
      // hold-time guidance
      int tp1_bars = g_trial.all.nh_win >= 8 ? g_trial.all.HoldPct(true, 0.5) : 0;
      if(tp1_bars <= 0 && a > 0.0)
      {
         const double d = g_eng.cfg.tp1_r * risk / (0.63 * a);
         tp1_bars = XMaxI(1, (int)MathRound(d * d));
      }
      const datetime t_exit = g_eng.m_t[g_sig_i + 1] + (datetime)(g_eng.MaxHold() * g_eng.cfg.base_sec);
      PutLine(row++, "Typical TP1 in ~" + DurText(tp1_bars) + "  |  exit by " + TimeToString(t_exit, TIME_MINUTES), CText());
      if(running)
      {
         if(g_live.stage == 0) PutLine(row++, "Manage: hold. Take " + DoubleToString(g_eng.cfg.partial_pct * 100.0, 0) + "% at TP1, then stop to break-even.", CDim());
         else                  PutLine(row++, "Manage: stop now " + Px(g_live.cur_sl) + " (trails). Let the runner work.", CDim());
      }
   }

   // ---- confluence ----
   PutLine(row++, "----------------------------------------", CDim());
   {
      const int i = n - 2;
      string cl = "Votes:";
      for(int m = 0; m < XM_COUNT; m++)
      {
         const double v = g_eng.m_vote[i * XM_COUNT + m];
         cl += " " + XModuleShort(m) + (v > 0.0 ? "+" : (v < 0.0 ? "-" : "."));
      }
      PutLine(row++, cl, CText());
      PutLine(row++, "Score long " + DoubleToString(g_eng.m_scl[i], 1) + " / short " + DoubleToString(g_eng.m_scs[i], 1)
                     + "  (need " + DoubleToString(g_eng.cfg.score_min, 1) + ", " + IntegerToString(g_eng.cfg.min_confluence) + "+ modules)", CDim());
   }

   // ---- trial ----
   PutLine(row++, "----------------------------------------", CDim());
   PutLine(row++, "TRIAL on this chart: last " + IntegerToString(g_trial_days) + " days, one trade at a time", CGold());
   if(g_trial.all.n > 0)
   {
      PutLine(row++, "Trades " + IntegerToString(g_trial.all.n) + "  Win " + DoubleToString(g_trial.all.WinRate(), 0) + "%  TP1 hit "
                     + DoubleToString(g_trial.all.Tp1Rate(), 0) + "%  PF " + DoubleToString(g_trial.all.ProfitFactor(), 2)
                     + "  Exp " + DoubleToString(g_trial.all.Expectancy(), 2) + "R", g_trial.all.Expectancy() > 0.0 ? CGreen() : CRed());
      string gl = "By grade:";
      for(int g = 3; g >= 1; g--)
         gl += "  " + XGradeName(g) + " " + (g_trial.grade[g].n > 0 ? DoubleToString(g_trial.grade[g].WinRate(), 0) + "%" : "n/a") + "(" + IntegerToString(g_trial.grade[g].n) + ")";
      PutLine(row++, gl, CText());
      string ml = "Modules:";
      for(int m = 0; m < XM_COUNT; m++)
         ml += " " + XModuleShort(m) + (g_trial.mod[m].n >= 5 ? StringFormat("%+.2f", g_trial.mod[m].Expectancy()) : " n/a");
      PutLine(row++, ml, CDim());
   }
   else PutLine(row++, "no completed trades in loaded history yet", CDim());
   if(g_fa_n > 0)
      PutLine(row++, "Direction call +4 bars: " + DoubleToString(100.0 * g_fa_hit / g_fa_n, 1) + "% right (n=" + IntegerToString(g_fa_n) + ", 50% = coin flip)", CDim());

   // ---- mtf + news ----
   if(InpShowMTF)
   {
      PutLine(row++, "----------------------------------------", CDim());
      PutLine(row++, "Trend  M5 " + MtfChar(g_mtf_dir[0]) + "  M15 " + MtfChar(g_mtf_dir[1]) + "  H1 " + MtfChar(g_mtf_dir[2])
                     + "  H4 " + MtfChar(g_mtf_dir[3]) + "  D1 " + MtfChar(g_mtf_dir[4]), CText());
   }
   if(InpUseNews) PutLine(row++, "News: " + g_news_text, g_news_blocked ? CRed() : CDim());
   PutLine(row++, "Projection = statistical expectation, not a promise.", CDim());

   g_rows_prev = row;
   XObjRectLabel("XO_PB", InpPanelX, InpPanelY, 470 + (InpFontSize - 9) * 30, row * lh0 + 18, XRGB(16, 20, 28), XRGB(58, 68, 88), CORNER_LEFT_UPPER);
   // clear stale rows from a longer previous layout
   for(int k = row; k < row + 6; k++) XObjDelete("XO_P_" + IntegerToString(k));
}

//+------------------------------------------------------------------+
//| alerts                                                            |
//+------------------------------------------------------------------+
void MaybeAlert()
{
   if(!g_ready || g_sig_i != g_n - 2) return;
   const datetime bt = g_eng.m_t[g_n - 1];
   if(g_last_alert == bt) return;
   g_last_alert = bt;
   const string msg = "XAU Oracle " + _Symbol + " " + XTfName((ENUM_TIMEFRAMES)_Period) + ": " + (g_sig.dir > 0 ? "BUY " : "SELL ")
                      + XGradeName(g_sig.grade) + " entry " + Px(g_sig.entry) + " SL " + Px(g_sig.sl)
                      + " TP1 " + Px(g_sig.tp1) + " TP2 " + Px(g_sig.tp2);
   if(InpAlertPopup) Alert(msg);
   if(InpAlertSound) PlaySound("alert.wav");
   if(InpAlertPush)  SendNotification(msg);
   if(InpAlertEmail) SendMail("XAU Oracle signal", msg);
}

//+------------------------------------------------------------------+
void RefreshNews()
{
   if(!InpUseNews) { g_news_blocked = false; g_news_text = ""; return; }
   g_news.Refresh(TimeCurrent());
   g_news_blocked = g_news.Blocked(TimeCurrent(), g_news_block);
   g_news_text = g_news.NextText(TimeCurrent());
}

//+------------------------------------------------------------------+
void UpdateForming(const int rates_total, const double &high[], const double &low[], const double &close[])
{
   if(!g_ready) return;
   const int k = g_n - 1;
   g_eng.m_h[k] = high[rates_total - 1];
   g_eng.m_l[k] = low[rates_total - 1];
   g_eng.m_c[k] = close[rates_total - 1];
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
         RefreshMTF();
         RefreshLive();
         DrawPlan();
         DrawForecast();
         DrawLevels();
         DrawPanel();
         MaybeAlert();
         ChartRedraw(0);
      }
      g_last_ui = GetTickCount64();
      return rates_total;
   }
   if(!g_ready) return rates_total;

   // intrabar: keep the forming bar current and refresh at most once a second
   const ulong now_ms = GetTickCount64();
   if(now_ms - g_last_ui >= 1000)
   {
      g_last_ui = now_ms;
      UpdateForming(rates_total, high, low, close);
      RefreshLive();
      DrawPlan();
      DrawPanel();
      ChartRedraw(0);
   }
   return rates_total;
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_ready) return;
   RefreshNews();
   RefreshMTF();
   DrawPanel();
}
