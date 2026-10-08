//+------------------------------------------------------------------+
//|                                                XAU_Platform.mqh  |
//|  MetaTrader 5 glue shared by XAU_Oracle (indicator) and          |
//|  XAU_Sniper_EA: data loading, symbol/lot maths, economic news    |
//|  filter and chart-drawing helpers.                               |
//+------------------------------------------------------------------+
#ifndef XAU_PLATFORM_MQH
#define XAU_PLATFORM_MQH

#include "XAU_Core.mqh"

#ifdef __MQL5__
   #define XSARR(name)      string name[]
   #define XRATESARR(name)  MqlRates name[]
   #define XRATESOUT(name)  MqlRates &name[]
   #define XCALARR(name)    MqlCalendarValue name[]
#endif

//+------------------------------------------------------------------+
//| timeframes                                                       |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES XAutoHTF(const ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1:  case PERIOD_M2:  case PERIOD_M3:  case PERIOD_M4:                    return PERIOD_M15;
      case PERIOD_M5:  case PERIOD_M6:  case PERIOD_M10: case PERIOD_M12:                   return PERIOD_H1;
      case PERIOD_M15: case PERIOD_M20:                                                     return PERIOD_H1;
      case PERIOD_M30:                                                                      return PERIOD_H4;
      case PERIOD_H1:  case PERIOD_H2:  case PERIOD_H3:                                     return PERIOD_H4;
      case PERIOD_H4:  case PERIOD_H6:  case PERIOD_H8:  case PERIOD_H12:                   return PERIOD_D1;
      case PERIOD_D1:                                                                       return PERIOD_W1;
      default: break;
   }
   return PERIOD_MN1;
}

string XTfName(const ENUM_TIMEFRAMES tf)
{
   return StringSubstr(EnumToString(tf), 7);
}

//+------------------------------------------------------------------+
//| data                                                             |
//+------------------------------------------------------------------+
// user-facing strategy / exit choices (AUTO = let the Strategy Lab choose on this chart's own history)
enum ENUM_XAU_STRAT
{
   XAU_ST_AUTO       = -1,  // AUTO: the strategy that passed the Strategy Lab
   XAU_ST_CONFLUENCE = 0,   // Confluence of 9 modules
   XAU_ST_ORB        = 1,   // Opening-range breakout (GOLD_ORB)
   XAU_ST_DIP        = 2,   // RSI-2 dip in trend
   XAU_ST_DOUBLE7    = 3,   // Double-7 dip in trend
   XAU_ST_IBS        = 4,   // Weak-close dip in trend
   XAU_ST_SWEEP      = 5,   // Stop-hunt reversal
   XAU_ST_PULLBACK   = 6,   // EMA pullback
   XAU_ST_SQUEEZE    = 7    // Squeeze breakout
};

enum ENUM_XAU_EXIT
{
   XAU_EX_AUTO    = -1,     // AUTO: chosen together with the strategy
   XAU_EX_CLASSIC = 0,      // Classic: half at 1R, runner to 2.5R
   XAU_EX_HIGHHIT = 1,      // High-hit: 70% at 0.5R, runner to 1.5R
   XAU_EX_QUICK   = 2,      // Quick: all out at 0.6R
   XAU_EX_MEANREV = 3,      // Mean-revert: exit on the close back over the 5-bar mean
   XAU_EX_RIDER   = 4,      // Trend rider: a third at 1R, the rest trails 3 ATR for up to 5 days
   XAU_EX_SWING   = 5       // Swing: the classic exit held up to 3 days
};

// Resolve the user's choice against the lab. Returns the cell (strategy * XP_COUNT + exit) or -1.
int XResolveCell(const CXauEngine &le, const int user_s, const int user_p, const int min_trades, bool &proven)
{
   proven = false;
   if(user_s < 0 && user_p < 0) return le.LabActiveCell(min_trades, proven);
   int best = -1;
   double sc = -1e9;
   for(int c = 0; c < XLAB_CELLS; c++)
   {
      const int st = c / XP_COUNT, pr = c % XP_COUNT;
      if(user_s >= 0 && st != user_s) continue;
      if(user_p >= 0 && pr != user_p) continue;
      const double v = le.lab[c].score + (le.lab[c].qualified ? 1000.0 : 0.0);
      if(le.lab[c].all.n >= 1 && v > sc) { sc = v; best = c; }
   }
   if(best < 0) best = XMaxI(user_s, 0) * XP_COUNT + XMaxI(user_p, 0);
   proven = le.lab[best].qualified;
   return best;
}

