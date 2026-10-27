//+------------------------------------------------------------------+
//| GoldTurtle55.mq5  v1.00  (indicator, places no orders)            |
//| "Turtle 55/20 breakout": the XAUUSD_Turtle_D1 EA's rules drawn on |
//| a D1 chart.                                                        |
//|  - Flat: buy when price reaches the highest high of the last 55   |
//|    closed days (blue dotted line).                                 |
//|  - Initial stop 2 x N below the entry (N = 20-day Wilder ATR),     |
//|    then raised to the lowest low of the last 20 closed days        |
//|    (orange dotted line), never lowered (red line).                 |
//|  - Exit when price touches the stop.                               |
//| Arrows: green = buy, red X = exit. Long only, like the EA.         |
//| Drawn from bid prices, no spread: real fills are a little worse.   |
//| Backtest (2004-2026, 0.01 lot): roughly ties holding gold, and is  |
//| not better than the GoldAllAgree + GoldAsiaBreak pair.             |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.00"
#property description "Turtle 55/20 breakout (XAUUSD_Turtle_D1 rules). Signals only, places no orders. D1 chart."
#property indicator_chart_window
#property indicator_buffers 5
#property indicator_plots   5
#property indicator_label1  "Entry level (55-day high)"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrDodgerBlue
#property indicator_style1  STYLE_DOT
#property indicator_label2  "Exit level (20-day low)"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrOrange
#property indicator_style2  STYLE_DOT
#property indicator_label3  "Stop"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrRed
#property indicator_width3  2
#property indicator_label4  "Buy"
#property indicator_type4   DRAW_ARROW
#property indicator_color4  clrLime
#property indicator_width4  2
#property indicator_label5  "Exit"
#property indicator_type5   DRAW_ARROW
#property indicator_color5  clrRed
#property indicator_width5  2

input int    EntryDays   = 55;    // breakout lookback (days)
input int    ExitDays    = 20;    // exit lookback (days)
input int    AtrDays     = 20;    // N period (Wilder)
input double StopN       = 2.0;   // initial stop in N
input bool   ShowPanel   = true;
input bool   AlertsOn    = true;  // pop-up alert on a new buy or exit
input bool   PushAlerts  = false; // also send to the MT5 phone app
input int    PanelX      = 10;    // panel distance from the right edge (px)
input int    PanelY      = 20;    // panel distance from the top (px)

double bHH[], bLL[], bStop[], bBuy[], bExit[], nArr[];
datetime alertedBuy=0, alertedExit=0;
string PFX;

