"""Аналитические функции: воронки, сегментация, сопоставимость групп, эффекты.

Методологическая рамка кейса («сначала проверь, насколько группы сопоставимы»):
* наивные сравнения групп всегда сопровождаем сопоставимостью (SMD) и
  скорректированной оценкой (логит / PSM / стратификация);
* причинность не заявляем: данные наблюдательные, инструменты подключают
  более «серьёзные» продавцы (self-selection).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SEG_ORDER

RNG = 42


# --------------------------------------------------------------------------
# 1. Воронка подключения инструментов и продаж
# --------------------------------------------------------------------------
def activation_funnel(b: pd.DataFrame) -> pd.DataFrame:
    """Строго вложенная воронка торгового стека.

    Каждый следующий шаг — подмножество предыдущего, поэтому step_conv
    корректно интерпретируется как конверсия шага.
    """
    n = len(b)
    cat = b.sku_active > 0
    chk = cat & (b.checkout == 1)
    dlv = chk & (b.delivery == 1)
    pay = dlv & (b.payment == 1)
    steps = [
        ("Бизнес-сообщество в выборке", n),
        ("Активный каталог (≥1 товар)", int(cat.sum())),
        ("+ подключён чекаут", int(chk.sum())),
        ("+ подключена доставка", int(dlv.sum())),
        ("+ подключена оплата (полный стек)", int(pay.sum())),
    ]
    f = pd.DataFrame(steps, columns=["step", "n"])
    f["share_of_all"] = f["n"] / n
    f["step_conv"] = f["n"] / f["n"].shift(1)
    return f


def tool_penetration(b: pd.DataFrame) -> pd.DataFrame:
    """Проникновение инструментов и результатов. Шаги НЕ вложенные.

    Важно: чекаут встречается чаще каталога — это логическая аномалия данных,
    а не «отрицательный отток» (см. ноутбук 00).
    """
    n = len(b)
    rows = [
        ("Товары загружены (sku_uploaded > 0)", int((b.sku_uploaded > 0).sum()), "инструмент"),
        ("Активный каталог (sku_active > 0)", int((b.sku_active > 0).sum()), "инструмент"),
        ("Подключён чекаут", int((b.checkout == 1).sum()), "инструмент"),
        ("Подключена доставка", int((b.delivery == 1).sum()), "инструмент"),
        ("Подключена оплата", int((b.payment == 1).sum()), "инструмент"),
        ("Публикует товарный контент", int((b.content_prod > 0).sum()), "поведение"),
        ("Есть открытия карточки из контента", int((b.card_opens > 0).sum()), "поведение"),
        ("Платит за рекламу", int((b.ad_spend > 0).sum()), "монетизация"),
        ("Участвует в реферальной программе", int((b.referral == 1).sum()), "монетизация"),
        ("≥1 заказ через чекаут", int((b.orders > 0).sum()), "результат"),
        ("≥5 заказов через чекаут", int((b.orders >= 5).sum()), "результат"),
    ]
    f = pd.DataFrame(rows, columns=["indicator", "n", "group"])
    f["share_of_all"] = f["n"] / n
    return f


def add_scenario_segment(b: pd.DataFrame) -> pd.DataFrame:
    """Сценарная сегментация по фактически используемым инструментам.

    Логика: сначала «полнота торгового стека», затем тип бизнеса.
    Сегменты взаимоисключающие, вместе покрывают 100% выборки.
    """
    b = b.copy()
    cond = [
        (b.sku_active > 0) & (b.checkout == 1) & (b.delivery == 1) & (b.payment == 1),
        (b.sku_active > 0) & (b.checkout == 1) & (b.delivery == 1),
        (b.sku_active > 0) & (b.checkout == 1),
        (b.sku_active > 0),
        (b.checkout == 1),
        (b.btype == "услужное"),
    ]
    choices = [SEG_ORDER[6], SEG_ORDER[5], SEG_ORDER[4],
               SEG_ORDER[3], SEG_ORDER[2], SEG_ORDER[0]]
    b["segment"] = np.select(cond, choices, default=SEG_ORDER[1])
    b["segment"] = pd.Categorical(b["segment"], categories=SEG_ORDER, ordered=True)
    return b


def segment_profile(b: pd.DataFrame) -> pd.DataFrame:
    """Профиль сегментов: размер, активность, продажи, реклама, эффективность."""
    g = b.groupby("segment", observed=True).agg(
        n=("biz_id", "size"),
        subs_median=("subs", "median"),
        sku_median=("sku_active", "median"),
        content_median=("content_all", "median"),
        prod_content_share=("has_prod_content", "mean"),
        card_opens=("card_opens", "sum"),
        sellers=("has_order", "sum"),
        orders=("orders", "sum"),
        gmv=("gmv", "sum"),
        ad_spend=("ad_spend", "sum"),
        ad_payers=("pays_ads", "sum"),
    )
    g["share_of_all"] = g["n"] / g["n"].sum()
    g["sell_rate"] = g["sellers"] / g["n"]
    g["orders_per_biz"] = g["orders"] / g["n"]
    g["orders_per_seller"] = g["orders"] / g["sellers"].replace(0, np.nan)
    g["gmv_per_seller"] = g["gmv"] / g["sellers"].replace(0, np.nan)
    g["aov"] = g["gmv"] / g["orders"].replace(0, np.nan)
    g["roas_gmv_per_ad_rub"] = g["gmv"] / g["ad_spend"].replace(0, np.nan)
    return g.reset_index()


def tool_combo_profile(b: pd.DataFrame, only_catalog: bool = True) -> pd.DataFrame:
    """Продажи по комбинациям инструментов (для проверки сопоставимости)."""
    d = b[b.sku_active > 0] if only_catalog else b
    g = d.groupby(["checkout", "delivery", "payment"], observed=True).agg(
        n=("biz_id", "size"), sellers=("has_order", "sum"), orders=("orders", "sum"),
        gmv=("gmv", "sum"), subs_median=("subs", "median"), sku_median=("sku_active", "median"),
        views_median=("views_reg", "median"), ad_spend=("ad_spend", "sum"),
    )
    g["sell_rate"] = g["sellers"] / g["n"]
    g["orders_per_biz"] = g["orders"] / g["n"]
    return g.reset_index()


# --------------------------------------------------------------------------
# 2. Контент: товарный vs обычный (парное сравнение внутри бизнеса)
# --------------------------------------------------------------------------
def content_paired(b: pd.DataFrame, organic_only: bool = False) -> tuple[pd.DataFrame, dict]:
    """Парное сравнение товарного и обычного контента внутри одного сообщества.

    Парность убирает главный конфаундер — размер аудитории: сравниваем
    бизнес сам с собой. Дополнительно можно исключить рекламодателей.
    """
    d = b[(b.views_prod > 0) & (b.views_reg > 0) & (b.content_prod > 0) & (b.content_all > 0)].copy()
    if organic_only:
        d = d[d.ad_spend == 0]
    d["vpp_ratio"] = d["vpp_prod"] / d["vpp_reg"]
    d["er_ratio"] = d["er_prod"] / d["er_reg"].replace(0, np.nan)
    stats = {
        "n_paired": len(d),
        "vpp_prod_median": d.vpp_prod.median(),
        "vpp_reg_median": d.vpp_reg.median(),
        "vpp_ratio_median": d.vpp_ratio.median(),
        "vpp_prod_worse_share": (d.vpp_ratio < 1).mean(),
        "er_prod_median": d.er_prod.median(),
        "er_reg_median": d.er_reg.median(),
        "er_ratio_median": d.er_ratio.median(),
        "er_prod_worse_share": (d.er_ratio < 1).mean(),
        "card_ctr_agg": b.card_opens.sum() / b.views_prod.sum(),
        "vpp_agg_prod": b.views_prod.sum() / b.content_prod.sum(),
        "vpp_agg_reg": b.views_reg.sum() / b.content_all.sum(),
    }
    # знаковый тест (Wilcoxon) — устойчив к выбросам
    from scipy.stats import wilcoxon
    for key, col in [("vpp", "vpp_ratio"), ("er", "er_ratio")]:
        x = d[col].dropna()
        x = x[np.isfinite(x)]
        try:
            stats[f"{key}_wilcoxon_p"] = float(wilcoxon(np.log(x)).pvalue)
        except Exception:
            stats[f"{key}_wilcoxon_p"] = np.nan
    d["size_decile"] = pd.qcut(d["subs"], 10, labels=False, duplicates="drop") + 1
    by_dec = d.groupby("size_decile", observed=True).agg(
        n=("biz_id", "size"), subs_median=("subs", "median"),
        vpp_prod=("vpp_prod", "median"), vpp_reg=("vpp_reg", "median"),
        er_prod=("er_prod", "median"), er_reg=("er_reg", "median"),
        card_ctr=("card_ctr", "median"),
    ).reset_index()
    by_dec["vpp_ratio"] = by_dec.vpp_prod / by_dec.vpp_reg
    by_dec["er_ratio"] = by_dec.er_prod / by_dec.er_reg
    stats["by_decile"] = by_dec
    return d, stats


# --------------------------------------------------------------------------
# 3. Драйверы активации: логит, PSM, ML
# --------------------------------------------------------------------------
def _design(b: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "log_subs": np.log1p(b.subs),
        "log_sku": np.log1p(b.sku_active),
        "log_content": np.log1p(b.content_all),
        "log_views_reg": np.log1p(b.views_reg),
        "has_prod_content": b.has_prod_content,
        "checkout": b.checkout,
        "delivery": b.delivery,
        "payment": b.payment,
        "log_ad_spend": np.log1p(b.ad_spend),
        "referral": b.referral,
    }, index=b.index)


def logit_activation(b: pd.DataFrame, only_catalog: bool = True) -> tuple[pd.DataFrame, dict]:
    """Логит P(≥1 заказ). Возвращает odds ratios с 95% ДИ.

    ВНИМАНИЕ: `checkout` — почти тавтология (заказы измеряются «через чекаут»),
    её коэффициент нельзя трактовать как эффект инструмента.
    """
    import statsmodels.api as sm
    d = b[b.sku_active > 0] if only_catalog else b
    X = sm.add_constant(_design(d))
    m = sm.Logit(d.has_order, X).fit(disp=0)
    ci = m.conf_int()
    res = pd.DataFrame({
        "coef": m.params, "odds_ratio": np.exp(m.params),
        "ci_low": np.exp(ci[0]), "ci_high": np.exp(ci[1]), "p_value": m.pvalues,
    }).reset_index(names="feature")
    info = {"n": int(m.nobs), "pseudo_r2": float(m.prsquared),
            "base_rate": float(d.has_order.mean()), "llf": float(m.llf)}
    return res, info


def ols_order_volume(b: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """OLS по log1p(orders) на подвыборке с каталогом: полуэластичности объёма."""
    import statsmodels.api as sm
    d = b[b.sku_active > 0].copy()
    X = sm.add_constant(_design(d))
    m = sm.OLS(np.log1p(d.orders), X).fit(cov_type="HC3")
    ci = m.conf_int()
    res = pd.DataFrame({"coef": m.params, "ci_low": ci[0], "ci_high": ci[1],
                        "p_value": m.pvalues}).reset_index(names="feature")
    return res, {"n": int(m.nobs), "r2": float(m.rsquared)}


def _smd(t: pd.Series, c: pd.Series) -> float:
    """Стандартизованная разница средних (|SMD|>0.1 — группы несопоставимы)."""
    s = np.sqrt((t.var(ddof=1) + c.var(ddof=1)) / 2)
    return float((t.mean() - c.mean()) / s) if s > 0 else 0.0


def psm_effect(b: pd.DataFrame, treatment: str = "delivery",
               restrict: dict | None = None, n_boot: int = 300,
               caliper_mult: float = 0.2) -> dict:
    """Propensity score matching 1:1 (ближайший сосед, с возвращением).

    caliper_mult — ширина калипера в SD логита propensity score (по умолчанию 0,2).
    Оценка ATT по трём исходам: активация (≥1 заказ), заказы, GMV.
    Возвращает наивную и скорректированную оценки + баланс ковариат.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import NearestNeighbors
    from sklearn.preprocessing import StandardScaler

    d = b[b.sku_active > 0].copy()
    if restrict:
        for k, v in restrict.items():
            d = d[d[k] == v]
    feats = pd.DataFrame({
        "log_subs": np.log1p(d.subs), "log_sku": np.log1p(d.sku_active),
        "log_content": np.log1p(d.content_all), "log_views_reg": np.log1p(d.views_reg),
        "has_prod_content": d.has_prod_content, "log_ad_spend": np.log1p(d.ad_spend),
    }, index=d.index)
    d = d.drop(columns=[c for c in feats.columns if c in d.columns]).join(feats)
    sc = StandardScaler().fit(feats)
    Z = sc.transform(feats)
    ps = LogisticRegression(max_iter=2000, C=1.0).fit(Z, d[treatment]).predict_proba(Z)[:, 1]
    d["_ps"] = ps
    logit_ps = np.log(np.clip(ps, 1e-6, 1 - 1e-6) / (1 - np.clip(ps, 1e-6, 1 - 1e-6)))
    d["_lps"] = logit_ps

    tr, ct = d[d[treatment] == 1], d[d[treatment] == 0]
    nn = NearestNeighbors(n_neighbors=1).fit(ct[["_lps"]].values)
    dist, idx = nn.kneighbors(tr[["_lps"]].values)
    caliper = caliper_mult * np.std(logit_ps)
    keep = dist[:, 0] <= caliper
    matched = ct.iloc[idx[keep, 0]]
    tr_k = tr.iloc[np.where(keep)[0]]

    outcomes = {"sell_rate": "has_order", "orders_per_biz": "orders", "gmv_per_biz": "gmv"}
    rows = []
    for name, col in outcomes.items():
        naive_t, naive_c = tr[col].mean(), ct[col].mean()
        att = tr_k[col].mean() - matched[col].mean()
        rng = np.random.default_rng(RNG)
        boots = []
        for _ in range(n_boot):
            ii = rng.integers(0, len(tr_k), len(tr_k))
            boots.append(tr_k[col].values[ii].mean() - matched[col].values[ii].mean())
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append({
            "outcome": name, "treated_naive": naive_t, "control_naive": naive_c,
            "naive_ratio": naive_t / naive_c if naive_c else np.nan,
            "treated_matched": tr_k[col].mean(), "control_matched": matched[col].mean(),
            "ATT": att, "ATT_ci_low": lo, "ATT_ci_high": hi,
            "matched_ratio": tr_k[col].mean() / matched[col].mean() if matched[col].mean() else np.nan,
        })
    balance = pd.DataFrame([
        {"feature": f, "SMD_before": _smd(tr[f], ct[f]), "SMD_after": _smd(tr_k[f], matched[f])}
        for f in feats.columns
    ])
    return {"effects": pd.DataFrame(rows), "balance": balance,
            "n_treated": len(tr), "n_control_pool": len(ct), "n_matched_pairs": len(tr_k),
            "caliper": float(caliper)}