// Overnight swap of this symbol as a COST per unit (1 oz for gold) per night, in price units (positive = you pay).
// MT5 reports swap in several modes; the common ones are converted, the rest fall back to 0 with a log line.
double XSwapCostPerUnit(const string sym, const bool is_buy)
{
   const double sw = SymbolInfoDouble(sym, is_buy ? SYMBOL_SWAP_LONG : SYMBOL_SWAP_SHORT);   // MT5: negative = charged
   const long mode = SymbolInfoInteger(sym, SYMBOL_SWAP_MODE);
   const double contract = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   const double price = SymbolInfoDouble(sym, SYMBOL_BID);
   double per_unit = 0.0;
   if(mode == SYMBOL_SWAP_MODE_POINTS) per_unit = sw * SymbolInfoDouble(sym, SYMBOL_POINT);
   else if(mode == SYMBOL_SWAP_MODE_CURRENCY_SYMBOL || mode == SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT ||
           mode == SYMBOL_SWAP_MODE_CURRENCY_MARGIN || mode == SYMBOL_SWAP_MODE_CURRENCY_PROFIT)
      per_unit = (contract > 0.0) ? sw / contract : 0.0;                      // money per lot -> per unit (USD accounts)
   else if(mode == SYMBOL_SWAP_MODE_INTEREST_CURRENT || mode == SYMBOL_SWAP_MODE_INTEREST_OPEN)
      per_unit = price * sw / 100.0 / 360.0;                                  // annual percent of the price
   return -per_unit;
}

// How the tools choose and trade (round 10, docs/REAL_DATA.md section 10).
//   STEADY: one strategy, the Lab's best with at least 60% winners (high win-rate, about break-even on real gold)
//   TREND : every strategy that passes a 50% Lab target trades, each its own position (up to a cap), multi-day
//           exits allowed, H1 and above buy only in a daily uptrend. On real H1/H4 history: about +0.1R per trade.
enum ENUM_XAU_MODE
{
   XAU_MODE_AUTO   = -1,   // AUTO: TREND on H1 and H4, STEADY elsewhere
   XAU_MODE_STEADY = 0,    // STEADY: one strategy, 60%+ winners
   XAU_MODE_TREND  = 1     // TREND: all passing strategies, trend-riding exits
};

int XResolveMode(const int input_mode, const ENUM_TIMEFRAMES tf)
{
   if(input_mode >= 0) return input_mode;
   const int ps = PeriodSeconds(tf);
   return (ps == 3600 || ps == 14400) ? XAU_MODE_TREND : XAU_MODE_STEADY;
}

// "Today's plan" in one line for both panels: trade or stand aside, which direction, and today's expected range
// (CXauEngine::DayRangeForecast) against what the day has already made. go = true when the tools may trade today.
string XTodayPlan(const int mode, const int npass, const bool proven, const bool too_small, const int d1_mode, const int dreg,
                  const double day_fc, const double day_sofar, bool &go)
{
   go = false;
   string s = "TODAY: ";
   if(too_small)                       s += "watch only - trades on this chart are too big for the account";
   else if(d1_mode == 2 && dreg < 0)   s += "stand aside - daily trend is down and this chart only buys";
   else if((mode == XAU_MODE_TREND && npass == 0 && !proven) || (mode != XAU_MODE_TREND && !proven))
                                       s += "stand aside - no strategy passed the Lab here";
   else
   {
      go = true;
      string side = "both directions";
      if(d1_mode == 2) side = "buys only";
      else if(d1_mode == 1 && dreg > 0) side = "buys only (daily trend up)";
      else if(d1_mode == 1 && dreg < 0) side = "sells only (daily trend down)";
      s += "wait for a signal, " + side;
      if(mode == XAU_MODE_TREND && npass > 0) s += ", " + IntegerToString(npass) + " strateg" + (npass > 1 ? "ies" : "y") + " armed";
   }
   if(day_fc > 0.0)
   {
      s += ". Today's range: about " + DoubleToString(day_fc, 0) + " expected, " + DoubleToString(day_sofar, 0) + " so far";
      if(day_sofar >= 0.9 * day_fc) s += ": most of today's move is done";
   }
   return s;
}

// One row that says which entry checks pass right now, so "why is it not trading?" is answered at a glance.
string XCheckRow(const bool lab, const bool trend, const bool news, const bool spread, const bool margin, const bool size, const bool limits)
{
   const string ok = "ok", no = "NO";
   string s = "Checks: Lab ";
   s += lab ? ok : no;
   s += ", Trend ";  s += trend ? ok : no;
   s += ", News ";   s += news ? ok : no;
   s += ", Spread "; s += spread ? ok : no;
   s += ", Margin "; s += margin ? ok : no;
   s += ", Size ";   s += size ? ok : no;
   s += ", Limits "; s += limits ? ok : no;
   return s;
}

