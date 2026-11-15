# -*- coding: utf-8 -*-
"""Собирает self-contained HTML и DOCX из research_findings.md.

HTML: все картинки встраиваются base64, стили внутри файла — можно отправлять
одним файлом. DOCX: A4, таблицы, подписи к рисункам, нумерация страниц.
"""
from __future__ import annotations

import base64
import html
import mimetypes
import re
from pathlib import Path

import markdown
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

REPORTS = Path(__file__).resolve().parent
ROOT = REPORTS.parent
MD_PATH = REPORTS / "research_findings.md"
HTML_PATH = REPORTS / "research_findings.html"
DOCX_PATH = REPORTS / "research_findings.docx"

VK = "0077FF"
DARK = "1F2733"
NAVY = "0B2A5B"
BLUE = "0B3D91"
GREY = "667085"
LIGHT = "E6ECF5"
SOFT = "F4F7FB"

MD_EXTENSIONS = ["tables", "sane_lists", "fenced_code", "attr_list", "toc"]


# ---------------------------------------------------------------------------
# Общие утилиты
# ---------------------------------------------------------------------------
def read_markdown() -> str:
    return MD_PATH.read_text(encoding="utf-8")


def split_cover(text: str) -> tuple[str, str]:
    marker = "\n---\n"
    idx = text.find(marker)
    if idx == -1:
        return "", text
    return text[:idx], text[idx + len(marker):]


