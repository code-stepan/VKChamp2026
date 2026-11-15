import pandas as pd, numpy as np
pd.set_option('display.width',260); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',120)
b=pd.read_excel("uploads/data.xlsx","Бизнесы")
b=b.rename(columns={'Число подписчиков':'subs','Число активных товаров в каталоге':'catalog','Заказы через чекаут':'orders','GMV через чекаут, ₽':'gmv','Траты на рекламу всего, ₽':'ads','Подключён чекаут':'checkout','Подключена доставка':'delivery','Подключена оплата':'payment','Открытия карточки товара из контента':'opens','Просмотры товарного контента':'pv','Просмотры обычного контента':'ov','Участие в реферальной программе':'ref','Автор оригинального контента (оценка модели)':'orig','Тематика':'theme','Тип бизнеса (товары / услуги)':'btype'})
b['prod_posts']=b['Посты с товаром за 30 дней']+b['Клипы с товаром за 30 дней']
b['posts']=b['Посты за 30 дней']+b['Клипы за 30 дней']
b['has_order']=(b['orders']>0).astype(int)
b['er_reg']=(b['Лайки обычного контента']+b['Репосты обычного контента'])/b['ov'].replace(0,np.nan)
b['has_prod_content']=(b['prod_posts']>0).astype(int)
print("### aggregate views per post")
print("prod:", b['pv'].sum()/b['prod_posts'].sum(), "regular:", b['ov'].sum()/b['posts'].sum(), "ratio:", (b['pv'].sum()/b['prod_posts'].sum())/(b['ov'].sum()/b['posts'].sum()))
print("\n### paired, organic only (ads==0)")
both=b[(b['pv']>0)&(b['ov']>0)&(b['prod_posts']>0)&(b['posts']>0)].copy()
both['vpp_prod']=both['pv']/both['prod_posts']; both['vpp_reg']=both['ov']/both['posts']
o=both[both['ads']==0]
print("n organic paired:",len(o),"median ratio vpp:",(o['vpp_prod']/o['vpp_reg']).median(),"share prod<reg:",(o['vpp_prod']<o['vpp_reg']).mean())
print("\n### orders concentration")
s=b['orders'].sort_values(ascending=False); tot=s.sum()
print("top10 share:", s.head(10).sum()/tot, "top1% share:", s.head(98).sum()/tot, "sellers:",(s>0).sum())
print("\n### theme sell rate (n>=100)")
g=b.groupby('theme').agg(n=('ID бизнеса','size'),cat=('catalog',lambda x:(x>0).mean()),chk=('checkout','mean'),dlv=('delivery','mean'),sellers=('has_order','sum'),orders=('orders','sum'),gmv=('gmv','sum'),ads=('ads','sum'),subs=('subs','median'))
g['sell_rate']=g['sellers']/g['n']; g['aov']=g['gmv']/g['orders'].replace(0,np.nan)
print(g[g.n>=100].sort_values('sell_rate',ascending=False).to_string())
print("\n### spearman corr with orders")
cols=['subs','catalog','posts','prod_posts','ov','pv','opens','checkout','delivery','payment','ads','ref','er_reg','orders','gmv']
print(b[cols].corr(method='spearman')['orders'].round(3).to_string())

print("\n### LOGIT P(order>0), catalog>0 subset")
import statsmodels.api as sm
sub=b[b['catalog']>0].copy()
X=pd.DataFrame({'log_subs':np.log1p(sub['subs']),'log_catalog':np.log1p(sub['catalog']),'log_posts':np.log1p(sub['posts']),'log_ov':np.log1p(sub['ov']),'has_prod_content':sub['has_prod_content'],'checkout':sub['checkout'],'delivery':sub['delivery'],'payment':sub['payment'],'log_ads':np.log1p(sub['ads']),'ref':sub['ref']})
X=sm.add_constant(X)
m=sm.Logit(sub['has_order'],X).fit(disp=0)
res=pd.DataFrame({'coef':m.params,'OR':np.exp(m.params),'p':m.pvalues,'lo':np.exp(m.conf_int()[0]),'hi':np.exp(m.conf_int()[1])})
print(res.round(4).to_string()); print("pseudo R2", round(m.prsquared,3), "n",int(m.nobs))