// Chance (0-1) that the next `trades` trades at `risk_pct` per trade dig a drawdown of `dd_pct` or more from the
// running peak, when trades win with probability win_p (average win avg_win_r R, average loss avg_loss_r R) and
// otherwise scratch at 0. Monte Carlo with a fixed-seed generator, so the same inputs always give the same answer.
double XDrawdownChance(const double win_p, const double loss_p, const double avg_win_r, const double avg_loss_r,
                       const double risk_pct, const int trades, const double dd_pct, const int paths)
{
   if(paths <= 0 || trades <= 0 || risk_pct <= 0.0) return 0.0;
   uint seed = 2463534242;
   int hit = 0;
   const double r = risk_pct / 100.0, lim = 1.0 - dd_pct / 100.0;
   for(int p = 0; p < paths; p++)
   {
      double eq = 1.0, peak = 1.0;
      for(int t = 0; t < trades; t++)
      {
         seed ^= (seed << 13); seed ^= (seed >> 17); seed ^= (seed << 5);
         const double u = (double)(seed % 1000000) / 1000000.0;
         if(u < win_p) eq *= 1.0 + r * avg_win_r;
         else if(u < win_p + loss_p) eq *= 1.0 - r * avg_loss_r;
         if(eq > peak) peak = eq;
         if(eq <= peak * lim) { hit++; break; }
      }
   }
   return (double)hit / paths;
}

// Live results that fall below what the Lab tested by more than bad luck explains (2 standard errors, 30+ trades)
// usually mean the broker's fills or spread differ from the test. Returns a warning, or "" when all is normal.
string XLiveDrift(const int live_n, const int live_wins, const double tested_win_pct)
{
   if(live_n < 30 || tested_win_pct <= 0.0) return "";
   const double p = tested_win_pct / 100.0;
   const double live = (double)live_wins / live_n;
   const double se = MathSqrt(p * (1.0 - p) / live_n);
   if(live >= p - 2.0 * se) return "";
   return "Live win-rate " + DoubleToString(100.0 * live, 0) + "% is below the tested " + DoubleToString(tested_win_pct, 0) +
          "% by more than luck explains: check spread and fills, or pause";
}

// Session clock for the panel: where the day is and what comes next (London local time; server midnight = daily break).
string XSessionLine(const XConfig &c, const datetime server_now)
{
   const int off = XOffsetAt(c, server_now);
   const long gmt = (long)server_now - off;
   const int lon_off = XEuDst(gmt) ? 3600 : 0;
   const long lon = gmt + lon_off;
   const int m = (int)((lon % 86400) / 60);                       // London minutes after midnight
   const int dow = (int)(((lon / 86400) + 4) % 7);
   if(dow == 6 || (dow == 0 && m < 23 * 60) || (dow == 5 && m >= 22 * 60)) return "Market closed for the weekend";
   string now_s = "Asia";
   if(m >= 8 * 60 && m < 13 * 60 + 30) now_s = "London";
   else if(m >= 13 * 60 + 30 && m < 16 * 60 + 30) now_s = "London + New York (busiest)";
   else if(m >= 16 * 60 + 30 && m < 22 * 60) now_s = "New York";
   else if(m >= 22 * 60 && m < 23 * 60) now_s = "daily break / thin";
   const int ev_min[4] = {8 * 60, 13 * 60 + 30, 14 * 60 + 30, 22 * 60};
   const string ev_nm[4] = {"London opens", "US data time", "New York opens", "daily break"};
   int best = -1, best_d = 100000;
   for(int k = 0; k < 4; k++)
   {
      int d = ev_min[k] - m;
      if(d <= 0) d += 1440;
      if(d < best_d) { best_d = d; best = k; }
   }
   string nxt = "";
   if(best >= 0) nxt = ev_nm[best] + " in " + IntegerToString(best_d / 60) + "h" + StringFormat("%02d", best_d % 60);
   return "Session: " + now_s + "   next: " + nxt;
}

// Daily trend filter (research/sim/drift.cpp, docs/REAL_DATA.md section 8). The daily trend is the last completed
// daily close above / below its 200-day mean.
enum ENUM_XAU_D1
{
   XAU_D1_AUTO = -1,   // AUTO: H1 and above buy only while the daily trend is up; M5-M30 unfiltered
   XAU_D1_OFF  = 0,    // off
   XAU_D1_WITH = 1,    // trade only in the daily trend's direction
   XAU_D1_LONG = 2     // buy only, and only while the daily trend is up
};

