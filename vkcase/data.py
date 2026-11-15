"""Загрузка и подготовка данных кейса VK Case Champ 2026.

Принципы:
1. Сырые листы не меняем — все производные метрики считаем явно и отдельно.
2. Каждое преобразование документировано (см. docstring функций).
3. Ничего не «чиним» молча: аномалии помечаем флагами и выносим в аудит.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import BIZ_COLS, DATA_PATH, SHEETS, TABLES, OUT


# --------------------------------------------------------------------------
# Загрузка
# --------------------------------------------------------------------------
def load_raw(path: Path | str = DATA_PATH) -> dict[str, pd.DataFrame]:
    """Читает все 7 листов книги как есть (без переименований)."""
    xl = pd.ExcelFile(path)
    return {key: pd.read_excel(xl, sheet) for key, sheet in SHEETS.items()}


def businesses(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Таблица «Бизнесы» (n≈9754) с англоязычными именами колонок и фичами.

    Производные поля
    ----------------
    content_all / content_prod : всего публикаций и публикаций с товаром
    views_all                  : все просмотры контента
    er_reg / er_prod           : engagement rate = (лайки+репосты)/просмотры
    vpp_reg / vpp_prod         : просмотров на одну публикацию
    card_ctr                   : открытия карточки / просмотры товарного контента
    has_catalog / has_order    : бинарные флаги
    aov_calc                   : GMV / заказы (вместо «битой» колонки «Средний чек»)
    size_band                  : размерная группа по подписчикам
    flags_*                    : флаги логических аномалий (для аудита)
    """
    b = pd.read_excel(path, SHEETS["biz"]).rename(columns=BIZ_COLS)

    b["content_all"] = b["posts"] + b["clips"]
    b["content_prod"] = b["posts_prod"] + b["clips_prod"]
    b["views_all"] = b["views_reg"] + b["views_prod"]
    b["has_catalog"] = (b["sku_active"] > 0).astype(int)
    b["has_order"] = (b["orders"] > 0).astype(int)
    b["has_prod_content"] = (b["content_prod"] > 0).astype(int)
    b["pays_ads"] = (b["ad_spend"] > 0).astype(int)
    b["tools_cnt"] = b[["checkout", "delivery", "payment"]].sum(axis=1)

    safe = lambda s: s.replace(0, np.nan)
    b["er_reg"] = (b["likes_reg"] + b["reposts_reg"]) / safe(b["views_reg"])
    b["er_prod"] = (b["likes_prod"] + b["reposts_prod"]) / safe(b["views_prod"])
    b["vpp_reg"] = b["views_reg"] / safe(b["content_all"])
    b["vpp_prod"] = b["views_prod"] / safe(b["content_prod"])
    b["card_ctr"] = b["card_opens"] / safe(b["views_prod"])
    b["aov_calc"] = b["gmv"] / safe(b["orders"])
    b["roas"] = b["gmv"] / safe(b["ad_spend"])
    b["orders_per_1k_opens"] = 1000 * b["orders"] / safe(b["card_opens"])

    b["size_band"] = pd.cut(
        b["subs"], [-1, 100, 1000, 10_000, 50_000, 10**9],
        labels=["0–100", "100–1k", "1k–10k", "10k–50k", "50k+"],
    )
    b["activity_band"] = pd.cut(
        b["content_all"], [-1, 0, 5, 20, 60, 10**9],
        labels=["0", "1–5", "6–20", "21–60", "60+"],
    )

    # Флаги аномалий — НЕ удаляем строки, только маркируем
    b["flag_checkout_no_catalog"] = ((b["checkout"] == 1) & (b["sku_active"] == 0)).astype(int)
    b["flag_gmv_no_orders"] = ((b["gmv"] > 0) & (b["orders"] == 0)).astype(int)
    b["flag_orders_no_gmv"] = ((b["orders"] > 0) & (b["gmv"] == 0)).astype(int)
    b["flag_views_no_posts"] = ((b["views_prod"] > 0) & (b["content_prod"] == 0)).astype(int)
    b["flag_opens_gt_views"] = (b["card_opens"] > b["views_prod"]).astype(int)
    b["flag_tools_no_checkout"] = (((b["delivery"] == 1) | (b["payment"] == 1)) & (b["checkout"] == 0)).astype(int)
    return b


