"""Produce a clean final paper from the verified instructor-feedback revision.

Only presentation text and navigation change. No estimators are loaded, fitted or
scored. Original manuscript, analytical evidence and release remain untouched.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from zipfile import ZipFile

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree
from PIL import Image, ImageDraw
from pypdf import PdfReader

from build_finals_revision import outline_map, roman, set_text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evidence import protected_fingerprints, verify_historical_evidence

SOURCE = ROOT / 'deliverables/final_research_paper_2026-11-05/Undersea_Cable_Fault_Research_FINAL_REVISED.docx'
SOURCE_SHA = 'c3a06131036ad6e55e3694c95eb365373ed1cc0ac9d83e2b242c55315d707ea4'
OUT = ROOT / 'deliverables/final_defense_copy_2026-11-05'
BUILD = OUT / '_build'
PAPER = OUT / 'Synthetic_Undersea_Cable_Fault_Labels_FINAL.docx'
TITLE = 'Predicting Next-Year Fault Labels in a Synthetic Undersea Cable Dataset Using Infrastructure and Operational Indicators'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_package(doc):
    xml = etree.tostring(doc._element, xml_declaration=True, encoding='UTF-8', standalone=True)
    with ZipFile(SOURCE) as source, ZipFile(PAPER, 'w') as target:
        for item in source.infolist():
            target.writestr(item, xml if item.filename == 'word/document.xml' else source.read(item.filename))


def remove_range(first, stop):
    cursor = first
    while cursor is not stop:
        following = cursor.getnext()
        assert cursor.find('.//' + qn('w:sectPr')) is None
        cursor.getparent().remove(cursor)
        cursor = following


def navigation(doc, original):
    start = next(p for p in doc.paragraphs if p.text == 'TABLE OF CONTENTS' and p.style.name == 'Heading 1')
    end = next(p for p in doc.paragraphs if p.text.startswith('CHAPTER I:') and p.style.name == 'Heading 1')
    boundary = end._p.getprevious()
    assert boundary.find('.//' + qn('w:sectPr')) is not None
    heading_template = deepcopy(start._p)
    plain = next(p for p in original if p.text.startswith('ABSTRACT\t'))
    chapter = next(p for p in original if p.text.startswith('CHAPTER I:') and '\t' in p.text)
    sub = next(p for p in original if p.text.startswith('Background of the Project\t'))
    caption = next(p for p in original if p.text.startswith('1.    ') and '\t' in p.text)
    remove_range(start._p, boundary)
    result = []

    def heading(label, new_page=False):
        p = Paragraph(deepcopy(heading_template), doc._body)
        set_text(p, label)
        p.paragraph_format.page_break_before = new_page
        boundary.addprevious(p._p)

    def entry(label, template, kind='heading', wanted=None):
        p = Paragraph(deepcopy(template._p), doc._body)
        for run in p.runs:
            run.text = ''
        while len(p.runs) < 3:
            p.add_run()
        p.runs[0].text, p.runs[1].text, p.runs[-1].text = label, '\t', '0'
        p.paragraph_format.keep_with_next = False
        boundary.addprevious(p._p)
        result.append(dict(label=label, kind=kind, wanted=wanted or label))

    heading('TABLE OF CONTENTS')
    for label in ['ABSTRACT', 'TABLE OF CONTENTS', 'LIST OF TABLES', 'LIST OF FIGURES']:
        entry(label, plain, 'front')
    active = False
    for p in list(doc.paragraphs):
        if p._p is end._p:
            active = True
        if active and p.style.name in ('Heading 1', 'Heading 2') and p.text:
            entry(p.text, chapter if p.style.name == 'Heading 1' else sub)
    for label, kind in [('LIST OF TABLES', 'Table'), ('LIST OF FIGURES', 'Figure')]:
        heading(label, True)
        for p in list(doc.paragraphs):
            match = re.match(r'^' + kind + r' (\d+)\n(.+)$', p.text)
            if match:
                entry(f'{match[1]}.    {match[2]}', caption, 'caption', p.text)
    return result


def build():
    assert sha(SOURCE) == SOURCE_SHA
    doc = Document(SOURCE)
    original = list(doc.paragraphs)
    sections = [etree.tostring(s._sectPr) for s in doc.sections]
    rubrics = [etree.tostring(t._tbl) for t in doc.tables[-3:]]
    set_text(original[1], TITLE)
    original[2]._p.getparent().remove(original[2]._p)
    remove_range(original[22]._p, original[25]._p)

    replacements = {
        26: 'This study tests whether year-end infrastructure and operational indicators distinguish next-year fault labels in a publisher-declared synthetic cable-year panel. Its 4,821 rows cover 500 identifiers, 21 variables and 2015-2026; they are not authenticated real-cable measurements. The workflow audits provenance, temporal labels, cleaning and statistical associations, then compares a dummy baseline, logistic regression, decision tree and random forest using training-fitted preprocessing and chronological splits. Random forest was selected by validation average precision and evaluated once on November 2, 2026 with its original 13 inputs, parameters and decision rule unchanged.',
        28: 'Keywords: synthetic cable-year data; infrastructure and operational indicators; chronological validation; random forest; average precision',
        196: 'We study infrastructure and operational indicators together because they answer different parts of the same question. Infrastructure describes the system: its age, extent, protection and route setting. Operations describes the recorded conditions at the time of assessment: activated capacity, utilization and recent fault experience. Comparing them asks whether knowing both adds useful information beyond knowing only one. The two indicator groups retain the approved proposal\'s focus while the revised title makes the synthetic-label task explicit.',
        199: 'The real-world concern is how to prepare for cable damage and maintain dependable connections. The research problem is narrower: determine whether the available infrastructure and operational fields help distinguish next-year fault labels, and whether their predictions justify further study. The supplied identifiers are synthetic, not verified real assets. We examine patterns within this panel while checking record quality, keeping years in order and making the limits of the evidence clear. Accepting the dataset for an educational experiment does not authenticate its identifiers or establish operational performance.',
        201: 'This project examines whether infrastructure and operational information available at the end of an observation year can distinguish synthetic cable-year records with a positive fault label in the following year. It compares the specified classifiers under the same chronological design and assesses ranking, fault-label detection, errors, stability and interpretability.',
        203: 'What distributions characterize the supplied synthetic cable-year panel in terms of route, operator type, age, length, fiber pairs, landing-country count, capacity, utilization, burial protection, route redundancy, vulnerability, current-year fault history and next-year fault labels?',
        205: 'How well do a majority-class baseline, logistic regression, decision tree and random forest predict next-year fault labels within the synthetic panel when preprocessing and model fitting use only information available before the held-out prediction year?',
        206: 'Which candidate has the highest validation average precision, and how do precision, recall, F1, ROC AUC, error patterns, temporal stability and interpretability qualify that selection?',
        211: 'Train and compare a prior-probability baseline, logistic regression, decision tree and random forest using chronological development partitions; retain validation average precision as the recorded selection criterion.',
        247: 'The final paper integrates six chapters: the research problem, related literature, methodology, implementation, results and conclusions. Scientific appendices identify the source fields, indicator groups, preparation rules, model settings, publication relations and supplementary statistical evidence. The electronic repository retains the corresponding machine-readable results and source code.',
        250: 'Development evidence consists of data audits, leakage decisions, exploratory work, statistical analysis, fitted pipelines, temporal comparisons and error review. The unchanged selected forest was evaluated once on November 2, 2026 after project-owner authorization. Candidate settings were fixed; no documented hyperparameter search is claimed. Operational use would additionally require authenticated records, independent validation, engineering ownership and monitored use.',
        371: 'Final Evaluation Protocol and Access History',
        374: 'The November 2 evaluation preceded the instructor memorandum dated November 4. The record establishes project-owner authorization but does not establish instructor authorization for that earlier unblinding. Consequently, the reported metrics are the completed experiment\'s results, not evidence that the evaluation sequence met every course approval requirement.',
        375: 'The final test is now exposed. The completed run is preserved and is not used to compare alternative candidates, retune thresholds or select new features. Supplementary reports read saved final metrics and restrict new diagnostic inference to development validation. A later model revision would require a separate independent evaluation design.',
        393: 'The repository organizes Python scripts and notebooks into source, data, outputs, documentation and tests. Raw Kaggle files remain in UnderseaCableRisk; real-world context remains separate under data/external/. Document builders read saved research artifacts rather than generating replacement observations or recomputing the final test. Generated papers and their render checks remain separate from the analytical evidence.',
        424: 'Data Preparation Verification',
        425: 'A read-only preparation audit checks the source, prepared tables, configuration and saved comparison without refitting models. It recomputes the numeric medians and categorical modes from the 2,960 eligible training rows in 2015-2022. Table 31 records those training statistics and the zero current input-missing counts. The audit does not change observations or replace the saved fitted pipeline.',
        427: 'scripts/run_pipeline.py requires an explicit new output root for a separate development reproduction and refuses to overwrite the completed experiment. Saved original models, tables and final results remain unchanged. Provenance validation rejects external rows without a source URL, and file-write errors stop the run rather than silently substitute an incomplete result.',
        464: 'Data Safeguards and Software Verification',
        465: 'src/data_loading.py distinguishes intentional numeric blanks from nonblank conversion failures. src/data_validation.py checks populated identifiers, unique keys, integer and binary fields, documented bounds, age consistency and checkable successor-label agreement. Invalid records stop validation rather than pass through an undocumented correction.',
        469: 'The website identifies the dataset as synthetic and presents record reconciliation, conditional validation uncertainty and aggregate supplementary CSV downloads. The original Supabase release, frozen estimator and saved predictive results remain unchanged. Optional read-only SQL verifies the existing database counts without a schema migration.',
        470: 'On November 5, the local Python verification suite passed 83 tests and the frontend/database suite passed 32. The TypeScript/Vite production build passed. All eight research notebooks executed in temporary copies without repeating final inference. These checks support software correctness and evidence preservation; they do not establish real-world predictive validity or an independent hosted-security audit.',
        477: 'Reproducibility also requires visible failures. Assertions stop execution when an expected column disappears, a key duplicates, a label is invalid or an existing protected output is targeted. Audit tables retain the reason a record is excluded, so an apparent prediction improvement cannot depend on an unexplained change to the input population.',
        478: 'The final evaluation was executed once, and the academic website presents saved results and an inference-only demonstration. The application is not a live cable-warning service and does not establish calibrated scores for real assets. Deployment does not supply missing tuning evidence, instructor authorization or empirical validation.',
        481: 'Tables and figures are generated from saved analysis outputs. Their source files and population definitions distinguish descriptive statistics, development diagnostics, final-test results and sector context throughout the paper.',
        492: 'Statistical Reporting and Sensitivity Findings',
        562: 'Table 33 links the four preparation objectives to observable artifacts: training-only replacement statistics, data-quality checks, the fitted prediction pipeline and traceable handling of source records. The one-time final evaluation is reported separately in Tables 21 and 22. Correct preparation supports a valid comparison but does not guarantee that the available predictors will detect most positive labels.',
        575: 'No documented hyperparameter-search or default-versus-tuned comparison preceded final testing. The estimator settings are therefore reported as fixed settings. This limits the comparison: the study does not demonstrate that the selected configuration is optimal. Choosing parameters on the exposed test would invalidate its use as independent evidence for a revised model.',
        589: 'The study demonstrates a reproducible next-year fault-label classification workflow within the synthetic panel. It preserves the cable-year unit, year-end prediction cutoff, documented primary inputs and chronological comparison. The unchanged selected forest was evaluated once. No oversampling, additional cable-year observations or fabricated external measurements were introduced.',
        590: 'The first research question is answered by the panel distributions: the records vary in route, operator type, age, length, capacity, utilization, protection, redundancy and label prevalence. These descriptions characterize the supplied synthetic records, not the global population of real cables.',
        591: 'For the second question, the numeric and categorical analyses identify several within-panel associations, but repeated identifiers, multiple testing and unknown generation rules limit interpretation. The latest-record-per-identifier sensitivity changes the population and leaves route redundancy as the only numeric association surviving Holm adjustment. Statistical significance does not establish a physical fault mechanism.',
        592: 'For the third question, logistic regression, decision tree and random forest detect positive validation labels that the hard majority baseline misses, but all make substantial errors. The supplementary indicator-block comparison does not replace the original combined-input experiment. The final combined forest achieves average precision 0.2877, precision 29.90% and recall 37.18%, detecting 29 of 78 positive labels while missing 49 and producing 68 false alarms.',
        593: 'For the fourth question, random forest is the recorded selection because its validation average precision is highest at 0.3171. Logistic regression is close at 0.3105 and finds more positives at the default decision rule. The paired identifier-bootstrap interval for the AP difference includes zero. The evidence therefore supports the recorded selection, not a claim of clear statistical superiority or operational reliability.',
        594: 'Conclusions From Supplementary Analyses',
        597: 'The website extends access to the records, saved results and supplementary reports through a read-only publication layer and a separate inference service. It does not create a new evaluation, authenticate synthetic identifiers or turn model scores into verified real-cable failure probabilities.',
        608: 'Preserve the completed evaluation, including missed positives and false alarms, and keep validation and final metrics distinct. The frozen model, protocol and saved predictions provide the reference for this experiment. Any later modeling study should define an independent evaluation design before examining its new outcomes.',
        625: 'The contribution is a reproducible classification workflow with explicit timing rules, preparation checks, model comparisons and error reporting. The separation of contextual facts from model rows prevents unsupported empirical claims and identifies the additional records needed for an operational study.',
        626: 'The evidence supports a methodological result even when the available signal is weak. Correct timing, traceable preparation and complete error reporting make the comparison interpretable; they do not guarantee that an operationally useful model can be obtained from this dataset.',
        665: 'The proposal defines the research unit, prediction cutoff, indicator scope and classifier comparison. The title now follows the instructor\'s synthetic-label wording. This clarification changes the interpretation of the study, not its source records, original predictors, model selection or saved final results. The matrix links the retained research commitments to their evidence.',
        710: 'This appendix connects the four preparation objectives to the implemented workflow. The preparation audit adds no cable-year observations. The completed evaluation stores predictions for existing eligible test rows rather than generating new source data.',
        716: 'The evidence concerns preparation and the recorded prediction workflow. It does not establish operational readiness.',
        720: 'This appendix identifies the files that connect the completed research to the website. Table 34 gives a selected module map; the electronic repository contains the full source at https://github.com/JSVNCNT/undersea-cable-fault-risk-prediction. The earlier deployment record references commit 57a1749. Subsequent local revisions retain the original release and frozen model; they are not represented here as a new hosted release.',
        728: 'Read Only Application Execution',
        730: 'The health endpoint reports service readiness and model-release information. The provided training example illustrates how 13 source inputs pass through the saved preprocessing and classifier. Its returned class and uncalibrated score describe a demonstration scenario, not a new labeled observation. Changing an input clears the previous result. Demonstration requests are not appended to the study dataset.',
        732: 'Website Verification Scope',
        733: 'Table 36 separates local automated checks, the observed health response and group-reported launch checks. These support software-readiness claims, not independent validation on real cable records.',
        736: 'A deployment is available only while its service and data connections remain ready. The application reports an unavailable state when readiness or data access fails; the saved research results remain distinct from any live scenario response.',
        737: 'Administrator credentials remain outside the browser in ignored local configuration files. Only blank examples are tracked. Publication requires administrator access; ordinary visitors can read published research but cannot change its evidence through the application.',
        738: 'Appendix F. Supplementary Statistical Evidence and Reproduction',
        739: 'The following evidence supplements the original development analysis. The clustered association model was already available; the latest-record sensitivity and cleaning audit were added after feedback. None replaces the frozen primary selection or supplies a new independent final test.',
        748: 'Supplementary Analysis and Reproduction',
        749: 'scripts/review_research.py writes audit and reporting evidence to a new --output-root below outputs/revisions. Its optional --model-diagnostics mode performs the frozen validation-only bootstrap and permutation checks. The script verifies runtime compatibility, refuses an existing destination and never runs final-test inference.',
        750: 'scripts/check_reproduction.py executes the fixed development workflow in a fresh temporary working copy, fits temporary candidates and compares validation, cross-validation and split evidence with the saved artifacts. It verifies that original fingerprints remain unchanged. requirements-research-frozen.txt records the compatible environment. This is a working-copy check in an existing environment, not independent replication or a fresh dependency installation.',
        751: 'The application execution paths are documented in Appendix E. scripts/publish_revision_assets.py prepares aggregate supplementary downloads bound to the existing release. The seven-table Supabase schema requires no migration. The optional 003_verify_revision_evidence.sql checks the original published release through read-only public-role queries.',
        753: 'Acknowledgment of Documentation Assistance',
        754: 'ChatGPT assisted with language, code explanation, website implementation and document preparation (OpenAI, n.d.). The group is responsible for verifying the implementation, explaining the methods, protecting credentials and accurately reporting the data provenance and research limitations.',
    }
    for index, text in replacements.items():
        set_text(original[index], text)

    # Remove process checklists and review notes; their separate repository records
    # remain available. Keep scientific evidence and actual limitations in the paper.
    remove_range(original[671]._p, original[685]._p)
    remove_range(original[740]._p, original[742]._p)
    for index in [627, 628, 752]:
        original[index]._p.getparent().remove(original[index]._p)
    for index, letter in [(685, 'C'), (709, 'D'), (719, 'E')]:
        set_text(original[index], re.sub(r'^Appendix [A-Z]\.', f'Appendix {letter}.', original[index].text))
    original[685].paragraph_format.page_break_before = True
    original[738].paragraph_format.page_break_before = True
    # The preparation table is about methods, not an unsigned submission checklist.
    preparation = next(t for t in doc.tables if t.cell(0, 0).text == 'Focus')
    for row in list(preparation.rows):
        if row.cells[0].text == 'Full finals completion':
            row._tr.getparent().remove(row._tr)

    # Update all surviving cross-references in one pass so numbers cannot cascade.
    captions = [p for p in doc.paragraphs if re.match(r'^Table \d+\n', p.text)]
    mapping = {int(re.match(r'^Table (\d+)', p.text)[1]): i for i, p in enumerate(captions, 1)}
    assert len(captions) == 36
    caption_nodes = {p._p for p in captions}
    paragraphs = list(doc.paragraphs) + [p for t in doc.tables[:-3] for row in t.rows for cell in row.cells for p in cell.paragraphs]
    appendix_map = {'F': 'C', 'G': 'D', 'H': 'E', 'I': 'F'}
    for p in paragraphs:
        if '\t' in p.text or p._p in caption_nodes:
            continue
        text = re.sub(r'\bTables? (\d+)(?: and (\d+))?', lambda m: ('Tables ' if m[2] else 'Table ') + str(mapping[int(m[1])]) + (' and ' + str(mapping[int(m[2])]) if m[2] else ''), p.text)
        if not p.text.startswith('Appendix '):
            text = re.sub(r'\bAppendix ([FGHI])\b', lambda m: 'Appendix ' + appendix_map[m[1]], text)
        text = text.replace('PR-AUC', 'average precision').replace('Mean PR-AUC', 'Mean AP')
        text = re.sub(r'(^|[.!?]\s+)average precision', lambda m: m[1] + 'Average precision', text)
        if text != p.text:
            set_text(p, text)
    for i, p in enumerate(captions, 1):
        title = p.text.split('\n', 1)[1]
        p.clear()
        run = p.add_run(f'Table {i}')
        run.bold = True
        run.add_break()
        p.add_run(title).italic = True
        # Preserve the source 12-point caption pattern explicitly.
        for run in p.runs:
            run.font.name = 'Times New Roman'
            from docx.shared import Pt
            run.font.size = Pt(12)
    maps = navigation(doc, original)
    assert sections == [etree.tostring(s._sectPr) for s in doc.sections]
    assert rubrics == [etree.tostring(t._tbl) for t in doc.tables[-3:]]
    BUILD.mkdir(parents=True, exist_ok=True)
    write_package(doc)
    manifest = dict(source=str(SOURCE), source_sha256=SOURCE_SHA, paper=str(PAPER), title=TITLE, maps=maps,
                    research_tables=36, retained_figures=4, table_mapping=mapping,
                    intended_removals=['approval page', 'redundant subtitle', 'administrative appendices', 'feedback theme table', 'editorial instructions'],
                    original_model_refitted=False, final_inference_repeated=False)
    (BUILD / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Clean final built with {len(captions)} research tables and {len(maps)} navigation entries.')


def paginate(pdf):
    manifest = json.loads((BUILD / 'manifest.json').read_text())
    reader = PdfReader(pdf)
    outline = outline_map(reader)
    first = outline['CHAPTER I: INTRODUCTION AND PROBLEM DEFINITION']
    texts = [re.sub(r'\W', '', p.extract_text()).casefold() for p in reader.pages]
    doc = Document(PAPER)
    active = False
    index = changed = 0
    values = []
    for p in doc.paragraphs:
        if p.text == 'TABLE OF CONTENTS' and p.style.name == 'Heading 1':
            active = True
        if p.text.startswith('CHAPTER I:') and p.style.name == 'Heading 1':
            break
        if not active or '\t' not in p.text:
            continue
        item = manifest['maps'][index]
        index += 1
        if item['kind'] in ['heading', 'front']:
            physical = outline[item['wanted']]
            value = roman(physical + 1) if item['kind'] == 'front' else str(physical - first + 1)
        else:
            wanted = re.sub(r'\W', '', item['wanted']).casefold()
            physical = next(i for i in range(first, len(texts)) if wanted in texts[i])
            value = str(physical - first + 1)
        changed += p.runs[-1].text != value
        p.runs[-1].text = value
        values.append(dict(**item, physical_page=physical + 1, value=value))
    assert index == len(manifest['maps'])
    if changed:
        write_package(doc)
    manifest.update(navigation=values, physical_pages=len(reader.pages), body_start=first + 1)
    (BUILD / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Navigation {index}; changed {changed}; physical pages {len(reader.pages)}')


def verify(render, visual=False, deliver=False):
    assert sha(SOURCE) == SOURCE_SHA
    source, doc = Document(SOURCE), Document(PAPER)
    manifest = json.loads((BUILD / 'manifest.json').read_text())
    protocol = json.loads((ROOT / 'outputs/revisions/2026-11-05/revision_protocol.json').read_text())
    assert verify_historical_evidence(protocol['protected_sha256'])
    with ZipFile(SOURCE) as old, ZipFile(PAPER) as new:
        assert old.namelist() == new.namelist()
        changed = [n for n in old.namelist() if old.read(n) != new.read(n)]
        assert changed == ['word/document.xml']
        xml = etree.fromstring(new.read('word/document.xml'))
        for tag in ['ins', 'del', 'commentReference', 'commentRangeStart', 'commentRangeEnd']:
            assert not xml.findall('.//' + qn('w:' + tag))
    assert [etree.tostring(s._sectPr) for s in source.sections] == [etree.tostring(s._sectPr) for s in doc.sections]
    assert [etree.tostring(t._tbl) for t in source.tables[-3:]] == [etree.tostring(t._tbl) for t in doc.tables[-3:]]
    assert next(p for p in doc.paragraphs if p.style.name == 'Title').text == TITLE
    whole = '\n'.join(p.text for p in doc.paragraphs)
    for forbidden in ['APPROVAL AND EVALUATION PAGE', 'Member Review and Contribution Confirmation', 'Completion and Evidence Checklist', 'Implemented Correction Record', 'Instructor Revision Evidence', '{{', 'Table pending', 'pending consultation']:
        assert forbidden not in whole, forbidden
    captions = [p.text for p in doc.paragraphs if re.match(r'^Table \d+\n', p.text)]
    assert [int(re.match(r'^Table (\d+)', t)[1]) for t in captions] == list(range(1, 37))
    assert len(doc.inline_shapes) == len(source.inline_shapes)
    assert len(doc.tables) == 39
    pdf = render / (PAPER.stem + '.pdf')
    reader = PdfReader(pdf)
    outline = outline_map(reader)
    assert outline['ABSTRACT'] == 1
    assert 'ABSTRACT' in reader.pages[1].extract_text()
    assert len(reader.pages) == manifest['physical_pages']
    texts = [re.sub(r'\W', '', p.extract_text()).casefold() for p in reader.pages]
    assert re.sub(r'\W', '', TITLE).casefold() in texts[0]
    first = manifest['body_start'] - 1
    for item in manifest['navigation']:
        actual = outline[item['wanted']] if item['kind'] != 'caption' else next(i for i in range(first, len(texts)) if re.sub(r'\W', '', item['wanted']).casefold() in texts[i])
        assert actual + 1 == item['physical_page'], item['label']
        wanted = roman(actual + 1) if item['kind'] == 'front' else str(actual - first + 1)
        assert wanted == item['value']
    for n in range(1, len(reader.pages) + 1):
        assert (render / f'page-{n}.png').exists()
    sheets = render / 'review_sheets'
    sheets.mkdir(exist_ok=True)
    for first in range(1, len(reader.pages) + 1, 4):
        images = [Image.open(render / f'page-{n}.png').convert('RGB') for n in range(first, min(first + 4, len(reader.pages) + 1))]
        w, h = images[0].size
        sheet = Image.new('RGB', (w * 2 + 30, h * 2 + 50), '#dddddd')
        draw = ImageDraw.Draw(sheet)
        for j, im in enumerate(images):
            x, y = (j % 2) * (w + 10) + 5, (j // 2) * (h + 20) + 15
            sheet.paste(im, (x, y))
            draw.text((x, y - 12), f'Physical page {first + j}', fill='black')
        sheet.save(sheets / f'sheet-{(first - 1) // 4 + 1:02}.png')
    result = dict(title=TITLE, pages=len(reader.pages), research_tables=36, figures=4,
                  navigation_entries=len(manifest['navigation']), abstract_physical_page=2,
                  chapter_starts={k: v + 1 for k, v in outline.items() if k.startswith('CHAPTER ')},
                  changed_package_parts=changed, exact_sections_preserved=True, exact_rubrics_preserved=True,
                  original_evidence_unchanged=True, source_unchanged=True,
                  final_inference_repeated=False, docx_sha256=sha(PAPER), pdf_sha256=sha(pdf),
                  visual_review='pending manual inspection')
    if visual:
        result.update(visual_review='Every final page image inspected at readable resolution; no clipping or overlap.',
                      reviewed_pages=list(range(1, len(reader.pages) + 1)),
                      reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
                      page_image_sha256={str(n): sha(render / f'page-{n}.png') for n in range(1, len(reader.pages) + 1)})
    if deliver:
        assert visual, 'Explicit image inspection required before delivery'
        destination = PAPER.with_suffix('.pdf')
        if destination.exists() and sha(destination) != sha(pdf):
            raise FileExistsError('Different delivery PDF already exists')
        shutil.copy2(pdf, destination)
    (BUILD / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['page_image_sha256', 'reviewed_pages']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'paginate', 'verify'])
    parser.add_argument('--pdf', type=Path)
    parser.add_argument('--render-dir', type=Path)
    parser.add_argument('--confirm-visual-review', action='store_true')
    parser.add_argument('--deliver-pdf', action='store_true')
    args = parser.parse_args()
    if args.action == 'build':
        build()
    elif args.action == 'paginate':
        paginate(args.pdf)
    else:
        verify(args.render_dir, args.confirm_visual_review, args.deliver_pdf)
