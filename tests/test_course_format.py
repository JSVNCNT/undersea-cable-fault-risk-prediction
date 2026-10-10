"""Formatting rules are explicit and do not imply completed field research."""
import importlib.util
from pathlib import Path
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('course_format', ROOT / 'scripts/revise_course_format.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_caption_number_above_italic_title():
    doc = Document()
    p = doc.add_paragraph()
    module.caption(p, 'Table', 2, 'Research purposes')
    assert p.text == 'Table 2\nResearch purposes'
    assert p.runs[0].bold and p.runs[-1].italic
    assert p.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.LEFT
    assert p.paragraph_format.keep_with_next
    assert p.runs[0].font.size.pt == 12


def test_source_notes_preserve_scope():
    assert 'synthetic' in module.table_note('Preliminary data dictionary')
    assert 'not final-test' in module.table_note('Development validation model comparison')
    assert 'not model inputs' in module.table_note('Source-backed context indicators')
    assert 'not training data' in module.table_note('Selected documented historical incidents')
    assert 'do not assert' in module.table_note('Correction record template')


def test_source_papers_not_overwritten():
    for stage in module.STAGES:
        assert module.path_for(stage) != module.path_for(stage, 'RATIONALE')
        assert module.path_for(stage).parent == ROOT / 'deliverables' / stage


def test_reference_format_links_and_italics_without_text_change():
    doc = Document()
    doc.add_paragraph('REFERENCES')
    text = 'Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5-32. https://doi.org/10.1023/A:1010933404324'
    p = doc.add_paragraph(text)
    doc.add_paragraph('APPENDICES')
    module.format_references(doc)
    assert p.text == text
    assert p.paragraph_format.first_line_indent.inches == -.5
    assert p.paragraph_format.line_spacing == 2
    assert [r.text for r in p.runs if r.italic] == ['Machine Learning, 45']
    assert p._p.xpath('./w:hyperlink')
