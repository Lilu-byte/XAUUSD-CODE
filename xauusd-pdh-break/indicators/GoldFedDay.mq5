//+------------------------------------------------------------------+
//| GoldFedDay.mq5  v1.00  (indicator, places no orders)              |
//| "Fed-day follow": the XAUUSD_FOMC_Follow EA's rules drawn on an   |
//| H1 chart.                                                          |
//|  - On a Fed (FOMC) statement day, watch the 14:00-15:00 New York  |
//|    hour. Closed up = buy, closed down = sell, flat = no trade.    |
//|  - Enter at the 15:00 New York open.                               |
//|  - Stop: that hour's low - (spread + $0.10) for a buy, its high + |
//|    (spread + $0.10) for a sell.                                    |
//|  - At each hourly close the stop trails to close -/+ 2 x ATR(14), |
//|    only ever tightening.                                           |
//|  - Out at 18:00 New York.                                          |
//| Arrows: green up = buy, red down = sell, X = exit; red line = stop.|
//| ServerMinusNY: hours your server clock is ahead of New York. It is |
//| 7 for David's broker all year (its day opens 01:00 = 18:00 NY).   |
//| Backtest 2016-2026: 80 trades, about $12 a year per 0.01 lot.     |
//| Break-even; not better than the pair or holding gold.             |
//+------------------------------------------------------------------+
#property copyright "Trading Agent project"
#property version   "1.00"
#property description "Fed-day follow (XAUUSD_FOMC_Follow rules). Signals only, places no orders. H1 chart."
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots   4
#property indicator_label1  "Fed-day buy"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrLime
#property indicator_width1  2
#property indicator_label2  "Fed-day sell"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrRed
#property indicator_width2  2
#property indicator_label3  "Exit"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  clrYellow
#property indicator_width3  2
#property indicator_label4  "Stop"
#property indicator_type4   DRAW_LINE
#property indicator_color4  clrRed
#property indicator_width4  2

input int    ServerMinusNY  = 7;      // server time minus New York time, hours
input double TrailATR       = 2.0;
input int    AtrPeriod      = 14;
input int    ExitHourNY     = 18;
input double SpreadUSD      = 0.30;   // spread used for the stop on past days
input double BufferUSD      = 0.10;
input string ExtraFomcDates = "";     // more statement days, YYYYMMDD,YYYYMMDD
input bool   ShowPanel      = true;
input bool   AlertsOn       = true;
input bool   PushAlerts     = false;
input int    PanelX         = 10;
input int    PanelY         = 20;

string FOMC_BUILTIN="20160127,20160316,20160427,20160615,20160727,20160921,20161102,20161214,20170201,20170315,20170503,20170614,20170726,20170920,20171101,20171213,20180131,20180321,20180502,20180613,20180801,20180926,20181108,20181219,20190130,20190320,20190501,20190619,20190731,20190918,20191030,20191211,20200129,20200429,20200610,20200729,20200916,20201105,20201216,20210127,20210317,20210428,20210616,20210728,20210922,20211103,20211215,20220126,20220316,20220504,20220615,20220727,20220921,20221102,20221214,20230201,20230322,20230503,20230614,20230726,20230920,20231101,20231213,20240131,20240320,20240501,20240612,20240731,20240918,20241107,20241218,20250129,20250319,20250507,20250618,20250730,20250917,20251029,20251210,20260128,20260318,20260429,20260617,20260729,20260916,20261028,20261209";

double bBuy[], bSell[], bExit[], bStop[];
datetime alertedIn=0, alertedOut=0;
string PFX="GFD_";