int OnInit(){
   if(_Period!=PERIOD_D1){ Alert("GoldTurtle: attach to a D1 chart (the rules use daily bars)."); return INIT_PARAMETERS_INCORRECT; }
   PFX="GT"+IntegerToString(EntryDays)+"_"+IntegerToString(ExitDays)+"_";
   SetIndexBuffer(0,bHH,INDICATOR_DATA); SetIndexBuffer(1,bLL,INDICATOR_DATA); SetIndexBuffer(2,bStop,INDICATOR_DATA);
   SetIndexBuffer(3,bBuy,INDICATOR_DATA); SetIndexBuffer(4,bExit,INDICATOR_DATA);
   for(int p=0;p<5;p++) PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetInteger(3,PLOT_ARROW,233); PlotIndexSetInteger(3,PLOT_ARROW_SHIFT,15);
   PlotIndexSetInteger(4,PLOT_ARROW,251); PlotIndexSetInteger(4,PLOT_ARROW_SHIFT,-15);
   PlotIndexSetString(0,PLOT_LABEL,"Entry level ("+IntegerToString(EntryDays)+"-day high)");
   PlotIndexSetString(1,PLOT_LABEL,"Exit level ("+IntegerToString(ExitDays)+"-day low)");
   IndicatorSetString(INDICATOR_SHORTNAME,"GoldTurtle "+IntegerToString(EntryDays)+"/"+IntegerToString(ExitDays));
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
string P(double x){ return DoubleToString(x,_Digits); }
string D(datetime t){ return TimeToString(t,TIME_DATE); }

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[]){
   int start=MathMax(EntryDays,ExitDays)+1;
   if(rates_total<=start+AtrDays) return 0;
   ArrayResize(nArr,rates_total);
   // N = Wilder ATR through each closed bar (EA: alpha = 1/AtrDays)
   double N=high[0]-low[0]; nArr[0]=N;
   for(int i=1;i<rates_total;i++){
      double tr=MathMax(high[i]-low[i],MathMax(MathAbs(high[i]-close[i-1]),MathAbs(low[i]-close[i-1])));
      N+=(tr-N)/AtrDays; nArr[i]=N;
   }
   ArrayInitialize(bHH,EMPTY_VALUE); ArrayInitialize(bLL,EMPTY_VALUE); ArrayInitialize(bStop,EMPTY_VALUE);
   ArrayInitialize(bBuy,EMPTY_VALUE); ArrayInitialize(bExit,EMPTY_VALUE);

   bool pos=false; double stop=0, entry=0; datetime entryT=0, lastExitT=0; double lastExitPx=0, lastEntryPx=0;
   int lastEvent=0; // 1 buy, 2 exit
   int lastEventBar=-1;
   double hh=0, ll=0;
   for(int i=start;i<rates_total;i++){
      hh=high[i-1]; for(int k=i-EntryDays;k<i-1;k++) hh=MathMax(hh,high[k]);
      ll=low[i-1];  for(int k=i-ExitDays;k<i-1;k++)  ll=MathMin(ll,low[k]);
      bHH[i]=hh; bLL[i]=ll;
      if(pos){
         stop=MathMax(stop,ll);
         bStop[i]=stop;
         if(low[i]<=stop){
            pos=false; lastExitPx=MathMin(open[i],stop); lastExitT=time[i];
            bExit[i]=high[i]; lastEvent=2; lastEventBar=i;
         }
         continue;   // the EA places its next buy stop the following day
      }
      if(high[i]>=hh){
         entry=MathMax(open[i],hh); entryT=time[i]; lastEntryPx=entry;
         stop=MathMax(entry-StopN*nArr[i-1],ll);
         pos=true; bBuy[i]=low[i]; bStop[i]=stop; lastEvent=1; lastEventBar=i;
      }
   }
   int cur=rates_total-1;
   string tag="GoldTurtle "+IntegerToString(EntryDays)+"/"+IntegerToString(ExitDays)+" "+_Symbol;
   if(lastEventBar==cur){
      if(lastEvent==1 && alertedBuy!=time[cur]){ alertedBuy=time[cur]; Say(tag+": BUY, price reached the "+IntegerToString(EntryDays)+"-day high "+P(hh)+", stop "+P(stop)); }
      if(lastEvent==2 && alertedExit!=time[cur]){ alertedExit=time[cur]; Say(tag+": EXIT, stop "+P(lastExitPx)+" touched"); }
   }
   if(ShowPanel){
      double bid=close[cur];
      Line(0,tag,clrSilver);
      if(pos){
         Line(1,"LONG since "+D(entryT)+" at "+P(entry),clrLime);
         Line(2,"Stop "+P(stop)+"  ($"+DoubleToString(bid-stop,2)+" below price, per 0.01 lot)",clrRed);
         Line(3,"Open result per 0.01 lot: $"+DoubleToString(bid-entry,2),bid>=entry?clrLime:clrTomato);
      } else {
         Line(1,"FLAT. Buy level today "+P(hh)+"  ($"+DoubleToString(hh-bid,2)+" above price)",clrDodgerBlue);
         Line(2,"Stop if bought now: "+P(MathMax(hh-StopN*nArr[cur-1],ll))+"  (risk $"+DoubleToString(MathMin(StopN*nArr[cur-1],hh-ll),2)+" per 0.01 lot)",clrOrange);
         Line(3,lastExitT>0?"Last exit "+D(lastExitT)+" at "+P(lastExitPx)+", trade $"+DoubleToString(lastExitPx-lastEntryPx,2)+" per 0.01 lot":"No trades yet",clrSilver);
      }
      Line(4,"Tested 2004-2026: about the same as holding gold; not better than the pair.",clrGray);
   }
   return rates_total;
}
//+------------------------------------------------------------------+
