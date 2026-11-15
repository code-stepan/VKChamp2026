# -*- coding: utf-8 -*-
"""Собирает reports/tex/main.tex из reports/research_findings.md.

Картинки копируются в reports/tex/figures. Компиляция — XeLaTeX (см. README).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
TEX = REPORTS / "tex"
FIG = TEX / "figures"
MD = REPORTS / "research_findings.md"

VK = "0077FF"
NAVY = "0B2A5B"
BLUE = "0B3D91"
DARK = "1F2733"
GREY = "667085"
LIGHT = "E6ECF5"
SOFT = "F4F7FB"
ZEBRA = "F4F7FB"

MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "☐": r"$\square$",
}
TOKEN = re.compile(
    r"(\*\*.+?\*\*|`[^`\n]+`|(?<!\*)\*[^*\n]+?\*(?!\*)|\[[^\]]+\]\([^)]+\))"
)
IMG = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")


def esc(text: str) -> str:
    return "".join(MAP.get(ch, ch) for ch in text)


def inline(text: str) -> str:
    out = []
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            out.append(esc(text[pos:m.start()]))
        token = m.group(0)
        if token.startswith("**") and token.endswith("**"):
            out.append(r"\textbf{" + inline(token[2:-2]) + "}")
        elif token.startswith("`") and token.endswith("`"):
            out.append(r"\texttt{" + esc(token[1:-1]) + "}")
        elif token.startswith("["):
            lm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            label = inline(lm.group(1)) if lm else esc(token)
            url = lm.group(2).replace("%", r"\%").replace("#", r"\#") if lm else ""
            out.append(r"\href{" + url + "}{" + label + "}")
        elif token.startswith("*") and token.endswith("*"):
            out.append(r"\emph{" + inline(token[1:-1]) + "}")
        pos = m.end()
    if pos < len(text):
        out.append(esc(text[pos:]))
    return "".join(out)


def plain(text: str) -> str:
    """Текст без разметки — для оценки ширины колонок."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    return text


def strip_number(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title).strip()


def is_sep(line: str) -> bool:
    s = line.strip().strip("|")
    if not s:
        return False
    cells = [c.strip() for c in s.split("|")]
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


# ---------------------------------------------------------------------------
# Блоки
# ---------------------------------------------------------------------------
def render_table(header: list[str], rows: list[list[str]]) -> str:
    n = len(header)
    lens = []
    for j in range(n):
        vals = [plain(header[j])] + [plain(r[j]) if j < len(r) else "" for r in rows]
        lens.append(max(4, min(46, max(len(v) for v in vals))))
    total = sum(lens)
    # Полоса набора 17,2 см ≈ 487 pt; между колонками 2×3 pt.
    avail = 1.0 - 6.0 * (n - 1) / 487.0
    fracs = [avail * l / total for l in lens]

    if n >= 9:
        size = r"\tiny"
    elif n >= 7:
        size = r"\scriptsize"
    elif n >= 5:
        size = r"\footnotesize"
    else:
        size = r"\small"

    spec = "".join(
        r">{\raggedright\arraybackslash}p{%.4f\linewidth}" % f for f in fracs
    )
    head_cells = " & ".join(
        r"\textcolor{white}{\textbf{" + inline(c) + "}}" for c in header
    )
    head = head_cells + r" \\"
    body = []
    for row in rows:
        cells = [(row[j] if j < len(row) else "") for j in range(n)]
        body.append(" & ".join(inline(c) for c in cells) + r" \\")

    return "\n".join(
        [
            r"\begingroup",
            size,
            r"\setlength{\tabcolsep}{3pt}",
            r"\renewcommand{\arraystretch}{1.12}",
            r"\rowcolors{1}{white}{zebra}",
            r"\begin{longtable}{@{}" + spec + r"@{}}",
            r"\rowcolor{blue}",
            head,
            r"\endfirsthead",
            r"\rowcolor{blue}",
            head,
            r"\endhead",
            r"\hline",
            *body,
            r"\hline",
            r"\end{longtable}",
            r"\endgroup",
            r"\vspace{4pt}",
        ]
    )


