"""Единая конфигурация проекта: пути, названия листов, палитра, константы.

Все ноутбуки импортируют этот модуль, чтобы не дублировать пути и настройки.
"""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib as mpl

# --- Пути -----------------------------------------------------------------
# Ноутбуки лежат в <ROOT>/notebooks, поэтому корень определяем от cwd.
def find_root() -> Path:
    here = Path.cwd().resolve()
    for cand in [here, *here.parents]:
        if (cand / "uploads" / "data.xlsx").exists() or (cand / "vkcase").exists():
            return cand
    return here


ROOT = find_root()
DATA_PATH = Path(os.environ.get("VKCASE_DATA", ROOT / "uploads" / "data.xlsx"))
OUT = ROOT / "outputs"
FIG = OUT / "figures"
TABLES = OUT / "tables"
for _d in (OUT, FIG, TABLES):
    _d.mkdir(parents=True, exist_ok=True)

# --- Листы книги ----------------------------------------------------------
SHEETS = {
    "biz": "Бизнесы",
    "totals": "Маркет Вконтакте — итоги",
    "daily": "Маркет Вконтакте — по дням",
    "sources": "Маркет Вконтакте — источники",
    "categories": "Маркет Вконтакте — категории",
    "buyers": "Покупатели",
    "regions": "Покупатели по регионам",
}

# --- Переименование колонок таблицы «Бизнесы» -----------------------------
BIZ_COLS = {
    "ID бизнеса": "biz_id",
    "Тематика": "theme",
    "Тип бизнеса (товары / услуги)": "btype",
    "Число подписчиков": "subs",
    "Посты за 30 дней": "posts",
    "Клипы за 30 дней": "clips",
    "Посты с товаром за 30 дней": "posts_prod",
    "Клипы с товаром за 30 дней": "clips_prod",
    "Просмотры обычного контента": "views_reg",
    "Лайки обычного контента": "likes_reg",
    "Репосты обычного контента": "reposts_reg",
    "Просмотры товарного контента": "views_prod",
    "Лайки товарного контента": "likes_prod",
    "Репосты товарного контента": "reposts_prod",
    "Открытия карточки товара из контента": "card_opens",
    "Товары загружены": "sku_uploaded",
    "Число активных товаров в каталоге": "sku_active",
    "Подключён чекаут": "checkout",
    "Подключена доставка": "delivery",
    "Подключена оплата": "payment",
    "Автор оригинального контента (оценка модели)": "orig_author",
    "Участие в реферальной программе": "referral",
    "Заказы через чекаут": "orders",
    "GMV через чекаут, ₽": "gmv",
    "Средний чек, ₽": "aov_col",
    "Траты на рекламу всего, ₽": "ad_spend",
    "Число активных услуг": "services",
    "Медианная цена товара, ₽": "price_median",
}

# --- Палитра (деловая, для слайдов) ---------------------------------------
VK = "#0077FF"        # Маркет ВКонтакте
PARTNER = "#FF7A45"   # Партнёр 1
GOOD = "#2BB673"
BAD = "#E0483D"
GREY = "#8A94A6"
DARK = "#1F2733"
LIGHT = "#E6ECF5"


def set_style() -> None:
    """Единый стиль графиков (кириллица поддерживается DejaVu Sans)."""
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.edgecolor": "#C9D2E0",
        "axes.labelcolor": DARK,
        "text.color": DARK,
        "xtick.color": GREY,
        "ytick.color": GREY,
        "axes.grid": True,
        "grid.color": LIGHT,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


# --- Внешние константы (открытые источники, см. reports/market_benchmarks.md)
VK_DAU_2026Q3 = 90_800_000      # дневная аудитория VK, квартальный отчёт (кейс, стр. 24)
VK_MAU_RUNET_SHARE = 0.97       # охват месячной аудитории рунета
RF_ECOM_GMV_2025 = 13.4e12      # ₽, Data Insight
RF_ECOM_ORDERS_2025 = 8.3e9     # заказов, Data Insight
RF_ECOM_AOV_2025 = 1600         # ₽, Data Insight
MARKETPLACE_ORDER_SHARE = 0.81  # доля маркетплейсов в заказах, Data Insight
VK_MARKET_SELLERS_PUBLIC = 200_000  # «более 200 тыс. продавцов», блог VK Рекламы

PERIOD = "2026-09-01 — 2026-09-30"

# Словарь «человеческих» подписей для сегментов
SEG_ORDER = [
    "S0. Услуги без каталога",
    "S1. Контент/переписка без товаров",
    "S2. Чекаут без каталога (аномалия)",
    "S3. Витрина без чекаута",
    "S4. Каталог + чекаут",
    "S5. Каталог + чекаут + доставка",
    "S6. Полный стек (+оплата)",
]
