"""Графика в едином деловом стиле. Все функции сохраняют PNG в outputs/figures."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from .config import BAD, FIG, GOOD, GREY, LIGHT, PARTNER, VK, set_style

set_style()

_pct = FuncFormatter(lambda v, _: f"{v*100:.1f}%")
_thousands = FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " "))


def save(fig, name: str):
    path = FIG / f"{name}.png"
    fig.savefig(path)
    plt.show()
    return path


def funnel_compare(f: pd.DataFrame, name="funnel_vk_vs_partner"):
    """Две воронки рядом: логарифмическая шкала объёмов + конверсии шагов."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    steps = ["impressions", "card_opens", "button_clicks", "orders"]
    labels = ["Показы", "Открытия\nкарточки", "Нажатия\nкнопки", "Заказы"]
    for ax, (_, row), color in zip(axes, f.iterrows(), [VK, PARTNER]):
        vals = row[steps].to_numpy(dtype=float)
        ax.bar(labels, vals, color=color, width=0.62)
        ax.set_yscale("log")
        ax.set_title(f"{row['segment']}")
        ax.set_ylabel("события за 30 дней (лог. шкала)")
        for i, v in enumerate(vals):
            ax.text(i, v * 1.15, f"{v:,.0f}".replace(",", " "), ha="center", fontsize=9, fontweight="bold")
        convs = [row.ctr_impression_to_open, row.click_rate_open_to_click, row.click_to_order]
        for i, cv in enumerate(convs):
            ax.annotate(f"{cv*100:.2f}%", xy=(i + 0.5, np.sqrt(vals[i] * vals[i + 1])),
                        ha="center", va="center", fontsize=10, color=BAD if cv < 0.05 else GOOD,
                        fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=LIGHT))
    fig.suptitle("Воронка Маркета ВКонтакте и Партнёра 1, сентябрь 2026", fontweight="bold", y=1.02)
    fig.tight_layout()
    return save(fig, name)


def step_conversion_bars(f: pd.DataFrame, name="funnel_step_conversions"):
    """Сравнение конверсий каждого шага — где именно теряется покупатель."""
    cols = ["ctr_impression_to_open", "click_rate_open_to_click", "click_to_order", "conv_open_to_order"]
    labels = ["Показ →\nоткрытие", "Открытие →\nнажатие кнопки", "Нажатие →\nзаказ", "Открытие →\nзаказ (сквозная)"]
    x = np.arange(len(cols))
    w = 0.38
    vk = f[f.segment == "Маркет ВКонтакте"][cols].to_numpy(float)[0]
    pt = f[f.segment == "Партнёр 1"][cols].to_numpy(float)[0]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(x - w / 2, vk * 100, w, label="Маркет ВКонтакте", color=VK)
    ax.bar(x + w / 2, pt * 100, w, label="Партнёр 1", color=PARTNER)
    ax.set_yscale("log")
    ax.set_ylabel("конверсия, % (лог. шкала)")
    ax.set_xticks(x, labels)
    for xi, (a, b) in enumerate(zip(vk, pt)):
        ax.text(xi - w / 2, a * 100 * 1.1, f"{a*100:.2f}%", ha="center", fontsize=9)
        ax.text(xi + w / 2, b * 100 * 1.1, f"{b*100:.2f}%", ha="center", fontsize=9)
        ax.text(xi, max(a, b) * 100 * 2.4, f"×{b/a:.1f}", ha="center", fontsize=11,
                fontweight="bold", color=BAD)
    ax.legend()
    ax.set_title("Узкое место — шаг «открытие карточки → нажатие кнопки»")
    fig.tight_layout()
    return save(fig, name)


def hbar(df: pd.DataFrame, label_col: str, value_col: str, title: str, name: str,
         color=VK, fmt="num", xlabel="", figsize=(10, 5), note=None):
    d = df.sort_values(value_col, ascending=True)
    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(d[label_col].astype(str), d[value_col], color=color, height=0.68)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.xaxis.set_major_formatter(_pct if fmt == "pct" else _thousands)
    for i, v in enumerate(d[value_col]):
        txt = f"{v*100:.2f}%" if fmt == "pct" else f"{v:,.0f}".replace(",", " ")
        ax.text(v, i, " " + txt, va="center", fontsize=9)
    ax.margins(x=0.14)
    if note:
        fig.text(0.01, -0.04, note, fontsize=8, color=GREY)
    fig.tight_layout()
    return save(fig, name)


def grouped_share(df: pd.DataFrame, label_col: str, c1: str, c2: str, title: str, name: str,
                  l1="Маркет ВКонтакте", l2="Партнёр 1", figsize=(11, 4.8)):
    x = np.arange(len(df))
    w = 0.4
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(x - w / 2, df[c1] * 100, w, label=l1, color=VK)
    ax.bar(x + w / 2, df[c2] * 100, w, label=l2, color=PARTNER)
    ax.set_xticks(x, df[label_col].astype(str), rotation=30, ha="right")
    ax.set_ylabel("доля, %")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return save(fig, name)


def time_series(d: pd.DataFrame, cols: list[str], labels: list[str], title: str, name: str,
                colors=(VK, PARTNER), normalize=False, ylabel="", figsize=(11, 4.2)):
    fig, ax = plt.subplots(figsize=figsize)
    for c, l, col in zip(cols, labels, colors):
        y = d[c].to_numpy(float)
        if normalize:
            y = y / y[:7].mean() * 100
        ax.plot(d["date"], y, marker="o", ms=3, lw=1.8, label=l, color=col)
    ax.set_title(title)
    ax.set_ylabel(ylabel or ("индекс, первые 7 дней = 100" if normalize else ""))
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    return save(fig, name)


def activation_funnel_plot(f: pd.DataFrame, name="activation_funnel"):
    fig, ax = plt.subplots(figsize=(10.5, 5))
    colors = [VK if i < 6 else GOOD for i in range(len(f))]
    ax.barh(f["step"][::-1], f["share_of_all"][::-1] * 100, color=colors[::-1], height=0.7)
    ax.set_xlabel("доля от всех сообществ выборки, %")
    ax.set_title("Вложенная воронка торгового стека (n = 9 754 сообществ)")
    for i, (n, s) in enumerate(zip(f["n"][::-1], f["share_of_all"][::-1])):
        ax.text(s * 100, i, f"  {n:,}  ({s*100:.1f}%)".replace(",", " "), va="center", fontsize=9)
    ax.margins(x=0.2)
    fig.tight_layout()
    return save(fig, name)


def scatter_segment(g: pd.DataFrame, name="segments_map"):
    """Карта сегментов: размер сегмента × доля продающих × заказы на бизнес."""
    fig, ax = plt.subplots(figsize=(10, 5.6))
    sizes = g["n"] / g["n"].max() * 1600 + 80
    ax.scatter(g["sell_rate"] * 100, g["orders_per_biz"], s=sizes, c=VK, alpha=0.55, edgecolor="white")
    for _, r in g.iterrows():
        ax.annotate(f"{r['segment']}\nn={int(r['n']):,}".replace(",", " "),
                    (r.sell_rate * 100, r.orders_per_biz), fontsize=8,
                    xytext=(8, 8), textcoords="offset points")
    ax.set_xlabel("доля сообществ с ≥1 заказом, %")
    ax.set_ylabel("заказов на сообщество за 30 дней")
    ax.set_title("Карта сценарных сегментов: где продажи уже случаются")
    ax.margins(0.2)
    fig.tight_layout()
    return save(fig, name)
