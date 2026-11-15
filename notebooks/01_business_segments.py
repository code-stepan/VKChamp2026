# %% [markdown]
# # 01 · Сегментация бизнесов и воронка активации
#
# **Отвечает на вопросы кейса №2:** какие бизнесы целевые, что им нужно, что мешает расти.
# **Данные:** лист «Бизнесы», 9 754 сообщества × 30 дней (сентябрь 2026).
#
# ## Логика анализа
# 1. Воронка **подключения инструментов** (строгая вложенность) — где обрывается путь к продаже.
# 2. Разрыв **«подключил → продал»** — главный источник роста без привлечения новых бизнесов.
# 3. **Сценарная сегментация** по фактическому стеку, а не по declared-типу бизнеса.
# 4. Проверка **сопоставимости** сегментов (размер, каталог, активность) — иначе выводы ложные.
# 5. Приоритизация целевых сегментов и оценка «спящего» пула.
# 6. Отдельно — **реклама**: кто платит и получает ли результат.

# %%
import sys, warnings
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from vkcase import data, analysis as an, viz
from vkcase.config import VK, PARTNER, GOOD, BAD, GREY

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 60)
# %matplotlib inline

d = data.load_all()
b = an.add_scenario_segment(d["biz"])
N = len(b)
print(f"Сообществ: {N:,} | тематик: {b.theme.nunique()} | типов бизнеса: {b.btype.nunique()}")

# %% [markdown]
# ## 1. Вложенная воронка торгового стека
#
# Каждый шаг — подмножество предыдущего, поэтому конверсии шага интерпретируемы.

# %%
funnel = an.activation_funnel(b)
data.save_table(funnel, "01_activation_funnel")
viz.activation_funnel_plot(funnel)
funnel.assign(share_of_all=lambda x: (x.share_of_all * 100).round(2),
              step_conv=lambda x: (x.step_conv * 100).round(1))

# %% [markdown]
# **Читаем воронку:**
# * каталог есть у **40,6%** сообществ — это вход в товарную коммерцию;
# * из имеющих каталог **91,9%** подключают чекаут → сам чекаут **не является барьером**;
# * дальше обрыв: доставка только у **19,7%** имеющих чекаут, оплата — у **13,1%** имеющих доставку;
# * полный стек (каталог+чекаут+доставка+оплата) — **94 сообщества, меньше 1% выборки**.
#
# Гипотеза для стратегии: барьер не в «кнопке чекаута», а в **логистике и платежах**,
# то есть в исполнении заказа, а не в его оформлении.

# %%
pen = an.tool_penetration(b)
data.save_table(pen, "01_tool_penetration")
fig, ax = plt.subplots(figsize=(10, 5))
colors = {"инструмент": VK, "поведение": "#7B61FF", "монетизация": PARTNER, "результат": GOOD}
order = pen.sort_values("share_of_all")
ax.barh(order.indicator, order.share_of_all * 100,
        color=[colors[g] for g in order.group], height=0.7)
for i, (v, n) in enumerate(zip(order.share_of_all * 100, order.n)):
    ax.text(v, i, f"  {v:.1f}%  ({n:,})".replace(",", " "), va="center", fontsize=9)
ax.set_xlabel("доля от 9 754 сообществ, %")
ax.set_title("Проникновение инструментов, поведения и результата (шаги не вложенные)")
ax.margins(x=0.22)
fig.tight_layout(); viz.save(fig, "01_penetration")
pen.assign(share_of_all=lambda x: (x.share_of_all * 100).round(2))

# %% [markdown]
# ## 2. Ключевой разрыв: «подключил → продал»
#
# Это самая важная цифра всего анализа бизнесов.

# %%
chk = b[b.checkout == 1]
sellers = b[b.orders > 0]
gap = pd.DataFrame([
    ["Подключили чекаут", len(chk)],
    ["Из них сделали ≥1 заказ через чекаут", int(chk.has_order.sum())],
    ["Из них сделали ≥5 заказов", int((chk.orders >= 5).sum())],
    ["Подключили доставку", int((b.delivery == 1).sum())],
    ["Подключили оплату", int((b.payment == 1).sum())],
], columns=["шаг", "сообществ"])
gap["доля_от_чекаута"] = gap.сообществ / len(chk)
print(f"Чекаут подключён: {len(chk):,} сообществ")
print(f"Продают через него: {int(chk.has_order.sum()):,} ({chk.has_order.mean():.2%})")
print(f"«Спящих» (чекаут есть, заказов нет): {len(chk)-int(chk.has_order.sum()):,}")
data.save_table(gap, "01_activation_gap")
gap

