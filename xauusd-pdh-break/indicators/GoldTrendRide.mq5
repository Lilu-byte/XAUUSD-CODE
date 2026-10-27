//+------------------------------------------------------------------+
//| GoldTrendRide.mq5  v1.00  (indicator, places no orders)           |
//| "Hourly trend ride": the XAUUSD_EWMAC_H1 EA's rules drawn on an   |
//| H1 chart.                                                          |
//|  raw   = (EMA16 - EMA64 of close) / EW std-dev(100) of hourly     |
//|          close-to-close changes                                    |
//|  score = raw / 2.11, kept between 0 and 2                          |
//|  units = round(score x 2)  -> 0..4 units of UnitLots               |
//| The EA changes its position at the next hour's open whenever the  |
//| units change. Arrows: green up = add units, orange down = cut     |
//| units, red X = back to flat. Lines: EMA16 (aqua), EMA64 (gold).   |
//| Long only, no stop loss, like the EA.                              |
//| Backtest: made most of its money in 2025; fell $1,570 at 0-4 units |
//| from Jan to Aug 2026 and lost money in 5 of 11 years. Not a       |
//| replacement for the GoldAllAgree + GoldAsiaBreak pair.            |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.00"
#property description "Hourly trend ride (XAUUSD_EWMAC_H1 rules). Signals only, places no orders. H1 chart."
#property indicator_chart_window
#property indicator_buffers 5
#property indicator_plots   5
#property indicator_label1  "EMA fast"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrAqua
#property indicator_label2  "EMA slow"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrGold
#property indicator_width2  2
#property indicator_label3  "Add units"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  clrLime
#property indicator_width3  2
#property indicator_label4  "Cut units"
#property indicator_type4   DRAW_ARROW
#property indicator_color4  clrOrange
#property indicator_width4  2
#property indicator_label5  "Flat"
#property indicator_type5   DRAW_ARROW
#property indicator_color5  clrRed
#property indicator_width5  2

input double UnitLots    = 0.01;  // lots per unit (for the panel only)
input int    FastSpan    = 16;
input int    SlowSpan    = 64;
input int    VolSpan     = 100;
input double Divisor     = 2.11;
input double Cap         = 2.0;   // 2.0 = up to 4 units; 0.5 = 0 or 1 unit
input int    WarmupBars  = 1000;  // no arrows before this many bars (the averages need history)
input bool   ShowPanel   = true;
input bool   AlertsOn    = true;  // pop-up alert when the units change
input bool   PushAlerts  = false;
input int    PanelX      = 10;
input int    PanelY      = 20;

double bF[], bS[], bUp[], bDn[], bFlat[], tgt[], fc[];
datetime alerted=0;
string PFX="GTR_";

int OnInit(){
   if(_Period!=PERIOD_H1){ Alert("GoldTrendRide: attach to an H1 chart (the rules use hourly closes)."); return INIT_PARAMETERS_INCORRECT; }
   SetIndexBuffer(0,bF,INDICATOR_DATA); SetIndexBuffer(1,bS,INDICATOR_DATA);
   SetIndexBuffer(2,bUp,INDICATOR_DATA); SetIndexBuffer(3,bDn,INDICATOR_DATA); SetIndexBuffer(4,bFlat,INDICATOR_DATA);
   for(int p=0;p<5;p++) PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetInteger(2,PLOT_ARROW,233); PlotIndexSetInteger(2,PLOT_ARROW_SHIFT,15);
   PlotIndexSetInteger(3,PLOT_ARROW,234); PlotIndexSetInteger(3,PLOT_ARROW_SHIFT,-15);
   PlotIndexSetInteger(4,PLOT_ARROW,251); PlotIndexSetInteger(4,PLOT_ARROW_SHIFT,-15);
   PlotIndexSetString(0,PLOT_LABEL,"EMA"+IntegerToString(FastSpan));
   PlotIndexSetString(1,PLOT_LABEL,"EMA"+IntegerToString(SlowSpan));
   IndicatorSetString(INDICATOR_SHORTNAME,"GoldTrendRide");
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ ObjectsDeleteAll(0,PFX); }