def ml_drivers(b: pd.DataFrame, only_catalog: bool = True) -> dict:
    """Градиентный бустинг + permutation importance (важность для прогноза, не эффект)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    d = b[b.sku_active > 0] if only_catalog else b
    X = pd.DataFrame({
        "log_subs": np.log1p(d.subs), "log_sku": np.log1p(d.sku_active),
        "log_content": np.log1p(d.content_all), "log_views_reg": np.log1p(d.views_reg),
        "log_views_prod": np.log1p(d.views_prod), "log_card_opens": np.log1p(d.card_opens),
        "has_prod_content": d.has_prod_content, "checkout": d.checkout,
        "delivery": d.delivery, "payment": d.payment,
        "log_ad_spend": np.log1p(d.ad_spend), "referral": d.referral,
        "orig_author": d.orig_author.fillna(-1), "er_reg": d.er_reg.fillna(0),
        "price_median": np.log1p(d.price_median.fillna(0)),
    }, index=d.index)
    y = d.has_order
    model = HistGradientBoostingClassifier(max_depth=3, max_iter=200, random_state=RNG)
    cv = StratifiedKFold(5, shuffle=True, random_state=RNG)
    pred = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
    model.fit(X, y)
    pi = permutation_importance(model, X, y, n_repeats=10, random_state=RNG, scoring="average_precision")
    imp = pd.DataFrame({"feature": X.columns, "importance": pi.importances_mean,
                        "std": pi.importances_std}).sort_values("importance", ascending=False)
    return {"auc": float(roc_auc_score(y, pred)), "ap": float(average_precision_score(y, pred)),
            "base_rate": float(y.mean()), "n": len(d), "importance": imp, "model": model, "X": X}


# --------------------------------------------------------------------------
# 4. Воронка Маркета и Партнёра
# --------------------------------------------------------------------------
def funnel_table(totals: pd.DataFrame) -> pd.DataFrame:
    """Пошаговая воронка для Маркета ВКонтакте и Партнёра 1 из листа «итоги»."""
    num = lambda m, c: float(pd.to_numeric(pd.Series([totals.loc[m, c]]), errors="coerce").iloc[0])
    rows = []
    for col, name in [("Маркет Вконтакте", "Маркет ВКонтакте"), ("Партнёр 1", "Партнёр 1")]:
        imp = num("Показы товаров", col)
        op = num("Открытия карточки товара", col)
        cl = num("Нажатия на кнопку в карточке", col)
        od = num("Оформленные заказы", col)
        gm = num("GMV, ₽", col)
        by = num("Уникальные покупатели за 30 дней", col)
        rows.append({
            "segment": name, "impressions": imp, "card_opens": op, "button_clicks": cl,
            "orders": od, "gmv": gm, "buyers": by,
            "ctr_impression_to_open": op / imp, "click_rate_open_to_click": cl / op,
            "click_to_order": od / cl, "conv_open_to_order": od / op,
            "conv_impression_to_order": od / imp, "aov": gm / od,
            "gmv_per_1k_impressions": gm / imp * 1000, "orders_per_buyer": od / by,
        })
    return pd.DataFrame(rows)


def gap_decomposition(f: pd.DataFrame) -> pd.DataFrame:
    """Лог-декомпозиция разрыва по заказам:orders = imp × CTR × click_rate × click2order.

    Вклад шага = ln(ratio шага) / ln(итогового ratio). Сумма вкладов = 100%.
    """
    vk = f[f.segment == "Маркет ВКонтакте"].iloc[0]
    pt = f[f.segment == "Партнёр 1"].iloc[0]
    total = np.log(pt.orders / vk.orders)
    steps = [
        ("Показы товаров (объём трафика)", pt.impressions / vk.impressions),
        ("Показ → открытие карточки (CTR)", pt.ctr_impression_to_open / vk.ctr_impression_to_open),
        ("Открытие → нажатие кнопки", pt.click_rate_open_to_click / vk.click_rate_open_to_click),
        ("Нажатие → заказ", pt.click_to_order / vk.click_to_order),
    ]
    out = pd.DataFrame(steps, columns=["step", "ratio_pt_vs_vk"])
    out["log_contribution"] = np.log(out.ratio_pt_vs_vk) / total
    out.attrs["total_orders_ratio"] = float(pt.orders / vk.orders)
    return out


# --------------------------------------------------------------------------
# 5. Прочее
# --------------------------------------------------------------------------
def gini(x: np.ndarray) -> float:
    """Коэффициент Джини (концентрация заказов/выручки)."""
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return np.nan
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def hhi(shares: pd.Series) -> float:
    """Индекс Херфиндаля—Хиршмана по долям (0…1)."""
    s = shares.dropna()
    return float((s ** 2).sum())


def trend(d: pd.DataFrame, col: str) -> dict:
    """Линейный тренд: наклон/день, изменение последних 7 дней к первым 7, p-value."""
    from scipy.stats import linregress
    y = d[col].to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    lr = linregress(x, y)
    return {"metric": col, "first7_avg": y[:7].mean(), "last7_avg": y[-7:].mean(),
            "change_pct": y[-7:].mean() / y[:7].mean() - 1,
            "slope_per_day": lr.slope, "r2": lr.rvalue ** 2, "p_value": lr.pvalue}


def cosine(a: pd.Series, b: pd.Series) -> float:
    """Косинусная близость двух распределений (структура трафика vs структура заказов)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(a.dot(b) / np.linalg.norm(a) / np.linalg.norm(b))