int XResolveD1Mode(const int input_mode, const ENUM_TIMEFRAMES tf)
{
   if(input_mode >= 0) return input_mode;
   return (PeriodSeconds(tf) >= 3600) ? XAU_D1_LONG : XAU_D1_OFF;
}

// Strategy Lab window: 0 = automatic (H1: 25,000 bars, about 4 years; everything else 10,000 bars).
int XResolveHistoryBars(const int input_bars, const ENUM_TIMEFRAMES tf)
{
   if(input_bars > 0) return input_bars;
   return (PeriodSeconds(tf) == 3600) ? 25000 : 10000;
}

// Daily bars needed to know the daily trend over `base_bars` bars of timeframe tf (plus the 200-day mean).
// What "the daily trend is up" means (round 11, docs/REAL_DATA.md section 11)
enum ENUM_XAU_D1DEF
{
   XAU_D1DEF_RISING = 1,   // close above its 200-day mean AND that mean rising (default since round 11)
   XAU_D1DEF_ABOVE  = 0,   // close above its 200-day mean (round 8-10)
   XAU_D1DEF_MOM12  = 2,   // close above the close of 12 months ago
   XAU_D1DEF_BOTH   = 3    // above the 200-day mean and above 12 months ago
};

// daily bars the chosen definition needs before it can say anything
int XDailyMinBars(const int d1_def)
{
   if(d1_def == XAU_D1DEF_RISING) return 225;
   if(d1_def == XAU_D1DEF_MOM12 || d1_def == XAU_D1DEF_BOTH) return 260;
   return 210;
}

int XDailyBarsNeeded(const int base_bars, const ENUM_TIMEFRAMES tf)
{
   return (int)((double)base_bars * PeriodSeconds(tf) / 86400.0 * 1.45) + 260;
}

enum ENUM_XAU_DST
{
   XAU_DST_FIXED = 0,   // server clock never changes
   XAU_DST_US    = 1,   // server follows US daylight time (typical "New York close" servers: GMT+2 / GMT+3)
   XAU_DST_EU    = 2    // server follows EU daylight time
};

// Server-time minus GMT in WINTER (standard) time, in seconds. With manual = true the value is the one you typed.
// Automatic: measure today's offset and, if the server is currently on summer time, remove the extra hour.
int XWinterOffsetSec(const bool manual, const double manual_hours, const int dst_mode)
{
   if(manual) return (int)MathRound(manual_hours * 3600.0);
   const double d = (double)(TimeTradeServer() - TimeGMT());
   int cur = (int)(MathRound(d / 1800.0) * 1800.0);
   const long g = (long)TimeGMT();
   if(dst_mode == XAU_DST_US && XUsDst(g)) cur -= 3600;
   if(dst_mode == XAU_DST_EU && XEuDst(g)) cur -= 3600;
   return cur;
}

// Loads the most recent `count` bars, oldest first (index count-1 = forming bar).
int XLoadRates(const string sym, const ENUM_TIMEFRAMES tf, const int count, XRATESOUT(out))
{
   ArraySetAsSeries(out, false);
   const int got = CopyRates(sym, tf, 0, count, out);
   return (got > 0) ? got : 0;
}

// Trend direction (+1/-1/0) and ADX on the last CLOSED bar of another timeframe.
int XTrendState(const string sym, const ENUM_TIMEFRAMES tf, double &adx_out)
{
   XRATESARR(r);
   adx_out = 0.0;
   const int got = XLoadRates(sym, tf, 450, r);
   if(got < 260) return 0;
   XDARR(c); XDARR(h); XDARR(l); XDARR(e50); XDARR(e200); XDARR(pdi); XDARR(mdi); XDARR(adx);
   ArrayResize(c, got); ArrayResize(h, got); ArrayResize(l, got);
   ArrayResize(e50, got); ArrayResize(e200, got); ArrayResize(pdi, got); ArrayResize(mdi, got); ArrayResize(adx, got);
   for(int i = 0; i < got; i++) { c[i] = r[i].close; h[i] = r[i].high; l[i] = r[i].low; }
   XCalcEMA(c, e50, got, 50);
   XCalcEMA(c, e200, got, 200);
   XCalcADX(h, l, c, pdi, mdi, adx, got, 14);
   const int k = got - 2;
   adx_out = adx[k];
   if(e50[k] > e200[k] && c[k] > e50[k]) return 1;
   if(e50[k] < e200[k] && c[k] < e50[k]) return -1;
   return 0;
}

