"""Patch the retained formatted finals paper using verified revision evidence.

No research computation, estimator loading, network, or final inference occurs.
Only document.xml changes; source styling/media/rubrics stay byte-identical.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from lxml import etree
import pandas as pd
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'deliverables/final_research_paper_2026-11-03/Undersea_Cable_Fault_Research_FINAL_WEBSITE_UPDATED.docx'
SOURCE_SHA='dbaabc6772e7dae1df8151661d7d48ee762fda2ffa47f1c1bede9c60fc64948d'
OUT=ROOT/'deliverables/final_research_paper_2026-11-05'
BUILD=OUT/'_build'
PAPER=OUT/'Undersea_Cable_Fault_Research_FINAL_REVISED.docx'
REPORT=ROOT/'outputs/revisions/2026-11-05'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def set_text(p,text):
    props=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    p.clear();run=p.add_run(str(text))
    if props is not None:run._r.insert(0,props)


def write_package(doc):
    xml=etree.tostring(doc._element,xml_declaration=True,encoding='UTF-8',standalone=True)
    with ZipFile(SOURCE) as src,ZipFile(PAPER,'w') as target:
        for item in src.infolist():target.writestr(item,xml if item.filename=='word/document.xml' else src.read(item.filename))


def csv(name):return pd.read_csv(REPORT/name,keep_default_na=False)


def number(value,digits=4):
    if value=='':return 'not available'
    return f'{float(value):.{digits}f}'


def pvalue(value):return f'{float(value):.2g}' if float(value)<.001 else number(value)


def build():
    if sha(SOURCE)!=SOURCE_SHA:raise ValueError('Retained source paper fingerprint changed')
    summary=json.loads((REPORT/'revision_summary.json').read_text())
    reproduction=json.loads((REPORT/'clean_copy_reproduction.json').read_text())
    if not summary['protected_evidence_unchanged'] or reproduction['returncode']!=0:raise ValueError('Unverified revision evidence')
    doc=Document(SOURCE); original=list(doc.paragraphs)
    sections=[etree.tostring(s._sectPr) for s in doc.sections]
    rubrics=[etree.tostring(t._tbl) for t in doc.tables[-3:]]
    body=next(p for p in original if p.text.startswith('Submarine fiber-optic cables form'))
    h2=next(p for p in original if p.text=='Data Quality and Cleaning')
    h3=next(p for p in original if p.text=='Infrastructure Indicator Definitions')
    cap_template=next(p for p in original if p.text.startswith('Table 21\n'))
    note_template=next(p for p in original if p.text.startswith('Note. Read-only calculation'))
    source_table=deepcopy(doc.tables[20]._tbl)
    new_captions={}

    def find(text):return next(p for p in doc.paragraphs if p.text==text and '\t' not in p.text)
    def before(anchor,text,template=body):
        p=Paragraph(deepcopy(template._p),doc._body);set_text(p,text)
        anchor._p.addprevious(p._p);return p
    def section(anchor,title,texts):
        before(anchor,title,h2)
        for text in texts:before(anchor,text)
    def table_node(headers,rows,widths):
        node=deepcopy(source_table)
        oldrows=node.findall(qn('w:tr'));header=deepcopy(oldrows[0]);normal=deepcopy(oldrows[1])
        for r in oldrows:node.remove(r)
        grid=node.find(qn('w:tblGrid'));grid.clear()
        node.find(qn('w:tblPr')).find(qn('w:tblW')).set(qn('w:w'),str(sum(widths)))
        for width in widths:
            el=OxmlElement('w:gridCol');el.set(qn('w:w'),str(width));grid.append(el)
        for i,values in enumerate([headers]+rows):
            row=deepcopy(header if i==0 else normal)
            cell_template=deepcopy(row.findall(qn('w:tc'))[0])
            for cell in row.findall(qn('w:tc')):row.remove(cell)
            for j,(value,width) in enumerate(zip(values,widths)):
                cell=deepcopy(cell_template);cell.find(qn('w:tcPr')).find(qn('w:tcW')).set(qn('w:w'),str(width))
                paragraphs=cell.findall(qn('w:p'))
                for extra in paragraphs[1:]:cell.remove(extra)
                p=Paragraph(paragraphs[0],doc._body);p.clear()
                p.paragraph_format.keep_with_next=i==0
                p.paragraph_format.first_line_indent=Pt(0)
                p.paragraph_format.line_spacing=1
                p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(2)
                r=p.add_run(str(value));r.font.name='Times New Roman';r.font.size=Pt(10);r.bold=i==0
                row.append(cell)
            for el in row.findall('.//'+qn('w:trHeight')):el.getparent().remove(el)
            if i:
                for el in row.findall('.//'+qn('w:tblHeader')):el.getparent().remove(el)
            node.append(row)
        return node
    def table(anchor,key,title,headers,rows,widths,note):
        p=before(anchor,'',cap_template);p.clear()
        r=p.add_run('Table pending');r.bold=True;r.add_break();p.add_run(title).italic=True
        for r in p.runs:r.font.name='Times New Roman';r.font.size=Pt(12)
        new_captions[key]=p
        anchor._p.addprevious(table_node(headers,rows,widths))
        before(anchor,'Note. '+note,note_template)
    def replace_table(index,headers,rows,widths):
        old=doc.tables[index]._tbl;old.getparent().replace(old,table_node(headers,rows,widths))
    def append_text(prefix,addition):
        p=next(p for p in doc.paragraphs if p.text.startswith(prefix) and '\t' not in p.text);set_text(p,p.text+' '+addition)

    # Local corrections preserve source run/paragraph components and approved scope.
    for p in original[157:639]:
        if '\t' in p.text:continue
        text=p.text.replace('following observed cable-year','following calendar year, when a consecutive successor is available').replace('following observed year','following calendar year')
        if text!=p.text:set_text(p,text)
    set_text(original[3],'FINAL TERM RESEARCH PAPER')
    qualifier=before(original[2],'An experimental study using synthetic cable-year records',original[2])
    qualifier.paragraph_format.line_spacing=1
    qualifier.paragraph_format.space_before=Pt(0);qualifier.paragraph_format.space_after=Pt(4)
    for r in qualifier.runs:r.italic=True;r.font.size=Pt(12)
    set_text(original[25], 'This study tests whether year-end infrastructure and operational indicators distinguish next-year fault labels in a publisher-declared synthetic cable-year panel. Its 4,821 rows cover 500 identifiers, 21 variables and 2015-2026; they are not authenticated real-cable measurements. The workflow audits provenance, temporal labels, cleaning and statistical associations, then compares a dummy baseline, logistic regression, decision tree and random forest using training-fitted preprocessing and chronological splits. The selected forest was evaluated once on November 2, 2026 with its original 13 inputs, parameters and decision rule unchanged. The project owner authorized that evaluation; instructor acceptance of its timing remains pending.')
    set_text(original[26], 'Temporal eligibility leaves 4,315 supervised rows: 2,960 for training, 891 for validation and 464 for the final test. Predictors have zero missing values; training-only median and mode imputers are safeguards, and missing targets are never filled. Using 2025 predictors and supplied 2026 labels, the final forest achieves accuracy 74.78%, precision 29.90%, recall 37.18%, F1 0.3314, average precision 0.2877 and ROC AUC 0.6411. It detects 29 of 78 positive labels, misses 49 and produces 68 false alarms. These findings show modest usefulness within the panel, not operational reliability. A research website presents saved evidence and demonstrates the unchanged Python pipeline; deployment does not validate real-world predictions.')
    for p in original:
        if p.text.startswith('Running scripts/run_pipeline.py reproduces'):
            set_text(p, 'The revised scripts/run_pipeline.py refuses to overwrite the completed experiment. A deliberate development reproduction requires an explicit new output root; saved original models, tables and final results remain unchanged. Opening an output CSV in Excel can lock it during a run. The execution guide separates reading saved evidence from isolated development fitting. Source-URL and file-lock errors must be corrected without bypassing provenance validation or inventing results.')
        if p.text.startswith('The repository uses Python scripts and notebooks organized'):
            set_text(p, 'The repository uses Python scripts and notebooks organized into source, data, outputs, documentation, tests and ignored deliverables. Raw Kaggle files remain in UnderseaCableRisk; real-world context remains separate under data/external/. The retained document was generated by scripts/build_research_documents.py. This revision uses scripts/build_finals_revision.py and keeps the source paper unchanged. Generated papers and render checks remain excluded from Git by the deliverables/ rule.')
        if p.text.startswith('Reproduction uses scripts/evaluate_final_holdout.py'):
            set_text(p, 'The original one-time evaluation used scripts/evaluate_final_holdout.py; its preserved evidence is now the reference, not a request to repeat final inference. The completed run directory cannot be reused by that runner. The revised development runner requires a new isolated output root and cannot overwrite the retained experiment. Document revisions read the existing final metrics only.')
        if p.text.startswith('Note. Paths are relative to the repository root;'):
            set_text(p, 'Note. Paths are relative to the repository root; line breaks within paths are for layout only. The revised development runner requires a new output root; ordinary website use never starts model training.')
    append_text('The real-world concern is how to prepare','The approved dataset has been accepted for an explicitly synthetic educational experiment, as confirmed by the project owner on November 5, 2026. This acceptance does not establish empirical authenticity or authorize claims about named assets.')
    append_text('The general', '') if False else None
    general=original[173]
    set_text(general,general.text.replace('records that experience a fault','synthetic records with a positive fault label'))
    for index in range(180,185):
        if original[index].text.startswith('Describe route'):
            set_text(original[index],original[index].text+' All descriptions concern the supplied synthetic panel.')
    # Correct Table 1, the original dictionary roles and ambiguous metric headers.
    for row in doc.tables[0].rows[1:]:
        if row.cells[0].text=='fault_next_year':set_text(row.cells[1].paragraphs[0],'Supplied binary label for calendar year t+1; supervised use requires an observed consecutive successor.')
        if row.cells[0].text=='PR-AUC':
            set_text(row.cells[0].paragraphs[0],'Average precision (AP)')
            set_text(row.cells[1].paragraphs[0],'Ranking measure calculated with average_precision_score. The internal pr_auc field is AP, not trapezoidal precision-recall area.')
    dictionary=csv('final_data_dictionary.csv').set_index('variable')
    for row in doc.tables[1].rows[1:]:
        variable=row.cells[0].text
        set_text(row.cells[2].paragraphs[0],str(dictionary.loc[variable,'role']))
        old=row.cells[3].text
        if variable=='age_years':old='Observation year minus ready-for-service year, in years; equality checked in source.'
        if variable=='is_low_redundancy':old='Verified threshold flag: route_redundancy < 40. Excluded when the continuous count is retained.'
        if variable=='fault_next_year':old='Supplied next-calendar-year label. Missing for each identifier\'s terminal observation, including some before 2026.'
        if variable=='utilization_pct':old='Supplied utilization percentage. Its generating denominator is not documented; do not assume lit/design capacity.'
        set_text(row.cells[3].paragraphs[0],old)
    set_text(next(p for p in original if p.text.startswith('Table 2\n')),'Table 2\nSource variables and final analytical roles')
    for t in doc.tables[:-3]:
        for cell in t.rows[0].cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next=True
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if p.text in ['PR-AUC','Mean PR-AUC']:set_text(p,p.text.replace('PR-AUC','AP'))
                    if p.text in ['dummy_baseline','logistic_regression','decision_tree','random_forest']:
                        set_text(p,p.text.replace('_',' '))
                    if p.text.startswith('Development cleaning, fitting and saved analysis.'):
                        set_text(p,'Development cleaning, fitting and saved analysis. Used only in an isolated working copy for the reproduction check; never called by ordinary website use.')

    anchor=find('Variables and Data Dictionary')
    section(anchor,'Study Population and Record Reconciliation',[
        'The unit is one synthetic identifier observed in one calendar year, not an independent verified fault event. The raw panel has 500 identifiers but only 486 have at least one eligible labeled row. Repeated observations and unequal entry/exit coverage make a simple row average different from an equally weighted average of systems.',
        'Table {{reconciliation}} reconciles the analysis populations. The 500 missing targets are terminal observations per identifier, not 500 observations all in 2026. Six populated labels precede a non-consecutive observed year; two are positive and four negative. Their exclusion leaves 818 positives and 3,497 negatives in 4,315 eligible rows.',
    ])
    reconciliation=csv('record_reconciliation.csv')
    table(anchor,'reconciliation','Record counts and label eligibility by processing stage',['Stage','Rows','IDs','Positive','Negative'],
          [[r.stage.replace('_',' '),str(r.rows),str(r.distinct_ids),str(r.positives),str(r.negatives)] for r in reconciliation.itertuples()],
          [3700,1200,1200,1450,1450], 'Counts are from preserved source records. Missing labels are not class 0. Final-partition counts are existing disclosed information, not new model scoring. Source: revision record_reconciliation.csv.')
    before(anchor,'Development EDA includes 3,860 rows through 2024. Three terminal observations lack labels and six additional predecessors fail temporal eligibility, leaving 3,851 supervised development rows. EDA means therefore use a different population from statistical tests and predictive fitting. The unexplained cause of an absent record is not assumed to be a real cable outage or retirement.')
    annual=csv('annual_panel_coverage.csv')
    table(anchor,'coverage','Annual coverage of the original synthetic panel',['Observation year','Cable-year rows','Unique identifiers'],
          [[str(r.year),str(r.rows),str(r.unique_identifiers)] for r in annual.itertuples()],[2800,3100,3100], 'Row counts equal unique-ID counts within each year because no cable-year key duplicates occur. Identifiers recur across years; coverage changes do not measure worldwide infrastructure growth.')
    before(anchor,'The retained source record gives an access date of September 16, 2026, a Kaggle location, recorded CC0 reuse status and SHA-256 fingerprints. The publisher version identifier, exact acquisition timestamp and complete simulator formula were not independently established. Reproducible file hashes identify this local snapshot without inventing missing metadata. Real cable publications supply motivation, not an external validation set.')

    anchor=find('Median and Categorical Imputation')
    section(anchor,'Parsing Exclusions and Forward Label Checks',[
        'Numeric conversion uses errors="coerce" so conversion problems can be located, but nonblank parsing failures are separately counted and now stop normal loading. The current source has zero such failures. Intentional blank targets are structural missing outcomes, never imputed. A blank categorical field is not silently treated as the valid literal None category.',
        'The temporal audit sorts by cable_id and year, shifts the successor within each identifier, and reindexes the result to the original row index. Sorting establishes chronological neighbors; grouping prevents cross-cable comparisons; reindexing restores correct alignment for unsorted input. A two-year gap never satisfies the one-calendar-year rule.',
        'The supplementary development check compares populated forward labels with fault_this_year in the observed consecutive successor. It finds 3,397 checkable development pairs and zero disagreements. This verifies internal label alignment, not how the simulator generated faults. Successor audit columns are excluded from X. No final-test prediction is generated by this check.',
        'Exclusion conditions are mutually exclusive by target presence: unavailable target versus populated target without a consecutive successor. Both remain in the cleaned panel. Separate test cases cover unsorted input, consecutive years, gaps, terminal rows, duplicates, invalid ranges and malformed numeric values.'
    ])
    gaps=csv('temporal_exclusion_examples.csv')
    table(anchor,'gaps','All nonconsecutive labeled predecessors excluded from supervised use',['Identifier','Year t','Next observed year','Supplied label'],
          [[r.cable_id,str(r.year),str(int(r.next_observed_year)),str(int(r.fault_next_year))] for r in gaps.itertuples()],[2300,1600,3000,2100], 'Rows are preserved for audit. The next observed row is not assumed to represent the missing immediate calendar year.')

    anchor=find('Indicator Groups and Comparative Analysis')
    section(anchor,'Statistical Hypotheses and Supplementary Dependence Checks',[
        'For each numeric rank comparison, the null is that the two outcome-group distributions are equal; the two-sided alternative is that they differ. Mann-Whitney U does not require normally distributed values, but its ordinary p-value assumes independent samples and is not generally a test of medians alone (SciPy, n.d.-b). For each categorical comparison, the null is independence between the category and the label; the alternative is association (SciPy, n.d.-a).',
        'The revision defines a family of 13 omnibus comparisons: ten numeric and three categorical tests, with alpha .05 and Holm-adjusted p-values reported beside the original values. The adjustment was added after feedback, not represented as a preregistered original decision. It addresses multiplicity, not within-cable dependence (statsmodels, n.d.).',
        'A signed rank-biserial effect accompanies numeric U statistics; positive values mean fault-labeled observations tend to rank higher. Cramer\'s V accompanies categorical tests and describes association magnitude without a causal interpretation. Expected cell frequencies are saved to identify sparse contingency tables.',
        'The already implemented multivariable logistic association analysis uses standard errors clustered by identifier. It is distinct from the predictive sklearn logistic classifier. As a supplementary check, one latest eligible development record is selected per identifier without using its outcome. This changes the population from repeated cable-years to 463 identifier-level records; it does not certify independent geographic systems or replace the original pooled analysis. Field availability at year end is assessed from supplied definitions, not independently timestamped operational logs; real prospective availability cannot be established from this simulator alone.'
    ])
    anchor=find('Reproducibility')
    section(anchor,'Exact Temporal Folds and Generalization Scope',[
        'Table {{folds}} lists the four expanding predictor-year folds. Each validation row predicts its following calendar-year label. Training outcomes can extend into the validation predictor year and must be known by that year-end cutoff; they do not extend into the following target year. Fresh preprocessing is fitted within each training fold.',
        'The main split has 424 shared identifiers among 460 validation identifiers. Thus it primarily checks later observations of previously represented synthetic systems, with some newly represented IDs. The aggregate score is not a separately validated estimate for unseen systems. A held-out-identifier extension would require a documented independent evaluation design and is not silently substituted for the approved experiment.'
    ])
    folds=csv('expanding_window_folds.csv')
    table(anchor,'folds','Expanding development folds by predictor year',['Fold','Training years','Validation year','Train rows','Validation rows'],
          [[str(i+1),f'2015-{int(r.train_max_year)}',str(int(r.validation_year)),str(int(r.n_train)),str(int(r.n_validation))] for i,r in enumerate(folds.itertuples())],
          [700,2500,2100,1800,1900], 'All are development folds. Preprocessing is refitted per fold. No 2025 predictor-year test row is used in these comparisons.')
    section(anchor,'Final Evaluation Access History and Remaining Consultation',[
        'The recorded primary selection is dated October 31, 2026. Aggregate test-label counts had already been disclosed, so the earlier lock meant scoring was procedurally withheld, not that all outcome information was technically inaccessible. The helper did not prevent a researcher from reading source labels or bypassing code.',
        'On November 2, the project owner authorized the existing frozen forest\'s evaluation. Its saved protocol records the model hash, 13 ordered features, preprocessing, parameters and argmax decision rule with ties mapping to class 0. It verifies saved validation reproduction and reserves an exclusive run directory before final inference. The unchanged forest remained fitted only on 2015-2022 predictor rows; training plus validation were not merged for refitting.',
        'That run precedes the instructor memorandum dated November 4. Instructor authorization for the earlier unblinding has not been supplied. The group must disclose the chronology and obtain a decision on how the completed evaluation will be assessed. Acceptance of the synthetic dataset, confirmed by the project owner, is separate from acceptance of this evaluation sequence.',
        'The final test is now exposed. Do not delete the run directory, overwrite its record, evaluate alternative candidates on it, retune a threshold, or call it untouched for a revised model. Revision reports read saved final metrics and limit new diagnostic inference to development validation. Any future model revision needs an approved independent evaluation design.'
    ])

    anchor=find('Technical Limitations')
    section(anchor,'Implemented Revision Safeguards and Verification',[
        'src/data_loading.py now records intentional numeric blanks separately from nonblank conversion failures. src/data_validation.py enforces populated identifiers, unique keys, integer and binary fields, documented bounds, age consistency, and checkable successor agreement. These are executable checks, not only statements in a report.',
        'The default development runner refuses to run over the completed final experiment. An explicit new output root is required for separate reproduction, and generated dictionaries, models, metadata and status records remain in that new scope. scripts/review_research.py writes a new supplementary directory, hashes the original data/models/results before and after, and never fits a classifier or runs final-test inference.',
        'The safeguard tests include future-label and future-record perturbations: altering later values must not change earlier engineered predictors. Other cases check missing intermediate years, terminal rows, unsorted input, literal None, unknown-category handling and training-only replacement statistics. A repeat-run test fails before any model is loaded when final evidence already exists.',
        'scripts/check_reproduction.py executed the development workflow in a fresh retained working copy using the recorded compatible environment. Only temporary fixed-configuration candidates were fitted. Validation metrics, temporal CV results and split summaries matched the originals within numerical tolerance; original evidence remained unchanged. This is a clean working-copy reproduction by the project workflow, not an independent instructor replication or a newly provisioned dependency installation.',
        'The website now retains explicit synthetic provenance, presents the supplementary reconciliation and conditional validation uncertainty, and offers aggregate revision CSV downloads. The original Supabase release, frozen estimator and saved predictive results are unchanged. Optional SELECT-only SQL verifies the existing database counts; no schema migration or cloud publication was performed.',
        'On November 5, the complete local Python verification suite passed 83 tests and the frontend/database suite passed 32. The TypeScript/Vite production build also passed. All eight revised notebooks executed in temporary copies without repeating final inference; notebook_execution.json retains the result. These checks verify software boundaries and local SQL behavior, not real-world predictive validity, independent hosted security or instructor approval. Cross-device browser review remains a manual check.'
    ])

    anchor=find('Validation Model Comparison')
    section(anchor,'Revised Statistical Reporting and Sensitivity Findings',[
        'Table {{numeric}} reports all numeric comparisons on 3,851 eligible development rows: 3,111 negative and 740 positive labels. Ordinary rank-test p-values remain exploratory because identifiers recur. The signed effect scale distinguishes a detectable difference from a large association. A non-significant result does not prove absence of a relationship.',
    ])
    numeric=csv('numeric_associations_holm.csv')
    table(anchor,'numeric','Numeric distribution comparisons with effects and multiplicity adjustment',['Variable','Median 0','Median 1','U','Rank effect','Holm p'],
          [[r.variable.replace('_',' '),number(r.median_no_fault,2),number(r.median_fault,2),number(r.statistic,1),number(r.rank_biserial_fault_higher,3),pvalue(r.p_value_holm_13_tests)] for r in numeric.itertuples()],
          [2800,1200,1200,1700,1000,1100], 'U and medians retain original results. Positive rank effect means higher ranks in class 1. Holm covers ten numeric and three categorical tests together. Raw p-values, separate group sizes and repeated-row cautions remain in the CSV.')
    cat=csv('categorical_associations_holm.csv')
    table(anchor,'categorical','Categorical effects and expected-count diagnostics',['Variable','Cramer V','Holm p','Minimum expected','Cells below 5'],
          [[r.variable.replace('_',' '),number(r.cramers_v,3),pvalue(r.p_value_holm_13_tests),number(r.minimum_expected_count,2),str(r.expected_cells_below_5)] for r in cat.itertuples()],
          [2800,1400,1400,1900,1500], 'Pooled development contingency tables have no expected cell below five. This does not remove dependence across cable-years. Source: categorical_associations_holm.csv.')
    before(anchor,'Route and chokepoint Cramer\'s V values are approximately .155 and .146, whereas operator type is approximately .026. The small effects must not be inflated by small pooled p-values. In the 463-record latest-per-ID sensitivity sample, only route redundancy remains below .05 after the same 13-test Holm adjustment (adjusted p approximately .0232); age, length and the categorical variables do not. The reduced sample and changed year/population weighting differ from the pooled experiment, so this does not prove the pooled associations are false or that variables are irrelevant.')
    before(anchor,'The cable-level chokepoint table has eight expected cells below five, with minimum approximately 1.05; its ordinary chi-square p-value is especially fragile. The existing cluster-robust multivariable results are retained in Appendix I with odds ratios and intervals. Neither standard-error correction nor the single-record sensitivity recovers an undocumented simulator mechanism.')
    before(anchor,'Capacity fields also require distinct interpretation. Among 3,851 development rows, only 273 match utilization = 100 times lit/design capacity within the stated numerical tolerance. The mean absolute difference is about 23.48 percentage points. This rules out treating that simple identity as universally observed in this snapshot; it does not reveal the actual generation formula. Spearman correlations are provided with the revision reports to examine redundancy, not to establish physical causation.')

    anchor=find('Infrastructure and Operational Indicator Results')
    section(anchor,'Conditional Uncertainty in the Recorded Model Advantage',[
        'The primary validation forest AP is .3171 versus logistic .3105, a difference of .0066. Table {{uncertainty}} resamples whole validation identifiers with their existing rows and fixed paired scores. Its interval for the difference includes zero, so the small original point advantage is not robust evidence of superiority. This check does not reselect a model or prove equivalence.',
    ])
    intervals=csv('validation_cluster_bootstrap.csv')
    table(anchor,'uncertainty','Paired identifier-bootstrap validation average precision',['Measure','Estimate','95% lower','95% upper'],
          [[r.measure.replace('_',' '),number(r.estimate),number(r.ci_low),number(r.ci_high)] for r in intervals.itertuples()],[4200,1600,1600,1600],
          '1,000 paired whole-ID resamples, seed 42, percentile intervals. Conditional on the already examined validation period and saved models. No final inference or classifier fitting. This is not independent confirmation or simulator-validity uncertainty.')

    anchor=find('What Data Preparation Establishes')
    section(anchor,'Validation Error Differences Across Recorded Groups',[
        'Table {{errors}} uses the saved forest validation predictions and an exact one-to-one cable_id/year/outcome join to the existing covariates. No new classifier or threshold is selected. Rows are grouped by year, route, operator, fixed age bands and fixed redundancy bands; both the numerator and denominator are shown so a high percentage from a few positives is not mistaken for reliable subgroup performance.',
    ])
    errors=csv('validation_subgroup_errors.csv')
    table(anchor,'errors','Validation subgroup counts and fault-label detection',['Grouping and category','n','Positive','TP','FN','FP','Recall'],
          [[r.grouping.replace('_',' ')+' '+str(r.group)+(' *' if str(r.small_sample_warning).lower()=='true' else ''),str(r.n),str(r.positives),str(r.TP),str(r.FN),str(r.FP),number(r.recall,3)] for r in errors.itertuples()],
          [3400,850,1000,800,800,800,1350], 'Asterisk: fewer than 30 rows or 10 positive labels. These are descriptive, overlapping development subgroups; no causal, fair-treatment or statistically confirmed subgroup ranking is claimed. Exact precision/F1/AP and all confusion counts are in validation_subgroup_errors.csv.')
    before(anchor,'The 2023 validation rows detect 37 of 95 positives and miss 58; 2024 detects 32 of 75 and misses 43. Intra-Asia detects 6 of 27 positives, while Americas detects 21 of 27. Different sizes, recorded covariates and reused validation outcomes limit comparison. These categories are generated groups, not identified affected communities or verified regions of operational risk. No error-cost amount or acceptable operational threshold can be established from this panel.')
    section(anchor,'Predictor Importance and Validation Permutation Checks',[
        'Table {{importance}} sums encoded impurity importances back to all 13 original inputs and compares them with validation AP decreases after permuting one original input. Impurity importance reflects training split improvement and may favor continuous or high-cardinality fields. Permutation asks how the fixed model\'s validation ranking changes when that field is disturbed (scikit-learn developers, n.d.). Neither is a causal effect.',
    ])
    importance=csv('original_predictor_importance.csv').merge(csv('validation_permutation_importance.csv'),on='feature',validate='one_to_one')
    table(anchor,'importance','Original-input impurity importance and validation permutation',['Predictor','Grouped impurity','Mean AP decrease','Permutation SD'],
          [[r.feature.replace('_',' '),number(r.importance),number(r.mean_ap_decrease),number(r.sd_ap_decrease)] for r in importance.itertuples()],
          [3500,1800,1900,1800], 'Five validation-only permutations per input, seed 42. SD measures variation across those perturbations, not a confidence interval. Correlations and row-wise permutations in repeated records limit interpretation; no features are removed or reselected.')
    before(anchor,'Length leads impurity importance at approximately .132 but has a smaller mean validation AP decrease than chokepoint or route. Lit capacity has substantial impurity importance but little mean permutation decrease, consistent with possible shared or unstable predictive information rather than a proven absence of usefulness. Current-year fault has a slightly negative mean decrease with wide permutation variation; it is not evidence that faults protect cables. Rankings concern this fitted model and examined panel, not engineering actionability.')

    # All candidate confusion matrices already exist; make the 2x2 interpretation explicit.
    anchor=find('Temporal Stability and Sensitivity')
    comparison=pd.read_csv(ROOT/'outputs/tables/model_comparison_validation.csv')
    before(anchor,'Table {{matrices}} presents every candidate\'s validation confusion matrix in actual-by-predicted orientation. Random forest finds 69 of 170 positives, logistic regression 88, decision tree 92 and the baseline zero. The higher recall comparators also generate more false flags. AP summarizes ranking across score cutoffs; these confusion counts describe only the recorded hard decision rule.')
    table(anchor,'matrices','Validation confusion matrices for the original candidates',['Model and actual class','Predicted 0','Predicted 1'],
          [[str(r.model).replace('_',' ')+' / actual '+str(actual),str(int(getattr(r,'TN' if actual==0 else 'FN'))),str(int(getattr(r,'FP' if actual==0 else 'TP')))] for r in comparison.itertuples() for actual in [0,1]],
          [4700,2150,2150], 'Actual 0: TN, FP. Actual 1: FN, TP. Same 891 validation rows, 170 positives and 721 negatives. These are saved original counts, not final evaluation of alternative models.')

    anchor=find('Limitations')
    section(anchor,'Conclusions From the Supplementary Revision',[
        'The added evidence supports internal consistency and a cautious model comparison. Numeric parsing finds no failed conversion and development successor labels agree where checkable. It does not authenticate the 500 generated identifiers. The forest remains the original AP-based selection; its small validation advantage is uncertain under paired whole-identifier resampling.',
        'Dependence and sensitivity checks qualify the association findings. The latest-record sample changes the population and weakens multiple-testing evidence; sparse categories and unknown generation rules remain material limitations. Validation subgroup errors and differing importance measures show where the fitted model is unreliable, not where actual cables need repair.',
        'The revised website communicates these distinctions and exposes aggregate supporting reports without changing the published data release. Deployment and software test counts are not measures of scientific validity. The existing final result is retained with its actual authorization history; instructor treatment of the November 2 sequence remains pending consultation.'
    ])
    # Source limitations and acceptance must not be hidden behind outdated pending labels.
    for p in doc.paragraphs:
        if '\t' in p.text:continue
        text=p.text.replace('instructor approval and actual contribution/correction records remain','instructor acceptance of the final-evaluation sequence and actual member sign-off remain')
        text=text.replace('obtaining required approval of the data choice','maintaining the accepted synthetic-data qualification and obtaining any required approval for evaluation changes')
        if text!=p.text:set_text(p,text)

    # Replace blank records with actual assisted change evidence and unsigned member review assignments.
    correction_heading=find('Appendix C. Correction Record Template');set_text(correction_heading,'Appendix C. Implemented Correction Record')
    p=next(p for p in doc.paragraphs if p.text.startswith('No instructor correction record'))
    set_text(p,'The November 5 revision implements the following assisted changes. The electronic compliance matrix retains all 320 instructor item numbers, action, location, evidence, and unresolved conditions. Implementation is not group sign-off or instructor approval.')
    replacement=[['2026-11-05',action,'Assisted implementation; group review pending',evidence] for action,evidence in [
        ('Clarify accepted synthetic scope','Cover, abstract and Chapters I-VI'),('Validate parsing, keys and labels','src/data_validation.py; safeguard tests'),('Reconcile records and timing','record_reconciliation.csv; forward-label audit'),('Expand statistics and error reporting','Holm, cable sensitivity, bootstrap and subgroup CSVs'),('Protect frozen evidence and reproduce development','clean_copy_reproduction.json'),('Align website and SQL verification','Revision evidence panel and SELECT-only SQL'),('Map instructor corrections','320-item compliance_matrix.csv')]]
    old=next(t for t in doc.tables if t.rows[0].cells[0].text=='Date' and len(t.columns)==4 and 'Correction' in t.rows[0].cells[1].text)
    old._tbl.getparent().replace(old._tbl,table_node(['Date','Implemented action','Review status','Evidence'],replacement,[1300,2800,2300,2600]))
    p=find('Appendix D. Group Contribution Record Template');set_text(p,'Appendix D. Member Review and Contribution Confirmation')
    p=next(p for p in doc.paragraphs if p.text.startswith('No authoritative contribution log'))
    set_text(p,'The assignments below are proposed verification responsibilities, not a claim that each member authored these assisted revisions. Members must record their actual work date, evidence and reviewer confirmation in member_review_record.csv. No signature, completed contribution or approval is inferred from Git authorship.')
    old=next(t for t in doc.tables if t.rows[0].cells[0].text=='Date' and len(t.columns)==4 and 'Member' in t.rows[0].cells[1].text)
    old._tbl.getparent().replace(old._tbl,table_node(['Member','Proposed review','Evidence','Confirmation'],[
        ['Bayoguing Jose Vincent III','Feedback coordination and consultation','Compliance matrix and access record','Pending member verification'],
        ['Cruz Aurum Fuego','Website explanations and presentation','Website revision panel and tests','Pending member verification'],
        ['Sapio John Rey','Python safeguards and result interpretation','Revision reports and safeguard tests','Pending member verification']],[2200,2500,2500,1800]))
    # Remove obsolete notes immediately after those two replaced tables.
    for p in list(doc.paragraphs):
        if p.text.startswith('Note. Blank template; these cells'):
            set_text(p,'Note. Actual assisted changes and proposed review assignments are distinguished. Member confirmation and instructor decisions remain unfilled until obtained.')

    anchor=find('Documentation Assistance')
    section(anchor,'Appendix I. Instructor Revision Evidence and Reproduction',[
        'This appendix provides supplementary statistics and a map to the electronic correction records. Its development diagnostics were added after feedback and are not substituted for the frozen primary experiment. The full 320-item compliance matrix is docs/revisions/2026-11-05/compliance_matrix.csv; it is not represented as 320 instructor-approved corrections.',
    ])
    themes=[['1-10','Provenance','Synthetic scope and simulator uncertainty'],['11-20','Access history','Actual November 2 sequence; instructor consultation'],['21-55','Dataset','Counts, annual IDs and final dictionary'],['56-75','Cleaning','Parsing, temporal agreement and tests'],['76-98','EDA','Correct population and interpretation'],['99-124','Statistics','Effects, multiplicity and dependence'],['125-145','Leakage','Train-only preparation and future-perturbation tests'],['146-166','Validation','Exact folds and limited generalization'],['167-216','Metrics and models','Fixed configurations, confusion matrices and uncertainty'],['217-240','Indicator groups','Exploratory disjoint nine/four comparison'],['241-270','Interpretation and errors','Importance and subgroup errors'],['271-300','Reproduction','Source, environment and clean-copy results'],['301-320','Presentation','Navigation, sources and genuine correction records']]
    table(anchor,'compliance','Instructor feedback themes and revised evidence',['Item range','Theme','Response'],themes,[1400,2200,5400], 'The electronic matrix has every individual item and its status. Member review, unknown source details and instructor decisions are not automatically closed.')
    assoc=csv('existing_cluster_robust_logistic_associations.csv')
    table(anchor,'clusterlogit','Existing multivariable logistic associations with identifier-clustered uncertainty',['Term','Odds ratio','95% lower','95% upper','p'],
          [[r.term.replace('_',' '),number(r.odds_ratio,6),number(r.ci_low,6),number(r.ci_high,6),pvalue(r.p_value)] for r in assoc.itertuples()],[4000,1250,1250,1250,1250], 'Saved existing development association model, not the predictive logistic classifier and not newly fitted for this appendix. Odds ratios and intervals retain six decimals to distinguish small per-unit effects from exactly 1. Wald intervals use identifier-clustered standard errors; correlated variables, model specification and synthetic construction limit causal interpretation. These coefficient p-values are not part of the separate 13-test omnibus Holm family.')
    one=csv('cable_level_numeric.csv')
    table(anchor,'cablesensitivity','Latest eligible record per identifier numeric sensitivity',['Variable','Median 0','Median 1','Rank effect','Holm p'],
          [[r.variable.replace('_',' '),number(r.median_no_fault,2),number(r.median_fault,2),number(r.rank_biserial_fault_higher,3),pvalue(r.p_value_holm_13_tests)] for r in one.itertuples()],[3000,1500,1500,1500,1500], '463 identifier records: 382 negatives and 81 positives. Latest eligible development year is selected without the outcome. Changed population and weighting prevent treating the result as an independent replication of pooled cable-year tests.')
    fields=csv('added_audit_dictionary.csv')
    table(anchor,'auditdictionary','Added cleaning fields and their non-predictive roles',['Field','Meaning'],[[r.variable,r.meaning] for r in fields.itertuples()],[3200,5800], 'The original and final source-field dictionary CSV covers all 21 original fields, with units, roles, missingness and timing. These four added fields support lineage only and are not primary predictors.')
    section(anchor,'Reproduction Commands and Evidence Limits',[
        'Run scripts/review_research.py with a new --output-root below outputs/revisions to rebuild audit and reporting evidence without loading an estimator. Add --model-diagnostics only for the frozen validation-only bootstrap/permutation procedure. It checks model/runtime compatibility and refuses an existing destination. Do not run the final-evaluation script.',
        'Run scripts/check_reproduction.py to execute the fixed development workflow in a fresh temporary working copy. It fits temporary candidates, compares saved validation/CV/split evidence, and verifies original fingerprints. requirements-research-frozen.txt records the compatible environment. The execution guide distinguishes this from independent reproduction or a fresh dependency installation.',
        'Start the website and its existing inference service using Appendix H. Revision CSV downloads and an explanatory static summary are prepared locally with scripts/publish_revision_assets.py. The existing seven-table Supabase schema requires no migration. Optional 003_verify_revision_evidence.sql uses public-role SELECT queries in a read-only transaction and checks the original release only. No administrator key belongs in the frontend or the paper.',
        'The group must verify the A4/justified institutional-template exception, confirm individual contribution evidence, and consult the instructor about the earlier final evaluation. These are human decisions, not missing statistical values that software can fill. The exact publisher version and generation rule remain source limitations, and the code does not fabricate replacements.'
    ])

    # Add primary method references while retaining all original reference components.
    ref_start=find('REFERENCES');ref_end=find('APPENDICES')
    reference_template=next(p for p in original if p.text.startswith('Breiman, L.'))
    refs=[
        ('SciPy. (n.d.-a). ','chi2_contingency.',' https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2_contingency.html'),
        ('SciPy. (n.d.-b). ','mannwhitneyu.',' https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html'),
        ('scikit-learn developers. (n.d.). ','Permutation feature importance.',' https://scikit-learn.org/stable/modules/permutation_importance.html'),
        ('statsmodels. (n.d.). ','statsmodels.stats.multitest.multipletests.',' https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html')]
    existing=[];active=False
    for p in list(doc.paragraphs):
        if p._p is ref_start._p:active=True;continue
        if p._p is ref_end._p:break
        if active and p.text.strip():
            p.paragraph_format.page_break_before=False
            existing.append(p)
        elif active and p._p.find('.//'+qn('w:sectPr')) is None:
            p._p.getparent().remove(p._p)
    for lead,title,tail in refs:
        p=Paragraph(deepcopy(reference_template._p),doc._body);p.clear();p.add_run(lead);p.add_run(title).italic=True;p.add_run(tail);existing.append(p)
    for p in sorted(existing,key=lambda p:p.text.casefold()):ref_end._p.addprevious(p._p)
    ref_end.paragraph_format.page_break_before=True

    for p in doc.paragraphs:
        if re.match(r'^Table \d+\nCorrection record template$',p.text):
            set_text(p,p.text.replace('Correction record template','Implemented correction record'))
        if re.match(r'^Table \d+\nGroup contribution record template$',p.text):
            set_text(p,p.text.replace('Group contribution record template','Proposed member review responsibilities'))

    # Number captions sequentially and update both old references and new tokens.
    captions=[p for p in doc.paragraphs if re.match(r'^Table (\d+|pending)\n',p.text)]
    old_to_new={};new_numbers={}
    for i,p in enumerate(captions,1):
        match=re.match(r'^Table (\d+)\n',p.text)
        if match:old_to_new[int(match[1])]=i
        for key,value in new_captions.items():
            if p._p is value._p:new_numbers[key]=i
    caption_elements={id(p._p) for p in captions}
    reference_paragraphs=list(doc.paragraphs)+[p for t in doc.tables[:-3] for row in t.rows for cell in row.cells for p in cell.paragraphs]
    for p in reference_paragraphs:
        if '\t' in p.text or id(p._p) in caption_elements:continue
        text=re.sub(r'Tables (\d+) and (\d+)',lambda m:f'Tables {old_to_new.get(int(m[1]),m[1])} and {old_to_new.get(int(m[2]),m[2])}',p.text)
        text=re.sub(r'\bTable (\d+)\b',lambda m:f'Table {old_to_new.get(int(m[1]),m[1])}',text)
        text=re.sub(r'Table \{\{(\w+)\}\}',lambda m:f'Table {new_numbers[m[1]]}',text)
        if text!=p.text:set_text(p,text)
    for i,p in enumerate(captions,1):
        title=p.text.split('\n',1)[1];p.clear();r=p.add_run(f'Table {i}');r.bold=True;r.add_break();p.add_run(title).italic=True
        for r in p.runs:r.font.name='Times New Roman';r.font.size=Pt(12)
    navigation=rebuild_navigation(doc,original)
    assert sections==[etree.tostring(s._sectPr) for s in doc.sections]
    assert rubrics==[etree.tostring(t._tbl) for t in doc.tables[-3:]]
    BUILD.mkdir(parents=True,exist_ok=True);write_package(doc)
    manifest=dict(source=str(SOURCE),source_sha256=SOURCE_SHA,paper=str(PAPER),maps=navigation,research_tables=len(captions),table_number_mapping=old_to_new,new_tables=new_numbers,
                  original_evidence_unchanged=summary['protected_evidence_unchanged'],original_model_refitted=False,final_inference_repeated=False,source_sections=sections_to_json(doc),rubrics_sha256=[hashlib.sha256(x).hexdigest() for x in rubrics])
    (BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Revised paper built; {len(captions)} sequential research tables; preserved source geometry, images and rubrics.')


def sections_to_json(doc):return [etree.tostring(s._sectPr).decode() for s in doc.sections]


def rebuild_navigation(doc,original):
    start=next(p for p in doc.paragraphs if p.text=='TABLE OF CONTENTS' and p.style.name=='Heading 1')
    end=next(p for p in doc.paragraphs if p.text.startswith('CHAPTER I:') and p.style.name=='Heading 1')
    boundary=end._p.getprevious();assert boundary.find('.//'+qn('w:sectPr')) is not None
    front=deepcopy(start._p)
    plain=next(p for p in original if p.text.startswith('APPROVAL AND EVALUATION PAGE\t'))
    chapter=next(p for p in original if p.text.startswith('CHAPTER I:') and '\t' in p.text)
    sub=next(p for p in original if p.text.startswith('Background of the Project\t'))
    caption_entry=next(p for p in original if p.text.startswith('1.    ') and '\t' in p.text)
    cursor=start._p
    while cursor is not boundary:
        nxt=cursor.getnext();cursor.getparent().remove(cursor);cursor=nxt
    maps=[]
    def heading(label,new_page=False):
        p=Paragraph(deepcopy(front),doc._body);set_text(p,label)
        if new_page:p.paragraph_format.page_break_before=True
        boundary.addprevious(p._p)
    def entry(label,template,kind='heading',wanted=None):
        p=Paragraph(deepcopy(template._p),doc._body)
        for r in p.runs:r.text=''
        while len(p.runs)<3:p.add_run()
        p.runs[0].text,p.runs[1].text,p.runs[-1].text=label,'\t','0'
        p.paragraph_format.keep_with_next=False;boundary.addprevious(p._p)
        maps.append(dict(label=label,kind=kind,wanted=wanted or label))
    heading('TABLE OF CONTENTS')
    for label in ['APPROVAL AND EVALUATION PAGE','ABSTRACT','TABLE OF CONTENTS','LIST OF TABLES','LIST OF FIGURES']:entry(label,plain,'front')
    active=False
    for p in list(doc.paragraphs):
        if p._p is end._p:active=True
        if active and p.style.name in ('Heading 1','Heading 2') and p.text:entry(p.text,chapter if p.style.name=='Heading 1' else sub)
    for label,kind in [('LIST OF TABLES','Table'),('LIST OF FIGURES','Figure')]:
        heading(label,True)
        for p in list(doc.paragraphs):
            match=re.match(r'^'+kind+r' (\d+)\n(.+)$',p.text)
            if match:entry(f'{match[1]}.    {match[2]}',caption_entry,'caption',p.text)
    return maps


def outline_map(reader):
    result={}
    def visit(nodes):
        for node in nodes:
            if isinstance(node,list):visit(node)
            else:result[str(node.title)]=reader.get_destination_page_number(node)
    visit(reader.outline);return result


def roman(n):
    value=''
    for unit,label in [(1000,'m'),(900,'cm'),(500,'d'),(400,'cd'),(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')]:
        while n>=unit:value+=label;n-=unit
    return value


def paginate(path):
    manifest=json.loads((BUILD/'manifest.json').read_text());reader=PdfReader(path);outline=outline_map(reader)
    first=outline['CHAPTER I: INTRODUCTION AND PROBLEM DEFINITION'];texts=[re.sub(r'\W','',p.extract_text()).casefold() for p in reader.pages]
    doc=Document(PAPER);active=False;index=0;changed=0;values=[]
    for p in doc.paragraphs:
        if p.text=='TABLE OF CONTENTS' and p.style.name=='Heading 1':active=True
        if p.text.startswith('CHAPTER I:') and p.style.name=='Heading 1':break
        if not active or '\t' not in p.text:continue
        item=manifest['maps'][index];index+=1
        if item['kind'] in ['heading','front']:
            physical=outline[item['wanted']];value=roman(physical+1) if item['kind']=='front' else str(physical-first+1)
        else:
            wanted=re.sub(r'\W','',item['wanted']).casefold();physical=next(i for i in range(first,len(texts)) if wanted in texts[i]);value=str(physical-first+1)
        changed+=p.runs[-1].text!=value;p.runs[-1].text=value;values.append(dict(**item,physical_page=physical+1,value=value))
    assert index==len(manifest['maps'])
    if changed:write_package(doc)
    manifest.update(navigation=values,physical_pages=len(reader.pages),body_start=first+1)
    (BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Navigation entries {index}; changed {changed}; pages {len(reader.pages)}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['build','paginate']);parser.add_argument('--pdf',type=Path)
    args=parser.parse_args();build() if args.action=='build' else paginate(args.pdf)
