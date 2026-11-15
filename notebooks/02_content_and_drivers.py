# %% [markdown]
# # 02 · Контент и драйверы продаж: что действительно связано с заказом
#
# **Отвечает на вопросы кейса №2 и №3:** что мешает расти и какие инструменты дадут эффект.
# **Методологическое требование кейса:** *«Только сначала проверь, насколько группы сопоставимы.
# Нам нужны data-driven выводы, а не просто несколько красивых графиков»*.
#
# ## План
# 1. Товарный контент vs обычный: **парное сравнение внутри одного сообщества** (контроль размера аудитории).
# 2. Парадокс агрегата (эффект Симпсона) — почему «товарный контент хуже» верно и неверно одновременно.
# 3. Где рвётся контентная воронка: просмотр → открытие карточки.
# 4. **Логит** активации: odds ratios с доверительными интервалами.
# 5. **PSM** (сопоставление по propensity score): честная оценка «эффекта доставки».
# 6. **ML** (градиентный бустинг): что предсказывает продажу, важность признаков.
# 7. Что из этого — рычаг для продукта, а что — просто корреляция.

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

# %% [markdown]
# ## 1. Товарный контент: сколько его и что он даёт
#
# В кейсе Максим утверждает: *«Товарный контент распространяется хуже обычного»*.
# Проверяем это утверждение на данных, а не принимаем на веру.

# %%
overview = pd.DataFrame([
    ["Публикаций всего (посты + клипы)", b.content_all.sum()],
    ["Публикаций с товаром", b.content_prod.sum()],
    ["Просмотров обычного контента", b.views_reg.sum()],
    ["Просмотров товарного контента", b.views_prod.sum()],
    ["Сообществ, публикующих товарный контент", int((b.content_prod > 0).sum())],
    ["Сообществ с открытиями карточки из контента", int((b.card_opens > 0).sum())],
], columns=["показатель", "значение"])
overview["доля"] = [np.nan, b.content_prod.sum()/b.content_all.sum(), np.nan,
                    b.views_prod.sum()/b.views_all.sum(),
                    (b.content_prod > 0).mean(), (b.card_opens > 0).mean()]
data.save_table(overview, "02_content_overview")
overview

# %% [markdown]
# Товарный контент — **9% публикаций и 5,5% просмотров**. Уже отсюда видно,
# что в агрегате товарные публикации получают меньше просмотров на штуку.
# Но агрегат обманчив: его формируют крупные сообщества. Смотрим парно.

# %%
paired, st = an.content_paired(b)
paired_org, st_org = an.content_paired(b, organic_only=True)
res = pd.DataFrame([
    {"метрика": "Просмотров на публикацию: товарный", "все пары": st["vpp_prod_median"], "без рекламодателей": st_org["vpp_prod_median"]},
    {"метрика": "Просмотров на публикацию: обычный", "все пары": st["vpp_reg_median"], "без рекламодателей": st_org["vpp_reg_median"]},
    {"метрика": "Отношение (товарный / обычный), медиана пар", "все пары": st["vpp_ratio_median"], "без рекламодателей": st_org["vpp_ratio_median"]},
    {"метрика": "Доля пар, где товарный ХУЖЕ по охвату", "все пары": st["vpp_prod_worse_share"], "без рекламодателей": st_org["vpp_prod_worse_share"]},
    {"метрика": "ER (лайки+репосты)/просмотры: товарный", "все пары": st["er_prod_median"], "без рекламодателей": st_org["er_prod_median"]},
    {"метрика": "ER: обычный", "все пары": st["er_reg_median"], "без рекламодателей": st_org["er_reg_median"]},
    {"метрика": "Отношение ER (товарный / обычный), медиана пар", "все пары": st["er_ratio_median"], "без рекламодателей": st_org["er_ratio_median"]},
    {"метрика": "Доля пар, где товарный ХУЖЕ по вовлечению", "все пары": st["er_prod_worse_share"], "без рекламодателей": st_org["er_prod_worse_share"]},
])
data.save_table(res, "02_content_paired")
print(f"Пар в тесте: {st['n_paired']} (без рекламодателей: {st_org['n_paired']})")
print(f"Wilcoxon p (охват): {st['vpp_wilcoxon_p']:.2g} | (вовлечение): {st['er_wilcoxon_p']:.2g}")
res.round(4)