def resolve_image(src: str) -> Path | None:
    src = src.replace("\\", "/").strip()
    if src.startswith("http://") or src.startswith("https://"):
        return None
    candidates = []
    if src.startswith("../outputs/"):
        candidates.append((REPORTS / src).resolve())
    elif src.startswith("outputs/"):
        candidates.append(ROOT / src)
    else:
        candidates.append((REPORTS / src).resolve())
        candidates.append((ROOT / src).resolve())
    for p in candidates:
        if p.exists():
            return p
    return None


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
CSS = r"""
:root {
  --vk: #0077FF;
  --navy: #0B2A5B;
  --blue: #0B3D91;
  --dark: #1F2733;
  --grey: #667085;
  --light: #E6ECF5;
  --soft: #F4F7FB;
  --good: #2BB673;
  --bad: #D64545;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: #EEF2F8;
  color: var(--dark);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.65;
}
.cover {
  background:
    radial-gradient(1200px 500px at 85% 10%, rgba(0,119,255,.45), transparent 60%),
    linear-gradient(135deg, #071426 0%, #0A2E66 55%, #0B4DA2 100%);
  color: #fff;
  padding: 78px 8vw 64px;
  min-height: 78vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.cover h1 {
  font-size: clamp(30px, 4.4vw, 54px);
  line-height: 1.08;
  margin: 0 0 14px;
  max-width: 980px;
  letter-spacing: -0.02em;
}
.cover h2 {
  font-size: clamp(18px, 2vw, 26px);
  font-weight: 500;
  margin: 0 0 24px;
  color: #DCE9FA;
  max-width: 900px;
}
.cover p {
  max-width: 900px;
  color: #EAF2FF;
  font-size: 15px;
  line-height: 1.65;
}
.cover p strong { color: #fff; }
.cover blockquote {
  margin: 26px 0 0;
  max-width: 940px;
  background: rgba(255,255,255,.10);
  border-left: 4px solid #7FB3FF;
  border-radius: 10px;
  padding: 16px 22px;
  color: #EAF2FF;
  font-size: 15px;
}
.cover blockquote p { margin: 0; }
main {
  max-width: 1120px;
  margin: -32px auto 0;
  background: #fff;
  padding: 46px 6vw 70px;
  border-radius: 18px 18px 0 0;
  box-shadow: 0 18px 50px rgba(11, 42, 91, .10);
}
h2 {
  font-size: 28px;
  line-height: 1.2;
  color: var(--navy);
  margin: 54px 0 14px;
  padding-top: 26px;
  border-top: 2px solid var(--light);
  page-break-before: always;
}
h2:first-of-type { border-top: none; padding-top: 0; margin-top: 0; }
h3 {
  font-size: 21px;
  line-height: 1.25;
  color: var(--blue);
  margin: 30px 0 10px;
  page-break-after: avoid;
}
h4 {
  font-size: 17px;
  color: var(--dark);
  margin: 22px 0 8px;
  page-break-after: avoid;
}
p { margin: 0 0 12px; }
ul, ol { margin: 0 0 16px; padding-left: 26px; }
li { margin: 4px 0; }
strong { color: #111827; }
a { color: var(--vk); text-decoration: none; }
a:hover { text-decoration: underline; }
code {
  background: #F0F3F8;
  border: 1px solid #E1E7F0;
  border-radius: 5px;
  padding: 1px 5px;
  font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
  font-size: 0.88em;
}
pre {
  background: #0F172A;
  color: #E6EDF7;
  padding: 16px 18px;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}
pre code { background: none; border: none; color: inherit; padding: 0; }
blockquote {
  margin: 16px 0 20px;
  background: #F0F6FF;
  border-left: 4px solid var(--vk);
  border-radius: 8px;
  padding: 13px 18px;
  color: #17385F;
}
blockquote p { margin: 0; }
hr {
  border: 0;
  height: 1px;
  background: var(--light);
  margin: 34px 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0 26px;
  font-size: 13.2px;
  line-height: 1.45;
  box-shadow: 0 1px 0 var(--light);
  page-break-inside: auto;
}
thead { display: table-header-group; }
th {
  background: var(--blue);
  color: #fff;
  text-align: left;
  padding: 8px 10px;
  border: 1px solid #154A9E;
  font-weight: 600;
  vertical-align: bottom;
}
td {
  padding: 7px 10px;
  border: 1px solid #DDE4EF;
  vertical-align: top;
}
tbody tr:nth-child(even) { background: var(--soft); }
tbody tr:hover { background: #EAF2FF; }
.table-wrap {
  margin: 14px 0 26px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.table-wrap table { margin: 0; }
figure {
  margin: 24px 0 28px;
  page-break-inside: avoid;
}
figure img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid var(--light);
  border-radius: 12px;
  background: #fff;
}
figcaption {
  margin-top: 9px;
  color: var(--grey);
  font-size: 13px;
  text-align: center;
}
.cover + main { position: relative; }
footer.doc-footer {
  max-width: 1120px;
  margin: 0 auto;
  padding: 18px 6vw 40px;
  color: #8A94A6;
  font-size: 12.5px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
}
@media (max-width: 760px) {
  body { font-size: 15px; }
  .cover { padding: 54px 6vw 46px; min-height: auto; }
  main { margin-top: 0; border-radius: 0; padding: 34px 5vw 50px; }
  table { font-size: 12px; }
  th, td { padding: 6px 7px; }
  footer.doc-footer { padding: 16px 5vw 30px; }
}
@page { size: A4; margin: 15mm; }
@media print {
  body { background: #fff; font-size: 11pt; }
  .cover { min-height: auto; page-break-after: always; }
  main { box-shadow: none; margin: 0; max-width: none; padding: 0; border-radius: 0; }
  h2 { page-break-before: always; }
  h2:first-of-type { page-break-before: auto; }
  table { page-break-inside: auto; }
  tr { page-break-inside: avoid; }
  figure { page-break-inside: avoid; }
  footer.doc-footer { display: none; }
}
"""


def render_html_fragment(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=MD_EXTENSIONS)