// DXY-like symbol (gold moves against it) or EURUSD fallback (gold moves with it).
string XResolveInterSymbol(const string user_symbol, bool &invert)
{
   invert = false;
   if(StringLen(user_symbol) > 0)
   {
      invert = (StringFind(user_symbol, "EUR") < 0 && StringFind(user_symbol, "GBP") < 0 && StringFind(user_symbol, "AUD") < 0);
      if(SymbolSelect(user_symbol, true)) return user_symbol;
      return "";
   }
   string cand[5];
   cand[0] = "USDX"; cand[1] = "DXY"; cand[2] = "DX"; cand[3] = "USDIDX"; cand[4] = "DXY.cash";
   for(int i = 0; i < 5; i++)
      if(SymbolSelect(cand[i], true)) { invert = true; return cand[i]; }
   if(SymbolSelect("EURUSD", true)) { invert = false; return "EURUSD"; }
   return "";
}

//+------------------------------------------------------------------+
//| lot sizing                                                       |
//+------------------------------------------------------------------+
struct XLotPlan
{
   bool   ok;
   double lots;
   double risk_money;        // money lost if the stop is hit at `lots`
   double risk_pct;          // of the supplied equity
   double margin;
   double min_lot_risk_pct;  // what the smallest tradable lot would risk
   string note;
   string src_note;          // set when the broker's tick value was found to be wrong
};

double XTickValueLoss(const string sym)
{
   double v = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(v <= 0.0) v = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   return v;
}

// Money lost by ONE lot if the stop (sl_dist away from price) is hit, in account currency.
// Some brokers report the XAUUSD tick value 10x too small, which would make every position 10x too big.
// The broker's own profit formula (OrderCalcProfit) is therefore the source of truth; the tick value and
// the contract size are only fallbacks. `note` explains when the sources disagreed.
double XLossPerLot(const string sym, const bool is_buy, const double price, const double sl_dist, string &note)
{
   note = "";
   if(sl_dist <= 0.0 || price <= 0.0) return 0.0;
   const ENUM_ORDER_TYPE ot = is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   const double sl = is_buy ? price - sl_dist : price + sl_dist;
   double prof = 0.0, by_profit = 0.0;
   if(OrderCalcProfit(ot, sym, 1.0, price, sl, prof) && prof < 0.0) by_profit = -prof;
   const double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   const double tv = XTickValueLoss(sym);
   const double by_tick = (ts > 0.0 && tv > 0.0) ? sl_dist / ts * tv : 0.0;
   double by_contract = 0.0;
   if(SymbolInfoString(sym, SYMBOL_CURRENCY_PROFIT) == AccountInfoString(ACCOUNT_CURRENCY))
      by_contract = sl_dist * SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   if(by_profit > 0.0)
   {
      if(by_tick > 0.0 && MathAbs(by_tick - by_profit) > 0.2 * by_profit)
         note = "broker tick value is off by x" + DoubleToString(by_profit / by_tick, 1) + "; using the broker's profit formula";
      return by_profit;
   }
   if(by_contract > 0.0)
   {
      if(by_tick > 0.0 && MathAbs(by_tick - by_contract) > 0.2 * by_contract) note = "tick value disagrees with contract size; using contract size";
      return by_contract;
   }
   return by_tick;
}

// Sizes a trade so that hitting the stop costs `risk_pct` of equity. Never rounds UP past
// the requested risk; if even the minimum lot risks more than overrun_factor x the request,
// the trade is refused (ok=false) instead of silently over-risking a small account.
void XPlanLots(const string sym, const double equity, const double risk_pct, const double sl_dist,
               const bool is_buy, const double price, const double overrun_factor,
               const double lot_cap, const double free_margin, const double margin_use_frac,
               XLotPlan &p)
{
   p.ok = false; p.lots = 0.0; p.risk_money = 0.0; p.risk_pct = 0.0; p.margin = 0.0;
   p.min_lot_risk_pct = 0.0; p.note = ""; p.src_note = "";
   const double vmin  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   const double vmax  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   const double vstep = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   string src_note = "";
   const double loss_per_lot = XLossPerLot(sym, is_buy, price, sl_dist, src_note);
   p.src_note = src_note;
   if(equity <= 0.0 || sl_dist <= 0.0 || loss_per_lot <= 0.0 || vstep <= 0.0)
   {
      p.note = "symbol data unavailable";
      return;
   }
   const double risk_money = equity * risk_pct / 100.0;
   double lots = XNormLotsDown(risk_money / loss_per_lot, vmin, vmax, vstep);
   p.min_lot_risk_pct = 100.0 * vmin * loss_per_lot / equity;
   if(lots <= 0.0)
   {
      if(vmin * loss_per_lot <= risk_money * overrun_factor) lots = vmin;
      else
      {
         p.note = "account too small: min lot would risk " + DoubleToString(p.min_lot_risk_pct, 1) + "%";
         return;
      }
   }
   if(lot_cap > 0.0 && lots > lot_cap) lots = XNormLotsDown(lot_cap, vmin, vmax, vstep);
   if(lots <= 0.0) { p.note = "lot cap below minimum lot"; return; }

   double margin = 0.0;
   const ENUM_ORDER_TYPE ot = is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(free_margin <= 0.0)
   {
      // report the size anyway (the indicator shows it), but it cannot be opened
      p.lots = lots; p.risk_money = lots * loss_per_lot; p.risk_pct = 100.0 * p.risk_money / equity;
      p.note = "no free margin left: open trades are using all of it";
      return;
   }
   if(OrderCalcMargin(ot, sym, lots, price, margin) && margin > 0.0)
   {
      const double allowed = free_margin * margin_use_frac;
      if(margin > allowed)
      {
         const double lots_before = lots;
         lots = XNormLotsDown(lots * allowed / margin, vmin, vmax, vstep);
         if(lots <= 0.0) { p.note = "not enough free margin"; return; }
         double margin2 = 0.0;
         if(OrderCalcMargin(ot, sym, lots, price, margin2) && margin2 > 0.0) margin = margin2;
         else margin = margin * lots / lots_before;   // recalculation failed: scale the earlier figure proportionally
      }
   }
   p.lots = lots;
   p.margin = margin;
   p.risk_money = lots * loss_per_lot;
   p.risk_pct = 100.0 * p.risk_money / equity;
   p.ok = true;
}