# %%
by_dec = st["by_decile"]
data.save_table(by_dec, "02_content_by_decile")
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
x = np.arange(len(by_dec)); w = 0.4
axes[0].bar(x - w/2, by_dec.vpp_prod, w, label="товарный", color=VK)
axes[0].bar(x + w/2, by_dec.vpp_reg, w, label="обычный", color=GREY)
axes[0].set_title("Просмотров на публикацию\n(медиана внутри дециля размера)")
axes[0].set_xlabel("дециль по числу подписчиков"); axes[0].legend()
axes[1].bar(x - w/2, by_dec.er_prod * 100, w, label="товарный", color=PARTNER)
axes[1].bar(x + w/2, by_dec.er_reg * 100, w, label="обычный", color=GREY)
axes[1].set_title("Engagement rate, %\n(медиана внутри дециля размера)")
axes[1].set_xlabel("дециль по числу подписчиков"); axes[1].legend()
fig.suptitle("Товарный контент: охват выше во всех децилях; вовлечение ниже — в 9 из 10", fontweight="bold", y=1.03)
fig.tight_layout(); viz.save(fig, "02_content_by_decile")
by_dec.round(4)

# %% [markdown]
# ### 2.1. Эффект Симпсона: почему агрегат и парный тест противоречат друг другу
#
# Это ровно тот случай, когда «красивый график» ведёт к неверному решению.

# %%
simpson = pd.DataFrame([
    ["Агрегат по всей выборке (взвешен крупными)", st["vpp_agg_prod"], st["vpp_agg_reg"],
     st["vpp_agg_prod"] / st["vpp_agg_reg"]],
    ["Медиана парных отношений (внутри сообщества)", st["vpp_prod_median"], st["vpp_reg_median"], st["vpp_ratio_median"]],
    ["Медиана парных отношений, только органика", st_org["vpp_prod_median"], st_org["vpp_reg_median"], st_org["vpp_ratio_median"]],
], columns=["способ расчёта", "просмотров/публикация: товарный", "просмотров/публикация: обычный", "отношение"])
data.save_table(simpson, "02_simpson")
simpson.round(3)

# %%
big = b[b.subs >= b.subs.quantile(0.99)]
small = b[b.subs < b.subs.quantile(0.99)]
print(f"Топ-1% по подписчикам: доля товарных публикаций {big.content_prod.sum()/big.content_all.sum():.2%}, "
      f"доля товарных просмотров {big.views_prod.sum()/big.views_all.sum():.2%}")
print(f"Остальные 99%: доля товарных публикаций {small.content_prod.sum()/small.content_all.sum():.2%}, "
      f"доля товарных просмотров {small.views_prod.sum()/small.views_all.sum():.2%}")

# %% [markdown]
# > **Вывод, который важно защитить перед жюри.**
# > Утверждение «товарный контент распространяется хуже» **не подтверждается на уровне сообщества**:
# > у одного и того же автора товарная публикация собирает **≈в 1,9 раза больше просмотров**,
# > и это устойчиво во всех децилях размера и без рекламодателей.
# > Но **вовлечение (ER) у товарного контента ниже примерно в 1,8 раза** (72,6% сообществ).
# >
# > Значит проблема не в «алгоритм не даёт охват», а в том, что **товарный контент хуже конвертирует
# > внимание в действие**. Рычаг — не «дать больше охвата», а **формат и CTA карточки в контенте**.

# %% [markdown]
# ## 3. Где рвётся контентная воронка
#
# Просмотр товарного контента → открытие карточки товара.