# %% [markdown]
# > **Инсайт для слайда «Выявление проблематики».**
# > Инструменты подключены массово, но **94,8% подключивших чекаут не сделали ни одного заказа**.
# > Значит цель кейса «увеличить число бизнесов, продающих через ВКонтакте» решается
# > **не привлечением новых сообществ, а активацией уже подключённых**.
# > Это дешевле, быстрее и измеримо.

# %% [markdown]
# ## 3. Сценарные сегменты
#
# Сегментируем по **фактическому стеку** (что реально подключено), а не по типу бизнеса,
# потому что тип «товарное» ничего не говорит о готовности продавать внутри VK.

# %%
prof = an.segment_profile(b)
data.save_table(prof, "01_segment_profile")
show = prof[["segment", "n", "share_of_all", "subs_median", "sku_median", "prod_content_share",
             "sellers", "sell_rate", "orders_per_biz", "gmv_per_seller", "ad_spend"]].copy()
show["share_of_all"] = (show.share_of_all * 100).round(1)
show["prod_content_share"] = (show.prod_content_share * 100).round(1)
show["sell_rate"] = (show.sell_rate * 100).round(2)
show.columns = ["сегмент", "n", "% выборки", "медиана подписчиков", "медиана SKU",
                "% с товарным контентом", "продающих", "% продающих", "заказов/бизнес",
                "GMV на продавца, ₽", "реклама, ₽"]
show

# %%
viz.scatter_segment(prof)

# %% [markdown]
# **Как читать карту:** правее — чаще случается первая продажа, выше — больше заказов на сообщество,
# размер пузыря — размер сегмента.
#
# * **S4 «Каталог + чекаут»** — самый большой *товарный* сегмент (2 922), но продают лишь 5,3%.
#   Это основной «спящий» пул.
# * **S5 «+ доставка»** и **S6 «полный стек»** — продают в 3,2 раза чаще (≈17%), но это всего 719 сообществ.
# * **S2 «Чекаут без каталога»** (2 096) — аномалия данных: инструмент есть, продавать нечего.
# * **S0/S1** (услуги и контент без товаров, 3 697) — вне фокуса кейса (кейс просит сосредоточиться на товарах).

# %% [markdown]
# ### 3.1. Проверка сопоставимости: а не потому ли S5 продаёт чаще, что он просто крупнее?
#
# Требование кейса: *«сначала проверь, насколько группы сопоставимы»*.

# %%
combo = an.tool_combo_profile(b, only_catalog=True)
data.save_table(combo, "01_tool_combos")
combo_show = combo[combo.n >= 20].copy()
combo_show["sell_rate"] = (combo_show.sell_rate * 100).round(2)
combo_show["stack"] = combo_show.apply(
    lambda r: f"чекаут={int(r.checkout)}, доставка={int(r.delivery)}, оплата={int(r.payment)}", axis=1)
combo_show[["stack", "n", "subs_median", "sku_median", "views_median", "sellers", "sell_rate", "orders_per_biz"]]

# %% [markdown]
# **Важно:** сообщества с доставкой имеют медианный каталог **39 SKU против 9** у сообществ без доставки,
# и медиану подписчиков 1 000 против 640. Группы **несопоставимы по размеру ассортимента**.
# Поэтому «наивный» эффект доставки ×3,2 нельзя выносить на слайд как эффект инструмента —
# корректную оценку с сопоставлением (PSM) делаем в ноутбуке 02.

# %% [markdown]
# ## 4. Кто продаёт: размер, тематика, ассортимент
#
# Продажи крайне концентрированы — это меняет логику приоритизации.

# %%
size = b.groupby("size_band", observed=True).agg(
    n=("biz_id", "size"), catalog_share=("has_catalog", "mean"), checkout=("checkout", "mean"),
    delivery=("delivery", "mean"), sellers=("has_order", "sum"), orders=("orders", "sum"),
    gmv=("gmv", "sum"), ad_spend=("ad_spend", "sum"))
