"""vkcase — общая библиотека для анализа кейса VK Case Champ 2026.

Модули:
    config    — пути, палитра, константы, стиль графиков
    data      — загрузка 7 листов и производные метрики
    analysis  — воронки, сегментация, сопоставимость групп, эффекты, тренды
    viz       — графики в едином стиле (PNG в outputs/figures)

Быстрый старт:
    from vkcase import data, analysis as an, viz
    d = data.load_all()
    b = d["biz"]
"""
from . import analysis, config, data, viz  # noqa: F401

__version__ = "1.0.0"