# %%
has_both = b[(b.views_prod > 0) & (b.card_opens > 0)]
ctr_agg = b.card_opens.sum() / b.views_prod.sum()
ctr_agg_valid = has_both.card_opens.sum() / has_both.views_prod.sum()
print(f"CTR карточки из товарного контента (агрегат по всем): {ctr_agg:.3%}")
print(f"CTR там, где есть и просмотры, и открытия (n={len(has_both)}): {ctr_agg_valid:.3%}")
print(f"Медианный CTR по сообществам с обоими событиями: {has_both.card_ctr.median():.3%}")
print(f"\nДля сравнения, платформенный CTR показ→открытие Маркета: {d['totals'].loc['Конверсия: показ → открытие карточки, %','Маркет Вконтакте']}%")
print(f"Платформенный CTR показ→открытие Партнёра: {d['totals'].loc['Конверсия: показ → открытие карточки, %','Партнёр 1']}%")

# %%
opens = b[b.card_opens > 0].copy()
opens["orders_per_1k_opens"] = 1000 * opens.orders / opens.card_opens
print(f"Сообществ с открытиями карточки из контента: {len(opens)}")
print(f"Из них с заказом: {int(opens.has_order.sum())} ({opens.has_order.mean():.1%})")
print(f"Заказов на 1000 открытий карточки (агрегат): {1000*opens.orders.sum()/opens.card_opens.sum():.2f}")
print(f"Медиана по сообществам: {opens.orders_per_1k_opens.median():.2f}")
data.save_table(opens[["biz_id", "theme", "segment", "views_prod", "card_opens", "card_ctr", "orders", "orders_per_1k_opens"]]
                .sort_values("card_opens", ascending=False), "02_content_to_card")
opens.nlargest(8, "card_opens")[["biz_id", "theme", "content_prod", "views_prod", "card_opens", "card_ctr", "orders"]]

# %% [markdown]
# **Ключевая цифра:** из контента в карточку переходит **менее 0,3%** просмотров товарного контента.
# Даже у сообществ, где открытия есть, медианный CTR — доли процента.
# При этом сообществ, которые вообще публикуют товарный контент, — **3,1%**.
#
# Два независимых рычага:
# 1. **Расширить использование шопсов** (сейчас 3% сообществ) — количественный рычаг.
# 2. **Поднять CTR карточки в контенте** — качественный рычаг (формат, цена/скидка в креативе, CTA, «купить в 1 клик»).

# %% [markdown]
# ## 4. Логит: что связано с фактом первой продажи
#
# Модель P(≥1 заказ) на подвыборке с каталогом (n≈3 961). Логарифмы — из-за сильной асимметрии.
#
# **Осторожно с интерпретацией `checkout`:** заказы у нас измеряются «через чекаут»,
# поэтому без чекаута заказ физически не может быть учтён. Коэффициент чекаута — **почти тавтология**,
# > а не эффект инструмента. Его нельзя использовать как аргумент «включим чекаут — вырастут продажи в 8 раз».

# %%
logit, info = an.logit_activation(b, only_catalog=True)
data.save_table(logit, "02_logit_activation")
print(f"n={info['n']}, базовая доля продающих={info['base_rate']:.2%}, pseudo-R²={info['pseudo_r2']:.3f}")
lg = logit[logit.feature != "const"].copy()
lg["значимость"] = np.where(lg.p_value < 0.01, "***", np.where(lg.p_value < 0.05, "**", np.where(lg.p_value < 0.1, "*", "нет")))
lg[["feature", "odds_ratio", "ci_low", "ci_high", "p_value", "значимость"]].round(3)

# %%
fig, ax = plt.subplots(figsize=(9, 4.6))
plot_df = lg.sort_values("odds_ratio")
colors = [GREY if f == "checkout" else (GOOD if o > 1 else BAD) for f, o in zip(plot_df.feature, plot_df.odds_ratio)]
ax.errorbar(plot_df.odds_ratio, np.arange(len(plot_df)),
            xerr=[plot_df.odds_ratio - plot_df.ci_low, plot_df.ci_high - plot_df.odds_ratio],
            fmt="o", color=VK, ecolor="#B9C6DA", capsize=3, ms=5)
