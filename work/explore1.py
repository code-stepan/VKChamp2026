import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',100)
xl="uploads/data.xlsx"
b=pd.read_excel(xl,"Бизнесы"); t=pd.read_excel(xl,"Маркет Вконтакте — итоги")
d=pd.read_excel(xl,"Маркет Вконтакте — по дням"); s=pd.read_excel(xl,"Маркет Вконтакте — источники")
c=pd.read_excel(xl,"Маркет Вконтакте — категории"); p=pd.read_excel(xl,"Покупатели"); r=pd.read_excel(xl,"Покупатели по регионам")

print("### 1. AUDIT")
print("dup ID:", b['ID бизнеса'].duplicated().sum(), "n:", len(b))
b['aov_calc']=np.where(b['Заказы через чекаут']>0, b['GMV через чекаут, ₽']/b['Заказы через чекаут'].replace(0,np.nan), np.nan)
m=b['Средний чек, ₽'].notna()
print("AOV col vs calc: corr", b.loc[m,'aov_calc'].corr(b.loc[m,'Средний чек, ₽']), " median ratio", (b.loc[m,'aov_calc']/b.loc[m,'Средний чек, ₽']).median())
print("rows GMV>0 but orders=0:", ((b['GMV через чекаут, ₽']>0)&(b['Заказы через чекаут']==0)).sum())
print("rows orders>0 but GMV=0:", ((b['GMV через чекаут, ₽']==0)&(b['Заказы через чекаут']>0)).sum())
print("checkout=1 & catalog=0:", ((b['Подключён чекаут']==1)&(b['Число активных товаров в каталоге']==0)).sum())
print("product views>0 & no product posts/clips:", ((b['Просмотры товарного контента']>0)&(b['Посты с товаром за 30 дней']+b['Клипы с товаром за 30 дней']==0)).sum())
print("card opens>0 & product views=0:", ((b['Открытия карточки товара из контента']>0)&(b['Просмотры товарного контента']==0)).sum())
print("card opens > product views:", (b['Открытия карточки товара из контента']>b['Просмотры товарного контента']).sum())
print("uploaded < active:", (b['Товары загружены']<b['Число активных товаров в каталоге']).sum())
print("orig content NaN by type:\n", b.groupby('Тип бизнеса (товары / услуги)')['Автор оригинального контента (оценка модели)'].apply(lambda x: x.isna().mean()))
print("services>0 by type:\n", pd.crosstab(b['Тип бизнеса (товары / услуги)'], b['Число активных услуг']>0))

print("\n### 2. CROSS-SHEET RECONCILIATION")
num=lambda x: pd.to_numeric(x, errors='coerce')
tt=t.set_index('Метрика')
pairs=[('Показы товаров','Показы товаров: Маркет Вконтакте','Показы товаров: Партнёр 1'),
('Открытия карточки товара','Открытия карточки: Маркет Вконтакте','Открытия карточки: Партнёр 1'),
('Нажатия на кнопку в карточке','Нажатия на кнопку: Маркет Вконтакте','Нажатия на кнопку: Партнёр 1'),
('Оформленные заказы','Заказы: Маркет Вконтакте','Заказы: Партнёр 1'),
('GMV, ₽','GMV, ₽: Маркет Вконтакте','GMV, ₽: Партнёр 1'),
('Уникальные покупатели за 30 дней','Покупатели: Маркет Вконтакте','Покупатели: Партнёр 1')]
for tot,cd,cp in pairs:
    print(f"{tot:35s} VK: total={num(tt.loc[tot,'Маркет Вконтакте']):>14,.0f} days={d[cd].sum():>14,.0f} diff={d[cd].sum()/num(tt.loc[tot,'Маркет Вконтакте'])-1:+.3%} | P: total={num(tt.loc[tot,'Партнёр 1']):>14,.0f} days={d[cp].sum():>14,.0f} diff={d[cp].sum()/num(tt.loc[tot,'Партнёр 1'])-1:+.3%}")
print("paid orders: total", tt.loc['Оплаченные заказы','Маркет Вконтакте'], "days sum", d['Оплаченные заказы: Маркет Вконтакте'].sum())
print("sources sum VK", s['Маркет Вконтакте'].sum(), "vs", tt.loc['Открытия карточки товара','Маркет Вконтакте'])
print("sources sum P", s['Партнёр 1'].sum()-82324081, "vs", tt.loc['Открытия карточки товара','Партнёр 1'])
print("categories sum opens VK", c['Открытия карточки: Маркет Вконтакте'].sum(), "orders VK", c['Заказы: Маркет Вконтакте'].sum())
print("categories sum opens P", c['Открытия карточки: Партнёр 1'].sum(), "orders P", c['Заказы: Партнёр 1'].sum())
print("buyers sheet: VK", p['Покупатели: Маркет Вконтакте'].sum(), p['Заказы: Маркет Вконтакте'].sum(), "| P", p['Покупатели: Партнёр 1'].sum(), p['Заказы: Партнёр 1'].sum())
print("regions sheet: VK", r['Покупатели: Маркет Вконтакте'].sum(), r['Заказы: Маркет Вконтакте'].sum(), "| P", r['Покупатели: Партнёр 1'].sum(), r['Заказы: Партнёр 1'].sum())
print("posts/clips opens total(totals sheet) 86,321,893 vs sources Лента+Клипы:", s.loc[s['Источник'].isin(['Лента','Клипы']),['Маркет Вконтакте','Партнёр 1']].sum().to_dict())
print("search queries days sum", d['Поисковые запросы'].sum(), "vs totals 28,585,243")
print("DAU mean", d['DAU Маркета Вконтакте'].mean(), "MAU 2,997,341 -> DAU/MAU", d['DAU Маркета Вконтакте'].mean()/2997341)

print("\n### 3. BIZ TOTALS")
tot=b[['Заказы через чекаут','GMV через чекаут, ₽','Траты на рекламу всего, ₽','Открытия карточки товара из контента','Просмотры товарного контента','Просмотры обычного контента']].sum()
print(tot.to_string())
print("sample checkout GMV / Market GMV:", tot['GMV через чекаут, ₽']/1564546740)
print("sample checkout orders / Market paid orders:", tot['Заказы через чекаут']/4903)
print("sample AOV:", tot['GMV через чекаут, ₽']/tot['Заказы через чекаут'])
print("ad spend total sample:", tot['Траты на рекламу всего, ₽'], "payers", (b['Траты на рекламу всего, ₽']>0).sum())
print("subscribers quantiles:", b['Число подписчиков'].quantile([.1,.25,.5,.75,.9,.95,.99,1]).to_dict())