def render_quote(text: str) -> str:
    return "\n".join(
        [
            r"\begin{quote}",
            r"\noindent\colorbox{soft}{\parbox{\dimexpr\linewidth-2\fboxsep}{",
            r"\raggedright " + inline(text),
            r"}}",
            r"\end{quote}",
            r"\vspace{2pt}",
        ]
    )


def render_list(items: list[str], numbered: bool) -> str:
    env = "enumerate" if numbered else "itemize"
    lines = [r"\begin{" + env + r"}[leftmargin=1.35em,itemsep=2pt,topsep=3pt,parsep=0pt]"]
    for item in items:
        lines.append(r"\item " + inline(item))
    lines.append(r"\end{" + env + "}")
    return "\n".join(lines)


def render_code(lines: list[str]) -> str:
    out = [r"\begin{flushleft}", r"\ttfamily\small", r"\begingroup\setlength{\parindent}{0pt}"]
    for line in lines:
        out.append(esc(line) + r"\\")
    out += [r"\endgroup", r"\end{flushleft}"]
    return "\n".join(out)


def render_figure(src: str, alt: str) -> str:
    path = resolve_image(src)
    if path is None:
        return r"\textit{[Не найден рисунок: " + esc(src) + "]}"
    name = path.name
    target = FIG / name
    if not target.exists():
        shutil.copy2(path, target)
    return "\n".join(
        [
            r"\begin{figure}[htbp]",
            r"\centering",
            r"\includegraphics[width=\linewidth,height=0.70\textheight,keepaspectratio]{figures/" + name + "}",
            r"\caption*{" + inline(alt) + "}",
            r"\end{figure}",
        ]
    )


