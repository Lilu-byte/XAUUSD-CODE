import pandas as pd, numpy as np
B='/mnt/project-files/xauusd-github-bots/market-matrix/'
r=pd.read_csv(B+'results.csv'); o=pd.read_csv(B+'oanda_2007_2016.csv')
pd.set_option('display.width',250); pd.set_option('display.max_rows',300); pd.set_option('display.max_columns',40)
hold=r[r.rule.str.startswith('Hold')].set_index('tf')
ohold=o[o.rule.str.startswith('Hold')].set_index('tf')
print(hold[['train_per_day','train_sharpe','train_max_dd','test_per_day','test_sharpe','test_max_dd','22-26_per_day','22-26_sharpe']])
print(ohold[['per_day','sharpe','max_dd']])
nr=r[~r.rule.str.startswith('Hold')].copy()
no=o[~o.rule.str.startswith('Hold')].copy()
print('n rules', nr.rule.nunique(), 'rows', len(nr), 'oanda rows', len(no))
# beat hold in $ per period
nr['beat_train']=nr.apply(lambda x: x.train_per_day>hold.loc[x.tf,'train_per_day'],axis=1)
nr['beat_test']=nr.apply(lambda x: x.test_per_day>hold.loc[x.tf,'test_per_day'],axis=1)
no['beat_o']=no.apply(lambda x: x.per_day>ohold.loc[x.tf,'per_day'],axis=1)
m=nr.merge(no[['tf','rule','mode','per_day','sharpe','max_dd','beat_o']],on=['tf','rule','mode'],how='left')
print(m.groupby('tf')[['beat_train','beat_test']].sum())
print('oanda beat', no.groupby('tf').beat_o.sum())
m['nbeat']=m.beat_train.astype(int)+m.beat_test.astype(int)+m.beat_o.fillna(False).astype(int)
print('any beat all periods', m[(m.beat_train)&(m.beat_test)&((m.tf=='D1')|(m.beat_o==True))][['tf','rule','mode']])
print(m[m.beat_test][['tf','rule','mode','train_per_day','test_per_day','per_day','beat_train','beat_o']])
print(m[m.beat_o==True][['tf','rule','mode','train_per_day','test_per_day','per_day','beat_train','beat_test']])
print(m[m.beat_train][['tf','rule','mode','train_per_day','test_per_day','per_day','beat_test','beat_o']])
# best on train by sharpe and by per_day
for tf in ['D1','H4','H1']:
    s=nr[nr.tf==tf]
    b=s.sort_values('train_sharpe',ascending=False).head(3)
    print(tf,'best train sharpe:\n',b[['rule','mode','train_sharpe','train_per_day','test_per_day','test_sharpe','test_max_dd']])
    b=s.sort_values('train_per_day',ascending=False).head(3)
    print(tf,'best train $:\n',b[['rule','mode','train_sharpe','train_per_day','test_per_day','test_sharpe','test_max_dd']])
m.to_csv(B+'verify-final/merged.csv',index=False)