//+------------------------------------------------------------------+
//| economic calendar filter                                         |
//+------------------------------------------------------------------+
class CXauNews
{
private:
   XTARR(m_t);
   XSARR(m_name);
   XIARR(m_imp);
   int      m_n;
   datetime m_last;
   bool     m_cal_ok;
public:
   int    before_min;
   int    after_min;
   int    min_importance;    // 1 low, 2 medium, 3 high
   bool   fallback_static;   // when the calendar is unavailable (e.g. Strategy Tester)
   int    gmt_offset_sec;
   string currency;

   CXauNews()
   {
      m_n = 0; m_last = 0; m_cal_ok = false;
      before_min = 30; after_min = 30; min_importance = 3;
      fallback_static = true; gmt_offset_sec = 0; currency = "USD";
   }
   bool CalendarAvailable() const { return m_cal_ok; }

   void Refresh(const datetime now)
   {
      if(m_last != 0 && now - m_last < 900 && now >= m_last) return;
      m_last = now;
      m_n = 0;
      m_cal_ok = false;
      XCALARR(vals);
      ResetLastError();
      if(!CalendarValueHistory(vals, now - 3 * 3600, now + 3 * 86400, NULL, currency)) return;
      const int got = ArraySize(vals);
      if(got <= 0) return;
      m_cal_ok = true;
      ArrayResize(m_t, got); ArrayResize(m_name, got); ArrayResize(m_imp, got);
      for(int i = 0; i < got; i++)
      {
         MqlCalendarEvent ev;
         if(!CalendarEventById(vals[i].event_id, ev)) continue;
         const int imp = (int)ev.importance;
         if(imp < min_importance) continue;
         m_t[m_n] = vals[i].time;
         m_name[m_n] = ev.name;
         m_imp[m_n] = imp;
         m_n++;
      }
   }

   // true when trading should pause; `why` explains
   bool Blocked(const datetime now, string &why) const
   {
      why = "";
      for(int i = 0; i < m_n; i++)
      {
         if(now >= m_t[i] - before_min * 60 && now <= m_t[i] + after_min * 60)
         {
            why = m_name[i] + " " + TimeToString(m_t[i], TIME_MINUTES);
            return true;
         }
      }
      if(!m_cal_ok && fallback_static)
      {
         // US data prints at 08:30 ET = 12:30 or 13:30 GMT. Without a calendar, stay out of both.
         const double hr = XHourGmt(now, gmt_offset_sec);
         const int wd = XWeekdayGmt(now, gmt_offset_sec);
         if(wd >= 1 && wd <= 5)
         {
            if((hr >= 12.25 && hr <= 12.75) || (hr >= 13.25 && hr <= 13.75))
            {
               why = "US data window (static)";
               return true;
            }
         }
      }
      return false;
   }

   // e.g. "NFP in 42m" for the panel; empty when nothing is near
   string NextText(const datetime now) const
   {
      datetime best = 0; int bi = -1;
      for(int i = 0; i < m_n; i++)
         if(m_t[i] >= now - after_min * 60 && (bi < 0 || m_t[i] < best)) { best = m_t[i]; bi = i; }
      if(bi < 0) return m_cal_ok ? "no high-impact USD news soon" : "calendar unavailable";
      const long mins = ((long)best - (long)now) / 60;
      string nm = m_name[bi];
      if(StringLen(nm) > 22) nm = StringSubstr(nm, 0, 22);
      if(mins >= 0) return nm + " in " + IntegerToString(mins) + "m";
      return nm + " " + IntegerToString(-mins) + "m ago";
   }
};

