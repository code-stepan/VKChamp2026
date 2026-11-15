import pandas as pd, numpy as np
pd.set_option('display.width',260); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',120)
b=pd.read_excel("uploads/data.xlsx","Бизнесы")
b['catalog']=b['Число активных товаров в каталоге']; b['orders']=b['Заказы через чекаут']; b['gmv']=b['GMV через чекаут, ₽']; b['ads']=b['Траты на рекламу всего, ₽']
b['has_order']=(b['orders']>0).astype(int)
b['pp']=b['Посты с товаром за 30 дней']; b['cp']=b['Клипы с товаром за 30 дней']
b['prod_posts']=b['pp']+b['cp']; b['posts']=b['Посты за 30 дней']+b['Клипы за 30 дней']
b['pv']=b['Просмотры товарного контента']; b['ov']=b['Просмотры обычного контента']
b['opens']=b['Открытия карточки товара из контента']
b['er_prod']=(b['Лайки товарного контента']+b['Репосты товарного контента'])/b['pv'].replace(0,np.nan)
b['er_reg']=(b['Лайки обычного контента']+b['Репосты обычного контента'])/b['ов'.replace('ов','ov')].replace(0,np.nan)
b['vpp_prod']=b['pv']/b['prod_posts'].replace(0,np.nan); b['vpp_reg']=b['ov']/(b['Посты за 30 дней']+b['Клипы за 30 дней']).replace(0,np.nan)
b['ctr_card']=b['opens']/b['pv'].replace(0,np.nan)

print("### ACTIVATION FUNNEL (n=9754)")
steps=[('Есть сообщество',len(b)),('Загружены товары (>0)',(b['Товары загружены']>0).sum()),('Активный каталог (>0)',(b['catalog']>0).sum()),
('Подключён чекаут',(b['Подключён чекаут']==1).sum()),('+ доставка',((b['Подключён чекаут']==1)&(b['Подключена доставка']==1)).sum()),
('+ оплата (полный стек)',((b['Подключён чекаут']==1)&(b['Подключена доставка']==1)&(b['Подключена оплата']==1)).sum()),
('Есть товарный контент',(b['prod_posts']>0).sum()),('Есть открытия карточки из контента',(b['opens']>0).sum()),
('≥1 заказ через чекаут',(b['orders']>0).sum()),('≥5 заказов',(b['orders']>=5).sum()),('Платит за рекламу',(b['ads']>0).sum())]
for k,v in steps: print(f"{k:38s} {v:6d}  {v/len(b):6.2%}")

print("\n### SCENARIO SEGMENTS")
def seg(r):
    if r['catalog']>0 and r['Подключён чекаут']==1 and r['Подключена доставка']==1 and r['Подключена оплата']==1: return '5. Полный стек'
    if r['catalog']>0 and r['Подключён чекаут']==1 and r['Подключена доставка']==1: return '4. Каталог+чекаут+доставка'
    if r['catalog']>0 and r['Подключён чекаут']==1: return '3. Каталог+чекаут (без логистики)'
    if r['catalog']>0: return '2. Витрина без чекаута'
    if r['Подключён чекаут']==1: return '1. Чекаут без каталога (аномалия)'
    if r['Тип бизнеса (товары / услуги)']=='услужное': return '0a. Услуги без каталога'
    return '0b. Только контент/переписка'
b['seg']=b.apply(seg,axis=1)
agg=b.groupby('seg').agg(n=('ID бизнеса','size'), subs_med=('Число подписчиков','median'), catalog_med=('catalog','median'),
   prod_posts_share=('prod_posts',lambda x:(x>0).mean()), opens_sum=('opens','sum'), sellers=('has_order','sum'), orders=('orders','sum'),
   gmv=('gmv','sum'), ads=('ads','sum'), ads_payers=('ads',lambda x:(x>0).sum()))