def embed_images(fragment: str) -> str:
    def repl(match: re.Match) -> str:
        alt_raw, src_raw = match.group(1), match.group(2)
        alt = html.unescape(alt_raw)
        path = resolve_image(html.unescape(src_raw))
        if path is None:
            return match.group(0)
        uri = data_uri(path)
        return (
            f'<figure><img src="{uri}" alt="{html.escape(alt)}" decoding="async">'
            f'<figcaption>{html.escape(alt)}</figcaption></figure>'
        )

    fragment = re.sub(
        r'<p><img alt="([^"]*)" src="([^"]*)" /></p>',
        repl,
        fragment,
    )
    # На случай, если картинка оказалась не в отдельном <p>.
    fragment = re.sub(
        r'<img alt="([^"]*)" src="([^"]*)" />',
        lambda m: repl(m) if resolve_image(html.unescape(m.group(2))) else m.group(0),
        fragment,
    )
    # Таблицы прокручиваются горизонтально на узких экранах, а не рвут вёрстку.
    fragment = fragment.replace("<table>", '<div class="table-wrap"><table>')
    fragment = fragment.replace("</table>", "</table></div>")
    return fragment


def build_html() -> Path:
    text = read_markdown()
    cover_md, body_md = split_cover(text)
    cover_html = embed_images(render_html_fragment(cover_md))
    body_html = embed_images(render_html_fragment(body_md))

    title_match = re.search(r"^#\s+(.+)$", cover_md, flags=re.M)
    doc_title = title_match.group(1).strip() if title_match else "Результаты исследования"
    doc_title = re.sub(r"\*\*", "", doc_title)

    html_doc = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(doc_title)}</title>
<style>{CSS}</style>
</head>
<body>
<section class="cover">
{cover_html}
</section>
<main>
{body_html}
</main>
<footer class="doc-footer">
  <span>VK Case Championship 2026 · handover-документ</span>
  <span>Данные: сентябрь 2026 · версия 1.0</span>
