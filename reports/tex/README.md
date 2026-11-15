# PDF-версия отчёта (LaTeX)

Готовый файл для отправки: **`VK_Case_2026_handover.pdf`** — 36 страниц, A4,
встроенные шрифты, все 16 рисунков и 56 таблиц внутри. Внешние файлы для
просмотра не нужны, интернет не требуется.

## Что в папке

| Файл | Назначение |
|---|---|
| `VK_Case_2026_handover.pdf` | Готовый PDF — его и отправляйте |
| `main.tex` | Сгенерированный LaTeX-исходник (обложка, оглавление, текст, таблицы) |
| `build_tex.py` | Конвертер `reports/research_findings.md` → `main.tex` |
| `figures/` | 16 PNG-рисунков, подключённых через `\includegraphics` |
| `main.pdf` | То же, что и `VK_Case_2026_handover.pdf` (рабочий выход компилятора) |

Правки вносите **в `reports/research_findings.md`**, а не в `main.tex`:
`main.tex` перезаписывается при каждом запуске `build_tex.py`.

## Пересборка

```powershell
# 1. Markdown → LaTeX (заодно копирует новые рисунки в figures/)
python reports\tex\build_tex.py

# 2. Компиляция — два прохода обязательны
cd reports\tex
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

Два прохода нужны потому, что оглавление, номера страниц и `LastPage`
(«стр. N из 36») собираются из `.toc`/`.aux` предыдущего прохода.

Проверка качества сборки:

```powershell
Select-String -Path main.log -Pattern "^! |Overfull \\hbox" | Measure-Object
```

Должно быть `Count = 0`. Если появились overfull — почти всегда виновата
таблица: увеличьте `\tabcolsep`-запас в `render_table()`
(`avail = 1.0 - 6.0 * (n - 1) / 487.0`).

## Требования

- **XeLaTeX** (не pdfLaTeX: нужны системные шрифты). Проверено на TinyTeX /
  TeX Live 2026.
- **Шрифты Windows:** `Segoe UI` (текст) и `Consolas` (моноширинный, `\texttt`).
  На macOS/Linux замените их в преамбуле `main.tex` на доступные кириллические
  (например, `PT Sans` + `PT Mono`).
- **Пакеты LaTeX:** `fontspec`, `polyglossia`, `babel-russian`, `hyphen-russian`,
  `geometry`, `xcolor` (с `table`), `longtable`, `array`, `booktabs`, `enumitem`,
  `graphicx`, `caption`, `amssymb`, `ragged2e`, `titlesec`, `fancyhdr`,
  `lastpage`, `hyperref`.

Установка недостающих пакетов в TinyTeX:

```powershell
tlmgr install --repository https://mirror.ctan.org/systems/texlive/tlnet `
  polyglossia babel-russian hyphen-russian colortbl booktabs titlesec `
  fancyhdr lastpage enumitem caption amsfonts ragged2e
```

## Устройство `build_tex.py`

- Заголовок `#` / `##` из Markdown → обложка; раздел `## Содержание` из
  Markdown выбрасывается, вместо него `\tableofcontents` (LaTeX строит своё).
- `##` → `\section` с `\clearpage` (каждый раздел с новой страницы),
  `###` → `\subsection`, `####` → `\subsubsection`.
- Таблицы Markdown → `longtable` с зеброй, ширины колонок считаются по длине
  текста; размер шрифта падает с 5 колонок (`\footnotesize`), 7 (`\scriptsize`),
  9 (`\tiny`).
- **Важно:** цвета в `\color{}`, `\colorbox{}`, `\rowcolor{}` задаются только
  именами (`vk`, `navy`, `blue`, `dark`, `grey`, `light`, `soft`, `zebra`),
  не hex-кодами — hex работает лишь в `\definecolor`.
- `&` внутри `\textcolor{...}{...}` всё равно делит колонки таблицы, поэтому
  каждая ячейка шапки красится отдельно.
- Символ `☐` заменяется на `$\square$`: в Segoe UI его нет.

## Что проверить после правок

1. `main.log` — нет `^!` и `Overfull \hbox`.
2. Оглавление: 13 разделов, номера страниц совпадают с фактическими.
3. Колонтитул: «стр. N из 36» на последней странице.
4. Рисунки: 16 штук, ни один не вылезает за поля.
