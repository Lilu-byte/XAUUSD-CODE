//+------------------------------------------------------------------+
//| MONKE_XAU_LITE_EA.mq5  v18.10  magic 880025  (pair: MONKE_XAU_LITE)|
//| Hands. One gold ticket, any magic counts. Attach to ONE chart.    |
#property strict
#property version "18.10"
#include <Trade/Trade.mqh>
input group "=== Trade ==="
input long   InpMagic=880025; input double InpLot=0.01; input int InpSlip=30;
input bool   InpBE=true; input double InpBER=0.8;   // BE: stop to entry at 0.8R, only after min-hold
input bool   InpManageAny=false;                    // true = also protect/close tickets from other magics
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
CTrade Tr; datetime LastBar=0; double gBank=0,gLeave=0; const string LOCK="ML_LOCK_880025";
double MinDist() { return (MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))+(double)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)+5)*_Point; }
bool Mine() { return PositionGetString(POSITION_SYMBOL)==_Symbol&&(InpManageAny||PositionGetInteger(POSITION_MAGIC)==InpMagic); }
void Fix(bool force)   // step 2 of the two-step send: attach Leave/Bank. Also BE.
  {
   static datetime lf=0; if(!force&&TimeCurrent()==lf) return; lf=TimeCurrent();
   double md=MinDist();
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(tk==0||!Mine()) continue;
      int d=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1;
      double op=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),nsl=sl,ntp=tp,b=0,l=0;
      double px=(d>0)?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      if(sl==0||tp==0)
        {
         if(gBank>0&&gLeave>0) { b=gBank; l=gLeave; } else Levels(d,op,b,l);
         if(sl==0&&l>0) nsl=(d>0)?MathMin(l,px-md):MathMax(l,px+md);
         if(tp==0&&b>0) ntp=(d>0)?MathMax(b,px+md):MathMin(b,px-md);
        }
      else if(InpBE&&d*(op-sl)>0&&Held((datetime)PositionGetInteger(POSITION_TIME))>=InpMinHold&&d*(px-op)>=InpBER*d*(op-sl)&&d*(px-op)>=md)
         nsl=op+d*(double)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)*_Point;
      nsl=NormalizeDouble(nsl,_Digits); ntp=NormalizeDouble(ntp,_Digits);
      if(nsl!=sl||ntp!=tp) Tr.PositionModify(tk,nsl,ntp);
     }
  }
void CloseMine()
  {
   for(int i=PositionsTotal()-1;i>=0;i--) { ulong tk=PositionGetTicket(i); if(tk!=0&&Mine()) Tr.PositionClose(tk); }
   gBank=0; gLeave=0;
  }
void Enter(int d,double bank,double leave)   // step 1: market, no stops
  {
   double ref=(d>0)?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK),md=MinDist();
   if(d*(bank-ref)<md||d*(ref-leave)<md) return;   // price already ran through a level: skip
   double st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),lot=MathMin(MathMax(InpLot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
   lot=NormalizeDouble(MathFloor(lot/st+1e-9)*st,2); gBank=bank; gLeave=leave;
   if((d>0)?Tr.Buy(lot,_Symbol,0,0,0,"MONKE LITE"):Tr.Sell(lot,_Symbol,0,0,0,"MONKE LITE")) Fix(true);
  }
int OnInit()
  {
   if(!IsGold()) { Alert("MONKE LITE EA: gold only (XAU / GOLD)."); return INIT_FAILED; }
   if(GlobalVariableCheck(LOCK)&&TimeLocal()-(datetime)GlobalVariableGet(LOCK)<120) { Alert("MONKE LITE EA already runs on another chart. One EA only."); return INIT_FAILED; }
   if(!InitH()) return INIT_FAILED;
   GlobalVariableSet(LOCK,(double)TimeLocal()); EventSetTimer(30);
   Tr.SetExpertMagicNumber(InpMagic); Tr.SetDeviationInPoints(InpSlip); Tr.SetTypeFillingBySymbol(_Symbol);
   LastBar=iTime(_Symbol,_Period,0);   // wait for the next close, never enter mid-bar on attach
   return INIT_SUCCEEDED;
  }
void OnTimer() { GlobalVariableSet(LOCK,(double)TimeLocal()); }
void OnDeinit(const int r) { EventKillTimer(); GlobalVariableDel(LOCK); Rel(); Comment(""); }
void OnTick()
  {
   double bank,leave; string say,w=State(bank,leave,say);
   Comment(Lines(w,say,bank,leave));
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED)||!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return;
   Fix(false);   // manage what is open first
   static datetime lc=0;
   if((w=="GET OUT"||w=="TAKE PROFIT")&&TimeCurrent()!=lc) { lc=TimeCurrent(); CloseMine(); }
   datetime b=iTime(_Symbol,_Period,0); if(b==LastBar) return;
   LastBar=b;   // new closed bar: State() above already read it
   if(StringFind(w,"GO")==0) Enter(H4Dir,bank,leave);
  }
