//+------------------------------------------------------------------+
//| MONKE_XAU_LITE.mq5  v18.10  (pair: MONKE_XAU_LITE_EA, magic 880025)|
//| Eyes. One word, Bank / Leave, one optional arrow. Map + gates,     |
//| not a crystal ball. Any gold chart, any timeframe. Direction = H4. |
#property strict
#property version "18.10"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2
#property indicator_label1  "GO LONG"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrGold
#property indicator_width1  2
#property indicator_label2  "GO SHORT"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrGold
#property indicator_width2  2
input group "=== Look ==="
input bool InpArrow=true;   // one gold arrow on the signal candle while GO is live
double Ab[],As[];
//--- SHARED GATES: this block is identical in the indicator and the EA ---
#define VER "18.10"
input group "=== Gates (keep identical in indicator and EA) ==="
input int    InpMinHold=6, InpRangeBars=20, InpMaxSpread=80, InpNewsMins=12;   // news = +/- LBMA 10:30 and 15:00 London
input int    InpSessStart=7, InpSessEnd=21, InpFriNoNew=16, InpFriFlat=19;       // GMT hours
input double InpBankMult=0.70, InpSellLoc=0.45, InpBuyLoc=0.55, InpMaxADR=0.90, InpHaltMoney=15.0, InpHaltPct=8.0;  // halt = REALIZED only
int hF4,hS4,hFc,hSc,H4Dir=0,MapDir=0; bool BarOk=false; MqlRates R[];

bool IsGold() { string s=_Symbol; StringToUpper(s); return StringFind(s,"XAU")>=0||StringFind(s,"GOLD")>=0; }
bool InitH()
  {
   ENUM_TIMEFRAMES b=(PeriodSeconds()<=3600)?PERIOD_H4:PERIOD_D1;   // direction TF
   hF4=iMA(_Symbol,b,20,0,MODE_EMA,PRICE_CLOSE); hS4=iMA(_Symbol,b,50,0,MODE_EMA,PRICE_CLOSE);
   hFc=iMA(_Symbol,_Period,20,0,MODE_EMA,PRICE_CLOSE); hSc=iMA(_Symbol,_Period,50,0,MODE_EMA,PRICE_CLOSE);
   ArraySetAsSeries(R,true);
   return hF4!=INVALID_HANDLE&&hS4!=INVALID_HANDLE&&hFc!=INVALID_HANDLE&&hSc!=INVALID_HANDLE;
  }
void Rel() { IndicatorRelease(hF4); IndicatorRelease(hS4); IndicatorRelease(hFc); IndicatorRelease(hSc); }
bool Ind(int h,double &v) { double b[1]; if(CopyBuffer(h,0,1,1,b)!=1) return false; v=b[0]; return true; }
bool Eval()   // last CLOSED bars only. false = data not ready
  {
   double f4,s4,fc,sc; int n=InpRangeBars+2;
   if(!Ind(hF4,f4)||!Ind(hS4,s4)||!Ind(hFc,fc)||!Ind(hSc,sc)||CopyRates(_Symbol,_Period,0,n,R)<n) return false;
   double e=_Point*10,rg=R[1].high-R[1].low,loc=(rg>0)?(R[1].close-R[1].low)/rg:0.5;
   int c=(R[1].close>R[1].open)?1:((R[1].close<R[1].open)?-1:0),ch=(fc>sc)?1:((fc<sc)?-1:0);
   H4Dir=(f4-s4>e)?1:((s4-f4>e)?-1:0);
   BarOk=(H4Dir!=0&&rg>0&&c==H4Dir&&(H4Dir<0?loc<=InpSellLoc:loc>=InpBuyLoc));
   MapDir=(ch==H4Dir&&c==H4Dir)?H4Dir:0;
   return true;
  }
datetime LastSun(int y,int m)   // 01:00 UTC on the last Sunday of month m (31-day months)
  { MqlDateTime t; ZeroMemory(t); t.year=y; t.mon=m; t.day=31; t.hour=1; datetime d=StructToTime(t); TimeToStruct(d,t); return (datetime)(d-t.day_of_week*86400); }
double ADRUsed()
  {
   static datetime lt=0; static double v=0; MqlRates d[];
   if(TimeCurrent()-lt<30) return v;
   lt=TimeCurrent(); v=0; ArraySetAsSeries(d,true);
   if(CopyRates(_Symbol,PERIOD_D1,0,15,d)!=15) return 0;
   double s=0; for(int i=1;i<=14;i++) s+=d[i].high-d[i].low;
   s/=14; if(s>0) v=(d[0].high-d[0].low)/s;
   return v;
  }
double Realized()   // today's closed P/L on this symbol. Floating never counts.
  {
   static datetime lt=0; static double v=0; datetime now=TimeCurrent();
   if(now-lt<15) return v;
   lt=now; v=0;
   if(!HistorySelect((datetime)((long)now-(long)now%86400),now)) return 0;
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong k=HistoryDealGetTicket(i); if(k==0||HistoryDealGetString(k,DEAL_SYMBOL)!=_Symbol) continue;
      long ty=HistoryDealGetInteger(k,DEAL_TYPE); if(ty!=DEAL_TYPE_BUY&&ty!=DEAL_TYPE_SELL) continue;
      v+=HistoryDealGetDouble(k,DEAL_PROFIT)+HistoryDealGetDouble(k,DEAL_COMMISSION)+HistoryDealGetDouble(k,DEAL_SWAP);
     }
   return v;
  }