ax.scatter(plot_df.odds_ratio, np.arange(len(plot_df)), c=colors, s=45, zorder=3)
ax.axvline(1, color=BAD, ls="--", lw=1)
ax.set_yticks(np.arange(len(plot_df)), plot_df.feature)
ax.set_xscale("log")
ax.set_xlabel("odds ratio (лог. шкала), 95% ДИ")
ax.set_title("Логит P(≥1 заказ): размер каталога и охват важнее самой «кнопки»\n(серый = checkout, коэффициент тавтологичен)")
fig.tight_layout(); viz.save(fig, "02_logit_forest")

# %% [markdown]
# **Что читаем:**
# * `log_sku` OR≈1,52 — **ассортимент** самый сильный содержательный предиктор: рост каталога в e раз
#   повышает шансы продажи примерно в 1,5 раза;
# * `log_views_reg` OR≈1,45 — важен **общий охват сообщества**, а не только товарный;
# * `log_content` OR≈0,81 — при фиксированном охвате **больше публикаций = ниже шансы**:
#   количество постов без качества размывает охват;
# * `delivery` OR≈1,59 (p<0,01) — доставка значима, но эффект в разы меньше «наивного» ×3,2;
# * `log_ad_spend` OR≈1,02 (p=0,31) — **траты на рекламу статистически не связаны** с фактом продажи;
# * `referral`, `payment` — незначимы (мало наблюдений: рефералка у 2%, оплата у 2,6%).

# %%
ols, ols_info = an.ols_order_volume(b)
data.save_table(ols, "02_ols_order_volume")
print(f"OLS log1p(orders), n={ols_info['n']}, R²={ols_info['r2']:.3f} (HC3-робастные ошибки)")
ols[ols.feature != "const"].assign(эффект_процентов=lambda x: (np.exp(x.coef)-1)*100).round(3)

# %% [markdown]
# ## 5. PSM: честная оценка «эффекта доставки»
#
# Наивное сравнение: сообщества с доставкой продают в 3,2 раза чаще.
# Но у них в 4 раза больше каталог. Сопоставляем **похожие** сообщества по propensity score
# (размер, каталог, активность, охват, товарный контент, реклама), 1:1, с калипером.

# %%
psm = an.psm_effect(b, treatment="delivery", restrict={"checkout": 1}, n_boot=400)
print(f"Леченых (доставка есть): {psm['n_treated']} | пул контроля: {psm['n_control_pool']} | сопоставленных пар: {psm['n_matched_pairs']}")
data.save_table(psm["effects"], "02_psm_delivery_effects")
data.save_table(psm["balance"], "02_psm_delivery_balance")
psm["effects"].round(3)

# %%
bal = psm["balance"]
fig, ax = plt.subplots(figsize=(8.5, 4))
y = np.arange(len(bal))
ax.scatter(bal.SMD_before, y, label="до сопоставления", color=BAD, s=60, zorder=3)
ax.scatter(bal.SMD_after, y, label="после сопоставления", color=GOOD, s=60, zorder=3)
for i, (a, bb) in enumerate(zip(bal.SMD_before, bal.SMD_after)):
    ax.plot([a, bb], [i, i], color="#C9D2E0", lw=1.5, zorder=2)
ax.axvline(0.1, color=GREY, ls="--", lw=1); ax.axvline(-0.1, color=GREY, ls="--", lw=1)
ax.axvline(0, color="#1F2733", lw=0.8)
ax.set_yticks(y, bal.feature)
ax.set_xlabel("стандартизованная разница средних (SMD); |SMD|>0,1 — группы несопоставимы")
ax.set_title("Баланс ковариат: наивное сравнение было смещённым")
ax.legend()
fig.tight_layout(); viz.save(fig, "02_psm_balance")
bal.round(3)