agg['sell_rate']=agg['sellers']/agg['n']; agg['orders_per_biz']=agg['orders']/agg['n']; agg['gmv_per_seller']=agg['gmv']/agg['sellers'].replace(0,np.nan)
agg['roas']=agg['gmv']/agg['ads'].replace(0,np.nan)
print(agg.to_string())

print("\n### TYPE x SELLERS")
g=b.groupby('Тип бизнеса (товары / услуги)').agg(n=('ID бизнеса','size'),checkout=('Подключён чекаут','mean'),delivery=('Подключена доставка','mean'),payment=('Подключена оплата','mean'),sellers=('has_order','sum'),orders=('orders','sum'),gmv=('gmv','sum'),ads=('ads','sum'))
g['sell_rate']=g['sellers']/g['n']; print(g.to_string())

print("\n### SELL RATE BY TOOL COMBO (catalog>0 only)")
cc=b[b['catalog']>0].groupby(['Подключён чекаут','Подключена доставка','Подключена оплата']).agg(n=('ID бизнеса','size'),sellers=('has_order','sum'),orders=('orders','sum'),gmv=('gmv','sum'),subs=('Число подписчиков','median'),opens=('opens','median'))
cc['sell_rate']=cc['sellers']/cc['n']; cc['orders_per_biz']=cc['orders']/cc['n']; print(cc.to_string())

print("\n### CONTENT: PRODUCT vs REGULAR (paired, businesses with both)")
both=b[(b['pv']>0)&(b['ov']>0)&(b['prod_posts']>0)&(b['posts']>0)]
print("n paired:",len(both))
for col,lab in [('vpp','views per post'),('er','engagement rate')]:
    a=both[col+'_prod']; z=both[col+'_reg']
    print(f"{lab}: prod median {a.median():.4f} | reg median {z.median():.4f} | ratio medians {a.median()/z.median():.3f} | paired median ratio {(a/z).median():.3f} | share prod<reg {(a<z).mean():.1%}")
print("card CTR from product views: median", b['ctr_card'].median(), "aggregate", b['opens'].sum()/b['pv'].sum())
print("product share of views (aggregate):", b['pv'].sum()/(b['pv'].sum()+b['ov'].sum()))
print("product share of posts (aggregate):", b['prod_posts'].sum()/b['posts'].sum())
print("\nby size decile: median views/post product vs regular")
both=both.copy(); both['size_dec']=pd.qcut(both['Число подписчиков'],10,labels=False,duplicates='drop')
print(both.groupby('size_dec').agg(n=('ID бизнеса','size'),vpp_prod=('vpp_prod','median'),vpp_reg=('vpp_reg','median'),er_prod=('er_prod','median'),er_reg=('er_reg','median'),ctr=('ctr_card','median')).to_string())

print("\n### TOP SELLERS")
print(b.nlargest(12,'orders')[['ID бизнеса','Тематика','Тип бизнеса (товары / услуги)','Число подписчиков','catalog','Подключена доставка','Подключена оплата','prod_posts','opens','orders','gmv','ads']].to_string())
print("\n### AD SPEND vs ORDERS")
b['ads_band']=pd.cut(b['ads'],[-1,0,10000,100000,1000000,1e12],labels=['0','1-10k','10-100k','100k-1M','>1M'])
print(b.groupby('ads_band',observed=True).agg(n=('ID бизнеса','size'),sellers=('has_order','sum'),orders=('orders','sum'),gmv=('gmv','sum'),ads=('ads','sum'),subs=('Число подписчиков','median')).assign(sell_rate=lambda x:x.sellers/x.n).to_string())
print("\nROAS among payers with GMV>0:", (b.loc[(b.ads>0)&(b.gmv>0),'gmv'].sum()/b.loc[(b.ads>0)&(b.gmv>0),'ads'].sum()), "n:",((b.ads>0)&(b.gmv>0)).sum())
print("ad payers with 0 orders:", ((b.ads>0)&(b.orders==0)).sum(), "their spend:", b.loc[(b.ads>0)&(b.orders==0),'ads'].sum())
