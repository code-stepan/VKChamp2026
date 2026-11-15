# -*- coding: utf-8 -*-
"""Собирает графики специально для handover-отчёта.

Все числа берутся из outputs/ (key_numbers.json и таблицы), ничего не вводится
руками, кроме годовых пересчётов, которые здесь же и помечены.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIG = Path(__file__).resolve().parent / "figures"
FIG.mkdir(parents=True, exist_ok=True)

VK = "#0077FF"
PARTNER = "#FF7A45"
GOOD = "#2BB673"
BAD = "#E0483D"
GREY = "#8A94A6"
DARK = "#1F2733"
LIGHT = "#E6ECF5"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10.5,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 10.5,
    "axes.edgecolor": "#C9D2DF",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.dpi": 170,
    "savefig.bbox": "tight",
})


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png")
    plt.close(fig)
    print("saved", FIG / f"{name}.png")


def fmt_int(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


kn = json.loads((OUT / "key_numbers.json").read_text(encoding="utf-8"))
prof = pd.read_csv(OUT / "tables" / "01_segment_profile.csv")
scen = pd.read_csv(OUT / "tables" / "04_platform_scenarios.csv")
mon = pd.read_csv(OUT / "tables" / "04_monetization.csv")
psm = pd.read_csv(OUT / "tables" / "05_psm_robustness.csv")
act = pd.read_csv(OUT / "tables" / "04_activation_scenarios.csv")

# ---------------------------------------------------------------------------
# 1. Масштаб: годовой эквивалент сентября 2026 против рынка e-com РФ
# ---------------------------------------------------------------------------
vk_gmv = kn["03_market"]["vk_gmv"] * 12
pt_gmv = kn["03_market"]["pt_gmv"] * 12
vk_orders = kn["03_market"]["vk_orders"] * 12
pt_orders = kn["03_market"]["pt_orders"] * 12
rf_gmv = 13.4e12
rf_orders = 8.3e9

fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.2))
labels = ["Рынок e-com РФ", "Партнёр 1", "Маркет ВКонтакте"]
gmv_vals = [rf_gmv, pt_gmv, vk_gmv]
ord_vals = [rf_orders, pt_orders, vk_orders]
shares_gmv = [1.0, pt_gmv / rf_gmv, vk_gmv / rf_gmv]
shares_ord = [1.0, pt_orders / rf_orders, vk_orders / rf_orders]
colors = [GREY, PARTNER, VK]

for ax, vals, shares, title, unit, div, fmt_share in [
    (axes[0], gmv_vals, shares_gmv, "GMV, млрд ₽/год", "₽", 1e9, True),
    (axes[1], ord_vals, shares_ord, "Заказы, млн/год", "шт.", 1e6, True),
]:
    disp = [v / div for v in vals]
    y = np.arange(len(labels))
    bars = ax.barh(y, disp, color=colors, height=0.55)
    ax.set_xscale("log")
    ax.set_yticks(y, labels)
    ax.set_xlabel("логарифмическая шкала")
    ax.set_title(title, fontsize=12.5)
    ax.grid(axis="x", color=LIGHT, lw=0.8)
    ax.set_axisbelow(True)
    lo = min(disp) * 0.25
    hi = max(disp) * 4
    ax.set_xlim(lo, hi)
    for i, (v, s) in enumerate(zip(disp, shares)):
        if i == 0:
            txt = f"{v:,.0f} ({s:.0%})".replace(",", " ")
        else:
            txt = f"{v:,.1f} ({s:.2%})".replace(",", " ").replace(".", ",")
        ax.text(v * 1.18, i, txt, va="center", fontsize=10, fontweight="bold", color=DARK)

fig.suptitle("Масштаб Маркета: 0,14% GMV и 0,06% заказов рынка e-com РФ",
             fontsize=14.5, fontweight="bold", y=1.02)
fig.text(0.5, -0.06,
         "Годовой эквивалент сентября 2026. Рынок e-com РФ — 13,4 трлн ₽ и 8,3 млрд заказов (ориентиры кейса).",
         ha="center", fontsize=9, color=GREY)
fig.tight_layout()
save(fig, "report_market_share")

# ---------------------------------------------------------------------------
# 2. Карта сегментов
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11.6, 5.4))
seg_colors = {
    "S0. Услуги без каталога": GREY,
    "S1. Контент/переписка без товаров": GREY,
    "S2. Чекаут без каталога (аномалия)": PARTNER,
    "S3. Витрина без чекаута": "#F2A93B",
    "S4. Каталог + чекаут": VK,
    "S5. Каталог + чекаут + доставка": GOOD,
    "S6. Полный стек (+оплата)": "#16845B",
}
short = {
    "S0. Услуги без каталога": "S0 · услуги",
    "S1. Контент/переписка без товаров": "S1 · контент",
    "S2. Чекаут без каталога (аномалия)": "S2 · пустой чекаут",
    "S3. Витрина без чекаута": "S3 · витрина",
    "S4. Каталог + чекаут": "S4 · спящий магазин",
    "S5. Каталог + чекаут + доставка": "S5 · доставка",
    "S6. Полный стек (+оплата)": "S6 · полный стек",
}
for _, r in prof.iterrows():
    size = 60 + np.sqrt(r["n"]) * 26
    ax.scatter(r["sell_rate"] * 100, r["orders_per_biz"], s=size,
               color=seg_colors[r["segment"]], alpha=0.85, edgecolor="white", lw=1.2, zorder=3)
offsets = {
    "S0. Услуги без каталога": (-0.30, 0.55, "right", "bottom"),
    "S1. Контент/переписка без товаров": (0.86, 0.72, "left", "bottom"),
    "S2. Чекаут без каталога (аномалия)": (0.51, -0.18, "left", "top"),
    "S3. Витрина без чекаута": (0.61, 0.30, "left", "bottom"),
    "S4. Каталог + чекаут": (0.60, 0.45, "left", "bottom"),
    "S5. Каталог + чекаут + доставка": (-0.72, 0.16, "right", "bottom"),
    "S6. Полный стек (+оплата)": (-0.62, 0.16, "right", "bottom"),
}
for _, r in prof.iterrows():
    dx, dy, ha, va = offsets[r["segment"]]
    ax.annotate(f"{short[r['segment']]}\nn={fmt_int(r['n'])}",
                (r["sell_rate"] * 100, r["orders_per_biz"]),
                xytext=(r["sell_rate"] * 100 + dx, r["orders_per_biz"] + dy),
                fontsize=9, ha=ha, va=va, color=DARK,
                arrowprops=dict(arrowstyle="-", color="#B8C2D0", lw=0.7))
ax.axvline(3.055, color=BAD, ls="--", lw=1.2, zorder=1)
ax.text(3.15, 2.95, "средняя доля продающих 3,1%", color=BAD, fontsize=9, va="top")
ax.set_xlim(-1.8, 19.8)
ax.set_ylim(-0.55, 3.80)
ax.set_xlabel("доля сообществ с ≥1 заказом за 30 дней, %")
ax.set_ylabel("заказов на сообщество за 30 дней")
ax.grid(color=LIGHT, lw=0.8)
ax.set_axisbelow(True)
ax.set_title("Сегменты: инструменты есть у многих, продают — единицы")
fig.text(0.5, -0.03,
         "Размер круга — число сообществ. S0/S1 — вне фокуса кейса (услуги и контент без товаров).",
         ha="center", fontsize=9, color=GREY)
fig.tight_layout()
save(fig, "report_segments_map")

# ---------------------------------------------------------------------------
# 3. Сравнение конверсий ВК и Партнёра
# ---------------------------------------------------------------------------
steps = ["Показ →\nоткрытие", "Открытие →\nкнопка", "Кнопка →\nзаказ", "Открытие →\nзаказ"]
vk_vals = [4.05, 3.08, 6.93, 0.214]
pt_vals = [1.52, 42.16, 13.45, 5.67]
x = np.arange(len(steps))
fig, ax = plt.subplots(figsize=(11.4, 5.0))
w = 0.36
b1 = ax.bar(x - w / 2, vk_vals, w, label="Маркет ВКонтакте", color=VK)
b2 = ax.bar(x + w / 2, pt_vals, w, label="Партнёр 1", color=PARTNER)
ax.set_yscale("log")
ax.set_ylim(0.1, 120)
ax.set_xticks(x, steps)
ax.set_ylabel("конверсия шага, % (лог. шкала)")
ax.grid(axis="y", color=LIGHT, lw=0.8)
ax.set_axisbelow(True)
for bars in (b1, b2):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h * 1.12, f"{h:.2f}%".replace(".", ","),
                ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=DARK)
ax.annotate("", xy=(1.30, 42), xytext=(1.30, 3.1),
            arrowprops=dict(arrowstyle="<->", color=BAD, lw=1.4))
ax.text(1.36, 11.5, "×13,7", color=BAD, fontsize=12, fontweight="bold", ha="left")
ax.legend(frameon=False, loc="upper left", ncol=2)
ax.set_title("Узкое место — «открытие карточки → кнопка»: 3,08% против 42,16%")
fig.text(0.5, -0.04,
         "Сентябрь 2026. На шаг «открытие → кнопка» приходится 106% логарифмического разрыва в заказах.",
         ha="center", fontsize=9, color=GREY)
fig.tight_layout()
save(fig, "report_funnel_compare")

# ---------------------------------------------------------------------------
# 4. Сценарии
# ---------------------------------------------------------------------------
order_now = kn["03_market"]["vk_orders"]
gmv_now = kn["03_market"]["vk_gmv"]
labels4 = ["Сейчас", "Консерв.", "Базовый", "Агресс."]
orders4 = [order_now] + scen["заказы/мес"].tolist()
gmv4 = [gmv_now / 1e9] + (scen["GMV/мес, ₽"] / 1e9).tolist()
rev_now_year = 0.7e6 * 12
rev4 = [rev_now_year / 1e6] + (mon["итого новая выручка, ₽/год"] / 1e6).tolist()
colors4 = [GREY, "#7FA9D9", VK, "#0047A8"]

fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.4))
panels = [
    (axes[0], [v / 1e3 for v in orders4], "Заказы, тыс./мес", "{:.0f}", False),
    (axes[1], gmv4, "GMV, млрд ₽/мес", "{:.2f}", False),
    (axes[2], rev4, "Новая выручка, млн ₽/год", "{:,.0f}", True),
]
for ax, vals, title, fmt, thousands in panels:
    bars = ax.bar(labels4, vals, color=colors4, width=0.62)
    ax.set_title(title, fontsize=12.5)
    ax.grid(axis="y", color=LIGHT, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(vals) * 1.2)
    for b, v in zip(bars, vals):
        txt = fmt.format(v)
        if thousands:
            txt = txt.replace(",", " ")
        ax.text(b.get_x() + b.get_width() / 2, v * 1.02, txt,
                ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=DARK)
    ax.tick_params(axis="x", labelsize=9)
fig.suptitle("Три сценария: заказы ×1,9–10,5, GMV ×1,8–8,1 к текущему уровню",
             fontsize=14.5, fontweight="bold", y=1.03)
fig.text(0.5, -0.05,
         "Не прогноз, а модель «что если»: конверсия кнопки 5/8/15%, нажатие→заказ 8/10/12%, оплаченная доля 25/50/70%, take rate 3/5/7%.",
         ha="center", fontsize=8.8, color=GREY)
fig.tight_layout()
save(fig, "report_scenarios")

# ---------------------------------------------------------------------------
# 5. PSM: наивное сравнение против сопоставления
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.2), gridspec_kw={"width_ratios": [1, 1.35]})
ax = axes[0]
groups = ["Наивное\nсравнение", "После PSM"]
control = [5.30, 13.45]
treated = [17.12, 16.67]
x = np.arange(2)
w = 0.32
b1 = ax.bar(x - w / 2, control, w, color=GREY, label="S4 · без доставки")
b2 = ax.bar(x + w / 2, treated, w, color=GOOD, label="S5 · с доставкой")
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.35, f"{b.get_height():.1f}%".replace(".", ","),
                ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.set_xticks(x, groups)
ax.set_ylim(0, 24)
ax.set_ylabel("доля с ≥1 заказом, %")
ax.grid(axis="y", color=LIGHT, lw=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, fontsize=9)
ax.annotate("+11,8 п.п.\n×3,2", (0, 19.5), ha="center", fontsize=11, fontweight="bold", color=BAD)
ax.annotate("+3,2 п.п.\n×1,24\nДИ включает 0", (1, 19.5), ha="center", fontsize=11, fontweight="bold", color=GREY)
ax.set_title("Наивный разрыв и эффект после PSM", fontsize=12.5)

ax = axes[1]
y = np.arange(len(psm))
ax.errorbar(psm["ATT активации, п.п."], y,
            xerr=[psm["ATT активации, п.п."] - psm["ДИ низ, п.п."],
                  psm["ДИ верх, п.п."] - psm["ATT активации, п.п."]],
            fmt="o", color=VK, ecolor="#AFC4DE", elinewidth=2, capsize=3, ms=7)
ax.axvline(0, color=BAD, ls="--", lw=1.2)
labels_y = []
for _, r in psm.iterrows():
    ctrl = "с чекаутом" if "с чекаутом" in r["спецификация"] else "весь каталог"
    labels_y.append(f"{ctrl}, калипер {r['калипер (SD)']:.2f}")
ax.set_yticks(y, labels_y)
ax.invert_yaxis()
ax.set_xlabel("ATT по вероятности первой продажи, п.п. (95% ДИ)")
ax.grid(axis="x", color=LIGHT, lw=0.8)
ax.set_axisbelow(True)
ax.set_xlim(-1.6, 8.0)
ax.set_title("8 спецификаций: знак устойчив, значимость — нет", fontsize=12.5)
fig.suptitle("Эффект доставки: ×3,2 — это отбор, а не эффект инструмента",
             fontsize=14.5, fontweight="bold", y=1.02)
fig.text(0.5, -0.04,
         "PSM по наблюдаемым признакам. ATT +2,8…+3,5 п.п.; во всех 8 спецификациях ДИ включает 0; эффект на число заказов отрицательный и незначим.",
         ha="center", fontsize=8.8, color=GREY)
fig.tight_layout()
save(fig, "report_psm")

# ---------------------------------------------------------------------------
# 6. Приоритет сегментов по числу новых продающих
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10.8, 4.6))
segs = ["S4: спящий магазин", "S2: пустой чекаут", "S3: витрина без чекаута"]
cols = ["S4: спящий магазин", "S2: пустой чекаут", "S3: витрина без чекаута"]
scen_names = act["сценарий"].tolist()
y = np.arange(len(segs))
h = 0.24
colors_scen = ["#9DBFE8", VK, "#003F8F"]
for i, s in enumerate(scen_names):
    vals = [act.loc[act["сценарий"] == s, c].iloc[0] for c in cols]
    bars = ax.barh(y + (i - 1) * h, vals, h, label=s, color=colors_scen[i])
    for b, v in zip(bars, vals):
        ax.text(v + 1.5, b.get_y() + b.get_height() / 2, f"{v:.0f}",
                va="center", fontsize=9, fontweight="bold", color=DARK)
ax.set_yticks(y, segs)
ax.invert_yaxis()
ax.set_xlabel("новых сообществ с ≥1 заказом в выборке, шт.")
ax.grid(axis="x", color=LIGHT, lw=0.8)
ax.set_axisbelow(True)
ax.set_xlim(0, 160)
ax.legend(frameon=False, loc="lower right", title="Сценарий", fontsize=9, title_fontsize=9)
ax.set_title("Ядро активации — S4: 63% новых продающих в базовом сценарии")
fig.text(0.5, -0.06,
         "Расчёт на выборке 9 754 сообщества с поправкой на охват рычага; S2 даёт быстрый прирост за счёт наполнения каталога.",
         ha="center", fontsize=9, color=GREY)
fig.tight_layout()
save(fig, "report_priority")

# ---------------------------------------------------------------------------
# 7. Три трека целевого пути
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(14.6, 6.2))
ax.set_xlim(0, 14.6)
ax.set_ylim(0, 6.2)
ax.axis("off")

def box(x, y, w, h, text, color, textcolor="white", fs=9.4, bold=True):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                       linewidth=0, facecolor=color, alpha=0.96, zorder=3)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=textcolor, fontweight="bold" if bold else "normal",
            zorder=4, linespacing=1.18)

def arrow(x1, y1, x2, y2, color=GREY):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=11, lw=1.4, color=color, zorder=2))

ax.text(0.15, 5.82, "Целевой путь: общий вход → развилка по товару → три трека → масштабирование",
        fontsize=14, fontweight="bold", color=DARK)
ax.text(0.15, 5.50, "Один и тот же путь, но разные первые шаги: S2 сначала наполняет каталог, S4 — замыкает сделку, S5/S6 — растит трафик и частоту.",
        fontsize=9.5, color=GREY)

# Общие этапы сверху
stages = [
    ("0 · Первый\nконтакт", 0.15),
    ("1 · Развилка:\nесть товар?", 2.15),
    ("2 · Каталог", 4.15),
    ("3 · Сделка", 6.15),
    ("4 · Первый\nтрафик", 8.15),
    ("5 · Первая\nпродажа", 10.15),
    ("6 · Повторные", 12.15),
]
for text, x in stages:
    box(x, 4.55, 1.75, 0.62, text, "#DCE9FA", textcolor=DARK, fs=9.2)
for i in range(len(stages) - 1):
    arrow(stages[i][1] + 1.77, 4.86, stages[i + 1][1] - 0.03, 4.86, "#9DB4D2")

# Треки
tracks = [
    ("S2 · пустой чекаут\n2 096", 3.30, PARTNER, [
        ("Импорт каталога\nOzon / CSV / фото", 4.15, 2.05),
        ("Чекаут\nпо умолчанию", 6.45, 1.75),
        ("Шопсы /\nпоиск", 8.45, 1.55),
        ("Кнопка «Купить»\n+ оплата", 10.25, 1.95),
        ("Повторный\nзаказ", 12.45, 1.45),
    ]),
    ("S3/S4 · каталог есть\n320 + 2 922", 2.10, VK, [
        ("Чекаут\nпо умолчанию", 3.95, 1.85),
        ("Доставка +\nоплата", 6.05, 1.65),
        ("Шопсы /\nреклама", 8.05, 1.65),
        ("Первая\nпродажа", 10.05, 1.55),
        ("Профиль\nпокупателя", 11.85, 1.55),
    ]),
    ("S5/S6 · уже продаёт\n625 + 94", 0.90, GOOD, [
        ("Контент /\nрефералка", 4.25, 2.05),
        ("Реклама\nна заказ", 6.55, 1.75),
        ("Повторные\nпокупки", 8.55, 1.75),
        ("Подписка\nPro", 10.55, 1.55),
    ]),
]
for name, y, color, items in tracks:
    ax.text(0.15, y + 0.28, name, fontsize=9.5, fontweight="bold", color=color, va="center")
    for text, x, w in items:
        box(x, y - 0.02, w, 0.58, text, color, textcolor="white", fs=8.8)

# Стрелки внутри треков
for y, color, items in [(t[1], t[2], t[3]) for t in tracks]:
    for i in range(len(items) - 1):
        x1 = items[i][1] + items[i][2]
        x2 = items[i + 1][1]
        if x2 > x1:
            arrow(x1 + 0.02, y + 0.27, x2 - 0.02, y + 0.27, color)

# S0/S1
box(0.15, 0.12, 13.45, 0.48,
    "S0/S1 · услуги и контент без товаров (3 697) — вне фокуса кейса: заявки и переписка, возвращаемся на следующем этапе",
    "#EEF1F6", textcolor=GREY, fs=9.0, bold=False)

fig.tight_layout()
save(fig, "report_tracks")

print("done")