# %%
eff = psm["effects"].set_index("outcome")
sr = eff.loc["sell_rate"]
print(f"Доля продающих: наивно {sr.treated_naive:.1%} vs {sr.control_naive:.1%} (×{sr.naive_ratio:.2f})")
print(f"После сопоставления: {sr.treated_matched:.1%} vs {sr.control_matched:.1%} (×{sr.matched_ratio:.2f})")
print(f"ATT = {sr.ATT*100:+.2f} п.п., 95% ДИ [{sr.ATT_ci_low*100:+.2f}; {sr.ATT_ci_high*100:+.2f}] п.п.")
print(f"Заказов на сообщество: ATT = {eff.loc['orders_per_biz','ATT']:+.2f} "
      f"(ДИ [{eff.loc['orders_per_biz','ATT_ci_low']:+.2f}; {eff.loc['orders_per_biz','ATT_ci_high']:+.2f}])")

# %% [markdown]
# > **Главный методологический вывод кейса.**
# > Наивный «эффект доставки» ×3,2 **на 3/4 объясняется размером каталога и аудитории**.
# > После сопоставления остаётся ≈×1,2 по вероятности первой продажи, и доверительный интервал
# > ATT включает ноль → **эффект направления положительный, но статистически не доказан**.
# > По объёму заказов эффекта не видно вовсе.
# >
# > Что это значит для решения: **подключение доставки — необходимое, но недостаточное условие**.
# > Нельзя обещать жюри «подключим доставку — продажи вырастут втрое». Правильная формулировка:
# > «доставка снимает барьер исполнения заказа; ожидаемый прирост активации — единицы процентных пунктов,
# > проверяем A/B-тестом на пилоте».

# %% [markdown]
# ## 6. ML: что предсказывает продажу (важность ≠ причинность)
#
# Градиентный бустинг, 5-fold кросс-валидация. Метрики для несбалансированного таргета:
# ROC-AUC и **average precision** (базовая доля продающих ≈7%).

# %%
ml = an.ml_drivers(b, only_catalog=True)
print(f"n={ml['n']} | ROC-AUC={ml['auc']:.3f} | Average Precision={ml['ap']:.3f} (база {ml['base_rate']:.3f})")
data.save_table(ml["importance"], "02_ml_importance")
viz.hbar(ml["importance"].head(10), "feature", "importance",
         "Важность признаков для прогноза продажи (permutation, AP)", "02_ml_importance",
         color=VK, xlabel="прирост average precision при перемешивании признака")
ml["importance"].head(10).round(4)

# %% [markdown]
# Модель уверенно отделяет продающие сообщества (AUC≈0,84), и топ-признаки — **ассортимент,
# охват, цена товара, размер аудитории**. Инструменты (`checkout`, `delivery`) дают меньший вклад,
# чем «есть что продавать и кому показать». Это согласуется с логитом и PSM.

# %% [markdown]
# ## 7. Свод: рычаг → доказательство → ожидаемый эффект → как проверить
#
# Именно эту таблицу стоит вынести в приложение к презентации.