size["sell_rate"] = size.sellers / size.n
size["orders_per_biz"] = size.orders / size.n
data.save_table(size.reset_index(), "01_size_bands")
size.assign(catalog_share=lambda x: (x.catalog_share*100).round(1),
            checkout=lambda x: (x.checkout*100).round(1),
            delivery=lambda x: (x.delivery*100).round(1),
            sell_rate=lambda x: (x.sell_rate*100).round(2))

# %%
theme = b.groupby("theme").agg(
    n=("biz_id", "size"), catalog=("has_catalog", "mean"), checkout=("checkout", "mean"),
    delivery=("delivery", "mean"), sellers=("has_order", "sum"), orders=("orders", "sum"),
    gmv=("gmv", "sum"), ad_spend=("ad_spend", "sum"), subs_median=("subs", "median"))
theme["sell_rate"] = theme.sellers / theme.n
theme["aov"] = theme.gmv / theme.orders.replace(0, np.nan)
theme = theme[theme.n >= 100].sort_values("sell_rate", ascending=False)
data.save_table(theme.reset_index(), "01_themes")
viz.hbar(theme.reset_index().head(10), "theme", "sell_rate",
         "Топ-10 тематик по доле продающих сообществ (n ≥ 100)", "01_themes_sell_rate",
         color=VK, fmt="pct", xlabel="доля сообществ с ≥1 заказом")
theme.head(10).assign(sell_rate=lambda x: (x.sell_rate*100).round(2),
                      catalog=lambda x: (x.catalog*100).round(1))

# %%
gini_orders = an.gini(b.orders.values)
top10 = b.orders.nlargest(10).sum() / b.orders.sum()
top1pct = b.orders.nlargest(int(N * 0.01)).sum() / b.orders.sum()
print(f"Джини по заказам: {gini_orders:.3f}")
print(f"Топ-10 сообществ дают {top10:.1%} всех заказов выборки")
print(f"Топ-1% сообществ ({int(N*0.01)}) дают {top1pct:.1%} заказов")
print(f"Медиана заказов среди продающих: {b.loc[b.orders>0,'orders'].median():.0f}")

# %% [markdown]
# **Вывод:** 1% сообществ даёт 91% заказов. Стратегия «поднять всех» не работает —
# нужны **разные траектории**: (а) массовая активация первой продажи для длинного хвоста,
# (б) рост объёма для узкой группы уже продающих.

# %% [markdown]
# ## 5. Реклама: кто платит и получает ли результат
#
# Это прямой ответ на реплику Дмитрия в кейсе: *«сейчас мы зарабатываем прежде всего на рекламе…
# хотим, чтобы предприниматель получал результат и был готов платить»*.

# %%
ad_band = pd.cut(b.ad_spend, [-1, 0, 10_000, 100_000, 1_000_000, 1e12],
                 labels=["0 ₽", "1–10 тыс.", "10–100 тыс.", "100 тыс.–1 млн", ">1 млн"])
ad_band.name = "ad_band"  # иначе имя индекса совпадёт с агрегатом ad_spend при reset_index
ads = b.groupby(ad_band, observed=True).agg(
    n=("biz_id", "size"), sellers=("has_order", "sum"), orders=("orders", "sum"),
    gmv=("gmv", "sum"), ad_spend=("ad_spend", "sum"), subs_median=("subs", "median"),
    checkout=("checkout", "mean"), delivery=("delivery", "mean"))
ads["sell_rate"] = ads.sellers / ads.n
ads["gmv_per_ad_rub"] = ads.gmv / ads.ad_spend.replace(0, np.nan)
data.save_table(ads.reset_index(), "01_ad_bands")
ads.assign(sell_rate=lambda x: (x.sell_rate*100).round(2),
           checkout=lambda x: (x.checkout*100).round(1),
           delivery=lambda x: (x.delivery*100).round(1))

