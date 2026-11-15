#!/usr/bin/env python
"""Прогон всех ноутбуков проекта по порядку с сохранением выводов.

Запуск:
    python run_all.py            # выполнить все ноутбуки
    python run_all.py 01 03      # выполнить только выбранные

Что делает:
1. конвертирует notebooks/*.py (jupytext percent) в .ipynb — источник правды это .py;
2. выполняет ноутбуки в текущем Python-окружении (nbclient);
3. сохраняет .ipynb с выводами, графики в outputs/figures, таблицы в outputs/tables.

Требования: requirements.txt (pandas, numpy, matplotlib, scipy, scikit-learn,
statsmodels, openpyxl, nbclient, nbformat, jupytext, ipykernel).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
NB_DIR = ROOT / "notebooks"


def convert(patterns: list[str]) -> list[Path]:
    """Конвертирует только выбранные .py → .ipynb.

    Важно: конвертация всех файлов затирает сохранённые выводы у тех ноутбуков,
    которые в этом запуске не исполняются, поэтому фильтруем до конвертации.
    """
    pys = sorted(NB_DIR.glob("*.py"))
    if patterns:
        pys = [p for p in pys if any(p.name.startswith(a) for a in patterns)]
    if pys:
        subprocess.run([sys.executable, "-m", "jupytext", "--to", "ipynb", *map(str, pys)], check=True)
    return [p.with_suffix(".ipynb") for p in pys if p.with_suffix(".ipynb").exists()]


def run(paths: list[Path]) -> None:
    for p in paths:
        t0 = time.time()
        print(f"-> {p.name} ... ", end="", flush=True)
        nb = nbformat.read(p, as_version=4)
        client = NotebookClient(nb, timeout=1200, kernel_name="python3",
                                resources={"metadata": {"path": str(p.parent)}})
        client.execute()
        nbformat.write(nb, p)
        print(f"OK за {time.time()-t0:.1f} c")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    paths = convert(args)
    if not paths:
        print("Ноутбуки не найдены")
        sys.exit(1)
    run(paths)
    print("\nГотово. Смотрите outputs/figures, outputs/tables, outputs/key_numbers.json")
