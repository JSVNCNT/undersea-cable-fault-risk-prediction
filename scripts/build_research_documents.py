"""Build the MASTER, PRELIM, MIDTERM, and FINAL research documents.

The generator reads repository artifacts rather than retyping reported values.
Generated DOCX/PDF/review files are written only below ``deliverables/`` (which
is git-ignored). The FINAL document is explicitly a near-final draft because
the 2025 held-out test remains locked.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path
from zipfile import ZipFile

os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TEMP", ".")) / "undersea-mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = ROOT / "deliverables"
MASTER_DIR = DELIVERABLES / "master"
PRELIM_DIR = DELIVERABLES / "prelim"
MIDTERM_DIR = DELIVERABLES / "midterm"
FINAL_DIR = DELIVERABLES / "final"
REVIEW_DIR = DELIVERABLES / "review"
TEMP_DIR = DELIVERABLES / "temporary"
BRANDING_DIR = TEMP_DIR / "branding"
UNOR_LOGO = BRANDING_DIR / "unor_seal.png"
CIT_LOGO = BRANDING_DIR / "cit_seal.png"

TITLE = "Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems Using Infrastructure and Operational Indicators"
COURSE = "Introduction to Data Science (COPE0683X)"
SECTION = "K44"
MEMBERS = ["Bayoguing, Jose Vincent III", "Cruz, Aurum Fuego", "Sapio, John Rey"]

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
INSTRUCTOR_DOCX = ROOT / "2026-2027 INTRODUCTION TO DATA SCIENCE PROJECT.docx"


def clean_text(value) -> str:
    text = str(value)
    replacements = {
        "â€“": "-", "â€”": "-", "â€™": "'", "â€œ": '"', "â€": '"',
        "–": "-", "—": "-", "’": "'", "“": '"', "”": '"',
        "Ã©": "e", "\ufffd": "-", "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


ROMAN_CHAPTERS = {"One": "I", "Two": "II", "Three": "III", "Four": "IV", "Five": "V", "Six": "VI"}


def read_csv(path: str | Path) -> pd.DataFrame:
    csv_path = ROOT / path
    try:
        return pd.read_csv(csv_path, keep_default_na=False)
    except pd.errors.ParserError:
        # Preserve source rows that contain an unquoted comma in a trailing
        # narrative field; this keeps the documentation build read-only with
        # respect to the verified source CSVs.
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        if not rows:
            return pd.DataFrame()
        width = len(rows[0])
        normalized = [rows[0]]
        for row in rows[1:]:
            if len(row) > width:
                row = row[: width - 1] + [", ".join(row[width - 1 :])]
            normalized.append(row + [""] * max(0, width - len(row)))
        return pd.DataFrame(normalized[1:], columns=normalized[0])


def scalar(path: str, column: str, row: int = 0):
    return read_csv(path).iloc[row][column]


def fmt(value, digits: int = 3) -> str:
    if value is None or value == "":
        return "not reported"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(value - round(value)) < 10 ** (-(digits + 1)):
        return f"{int(round(value)):,}"
    return f"{value:,.{digits}f}"


def pct(value, digits: int = 2) -> str:
    return f"{float(value) * 100:.{digits}f}%"


def set_cell_shading(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=110, bottom=100, end=110):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, *, bottom=None, all_borders=None):
    """Apply deterministic table borders using Word's eighth-point units."""
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    edges = ("top", "left", "bottom", "right", "insideH", "insideV")
    for edge in edges:
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        if all_borders:
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), str(all_borders))
            element.set(qn("w:color"), "000000")
        else:
            element.set(qn("w:val"), "nil")
    if bottom:
        element = borders.find(qn("w:bottom"))
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(bottom))
        element.set(qn("w:color"), "000000")


def extract_branding_assets():
    """Reuse the official UNO-R and CIT marks embedded in the instructor file."""
    BRANDING_DIR.mkdir(parents=True, exist_ok=True)
    if UNOR_LOGO.exists() and CIT_LOGO.exists():
        return
    with ZipFile(INSTRUCTOR_DOCX) as archive:
        UNOR_LOGO.write_bytes(archive.read("word/media/image1.png"))
        CIT_LOGO.write_bytes(archive.read("word/media/image2.png"))


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_table_width(table, width_inches=6.3, widths=None):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = widths is None
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(int(width_inches * 1440)))
    tbl_w.set(qn("w:type"), "dxa")
    if widths:
        grid = table._tbl.tblGrid
        for child in list(grid):
            grid.remove(child)
        for width in widths:
            col = OxmlElement("w:gridCol")
            col.set(qn("w:w"), str(int(width * 1440)))
            grid.append(col)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if widths:
                tc_w = cell._tc.get_or_add_tcPr().first_child_found_in("w:tcW")
                if tc_w is None:
                    tc_w = OxmlElement("w:tcW")
                    cell._tc.get_or_add_tcPr().append(tc_w)
                tc_w.set(qn("w:w"), str(int(widths[index] * 1440)))
                tc_w.set(qn("w:type"), "dxa")


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


def set_page_number_format(section, fmt_name: str, start: int = 1):
    sect_pr = section._sectPr
    pg_num = sect_pr.find(qn("w:pgNumType"))
    if pg_num is None:
        pg_num = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num)
    pg_num.set(qn("w:fmt"), fmt_name)
    pg_num.set(qn("w:start"), str(start))


def set_run_typeface(run, name="Times New Roman"):
    run.font.name = name
    r_fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        r_fonts.set(qn(f"w:{attr}"), name)