</footer>
</body>
</html>
"""
    HTML_PATH.write_text(html_doc, encoding="utf-8")
    print(f"HTML: {HTML_PATH} ({HTML_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
    return HTML_PATH


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------
TOKEN_RE = re.compile(
    r"(\*\*.+?\*\*|\*[^*\n]+?\*|`[^`\n]+`|\[[^\]]+\]\([^)]+\))"
)


def set_run_font(run, name: str = "Segoe UI", size: float | None = None,
                 color: str | None = None, bold: bool | None = None,
                 italic: bool | None = None) -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_inline(paragraph, text: str, size: float = 10.5,
               color: str | None = None, base_bold: bool = False,
               base_italic: bool = False) -> None:
    pos = 0
    for match in TOKEN_RE.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos:match.start()])
            set_run_font(run, size=size, color=color, bold=base_bold, italic=base_italic)
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, size=size, color=color, bold=True, italic=base_italic)
        elif token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, name="Consolas", size=size - 0.7, color="1F3A5F",
                         bold=base_bold, italic=False)
        elif token.startswith("["):
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            label = m.group(1) if m else token
            run = paragraph.add_run(label)
            set_run_font(run, size=size, color=VK, bold=base_bold, italic=base_italic)
            run.underline = True
        else:
            run = paragraph.add_run(token.strip("*"))
            set_run_font(run, size=size, color=color, bold=base_bold, italic=True)
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, size=size, color=color, bold=base_bold, italic=base_italic)


def add_para(doc, text: str, size: float = 10.5, color: str | None = None,
             space_after: float = 6, align=None, bold: bool = False,
             italic: bool = False) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.15
    if align is not None:
        p.alignment = align
    add_inline(p, text, size=size, color=color, base_bold=bold, base_italic=italic)


def add_heading(doc, text: str, level: int, page_break: bool = False) -> None:
    p = doc.add_heading(level=level)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(12 if level > 1 else 0)
    p.paragraph_format.space_after = Pt(6)
    if page_break:
        p.paragraph_format.page_break_before = True
    size = {1: 26, 2: 18, 3: 14, 4: 11.5}.get(level, 11)
    color = {1: NAVY, 2: BLUE, 3: BLUE, 4: DARK}.get(level, DARK)
    run = p.add_run(re.sub(r"\*\*", "", text))
    set_run_font(run, size=size, color=color, bold=True)


def shade_paragraph(p, fill: str) -> None:
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def border_paragraph(p, side: str = "bottom", color: str = LIGHT,
                     size: int = 8) -> None:
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), "4")
    el.set(qn("w:color"), color)
    pBdr.append(el)
    pPr.append(pBdr)


def add_blockquote(doc, text: str) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.45)
    pf.right_indent = Cm(0.2)
    pf.space_before = Pt(4)
    pf.space_after = Pt(10)
    pf.line_spacing = 1.15
    shade_paragraph(p, "F0F6FF")
    border_paragraph(p, "left", VK, 18)
    add_inline(p, text, size=10.2, color="17385F")


def add_bullet(doc, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.12
    add_inline(p, text, size=10.3)


def add_numbered(doc, text: str, num: int) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.65)
    pf.first_line_indent = Cm(-0.45)
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.12
    run = p.add_run(f"{num}. ")
    set_run_font(run, size=10.3, color=BLUE, bold=True)
    add_inline(p, text, size=10.3)


def add_code_block(doc, lines: list[str]) -> None:
    for line in lines:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.3)
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        shade_paragraph(p, "F4F6FA")
        run = p.add_run(line if line else " ")
        set_run_font(run, name="Consolas", size=9, color="1F3A5F")


def set_cell_shading(cell, fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def set_cell_margins(cell, top: int = 50, bottom: int = 50,
                     left: int = 70, right: int = 70) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for key, val in (("top", top), ("bottom", bottom),
                     ("left", left), ("right", right)):
        el = OxmlElement(f"w:{key}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        tcMar.append(el)
    tcPr.append(tcMar)


def set_row_flags(row, header: bool = False) -> None:
    trPr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    trPr.append(cant)
    if header:
        hdr = OxmlElement("w:tblHeader")
        hdr.set(qn("w:val"), "true")
        trPr.append(hdr)


def add_table(doc, header: list[str], rows: list[list[str]]) -> None:
    n_cols = len(header)
    if n_cols == 0:
        return
    table = doc.add_table(rows=1, cols=n_cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    table.allow_autofit = True

    font_size = 7.6 if n_cols >= 8 else (8.1 if n_cols >= 6 else 8.7)

    hdr = table.rows[0]
    set_row_flags(hdr, header=True)
    for j, text in enumerate(header):
        cell = hdr.cells[j]
        set_cell_shading(cell, BLUE)
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        add_inline(p, text, size=font_size, color="FFFFFF", base_bold=True)

    for i, row in enumerate(rows):
        cells = table.add_row()
        set_row_flags(cells)
        for j in range(n_cols):
            text = row[j] if j < len(row) else ""
            cell = cells.cells[j]
            if i % 2 == 1:
                set_cell_shading(cell, SOFT)
            set_cell_margins(cell)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            add_inline(p, text, size=font_size, color=DARK)

    # Оценка ширин по длине текста, чтобы длинные колонки не сжимались.
    lengths = []
    for j in range(n_cols):
        vals = [header[j]] + [r[j] if j < len(r) else "" for r in rows]
        lengths.append(max(6, min(38, max(len(v) for v in vals))))
    total = sum(lengths)
    usable = 16.3  # см, ширина полосы набора
    widths = [max(1.15, usable * lengths[j] / total) for j in range(n_cols)]
    scale = min(1.0, usable / sum(widths))
    widths = [w * scale for w in widths]

    table.autofit = False
    for j, width in enumerate(widths):
        table.columns[j].width = Cm(width)
    for row in table.rows:
        for j, cell in enumerate(row.cells):
            cell.width = Cm(widths[j])

    # Минимальный отступ после таблицы, не занимающий полноценную строку.
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = Pt(2)
    run = p.add_run(" ")
    set_run_font(run, size=1)


def add_image(doc, src: str, alt: str) -> None:
    path = resolve_image(src)
    if path is None:
        add_para(doc, f"[Не найден файл: {src}]", size=9, color="D64545")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(16.2))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    add_inline(cap, alt, size=8.6, color=GREY, base_italic=True)


def is_table_separator(line: str) -> bool:
    s = line.strip().strip("|")
    if not s:
        return False
    cells = [c.strip() for c in s.split("|")]
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def parse_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    rows = []
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        rows.append([c.strip() for c in s.split("|")])
    if not rows:
        return [], []
    header = rows[0]
    body = rows[1:]
    if body and is_table_separator(lines[1]):
        body = body[1:]
    width = len(header)
    body = [r + [""] * (width - len(r)) if len(r) < width else r[:width] for r in body]
    return header, body


def add_hr(doc) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    border_paragraph(p, "bottom", LIGHT, 6)


def docx_blocks(doc, md_text: str, cover: bool = False) -> None:
    lines = md_text.splitlines()
    i = 0
    first_body_h2 = not cover
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Fenced code
        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            add_code_block(doc, code_lines)
            continue

        # Horizontal rule
        if stripped == "---":
            add_hr(doc)
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            page_break = False
            if level == 2 and not cover:
                if first_body_h2:
                    first_body_h2 = False
                else:
                    page_break = True
            add_heading(doc, text, level, page_break=page_break)
            i += 1
            continue

        # Table
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            if len(table_lines) >= 2 and is_table_separator(table_lines[1]):
                header, rows = parse_table(table_lines)
                add_table(doc, header, rows)
            else:
                for tl in table_lines:
                    add_para(doc, tl)
            continue

        # Image
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if m:
            add_image(doc, m.group(2), m.group(1))
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q = lines[i].strip()
                q = q[1:].strip() if q.startswith(">") else q
                quote_lines.append(q)
                i += 1
            add_blockquote(doc, " ".join(quote_lines))
            continue

        # Bullet list
        if re.match(r"^[-*]\s+", stripped):
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                add_bullet(doc, item)
                i += 1
            continue

        # Numbered list
        if re.match(r"^\d+\.\s+", stripped):
            n = 1
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                add_numbered(doc, item, n)
                n += 1
                i += 1
            continue

        # Paragraph: collect until blank or a block start
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                break
            if (nxt.startswith("#") or nxt.startswith("|") or nxt.startswith(">")
                    or nxt.startswith("```") or nxt == "---"
                    or re.match(r"^[-*]\s+", nxt)
                    or re.match(r"^\d+\.\s+", nxt)
                    or re.match(r"^!\[[^\]]*\]\([^)]+\)$", nxt)):
                break
            para_lines.append(nxt)
            i += 1
        add_para(doc, " ".join(para_lines))


def add_page_number_footer(section) -> None:
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("VK Case Championship 2026 · handover-документ · стр. ")
    set_run_font(run, size=8.5, color="8A94A6")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    p._p.append(fld)


def build_docx() -> Path:
    text = read_markdown()
    cover_md, body_md = split_cover(text)

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.7)
    section.left_margin = Cm(1.9)
    section.right_margin = Cm(1.9)

    normal = doc.styles["Normal"]
    normal.font.name = "Segoe UI"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Segoe UI")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for level in (1, 2, 3, 4):
        style = doc.styles[f"Heading {level}"]
        style.font.name = "Segoe UI"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Segoe UI")
        style.font.color.rgb = RGBColor.from_string(
            {1: NAVY, 2: BLUE, 3: BLUE, 4: DARK}[level]
        )

    add_page_number_footer(section)

    # Титульная часть
    docx_blocks(doc, cover_md, cover=True)
    doc.add_page_break()

    # Основной текст
    docx_blocks(doc, body_md, cover=False)

    doc.core_properties.title = "Социальная коммерция ВКонтакте: результаты исследования"
    doc.core_properties.subject = "VK Case Championship 2026 · handover"
    doc.core_properties.author = "Команда проекта"
    doc.core_properties.comments = "Собрано из research_findings.md; числа воспроизводятся run_all.py."

    doc.save(DOCX_PATH)
    print(f"DOCX: {DOCX_PATH} ({DOCX_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
    return DOCX_PATH


if __name__ == "__main__":
    if not MD_PATH.exists():
        raise SystemExit(f"Нет файла: {MD_PATH}")
    build_html()
    build_docx()