//+------------------------------------------------------------------+
//| drawing helpers                                                  |
//+------------------------------------------------------------------+
color XRGB(const int r, const int g, const int b)
{
   return (color)((b << 16) | (g << 8) | r);
}

void XObjLabel(const string name, const int x, const int y, const string text, const color clr,
               const int fsize, const string font, const ENUM_BASE_CORNER corner)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetString(0, name, OBJPROP_FONT, font);
   }
   ObjectSetInteger(0, name, OBJPROP_CORNER, corner);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fsize);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
}

void XObjRectLabel(const string name, const int x, const int y, const int w, const int h,
                   const color bg, const color border, const ENUM_BASE_CORNER corner)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   }
   ObjectSetInteger(0, name, OBJPROP_CORNER, corner);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, name, OBJPROP_COLOR, border);
}

void XObjTrend(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
               const color clr, const ENUM_LINE_STYLE style, const int width, const bool ray_right)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
   }
   else
   {
      ObjectMove(0, name, 0, t1, p1);
      ObjectMove(0, name, 1, t2, p2);
   }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, ray_right);
}

void XObjRect(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
              const color clr, const bool fill)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
   }
   else
   {
      ObjectMove(0, name, 0, t1, p1);
      ObjectMove(0, name, 1, t2, p2);
   }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FILL, fill);
}

void XObjText(const string name, const datetime t, const double p, const string text, const color clr, const int fsize)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
   }
   else ObjectMove(0, name, 0, t, p);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fsize);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
}

void XObjVLine(const string name, const datetime t, const color clr)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_VLINE, 0, t, 0.0);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
   }
   else ObjectMove(0, name, 0, t, 0.0);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
}

void XObjDelete(const string name)
{
   if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
}

//+------------------------------------------------------------------+
//| panel: lines are collected, then drawn in a box that fits them   |
//+------------------------------------------------------------------+
enum ENUM_XAU_PANEL_POS
{
   XAU_PANEL_TOP_LEFT    = 0,   // top left
   XAU_PANEL_BOTTOM_LEFT = 1,   // bottom left
   XAU_PANEL_TOP_RIGHT   = 2,   // top right (left of the price scale)
   XAU_PANEL_BOTTOM_RIGHT = 3   // bottom right
};

int XTextWidth(const string text, const string font, const int size)
{
   uint w = 0, h = 0;
   if(TextSetFont(font, -size * 10, 0, 0) && TextGetSize(text, w, h) && w > 0) return (int)w;
   return (int)(StringLen(text) * size * 0.8);
}

class CXPanel
{
private:
   string m_text[48];
   color  m_clr[48];
   int    m_extra[48];
   int    m_rows, m_drawn;
public:
   string prefix;
   string font;
   int    x, y, fs, min_w;
   ENUM_XAU_PANEL_POS pos;
   color  bg, border;