string Refuse()   // "" = clear. Otherwise the reason there is no new ticket.
  {
   datetime g=TimeGMT(); MqlDateTime t; TimeToStruct(g,t);
   if(t.day_of_week==0||t.day_of_week==6||t.hour<InpSessStart||t.hour>=InpSessEnd) return "Thin hours";
   if(t.day_of_week==5&&t.hour>=InpFriNoNew) return "Friday late";
   int m=(t.hour*60+t.min+((g>=LastSun(t.year,3)&&g<LastSun(t.year,10))?60:0))%1440;   // London clock
   if(MathAbs(m-630)<=InpNewsMins||MathAbs(m-900)<=InpNewsMins) return "LBMA fix";
   if(SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)>InpMaxSpread) return "Spread too wide";
   if(ADRUsed()>=InpMaxADR) return "Day range used up";
   if(Realized()<=-MathMax(InpHaltMoney,AccountInfoDouble(ACCOUNT_BALANCE)*InpHaltPct/100.0)) return "Day halted";
   return "";
  }
bool AnyPos(int &d,double &op,double &sl,double &tp,datetime &ot)   // ANY magic on this symbol
  {
   for(int i=0;i<PositionsTotal();i++)
     {
      if(PositionGetTicket(i)==0||PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      d=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1; op=PositionGetDouble(POSITION_PRICE_OPEN); sl=PositionGetDouble(POSITION_SL); tp=PositionGetDouble(POSITION_TP);
      ot=(datetime)PositionGetInteger(POSITION_TIME); return true;
     }
   return false;
  }
int Held(datetime ot) { int h=iBarShift(_Symbol,_Period,ot,false); return (h<0)?9999:h; }
void Levels(int d,double ref,double &bank,double &leave)   // d=-1 sell, +1 buy. This chart's range only.
  {
   bank=0; leave=0; if(ArraySize(R)<InpRangeBars+2) return;
   double hh=0,ll=DBL_MAX,sw=(d<0)?0:DBL_MAX;
   for(int i=1;i<=InpRangeBars;i++) { hh=MathMax(hh,R[i].high); ll=MathMin(ll,R[i].low); }
   for(int i=1;i<=6;i++) sw=(d<0)?MathMax(sw,R[i].high):MathMin(sw,R[i].low);
   double rng=MathMax(hh-ll,2.0),ld=MathMin(MathMax(MathAbs(sw-ref),0.5*rng),rng);
   int ps=PeriodSeconds(); double g=(ps<=900)?1.0:((ps<=3600)?2.0:5.0);   // $1 M5, $2 H1, $5 H4
   bank=MathRound((ref+d*InpBankMult*rng)/g)*g; if(d*(bank-ref)<1.0) bank=ref+d;
   leave=MathRound((ref-d*ld)/g)*g-d*0.30;   // one step past the swing, never parked on the round
  }
string State(double &bank,double &leave,string &say)   // the ONE word. Panel and EA both read this.
  {
   int d=0; double op=0,sl=0,tp=0; datetime ot=0; bank=0; leave=0; bool ok=Eval();
   if(AnyPos(d,op,sl,tp,ot))
     {
      if(ok) Levels(d,op,bank,leave);
      if(tp>0) bank=tp;
      if(sl>0) leave=sl;
      MqlDateTime t; TimeToStruct(TimeGMT(),t);
      double px=(d>0)?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      if(t.day_of_week==5&&t.hour>=InpFriFlat) { say="Friday close. Get flat before the weekend."; return "GET OUT"; }
      if(bank>0&&d*(px-bank)>=0) { say="Bank reached. Take the profit."; return "TAKE PROFIT"; }
      if(ok&&leave>0&&Held(ot)>=InpMinHold&&d*(R[1].close-leave)<0) { say="Candle closed past Leave. Cover it."; return "GET OUT"; }
      say="You are in. Do nothing until Bank or Leave."; return (d>0)?"SIT ON LONG":"SIT ON SHORT";
     }
   if(!ok) { say="Loading data. Do nothing."; return "WAIT"; }
   string why=Refuse();
   if(why=="")
     {
      if(H4Dir!=0&&BarOk&&MapDir==H4Dir)
        {
         Levels(H4Dir,R[1].close,bank,leave);
         say=(H4Dir<0)?"Sell now. H4 down, candle closed weak, map agrees.":"Buy now. H4 up, candle closed strong, map agrees.";
         return (H4Dir<0)?"GO SHORT":"GO LONG";
        }
      if(H4Dir==0) say="H4 has no direction. Do nothing.";
      else if(!BarOk) say=(H4Dir<0)?"H4 is down. Wait for a red candle that closes low.":"H4 is up. Wait for a green candle that closes high.";
      else say="Chart trend fights H4. Wait.";
     }
   else say="Skip: "+why+". No new ticket.";
   return "WAIT";
  }
string Lines(string w,string say,double b,double l)   // the box, as 4 lines
  {
   return "LITE "+VER+"   H4 "+(H4Dir!=0?"ON":"off")+"   BAR "+(BarOk?"ON":"off")+"   MAP "+((H4Dir!=0&&MapDir==H4Dir)?"ON":"off")+"\n"+w+"\n"+say+"\n"+
          ((b>0&&l>0)?"Bank "+DoubleToString(b,_Digits)+"     Leave "+DoubleToString(l,_Digits):"Bank --     Leave --");
  }

void Lbl(int i,string tx,color c)
  {
   string n="ML_L"+IntegerToString(i); int y[4]={12,30,58,82};
   if(ObjectFind(0,n)<0)
     {
      ObjectCreate(0,n,OBJ_LABEL,0,0,0); ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,n,OBJPROP_XDISTANCE,18); ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y[i]);
      ObjectSetString(0,n,OBJPROP_FONT,"Consolas"); ObjectSetInteger(0,n,OBJPROP_FONTSIZE,i==1?14:10);
      ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,n,OBJPROP_HIDDEN,true);
     }
   ObjectSetString(0,n,OBJPROP_TEXT,tx); ObjectSetInteger(0,n,OBJPROP_COLOR,c);
  }
