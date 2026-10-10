"""Course-specific caption/reference corrections, without changing analyses."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.text.paragraph import Paragraph
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import pymupdf

from revise_indicator_documents import capture_preserved, locate, norm

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'deliverables/review/course_format_revision'
META = REVIEW / 'revision_manifest.json'
STAGES = ('master', 'final', 'midterm', 'prelim')
REFERENCE = Path('C:/Users/Vincent/Downloads/2026-2027 INTRODUCTION TO DATA SCIENCE PROJECT.docx')
REFERENCE_HASH = '48c0a7b94d7df72262eb71cd9827845f76905bf21997d1e93cc3d3d08a0abdf7'
EXTRA_TABLE_TITLES = {
    'Term': 'Definition of important terms',
    'Proposal commitment': 'Approved proposal alignment',
    'Claim/output': 'Research artifact traceability',
    'Area': 'Completion and evidence checklist',
}
ITALIC_PHRASES = (
    'Machine Learning, 45',
    'Submarine cables and the oceans: Connecting the world',
    'Oceanography, 27',
    'Pattern Recognition Letters, 27',
    'IEEE Transactions on Knowledge and Data Engineering, 21',
    'Damage to submarine cables caused by anchors',
    'ITU-T Supplement 41: Design guidelines for optical fibre submarine cable systems',
    'Restoring connectivity in Tonga through collaborative disaster response',
    'Global Connectivity Report 2025: Chapter 3',
    "Strengthening the world's digital backbone",
    'Submarine cable resilience',
    'Economic Geography, 78',
    'Journal of Machine Learning Research, 12',
    'PLOS ONE, 10',
    'Undersea cables and global digital infrastructure',
    'The undersea network',
    'Written testimony on submarine cable security',
    'Goal 9: Industry, innovation and infrastructure',
    "Unlocking the Philippines' digital transformation by increasing internet connectivity",
)


def path_for(stage, revision='COURSE_FORMAT'):
    return ROOT / f'deliverables/{stage}/Undersea_Cable_Fault_Research_{stage.upper()}_{revision}_REVISED.docx'


def font(run, size=12):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    fonts = run._r.get_or_add_rPr().rFonts
    for attr in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        fonts.set(qn('w:' + attr), 'Times New Roman')


def inserted_before(element, parent):
    p = OxmlElement('w:p')
    element.addprevious(p)
    return Paragraph(p, parent)


def inserted_after(element, parent):
    p = OxmlElement('w:p')
    element.addnext(p)
    return Paragraph(p, parent)


def caption(paragraph, kind, number, title):
    paragraph.clear()
    f = paragraph.paragraph_format
    f.alignment = WD_ALIGN_PARAGRAPH.LEFT
    f.first_line_indent = Inches(0)
    f.line_spacing = 1
    f.space_before = Pt(0)
    f.space_after = Pt(3)
    f.keep_with_next = True
    f.keep_together = True
    number_run = paragraph.add_run(f'{kind} {number}')
    font(number_run)
    number_run.bold = True
    number_run.add_break()
    title_run = paragraph.add_run(title)
    font(title_run)
    title_run.italic = True


def note(paragraph, text):
    f = paragraph.paragraph_format
    f.alignment = WD_ALIGN_PARAGRAPH.LEFT
    f.first_line_indent = Inches(0)
    f.line_spacing = 1
    f.space_before = Pt(0)
    f.space_after = Pt(6)
    f.keep_together = True
    lead = paragraph.add_run('Note. ')
    font(lead, 10)
    lead.italic = True
    font(paragraph.add_run(text), 10)


def table_note(title):
    if 'Source-backed context' in title:
        return 'Cited ITU, ICPC and TeleGeography records; context only, not model inputs.'
    if 'historical incidents' in title:
        return 'Cited incident records; selected cases, not training data or a complete inventory.'
    if title in ('Correction record template', 'Group contribution record template'):
        return 'Blank template; these cells do not assert completed work or instructor approval.'
    if title == 'Purpose of the research analyses':
        return 'Group-prepared research-question mapping; not new observations or an experiment.'
    if any(word in title.lower() for word in ('model', 'comparison', 'validation', 'association', 'statistical')):
        return 'Saved development outputs; synthetic panel only, not final-test evidence.'
    if any(word in title.lower() for word in ('dictionary', 'data-quality', 'raw-versus', 'distribution', 'partition', 'split', 'indicator registry')):
        return 'Project summary of the disclosed synthetic source (sergionefedov, n.d.).'
    return 'Group-prepared documentation; see the accompanying explanations and evidence record.'


def update_list(doc, label, captions):
    within = False
    entries = []
    for p in doc.paragraphs:
        if p.text == label:
            within = True
        elif within and p.style.name.startswith('Heading'):
            break
        elif within and '\t' in p.text:
            entries.append(p)
    if not entries:
        raise ValueError(f'Missing caption list: {label}')
    template = deepcopy(entries[0]._p)
    anchor = entries[-1]._p
    for kind, number, title in captions:
        element = deepcopy(template)
        anchor.addnext(element)
        anchor = element
        p = Paragraph(element, entries[0]._parent)
        p.runs[0].text = f'{number}.    {title}'
        p.runs[-1].text = '-'
    for p in entries:
        p._p.getparent().remove(p._p)


def format_references(doc):
    start = next(i for i, p in enumerate(doc.paragraphs) if p.text == 'REFERENCES')
    end = next(i for i, p in enumerate(doc.paragraphs) if i > start and p.text == 'APPENDICES')
    for p in doc.paragraphs[start + 1:end]:
        if not p.text.strip():
            continue
        text = p.text
        phrases = [x for x in ITALIC_PHRASES if x in text]
        if len(phrases) != 1:
            raise ValueError(f'Reference-title mapping ambiguous: {text}')
        italic = phrases[0]
        a = text.index(italic)
        b = a + len(italic)
        p.clear()
        for value, emphasis in ((text[:a], False), (text[a:b], True), (text[b:], False)):
            # URLs become genuine active hyperlinks without changing their text.
            chunks = re.split(r'(https?://\S+)', value)
            for chunk in chunks:
                if not chunk:
                    continue
                if chunk.startswith(('http://', 'https://')):
                    link = OxmlElement('w:hyperlink')
                    link.set(qn('r:id'), p.part.relate_to(chunk, RT.HYPERLINK, is_external=True))
                    holder = OxmlElement('w:r')
                    from docx.text.run import Run
                    run = Run(holder, p)
                    run.text = chunk
                    font(run)
                    run.font.underline = False
                    link.append(holder)
                    p._p.append(link)
                else:
                    run = p.add_run(chunk)
                    font(run)
                    run.italic = emphasis
        f = p.paragraph_format
        f.alignment = WD_ALIGN_PARAGRAPH.LEFT
        f.left_indent = Inches(.5)
        f.first_line_indent = Inches(-.5)
        f.line_spacing = 2


def text_without_maps(doc):
    result = []
    for p in doc.paragraphs:
        if '\t' in p.text or re.match(r'^(Table|Figure) \d+[.\n]', p.text):
            continue
        if p.text.startswith(('Note. ', 'Presented to ', 'Submitted to: ')) or p.text in ('By:', 'Submitted By:', 'And to the Faculty of the'):
            continue
        if p.text.strip():
            result.append(re.sub(r'Why Figure \d+ is included:', 'Why this figure is included:', p.text))
    return Counter(result)


def build(stages=STAGES):
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == REFERENCE_HASH
    REVIEW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(META.read_text(encoding='utf-8')) if META.exists() and tuple(stages) != STAGES else {}
    for stage in stages:
        source = path_for(stage, 'RATIONALE')
        doc = Document(source)
        tables = []
        date_tables = 0
        for table in doc.tables[:-3]:
            prior = table._tbl.getprevious()
            existing = Paragraph(prior, doc._body) if prior.tag == qn('w:p') else None
            match = re.match(r'^Table\s+\d+\.\s*(.+)$', existing.text) if existing else None
            if match:
                p = existing
                title = match.group(1)
            else:
                p = inserted_before(table._tbl, doc._body)
                first_cell = table.cell(0, 0).text
                if first_cell == 'Date':
                    title = ('Correction record template', 'Group contribution record template')[date_tables]
                    date_tables += 1
                else:
                    title = EXTRA_TABLE_TITLES[first_cell]
            number = len(tables) + 1
            caption(p, 'Table', number, title)
            tables.append(('Table', number, title))
            n = inserted_after(table._tbl, doc._body)
            note(n, table_note(title))
            borders = table._tbl.tblPr.find(qn('w:tblBorders'))
            if borders is None:
                borders = OxmlElement('w:tblBorders')
                table._tbl.tblPr.append(borders)
            for side in ('top', 'bottom', 'left', 'right', 'insideH', 'insideV'):
                edge = borders.find(qn('w:' + side))
                if edge is None:
                    edge = OxmlElement('w:' + side)
                    borders.append(edge)
                edge.set(qn('w:val'), 'single' if side in ('top', 'bottom') else 'nil')
                edge.set(qn('w:sz'), '6')
                edge.set(qn('w:color'), '000000')
            for cell in table.rows[0].cells:
                props = cell._tc.get_or_add_tcPr()
                cell_borders = props.find(qn('w:tcBorders'))
                if cell_borders is None:
                    cell_borders = OxmlElement('w:tcBorders')
                    props.append(cell_borders)
                edge = OxmlElement('w:bottom')
                edge.set(qn('w:val'), 'single')
                edge.set(qn('w:sz'), '6')
                edge.set(qn('w:color'), '000000')
                cell_borders.append(edge)
            # Improve legibility of the dense results/context tables. Leave
            # the retained four-column source dictionaries at their own size.
            result_titles = ('statistical association', 'validation model', 'cross-validation',
                             'operational block comparison', 'Source-backed context', 'historical incidents')
            if any(token.lower() in title.lower() for token in result_titles):
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                if run.font.size and run.font.size.pt < 10:
                                    font(run, 10)
            # 2.5pt vertical cell padding keeps research tables readable while
            # making room for their required two-line captions and source notes.
            # Official rubric forms are excluded from this local adjustment.
            for cell in {id(c._tc): c for row in table.rows for c in row.cells}.values():
                props = cell._tc.get_or_add_tcPr()
                margins = props.find(qn('w:tcMar'))
                if margins is None:
                    margins = OxmlElement('w:tcMar')
                    props.append(margins)
                for side in ('top', 'bottom'):
                    node = margins.find(qn('w:' + side))
                    if node is None:
                        node = OxmlElement('w:' + side)
                        margins.append(node)
                    compact = title == 'Purpose of the research analyses' or any(token.lower() in title.lower() for token in result_titles)
                    node.set(qn('w:w'), '30' if compact else '50')
                    node.set(qn('w:type'), 'dxa')
            for row in table.rows:
                properties = row._tr.get_or_add_trPr()
                if properties.find(qn('w:cantSplit')) is None:
                    properties.append(OxmlElement('w:cantSplit'))
            for cell in table.rows[-1].cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
            if stage == 'midterm' and title == 'Development validation model comparison':
                # Exact DXA geometry: a readable model-name column and six
                # numeric columns wide enough for the 10pt metric values.
                total = sum(int(col.get(qn('w:w'))) for col in table._tbl.tblGrid)
                numeric_width = (total - 1750) // 6
                widths = [total - numeric_width * 6] + [numeric_width] * 6
                table.autofit = False
                table_width = table._tbl.tblPr.find(qn('w:tblW'))
                table_width.set(qn('w:w'), str(total))
                table_width.set(qn('w:type'), 'dxa')
                for col, width in zip(table._tbl.tblGrid, widths):
                    col.set(qn('w:w'), str(width))
                for row in table.rows:
                    for cell, width in zip(row.cells, widths):
                        cell._tc.get_or_add_tcPr().tcW.set(qn('w:w'), str(width))
                        cell._tc.get_or_add_tcPr().tcW.set(qn('w:type'), 'dxa')
        figures = []
        for p in list(doc.paragraphs):
            match = re.match(r'^Figure\s+(\d+)\.\s*(.+)$', p.text)
            if not match:
                continue
            number, title = int(match.group(1)), match.group(2)
            drawing = p._p.getprevious()
            assert drawing.findall('.//' + qn('w:drawing'))
            caption(p, 'Figure', number, title)
            drawing.addprevious(p._p)
            drawing_p = Paragraph(drawing, doc._body)
            drawing_p.paragraph_format.keep_with_next = True
            # A modest, proportional reduction makes room for the source note;
            # pixel data, labels and all analytical values remain unchanged.
            extent = drawing.find('.//' + qn('wp:extent'))
            old_height = int(extent.get('cy'))
            new_height = old_height - int(Pt(3 if number == 1 else 12))
            ratio = new_height / old_height
            new_width = round(int(extent.get('cx')) * ratio)
            extent.set('cx', str(new_width))
            extent.set('cy', str(new_height))
            picture_extent = drawing.find('.//' + qn('a:ext'))
            picture_extent.set('cx', str(new_width))
            picture_extent.set('cy', str(new_height))
            n = inserted_after(drawing, doc._body)
            detail = ('Group-created workflow; not a live monitoring architecture.' if number == 1 else 'Group-created figure from the synthetic panel (sergionefedov, n.d.).')
            note(n, detail)
            figures.append(('Figure', number, title))
            purpose = Paragraph(n._p.getnext(), doc._body)
            assert purpose.text.startswith('Why this figure is included:')
            purpose.runs[0].text = purpose.runs[0].text.replace('Why this figure is included:', f'Why Figure {number} is included:', 1)
        update_list(doc, 'LIST OF TABLES', tables)
        update_list(doc, 'LIST OF FIGURES', figures)
        format_references(doc)
        for p in doc.paragraphs[:20]:
            if p.text.startswith('Presented to '):
                p.runs[0].text = p.runs[0].text.replace('Presented to ', 'Submitted to: \n', 1)
                faculty = inserted_after(p._p, doc._body)
                faculty._p.insert(0, deepcopy(p._p.pPr))
                font(faculty.add_run('And to the Faculty of the'))
            elif p.text == 'By:':
                p.runs[0].text = 'Submitted By:'
        for p in doc.paragraphs:
            if p.style.name == 'Heading 2' and '\t' not in p.text:
                # One coherent subsection-spacing override, not main-text
                # compression or hidden chapter-specific padding.
                p.paragraph_format.space_before = Pt(7)
        # Do not use a LibreOffice save to refresh fields or alter opaque parts.
        output = path_for(stage)
        doc.save(output)
        assert capture_preserved(source) == capture_preserved(output)
        assert text_without_maps(Document(source)) == text_without_maps(doc)
        assert [[c.text for r in t.rows for c in r.cells] for t in Document(source).tables] == [[c.text for r in t.rows for c in r.cells] for t in doc.tables]
        manifest[stage] = dict(source=str(source), output=str(output), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), preserved_parts=capture_preserved(source), tables=tables, figures=figures)
    META.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'{len(stages)} separate course-format copies created; source content and all table cells preserved.')


def paginate(directory):
    manifest = json.loads(META.read_text(encoding='utf-8'))
    for stage, info in manifest.items():
        output = path_for(stage)
        with pymupdf.open(directory / stage / (output.stem + '.pdf')) as pdf:
            first = next(i for i,p in enumerate(pdf) if 'CHAPTER I:' in p.get_text() and 'Submarine fiber-optic cables form' in p.get_text())
            doc = Document(output)
            entries = {}
            mode = None
            for p in doc.paragraphs:
                if p.text in ('LIST OF FIGURES', 'LIST OF TABLES', 'TABLE OF CONTENTS'):
                    mode = p.text
                if '\t' not in p.text or len(p.runs) < 3:
                    continue
                label = p.text.split('\t')[0].strip()
                if mode in ('LIST OF FIGURES', 'LIST OF TABLES'):
                    number = int(re.match(r'\d+', label).group())
                    kind, number, title = info['figures' if mode == 'LIST OF FIGURES' else 'tables'][number - 1]
                    wanted = f'{kind} {number}\n{title}'
                else:
                    if label in ('ABSTRACT', 'APPROVAL AND EVALUATION PAGE', 'LIST OF FIGURES', 'LIST OF TABLES', 'TABLE OF CONTENTS'):
                        continue
                    wanted = label.split(':', 1)[1].strip() if label.startswith('CHAPTER ') else label
                value = locate(pdf, wanted, first) - first + 1
                p.runs[-1].text = str(value)
                entries[label] = value
            doc.save(output)
            info.update(physical_pages=len(pdf), physical_body_start=first + 1, page_map=entries)
            print(stage, len(pdf), 'pages')
    META.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def verify(directory):
    manifest = json.loads(META.read_text(encoding='utf-8'))
    report = {}
    for stage, info in manifest.items():
        source, output = Path(info['source']), path_for(stage)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == info['source_sha256']
        assert capture_preserved(output) == info['preserved_parts']
        doc = Document(output)
        assert text_without_maps(Document(source)) == text_without_maps(doc)
        assert [[c.text for r in t.rows for c in r.cells] for t in Document(source).tables] == [[c.text for r in t.rows for c in r.cells] for t in doc.tables]
        assert doc.styles['Normal'].font.name == 'Times New Roman'
        assert doc.styles['Normal'].font.size.pt == 12 and doc.styles['Normal'].paragraph_format.line_spacing == 2
        for section in doc.sections:
            assert abs(section.page_width.cm - 21) < .03 and abs(section.page_height.cm - 29.7) < .03
            assert all(abs(m.inches - 1) < .01 for m in (section.top_margin, section.bottom_margin, section.left_margin, section.right_margin))
        for p in doc.paragraphs:
            if re.match(r'^(Table|Figure) \d+\n', p.text):
                assert p.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.LEFT
                assert p.runs[0].bold and p.runs[-1].italic
                assert p.paragraph_format.keep_with_next and p.paragraph_format.keep_together
                assert p._p.getnext().tag == (qn('w:tbl') if p.text.startswith('Table') else qn('w:p'))
                if p.text.startswith('Figure'):
                    assert p._p.getnext().findall('.//' + qn('w:drawing'))
        assert 'synthetic' in ' '.join(p.text for p in doc.paragraphs).lower()
        references = next(i for i,p in enumerate(doc.paragraphs) if p.text == 'REFERENCES')
        appendices = next(i for i,p in enumerate(doc.paragraphs) if p.text == 'APPENDICES')
        reference_texts = [p.text for p in doc.paragraphs[references+1:appendices] if p.text]
        assert reference_texts == sorted(reference_texts, key=str.casefold)
        assert all(p.paragraph_format.first_line_indent.inches == -.5 and p.paragraph_format.line_spacing == 2 and any(r.italic for r in p.runs) for p in doc.paragraphs[references+1:appendices] if p.text)
        with pymupdf.open(directory / stage / (output.stem + '.pdf')) as pdf:
            first = info['physical_body_start'] - 1
            assert len(pdf) == info['physical_pages']
            gaps = []
            for i, page in enumerate(pdf):
                text = page.get_text()
                assert '\ufffd' not in text
                assert any(72 <= b[1] and b[3] < 780 and norm(b[4]) for b in page.get_text('blocks')) or i == 0
                if i < first:
                    continue
                spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
                numbers = [s for s in spans if s['bbox'][1] > 800 and s['text'].strip().isdigit()]
                assert len(numbers) == 1 and numbers[0]['text'].strip() == str(i-first+1)
                assert numbers[0]['size'] == 12 and 'TimesNewRoman' in numbers[0]['font']
                match = re.search(r'CHAPTER (II|III|IV|V|VI):', text)
                if match:
                    assert next(b[1] for b in page.get_text('blocks') if match.group(0) in b[4]) < 120
                    bottom = max(b[3] for b in pdf[i-1].get_text('blocks') if b[1] > 75 and b[3] < 780)
                    gap = round(pdf[i-1].rect.height - 72 - bottom, 1)
                    gaps.append((match.group(1), i+1, gap))
                    assert gap <= 96, f'{stage}: excess whitespace before chapter {match.group(1)}: {gap}'
            ending_label = ('DATA DICTIONARY' if stage == 'prelim' else
                            'UPDATED DATA DICTIONARY AND DATA-QUALITY REPORT' if stage == 'midterm' else 'REFERENCES')
            end_index = locate(pdf, ending_label, first)
            last_bottom = max(b[3] for b in pdf[end_index-1].get_text('blocks') if b[1] > 75 and b[3] < 780)
            last_gap = round(pdf[end_index-1].rect.height - 72 - last_bottom, 1)
            assert last_gap <= 96, f'{stage}: excess whitespace after last chapter: {last_gap}'
            gaps.append(('last chapter end', end_index+1, last_gap))
            for label, value in info['page_map'].items():
                wanted = label.split(':',1)[1].strip() if label.startswith('CHAPTER ') else label
                if re.match(r'^\d+\.', label):
                    # Lists are checked against their own kind rather than an
                    # ambiguous table/figure number stored in the shared map.
                    continue
                assert locate(pdf,wanted,first)-first+1 == value
            mode = None
            for p in doc.paragraphs:
                if p.text in ('LIST OF FIGURES','LIST OF TABLES','TABLE OF CONTENTS'):
                    mode = p.text
                if mode in ('LIST OF FIGURES','LIST OF TABLES') and '\t' in p.text:
                    label, value = p.text.split('\t')
                    number = int(re.match(r'\d+',label).group())
                    kind,number,title = info['figures' if mode == 'LIST OF FIGURES' else 'tables'][number-1]
                    assert locate(pdf,f'{kind} {number}\n{title}',first)-first+1 == int(value)
            report[stage] = dict(pages=len(pdf), tables=len(info['tables']), figures=len(info['figures']), chapter_gaps=gaps)
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == REFERENCE_HASH
    target = REVIEW / 'structural_qa.json'
    target.write_text(json.dumps(dict(status='PASS', documents=report),indent=2)+'\n',encoding='utf-8')
    print(target.read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('build','paginate','verify'))
    parser.add_argument('--pdf-dir', type=Path)
    parser.add_argument('--stages', nargs='+', choices=STAGES, default=STAGES)
    args = parser.parse_args()
    if args.action == 'build':
        build(args.stages)
    else:
        if not args.pdf_dir:
            parser.error('--pdf-dir is required')
        (paginate if args.action == 'paginate' else verify)(args.pdf_dir)
