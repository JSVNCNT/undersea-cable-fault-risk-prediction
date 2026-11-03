"""Create a sample-matched code/results PDF without rerunning any analysis.

Reads existing source and saved development outputs only. The sample supplies
institutional header artwork and layout, never research content or authorship.
Requires reportlab, PyMuPDF and Pillow. Run from the repository environment.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import textwrap
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import pymupdf
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'tmp/pdfs/code_results'
OUT = ROOT / 'output/pdf/Group_5_Undersea_Cable_Code_and_Results.pdf'
TITLE = ('Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems '
         'Using Infrastructure and Operational Indicators')
MEMBERS = ['Bayoguing, Jose Vincent III', 'Cruz, Aurum Fuego', 'Sapio, John Rey']
W, H = 596, 842
LEFT, RIGHT = 72, 524
SOURCES: set[Path] = set()


def read(path: str) -> str:
    p = ROOT / path
    SOURCES.add(p)
    return p.read_text(encoding='utf-8-sig')


def rows(path: str):
    return list(csv.DictReader(read(path).splitlines()))


def excerpt(path: str, *names: str) -> str:
    source = read(path)
    lines = source.splitlines()
    tree = ast.parse(source)
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert len(selected) == len(names), (path, names)
    return '\n\n'.join('\n'.join(lines[n.lineno - 1:n.end_lineno]) for n in selected)


def table(records, columns, labels=None, decimals=3):
    labels = labels or columns
    values = []
    for r in records:
        line = []
        for col in columns:
            value = r[col]
            try:
                if col == 'p':
                    raise ValueError('Keep scientific p-value notation')
                numeric = float(value)
                value = str(int(numeric)) if numeric.is_integer() else f'{numeric:.{decimals}f}'
            except (ValueError, TypeError):
                pass
            line.append(str(value))
        values.append(line)
    widths = [max(len(label), *(len(row[i]) for row in values)) for i, label in enumerate(labels)]
    fmt = lambda row: '  '.join(v.ljust(widths[i]) for i, v in enumerate(row)).rstrip()
    return '\n'.join([fmt(labels), fmt(['-' * x for x in widths]), *(fmt(row) for row in values)])


class Report:
    def __init__(self):
        QA.mkdir(parents=True, exist_ok=True)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        self.raw = QA / 'body.pdf'
        for name, file in [('TimesLocal', 'times.ttf'), ('TimesBoldLocal', 'timesbd.ttf'),
                           ('CodeLocal', 'consola.ttf')]:
            pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / file)))
        self.c = canvas.Canvas(str(self.raw), pagesize=(W, H))
        self.c.setTitle(TITLE + ' Code and Results Documentation')
        self.c.setAuthor('; '.join(MEMBERS))
        self.page = 0
        self.y = 0
        self.audit = []

    def start(self, title=None, description=None):
        if self.page:
            self.c.showPage()
        self.page += 1
        self.y = 92
        self.c.setFillColor(colors.black)
        self.c.setFont('TimesLocal', 12)
        self.c.drawCentredString(W / 2, H - 771, str(self.page))
        if title:
            self.para(title, bold=True, after=4)
        if description:
            self.para('- ' + description, indent=18, after=10)

    def para(self, text, bold=False, indent=0, center=False, after=9, size=12, leading=20.7):
        style = ParagraphStyle('body', fontName='TimesBoldLocal' if bold else 'TimesLocal',
                               fontSize=size, leading=leading,
                               alignment=TA_CENTER if center else TA_JUSTIFY)
        p = Paragraph(escape(text), style)
        _, height = p.wrap(RIGHT - LEFT - indent, H)
        self.check(height)
        p.drawOn(self.c, LEFT + indent, H - self.y - height)
        self.y += height + after

    def check(self, height):
        if self.y + height > 726:
            raise ValueError(f'Page {self.page} overflow at {self.y} plus {height}')

    def panel(self, label, content, code=False):
        self.para(label, size=9.5, leading=13, after=4)
        # Searchable source/output text, not fabricated terminal screenshots.
        size, leading = 8.7, 11.1
        char_width = pdfmetrics.stringWidth('M', 'CodeLocal', size)
        width = int((RIGHT - LEFT - 24) / char_width)
        physical = []
        for line in content.expandtabs(4).splitlines():
            chunks = textwrap.wrap(line, width=width, replace_whitespace=False,
                                   drop_whitespace=False, subsequent_indent='    ') or ['']
            physical.extend(chunks)
        height = len(physical) * leading + 20
        self.check(height)
        self.c.setFillColor(colors.HexColor('#191b1c'))
        self.c.rect(LEFT, H - self.y - height, RIGHT - LEFT, height, fill=1, stroke=0)
        self.c.setFillColor(colors.HexColor('#f2f2f2'))
        self.c.setFont('CodeLocal', size)
        for i, line in enumerate(physical):
            self.c.drawString(LEFT + 12, H - self.y - 15 - i * leading, line)
        self.audit.append({'page': self.page, 'label': label, 'lines': len(physical),
                           'bottom': self.y + height})
        self.y += height + 13

    def picture(self, path, max_height=242):
        from PIL import Image
        p = ROOT / path
        SOURCES.add(p)
        with Image.open(p) as im:
            iw, ih = im.size
        scale = min((RIGHT - LEFT) / iw, max_height / ih)
        width, height = iw * scale, ih * scale
        self.check(height)
        self.c.drawImage(str(p), LEFT + (RIGHT - LEFT - width) / 2,
                         H - self.y - height, width, height)
        self.y += height + 10

    def finish(self, reference):
        self.c.save()
        sample = pymupdf.open(reference)
        # Remove other authors' body content from the copied PDF form as well
        # as excluding it from the visible clip. The original remains intact.
        sample[0].add_redact_annot(pymupdf.Rect(0, 85, W, 741), fill=(1, 1, 1))
        sample[0].add_redact_annot(pymupdf.Rect(0, 759, W, H), fill=(1, 1, 1))
        sample[0].apply_redactions()
        body = pymupdf.open(self.raw)
        final = pymupdf.open()
        for i, original in enumerate(body):
            p = final.new_page(width=W, height=H)
            p.show_pdf_page(p.rect, body, i)
            # Only institutional artwork/text is reused from the sample.
            p.show_pdf_page(pymupdf.Rect(0, 0, W, 85), sample, 0,
                            clip=pymupdf.Rect(0, 0, W, 85))
            p.show_pdf_page(pymupdf.Rect(180, 741, 420, 759), sample, 0,
                            clip=pymupdf.Rect(180, 741, 420, 759))
        final.set_metadata(body.metadata)
        final.save(OUT, garbage=4, deflate=True)
        final.close()
        manifest = {'output': str(OUT), 'pages': len(body), 'reference': str(reference),
                    'reference_use': 'institutional header and footer only; layout reference',
                    'analysis_rerun': False, 'final_test_scored': False,
                    'panels': self.audit,
                    'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(SOURCES)}}
        (QA / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        pdf = pymupdf.open(OUT)
        for i, p in enumerate(pdf):
            p.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(QA / f'page-{i+1:02}.png')
        print(json.dumps({'output': str(OUT), 'pages': len(pdf), 'qa': str(QA)}))


def build(reference):
    r = Report()
    r.start()
    r.para(TITLE, bold=True, center=True, after=44)
    r.para('Code and Results Documentation', center=True, after=0)
    r.para('Introduction to Data Science', center=True, after=52)
    for text in ['Submitted to:', 'Mr. Maxil S. Urocay, MSCS candidate', 'And to the Faculty of the',
                 'College of Information Technology', 'University of Negros Occidental - Recoletos, Inc.']:
        r.para(text, center=True, after=0)
    r.y += 51
    for text in ['In Partial Fulfillment', 'Of the Requirements for the Course', 'COPE0683X']:
        r.para(text, center=True, after=0)
    r.y += 51
    for text in ['Submitted By', 'Group 5 - K44', *MEMBERS]:
        r.para(text, center=True, after=0)
    r.y += 18
    r.para(date.today().strftime('%B %d, %Y'), center=True)

    r.start('Component 1  Data Loading and Quality Assessment',
            'The loader preserves the valid category "None". The saved audit reports the dimensions, labels, '
            'and duplicate checks. The supplied panel is procedurally generated synthetic data; these are '
            'not authenticated observations of real cable systems.')
    r.panel('Source excerpt  src/data_loading.py', excerpt('src/data_loading.py', 'load_csv'), True)
    audit = rows('outputs/tables/raw_data_quality_summary.csv')
    r.panel('Saved output  outputs/tables/raw_data_quality_summary.csv', table(audit, ['check', 'value']))

    r.start('Component 2  Temporal Label Checks and Cleaning',
            'A next-year label is eligible only when the next observed year is consecutive. Records remain '
            'in the cleaned panel even when they cannot enter supervised modeling.')
    r.panel('Source excerpt  src/data_validation.py', excerpt('src/data_validation.py', 'add_temporal_label_audit'), True)
    r.panel('Source excerpt  scripts/run_pipeline.py', excerpt('scripts/run_pipeline.py', 'clean_data'), True)
    clean = rows('outputs/tables/cleaning_summary.csv')[0]
    r.panel('Saved cleaning summary  selected fields', '\n'.join(f'{k}: {clean[k]}' for k in
            ['rows_before', 'rows_after', 'supervised_eligible_rows', 'literal_None_preserved']) +
            '\n\nSix non-consecutive labels excluded from supervised data.\n500 final observations have no forward label.')

    r.start('Component 3  Exploratory Analysis and Statistical Summaries',
            'Descriptive outputs cover observations through 2024, before the reserved final-test year. '
            'Numeric summaries and category counts describe the development-period panel, including rows '
            'not eligible for supervised analysis.')
    eda = rows('outputs/tables/eda/descriptive_statistics.csv')
    wanted = ['age_years', 'length_km', 'design_capacity_tbps', 'lit_capacity_tbps', 'utilization_pct', 'route_redundancy']
    r.panel('Saved output  eda/descriptive_statistics.csv  selected variables',
            table([x for x in eda if x['variable'] in wanted], ['variable', 'count', 'mean', '50%', 'min', 'max'],
                  ['Variable', 'N', 'Mean', 'Median', 'Min', 'Max'], 2))
    for col in ['ocean_route', 'operator_type']:
        r.panel('Saved output  eda/' + col + '_summary.csv',
                table(rows('outputs/tables/eda/' + col + '_summary.csv'), [col, 'count', 'proportion']))

    r.start('Component 4  Exploratory Analysis Graphical Outputs',
            'The saved figures show annual next-year fault prevalence and route redundancy in the '
            'development-period panel. They are descriptive views of the supplied dataset, not observed '
            'global cable fault rates.')
    r.picture('outputs/figures/eda/figure_02_annual_prevalence.png', 241)
    r.para('Saved figure  outputs/figures/eda/figure_02_annual_prevalence.png', size=9, leading=12)
    r.picture('outputs/figures/eda/figure_03_route_redundancy.png', 241)
    r.para('Saved figure  outputs/figures/eda/figure_03_route_redundancy.png', size=9, leading=12)

    r.start('Component 5  Statistical Association Analysis',
            'Saved tests compare eligible development records with and without next-year faults. '
            'Associations are exploratory and non-causal; repeated cable observations and multiple '
            'comparisons limit ordinary p-value interpretation.')
    r.panel('Source excerpt  src/statistics.py', excerpt('src/statistics.py', 'numeric_comparisons'), True)
    nums = rows('outputs/tables/statistics/numeric_comparisons.csv')
    r.panel('Saved numeric comparisons  selected fields  n = 3851',
            table([dict(x, p=f"{float(x['p_value']):.2e}") for x in nums],
                  ['variable', 'median_no_fault', 'median_fault', 'p'], ['Variable', 'Median 0', 'Median 1', 'p']))
    cats = rows('outputs/tables/statistics/categorical_associations.csv')
    r.panel('Saved categorical associations  selected fields',
            table([dict(x, p=f"{float(x['p_value']):.2e}") for x in cats],
                  ['variable', 'cramers_v', 'p', 'n'], ['Variable', 'Cramers V', 'p', 'N']))

    r.start('Component 6  Predictor Preparation and Chronological Splits',
            'The primary analysis uses 13 approved predictors. Imputation and encoding belong inside '
            'each fitted pipeline. The final-test partition is reserved and is not scored here.')
    cfg = read('src/config.py')
    start = cfg.index('CATEGORICAL_PREDICTORS =')
    end = cfg.index('\ndef ensure_directories')
    r.panel('Source excerpt  src/config.py', cfg[start:end].strip(), True)
    r.panel('Source excerpt  src/preprocessing.py', excerpt('src/preprocessing.py', 'chronological_split'), True)
    # No holdout label counts or holdout scores are reproduced in this exhibit.
    split = rows('outputs/tables/data_split_summary.csv')
    r.panel('Saved split summary  label counts omitted for the locked final test',
            table(split, ['partition', 'min_year', 'max_year', 'rows'], ['Partition', 'First year', 'Last year', 'Rows']))

    r.start('Component 7  Model Development Code',
            'The repository defines a majority-class baseline, logistic regression, decision tree, '
            'and random forest. These excerpts show the saved candidate specifications and the '
            'training-versus-validation workflow; the documentation build does not retrain them.')
    r.panel('Source excerpt  src/modeling.py', excerpt('src/modeling.py', 'candidate_estimators'), True)
    r.panel('Source excerpt  src/modeling.py', excerpt('src/modeling.py', 'fit_and_compare'), True)

    r.start('Component 8  Validation Performance and Model Selection',
            'Saved scores evaluate 891 records from 2023-2024, including 170 positive labels. '
            'The primary model selection uses average precision. The majority baseline has high '
            'accuracy because it predicts no faults, but it detects none of the positive records.')
    r.panel('Source excerpt  src/modeling.py', excerpt('src/modeling.py', 'select_model'), True)
    models = rows('outputs/tables/model_comparison_validation.csv')
    r.panel('Saved validation metrics  fault class is the positive class',
            table(models, ['model', 'precision', 'recall', 'f1', 'pr_auc', 'roc_auc', 'accuracy'],
                  ['Model', 'Prec', 'Recall', 'F1', 'AP', 'ROC AUC', 'Acc']))
    selection = json.loads(read('outputs/metrics/model_selection.json'))
    r.panel('Saved model selection  outputs/metrics/model_selection.json',
            '\n'.join(f'{k}: {selection[k]}' for k in ['selected_model', 'development_partitions', 'limitations']))
    r.para('AP denotes average precision, stored as pr_auc in the project CSV. These are validation '
           'results, not final-test performance estimates.', size=11, leading=17)
    cv = rows('outputs/tables/temporal_cv_summary.csv')
    r.panel('Saved expanding-window cross-validation  training years only',
            table(cv, ['model', 'temporal_cv_pr_auc_mean', 'temporal_cv_pr_auc_sd', 'folds'],
                  ['Model', 'Mean AP', 'SD AP', 'Folds']))

    r.start('Component 9  Infrastructure and Operational Indicators',
            'The supplementary comparison separates nine infrastructure predictors and four operational '
            'predictors, then compares them with the combined set. It reuses the development validation '
            'period and does not replace the frozen primary model selection.')
    registry = rows('outputs/tables/indicator_analysis/indicator_registry.csv')
    # Read names directly from the registry rather than reconstructing membership.
    r.panel('Saved indicator registry  selected columns',
            table(registry, ['feature', 'indicator_group']))
    blocks = rows('outputs/tables/indicator_analysis/indicator_block_validation.csv')
    r.panel('Saved indicator-block validation comparison',
            table(blocks, ['indicator_group', 'model', 'predictor_count', 'pr_auc', 'recall', 'f1'],
                  ['Group', 'Model', 'Inputs', 'AP', 'Recall', 'F1']))
    r.para('Infrastructure-only random forest has higher AP in this supplementary comparison '
           '(0.327 versus 0.317 combined), while combined random forest has higher recall '
           '(0.406 versus 0.382). Repeated validation is not independent confirmation.', size=11, leading=17)

    r.start('Component 10  Model Interpretation Outputs',
            'The saved random-forest importances rank inputs used by the model. Higher importance '
            'does not establish a causal effect or show that an indicator can be changed to prevent faults.')
    source = read('scripts/run_pipeline.py').splitlines()
    first = next(i for i, line in enumerate(source) if 'for model_name in ["decision_tree", "random_forest"]:' in line)
    r.panel('Source excerpt  scripts/run_pipeline.py', textwrap.dedent('\n'.join(source[first:first+4])), True)
    imp = rows('outputs/tables/model_interpretation/random_forest_feature_importance.csv')
    r.panel('Saved output  random_forest_feature_importance.csv  first 15 rows',
            table(imp[:15], ['feature', 'importance'], decimals=5))
    r.para('These are impurity-based importances for encoded model inputs. Correlated variables '
           'can share importance, and one-hot categories appear as separate inputs.', size=11, leading=17)

    r.start('Component 11  Validation Error Counts and Final Test Status',
            'The selected random forest detects 69 of the 170 positive validation records and misses '
            '101. The error counts are recorded development results; no final-test predictions or '
            'scores are generated for this document.')
    r.panel('Source excerpt  src/evaluation.py', excerpt('src/evaluation.py', 'evaluate_pipeline', 'final_test_guard'), True)
    r.panel('Saved validation confusion counts  all candidate models',
            table(models, ['model', 'TN', 'FP', 'FN', 'TP']))
    rf = next(x for x in models if x['model'] == 'random_forest')
    r.panel('Selected random forest  validation confusion matrix',
            '                         Predicted 0   Predicted 1\n'
            f"Actual 0  no next-year fault    {rf['TN']:>4}          {rf['FP']:>4}\n"
            f"Actual 1  next-year fault       {rf['FN']:>4}          {rf['TP']:>4}\n\n"
            'TN: correct non-fault   FP: false alarm\nFN: missed fault       TP: detected fault')
    r.panel('Saved status  outputs/metrics/final_test_status.txt', read('outputs/metrics/final_test_status.txt').strip())
    r.para('The 2025 predictor-year holdout remains reserved for authorized final evaluation. '
           'External real-world context and incident records are not joined to the synthetic CAB identifiers.',
           size=11, leading=17)
    r.finish(reference)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    build(parser.parse_args().reference)