void Say(string s){ if(!AlertsOn) return; Alert(s); if(PushAlerts) SendNotification(s); }
void Line(int k,string txt,color c){
   string n=PFX+IntegerToString(k);
   if(ObjectFind(0,n)<0){
      ObjectCreate(0,n,OBJ_LABEL,0,0,0);
      ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_RIGHT_UPPER); ObjectSetInteger(0,n,OBJPROP_ANCHOR,ANCHOR_RIGHT_UPPER);
      ObjectSetInteger(0,n,OBJPROP_XDISTANCE,PanelX); ObjectSetInteger(0,n,OBJPROP_YDISTANCE,PanelY+k*16);
      ObjectSetInteger(0,n,OBJPROP_FONTSIZE,9); ObjectSetString(0,n,OBJPROP_FONT,"Arial");
      ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,n,OBJPROP_HIDDEN,true);
   }
   ObjectSetString(0,n,OBJPROP_TEXT,txt); ObjectSetInteger(0,n,OBJPROP_COLOR,c);
}
string L(int u){ return DoubleToString(u*UnitLots,2); }

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[]){
   if(rates_total<WarmupBars+2) return 0;
   static datetime lastBar=0;
   bool newBar=(time[rates_total-1]!=lastBar);
   if(!newBar && prev_calculated>0) return rates_total;   // the rules only use closed hours
   lastBar=time[rates_total-1];

   ArrayResize(tgt,rates_total); ArrayResize(fc,rates_total);
   ArrayInitialize(bUp,EMPTY_VALUE); ArrayInitialize(bDn,EMPTY_VALUE); ArrayInitialize(bFlat,EMPTY_VALUE);
   double af=2.0/(FastSpan+1), as=2.0/(SlowSpan+1), av=2.0/(VolSpan+1);
   double ef=close[0], es=close[0], m=0, v=0;
   bF[0]=ef; bS[0]=es; tgt[0]=0; fc[0]=0;
   for(int i=1;i<rates_total;i++){
      ef+=af*(close[i]-ef); es+=as*(close[i]-es);
      double d=close[i]-close[i-1], dm=d-m; m+=av*dm; v=(1-av)*(v+av*dm*dm);   // same EW mean/variance as the EA
      bF[i]=ef; bS[i]=es;
      double sd=MathSqrt(v);
      double f=(sd>0)? MathMax(0.0,MathMin(Cap,(ef-es)/sd/Divisor)) : 0;
      fc[i]=f; tgt[i]=MathRound(f*2.0);
   }
   // position: decided on the close of bar j-1, changed at the open of bar j
   int cur=0, lastChangeBar=-1, prevUnits=0;
   for(int j=WarmupBars;j<rates_total;j++){
      int t=(int)tgt[j-1];
      if(t==cur) continue;
      if(t==0) bFlat[j]=high[j]; else if(t>cur) bUp[j]=low[j]; else bDn[j]=high[j];
      prevUnits=cur; cur=t; lastChangeBar=j;
   }
   int last=rates_total-1;
   if(lastChangeBar==last && alerted!=time[last]){
      alerted=time[last];
      Say(StringFormat("GoldTrendRide %s: units %d -> %d (%s -> %s lots), score %.2f. %s at this hour's open.",
          _Symbol,prevUnits,cur,L(prevUnits),L(cur),fc[last-1],cur>prevUnits?"BUY "+L(cur-prevUnits):"SELL "+L(prevUnits-cur)));
   }
   if(ShowPanel){
      Line(0,"GoldTrendRide "+_Symbol+"  (EMA"+IntegerToString(FastSpan)+"/EMA"+IntegerToString(SlowSpan)+")",clrSilver);
      Line(1,StringFormat("Hold now: %d units = %s lots   (score %.2f of %.1f)",cur,L(cur),fc[last-1],Cap),cur>0?clrLime:clrSilver);
      if(lastChangeBar>=0) Line(2,"Last change "+TimeToString(time[lastChangeBar],TIME_DATE|TIME_MINUTES)+": "+IntegerToString(prevUnits)+" -> "+IntegerToString(cur)+" units",clrSilver);
      string nxt="";
      if((cur+0.5)/2.0<=Cap) nxt+=StringFormat("adds a unit at an hourly close with score >= %.2f",(cur+0.5)/2.0);
      if(cur>0) nxt+=(nxt==""?"":", ")+StringFormat("cuts one below %.2f",(cur-0.5)/2.0);
      Line(3,"Next: "+nxt,clrSilver);
      Line(4,"Tested: no stop; fell $1,570 Jan-Aug 2026 at 0-4 units. Not better than the pair.",clrGray);
   }
   return rates_total;
}
//+------------------------------------------------------------------+