# %%
levers = pd.DataFrame([
    ["Наполнение каталога (импорт из маркетплейса, карточка из фото)",
     "log_sku OR≈1,52 (p<0,001); топ-1 важность в ML; у продающих медиана каталога в 4 раза выше",
     "рост вероятности первой продажи; сильнее всего у S2/S4",
     "A/B: автоимпорт каталога при онбординге; метрика — доля сообществ с ≥1 заказом за 30 дней"],
    ["Доставка «из коробки» + оплата внутри VK",
     "наивно ×3,2 → PSM ×1,2 (ATT +3 п.п., ДИ включает 0); логит OR≈1,59 (p<0,01)",
     "снятие барьера исполнения; единицы п.п. активации",
     "A/B на S4: дефолтная доставка vs текущий сценарий; метрики — активация, заказы, отмены"],
    ["Шопсы: товарные карточки в постах/клипах",
     "товарный контент публикуют 3,1%; CTR в карточку <0,3%; ER товарного контента ниже в 1,8 раза",
     "новый интентный трафик в карточку; сейчас почти не используется",
     "A/B формата креатива (цена/скидка/CTA); метрика — CTR просмотр→карточка и заказ/1000 открытий"],
    ["Реклама на карточку товара (вместо рекламы сообщества)",
     "log_ad_spend OR≈1,02 (p=0,31); 92% плательщиков без измеримых заказов",
     "перераспределение бюджета в измеримый результат; удержание рекламодателя",
     "A/B: цель кампании «заказ в чекауте» vs «охват»; метрика — ROAS и retention бюджета"],
    ["Реферальная программа / авторы",
     "в выборке участвуют 2%, значимого эффекта нет (мало данных); на платформе 94,8% открытий Партнёра — реферальные",
     "потенциально большой канал, но в выборке не проверяем",
     "пилот с 200 авторами; метрика — заказы на 1000 открытий и стоимость привлечённого заказа"],
], columns=["рычаг", "доказательство из данных", "ожидаемый эффект", "как проверяем"])
data.save_table(levers, "02_levers_evidence")
levers

# %%
data.save_key_numbers({
    "prod_content_share_of_posts": float(b.content_prod.sum() / b.content_all.sum()),
    "prod_content_share_of_views": float(b.views_prod.sum() / b.views_all.sum()),
    "prod_content_users_share": float((b.content_prod > 0).mean()),
    "paired_n": st["n_paired"],
    "vpp_ratio_paired": st["vpp_ratio_median"],
    "er_ratio_paired": st["er_ratio_median"],
    "er_prod_worse_share": st["er_prod_worse_share"],
    "vpp_ratio_aggregate": st["vpp_agg_prod"] / st["vpp_agg_reg"],
    "card_ctr_from_content": float(ctr_agg),
    "logit_or_sku": float(logit.set_index("feature").loc["log_sku", "odds_ratio"]),
    "logit_or_delivery": float(logit.set_index("feature").loc["delivery", "odds_ratio"]),
    "logit_or_ads": float(logit.set_index("feature").loc["log_ad_spend", "odds_ratio"]),
    "psm_naive_ratio": float(sr.naive_ratio),
    "psm_matched_ratio": float(sr.matched_ratio),
    "psm_att_pp": float(sr.ATT * 100),
    "psm_att_ci_low_pp": float(sr.ATT_ci_low * 100),
    "psm_att_ci_high_pp": float(sr.ATT_ci_high * 100),
    "ml_auc": ml["auc"], "ml_ap": ml["ap"],
}, "02_drivers")
print("Сохранено: outputs/tables/02_*.csv")

# %% [markdown]
# ## Итоги ноутбука 02
#
# 1. **Гипотеза кейса о «плохом охвате товарного контента» не подтверждается**: парно охват выше в ≈1,9 раза.
#    Ниже **вовлечение** (в ≈1,8 раза) и **CTR в карточку** (<0,3%) — вот настоящая проблема.
# 2. Агрегат показывает обратное (×0,64) — **эффект Симпсона**, обязательно оговаривать.
# 3. **Ассортимент и охват** — сильнейшие предикторы продажи; количество постов при том же охвате — отрицательно.
# 4. **Эффект доставки после сопоставления ≈×1,2, а не ×3,2**; ДИ включает ноль → обещать «втрое» нельзя.
# 5. **Реклама не связана с фактом продажи** (OR≈1,02, p=0,31) → продукт должен замкнуть сделку до продажи трафика.
# 6. ML подтверждает: AUC≈0,84, топ-признаки — каталог, охват, цена.
#
# **Дальше:** ноутбук 03 — Маркет ВКонтакте vs Партнёр: где теряется покупатель.