int OnInit(){
   if(_Period!=PERIOD_H1){ Alert("GoldFedDay: attach to an H1 chart (the rules use hourly bars)."); return INIT_PARAMETERS_INCORRECT; }
   SetIndexBuffer(0,bBuy,INDICATOR_DATA); SetIndexBuffer(1,bSell,INDICATOR_DATA);
   SetIndexBuffer(2,bExit,INDICATOR_DATA); SetIndexBuffer(3,bStop,INDICATOR_DATA);
   for(int p=0;p<4;p++) PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetInteger(0,PLOT_ARROW,233); PlotIndexSetInteger(0,PLOT_ARROW_SHIFT,15);
   PlotIndexSetInteger(1,PLOT_ARROW,234); PlotIndexSetInteger(1,PLOT_ARROW_SHIFT,-15);
   PlotIndexSetInteger(2,PLOT_ARROW,251); PlotIndexSetInteger(2,PLOT_ARROW_SHIFT,-15);
   IndicatorSetString(INDICATOR_SHORTNAME,"GoldFedDay");
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
string Key(datetime ny){ MqlDateTime t; TimeToStruct(ny,t); return StringFormat("%04d%02d%02d",t.year,t.mon,t.day); }
bool IsFomc(datetime ny){ string k=Key(ny); return StringFind(FOMC_BUILTIN,k)>=0 || StringFind(ExtraFomcDates,k)>=0; }
datetime DayStart(datetime t){ return (datetime)((long)t-((long)t%86400)); }

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[]){
   if(rates_total<AtrPeriod+20) return 0;
   ArrayInitialize(bBuy,EMPTY_VALUE); ArrayInitialize(bSell,EMPTY_VALUE);
   ArrayInitialize(bExit,EMPTY_VALUE); ArrayInitialize(bStop,EMPTY_VALUE);
   int off=ServerMinusNY*3600;
   int last=rates_total-1;
   int inTrade=0; double tEntry=0, tStop=0; datetime tWhen=0;      // a trade still open on the last bar
   int lastDir=0; double lastPnl=0; datetime lastDay=0; string lastNote="";
   for(int k=AtrPeriod+3;k<last;k++){
      datetime ny=time[k]-off;
      if((int)(((long)ny%86400)/3600)!=14 || !IsFomc(ny)) continue;
      if(time[k+1]!=time[k]+3600) continue;                         // EA: the 14:00 NY bar must be the one just before
      lastDay=DayStart(ny);
      if(close[k]==open[k]){ lastDir=0; lastNote="14:00 hour closed flat, no trade"; continue; }
      int dir=close[k]>open[k]?1:-1;
      int i=k+1;
      double ent=open[i];                                          // bid at the 15:00 NY open
      double sl=dir==1? low[k]-(SpreadUSD+BufferUSD) : high[k]+SpreadUSD+BufferUSD;
      if(dir==1? sl>=ent : sl<=ent){ lastDir=0; lastNote="price already beyond the stop, no trade"; continue; }
      if(dir==1) bBuy[i]=low[i]; else bSell[i]=high[i];
      datetime exitAt=lastDay+ExitHourNY*3600;
      double px=0; int j=i; bool done=false;
      for(;j<rates_total;j++){
         datetime nyj=time[j]-off;
         if(nyj>=exitAt){ px=open[j]; done=true; break; }
         if(j>i){
            double atr=0;
            for(int q=j-2;q>j-2-AtrPeriod;q--) atr+=MathMax(high[q]-low[q],MathMax(MathAbs(high[q]-close[q-1]),MathAbs(low[q]-close[q-1])));
            atr/=AtrPeriod;
            double want=dir==1? close[j-1]-TrailATR*atr : close[j-1]+TrailATR*atr;
            if(dir==1? want>sl : want<sl){
               if(dir==1? want>=open[j] : want<=open[j]+SpreadUSD){ px=open[j]; done=true; bStop[j]=want; break; }
               sl=want;
            }
         }
         bStop[j]=sl;
         if(dir==1 && low[j]<=sl){ px=MathMin(open[j],sl); done=true; break; }
         if(dir==-1 && high[j]+SpreadUSD>=sl){ px=MathMax(open[j],sl-SpreadUSD); done=true; break; }
      }
      if(done){
         bExit[j]=high[j];
         lastDir=dir; lastPnl=(px-ent)*dir; lastNote="";
         if(j==last && alertedOut!=time[last]){ alertedOut=time[last]; Say("GoldFedDay "+_Symbol+": EXIT the Fed-day "+(dir==1?"buy":"sell")+" now"); }
         k=j;
      } else {
         inTrade=dir; tEntry=ent; tStop=sl; tWhen=time[i]; lastDir=dir;
         k=j;
      }
      if(i==last && alertedIn!=time[last]){
         alertedIn=time[last];
         Say(StringFormat("GoldFedDay %s: Fed-day %s at ~%s, stop %s, trail %.1f x ATR, out at %d:00 New York",
             _Symbol,dir==1?"BUY":"SELL",P(ent),P(sl),TrailATR,ExitHourNY));
      }
   }
   if(ShowPanel){
      Line(0,"GoldFedDay "+_Symbol+"  (server = New York + "+IntegerToString(ServerMinusNY)+"h)",clrSilver);
      if(inTrade!=0) Line(1,(inTrade==1?"IN A BUY":"IN A SELL")+string(" since ")+TimeToString(tWhen,TIME_DATE|TIME_MINUTES)+" at "+P(tEntry)+", stop "+P(tStop),inTrade==1?clrLime:clrTomato);
      else if(lastDay>0) Line(1,"Last Fed day "+TimeToString(lastDay,TIME_DATE)+": "+(lastNote!=""?lastNote:(lastDir==1?"buy":"sell")+string(", $")+DoubleToString(lastPnl,2)+" per 0.01 lot before costs"),clrSilver);
      else Line(1,"No Fed day in the loaded history",clrSilver);
      // next statement day after the server's current New York date
      datetime nowNY=TimeCurrent()-off; string today=Key(nowNY), next="";
      string all=FOMC_BUILTIN+(ExtraFomcDates==""?"":","+ExtraFomcDates); string parts[];
      int n=StringSplit(all,',',parts);
      for(int p=0;p<n;p++){ string s=parts[p]; StringTrimLeft(s); StringTrimRight(s); if(StringLen(s)==8 && s>=today && (next=="" || s<next)) next=s; }
      Line(2,next==""?"No future Fed day in the list: add dates in ExtraFomcDates":"Next Fed day: "+StringSubstr(next,0,4)+"-"+StringSubstr(next,4,2)+"-"+StringSubstr(next,6,2)+" (signal after the 14:00 NY hour)",clrSilver);
      Line(3,"Tested 2016-2026: break-even. Not better than the pair.",clrGray);
   }
   return rates_total;
}
//+------------------------------------------------------------------+
