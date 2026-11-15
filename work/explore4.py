import pandas as pd, numpy as np
pd.set_option('display.width',260); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',120)
xl="uploads/data.xlsx"
t=pd.read_excel(xl,"Маркет Вконтакте — итоги").set_index('Метрика')
d=pd.read_excel(xl,"Маркет Вконтакте — по дням"); s=pd.read_excel(xl,"Маркет Вконтакте — источники")
c=pd.read_excel(xl,"Маркет Вконтакте — категории"); p=pd.read_excel(xl,"Покупатели"); r=pd.read_excel(xl,"Покупатели по регионам")
n=lambda k,col='Маркет Вконтакте': float(t.loc[k,col])
print("### FUNNEL")
for col in ['Маркет Вконтакте','Партнёр 1']:
    imp=n('Показы товаров',col); op=n('Открытия карточки товара',col); cl=n('Нажатия на кнопку в карточке',col); od=n('Оформленные заказы',col); gmv=n('GMV, ₽',col)
    print(f"\n{col}: imp {imp:,.0f} -> opens {op:,.0f} ({op/imp:.2%}) -> clicks {cl:,.0f} ({cl/op:.2%}) -> orders {od:,.0f} ({od/cl:.2%})")
    print(f"  opens->order {od/op:.3%}; imp->order {od/imp:.4%}; GMV {gmv:,.0f}; AOV {gmv/od:,.0f}; GMV/1000 imp {gmv/imp*1000:,.1f} ₽; orders/1000 opens {od/op*1000:.2f}")
print("\nGap decomposition (orders gap = product of step ratios):")
vk=[n('Показы товаров'),n('Открытия карточки товара'),n('Нажатия на кнопку в карточке'),n('Оформленные заказы')]
pt=[n('Показы товаров','Партнёр 1'),n('Открытия карточки товара','Партнёр 1'),n('Нажатия на кнопку в карточке','Партнёр 1'),n('Оформленные заказы','Партнёр 1')]
labels=['Показы','CTR показ→открытие','Клик по кнопке (открытие→клик)','Клик→заказ']
tot=np.log(pt[3]/vk[3])
for i in range(4):
    ratio = pt[i]/vk[i] if i==0 else (pt[i]/pt[i-1])/(vk[i]/vk[i-1])
    print(f"{labels[i]:32s} P/VK ratio {ratio:8.3f}  вклад в лог-разрыв {np.log(ratio)/tot:7.1%}")
print("total orders ratio", pt[3]/vk[3])
print("\nVK paid/orders:", 4903/413740, " Partner direct-to-site transitions:", n('Прямые переходы к Партнёру 1 (без открытия карточки)','Партнёр 1'))
print("Partner total clicks incl direct:", 36626075+106914679, "orders/(clicks+direct):", 4927525/(36626075+106914679))

print("\n### SOURCES")
s2=s[s['Источник']!='в т.ч. из реферальных постов и клипов'].copy()
s2['VK_share']=s2['Маркет Вконтакте']/s2['Маркет Вконтакте'].sum(); s2['P_share']=s2['Партнёр 1']/s2['Партнёр 1'].sum()
print(s2.to_string(index=False))
print("VK browse (Другое+Витрина+Главная):", s2.loc[s2['Источник'].isin(['Другое','Витрина магазина','Главная Маркета Вконтакте']),'VK_share'].sum())
print("VK content (Лента+Клипы):", s2.loc[s2['Источник'].isin(['Лента','Клипы']),'VK_share'].sum())
print("P content:", s2.loc[s2['Источник'].isin(['Лента','Клипы']),'P_share'].sum())

print("\n### CATEGORIES")
c['conv_vk']=c['Заказы: Маркет Вконтакте']/c['Открытия карточки: Маркет Вконтакте'].replace(0,np.nan)
c['conv_p']=c['Заказы: Партнёр 1']/c['Открытия карточки: Партнёр 1'].replace(0,np.nan)
c['vk_open_share']=c['Открытия карточки: Маркет Вконтакте']/c['Открытия карточки: Маркет Вконтакте'].sum()
c['vk_order_share']=c['Заказы: Маркет Вконтакте']/c['Заказы: Маркет Вконтакте'].sum()
c['p_order_share']=c['Заказы: Партнёр 1']/c['Заказы: Партнёр 1'].sum()
print(c.sort_values('Открытия карточки: Маркет Вконтакте',ascending=False).to_string(index=False))
dead=c[c['conv_vk']<0.001]
print("\n'Dead traffic' categories (conv<0.1%):", dead['Категория'].tolist())
print("share of VK opens in dead categories:", dead['Открытия карточки: Маркет Вконтакте'].sum()/c['Открытия карточки: Маркет Вконтакте'].sum())
print("their share of VK orders:", dead['Заказы: Маркет Вконтакте'].sum()/c['Заказы: Маркет Вконтакте'].sum())
cos=lambda a,b: float(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b))
print("cosine VK opens vs VK orders:", round(cos(c.vk_open_share,c.vk_order_share),3))
print("cosine VK opens vs P orders:", round(cos(c.vk_open_share,c.p_order_share),3))
print("cosine VK orders vs P orders:", round(cos(c.vk_order_share,c.p_order_share),3))