# --------------------------------------------------------------------------
# 6. Проверка устойчивости выводов
# --------------------------------------------------------------------------
def two_prop_test(k1: int | float, n1: int | float,
                  k2: int | float, n2: int | float) -> dict:
    """Сравнение двух долей: z-тест + 95% ДИ разницы (Newcombe) и отношение.

    Используется, чтобы не называть «×3,2» значимым, не проверив интервал.
    """
    from scipy.stats import norm

    p1, p2 = k1 / n1, k2 / n2
    diff = p1 - p2
    p_pool = (k1 + k2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = diff / se if se > 0 else np.nan
    pval = float(2 * norm.sf(abs(z))) if np.isfinite(z) else np.nan
    try:
        from statsmodels.stats.proportion import confint_proportions_2indep
        lo, hi = confint_proportions_2indep(k1, n1, k2, n2, method="newcomb")
    except Exception:  # pragma: no cover - fallback для старых версий statsmodels
        lo, hi = diff - 1.96 * se, diff + 1.96 * se
    return {
        "p1": p1, "p2": p2, "diff": diff, "diff_ci_low": float(lo),
        "diff_ci_high": float(hi), "ratio": p1 / p2 if p2 else np.nan,
        "z": float(z), "p_value": pval, "n1": n1, "n2": n2,
        "significant": bool(np.isfinite(pval) and pval < 0.05),
    }


def category_mix_decomposition(c: pd.DataFrame) -> dict:
    """Разложение разрыва конверсии VK vs Партнёр на «состав трафика» и «механику».

    Конверсия = сумма(доля категории × конверсия категории). Считаем контрфактику:
    если бы у Маркета был состав открытий Партнёра, но его собственные
    внутрикатегорийные конверсии. Тогда:

        ratio_total   = conv_pt / conv_vk          (общий разрыв)
        ratio_mix     = conv_cf / conv_vk          (вклад состава трафика)
        ratio_within  = conv_pt / conv_cf          (вклад механики внутри категорий)

    Логарифмы вкладов складываются в логарифм общего разрыва.
    """
    d = c[(c.opens_vk > 0) & (c.opens_pt > 0) & c.conv_vk.notna() & c.conv_pt.notna()].copy()
    share_vk = d.opens_vk / d.opens_vk.sum()
    share_pt = d.opens_pt / d.opens_pt.sum()
    conv_vk = d.orders_vk / d.opens_vk
    conv_pt = d.orders_pt / d.opens_pt

    conv_vk_actual = float((share_vk * conv_vk).sum())
    conv_pt_actual = float((share_pt * conv_pt).sum())
    conv_cf = float((share_pt * conv_vk).sum())

    total = np.log(conv_pt_actual / conv_vk_actual)
    mix = np.log(conv_cf / conv_vk_actual)
    within = np.log(conv_pt_actual / conv_cf)

    d["share_vk"] = share_vk
    d["share_pt"] = share_pt
    d["conv_vk"] = conv_vk
    d["conv_pt"] = conv_pt
    d["d_share"] = share_pt - share_vk
    d["mix_contribution_log"] = d.d_share * conv_vk / conv_cf
    d["conversion_lift_x"] = d.conv_pt / d.conv_vk
    by_cat = d[["category", "share_vk", "share_pt", "d_share", "conv_vk", "conv_pt",
                "conversion_lift_x", "mix_contribution_log"]].sort_values(
        "d_share", key=np.abs, ascending=False)

    summary = pd.DataFrame([
        {"компонента": "Состав трафика (какие категории смотрят)", "ratio": conv_cf / conv_vk_actual,
         "share_of_log_gap": mix / total if total else np.nan},
        {"компонента": "Механика внутри категорий (карточка → заказ)", "ratio": conv_pt_actual / conv_cf,
         "share_of_log_gap": within / total if total else np.nan},
        {"компонента": "Итого (Партнёр / Маркет)", "ratio": conv_pt_actual / conv_vk_actual,
         "share_of_log_gap": 1.0},
    ])
    return {
        "summary": summary, "by_category": by_cat,
        "conv_vk": conv_vk_actual, "conv_pt": conv_pt_actual, "conv_counterfactual": conv_cf,
        "n_categories": len(d), "total_log_gap": total,
    }


def trend_adjusted(d: pd.DataFrame, col: str) -> dict:
    """Тренд с поправкой на день недели: log(y) ~ t + dummies(dow).

    Обычный `trend` даёт «последние 7 к первым 7», но в 30-дневном окне
    это может быть календарным артефактом. Здесь наклон — уже очищенный
    от структуры недели и с HAC-ошибками.
    """
    import statsmodels.api as sm

    x = pd.DataFrame({"t": np.arange(len(d), dtype=float)}, index=d.index)
    for k in range(1, 7):
        x[f"dow_{k}"] = (d["dow"].to_numpy() == k).astype(float)
    y = np.log(d[col].astype(float).clip(lower=1e-9))
    m = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    ci = m.conf_int().loc["t"]
    slope = float(m.params["t"])
    raw = trend(d, col)
    return {
        "metric": col,
        "daily_pct": float(np.exp(slope) - 1),
        "daily_pct_ci_low": float(np.exp(ci[0]) - 1),
        "daily_pct_ci_high": float(np.exp(ci[1]) - 1),
        "p_value_adjusted": float(m.pvalues["t"]),
        "r2": float(m.rsquared),
        "change_pct_raw": raw["change_pct"],
        "p_value_raw": raw["p_value"],
    }