# %%
payers = b[b.ad_spend > 0]
no_order_payers = payers[payers.orders == 0]
print(f"Плательщиков рекламы: {len(payers)} ({len(payers)/N:.2%} выборки)")
print(f"Из них без единого заказа через чекаут: {len(no_order_payers)} ({len(no_order_payers)/len(payers):.1%})")
print(f"Их бюджет: {no_order_payers.ad_spend.sum():,.0f} ₽ ({no_order_payers.ad_spend.sum()/payers.ad_spend.sum():.1%} всех трат)")
ok = payers[payers.gmv > 0]
print(f"\nGMV через чекаут / траты на рекламу (плательщики с GMV>0, n={len(ok)}): {ok.gmv.sum()/ok.ad_spend.sum():.3f}")
print(f"Медианный ROAS по сообществам: {ok.roas.median():.3f}")
print("\n!!! Это НИЖНЯЯ оценка: продажи через сообщения и внешний сайт в данных не видны (см. ноутбук 00).")

# %% [markdown]
# > **Инсайт для слайда «Проблематика» и для монетизации.**
# > 92% рекламодателей выборки не получают ни одного *измеримого* заказа, и на них уходит 88% бюджета.
# > Даже если часть продаж происходит в сообщениях, **бизнес не видит связи «реклама → продажа»**,
# > а значит не будет наращивать бюджет. Реклама без замкнутой сделки — это тупик монетизации.
#
# Продуктовый вывод: сначала **«доделать сделку»** (чекаут → доставка → оплата → атрибуция),
# и только потом продавать трафик.

# %% [markdown]
# ## 6. Приоритизация целевых сегментов
#
# Скоринг = **потенциал** (сколько заказов может дать) × **готовность** (насколько близко к сделке)
# × **доступность рычага** (есть ли у нас инструмент, чтобы это изменить).
# Все компоненты считаем из данных, веса — экспертное допущение (прозрачно указано).

# %%
lev = {
    # segment: (рычаг, доля сегмента, достижимая sell_rate, источник оценки)
    "S4. Каталог + чекаут": ("Подключить доставку/оплату «в один клик» + шаблоны логистики", 0.35, None,
                             "уровень S5 с поправкой на self-selection (PSM, ноутбук 02)"),
    "S3. Витрина без чекаута": ("Включить чекаут по умолчанию для сообществ с каталогом", 0.50, None,
                                "переход на уровень S4"),
    "S2. Чекаут без каталога (аномалия)": ("Импорт каталога (Ozon/CSV/фото→карточка) + разбор аномалии", 0.25, None,
                                           "переход на уровень S4 после наполнения каталога"),
    "S5. Каталог + чекаут + доставка": ("Шопсы/контент + реклама на карточку, оплата внутри VK", 0.60, None,
                                        "рост объёма у уже продающих"),
    "S6. Полный стек (+оплата)": ("Масштабирование: реферальная программа, ретаргетинг, подписка", 0.80, None,
                                  "рост объёма"),
}
base = prof.set_index("segment")
s5_rate = base.loc["S5. Каталог + чекаут + доставка", "sell_rate"]
s4_rate = base.loc["S4. Каталог + чекаут", "sell_rate"]
rows = []
for seg, (lever, reach, _, src) in lev.items():
    r = base.loc[seg]
    target_rate = {"S4. Каталог + чекаут": s4_rate + 0.5 * (s5_rate - s4_rate),
                   "S3. Витрина без чекаута": s4_rate,
                   "S2. Чекаут без каталога (аномалия)": s4_rate,
                   "S5. Каталог + чекаут + доставка": r.sell_rate,
                   "S6. Полный стек (+оплата)": r.sell_rate}[seg]
    new_sellers = max(0.0, (target_rate - r.sell_rate)) * r.n * reach
    rows.append({"сегмент": seg, "n": int(r.n), "текущая доля продающих": r.sell_rate,
                 "рычаг": lever, "охват рычага": reach,
                 "целевая доля продающих": target_rate,
                 "новых продающих бизнесов": new_sellers,
                 "заказов/бизнес сейчас": r.orders_per_biz, "основание оценки": src})
prior = pd.DataFrame(rows).sort_values("новых продающих бизнесов", ascending=False)
data.save_table(prior, "01_target_priorities")
prior.assign(**{"текущая доля продающих": lambda x: (x["текущая доля продающих"]*100).round(2),
                "целевая доля продающих": lambda x: (x["целевая доля продающих"]*100).round(2),
                "охват рычага": lambda x: (x["охват рычага"]*100).round(0)})

# %%
print(f"Суммарный потенциал активации в выборке: +{prior['новых продающих бизнесов'].sum():,.0f} продающих сообществ")
print(f"Это +{prior['новых продающих бизнесов'].sum()/b.has_order.sum():.0%} к текущему числу продающих ({int(b.has_order.sum())})")
print("\nВажно: охват рычага — экспертное допущение, чувствительность считаем в ноутбуке 04.")