print("\n### DEMOGRAPHY")
p2=p.dropna(subset=['Покупатели: Маркет Вконтакте']).copy()
p2['vk_share']=p2['Покупатели: Маркет Вконтакте']/p2['Покупатели: Маркет Вконтакте'].sum()
p2['p_share']=p2['Покупатели: Партнёр 1']/p['Покупатели: Партнёр 1'].sum()
p2['vk_opb']=p2['Заказы: Маркет Вконтакте']/p2['Покупатели: Маркет Вконтакте']
p2['p_opb']=p2['Заказы: Партнёр 1']/p2['Покупатели: Партнёр 1']
print(p2.sort_values('vk_share',ascending=False).to_string(index=False))
print("\nby gender VK:", p2.groupby('Пол')[['Покупатели: Маркет Вконтакте','Покупатели: Партнёр 1']].sum().assign(vk=lambda x:x.iloc[:,0]/x.iloc[:,0].sum(), pt=lambda x:x.iloc[:,1]/x.iloc[:,1].sum()).round(3).to_string())
age=p2.groupby('Возраст')[['Покупатели: Маркет Вконтакте','Покупатели: Партнёр 1']].sum()
print("\nby age shares:\n", (age/age.sum()).round(3).to_string())
print("\n35+ share VK:", p2[p2['Возраст'].isin(['35–44','45–54','55+'])]['Покупатели: Маркет Вконтакте'].sum()/p2['Покупатели: Маркет Вконтакте'].sum())
print("35+ share P:", p[p['Возраст'].isin(['35–44','45–54','55+'])]['Покупатели: Партнёр 1'].sum()/p['Покупатели: Партнёр 1'].sum())

print("\n### GEO")
r2=r.dropna(subset=['Покупатели: Маркет Вконтакте']).copy()
r2['vk_share']=r2['Покупатели: Маркет Вконтакте']/r2['Покупатели: Маркет Вконтакте'].sum(); r2['p_share']=r2['Покупатели: Партнёр 1']/r['Покупатели: Партнёр 1'].sum()
r2['idx']=r2['vk_share']/r2['p_share']
print(r2.head(12).to_string(index=False))
print("top5 VK share:", r2.nlargest(5,'vk_share').vk_share.sum(), "top5 P share:", r2.nlargest(5,'p_share').p_share.sum())
print("MSK+SPB VK:", r2[r2['Регион'].isin(['г. Москва','г. Санкт-Петербург'])].vk_share.sum(), "P:", r[r['Регион'].isin(['г. Москва','г. Санкт-Петербург'])]['Покупатели: Партнёр 1'].sum()/r['Покупатели: Партнёр 1'].sum())
print("HHI VK:", (r2.vk_share**2).sum(), "P:", (r2.p_share**2).sum())
print("over-index regions:", r2.nlargest(6,'idx')[['Регион','vk_share','p_share','idx']].to_string(index=False))

print("\n### DAILY DYNAMICS")
d['dt']=pd.to_datetime(d['Дата']); d['dow']=d['dt'].dt.dayofweek; d['week']=d['dt'].dt.isocalendar().week
for col in ['Показы товаров: Маркет Вконтакте','Открытия карточки: Маркет Вконтакте','Заказы: Маркет Вконтакте','GMV, ₽: Маркет Вконтакте','Показы товаров: Партнёр 1','Открытия карточки: Партнёр 1','Заказы: Партнёр 1','GMV, ₽: Партнёр 1','DAU Маркета Вконтакте','Поисковые запросы']:
    y=d[col].values; x=np.arange(len(y)); sl=np.polyfit(x,y,1)[0]
    print(f"{col:42s} first7avg {y[:7].mean():>14,.0f} last7avg {y[-7:].mean():>14,.0f} chg {y[-7:].mean()/y[:7].mean()-1:+7.1%} slope/day {sl:>12,.0f}")
d['conv_vk']=d['Заказы: Маркет Вконтакте']/d['Открытия карточки: Маркет Вконтакте']
d['conv_p']=d['Заказы: Партнёр 1']/d['Открытия карточки: Партнёр 1']
d['ctr_vk']=d['Открытия карточки: Маркет Вконтакте']/d['Показы товаров: Маркет Вконтакте']
d['ctr_p']=d['Открытия карточки: Партнёр 1']/d['Показы товаров: Партнёр 1']
print("\nconv_vk first7 %.4f%% last7 %.4f%% | conv_p first7 %.3f%% last7 %.3f%%"%(d.conv_vk[:7].mean()*100,d.conv_vk[-7:].mean()*100,d.conv_p[:7].mean()*100,d.conv_p[-7:].mean()*100))
print("weekday effect (mean orders, 0=Mon):\n", d.groupby('dow')[['Заказы: Маркет Вконтакте','Заказы: Партнёр 1']].mean().round(0).to_string())
print("\nsearch: queries/day %.0f, with card open %.1f%%"%(d['Поисковые запросы'].mean(), 100*d['Поисковые запросы с открытием карточки'].sum()/d['Поисковые запросы'].sum()))
print("Market DAU/MAU %.2f%%; DAU share of VK 90.8M: %.3f%%"%(100*127406/2997341, 100*127406/90_800_000))
print("monthly card openers 27.33M / saw products 66.62M = %.1f%%"%(100*27333960/66617967))
print("referral share of all card opens: %.1f%%"%(100*82324081/(193512461+86882822)))