def totals(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Лист «итоги» в широком виде, индекс — название метрики."""
    return pd.read_excel(path, SHEETS["totals"]).set_index("Метрика")


def total(metric: str, col: str = "Маркет Вконтакте", path: Path | str = DATA_PATH) -> float:
    """Числовое значение метрики из листа «итоги» ('—' → NaN)."""
    t = totals(path)
    return float(pd.to_numeric(pd.Series([t.loc[metric, col]]), errors="coerce").iloc[0])


def daily(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Дневная динамика + производные конверсии и календарные признаки."""
    d = pd.read_excel(path, SHEETS["daily"])
    d = d.rename(columns={"Дата": "date"})
    d["date"] = pd.to_datetime(d["date"])
    d["dow"] = d["date"].dt.day_of_week
    d["is_weekend"] = (d["dow"] >= 5).astype(int)
    d["week"] = d["date"].dt.isocalendar().week.astype(int)
    for who, suf in [("vk", "Маркет Вконтакте"), ("pt", "Партнёр 1")]:
        imp = d[f"Показы товаров: {suf}"]
        op = d[f"Открытия карточки: {suf}"]
        cl = d[f"Нажатия на кнопку: {suf}"]
        od = d[f"Заказы: {suf}"]
        gm = d[f"GMV, ₽: {suf}"]
        d[f"ctr_{who}"] = op / imp
        d[f"click_rate_{who}"] = cl / op
        d[f"click2order_{who}"] = od / cl
        d[f"conv_{who}"] = od / op
        d[f"aov_{who}"] = gm / od
    d["search_ctr"] = d["Поисковые запросы с открытием карточки"] / d["Поисковые запросы"]
    return d


def sources(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Источники открытий карточки. Строка «в т.ч. реферальные» — подмножество, выносим отдельно."""
    s = pd.read_excel(path, SHEETS["sources"])
    ref = s[s["Источник"].str.contains("реферальн", case=False, na=False)]
    s = s[~s["Источник"].str.contains("реферальн", case=False, na=False)].copy()
    s["share_vk"] = s["Маркет Вконтакте"] / s["Маркет Вконтакте"].sum()
    s["share_pt"] = s["Партнёр 1"] / s["Партнёр 1"].sum()
    s.attrs["referral_opens"] = float(ref["Партнёр 1"].iloc[0]) if len(ref) else np.nan
    return s


def categories(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Категории: конверсии, доли трафика и заказов, «мёртвый трафик»."""
    c = pd.read_excel(path, SHEETS["categories"])
    c = c.rename(columns={
        "Открытия карточки: Маркет Вконтакте": "opens_vk",
        "Заказы: Маркет Вконтакте": "orders_vk",
        "Открытия карточки: Партнёр 1": "opens_pt",
        "Заказы: Партнёр 1": "orders_pt",
        "Категория": "category",
    })
    c["conv_vk"] = c["orders_vk"] / c["opens_vk"].replace(0, np.nan)
    c["conv_pt"] = c["orders_pt"] / c["opens_pt"].replace(0, np.nan)
    c["open_share_vk"] = c["opens_vk"] / c["opens_vk"].sum()
    c["order_share_vk"] = c["orders_vk"] / c["orders_vk"].sum()
    c["open_share_pt"] = c["opens_pt"] / c["opens_pt"].sum()
    c["order_share_pt"] = c["orders_pt"] / c["orders_pt"].sum()
    c["conv_gap_x"] = c["conv_pt"] / c["conv_vk"]
    c["is_dead_traffic"] = (c["conv_vk"] < 0.001).astype(int)
    return c


def buyers(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Пол × возраст: доли и заказов на покупателя. NaN = группы <100 (см. «итоги»)."""
    p = pd.read_excel(path, SHEETS["buyers"])
    p = p.rename(columns={
        "Пол": "sex", "Возраст": "age",
        "Покупатели: Маркет Вконтакте": "buyers_vk", "Заказы: Маркет Вконтакте": "orders_vk",
        "Покупатели: Партнёр 1": "buyers_pt", "Заказы: Партнёр 1": "orders_pt",
    })
    for who in ("vk", "pt"):
        p[f"share_{who}"] = p[f"buyers_{who}"] / p[f"buyers_{who}"].sum()
        p[f"opb_{who}"] = p[f"orders_{who}"] / p[f"buyers_{who}"]
    p["age_index_vk_vs_pt"] = p["share_vk"] / p["share_pt"]
    return p


def regions(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Регионы: доли, индекс переиндексации VK vs Партнёр, заказы на покупателя."""
    r = pd.read_excel(path, SHEETS["regions"])
    r = r.rename(columns={
        "Регион": "region",
        "Покупатели: Маркет Вконтакте": "buyers_vk", "Заказы: Маркет Вконтакте": "orders_vk",
        "Покупатели: Партнёр 1": "buyers_pt", "Заказы: Партнёр 1": "orders_pt",
    })
    for who in ("vk", "pt"):
        r[f"share_{who}"] = r[f"buyers_{who}"] / r[f"buyers_{who}"].sum()
        r[f"opb_{who}"] = r[f"orders_{who}"] / r[f"buyers_{who}"]
    r["index_vk_vs_pt"] = r["share_vk"] / r["share_pt"]
    return r


def load_all(path: Path | str = DATA_PATH) -> dict[str, pd.DataFrame]:
    """Одна точка входа для ноутбуков: все подготовленные таблицы."""
    return {
        "biz": businesses(path), "totals": totals(path), "daily": daily(path),
        "sources": sources(path), "categories": categories(path),
        "buyers": buyers(path), "regions": regions(path),
    }


# --------------------------------------------------------------------------
# Выгрузки
# --------------------------------------------------------------------------
def save_table(df: pd.DataFrame, name: str) -> Path:
    """Сохраняет таблицу в outputs/tables/<name>.csv (UTF-8 BOM для Excel)."""
    p = TABLES / f"{name}.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p


def save_key_numbers(values: dict, namespace: str) -> Path:
    """Накапливает ключевые цифры в outputs/key_numbers.json.

    Нужно, чтобы отчёт и дашборд собирались из посчитанных значений,
    а не из чисел, переписанных руками.
    """
    p = OUT / "key_numbers.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    data.setdefault(namespace, {}).update(
        {k: (None if v is None or (isinstance(v, float) and not np.isfinite(v))
             else float(v) if isinstance(v, (int, float, np.number)) else v)
         for k, v in values.items()}
    )
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
