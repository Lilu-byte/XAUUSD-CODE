import pandas as pd, numpy as np
B='/mnt/project-files/xauusd-github-bots/market-matrix/'
m=pd.read_csv(B+'verify-final/merged.csv')
r=pd.read_csv(B+'results.csv'); o=pd.read_csv(B+'oanda_2007_2016.csv')
hold=r[r.rule.str.startswith('Hold')].set_index('tf'); ohold=o[o.rule.str.startswith('Hold')].set_index('tf')
pd.set_option('display.width',250); pd.set_option('display.max_rows',300); pd.set_option('display.max_columns',40)
m['sh_tr']=m.apply(lambda x: x.train_sharpe>=hold.loc[x.tf,'train_sharpe'],axis=1)
m['sh_te']=m.apply(lambda x: x.test_sharpe>=hold.loc[x.tf,'test_sharpe'],axis=1)
m['sh_o']=m.apply(lambda x: (x.sharpe>=ohold.loc[x.tf,'sharpe']) if x.tf!='D1' and not np.isnan(x.sharpe) else np.nan,axis=1)
print('sharpe all three (H4/H1):'); print(m[(m.tf!='D1')&m.sh_tr&m.sh_te&(m.sh_o==True)][['tf','rule','mode','train_sharpe','test_sharpe','sharpe','train_max_dd','test_max_dd','max_dd','train_per_day','test_per_day','per_day']])
print('D1 sharpe both:'); print(m[(m.tf=='D1')&m.sh_tr&m.sh_te][['tf','rule','mode','train_sharpe','test_sharpe']])
print('sharpe 2 of 3:'); m['nsh']=m.sh_tr.astype(int)+m.sh_te.astype(int)+(m.sh_o==True).astype(int); print(m[m.nsh>=2][['tf','rule','mode','train_sharpe','test_sharpe','sharpe','nsh']])
# long+short vs long only sharpe
w=m.pivot_table(index=['tf','rule'],columns='mode',values=['train_sharpe','test_sharpe','sharpe'])
for col in ['train_sharpe','test_sharpe','sharpe']:
    a=w[(col,'long+short')]; b=w[(col,'long only')]
    ok=a.notna()&b.notna()
    print(col,'LS<LO',int((a[ok]<b[ok]).sum()),'LS<=LO',int((a[ok]<=b[ok]).sum()),'of',int(ok.sum()),'nan pairs',int((~ok).sum()))
    print(' exceptions:', list(zip(a[ok][a[ok]>=b[ok]].index, a[ok][a[ok]>=b[ok]].values, b[ok][a[ok]>=b[ok]].values)))
# per tf
for col in ['train_sharpe','test_sharpe']:
  for tf in ['D1','H4','H1']:
    a=w.loc[tf][(col,'long+short')]; b=w.loc[tf][(col,'long only')]
    print(tf,col,'LS<LO',int((a<b).sum()),'of',len(a))
# also 22-26 and common
w2=r[~r.rule.str.startswith('Hold')].pivot_table(index=['tf','rule'],columns='mode',values=['22-26_sharpe','common_sharpe'])
for col in ['22-26_sharpe','common_sharpe']:
    a=w2[(col,'long+short')]; b=w2[(col,'long only')]; print(col,'LS<LO',int((a<b).sum()),'of',len(a))
# combined: train and test both
a1=w[('train_sharpe','long+short')]<w[('train_sharpe','long only')]; a2=w[('test_sharpe','long+short')]<w[('test_sharpe','long only')]
print('both train and test LS<LO', int((a1&a2).sum()), 'of', len(a1))
# medians
for tf in ['D1','H4','H1']:
    s=r[(r.tf==tf)&~r.rule.str.startswith('Hold')]
    print(tf,'median test sharpe LS',s[s['mode']=='long+short'].test_sharpe.median(),'LO',s[s['mode']=='long only'].test_sharpe.median())