print("\n### PSM: delivery effect among checkout=1 & catalog>0")
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
d=sub[sub['checkout']==1].copy()
feat=pd.DataFrame({'log_subs':np.log1p(d['subs']),'log_catalog':np.log1p(d['catalog']),'log_posts':np.log1p(d['posts']),'log_ov':np.log1p(d['ov']),'prod':d['has_prod_content'],'log_ads':np.log1p(d['ads'])})
sc=StandardScaler().fit(feat); f=sc.transform(feat)
ps=LogisticRegression(max_iter=1000,C=1.0).fit(f,d['delivery']).predict_proba(f)[:,1]
d['ps']=ps
tr=d[d.delivery==1]; ct=d[d.delivery==0]
nn=NearestNeighbors(n_neighbors=1).fit(ct[['ps']].values)
dist,idx=nn.kneighbors(tr[['ps']].values)
matched=ct.iloc[idx[:,0]]
print("treated n",len(tr),"control pool",len(ct))
print("sell rate treated %.4f vs matched control %.4f  lift %.2fx"%(tr.has_order.mean(),matched.has_order.mean(),tr.has_order.mean()/matched.has_order.mean()))
print("orders/biz treated %.3f vs matched %.3f"%(tr.orders.mean(),matched.orders.mean()))
print("gmv/biz treated %.0f vs matched %.0f"%(tr.gmv.mean(),matched.gmv.mean()))
print("SMD before/after log_subs:", (np.log1p(tr.subs).mean()-np.log1p(ct.subs).mean())/np.log1p(d.subs).std(), (np.log1p(tr.subs).mean()-np.log1p(matched.subs).mean())/np.log1p(d.subs).std())
print("SMD before/after log_catalog:", (np.log1p(tr.catalog).mean()-np.log1p(ct.catalog).mean())/np.log1p(d.catalog).std(), (np.log1p(tr.catalog).mean()-np.log1p(matched.catalog).mean())/np.log1p(d.catalog).std())

print("\n### ML feature importance (GBM, catalog>0)")
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import roc_auc_score, average_precision_score
Xf=pd.DataFrame({'log_subs':np.log1p(sub['subs']),'log_catalog':np.log1p(sub['catalog']),'log_posts':np.log1p(sub['posts']),'log_ov':np.log1p(sub['ov']),'log_pv':np.log1p(sub['pv']),'opens':np.log1p(sub['opens']),'prod':sub['has_prod_content'],'checkout':sub['checkout'],'delivery':sub['delivery'],'payment':sub['payment'],'log_ads':np.log1p(sub['ads']),'ref':sub['ref'],'orig':sub['orig'].fillna(-1),'er':sub['er_reg'].fillna(0)})
cv=StratifiedKFold(5,shuffle=True,random_state=42)
pred=cross_val_predict(HistGradientBoostingClassifier(max_depth=3,random_state=42),Xf,sub['has_order'],cv=cv,method='predict_proba')[:,1]
print("AUC",round(roc_auc_score(sub['has_order'],pred),3),"AP",round(average_precision_score(sub['has_order'],pred),3),"base rate",round(sub['has_order'].mean(),4))
from sklearn.inspection import permutation_importance
mm=HistGradientBoostingClassifier(max_depth=3,random_state=42).fit(Xf,sub['has_order'])
pi=permutation_importance(mm,Xf,sub['has_order'],n_repeats=10,random_state=42,scoring='average_precision')
print(pd.Series(pi.importances_mean,index=Xf.columns).sort_values(ascending=False).round(4).to_string())