def resolve_image(src: str) -> Path | None:
    src = src.replace("\\", "/").strip()
    for p in ((REPORTS / src).resolve(), (ROOT / src).resolve()):
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Разбор markdown
# ---------------------------------------------------------------------------
def parse_body(md: str) -> list[str]:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        if s.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append(render_code(code))
            continue

        if s == "---":
            i += 1
            continue

        m = re.match(r"^(#{2,4})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 2:
                out.append(r"\clearpage")
                out.append(r"\section{" + inline(strip_number(title)) + "}")
            elif level == 3:
                out.append(r"\subsection{" + inline(strip_number(title)) + "}")
            else:
                out.append(r"\subsubsection{" + inline(title) + "}")
            i += 1
            continue

        if s.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            if len(block) >= 2 and is_sep(block[1]):
                header = split_row(block[0])
                rows = [split_row(r) for r in block[2:]]
                width = len(header)
                rows = [r + [""] * (width - len(r)) if len(r) < width else r[:width] for r in rows]
                out.append(render_table(header, rows))
            else:
                for b in block:
                    out.append(inline(b.strip()) + r"\par")
            continue

        m = IMG.match(s)
        if m:
            out.append(render_figure(m.group(2), m.group(1)))
            i += 1
            continue

        if s.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q = lines[i].strip()[1:].strip()
                quote.append(q)
                i += 1
            out.append(render_quote(" ".join(quote)))
            continue

        if re.match(r"^[-*]\s+", s):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                i += 1
                while (i < len(lines) and lines[i].strip()
                       and not re.match(r"^[-*]\s+|^\d+\.\s+|^#|^\||^>|^```", lines[i].strip())
                       and not IMG.match(lines[i].strip())):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(item)
            out.append(render_list(items, numbered=False))
            continue

        if re.match(r"^\d+\.\s+", s):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                i += 1
                while (i < len(lines) and lines[i].strip()
                       and not re.match(r"^[-*]\s+|^\d+\.\s+|^#|^\||^>|^```", lines[i].strip())
                       and not IMG.match(lines[i].strip())):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(item)
            out.append(render_list(items, numbered=True))
            continue

        para = [s]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                break
            if (nxt.startswith("#") or nxt.startswith("|") or nxt.startswith(">")
                    or nxt.startswith("```") or nxt == "---"
                    or re.match(r"^[-*]\s+", nxt) or re.match(r"^\d+\.\s+", nxt)
                    or IMG.match(nxt)):
                break
            para.append(nxt)
            i += 1
        text = " ".join(para)
        if text.startswith("**") and text.endswith("**") and text.count("**") == 2:
            out.append(r"\noindent\textbf{" + inline(text[2:-2]) + r"}\par\vspace{4pt}")
        else:
            out.append(inline(text) + r"\par")
    return out


def build_cover(cover_md: str) -> str:
    title = ""
    subtitle = ""
    meta = []
    quote = ""
    for line in cover_md.splitlines():
        s = line.strip()
        if not s or s == "---":
            continue
        if s.startswith("# "):
            title = s[2:].strip()
        elif s.startswith("## "):
            subtitle = s[3:].strip()
        elif s.startswith(">"):
            quote = (quote + " " + s[1:].strip()).strip()
        elif s.startswith("**") and s.endswith("**") and len(s) < 400 and not meta:
            meta.append(s.strip("*"))
        elif s.startswith("Дата:"):
            meta.append(s)
    main, _, rest = title.partition(":")
    title_tex = "\n".join(
        [
            r"{\raggedright\fontsize{26}{31}\selectfont\bfseries\color{navy}" + inline(main) + r"\par}",
            r"\vspace{2pt}",
            r"{\raggedright\fontsize{21}{26}\selectfont\bfseries\color{blue}" + inline(rest.strip()) + r"\par}",
        ]
    )
    meta_par = "\n".join(
        r"{\small\color{dark}\raggedright " + inline(m) + r"\par}" for m in meta
    )
    quote_tex = ""
    if quote:
        quote_tex = "\n".join(
            [
                r"\vspace{18pt}",
                r"\noindent\colorbox{soft}{\parbox{\dimexpr\linewidth-2\fboxsep}{",
                r"\raggedright\color{navy}" + inline(quote),
                r"}}",
            ]
        )
    return "\n".join(
        [
            r"\begin{titlepage}",
            r"\thispagestyle{empty}",
            r"\noindent\colorbox{vk}{\parbox{\dimexpr\linewidth-2\fboxsep}{",
            r"\color{white}\small\bfseries VK CASE CHAMPIONSHIP 2026\ \ \textbullet\ \ ОТБОРОЧНЫЙ ЭТАП\ \ \textbullet\ \ КЕЙС «СОЦИАЛЬНАЯ КОММЕРЦИЯ»}}\par",
            r"\vspace*{56pt}",
            title_tex,
            r"\vspace{16pt}",
            r"{\Large\color{grey}" + inline(subtitle) + r"\par}",
            r"\vspace{30pt}",
            r"{\color{light}\rule{\linewidth}{1.2pt}}\par",
            r"\vspace{12pt}",
            meta_par,
            quote_tex,
            r"\vfill",
            r"{\footnotesize\color{grey}Материалы для команды: числа, логика, границы выводов и заготовки слайдов.\ Все расчёты воспроизводятся командой \texttt{python run\_all.py}.\par}",
            r"\end{titlepage}",
        ]
    )


PREAMBLE = r"""
\documentclass[10pt,a4paper]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\setdefaultlanguage{russian}
\setotherlanguage{english}
\setmainfont{Segoe UI}
\setsansfont{Segoe UI}
\setmonofont{Consolas}[Scale=0.92]

\usepackage[a4paper,top=2.0cm,bottom=2.0cm,left=1.9cm,right=1.9cm,headheight=14pt]{geometry}
\usepackage[table]{xcolor}
\definecolor{vk}{HTML}{__VK__}
\definecolor{navy}{HTML}{__NAVY__}
\definecolor{blue}{HTML}{__BLUE__}
\definecolor{dark}{HTML}{__DARK__}
\definecolor{grey}{HTML}{__GREY__}
\definecolor{light}{HTML}{__LIGHT__}
\definecolor{soft}{HTML}{__SOFT__}
\definecolor{zebra}{HTML}{__ZEBRA__}

\usepackage{longtable}
\usepackage{array}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{graphicx}
\usepackage{caption}
\usepackage{amssymb}
\usepackage{ragged2e}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage[hidelinks]{hyperref}

\hypersetup{
  pdftitle={Социальная коммерция ВКонтакте: результаты исследования},
  pdfauthor={Команда проекта},
  pdfsubject={VK Case Championship 2026, handover-документ},
  pdfkeywords={ВКонтакте, социальная коммерция, Маркет, e-commerce}
}

\linespread{1.12}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt plus 1pt}
\setlength{\emergencystretch}{3em}
\sloppy

\captionsetup{font={small,color=grey},justification=centering,skip=5pt}
\setlength{\LTpre}{6pt}
\setlength{\LTpost}{10pt}

\titleformat{\section}
  {\Large\bfseries\color{navy}}{\thesection}{0.55em}{}
  [\vspace{-2pt}{\color{light}\titlerule[1.1pt]}]
\titlespacing*{\section}{0pt}{6pt}{12pt}
\titleformat{\subsection}
  {\large\bfseries\color{blue}}{\thesubsection}{0.5em}{}
\titlespacing*{\subsection}{0pt}{14pt}{6pt}
\titleformat{\subsubsection}
  {\normalsize\bfseries\color{dark}}{\thesubsubsection}{0.5em}{}
\titlespacing*{\subsubsection}{0pt}{10pt}{4pt}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\color{grey}VK Case Championship 2026\ \textbullet\ handover}
\fancyhead[R]{\footnotesize\color{grey}\nouppercase{\leftmark}}
\fancyfoot[C]{\footnotesize\color{grey}стр. \thepage\ из \pageref{LastPage}}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{light}\leaders\hrule height \headrulewidth\hfill}}
\renewcommand{\footrulewidth}{0pt}

\begin{document}
""".replace("__VK__", VK).replace("__NAVY__", NAVY).replace("__BLUE__", BLUE) \
   .replace("__DARK__", DARK).replace("__GREY__", GREY).replace("__LIGHT__", LIGHT) \
   .replace("__SOFT__", SOFT).replace("__ZEBRA__", ZEBRA)


def main() -> None:
    TEX.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    md = MD.read_text(encoding="utf-8")
    idx = md.find("\n---\n")
    cover_md, body_md = (md[:idx], md[idx + 5:]) if idx != -1 else ("", md)

    # Выкидываем ручное оглавление из markdown: LaTeX строит своё.
    lines = body_md.splitlines()
    filtered = []
    skip = False
    for line in lines:
        s = line.strip()
        if re.match(r"^##\s+Содержание\s*$", s):
            skip = True
            continue
        if skip:
            if re.match(r"^##\s+", s):
                skip = False
            else:
                continue
        filtered.append(line)
    body_md = "\n".join(filtered)

    parts = [
        PREAMBLE,
        build_cover(cover_md),
        r"\setcounter{page}{2}",
        r"\clearpage",
        r"{\small",
        r"\tableofcontents",
        r"}",
        *parse_body(body_md),
        r"\end{document}",
    ]
    tex = "\n\n".join(parts)
    (TEX / "main.tex").write_text(tex, encoding="utf-8")
    print("tex:", TEX / "main.tex", len(tex), "chars")
    print("figures:", len(list(FIG.glob('*.png'))))


if __name__ == "__main__":
    main()