# %% [markdown]
# ## 7. Портреты целевых сегментов (для слайда «целевые бизнесы и их боли»)
#
# Собираем из данных то, что можно утверждать, и формулируем боли как гипотезы для проверки.

# %%
portrait = pd.DataFrame([
    ["S4 «Спящий магазин»", 2922, "каталог ~9 SKU, 665 подписчиков, чекаут есть, доставки нет",
     "хочет заказы без своего сайта и логистики",
     "не может исполнить заказ: доставка/оплата не подключены; карточка не ведёт к сделке",
     "доставка «из коробки» + оплата + автогенерация карточек; обучение в 3 шага"],
    ["S3 «Витрина-каталог»", 320, "каталог ~20 SKU, 1 300 подписчиков, чекаута нет",
     "показывать ассортимент и получать заявки",
     "сделка уходит в сообщения, потеря конверсии и учёта",
     "чекаут по умолчанию + шаблоны ответов с карточкой"],
    ["S2 «Пустой чекаут»", 2096, "чекаут подключён, каталог пуст, 280 подписчиков",
     "попробовать продажи без затрат",
     "нет наполненного каталога (барьер загрузки товаров)",
     "импорт каталога из маркетплейса/CSV, карточка из фото"],
    ["S5/S6 «Работающий продавец»", 719, "39–59 SKU, 1 000–1 250 подписчиков, доставка есть",
     "масштабировать заказы и повторные покупки",
     "мало нового трафика; товарный контент не даёт переходов в карточку",
     "шопсы + реклама на карточку + реферальная программа + оплата внутри VK"],
], columns=["сегмент", "n", "профиль из данных", "цель бизнеса", "барьер (гипотеза)", "что даём"])
data.save_table(portrait, "01_target_portraits")
portrait

# %%
data.save_key_numbers({
    "catalog_share": float(b.has_catalog.mean()),
    "checkout_share": float(b.checkout.mean()),
    "sellers_share": float(b.has_order.mean()),
    "checkout_to_seller_rate": float(b.loc[b.checkout == 1, "has_order"].mean()),
    "sleeping_checkout": int((b.checkout == 1).sum() - (b[b.checkout == 1].has_order).sum()),
    "s4_n": int(base.loc["S4. Каталог + чекаут", "n"]),
    "s4_sell_rate": float(s4_rate),
    "s5_sell_rate": float(s5_rate),
    "gini_orders": gini_orders,
    "top1pct_orders_share": float(top1pct),
    "ad_payers": int(len(payers)),
    "ad_payers_without_orders": int(len(no_order_payers)),
    "ad_budget_without_orders_share": float(no_order_payers.ad_spend.sum() / payers.ad_spend.sum()),
    "roas_lower_bound": float(ok.gmv.sum() / ok.ad_spend.sum()),
    "activation_potential_new_sellers": float(prior["новых продающих бизнесов"].sum()),
}, "01_segments")
b.to_csv(data.TABLES / "01_businesses_segmented.csv", index=False, encoding="utf-8-sig")
print("Сохранено: outputs/tables/01_*.csv")

# %% [markdown]
# ## Итоги ноутбука 01
#
# 1. **Барьер — не чекаут, а исполнение заказа.** Чекаут подключают 92% сообществ с каталогом,
#    доставку — 20% из них, оплату — 13% из имеющих доставку. Полный стек — <1% выборки.
# 2. **94,8% подключивших чекаут не продают.** Главный резерв роста — активация, а не привлечение.
# 3. **Сегменты несопоставимы по размеру каталога** (39 vs 9 SKU) → наивные сравнения завышают эффект инструментов.
# 4. **1% сообществ = 91% заказов** → нужны две разные траектории: «первая продажа» и «масштабирование».
# 5. **92% рекламодателей без измеримых заказов, 88% бюджета** → реклама без замкнутой сделки не удержит бизнес.
# 6. Приоритет №1 — **S4 «Спящий магазин»** (2 922 сообщества): ближе всего к сделке и самый большой товарный пул.
#
# **Дальше:** ноутбук 02 — контент и корректная оценка драйверов продаж.