void HL(string n,double p,color c,string tx)
  {
   if(p<=0) { ObjectDelete(0,n); return; }
   if(ObjectFind(0,n)<0)
     {
      ObjectCreate(0,n,OBJ_HLINE,0,0,p); ObjectSetInteger(0,n,OBJPROP_STYLE,STYLE_DASH); ObjectSetString(0,n,OBJPROP_TEXT,tx);
      ObjectSetInteger(0,n,OBJPROP_COLOR,c); ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false); ObjectSetInteger(0,n,OBJPROP_HIDDEN,true);
     }
   ObjectSetDouble(0,n,OBJPROP_PRICE,p);
  }
int OnInit()
  {
   if(!IsGold()) { Alert("MONKE LITE: gold only (XAU / GOLD)."); return INIT_FAILED; }
   if(!InitH()) return INIT_FAILED;
   ObjectsDeleteAll(0,"ML_");
   ObjectCreate(0,"ML_BOX",OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,"ML_BOX",OBJPROP_XDISTANCE,8); ObjectSetInteger(0,"ML_BOX",OBJPROP_YDISTANCE,6);
   ObjectSetInteger(0,"ML_BOX",OBJPROP_XSIZE,430); ObjectSetInteger(0,"ML_BOX",OBJPROP_YSIZE,104);
   ObjectSetInteger(0,"ML_BOX",OBJPROP_BGCOLOR,C'20,22,28'); ObjectSetInteger(0,"ML_BOX",OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,"ML_BOX",OBJPROP_COLOR,C'60,64,74'); ObjectSetInteger(0,"ML_BOX",OBJPROP_SELECTABLE,false); ObjectSetInteger(0,"ML_BOX",OBJPROP_HIDDEN,true);
   SetIndexBuffer(0,Ab,INDICATOR_DATA); SetIndexBuffer(1,As,INDICATOR_DATA);
   for(int i=0;i<2;i++) { PlotIndexSetInteger(i,PLOT_ARROW,i==0?233:234); PlotIndexSetDouble(i,PLOT_EMPTY_VALUE,0.0); }
   IndicatorSetString(INDICATOR_SHORTNAME,"MONKE LITE");
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int r) { ObjectsDeleteAll(0,"ML_"); Comment(""); Rel(); }
int OnCalculate(const int n,const int pc,const datetime &t[],const double &o[],const double &h[],const double &l[],const double &c[],
                const long &tv[],const long &v[],const int &sp[])
  {
   double bank,leave; string a[]; string say,w=State(bank,leave,say),tx=Lines(w,say,bank,leave);
   StringSplit(tx,'\n',a); Comment(tx);
   color wc=(StringFind(w,"SHORT")>=0)?clrTomato:((StringFind(w,"LONG")>=0)?C'0,190,170':((w=="WAIT")?clrSilver:clrGold));
   Lbl(0,a[0],C'150,155,165'); Lbl(1,a[1],wc); Lbl(2,a[2],clrWhite); Lbl(3,a[3],clrWhite);
   HL("ML_BANK",bank,C'0,190,170',"BANK"); HL("ML_LEAVE",leave,clrRed,"LEAVE");
   if(pc==0) { ArrayInitialize(Ab,0.0); ArrayInitialize(As,0.0); }
   for(int i=MathMax(0,n-4);i<n;i++) { Ab[i]=0.0; As[i]=0.0; }
   if(InpArrow&&n>2&&ArraySize(R)>2)
     {
      double off=(R[1].high-R[1].low)*0.3;
      if(w=="GO LONG") Ab[n-2]=R[1].low-off;
      if(w=="GO SHORT") As[n-2]=R[1].high+off;
     }
   return n;
  }