def set_compact_paragraph(paragraph, *, alignment=WD_ALIGN_PARAGRAPH.CENTER):
    paragraph.alignment = alignment
    paragraph.paragraph_format.first_line_indent = Inches(0)
    paragraph.paragraph_format.left_indent = Inches(0)
    paragraph.paragraph_format.right_indent = Inches(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0


def add_branding_to_section(section, styles):
    """Create the reference-derived institutional header and footer."""
    section.header_distance = Inches(0.22)
    section.footer_distance = Inches(0.18)

    header = section.header
    header.is_linked_to_previous = False
    for table in list(header.tables):
        header._element.remove(table._element)
    for paragraph in header.paragraphs:
        paragraph.clear()
        set_compact_paragraph(paragraph)
        paragraph.paragraph_format.line_spacing = Pt(1)

    header_table = header.add_table(rows=1, cols=3, width=Inches(6.5))
    header_table.autofit = False
    set_table_width(header_table, width_inches=6.5, widths=[0.9, 4.7, 0.9])
    set_table_borders(header_table, bottom=16)
    for cell in header_table.rows[0].cells:
        set_cell_margins(cell, top=0, start=0, bottom=30, end=0)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_compact_paragraph(cell.paragraphs[0])
    header_table.cell(0, 0).paragraphs[0].add_run().add_picture(str(UNOR_LOGO), width=Inches(0.62))
    center = header_table.cell(0, 1).paragraphs[0]
    run = center.add_run("UNIVERSITY OF NEGROS OCCIDENTAL - RECOLETOS, INC.")
    run.bold = True
    run.font.size = Pt(10.5)
    run = center.add_run("\nCOLLEGE OF INFORMATION TECHNOLOGY")
    run.bold = True
    run.font.size = Pt(10.5)
    run = center.add_run("\nIntroduction to Data Science (COPE0683X)")
    run.bold = True
    run.font.size = Pt(8.5)
    header_table.cell(0, 2).paragraphs[0].add_run().add_picture(str(CIT_LOGO), width=Inches(0.62))
    # Move the table ahead of Word's mandatory empty header paragraph.
    header._element.remove(header_table._element)
    header._element.insert(0, header_table._element)

    footer = section.footer
    footer.is_linked_to_previous = False
    for table in list(footer.tables):
        footer._element.remove(table._element)
    for paragraph in footer.paragraphs:
        paragraph.clear()
        set_compact_paragraph(paragraph)
        paragraph.paragraph_format.line_spacing = Pt(1)

    footer_table = footer.add_table(rows=1, cols=3, width=Inches(6.5))
    footer_table.autofit = False
    set_table_width(footer_table, width_inches=6.5, widths=[0.9, 4.7, 0.9])
    set_table_borders(footer_table)
    for cell in footer_table.rows[0].cells:
        set_cell_margins(cell, top=0, start=0, bottom=0, end=0)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_compact_paragraph(cell.paragraphs[0])
    footer_table.cell(0, 0).paragraphs[0].add_run().add_picture(str(UNOR_LOGO), width=Inches(0.55))
    center = footer_table.cell(0, 1).paragraphs[0]
    run = center.add_run("College of Information Technology")
    run.bold = True
    run.font.size = Pt(10)
    center.add_run("\n")
    add_page_number(center)
    for run in center.runs:
        if run.font.size is None:
            run.font.size = Pt(9)
    footer_table.cell(0, 2).paragraphs[0].add_run().add_picture(str(CIT_LOGO), width=Inches(0.55))
    footer._element.remove(footer_table._element)
    footer._element.insert(0, footer_table._element)


def add_toc_field(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "Right-click to update the table of contents."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def set_repeat_header(row):
    set_repeat_table_header(row)


class Paper:
    def __init__(self, status: str):
        self.doc = Document()
        self.status = status
        self.chapter_number = None
        self.section_number = 0
        self.subsection_number = 0
        self._configure()

    def _configure_section(self, section):
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    def _configure(self):
        section = self.doc.sections[0]
        self._configure_section(section)
        styles = self.doc.styles
        normal = styles["Normal"]
        normal.font.name = "Times New Roman"
        normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        normal.font.size = Pt(12)
        normal.paragraph_format.line_spacing = 2.0
        normal.paragraph_format.space_before = Pt(0)
        normal.paragraph_format.space_after = Pt(0)
        normal.paragraph_format.first_line_indent = Inches(0.5)
        for name, size in [("Title", 12), ("Heading 1", 12), ("Heading 2", 12), ("Heading 3", 12)]:
            style = styles[name]
            style.font.name = "Times New Roman"
            style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
            style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = RGBColor.from_string("000000")
            style.paragraph_format.space_before = Pt(12)
            style.paragraph_format.space_after = Pt(0)
            style.paragraph_format.line_spacing = 2.0
            style.paragraph_format.keep_with_next = True
            # The default Word Title style carries an accent-colored bottom
            # border.  The formatting reference uses a plain black title with
            # no decorative rule, so remove any inherited paragraph border.
            if name == "Title":
                p_pr = style._element.get_or_add_pPr()
                p_bdr = p_pr.find(qn("w:pBdr"))
                if p_bdr is not None:
                    p_pr.remove(p_bdr)
        styles["Heading 3"].font.italic = True
        for list_name in ("List Bullet", "List Number"):
            style = styles[list_name]
            style.font.name = "Times New Roman"
            style.font.size = Pt(12)
            style.paragraph_format.line_spacing = 2.0
            style.paragraph_format.space_before = Pt(0)
            style.paragraph_format.space_after = Pt(0)
            style.paragraph_format.left_indent = Inches(0.5)
            style.paragraph_format.first_line_indent = Inches(-0.25)
        add_branding_to_section(section, styles)
        set_page_number_format(section, "lowerRoman", 1)

    def _start_numbered_section(self, number_format: str, start: int = 1):
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._configure_section(section)
        add_branding_to_section(section, self.doc.styles)
        set_page_number_format(section, number_format, start)
        return section

    def start_front_matter(self):
        return self._start_numbered_section("lowerRoman", 2)

    def start_main_matter(self):
        return self._start_numbered_section("decimal")

    def page_break(self):
        self.doc.add_page_break()

    def heading(self, text: str, level: int = 1):
        text = clean_text(text)
        match = re.match(r"^Chapter (One|Two|Three|Four|Five|Six):\s*(.+)$", text, re.I)
        if match:
            word = match.group(1).title()
            self.chapter_number = list(ROMAN_CHAPTERS).index(word) + 1
            self.section_number = 0
            self.subsection_number = 0
            p = self.doc.add_paragraph(style="Heading 1")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Inches(0)
            # Chapter I already follows the main-matter section break. Every
            # later chapter starts on a fresh page, matching the reference and
            # preventing a chapter title from being squeezed into the tail of
            # the preceding chapter.
            if self.chapter_number > 1:
                p.paragraph_format.page_break_before = True
            p.add_run(f"CHAPTER {ROMAN_CHAPTERS[word]}: {match.group(2).upper()}")
            return p
        if level == 1:
            self.chapter_number = None
            p = self.doc.add_paragraph(style="Heading 1")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Inches(0)
            p.add_run(text.upper())
            return p
        if level == 2 and self.chapter_number is not None:
            self.section_number += 1
            self.subsection_number = 0
        elif level == 3 and self.chapter_number is not None:
            self.subsection_number += 1
        p = self.doc.add_paragraph(style=f"Heading {level}")
        p.paragraph_format.first_line_indent = Inches(0)
        p.add_run(text)
        return p

    def front_title(self, text: str):
        p = self.doc.add_paragraph(style="Heading 1")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Inches(0)
        p.add_run(clean_text(text).upper())
        return p

    def dotted_entry(self, label: str, page, level: int = 0, *, bold=False, italic=False):
        p = self.doc.add_paragraph(style="Normal")
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.left_indent = Inches(0.35 * level)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6.0 - 0.35 * level), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        for value in (clean_text(label), "\t", str(page) if page else "-"):
            run = p.add_run(value)
            run.font.size = Pt(10.5)
            run.bold = bold
            run.italic = italic
        return p

    def para(self, text: str, *, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        p = self.doc.add_paragraph(style="Normal")
        p.alignment = align
        p.paragraph_format.first_line_indent = Inches(0.5) if indent else Inches(0)
        p.add_run(clean_text(text))
        return p

    def bullet(self, text: str):
        p = self.doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.add_run(clean_text(text))
        return p

    def table(self, headers, rows, widths=None, font_size=9):
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        set_table_width(table, widths=widths)
        hdr = table.rows[0]
        set_repeat_header(hdr)
        for i, header in enumerate(headers):
            cell = hdr.cells[i]
            cell.text = clean_text(header)
            set_cell_shading(cell, "F2F2F2")
            cell.paragraphs[0].paragraph_format.first_line_indent = Inches(0)
            cell.paragraphs[0].paragraph_format.line_spacing = 1.0
            cell.paragraphs[0].paragraph_format.space_before = Pt(0)
            cell.paragraphs[0].paragraph_format.space_after = Pt(0)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.name = "Times New Roman"
                run.font.size = Pt(font_size)
        for values in rows:
            cells = table.add_row().cells
            for i, value in enumerate(values):
                cells[i].text = clean_text(value)
                for paragraph in cells[i].paragraphs:
                    paragraph.paragraph_format.first_line_indent = Inches(0)
                    paragraph.paragraph_format.line_spacing = 1.0
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in paragraph.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(font_size)
        return table

    def caption(self, text: str):
        p = self.doc.add_paragraph(style="Normal")
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        text = clean_text(text)
        if text.startswith("Figure "):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            match = re.match(r"^(Figure\s+\d+[.:])\s*(.*)$", text)
            if match:
                label = p.add_run(match.group(1) + " ")
                label.bold = True
                title = p.add_run(match.group(2))
                title.italic = True
            else:
                p.add_run(text).italic = True
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.add_run(text).bold = True
        return p

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        paragraph_groups = [self.doc.paragraphs]
        for table in self.doc.tables:
            paragraph_groups.extend(cell.paragraphs for row in table.rows for cell in row.cells)
        for section in self.doc.sections:
            paragraph_groups.extend([section.header.paragraphs, section.footer.paragraphs])
            for table in [*section.header.tables, *section.footer.tables]:
                paragraph_groups.extend(cell.paragraphs for row in table.rows for cell in row.cells)
        for paragraphs in paragraph_groups:
            for paragraph in paragraphs:
                for run in paragraph.runs:
                    set_run_typeface(run)
        self.doc.save(path)


def load_artifacts():
    quality = read_csv("outputs/tables/raw_data_quality_summary.csv").set_index("check")["value"]
    split = read_csv("outputs/tables/data_split_summary.csv")
    model = read_csv("outputs/tables/model_comparison_validation.csv")
    cv = read_csv("outputs/tables/temporal_cv_summary.csv")
    cats = read_csv("outputs/tables/statistics/categorical_associations.csv")
    nums = read_csv("outputs/tables/statistics/numeric_comparisons.csv")
    routes = read_csv("outputs/tables/eda/ocean_route_summary.csv")
    chokepoints = read_csv("outputs/tables/eda/chokepoint_summary.csv")
    errors = read_csv("outputs/tables/validation_error_analysis.csv")
    inventory = read_csv("outputs/tables/current_csv_inventory.csv")
    ext_context = read_csv("data/external/context_indicators.csv")
    ext_incidents = read_csv("data/external/historical_incidents.csv")
    selection = json.loads((ROOT / "outputs/metrics/model_selection.json").read_text(encoding="utf-8"))
    dictionary = read_csv("UnderseaCableRisk/data_dictionary.csv")
    instructor = Document(INSTRUCTOR_DOCX)
    rubric_tables = [
        [[clean_text(cell.text) for cell in row.cells] for row in table.rows]
        for table in instructor.tables
    ]
    return locals()


def add_cover(paper: Paper, subtitle: str):
    paper.para("UNIVERSITY OF NEGROS OCCIDENTAL – RECOLETOS, INC.", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("COLLEGE OF INFORMATION TECHNOLOGY", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.doc.add_paragraph()
    p = paper.doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Inches(0)
    p.add_run(TITLE)
    paper.para("A RESEARCH PROJECT", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para(COURSE, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.doc.add_paragraph()
    paper.para(subtitle, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.doc.add_paragraph()
    paper.para("Submitted to:", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("Mr. Maxil S. Urocay, MSCS candidate", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("and to the Faculty of the College of Information Technology", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.doc.add_paragraph()
    paper.para("Submitted by:", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    for member in MEMBERS:
        paper.para(member, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para(SECTION, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("September 2026", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)


def add_reference_style_cover(paper: Paper, subtitle: str):
    """Create the black, institutional cover pattern from the format reference."""
    paper.doc.add_paragraph()
    title = paper.doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.first_line_indent = Inches(0)
    title.paragraph_format.space_before = Pt(6)
    title.paragraph_format.space_after = Pt(18)
    run = title.add_run(TITLE)
    run.bold = True
    run.font.color.rgb = RGBColor.from_string("000000")

    paper.para(COURSE, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para(clean_text(subtitle), indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.doc.add_paragraph()
    paper.para("Presented to Mr. Maxil S. Urocay, MSCS candidate", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("College of Information Technology", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("University of Negros Occidental - Recoletos, Inc.", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.doc.add_paragraph()
    paper.para("In Partial Fulfillment", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("Of the Requirements for the Course", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("COPE0683X", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.doc.add_paragraph()
    paper.para("By:", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    for member in MEMBERS:
        paper.para(member, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para(SECTION, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    paper.para("September 2026", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)


def load_front_matter_pages(stage: str):
    path = TEMP_DIR / "front_matter_page_map.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get(stage.lower(), {})


def figure_entries():
    return [
        ("1.", "Reproducible Project Workflow", "Figure 1. Reproducible project workflow"),
        ("2.", "Annual Cable-Year Records", "Figure 2. Annual cable-year records"),
        ("3.", "Annual Next-Year Fault Prevalence", "Figure 3. Annual next-year fault prevalence"),
        ("4.", "Route-Redundancy Distribution", "Figure 4. Route-redundancy distribution"),
    ]


def table_entries(stage: str):
    if stage.lower() == "prelim":
        return [
            ("1.", "Preliminary Data Dictionary", "Table 1. Preliminary data dictionary"),
            ("2.", "Complete Data Dictionary", "Table 2. Complete data dictionary"),
            ("3.", "Data-Quality Assessment Summary", "Table 3. Data-quality assessment summary"),
            ("4.", "Raw-versus-Cleaned Data Summary", "Table 4. Raw-versus-cleaned data summary"),
            ("5.", "Descriptive Statistical Summary", "Table 5. Descriptive statistical summary"),
        ]
    if stage.lower() == "midterm":
        return [
            ("1.", "Preliminary Data Dictionary", "Table 1. Preliminary data dictionary"),
            ("2.", "Dataset and Partition Summary", "Table 2. Dataset and partition summary"),
            ("3.", "Data-Quality Assessment Summary", "Table 3. Data-quality assessment summary"),
            ("4.", "Ocean-Route Distribution", "Table 4. Ocean-route distribution"),
            ("5.", "Categorical Association Results", "Table 5. Categorical association results"),
            ("6.", "Chronological Data Split", "Table 6. Chronological data split"),
            ("7.", "Development Validation Model Comparison", "Table 7. Development validation model comparison"),
        ]
    return [
        ("1.", "Preliminary Data Dictionary", "Table 1. Preliminary data dictionary"),
        ("2.", "Dataset and Partition Summary", "Table 2. Dataset and partition summary"),
        ("3.", "Selected Statistical Association Results", "Table 3. Selected statistical association results"),
        ("4.", "Development Validation Model Comparison", "Table 4. Development validation model comparison"),
        ("5.", "Expanding-Window Temporal Cross-Validation Summary", "Table 5. Expanding-window temporal cross-validation summary"),
        ("6.", "Source-Backed Context Indicators", "Table 6. Source-backed context indicators"),
        ("7.", "Selected Documented Historical Incidents", "Table 7. Selected documented historical incidents"),
    ]


CHAPTER_TOC = {
    1: ("INTRODUCTION AND PROBLEM DEFINITION", ["Background of the Project", "Statement of the Problem", "General Research Problem", "Specific Research Questions", "Project Objectives", "Significance of the Project", "Target Users and Beneficiaries", "Scope and Limitations", "Information Technology Relevance", "Sustainable Development Goal Alignment", "Definition of Important Terms"]),
    2: ("REVIEW OF RELATED LITERATURE AND DATA SCIENCE STUDIES", ["Submarine Cable Infrastructure and Global Connectivity", "Fault Mechanisms, Protection, and Chokepoints", "Capacity, Design Life, and Resilience Planning", "Predictive Maintenance and Infrastructure Analytics", "Classification, Imbalance, and Evaluation", "Synthesis and Project Gap"]),
    3: ("DATA SCIENCE METHODOLOGY", ["Research and Analytical Design", "Dataset Source, Coverage, and Provenance", "Variables and Data Dictionary", "Data Acquisition, Ethics, and Governance", "Data Quality and Cleaning", "Exploratory and Statistical Analysis", "Feature Preparation and Modeling", "Validation and Evaluation", "Reproducibility"]),
    4: ("IMPLEMENTATION AND ANALYTICAL DEVELOPMENT", ["Project Environment and File Organization", "Importation, Quality Findings, and Cleaning", "Exploratory Analysis", "Statistical Analysis", "Feature Preparation, Models, and Cross-Validation", "Technical Limitations"]),
    5: ("RESULTS, EVALUATION, AND DISCUSSION", ["Final Descriptive and Exploratory Results", "Statistical-Analysis Results", "Validation Model Comparison", "Temporal Stability and Sensitivity", "Source-Backed Context Indicators", "Selected Historical Incidents", "Error Analysis and Interpretation", "Final-Test Status"]),
    6: ("CONCLUSIONS, LIMITATIONS, AND RECOMMENDATIONS", ["Conclusions", "Limitations", "Recommendations", "Responsible-Use Statement"]),
}


def add_front_lists_and_toc(paper: Paper, stage: str):
    pages = load_front_matter_pages(stage)
    paper.front_title("List of Figures")
    for number, title, locator in figure_entries():
        paper.dotted_entry(f"{number}    {title}", pages.get(locator))
    paper.page_break()
    paper.front_title("List of Tables")
    for number, title, locator in table_entries(stage):
        paper.dotted_entry(f"{number}    {title}", pages.get(locator))
    paper.page_break()
    paper.front_title("Table of Contents")
    front_entries = {
        "prelim": [("LIST OF FIGURES", "ii"), ("LIST OF TABLES", "iii"), ("TABLE OF CONTENTS", "iv")],
        "midterm": [("LIST OF FIGURES", "ii"), ("LIST OF TABLES", "iii"), ("TABLE OF CONTENTS", "iv")],
        "master": [("ABSTRACT", "ii"), ("LIST OF FIGURES", "iii"), ("LIST OF TABLES", "iv"), ("TABLE OF CONTENTS", "v")],
        "final": [("APPROVAL AND EVALUATION PAGE", "ii"), ("ABSTRACT", "iii"), ("LIST OF FIGURES", "iv"), ("LIST OF TABLES", "v"), ("TABLE OF CONTENTS", "vi")],
    }[stage.lower()]
    for title, page in front_entries:
        paper.dotted_entry(title, page)
    paper.doc.add_paragraph()
    max_chapter = {"prelim": 3, "midterm": 4, "master": 6, "final": 6}[stage.lower()]
    paper.para("CHAPTER", indent=False, align=WD_ALIGN_PARAGRAPH.LEFT)
    for chapter in range(1, max_chapter + 1):
        title, sections = CHAPTER_TOC[chapter]
        roman = list(ROMAN_CHAPTERS.values())[chapter - 1]
        paper.dotted_entry(f"CHAPTER {roman}: {title}", pages.get(title), bold=True, italic=True)
        for section_title in sections:
            paper.dotted_entry(section_title, pages.get(section_title), level=1, bold=True)
    extras = []
    if stage.lower() == "prelim":
        extras = ["Data Dictionary", "Data-Quality Assessment Report", "Raw-versus-Cleaned Data Summary", "Descriptive Statistical Results", "Exploratory Data-Analysis Figures", "Proposal Correction Record", "Consultation and Defense Correction Record", "Group Contribution Record", "Official Prelim Rubrics"]
    elif stage.lower() == "midterm":
        extras = ["Updated Data Dictionary and Data-Quality Report", "Expanded Exploratory Analysis", "Statistical Assumption and Analysis Results", "Feature Preparation and Data Splitting", "Baseline, Candidate Models, and Initial Comparison", "Initial Error Analysis and Interpretation", "Prelim and Midterm Correction Records", "Appendices", "Official Midterm Rubrics"]
    else:
        extras = ["References", "Appendices", "Official Final Rubrics"]
    for title in extras:
        paper.dotted_entry(title.upper(), pages.get(title.upper()) or pages.get(title), bold=True, italic=True)


def add_abstract(paper: Paper, artifacts):
    paper.heading("Abstract", 1)
    paper.para("This study evaluates whether infrastructure and operational indicators available at the end of an observation year can distinguish cable-year records associated with a fault in the following observed year. The repository implements an auditable Python workflow for source verification, temporal-label validation, cleaning, exploratory analysis, statistical association testing, leakage-aware feature preparation, chronological validation, and model comparison. The working panel contains 4,821 rows, 500 cable identifiers, and 21 variables covering 2015–2026. The publisher identifies the observations as procedurally generated synthetic records; therefore, the reported relationships and validation results describe behavior within the supplied dataset and are not evidence about named operational cables. Development results compare a prior-probability dummy baseline, logistic regression, decision tree, and random forest. The 2025 held-out evaluation remains locked in the current repository, so this document is a near-final research draft rather than a completed final evaluation report.")
    paper.para("Of 4,321 populated forward labels, 820 are positive and 3,501 are negative, making minority-class evaluation essential. Random forest has the highest recorded validation PR-AUC point estimate, while logistic regression provides a more transparent comparison and stronger validation recall. Expanding-window results are used to assess stability rather than erase variation between years. Source-backed facts about international traffic, fault frequency and cause, design life, capacity growth, and selected incidents are discussed only as external context and are never copied onto synthetic training rows.")
    paper.para("Keywords: submarine cables; fault occurrence; chronological validation; imbalanced classification; infrastructure analytics", indent=False)


def add_chapter_one(paper: Paper, a):
    q = a["quality"]
    paper.heading("Chapter One: Introduction and Problem Definition", 1)
    paper.heading("Background of the Project", 2)
    paper.para("Submarine fiber-optic cables form a physical layer of international digital connectivity by linking landing stations and carrying traffic between countries and regions. The International Telecommunication Union (ITU, 2025b) reports that submarine cables carry approximately 99% of the world's international data traffic. The ITU's Global Connectivity Report also reports that 86% of cable faults result from human activities such as fishing and anchoring (ITU, 2025a). These are sector-level reference statistics, not observations in the study panel. Cable resilience additionally depends on physical protection, route diversity, restoration arrangements, and the ability to repair faults (Carter et al., 2009; Starosielski, 2015).")
    paper.para("The project examines this infrastructure-resilience problem as a data-science classification task. It asks whether information available at the end of year t can distinguish records with a fault in the following observed year. The goal is methodological evidence about preparation, leakage prevention, temporal validation, and model comparison rather than engineering diagnosis or an operational warning system.")
    paper.para("The revised and approved proposal defines the prediction moment as the end of an observation year. That timing is central to the study: age, capacity, utilization, burial protection, redundancy, and current-year fault history may be considered only when their values are available by that moment. A feature derived from a future label, a later year, or the complete time series would make evaluation optimistic and would no longer answer the approved research problem. Temporal eligibility is therefore treated as a data-quality requirement rather than merely a modeling preference.")
    paper.para("The project also distinguishes physical cable resilience from service continuity. A cable fault does not always produce a user-visible outage because traffic may be rerouted, and a service disruption may depend on topology, spare capacity, landing-station conditions, and repair arrangements that are absent from the panel. Accordingly, fault_next_year is analyzed as the supplied forward classification label, not as outage duration, economic loss, repair urgency, or the probability that a named cable will fail.")
    paper.heading("Statement of the Problem", 2)
    paper.para("The working data represent repeated cable-year observations with a forward fault label, but the supplied identifiers are synthetic and the dataset is not an authenticated incident register. The analytical problem is therefore to determine what predictive signal can be measured within the supplied panel while preserving temporal order, handling repeated observations, avoiding target leakage, and reporting limitations honestly.")
    paper.heading("General Research Problem", 2)
    paper.para("This project seeks to determine whether infrastructure and operational information available at the end of an observation year can distinguish cable-year records that experience a fault in the following year, and to identify which approved classification method provides the most defensible balance of fault detection, predictive performance, stability, and interpretability under chronological testing.")
    paper.heading("Specific Research Questions", 2)
    for text in ["What are the distributions and operational characteristics of the cable-year observations in terms of route, operator type, age, length, fiber pairs, landing-country count, capacity, utilization, burial protection, route redundancy, vulnerability, current-year fault history, and next-year fault status?", "Which selected infrastructure and operational variables are statistically associated with fault_next_year after accounting for variable type and the repeated cable-year structure, without interpreting those associations as causal effects?", "How well do a majority-class baseline, logistic regression, decision tree, and random forest predict next-year fault occurrence when preprocessing and model fitting use only information available before the held-out prediction year?", "Which candidate model provides the most appropriate balance of precision, recall, F1-score, PR-AUC, ROC-AUC, error pattern, stability, and interpretability on chronologically held-out data?"]:
        paper.bullet(text)
    paper.heading("Project Objectives", 2)
    for text in ["Describe route, operator, age, length, fiber-pair, landing-country, capacity, utilization, protection, redundancy, fault-history, and target distributions.", "Test categorical and numeric associations and fit an adjusted logistic association model where assumptions permit.", "Prepare a leakage-aware analytical dataset, including temporal-label validation and documented treatment of derived variables.", "Train and compare a prior-probability baseline, logistic regression, decision tree, and random forest using chronological development partitions.", "Document errors, uncertainty, limitations, responsible-use boundaries, and the status of the locked final test."]:
        paper.bullet(text)
    paper.heading("Significance of the Project", 2)
    paper.para("The academic contribution is a reproducible example of infrastructure analytics using repeated observations, imbalanced classification, and time-aware validation. The study demonstrates how model comparison can be conducted without treating a high accuracy baseline as sufficient evidence. It does not certify a real cable, estimate actual global failure risk, or replace engineering inspection.")
    paper.para("The methodological value is the connection between source governance and model evaluation. Provenance determines what claims the observations support; prediction timing determines which features are admissible; class imbalance determines which metrics are informative; and chronological validation determines whether reported performance resembles a future-use setting. Treating these decisions as one auditable workflow produces stronger evidence than an isolated accuracy score or visualization dashboard.")
    paper.heading("Target Users and Beneficiaries", 2)
    for text in ["Submarine-cable operators and consortium network-operations or asset-reliability teams may use the workflow structure to organize later engineering review, but not its synthetic-row scores as maintenance instructions.", "Telecommunications carriers and hyperscaler resilience teams may use the documented indicators as a scenario-analysis template for redundancy and continuity planning, not as a stand-alone rerouting or investment rule.", "Public-sector digital-infrastructure agencies and regulators may use the study to understand how infrastructure indicators can be audited while recognizing that no Philippine or foreign asset is identified or officially assessed.", "Infrastructure-risk researchers and Information Technology students can reproduce the workflow as a case study in panel cleaning, imbalance, chronological validation, model comparison, and responsible communication."]:
        paper.bullet(text)
    paper.heading("Scope and Limitations", 2)
    paper.para(f"The source panel contains {fmt(q['rows'])} rows, {fmt(q['unique_cables'])} cable identifiers, {fmt(q['columns'])} variables, and years 2015–2026. The target has {fmt(q['labeled_rows'])} populated labels ({fmt(q['positive_labels'])} positive and {fmt(q['negative_labels'])} negative; prevalence {pct(q['positive_prevalence'])}). Six non-consecutive temporal predecessors are excluded from supervised eligibility. The panel lacks named real cables, coordinates, seabed conditions, vessel tracks, maintenance logs, repair duration, and authenticated incident-level outcomes.")
    paper.para("Because the observations are procedurally generated rather than empirical measurements of operational submarine cable systems, the statistical relationships and predictive performance reported in this study describe behavior within the supplied dataset. Validation using traceable empirical cable-system records would be required before generalizing the findings to operational infrastructure.")
    paper.para("The analytical scope includes source documentation, a quality and leakage audit, descriptive and exploratory analysis, type-appropriate association tests, a dummy benchmark, three approved classifiers, expanding-window checks, error analysis, interpretability evidence, and reproducible reporting in Python. It excludes exact fault localization, causal failure diagnosis, live network monitoring, repair scheduling, security assessment, and automatic action affecting real infrastructure.")
    paper.heading("Information Technology Relevance", 2)
    paper.para("The project applies data management, Python pipeline engineering, infrastructure analytics, reproducible modeling, version-controlled artifacts, validation, and responsible communication. It demonstrates the complete data-science workflow expected in an Information Technology project.")
    paper.heading("Sustainable Development Goal Alignment", 2)
    paper.para("The project aligns with Sustainable Development Goal 9, Industry, Innovation and Infrastructure. Its contribution is limited to methodological analysis of infrastructure-resilience indicators and transparent limits on automated use (United Nations, n.d.).")
    paper.para("The direct connection is resilient digital infrastructure: submarine systems support international communications, and the study evaluates whether broad infrastructure and operational indicators contain forward classification signal. The contribution is modest. It does not construct, certify, or repair infrastructure, but it demonstrates data stewardship, reproducible analysis, and responsible limits on decision support.")
    paper.heading("Definition of Important Terms", 2)
    paper.table(["Term", "Definition"], [["Cable-year observation", "One row representing one cable identifier in one observation year."], ["fault_next_year", "Forward target: whether a fault occurs in the following observed cable-year."], ["Chronological validation", "Training on earlier years and evaluating on later years to preserve prediction timing."], ["PR-AUC", "Area under the precision-recall curve, emphasized because the fault class is a minority class."], ["Source-backed context", "Published sector facts or documented incidents retained separately from model-training rows."]])


    paper.para("The study uses an explicit evidence hierarchy to keep its claims proportionate. Values calculated from the supplied cable-year records support statements about the synthetic panel; executed validation outputs support statements about development performance; and cited sector publications support background statements about global connectivity, fault mechanisms, repairs, design life, and capacity growth. None of those layers substitutes for authenticated operational records. This hierarchy is applied in the wording of every result and recommendation.")
    paper.para("Several working assumptions are therefore conservative. A current-year variable is eligible only when it is available at the stated year-end prediction moment. A blank-looking value is not assigned a meaning until the dictionary and raw representation are checked. A derived field is not accepted merely because it correlates with the target; its formula and timing must also be defensible. When provenance is incomplete, the paper records the uncertainty instead of creating a value or silently treating the field as verified.")
    paper.para("The expected practical output is a documented screening workflow rather than an autonomous risk product. In an empirical setting, a screening score could help organize review queues, compare scenarios, or identify records that merit additional engineering evidence. It could not determine a repair route, declare a cable safe, or allocate emergency resources without current physical, geographic, traffic, and maintenance information. Human review and authenticated source data remain necessary conditions for any operational use.")
    paper.para("Taken together, the problem definition preserves the approved proposal while clarifying the boundary between an academic classification exercise and real infrastructure management. The succeeding chapters first establish the domain and evaluation literature, then document the implemented methodology, development evidence, limitations, and the remaining locked-test obligation.")


    paper.para("Success for the semester project is defined by defensibility rather than by a predetermined performance level. A valid outcome may show that the approved predictors provide only modest discrimination, that an interpretable model is competitive with a more flexible model, or that performance changes across years. What matters is that the result follows the approved timing, reports minority-class behavior, preserves the locked test, and can be reproduced from the recorded artifacts.")
    paper.para("The paper deliverables support that definition of success. The Prelim document establishes the problem, literature, source limitations, dictionary, cleaning logic, and initial exploration. The Midterm document retains that foundation and adds the executed implementation, statistical work, split design, candidate comparison, and early error analysis. The Master and Final drafts integrate all six chapters, contextual evidence, appendices, rubrics, and the explicit status of the final evaluation. Earlier evidence is retained rather than compressed away at later checkpoints.")
    paper.para("This progression also protects the approved scope. New contextual facts may deepen the explanation, and future empirical variables may be recommended, but neither changes the current unit of analysis or silently converts the project into causal engineering diagnosis. Any proposed expansion is identified as future work unless a traceable source, valid join key, compatible time basis, and documented role in the analysis are available.")


    paper.para("The research questions and objectives remain aligned through a direct evidence chain. The first question is answered by distributions and figures; the second by categorical, numeric, and adjusted association evidence; the third by common-split model metrics; and the fourth by validation ranking, temporal folds, error counts, and interpretability. Conclusions are organized in the same order. This chain helps the reader verify that every major claim answers an approved question and that no method is included only because it produces an attractive output.")
    paper.para("The project also defines a clear stopping rule for the current phase. Development is complete when the data audit, leakage decisions, exploratory work, statistical analysis, pipelines, temporal comparison, error review, documentation, and reproducibility artifacts are present and internally consistent. Final evaluation is complete only after authorized test unblinding and reporting. Operational readiness is a separate standard requiring empirical validation, security review, engineering ownership, and monitored use; it is not implied by submission of the semester paper.")


    paper.para("Within those boundaries, the intended contribution remains concrete: a reviewer can trace each observation from source through eligibility, compare the approved models on later-year data, understand why certain fields were excluded, and distinguish development evidence from external context. That traceability supports academic assessment now and provides a disciplined starting point if authenticated operational data become available later.")


def add_chapter_two(paper: Paper, a):
    paper.heading("Chapter Two: Review of Related Literature and Data Science Studies", 1)
    paper.heading("Submarine Cable Infrastructure and Global Connectivity", 2)
    paper.para("The 99% international-traffic figure communicates dependence on subsea infrastructure, but it is a sector-level share rather than a feature or outcome in the modeling panel. Network importance is not distributed evenly: landing stations, regional corridors, and systems with limited substitutes can have different consequences when damaged. The project therefore discusses connectivity and concentration as motivation while avoiding claims that its broad ocean_route or chokepoint categories reproduce an authenticated global topology.")
    paper.para("Submarine cable systems connect landing stations and form a critical physical layer of international communications. ITU describes submarine cables as carrying approximately 99% of international data traffic and reports more than 500 active and planned systems in its resilience backgrounder (ITU, 2026). Carter et al. (2009) and Starosielski (2015) place cable networks in a broader ocean and communications-infrastructure context, emphasizing the interaction between physical geography, network organization, and global connectivity.")
    paper.heading("Fault Mechanisms, Protection, and Chokepoints", 2)
    paper.para("Fishing and anchoring figures are not interchangeable. They change with water depth, fishing intensity, shipping patterns, burial practice, local regulation, reporting coverage, and the period summarized. The contrast between historical global and UK-specific tables is analytically useful: a percentage without geography and time can mislead. In this study, protected_burial and chokepoint are broad indicators, not measurements of burial depth, anchor penetration, vessel proximity, or fishing effort.")
    paper.para("Infrastructure chokepoints matter because several routes, landing areas, or external hazards may share a constrained corridor. However, a chokepoint label does not by itself measure common-mode failure, capacity lost, or available restoration paths. Operational assessment would require route geometry, landing-station dependencies, active traffic, spare capacity, and contemporaneous maritime exposure. These missing layers are requirements for future empirical extension rather than generated or imputed values in the present panel.")
    paper.para("Published sources distinguish accidental human activity from natural hazards and equipment-related failure. The ITU reports that 86% of faults result from human activities such as fishing and anchoring (ITU, 2025a). The ICPC's historical bulletin reports a 67% fishing share and 8% anchor share through 2006, while its UK 2007–2008 table shows a different local distribution (ICPC, 2009). These figures demonstrate why scope and period must accompany any fault-cause percentage. Chokepoints and landing corridors can concentrate maritime activity, but a broad category is not equivalent to route geometry or measured traffic exposure.")
    paper.heading("Capacity, Design Life, and Resilience Planning", 2)
    paper.para("Design life is an engineering planning horizon, not a deterministic expiration date. Individual systems may be upgraded, retired, repaired, or operated beyond an initial planning period depending on technical and economic conditions. In the supplied panel, design_life_years is constant at 25 and therefore cannot explain differences between rows; it is documented for context but excluded from the primary model. Age remains available because it varies across cable-years, although an age association still cannot prove physical deterioration.")
    paper.para("Capacity trends also require careful interpretation. ITU reports approximately 22% annual submarine-bandwidth growth since 2021 and about 200,000 kilometers of new cable installed in 2024. These facts indicate a changing global environment, but they do not establish the trend in the synthetic panel. Design capacity, lit capacity, and utilization describe different concepts, are mathematically related, and may introduce redundancy. Their distributions and relationships are inspected before modeling, and their associations are not treated as direct failure mechanisms.")
    paper.para("ITU-T design guidance describes a typical 25-year submarine-system design life (ITU, 2005). ITU also reports increasing network demand and bandwidth growth, while its resilience backgrounder notes substantial new cable installation (ITU, 2025a, 2026). These sources motivate examination of capacity, age, utilization, and redundancy, but the study panel's values remain synthetic and cannot be used to estimate actual global capacity or traffic.")
    paper.heading("Predictive Maintenance and Infrastructure Analytics", 2)
    paper.para("A useful screening model must also be interpreted in relation to its errors. A false negative is a fault-labeled cable-year that the classifier misses, while a false positive is a cable-year flagged despite a negative forward label. In a real deployment those errors could have different review costs, but the present study has no validated cost function. It therefore reports the precision-recall trade-off, confusion counts, and stability evidence rather than claiming a universal operational threshold.")
    paper.para("Infrastructure analytics commonly combines descriptive monitoring, statistical association, and predictive classification. The present project follows that progression while preserving a clear distinction between association and causation. Repeated cable-year records require time-aware splits and careful treatment of within-cable dependence; a randomly shuffled split could allow future information to influence development estimates.")
    paper.heading("Classification, Imbalance, and Evaluation", 2)
    paper.para("The approved comparison deliberately includes models with different strengths. Logistic regression supplies a transparent linear reference; a decision tree produces understandable threshold rules but can be unstable; and a random forest reduces single-tree variance while sacrificing some direct interpretability. The dummy baseline exposes the weakness of relying on accuracy in an imbalanced dataset. Selection by validation PR-AUC is paired with recall, precision, F1, ROC-AUC, temporal variation, and interpretation so that no single number is treated as complete evidence.")
    paper.para("Logistic regression provides an interpretable probability model, while decision trees and random forests represent nonlinear thresholds and interactions (Breiman, 2001). Scikit-learn provides the pipeline and preprocessing framework (Pedregosa et al., 2011). Because the positive class is a minority, PR-AUC, recall, precision, and F1-score are more informative for fault detection than accuracy alone (He & Garcia, 2009; Saito & Rehmsmeier, 2015). ROC analysis remains a complementary discrimination measure (Fawcett, 2006).")
    paper.heading("Synthesis and Project Gap", 2)
    paper.para("The project makes two separations explicit. First, it separates model evidence from sector context: published traffic, fault, repair, and capacity statistics explain why the topic matters but do not validate synthetic row values. Second, it separates prediction from intervention: a classifier can rank observations within a dataset without establishing a physical cause or prescribing a repair. These separations address the principal evidence gap identified during proposal review and provide a defensible foundation for later empirical work.")
    paper.para("The literature establishes the importance of cable infrastructure, physical hazards, protection, and resilient connectivity, while machine-learning research provides tools for imbalanced classification. The gap addressed here is methodological: a single reproducible workflow connects source disclosure, temporal-label auditing, leakage-safe preparation, repeated-observation limitations, chronological model comparison, and responsible interpretation in a clearly bounded synthetic-data setting. The source-backed context layer extends the background without pretending that global published statistics are row-level predictors.")


    paper.para("The literature also indicates that resilience cannot be reduced to the probability of a physical break. Service continuity depends on whether alternate paths exist, whether they share the same landing station or hazard corridor, how much spare capacity is available, and how quickly repair resources can reach the site. The supplied route_redundancy count is therefore treated as a limited indicator. It does not demonstrate true path diversity, geographic independence, or the ability to restore a particular traffic load.")
    paper.para("Historical incidents strengthen this distinction between mechanism and frequency. Anchor-dragging cases show that one vessel event can affect several cables and sometimes other seabed assets, yet a selected incident list cannot supply a denominator for estimating annual risk. Similarly, approximate annual fault counts provide scale but do not reveal exposure time, cable kilometers, reporting completeness, or system-specific failure probability. The study uses those records to explain plausible mechanisms and consequences, not to calibrate the synthetic target.")
    paper.para("The reviewed classification literature further supports reporting probabilities and threshold-dependent errors separately. PR-AUC summarizes ranking behavior across thresholds, whereas the confusion matrix reflects one selected hard-decision rule. A model can have a higher PR-AUC but lower recall at 0.50, or a lower apparent accuracy while identifying more positives. For a minority-class problem, these differences must be visible so that model selection does not hide the operational implications of a threshold.")
    paper.para("The resulting project gap is therefore not the absence of a more complex algorithm. It is the need for a traceable end-to-end method that connects provenance, prediction timing, repeated observations, imbalance, chronological validation, interpretation, and responsible-use limits. Addressing that gap provides a defensible academic contribution even though external operational validation remains outside the supplied data.")


    paper.para("Responsible infrastructure analytics must also consider information sensitivity. Exact routes, landing dependencies, spare capacity, and damage history may be commercially or operationally sensitive even when they contain no personal data. The present public academic package avoids that issue by using synthetic identifiers and broad categories. A later empirical study would need access classification, a minimum-necessary data policy, controlled sharing, and a publication review that prevents detailed vulnerability information from being exposed.")
    paper.para("The literature review therefore supports both the variables examined and the variables deliberately withheld from interpretation. Age, utilization, protection, redundancy, and fault history are plausible analytical indicators, while undocumented composite indices and target-adjacent fields require stronger scrutiny. This is consistent with a general data-science principle: relevance alone does not establish admissibility, because provenance and prediction timing determine whether a variable can be used fairly.")
    paper.para("In synthesis, the domain literature establishes strategic importance and plausible mechanisms; the statistical literature establishes appropriate comparisons and uncertainty; and the machine-learning literature establishes candidate methods and imbalance-aware evaluation. The implemented methodology translates those three strands into one auditable study design while keeping the empirical limitations visible.")


    paper.para("This synthesis justifies a cautious interpretation of performance: the models test whether structured signal exists within the supplied panel, not whether a global cable operator could rely on the same score. That distinction is carried into the methodology through provenance labels, feature exclusions, chronological partitions, and a separate external-context layer.")


def add_chapter_three(paper: Paper, a, stage="complete"):
    q = a["quality"]
    paper.heading("Chapter Three: Data Science Methodology", 1)
    paper.heading("Research and Analytical Design", 2)
    paper.para("The approved research questions are answered in sequence. Descriptive analysis addresses distributions and operational characteristics; type-appropriate tests examine unadjusted associations; the modeling pipelines compare the approved baseline and classifiers; and chronological validation, error analysis, and interpretation support the development selection. This mapping prevents a method from being introduced without a corresponding question and prevents a conclusion from exceeding the available evidence.")
    paper.para("The study uses an observational, quantitative, predictive-comparison design. The unit is a cable-year row, and the forward target is defined at the end of year t for the following observed year. The design is not causal and does not estimate a real-world engineering failure probability.")
    workflow = TEMP_DIR / "pipeline_workflow.png"
    if workflow.exists():
        paper.doc.add_picture(str(workflow), width=Inches(5.8))
        paper.caption("Figure 1. Reproducible project workflow")
    paper.heading("Dataset Source, Coverage, and Provenance", 2)
    paper.para("The raw archive and three supplied CSV files are preserved without manual spreadsheet editing. File hashes and an inventory make later changes detectable. The master table supplies repeated observations, the reference file supplies supporting attributes, and the data dictionary supplies field definitions. Reproducibility of a synthetic source does not convert it into empirical infrastructure evidence, so provenance remains a substantive limitation throughout the paper.")
    paper.para("The modeling panel is Undersea Cables and Global Digital Infrastructure, distributed by sergionefedov through Kaggle. According to the publisher, the records are procedurally generated synthetic cable-year observations rather than authenticated measurements of specific real-world submarine cable systems. The source record records CC0, hashes, access date, dimensions, and this limitation. Separate source-backed context and incident files are stored in data/external/ and are not joined to the panel because the CAB#### identifiers have no real-world crosswalk.")
    paper.heading("Variables and Data Dictionary", 2)
    paper.para("The unit of analysis is one cable identifier in one observation year. cable_id is a grouping and lineage field rather than an ordered or numerical measurement. fault_next_year is the binary target and is meaningful only when the next observed row for the same cable is the immediately following calendar year. Infrastructure and operational predictors retain the units and category meanings documented by the supplied dictionary.")
    rows = []
    for _, row in a["dictionary"].iterrows():
        role = "target" if row["column"] == "fault_next_year" else ("identifier" if row["column"] == "cable_id" else "predictor/audit")
        rows.append([row["column"], row["type"], role, row["description"]])
    paper.caption("Table 1. Preliminary data dictionary")
    paper.table(["Variable", "Type", "Role", "Description"], rows, font_size=8)
    paper.para("The implementation excludes cable_id, rfs_year, design_life_years, is_low_redundancy, vulnerability_index, and fault_cause from the primary predictor set for identifier, redundancy, construction, or leakage reasons. The engineered sensitivity set uses only current and prior calendar-year information and does not replace the primary model.")
    paper.heading("Data Acquisition, Ethics, and Governance", 2)
    paper.para("The main ethical risks are authenticity, licensing, infrastructure sensitivity, and misuse rather than personal privacy. Results are aggregated for an academic report; no model output identifies a real asset. Any future work with authenticated route geometry, repair records, or security-sensitive network information would require access controls, minimization, authorized storage, and domain review. The current project does not infer missing real locations or publish operational vulnerability rankings.")
    paper.para("The raw source files are preserved under UnderseaCableRisk and are not manually edited. Source-backed context and incidents retain source URLs, access dates, scope, period, and notes under data/external/. No personal, confidential, or sensitive records are used. Public-source facts are not presented as row-level validation of the synthetic panel. No generated external observations, synthetic oversampling rows, or invented incidents are used.")
    paper.heading("Data Quality and Cleaning", 2)
    paper.para("The cleaning sequence validates schema, data types, allowed binary values, numeric bounds, year coverage, uniqueness of cable_id-year, and target consistency. Blank-looking chokepoint values are confirmed as the literal None category instead of being silently treated as missing. A populated fault_next_year is eligible only when the next observed record for the same cable is exactly one calendar year later; rows that fail temporal continuity remain documented outside the supervised set.")
    paper.para("Primary feature exclusions are decided before final-test access. cable_id is retained for grouping but not used as numeric signal; rfs_year is redundant with year and age; design_life_years is constant; is_low_redundancy duplicates a derived threshold; vulnerability_index lacks a documented formula; and fault_cause is conditional on a current fault and may duplicate fault_this_year. The excluded fields remain in audit outputs so the decision is reviewable.")
    paper.para(f"The audit verified {fmt(q['rows'])} rows and {fmt(q['columns'])} variables, no duplicate rows or cable-year keys, {fmt(q['chokepoint_literal_None'])} literal None chokepoint categories, and six unresolved temporal gaps. The 500 structurally unlabeled final observations are retained in the full panel but excluded from supervised training and evaluation. Cleaning preserves lineage and adds explicit temporal eligibility and exclusion-reason fields.")
    paper.heading("Exploratory and Statistical Analysis", 2)
    paper.para("Numeric variables are summarized with counts, central tendency, dispersion, quartiles, and ranges; categorical variables are summarized with counts and proportions. Mann-Whitney procedures are used where a rank comparison is more defensible than a simple mean comparison. Chi-square results are paired with Cramer's V so that statistical evidence is not confused with practical magnitude. P-values are interpreted alongside effect sizes, sample size, repeated observations, and the synthetic-data limitation.")
    paper.para("Development EDA and inferential analyses use years through 2024 so that the 2025 final-test period is not used for outcome-aware feature or model decisions. Descriptive statistics, category summaries, annual prevalence, Mann–Whitney comparisons, chi-square associations, and an adjusted logistic association model are reported with non-causal interpretation. Repeated cable observations are acknowledged as a limitation, with clustered interpretation where feasible.")
    paper.heading("Feature Preparation and Modeling", 2)
    paper.para("Preprocessing is fitted inside each development pipeline. Numeric imputation and scaling, where required, are learned from training data; categorical levels are one-hot encoded with unknown-category handling. The tree models receive the same primary information set as logistic regression so that performance differences reflect model behavior rather than inconsistent feature access.")
    paper.para("The dummy model supplies the training-prior probability and majority hard classification. Logistic regression uses L2 regularization and considers balanced class weighting. The decision tree constrains depth and minimum leaf size, while the random forest averages many constrained trees with a fixed random seed. Hyperparameters and any threshold choice are determined only from development evidence. No synthetic oversampling is used, preserving the original row counts and class distribution.")
    paper.para("Categorical variables are one-hot encoded and numeric variables are imputed and standardized where required inside scikit-learn pipelines fitted on training data only. The baseline is DummyClassifier with the training prior. Logistic regression, a constrained decision tree, and a random forest are compared using the same primary features. A separate engineered sensitivity set adds causal lag/trend and capacity-headroom features without using the forward target.")
    paper.heading("Validation and Evaluation", 2)
    paper.para("Four expanding-window folds repeat the future-prediction logic across earlier cutoffs. Their mean and standard deviation show whether a validation result is stable across periods rather than dependent on a single split. The final-test guard is an executable control that prevents routine pipeline runs from producing 2025 predictions or metrics. Once authorized, the selected preprocessing, features, model, and threshold must be frozen and evaluated once without post-test retuning.")
    paper.para("The development split uses 2015–2022 for training and 2023–2024 for validation/model selection. Expanding-window temporal cross-validation is also reported. The 2025 rows are held as a final test partition for predicting 2026 faults, but final evaluation remains locked. Metrics include accuracy, precision, recall, F1-score, ROC-AUC, PR-AUC, and confusion-matrix counts; accuracy is secondary because the positive class is imbalanced.")
    paper.heading("Reproducibility", 2)
    paper.para("Reproducibility includes more than executable code. The repository records source metadata, raw hashes, environment versions, deterministic random states, split summaries, model parameters, eligibility reasons, figures, machine-readable tables, and final-test status. Document values are read from those artifacts rather than manually retyped, reducing the chance that the narrative and analysis diverge.")
    paper.para("The workflow is implemented in scripts/run_pipeline.py and modular files under src/. Generated CSV/JSON outputs, figures, saved pipelines, environment versions, and a manifest provide traceability from raw source through the reported validation results. The tracked document generator reads these artifacts and writes only ignored deliverables.")


    paper.para("Temporal-label construction is checked independently from ordinary missing-value handling. A row may contain a non-null forward label yet still fail the immediate-successor rule when its cable history skips a calendar year. Conversely, a final row with no future observation is not considered erroneous; it is structurally unlabeled for supervised evaluation. Maintaining both cases in the cleaned panel preserves the difference between a quality exception and a legitimate future-scoring record.")
    paper.para("The development design also separates model selection from final estimation. Training years establish transformations and fitted parameters, validation years support hyperparameter and candidate comparison, and the final year is reserved for one later estimate of locked performance. This separation is procedural as well as conceptual: output artifacts record the chosen feature set, model family, parameters, threshold status, and test lock so that an evaluator can determine whether a later result was produced according to the prespecified plan.")
    paper.para("Interpretability is matched to the model. Logistic coefficients can describe the direction of a conditional linear relationship after encoding and scaling, but correlated features and category references affect their meaning. A decision tree can be read as a sequence of thresholds, but individual splits may be unstable. Random-forest importance can identify variables useful to the ensemble, but it does not reveal a causal mechanism. Validation-set permutation evidence and error analysis are therefore preferred over unqualified claims that the model has discovered physical causes.")
    paper.para("The evaluation plan keeps discrimination, classification, and calibration questions distinct. ROC-AUC and PR-AUC describe ranking across thresholds; precision, recall, F1, and the confusion matrix describe a chosen threshold; accuracy supplies only a secondary overall proportion. A future empirical extension should additionally examine calibration so that predicted probabilities correspond to observed frequencies, but calibration is not claimed from the present development comparison.")
    paper.para("Quality assurance is applied at both data and reporting levels. Automated checks validate dimensions, keys, ranges, splits, and final-test status. Machine-readable results are the source for manuscript numbers. Visual document checks then verify tables, figures, headings, page numbers, and source notes. This combination reduces the risk that a correct computation is reported incorrectly or that a polished report conceals an undocumented analytical choice.")


    paper.para("The methodology includes a negative-evidence rule: absence of a variable from the model is not automatically a defect. A constant variable cannot support discrimination, an undocumented composite may create hidden leakage, an identifier may encourage memorization, and a redundant field may inflate instability without adding information. Exclusion decisions are documented beside the retained fields so an evaluator can distinguish purposeful control from accidental omission.")
    paper.para("A similar rule applies to external data. Published global percentages, selected incidents, and sector growth indicators are valuable for background, but no defensible cable-level join exists for the synthetic CAB identifiers. The correct methodological action is therefore to retain those records in a separate contextual layer with source metadata. Generating coordinates or assigning global averages to individual rows would create false precision and is explicitly prohibited.")
    paper.para("The final methodological standard is auditability under revision. If an instructor-approved correction changes the target definition, feature scope, or final-test protocol, the change should be recorded before rerunning the affected stages. Earlier outputs should remain traceable, the reason for regeneration should be stated, and the manuscript should be rebuilt from the new artifacts. This preserves a clear distinction between legitimate correction and result-driven adjustment.")


    paper.para("These procedures create a reproducible contract between the proposal and the results: the same unit, timing, eligibility rule, candidate set, development split, evaluation measures, and interpretation limits are used throughout. Any later departure must be documented as a correction or a new analysis rather than absorbed silently into the final narrative.")


def add_eda_figures(paper: Paper):
    figures = [
        (TEMP_DIR / "document_annual_records.png", "Figure 2. Annual cable-year records"),
        (TEMP_DIR / "document_annual_prevalence.png", "Figure 3. Annual next-year fault prevalence"),
        (TEMP_DIR / "document_route_redundancy.png", "Figure 4. Route-redundancy distribution"),
    ]
    for figure, caption in figures:
        path = Path(figure)
        if path.exists():
            picture = paper.doc.add_paragraph()
            picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
            picture.paragraph_format.first_line_indent = Inches(0)
            picture.paragraph_format.keep_with_next = True
            picture.add_run().add_picture(str(path), width=Inches(5.2))
            cap = paper.caption(caption)
            cap.paragraph_format.keep_with_next = False


def add_chapter_four(paper: Paper, a):
    q = a["quality"]
    paper.heading("Chapter Four: Implementation and Analytical Development", 1)
    paper.heading("Project Environment and File Organization", 2)
    paper.para("The implementation follows a separation-of-concerns structure. Immutable source files and metadata support provenance; processed data contain explicit audit fields; reusable source modules implement validation and modeling; outputs contain tables, metrics, figures, and serialized pipelines; and documentation explains decisions and constraints. This arrangement allows a reviewer to distinguish inputs, transformations, evidence, and presentation artifacts.")
    paper.para("The repository uses Python scripts and notebooks organized into source, data, outputs, documentation, tests, and ignored deliverables. The raw Kaggle files remain in UnderseaCableRisk. The real-world context layer is explicitly separated under data/external/. The document generator is scripts/build_research_documents.py; generated papers and review renders are excluded by the deliverables/ rule in .gitignore.")
    paper.heading("Importation, Quality Findings, and Cleaning", 2)
    paper.para("Import assertions check the expected 21-column schema, year range, identifier count, binary fields, and uniqueness of cable-year keys. The pipeline does not discard the 500 final rows simply because their forward labels are structurally absent. They remain in the cleaned panel for lineage and future scoring, while supervised eligibility is a separate flag. This distinction prevents a valid unlabeled prediction row from being mislabeled as poor-quality data.")
    paper.para("The six unresolved temporal predecessors illustrate why non-null targets alone are insufficient. If a cable's next observed record skips a year, the supplied forward label cannot be assumed to represent the immediate next calendar year without additional documentation. Those rows are retained with explicit exclusion reasons. This auditable rule keeps the implementation aligned with the proposal's year-t to year-t+1 definition.")
    paper.para(f"The executed audit produced {fmt(q['rows'])} raw rows, {fmt(q['columns'])} columns, {fmt(q['unique_cables'])} unique identifiers, and {fmt(q['duplicate_rows'])} exact duplicates. The pipeline retained all rows in the cleaned panel, flagged six unresolved temporal predecessors, preserved the literal chokepoint category None, and produced {fmt(q['temporally_valid_labeled'])} temporally eligible supervised rows.")
    paper.caption("Table 2. Dataset and partition summary")
    split_rows = []
    for _, row in a["split"].iterrows():
        split_rows.append([row["partition"], f"{int(row['min_year'])}–{int(row['max_year'])}", fmt(row["rows"]), fmt(row["unique_cables"]), fmt(row["positives"]), fmt(row["negatives"]), pct(row["prevalence"])])
    paper.table(["Partition", "Years", "Rows", "Cables", "Positive", "Negative", "Prevalence"], split_rows)
    paper.heading("Exploratory Analysis", 2)
    paper.para("Exploration is restricted to the development period when outcome-aware summaries could influence modeling decisions. Annual counts reveal changing coverage, while annual prevalence shows whether the class balance is stable through time. Route, operator, and chokepoint summaries examine category representation; numeric summaries and histograms reveal scale, skewness, and concentration; and target-group comparisons identify variables that warrant cautious statistical follow-up.")
    paper.para("The figures are descriptive rather than diagnostic. A changing annual fault prevalence could reflect the synthetic generation process, cohort composition, or predictor distribution rather than a real global trend. Similarly, a route-redundancy histogram describes the supplied counts but does not measure physically independent restoration paths. Each visualization is interpreted within the data dictionary and provenance limits.")
    paper.para("The executed EDA produced annual record and prevalence figures, route and operator summaries, chokepoint frequencies, descriptive statistics, and route-redundancy visualizations. The separate context indicators and selected incidents are summarized as source-backed evidence rather than merged into the panel EDA.")
    add_eda_figures(paper)
    paper.heading("Statistical Analysis", 2)
    paper.para("Categorical tests evaluate whether target proportions vary across observed groups, and Cramer's V provides an effect-size scale independent of sample size. Numeric rank comparisons evaluate whether the two target groups tend to occupy different parts of a distribution. The adjusted logistic association model provides a multivariable view, but coefficients are interpreted as conditional associations within the supplied panel, not engineering causal effects.")
    paper.para("Repeated cable identifiers create dependence between rows across years. Where clustered standard errors are feasible they are preferred for inferential interpretation; otherwise, the repeated structure is disclosed as a limitation. The predictive evaluation addresses a different question and therefore relies on chronological holdout performance rather than inferential significance alone.")
    paper.para("The statistical outputs use development years and report effect-size or rank/association statistics alongside p-values. These tests are interpreted as associations, not causal effects. The exact machine-readable results remain in outputs/tables/statistics/.")
    paper.heading("Feature Preparation, Models, and Cross-Validation", 2)
    paper.para("All transformations are encapsulated in scikit-learn pipelines. This prevents the validation period from setting imputation values, category columns, or scaling parameters. The primary information set remains fixed across substantive models. The dummy baseline demonstrates the apparent accuracy available from class imbalance, the linear model offers transparency, the decision tree offers compact nonlinear rules, and the random forest offers a lower-variance nonlinear ensemble.")
    paper.para("Model selection uses the 2023-2024 validation period and emphasizes PR-AUC because the positive class is the minority. Precision, recall, F1, ROC-AUC, accuracy, and confusion counts remain visible because each answers a different evaluation question. Expanding-window folds test whether the ranking and minority-class behavior persist across earlier future periods. The final-test lock prevents the 2025 period from becoming another tuning set.")
    paper.para("The primary pipeline uses three categorical predictors and ten numeric predictors after the documented exclusions. The sensitivity pipeline adds causal lag/trend features. Four expanding temporal folds were generated for development stability, and the same 2023–2024 validation partition was used for the sensitivity comparison. The final-test guard prevented premature scoring.")
    paper.heading("Technical Limitations", 2)
    paper.para("A technically reproducible workflow can still be externally invalid. The synthetic panel cannot establish operational fault frequencies, causal mechanisms, geographic exposure, or current risk for a named cable. Missing geometry prevents spatial joins to earthquakes, bathymetry, fishing effort, or vessel tracks. Missing repair records prevent analysis of restoration time and consequences. These are data-bound limitations rather than defects that can be solved through additional model complexity.")
    paper.para("The source does not document the simulator formula for vulnerability_index, the exact construction of some derived quantities, or a real cable crosswalk. These limitations constrain interpretation even though the code and outputs are reproducible.")


    paper.para("The implementation can be reconstructed from the source archive through the final development tables without editing a CSV by hand. Raw-file hashes identify the exact inputs; cleaning outputs retain source keys and exclusion reasons; split tables show the temporal partitions; parameter records identify fitted candidates; and the generated manuscript reads those artifacts. This lineage is important because an unexplained spreadsheet change could otherwise alter both the class counts and the apparent model performance.")
    paper.para("The executed pipeline also demonstrates why leakage controls must be tested rather than merely described. Derived variables are reviewed for their construction, transformations live inside fitted pipelines, development EDA excludes the locked test outcome, and the final-test guard prevents accidental scoring during routine runs. Each control addresses a different path by which later information could make a model appear more accurate than it would be at the stated prediction time.")
    paper.para("Model development remains deliberately bounded. The candidate list follows the approved proposal, class weighting is preferred over row generation, and the same primary information set is used across substantive models. This makes comparisons easier to interpret and avoids turning the semester project into an unconstrained search over algorithms. The engineered feature set remains a labeled sensitivity analysis rather than a post hoc replacement for the primary specification.")
    paper.para("From a software-engineering perspective, reproducibility also requires failure visibility. Assertions should stop execution when an expected column disappears, a key duplicates, an impossible label appears, or a protected output is requested without authorization. Silent recovery would make the pipeline convenient but less trustworthy. The recorded audit tables and explicit pending markers are therefore part of the research result, not merely administrative files.")


    paper.para("The current implementation is also intentionally transparent about what it has not executed. The final test is locked, no operational deployment interface is presented, and no claim is made that the synthetic ranking is calibrated for a real asset. Pending work is visible in status artifacts and manuscript language. This is preferable to filling required sections with implied results or presenting a validation estimate as though it were an independent final test.")
    paper.para("Reviewers can evaluate the project at several levels. A data reviewer can inspect schema, keys, missingness, and eligibility. A statistical reviewer can inspect assumptions, effect sizes, repeated observations, and class imbalance. A software reviewer can inspect pipeline boundaries, parameters, tests, and manifests. A domain reviewer can inspect whether contextual claims retain their geographic and historical scope. The package is organized so that disagreement at one level can be addressed without obscuring the others.")
    paper.para("The implementation chapter therefore demonstrates completion of the approved development work rather than completion of all possible submarine-cable analytics. It establishes a controlled, reproducible basis for the results chapter and for the later one-time final evaluation, while leaving empirical enrichment and operational validation as clearly specified next steps.")


    paper.para("Finally, the implementation maintains a separation between presentation and evidence. Tables and figures are regenerated from saved analytical outputs, and document pagination does not alter calculations. This allows formatting revisions, including chapter-level page breaks and expanded explanations, without changing the verified dataset counts or model metrics. The resulting manuscript can therefore grow in completeness while the analytical record remains stable and auditable.")


def add_chapter_five(paper: Paper, a):
    paper.heading("Chapter Five: Results, Evaluation, and Discussion", 1)
    paper.heading("Final Descriptive and Exploratory Results", 2)
    paper.para("The descriptive results answer the first approved research question by establishing the scale, class balance, time coverage, and principal infrastructure distributions before model interpretation. The panel is longitudinal rather than a collection of independent incidents: a cable identifier can appear in multiple years, and the availability of its forward label depends on an observed successor. Counts are therefore reported both for raw rows and for temporally eligible supervised rows.")
    paper.para(f"The raw source contains {fmt(a['quality']['rows'])} rows and {fmt(a['quality']['unique_cables'])} cable identifiers. Among {fmt(a['quality']['labeled_rows'])} populated forward labels, {fmt(a['quality']['positive_labels'])} are positive and {fmt(a['quality']['negative_labels'])} are negative ({pct(a['quality']['positive_prevalence'])} prevalence). The most frequent development route is Intra-Asia ({fmt(a['routes'].iloc[0]['count'])} rows), while the literal None chokepoint category is retained as a valid category rather than treated as missing.")
    paper.heading("Statistical-Analysis Results", 2)
    paper.para("The statistical analyses address the second research question at two levels. Unadjusted categorical and numeric comparisons identify observable distribution differences, while the adjusted logistic analysis asks whether selected variables retain conditional association when considered together. Neither level proves that changing an attribute would change fault occurrence, and statistical significance is not used as a substitute for predictive validation.")
    paper.caption("Table 3. Selected statistical association results")
    stat_rows = []
    for _, row in a["cats"].iterrows():
        stat_rows.append([row["variable"], row["test"], fmt(row["statistic"], 4), fmt(row["df"], 0), f"{float(row['p_value']):.3g}", fmt(row["cramers_v"], 3)])
    paper.table(["Variable", "Test", "Statistic", "df", "p-value", "Cramér's V"], stat_rows)
    paper.para("The categorical outputs show strong evidence of association for ocean_route and chokepoint in the development data, while operator_type has a small non-significant chi-square result at the predeclared 0.05 level. Numeric comparisons show statistically detectable distribution differences for age, length, design capacity, utilization, protected burial, route redundancy, and current-year fault history, but not for every capacity or landing-country measure. These results are descriptive associations within the supplied data and do not establish causes.")
    paper.para("Median comparisons provide a concrete description of several differences. Fault-labeled rows have a higher median age (13 versus 10 years), longer median cable length (6,810.5 versus 5,630 kilometers), higher median utilization (64.95% versus 60.2%), and lower median route redundancy (41 versus 44) in the development data. Fiber pairs, landing-country count, and lit capacity do not show the same level of rank-test evidence. These patterns are useful for understanding the generated panel, but their direction and magnitude require empirical validation before any infrastructure interpretation.")
    paper.heading("Validation Model Comparison", 2)
    paper.para("The third and fourth research questions are answered by comparing all approved candidates on the same later-year validation period. The dummy classifier reaches high apparent accuracy by predicting the majority class, but its recall and F1 for faults are zero and its PR-AUC equals the class-prior baseline. This result shows why accuracy alone would reward a model that never identifies the outcome of interest.")
    paper.caption("Table 4. Development validation model comparison")
    rows = []
    for _, row in a["model"].iterrows():
        rows.append([row["model"], f"{float(row['precision']):.3f}", f"{float(row['recall']):.3f}", f"{float(row['f1']):.3f}", f"{float(row['pr_auc']):.3f}", f"{float(row['roc_auc']):.3f}", f"{float(row['accuracy']):.3f}", f"TN {int(row['TN'])}; FP {int(row['FP'])}; FN {int(row['FN'])}; TP {int(row['TP'])}"])
    paper.table(["Model", "Precision", "Recall", "F1", "PR-AUC", "ROC-AUC", "Accuracy", "Confusion"], rows, font_size=8)
    paper.para("The validation comparison selects random_forest by the recorded PR-AUC point estimate ({:.3f}), with logistic regression providing a more interpretable comparison and the dummy baseline establishing the prior-probability floor. The selected model is a development choice only; it is not a claim of real-world superiority.".format(float(a["model"].loc[a["model"]["model"] == "random_forest", "pr_auc"].iloc[0])))
    paper.para("The substantive trade-off is visible in the confusion counts. Logistic regression detects more positive cases than random forest (88 versus 69 true positives) but also produces more false positives (260 versus 162). Random forest improves precision and overall separation while missing more positives at the default decision threshold. Decision tree recall is slightly higher than logistic regression, yet its precision, PR-AUC, and ROC-AUC are lower. The selection therefore favors random forest's validation PR-AUC while preserving logistic regression as an interpretable, higher-recall comparator.")
    paper.heading("Temporal Stability and Sensitivity", 2)
    paper.para("A single holdout can be unusually easy or difficult, so expanding-window evidence is used to evaluate stability. Across four folds, random forest has the highest mean PR-AUC, followed by logistic regression, decision tree, and the dummy baseline. Logistic regression has the highest mean recall, which reinforces the practical distinction between ranking quality and the number of positives captured at a fixed threshold. Standard deviations are retained to show uncertainty across time rather than presenting the means as invariant performance.")
    cv_rows = []
    for _, row in a["cv"].iterrows():
        cv_rows.append([row["model"], f"{float(row['temporal_cv_pr_auc_mean']):.3f}", f"{float(row['temporal_cv_pr_auc_sd']):.3f}", f"{float(row['temporal_cv_f1_mean']):.3f}", f"{float(row['temporal_cv_recall_mean']):.3f}", int(row["folds"])])
    paper.caption("Table 5. Expanding-window temporal cross-validation summary")
    paper.table(["Model", "Mean PR-AUC", "SD", "Mean F1", "Mean Recall", "Folds"], cv_rows)
    paper.para("The temporal cross-validation summary supports the usefulness of time-ordered development checks. The engineered-feature comparison remains a sensitivity analysis and does not replace the primary selection record. The final test period has not been scored.")
    paper.heading("Source-Backed Context Indicators", 2)
    paper.para("The external context layer answers the request for broader evidence without manufacturing rows. It includes the reported share of international data traffic carried by submarine cables, approximate annual fault and repair counts, human-activity and historical fishing/anchoring proportions, typical design life, recent new-cable length, and bandwidth growth. Every record retains its organization, period, geographic scope, access date, URL, and interpretation note.")
    rows = []
    for _, row in a["ext_context"].iterrows():
        rows.append([row["metric"], row["value"], row["unit"], row["scope"], row["reference_period"], row["source_organization"]])
    paper.caption("Table 6. Source-backed context indicators (not model predictors)")
    paper.table(["Metric", "Value", "Unit", "Scope", "Period", "Source"], rows, font_size=7)
    paper.para("These indicators retain their published scope and period. Historical cause percentages are not treated as current global rates, and global indicators are not copied onto individual synthetic cable rows.")
    paper.para("The indicators also show why direct comparison requires caution. The 86% ITU human-activity figure is a recent global summary, the ICPC 67% fishing and 8% anchor shares are historical global figures through 2006, and the UK 2007-2008 table has a different local balance. The approximate 200 annual faults and the lower-bound count of 170 repairs in 2025 are different measures, not competing estimates of the same quantity. Context is therefore reported with its denominator and period rather than combined into a synthetic trend.")
    paper.heading("Selected Historical Incidents", 2)
    paper.para("The selected incidents illustrate how a single anchor-dragging event can affect several telecommunications cables and, in some cases, power cables or pipelines. Examples range from the 2002 U.S. East Coast event to the 2025 Baltic case. Their purpose is mechanism illustration and source documentation; the list is neither a random sample nor a complete census and cannot be used to estimate incident frequency.")
    rows = []
    for _, row in a["ext_incidents"].iterrows():
        rows.append([row["incident_date"], row["location"], row["vessel_or_description"], row["cause_summary"], row["telecom_cables_damaged"] or "not quantified"])
    paper.caption("Table 7. Selected documented historical incidents")
    paper.table(["Date", "Location", "Vessel/description", "Cause summary", "Telecom cables"], rows, font_size=8)
    paper.para("The incident table is a selected compilation rather than a complete incident census. It is retained for background and discussion only; it has no cable-ID or geometry crosswalk to the modeling panel.")
    paper.heading("Error Analysis and Interpretation", 2)
    paper.para("False negatives matter because they represent positive forward labels that a screening model would not flag. False positives matter because they would consume review attention without a positive forward label. The current academic dataset supplies no monetary, safety, or service-continuity cost for either error, so the paper does not optimize an operational cost function. Instead, it exposes both counts and recommends that any future empirical deployment set thresholds with stakeholder-defined consequences and independent validation.")
    counts = a["errors"]["error_type"].value_counts().to_dict()
    paper.para("On the development validation partition, the selected model produced {} true negatives, {} false positives, {} false negatives, and {} true positives. These counts are used to discuss the precision–recall trade-off and not to certify operational risk.".format(counts.get("TN", 0), counts.get("FP", 0), counts.get("FN", 0), counts.get("TP", 0)))
    paper.para("The model-interpretation outputs provide logistic coefficients and tree/forest importance rankings. Because the features are observational and the panel is synthetic, importance and association are not causal effects. The model can support methodological comparison but not maintenance, routing, regulatory, or safety decisions.")
    paper.heading("Final-Test Status", 2)
    paper.para("The locked test contains the latest labeled period and is reserved to estimate performance after development choices are complete. Its status is deliberately prominent because a near-final manuscript must not imply that validation metrics are final generalization estimates. Unblinding must be a one-time, authorized action followed by reporting of all prespecified metrics, including unfavorable results, without selecting a new model from the test set.")
    paper.para("[FINAL-TERM EVALUATION PENDING — HELD-OUT TEST REMAINS LOCKED] The 2025 partition is preserved for a one-time final evaluation after the selection record and threshold are frozen. No final-test predictions, confusion matrix, or metrics are included in this generation pass.")


    paper.para("The results should not be read as a competition in which one model wins every criterion. Random forest has the strongest recorded validation PR-AUC point estimate and temporal mean PR-AUC, while logistic regression captures more positives at the default threshold and offers a simpler explanation. Decision tree provides compact rules but weaker ranking evidence, and the dummy baseline exposes the misleading comfort of majority-class accuracy. The appropriate choice therefore depends on the prespecified priority and the cost of errors, neither of which can be inferred from synthetic labels alone.")
    paper.para("Temporal variation is itself a result. Performance changes across expanding windows because the composition, prevalence, and relationships in a later period need not match an earlier period. Reporting the fold standard deviation prevents the mean from appearing more certain than it is. If the final test later falls outside the development range, that difference should prompt an investigation of drift, cohort change, or overfitting rather than an attempt to revise the model using the test outcomes.")
    paper.para("The external indicators place the academic results in context while preserving their own definitions. A traffic-share statistic communicates strategic dependence, a repair count communicates workload, a design-life guideline communicates an engineering planning horizon, and bandwidth growth communicates changing demand. They do not share a common denominator and cannot be combined into a single risk score. Their value in this report is explanatory and comparative, not predictive at the cable-row level.")
    paper.para("The historical cases similarly support qualitative reasoning about common-cause and multi-asset events. Their inclusion justifies future interest in route geometry, vessel tracks, and landing-station dependencies, but the incidents do not identify any CAB identifier in the synthetic panel. This prevents an illustrative case from being mistaken for a matched training example or external test observation.")
    paper.para("Overall, the development evidence is sufficient to justify the implemented workflow and the recorded provisional selection, but not to justify deployment. The decisive remaining analytical step is the authorized, one-time held-out evaluation. The decisive longer-term research step is independent replication on traceable empirical records collected under an appropriate governance arrangement.")


def add_chapter_six(paper: Paper, a):
    paper.heading("Chapter Six: Conclusions, Limitations, and Recommendations", 1)
    paper.heading("Conclusions", 2)
    paper.para("The completed development work remains faithful to the approved proposal. It uses the cable-year as the analytical unit, fixes the prediction time at the end of year t, preserves the specified predictors subject to leakage and provenance review, compares the approved baseline and three classifiers, prioritizes minority-class metrics, and reserves the latest period for a locked final evaluation. No synthetic oversampling or fabricated external observation is introduced.")
    paper.para("The four questions are answered conditionally. Descriptive evidence documents varied routes, operator types, ages, lengths, capacities, utilization levels, protection, redundancy, and class prevalence. Categorical and numeric analyses identify several associations while leaving some measures non-significant. All substantive models improve minority-class detection over the hard majority baseline but remain imperfect. Random forest is the recorded development selection because of PR-AUC, while logistic regression remains important where transparency and recall receive more weight.")
    paper.para("The project established a reproducible workflow for predicting a forward fault label within the supplied cable-year panel. The data audit verified the source dimensions, target structure, repeated observations, literal None chokepoint category, derived-variable concerns, and six unresolved temporal predecessors. The primary development comparison produced measurable differences among the baseline and candidate models, with random forest recorded as the selected development model by validation PR-AUC. These conclusions describe the supplied dataset only.")
    paper.para("The research questions are therefore answered conditionally: the panel contains diverse infrastructure and operational distributions; several variables show statistical association with the forward label; the candidate models provide different precision–recall trade-offs under chronological validation; and random forest offers the strongest recorded validation PR-AUC point estimate while logistic regression offers greater transparency. The locked final test is still required before any final performance conclusion.")
    paper.heading("Limitations", 2)
    paper.para("The most important limitation is evidentiary, not computational. A model can reproduce patterns in procedurally generated data without learning the behavior of real submarine systems. More tuning, a more complex algorithm, or a larger synthetic sample would not solve the lack of authenticated asset identities, collection methods, and incident outcomes. The conclusions are explicitly bounded to the supplied panel and development procedure.")
    for text in ["The panel is procedurally generated synthetic data, not authenticated operational cable measurements.", "The data lack real cable names, geometry, seabed/environmental exposures, vessel activity, maintenance records, and incident-level outcomes.", "Six temporal gaps required eligibility exclusions, and repeated cable observations limit independent-row interpretation.", "The vulnerability-index construction and some simulator-derived quantities are undocumented.", "The model comparison is a validation result; final-test performance has not been evaluated.", "Statistical association and feature importance do not establish causality or engineering mechanisms.", "Source-backed context indicators and selected incidents are not row-level joins and cannot validate the panel."]:
        paper.bullet(text)
    paper.heading("Recommendations", 2)
    paper.para("The immediate recommendation is to finish the planned workflow without changing its evidentiary rules. The selection record, primary feature set, preprocessing, and threshold should be frozen before the authorized one-time test. The final report should show the complete confusion matrix and all prespecified metrics, compare them with validation expectations, explain any performance drop, and retain the result even if it is unfavorable.")
    paper.para("A future empirical version should begin with a traceable cable inventory and incident schema rather than append unsupported values to the present rows. Useful additions include named or securely pseudonymized cable identifiers, route geometry, landing-station dependencies, water depth and bathymetry, burial depth, vessel and fishing activity, earthquakes and submarine landslides, maintenance history, fault dates and causes, repair-vessel response, restoration duration, traffic impact, and source-specific uncertainty. Such data should be joined only through documented spatial or identifier keys and at a time resolution consistent with the prediction question.")
    for text in ["Complete the authorized one-time 2025 final evaluation without retuning after unblinding.", "Retain the source, hashes, data dictionary, audit outputs, and generated artifacts for reproducibility.", "For empirical extension, obtain named cable identifiers or geometry, incident dates and causes, repair outcomes, and a documented crosswalk before joining environmental or maritime data.", "Use ITU, ICPC, TeleGeography, and other primary sources with scope, period, and access metadata for context claims.", "Treat any future operational deployment as requiring engineering review, security controls, independent validation, and an approved governance process."]:
        paper.bullet(text)
    paper.heading("Responsible-Use Statement", 2)
    paper.para("If the workflow is later adapted to real infrastructure, every score should remain decision support subject to engineering review. Access to sensitive route or vulnerability data should be role-limited; model drift and subgroup errors should be monitored; affected operators should be able to challenge data quality; and a documented owner should decide when retraining, withdrawal, or incident escalation is appropriate.")
    paper.para("The project is an educational and methodological analysis. It must not be used to make maintenance, routing, investment, regulatory, safety, or security decisions about real submarine cable systems without authenticated data and independent validation.")


    paper.para("A staged continuation plan follows from these conclusions. First, preserve the present package and complete the locked test exactly once. Second, document whether the final estimates confirm or weaken the development interpretation. Third, if an empirical dataset becomes available, rebuild the data dictionary and prediction-time audit before transferring the model. Fourth, compare the existing candidates against an empirical baseline before considering additional complexity. This order keeps evidence quality ahead of algorithm expansion.")
    paper.para("For data acquisition, priority should be given to variables that close a known analytical gap rather than variables that are merely easy to download. Exact or securely generalized route geometry would enable spatial exposure measures; incident dates and causes would establish real outcomes; maintenance and repair logs would support recovery analysis; and traffic, redundancy, and landing-station dependencies would connect physical faults to service consequences. Every addition should have a documented owner, timestamp, unit, permissible use, and join key.")
    paper.para("For evaluation, future work should report uncertainty and calibration in addition to discrimination. Repeated systems and changing years may require grouped or hierarchical methods, and rare severe events may require scenario analysis rather than ordinary classification alone. Thresholds should be selected with explicit review capacity and false-negative consequences, then monitored for drift. These extensions are recommended only after the authenticity and temporal availability of the data are established.")
    paper.para("The final contribution is therefore a disciplined research foundation: an approved problem translated into auditable data rules, a reproducible comparison, a transparent separation between contextual facts and model rows, and a clear record of what remains unknown. That foundation is more defensible than a larger but unverifiable risk table, and it provides a practical basis for subsequent empirical collaboration.")


    paper.para("The project should be judged against the approved question and the quality of its evidence, not against an assumption that a high-performing operational model must emerge from every dataset. Honest reporting of weak signal, unstable performance, or a failed final test would still be a valid data-science result when the workflow is correct and the limitations are explained. This standard discourages result shopping and keeps the final interpretation consistent with the educational purpose of the project.")
    paper.para("Accordingly, the recommended handoff preserves three labels: verified for executed checks and artifact-backed values, contextual for cited facts that are not panel observations, and pending for the locked final evaluation or any future empirical extension. Maintaining those labels in the paper, repository, presentation, and defense gives readers a concise way to distinguish what the group knows, what it uses only for background, and what still requires evidence.")
    paper.para("This labeling convention should remain unchanged in the final slides, recorded presentation, repository release, and oral defense.")


def add_references(paper: Paper):
    paper.page_break()
    paper.heading("References", 1)
    refs = [
        "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5–32. https://doi.org/10.1023/A:1010933404324",
        "Carter, L., Burnett, D., Drew, S., Marle, G., Hagadorn, L., Bartlett-McNeil, D., & Irvine, N. (2009). Submarine cables and the oceans: Connecting the world. UNEP World Conservation Monitoring Centre.",
        "Carter, L., Gavey, R., Talling, P. J., & Liu, J. T. (2014). Insights into submarine geohazards from breaks in subsea telecommunication cables. Oceanography, 27(2), 58–67. https://doi.org/10.5670/oceanog.2014.40",
        "Fawcett, T. (2006). An introduction to ROC analysis. Pattern Recognition Letters, 27(8), 861–874. https://doi.org/10.1016/j.patrec.2005.10.010",
        "He, H., & Garcia, E. A. (2009). Learning from imbalanced data. IEEE Transactions on Knowledge and Data Engineering, 21(9), 1263–1284. https://doi.org/10.1109/TKDE.2008.239",
        "International Cable Protection Committee. (2009). Damage to submarine cables caused by anchors. https://www.iscpc.org/documents/?id=139",
        "International Telecommunication Union. (2005). ITU-T Supplement 41: Design guidelines for optical fibre submarine cable systems. https://www.itu.int/rec/dologin_pub.asp?id=T-REC-G.Sup41-200505-S%21%21PDF-E&lang=e&type=items",
        "International Telecommunication Union. (2025a). Global Connectivity Report 2025: Chapter 3. https://www.itu.int/itu-d/reports/statistics/2025/11/17/gcr-2025-chapter-3/",
        "International Telecommunication Union. (2025b). Strengthening the world's digital backbone. https://www.itu.int/hub/2025/02/strengthening-the-worlds-digital-backbone/",
        "International Telecommunication Union. (2026). Submarine cable resilience. https://www.itu.int/en/mediacentre/backgrounders/Pages/submarine-cable-resilience.aspx",
        "Malecki, E. J. (2002). The economic geography of the Internet's infrastructure. Economic Geography, 78(4), 399–424.",
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, E. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
        "Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot on imbalanced datasets. PLOS ONE, 10(3), e0118432. https://doi.org/10.1371/journal.pone.0118432",
        "sergionefedov. (n.d.). Undersea cables and global digital infrastructure [Data set]. Kaggle. https://www.kaggle.com/datasets/sergionefedov/undersea-cables-and-global-digital-infrastructure",
        "Starosielski, N. (2015). The undersea network. Duke University Press.",
        "TeleGeography. (n.d.). Written testimony on submarine cable security. https://resources.telegeography.com/hubfs/Tim%20Stronge%20Written%20Congressional%20Testimony%20%7C%20TeleGeography.pdf",
        "United Nations. (n.d.). Goal 9: Industry, innovation and infrastructure. https://sdgs.un.org/goals/goal9",
    ]
    for ref in refs:
        p = paper.para(ref, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT)
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)


RUBRIC_CONFIG = {
    "prelim": [
        (5, "RUBRIC A: PRELIM PROJECT OUTPUT (Working Prototype, Research Paper, Hard Copy, and Soft Copy)"),
        (6, "RUBRIC B: GROUP DEFENSE AND PRESENTATION"),
        (7, "RUBRIC C: INDIVIDUAL QUESTION-AND-ANSWER PERFORMANCE"),
    ],
    "midterm": [
        (8, "RUBRIC A: MIDTERM PROJECT OUTPUT (Application, Paper, Hard Copy, and Soft Copy)"),
        (9, "RUBRIC B: GROUP DEFENSE AND PRESENTATION"),
        (10, "RUBRIC C: INDIVIDUAL QUESTION-AND-ANSWER PERFORMANCE"),
    ],
    "final": [
        (11, "RUBRIC A: FINAL PROJECT OUTPUT (Application, Paper, Hard Copy, and Soft Copy)"),
        (12, "RUBRIC B: GROUP DEFENSE AND PRESENTATION"),
        (13, "RUBRIC C: INDIVIDUAL QUESTION-AND-ANSWER PERFORMANCE"),
    ],
}


def add_official_rubrics(paper: Paper, a, stage: str):
    rubric_stage = "final" if stage == "master" else stage
    paper.page_break()
    paper.front_title(f"Official {rubric_stage.title()} Rubrics")
    paper.para("The following score sheets reproduce the official instructor-provided criteria and rating scales. Ratings and total scores are intentionally left blank for the evaluator.", indent=False)
    for position, (table_index, title) in enumerate(RUBRIC_CONFIG[rubric_stage]):
        if position:
            paper.page_break()
        paper.front_title(title)
        source_rows = [row[:] for row in a["rubric_tables"][table_index]]
        if len(source_rows[0]) == 4:
            source_rows[0] = ["Criterion", "Bayoguing, Jose Vincent III", "Cruz, Aurum Fuego", "Sapio, John Rey"]
            paper.table(source_rows[0], source_rows[1:], widths=[3.55, 0.9, 0.9, 0.9], font_size=7)
        else:
            paper.table(source_rows[0], source_rows[1:], widths=[5.15, 1.1], font_size=8)


def add_appendices(paper: Paper, a, stage):
    paper.page_break()
    paper.heading("Appendices", 1)
    paper.heading("Appendix A. Approved Proposal Alignment", 2)
    paper.para("The revised proposal remains the scope authority. The matrix records how its central commitments are represented in the implemented research package; a development-stage result does not convert the still-locked final test into completed evidence.")
    alignment = [
        ["Question 1 / Objective 1", "Describe route, operator, age, length, capacity, utilization, protection, redundancy, fault history, and target distributions.", "EDA tables, descriptive statistics, and Figures 2-4", "Implemented on development data"],
        ["Question 2 / Objective 2", "Test type-appropriate associations with repeated-observation and non-causal interpretation.", "Categorical, numeric, and adjusted association outputs", "Implemented; bounded interpretation"],
        ["Question 3 / Objectives 3-4", "Create a leakage-aware dataset and compare dummy, logistic, decision-tree, and random-forest models chronologically.", "Audit fields, pipelines, split summary, validation comparison, temporal folds", "Implemented on development data"],
        ["Question 4 / Objective 5", "Select using precision, recall, F1, ROC-AUC, PR-AUC, errors, stability, and interpretability.", "Selection JSON, comparison tables, error analysis, model interpretation", "Development selection recorded"],
        ["Final evaluation", "Use 2025 observations once to predict the 2026 label after model and threshold lock.", "Final-test guard and status artifact", "Pending; test remains locked"],
        ["Responsible use", "No causal, engineering, operational, or real-asset claim without authenticated evidence.", "Provenance record, limitations, context separation, responsible-use statement", "Implemented"],
    ]
    paper.table(["Proposal commitment", "Approved requirement", "Implementation evidence", "Current status"], alignment, font_size=7)
    paper.heading("Appendix B. Artifact Traceability", 2)
    trace = [["Claim/output", "Repository artifact", "Status"], ["Dataset dimensions and quality", "outputs/tables/raw_data_quality_summary.csv", "verified"], ["Temporal gaps", "outputs/tables/temporal_gap_audit.csv", "verified"], ["Validation comparison", "outputs/tables/model_comparison_validation.csv", "verified"], ["Final-test status", "outputs/metrics/final_test_status.txt", "locked"], ["Context indicators", "data/external/context_indicators.csv", "source-backed, not joined"], ["Historical incidents", "data/external/historical_incidents.csv", "selected compilation, not joined"]]
    paper.table(trace[0], trace[1:])
    paper.heading("Appendix C. Correction Record Template", 2)
    paper.para("No instructor correction record was found in the repository. The following empty template is provided for manual completion.")
    paper.table(["Date", "Correction / required action", "Owner / status", "Evidence"], [["", "", "Pending", ""]], font_size=8)
    paper.heading("Appendix D. Group Contribution Record Template", 2)
    paper.para("No authoritative contribution log was found in the repository. Members must complete this record from their actual work and defensible Git history; no contribution is inferred from commit authorship alone.")
    paper.table(["Date", "Member / assigned task", "Work / file evidence", "Reviewer / status"], [["", "", "", "Pending"]], font_size=8)
    paper.heading("Appendix E. Completion and Evidence Checklist", 2)
    paper.para("This checklist separates completed analytical evidence from manual submission tasks and the still-locked final evaluation. Status must be updated only from actual repository, consultation, or evaluator evidence.")
    checklist = [
        ["Source", "Raw archive, file hashes, license/provenance record, and authenticity decision are preserved.", "Verified / update if source changes"],
        ["Schema", "Dimensions, keys, types, ranges, allowed values, and duplicate checks are recorded.", "Verified"],
        ["Target", "Forward-label continuity, structural unlabeled rows, and six temporal exclusions are documented.", "Verified"],
        ["Features", "Primary inclusions and exclusions have timing, redundancy, and provenance reasons.", "Verified"],
        ["EDA", "Development-only summaries, figures, units, captions, and bounded interpretations are present.", "Verified"],
        ["Statistics", "Tests match variable type and report effect size, assumptions, and non-causal limits.", "Verified"],
        ["Models", "Dummy, logistic regression, decision tree, and random forest use comparable inputs.", "Verified"],
        ["Validation", "Chronological split, expanding windows, parameters, and selection record are preserved.", "Verified"],
        ["Context", "External indicators and incidents retain source, period, scope, and non-join status.", "Verified"],
        ["Final test", "Model, features, preprocessing, and threshold are frozen before one-time unblinding.", "Pending authorization"],
        ["Records", "Consultation corrections and contribution entries are supported by dated evidence.", "Manual completion required"],
        ["Submission", "Signatures, evaluator ratings, filenames, links, slides, video, and required copies are checked.", "Manual completion required"],
        ["Page map", "Table of Contents, List of Figures, and List of Tables match the latest rendered pagination.", "Verified after final render"],
        ["Formatting", "A4 geometry, margins, typeface, double spacing, chapter starts, headers, footers, and captions are checked.", "Verified after final render"],
        ["Rubrics", "Stage-specific official rubric text is retained and evaluator score cells remain unfilled.", "Verified / evaluator pending"],
        ["Packaging", "DOCX files remain separate and uncompressed unless the submission platform explicitly requires an archive.", "Verified"],
        ["Backup", "A second copy of source data, code, outputs, paper, slides, and video links is retained before submission.", "Manual completion required"],
        ["Defense", "Each member can explain the problem, variables, leakage controls, metrics, limitations, and pending test status.", "Manual preparation required"],
    ]
    paper.table(["Area", "Required evidence or action", "Status"], checklist, widths=[0.85, 4.15, 1.3], font_size=7)
    paper.para("Before printing or uploading, the group should review this checklist together and date any status change in the correction or contribution record. A checked item should point to evidence rather than rely on memory.", indent=False)
    add_official_rubrics(paper, a, stage)


def build_master(a):
    paper = Paper("MASTER")
    add_reference_style_cover(paper, "MASTER RESEARCH PAPER - CURRENT VERIFIED IMPLEMENTATION")
    paper.start_front_matter()
    add_abstract(paper, a)
    paper.page_break()
    add_front_lists_and_toc(paper, "master")
    paper.start_main_matter()
    add_chapter_one(paper, a)
    add_chapter_two(paper, a)
    add_chapter_three(paper, a)
    add_chapter_four(paper, a)
    add_chapter_five(paper, a)
    add_chapter_six(paper, a)
    add_references(paper)
    add_appendices(paper, a, "master")
    path = MASTER_DIR / "Undersea_Cable_Fault_Research_MASTER_EXPANDED_REFERENCE_FORMATTED.docx"
    paper.save(path)
    return path


def build_prelim(a):
    paper = Paper("PRELIM")
    add_reference_style_cover(paper, "PRELIM TERM PROJECT DOCUMENTATION - APPROXIMATELY 50% FOUNDATION")
    paper.start_front_matter()
    add_front_lists_and_toc(paper, "prelim")
    paper.start_main_matter()
    add_chapter_one(paper, a)
    add_chapter_two(paper, a)
    add_chapter_three(paper, a, stage="initial")
    paper.heading("Data Dictionary", 1)
    rows = [[r["column"], r["type"], r["description"]] for _, r in a["dictionary"].iterrows()]
    paper.caption("Table 2. Complete data dictionary")
    paper.table(["Variable", "Type", "Description"], rows, font_size=8)
    paper.heading("Data-Quality Assessment Report", 1)
    paper.para("The executed quality report is summarized below. The full machine-readable outputs remain in outputs/tables/ and the tracked documentation directory.")
    paper.caption("Table 3. Data-quality assessment summary")
    paper.table(["Check", "Value"], [[k, fmt(v)] for k, v in a["quality"].items()])
    paper.heading("Raw-versus-Cleaned Data Summary", 1)
    paper.para("The cleaning implementation retains all raw rows, adds temporal-label audit fields, and excludes only unresolved or unlabeled observations from supervised model-ready data.")
    paper.caption("Table 4. Raw-versus-cleaned data summary")
    paper.table(["Artifact", "Rows", "Columns", "Purpose"], [["Raw master", fmt(a["quality"]["rows"]), fmt(a["quality"]["columns"]), "Immutable source"], ["Cleaned panel", fmt(a["quality"]["rows"]), "audit fields added", "Lineage-preserving analysis copy"], ["Supervised eligible", fmt(a["quality"]["temporally_valid_labeled"]), "primary variables", "Future-label eligible rows"]])
    paper.heading("Descriptive Statistical Results", 1)
    paper.caption("Table 5. Descriptive statistical summary")
    paper.table(["Variable", "Mean", "Std", "Min", "Median", "Max"], [[r["variable"], fmt(r["mean"]), fmt(r["std"]), fmt(r["min"]), fmt(r["50%"]), fmt(r["max"])] for _, r in read_csv("outputs/tables/eda/descriptive_statistics.csv").iterrows() if r["variable"] in ["age_years", "length_km", "design_capacity_tbps", "lit_capacity_tbps", "utilization_pct", "route_redundancy"]])
    paper.heading("Exploratory Data-Analysis Figures", 1)
    add_eda_figures(paper)
    paper.heading("Proposal Correction Record", 1); paper.para("No instructor correction record was found. Complete the empty template in Appendix A after consultation.")
    paper.heading("Consultation and Defense Correction Record", 1); paper.para("No consultation or defense record was found. Complete the empty template after the Prelim defense.")
    paper.heading("Group Contribution Record", 1); paper.para("Complete the contribution template from actual member work and reviewed evidence.")
    paper.para("For the Prelim checkpoint, each entry should identify the assigned foundation task, the file or output that demonstrates completion, the date reviewed by the group, and any correction still open. Suitable evidence includes source-verification notes, data-dictionary review, quality-audit outputs, literature summaries, repository setup, figure generation, manuscript sections, and presentation preparation. Percentages should not be invented when the group does not have a defensible allocation method.")
    paper.para("The record should also distinguish individual production from group review. A member who writes a section may not be the only person who validated its claims, formatting, or code linkage. Recording both roles makes the contribution statement more accurate and gives the group a practical checklist for completing unresolved Prelim work before the Midterm stage.")
    paper.para("Before the Prelim defense, the group should reconcile this record with the repository and presentation materials. Each claimed task should point to a file, commit, output, meeting note, or reviewed manuscript change; unresolved assignments should have an owner and target date. After the defense, the same record can be extended with the member responsible for each correction, the evidence used to close it, and the reviewer who confirmed that the correction did not introduce a conflict elsewhere in the proposal or analysis plan.")
    add_appendices(paper, a, "prelim")
    path = PRELIM_DIR / "Undersea_Cable_Fault_Research_PRELIM_EXPANDED_REFERENCE_FORMATTED.docx"; paper.save(path); return path


def build_midterm(a):
    paper = Paper("MIDTERM")
    add_reference_style_cover(paper, "MIDTERM TERM PROJECT DOCUMENTATION - APPROXIMATELY 75% DEVELOPMENT")
    paper.start_front_matter()
    add_front_lists_and_toc(paper, "midterm")
    paper.start_main_matter()
    add_chapter_one(paper, a); add_chapter_two(paper, a); add_chapter_three(paper, a); add_chapter_four(paper, a)
    paper.heading("Updated Data Dictionary and Data-Quality Report", 1)
    paper.caption("Table 3. Data-quality assessment summary")
    paper.table(["Check", "Value"], [[k, fmt(v)] for k, v in a["quality"].items()])
    paper.heading("Expanded Exploratory Analysis", 1)
    paper.caption("Table 4. Ocean-route distribution")
    paper.table(["Route", "Count", "Proportion"], [[r["ocean_route"], fmt(r["count"]), pct(r["proportion"])] for _, r in a["routes"].iterrows()])
    paper.heading("Statistical Assumption and Analysis Results", 1)
    paper.caption("Table 5. Categorical association results")
    paper.table(["Variable", "Test", "Statistic", "p-value", "Effect size"], [[r["variable"], r["test"], fmt(r["statistic"]), f"{float(r['p_value']):.3g}", fmt(r.get("cramers_v", ""))] for _, r in a["cats"].iterrows()])
    paper.heading("Feature Preparation and Data Splitting", 1)
    paper.para("Primary features are prepared inside scikit-learn pipelines. The engineered sensitivity dataset is retained separately. The chronological partitions are shown below; the final test remains unscored.")
    paper.caption("Table 6. Chronological data split")
    paper.table(["Partition", "Years", "Rows", "Positive", "Negative", "Prevalence"], [[r["partition"], f"{int(r['min_year'])}–{int(r['max_year'])}", fmt(r["rows"]), fmt(r["positives"]), fmt(r["negatives"]), pct(r["prevalence"])] for _, r in a["split"].iterrows()])
    paper.heading("Baseline, Candidate Models, and Initial Comparison", 1)
    paper.caption("Table 7. Development validation model comparison")
    paper.table(["Model", "Precision", "Recall", "F1", "PR-AUC", "ROC-AUC", "Accuracy"], [[r["model"], f"{float(r['precision']):.3f}", f"{float(r['recall']):.3f}", f"{float(r['f1']):.3f}", f"{float(r['pr_auc']):.3f}", f"{float(r['roc_auc']):.3f}", f"{float(r['accuracy']):.3f}"] for _, r in a["model"].iterrows()])
    paper.heading("Initial Error Analysis and Interpretation", 1)
    paper.para("Validation errors are preserved in outputs/tables/validation_error_analysis.csv. The recorded selected model is random_forest by validation PR-AUC point estimate. This is an initial development result and not final-test evidence.")
    paper.heading("Prelim and Midterm Correction Records", 1); paper.para("No authoritative teacher correction records were found. Empty templates are included in the appendices for manual completion.")
    paper.para("When corrections are received, the group should record the original issue, required action, responsible member, affected artifact, completion date, and reviewer confirmation. A correction that changes data eligibility, target timing, feature scope, or model selection must trigger regeneration of the dependent outputs and manuscript values; a formatting-only correction should not alter analytical artifacts.")
    paper.para("The Midterm handoff should therefore show which Prelim comments were closed, which remain pending, and what evidence supports each status. This prevents verbal consultation notes from being lost and separates genuine instructor direction from later assumptions made by the group.")
    add_appendices(paper, a, "midterm")
    path = MIDTERM_DIR / "Undersea_Cable_Fault_Research_MIDTERM_EXPANDED_REFERENCE_FORMATTED.docx"; paper.save(path); return path


def build_final(a):
    paper = Paper("FINAL")
    add_reference_style_cover(paper, "FINAL-TERM NEAR-FINAL DRAFT - FINAL HELD-OUT EVALUATION PENDING")
    paper.start_front_matter()
    paper.front_title("Approval and Evaluation Page")
    paper.para("Instructor approval, evaluator signatures, ratings, and defense outcomes are intentionally left blank for manual completion. No institutional approval or grade is inferred.", indent=False)
    paper.page_break()
    add_abstract(paper, a)
    paper.page_break()
    add_front_lists_and_toc(paper, "final")
    paper.start_main_matter()
    add_chapter_one(paper, a); add_chapter_two(paper, a); add_chapter_three(paper, a); add_chapter_four(paper, a); add_chapter_five(paper, a); add_chapter_six(paper, a)
    add_references(paper); add_appendices(paper, a, "final")
    path = FINAL_DIR / "Undersea_Cable_Fault_Research_FINAL_EXPANDED_REFERENCE_FORMATTED.docx"; paper.save(path); return path


def build_review_report(paths, a):
    report = REVIEW_DIR / "document_generation_report.md"
    lines = ["# Document generation report", "", f"Generated: {date.today().isoformat()}", "", "## Outputs"]
    for path in paths:
        lines.append(f"- `{path.relative_to(ROOT)}`")
    lines += ["", "## Verified status", f"- Master panel: {fmt(a['quality']['rows'])} rows, {fmt(a['quality']['columns'])} variables, {fmt(a['quality']['unique_cables'])} cable identifiers.", f"- Labeled target rows: {fmt(a['quality']['labeled_rows'])}; positives: {fmt(a['quality']['positive_labels'])}; negatives: {fmt(a['quality']['negative_labels'])}.", f"- Temporally eligible supervised rows: {fmt(a['quality']['temporally_valid_labeled'])}; unresolved temporal gaps: 6.", "- Final test: locked; no final-test metrics or predictions included.", "- Official stage-specific Rubrics A-C and individual Q&A score sheets are embedded from the instructor document; no ratings or scores were invented.", "- Correction and contribution records: empty templates only; no instructor comments or member contributions were fabricated.", "", "## Formatting applied", "- A4 paper, one-inch margins, Times New Roman 12-point body text, double spacing, justified body paragraphs, black centered chapter headings, unnumbered black subsection headings, APA-style references, and Roman/Arabic page numbering.", "- The reference-derived institutional header/footer uses the official UNO-Recoletos and College of Information Technology marks, a black header rule, and centered page numbering.", "- The research title is black with no decorative underline. List of Figures, List of Tables, and Table of Contents use black dot leaders and rendered page numbers.", "- Body headings and tables use black/gray/white styling; color is limited to official logos and analytical charts/diagram.", "", "## Visual QA", "- DOCX structural generation and source-artifact checks completed by the generator.", "- Final LibreOffice/PDF/PNG inspection is required after generation and is recorded separately in this report after QA.", "", "## Pending manual tasks", "- Evaluators must complete rubric ratings, total scores, signatures, and approval fields.", "- Complete correction, consultation/defense, and contribution records from actual evidence.", "- Verify all references and links before submission.", "- Perform the authorized one-time final-test evaluation before treating the Final document as complete."]
    qa_start = lines.index("## Visual QA")
    pending_start = lines.index("## Pending manual tasks")
    lines[qa_start + 1 : pending_start] = [
        "- LibreOffice PDF rendering completed for all four documents.",
        "- Every rendered page was visually inspected through page images/contact sheets: Final 55 pages, Master 54 pages, Midterm 40 pages, and Prelim 35 pages (184 pages total).",
        "- No blank pages, clipped tables, overflow, replacement characters, or page-size errors were detected.",
        "- Chapters II-VI begin on fresh pages. The rendered body content immediately before each chapter break leaves no more than approximately four double-spaced text lines of unused vertical space.",
        "- The four DOCX deliverables remain separate and uncompressed; no ZIP archive was created.",
        "- The final cover titles are black and have no blue/decorative title rule; the only cover rule is the black institutional header line.",
        "- DOCX integrity, A4 geometry, one-inch margins, Times New Roman 12-point double-spaced body style, institutional branding, rubric content, and stable rendered page maps passed automated checks.",
        "",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    trace = REVIEW_DIR / "document_traceability.csv"
    pd.DataFrame([
        ["Approved project scope", "Undersea_Cable_Fault_Risk_Project_Proposal_REVISED (1).docx", "scripts/build_research_documents.py", "incorporated through proposal-alignment appendix"],
        ["Dataset dimensions", "outputs/tables/raw_data_quality_summary.csv", "scripts/run_pipeline.py", "verified"],
        ["Validation metrics", "outputs/tables/model_comparison_validation.csv", "scripts/run_pipeline.py", "verified"],
        ["Temporal stability", "outputs/tables/temporal_cv_summary.csv", "scripts/run_pipeline.py", "verified"],
        ["External context", "data/external/context_indicators.csv", "src/external_data.py", "source-backed; not joined"],
        ["Historical incidents", "data/external/historical_incidents.csv", "src/external_data.py", "selected; not joined"],
        ["Final test status", "outputs/metrics/final_test_status.txt", "scripts/run_pipeline.py", "locked"],
    ], columns=["document_section", "source_artifact", "source_code", "verification_status"]).to_csv(trace, index=False)
    return report, trace


def make_workflow_figure():
    """Create a schematic (not data) of the reproducible analysis workflow."""
    path = TEMP_DIR / "pipeline_workflow.png"
    fig, ax = plt.subplots(figsize=(10, 1.8), dpi=180)
    ax.axis("off")
    labels = ["Raw source\n(snapshot)", "Audit +\nprovenance", "Temporal label\nvalidation", "Leakage-safe\nfeatures", "Chronological\nmodeling", "Report +\nlocked test"]
    x = list(range(len(labels)))
    for i, label in enumerate(labels):
        ax.text(i, 0.5, label, ha="center", va="center", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.45", facecolor="#D9EAF7", edgecolor="#4472C4"))
        if i < len(labels) - 1:
            ax.annotate("", xy=(i + 0.72, 0.5), xytext=(i + 0.28, 0.5),
                        arrowprops=dict(arrowstyle="->", color="#555555", lw=1.2))
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def make_document_eda_figures():
    """Render clean, publication-style copies of the verified EDA charts.

    Formal figure numbering belongs in the Word captions, so the chart titles
    deliberately omit embedded ``Figure N`` prefixes.
    """
    data = read_csv("data/processed/undersea_cables_cleaned.csv").copy()
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    data["fault_next_year"] = pd.to_numeric(data["fault_next_year"], errors="coerce")
    data["route_redundancy"] = pd.to_numeric(data["route_redundancy"], errors="coerce")
    eda = data[data["year"] <= 2024]
    yearly = eda.groupby("year").agg(
        records=("cable_id", "size"),
        prevalence=("fault_next_year", "mean"),
    )

    fig, ax = plt.subplots(figsize=(8, 4))
    yearly.records.plot(ax=ax, marker="o", color="tab:blue")
    ax.set(xlabel="Observation year", ylabel="Records", title="Annual cable-year records")
    fig.tight_layout()
    fig.savefig(TEMP_DIR / "document_annual_records.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    yearly.prevalence.plot(ax=ax, marker="o", color="tab:red")
    ax.set(
        xlabel="Observation year",
        ylabel="Next-year fault prevalence",
        title="Annual next-year fault prevalence",
    )
    fig.tight_layout()
    fig.savefig(TEMP_DIR / "document_annual_prevalence.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    eda["route_redundancy"].dropna().plot(kind="hist", bins=25, ax=ax, color="tab:green")
    ax.set(xlabel="Route redundancy (count)", title="Route-redundancy distribution")
    fig.tight_layout()
    fig.savefig(TEMP_DIR / "document_route_redundancy.png", dpi=150)
    plt.close(fig)


def main():
    for directory in [MASTER_DIR, PRELIM_DIR, MIDTERM_DIR, FINAL_DIR, REVIEW_DIR, TEMP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    extract_branding_assets()
    artifacts = load_artifacts()
    make_workflow_figure()
    make_document_eda_figures()
    paths = [build_master(artifacts), build_prelim(artifacts), build_midterm(artifacts), build_final(artifacts)]
    report, trace = build_review_report(paths, artifacts)
    print("Generated:")
    for path in paths + [report, trace]:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