   CXPanel() { m_rows = 0; m_drawn = 0; prefix = "XP_"; font = "Consolas"; x = 12; y = 24; fs = 10; min_w = 300;
               pos = XAU_PANEL_TOP_LEFT; bg = XRGB(16, 20, 28); border = XRGB(58, 68, 88); }
   void Begin() { m_rows = 0; }
   // MT5 cuts a text label after 63 characters, so longer lines are wrapped at a space
   void Line(const string text, const color clr, const int extra = 0)
   {
      string rest = text;
      bool first = true;
      while(m_rows < 48)
      {
         string part = rest;
         const int lim = first ? 62 : 60;
         if(StringLen(rest) > lim)
         {
            int cut = lim;
            while(cut > 20 && StringGetCharacter(rest, cut) != ' ') cut--;
            if(cut <= 20) cut = lim;
            part = StringSubstr(rest, 0, cut);
            rest = StringSubstr(rest, cut);
            while(StringLen(rest) > 0 && StringGetCharacter(rest, 0) == ' ') rest = StringSubstr(rest, 1);
         }
         else rest = "";
         m_text[m_rows] = first ? part : "  " + part;
         m_clr[m_rows] = clr; m_extra[m_rows] = extra; m_rows++;
         first = false;
         if(StringLen(rest) == 0) break;
      }
   }
   int Rows() const { return m_rows; }
   string Text(const int k) const { return (k >= 0 && k < m_rows) ? m_text[k] : ""; }
   // measured size of the collected lines
   void Measure(int &w, int &h) const
   {
      w = min_w; h = 16;
      for(int k = 0; k < m_rows; k++)
      {
         const int fsz = fs + m_extra[k];
         const int tw = XTextWidth(m_text[k], font, fsz) + 24;
         if(tw > w) w = tw;
         h += fsz + 8;
      }
   }
   void End()
   {
      int w, h;
      Measure(w, h);
      const int ch = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS);
      const int cw = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
      int top = y, left = x;
      if(pos == XAU_PANEL_BOTTOM_LEFT) top = XMaxI(4, ch - h - y);
      if(pos == XAU_PANEL_TOP_RIGHT || pos == XAU_PANEL_BOTTOM_RIGHT) left = XMaxI(4, cw - w - x - 70);
      if(pos == XAU_PANEL_BOTTOM_RIGHT) top = XMaxI(4, ch - h - y - 20);
      XObjRectLabel(prefix + "BG", left, top, w, h, bg, border, CORNER_LEFT_UPPER);
      int py = top + 8;
      for(int k = 0; k < m_rows; k++)
      {
         const int fsz = fs + m_extra[k];
         XObjLabel(prefix + IntegerToString(k), left + 12, py, m_text[k], m_clr[k], fsz, font, CORNER_LEFT_UPPER);
         py += fsz + 8;
      }
      for(int k = m_rows; k < m_drawn; k++) XObjDelete(prefix + IntegerToString(k));
      m_drawn = m_rows;
   }
   void Clear()
   {
      for(int k = 0; k < 48; k++) XObjDelete(prefix + IntegerToString(k));
      XObjDelete(prefix + "BG");
      m_drawn = 0;
   }
};

//+------------------------------------------------------------------+
//| account health: things that can blow an account up               |
//+------------------------------------------------------------------+
string XAccountWarning(const string sym)
{
   int naked = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != sym) continue;
      if(PositionGetDouble(POSITION_SL) <= 0.0) naked++;
   }
   string w = "";
   if(naked > 0) w = IntegerToString(naked) + " open trade" + (naked > 1 ? "s have" : " has") + " NO stop loss";
   const double ml = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   if(ml > 0.0 && ml < 200.0)
   {
      string so = "";
      if(AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE) == ACCOUNT_STOPOUT_MODE_PERCENT)
         so = " (broker closes trades at " + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_SO_SO), 0) + "%)";
      if(StringLen(w) > 0) w += "; ";
      w += "margin level " + DoubleToString(ml, 0) + "%" + so;
   }
   return w;
}

//+------------------------------------------------------------------+
//| daily Strategy Lab on a fixed data window                         |
//| Both the indicator and the EA run the lab on exactly the same     |
//| bars (N closed bars ending before today's server midnight), so    |
//| they always choose the same strategy on the same day.             |
//+------------------------------------------------------------------+
datetime XServerDayStart(const datetime t)
{
   return t - (t % 86400);
}

bool XRunDailyLab(CXauEngine &le, const string sym, const ENUM_TIMEFRAMES tf, const ENUM_TIMEFRAMES htf,
                  const int bars, const string inter_sym, const bool inter_invert,
                  const double win_target, const int min_trades, const int folds, const datetime day_start)
{
   XRATESARR(b);
   XRATESARR(h);
   XRATESARR(x);
   ArraySetAsSeries(b, false);
   ArraySetAsSeries(h, false);
   ArraySetAsSeries(x, false);
   const datetime upto = day_start - 1;
   const int gb = CopyRates(sym, tf, upto, bars, b);
   if(gb < 600) return false;
   const int need_h = (int)((double)gb * PeriodSeconds(tf) / PeriodSeconds(htf)) + 320;
   const int gh = CopyRates(sym, htf, upto, need_h, h);
   if(gh < 300) return false;
   le.SetBase(b, gb);
   le.SetHTF(h, gh);
   XRATESARR(d);
   ArraySetAsSeries(d, false);
   int gd = 0;
   if(le.cfg.d1_mode > 0)
   {
      gd = CopyRates(sym, PERIOD_D1, upto, XDailyBarsNeeded(gb, tf), d);
      if(gd < XDailyMinBars(le.cfg.d1_def)) return false;   // daily history still loading: retry, never test the filter blind
   }
   le.SetDaily(d, gd);
   if(StringLen(inter_sym) > 0)
   {
      const int gx = CopyRates(inter_sym, tf, upto, gb + 50, x);
      if(gx > 100) le.SetInter(x, gx, inter_invert);
   }
   if(!le.Compute()) return false;
   le.RunLab(le.cfg.warmup, le.n - 1, win_target, min_trades, folds);
   return true;
}

#endif // XAU_PLATFORM_MQH
