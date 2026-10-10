"""Revise retained formatted papers with an explicit indicator framework.

Build: python scripts/revise_indicator_documents.py build
After PDF conversion: python scripts/revise_indicator_documents.py paginate --pdf-dir PATH
The old papers, proposal copies, and instructor document are preserved.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pymupdf
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_research_documents as base
from src.indicator_analysis import indicator_registry

REVIEW = ROOT / "deliverables/review/indicator_revision"
META = REVIEW / "revision_manifest.json"
STAGES = ("master", "final", "midterm", "prelim")
NEW_HEADINGS = {
    1: "Infrastructure and Operational Indicators in the Research Title",
    3: "Indicator Groups and Comparative Analysis",
    4: "Implementation of Indicator-Group Analysis",
    5: "Infrastructure and Operational Indicator Results",
}


def norm(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def new_path(stage):
    return ROOT / f"deliverables/{stage}/Undersea_Cable_Fault_Research_{stage.upper()}_INDICATOR_REVISED.docx"


def find_paragraph(doc, text):
    matches = [p for p in doc.paragraphs if norm(p.text) == norm(text) and "\t" not in p.text]
    if len(matches) != 1:
        raise ValueError(f"Expected one paragraph: {text}; found {len(matches)}")
    return matches[0]


def insert_block(paper, anchor, writer):
    before = set(paper.doc._element.body)
    writer(paper)
    created = [el for el in paper.doc._element.body if el not in before]
    for element in created:
        if element.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            paragraph = Paragraph(element, anchor._parent)
            if paragraph.style.name.startswith("Heading "):
                # Retained styles include theme-font hints; explicitly match the
                # reference's run font so Word/LibreOffice cannot choose Calibri.
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
        anchor._p.addprevious(element)


def lead(paper, label, text):
    p = paper.para("")
    p.add_run(label + " ").bold = True
    p.add_run(text)


def add_title_framework(paper):
    paper.heading(NEW_HEADINGS[1], 2)
    lead(paper, "Infrastructure indicators.", "The title refers first to the physical and geographic setting of a cable system: its route region, chokepoint category, age, fiber pairs, length, landing-country count, design capacity, burial or armor flag, and number of cables sharing its route-year. These nine fields describe configuration, lifecycle position, protection, or network multiplicity. They give the classification model information about the system represented by a record.")
    lead(paper, "Operational indicators.", "The second part of the title refers to conditions and context at the prediction cutoff: operator category, activated or lit capacity, utilization percentage, and whether a fault occurred during the observation year. These four fields describe organizational context, capacity placed into service, a supplied load measure, and fault experience. They are available for the next-year task only when the current observation year has ended.")
    paper.para("The distinction follows a variable's meaning rather than how often it changes. Cable age and route cable count may change annually while retaining an infrastructure role. Lit capacity depends on installed equipment as well as activation decisions, so the study assigns it to the operational group for a clear comparison while acknowledging the overlap. Operator type is an organizational category; it is not a direct observation of maintenance quality or repair speed.")
    paper.para("The title's predictive question can therefore be stated concretely: do the infrastructure fields, the operational fields, or their combination distinguish cable-year records with a following-year fault label? A model can use such indicators for ranking without showing that any one factor physically causes a break. The group comparison is a supplementary analysis of the existing approved predictors and does not replace the approved research questions or the primary candidate-model comparison.")
    paper.para("A reader should also distinguish the two indicators called capacity. Design capacity is the supplied transmission potential; lit capacity is capacity activated for service. Neither is the amount of traffic measured on a specific cable. Likewise, the route-redundancy field counts cables sharing a route-year; it does not establish independent paths or capacity available for rerouting. These definitions prevent the title from promising measurements that the data do not contain.")
    paper.para("The indicators also describe different parts of a prospective review. A long, older cable with a reported protection flag has a different recorded configuration from a short, newer cable without that flag. An activated-capacity value, utilization percentage, and current-year fault status describe additional conditions at the cutoff. These examples identify how the model receives information; they do not assign an unobserved fault rate or declare either system safer. The relevant question is whether the recorded attributes distinguish following-year labels under the study's chronological evaluation.")
    paper.para("This distinction improves the practical meaning of the project for Information Technology. Infrastructure indicators organize the inventory and connection context that a network analyst would need to understand. Operational indicators organize what is active and what has happened by the time a forecast is issued. A reproducible comparison can show whether these categories provide complementary statistical information. A future operational decision would still need authenticated measurements, service dependencies, and review of the consequences of false flags and missed events.")
    paper.para("Each indicator therefore needs a defined unit, analytical role, and availability time. Physical plausibility cannot justify entering a missing or future value into the model. Explicit definitions and the group comparison connect the title to the available evidence while keeping interpretation within the dataset's limits.")


def add_method_framework(paper, stage):
    paper.heading(NEW_HEADINGS[3], 2)
    paper.para("Each primary predictor is assigned exactly once to an indicator group using its analytical meaning. The complete registry in Appendix F records the source field, group, unit, end-of-year availability, interpretation, and qualification. The registry retains the 13 approved predictors. The temporal target remains fault_next_year, and identifiers, design-life constants, duplicate redundancy flags, undocumented vulnerability indices, and cause fields remain excluded from the primary predictor list.")
    lead(paper, "Infrastructure block (nine predictors).", "ocean_route, chokepoint, age_years, fiber_pairs, length_km, n_landing_countries, design_capacity_tbps, protected_burial, and route_redundancy.")
    lead(paper, "Operational block (four predictors).", "operator_type, lit_capacity_tbps, utilization_pct, and fault_this_year. The combined block contains all 13 fields in the existing primary feature order.")
    paper.para("The comparison uses fixed logistic-regression and random-forest estimators for each block. Holding the estimator settings, observations, seed, and prediction threshold constant makes the input group the explicit difference between fits. Training uses 2015-2022 observations and validation uses 2023-2024 observations. Numeric imputation, optional scaling, and categorical encoding are fitted only to training rows. The final 2025 partition is excluded from this supplementary analysis.")
    paper.para("The main comparison measure is average precision, stored under the repository's existing pr_auc field. Average precision summarizes the precision-recall ranking; it is not numerically identical to every possible trapezoidal area calculation. Precision, recall, F1, ROC-AUC, accuracy, and confusion counts remain available so a ranking advantage can be checked against missed faults and false flags at the default threshold.")
    tense = "is specified for the later development phase" if stage == "prelim" else "is reported as supplementary development evidence"
    paper.para(f"The indicator comparison {tense}. The validation period has already been used in the primary development workflow; any additional comparisons are exploratory and are not independent final-test evidence. A difference in a point estimate does not establish statistical significance, a causal mechanism, or a universally superior indicator group. Repeated records from the same identifiers and correlations between predictors remain relevant qualifications.")
    paper.para("A fair comparison also requires the same outcome population for every block. Dropping different rows for each input group could make a model appear better simply because it was evaluated on an easier subset. The implemented block pipelines therefore retain the same temporally eligible observations and impute numeric values within the training pipeline. Category handling follows the same training-only rule, with unknown validation categories accepted without learning an encoding from the validation outcomes.")
    paper.para("Interpretation proceeds at two levels. Existing association tests describe individual fields or categories, while the block comparison evaluates the joint information available from a specified input set. A strong individual association does not guarantee a large incremental model improvement when another field carries similar information. Conversely, a field with weak standalone association can participate in a multivariable relationship. The paper keeps these questions separate and reports the block definitions alongside the estimator and metric.")
    paper.para("The analysis does not rank groups by their number of predictors or present a group score as the percentage of real failures explained. Infrastructure has nine fields and operations has four, with different types and overlaps in meaning. Removing a block changes the available feature representation; it does not experimentally remove infrastructure or operating conditions from a real system. The resulting comparison is a transparent sensitivity check of the title's categories within the existing dataset, with the original candidate selection and final-test protocol preserved.")


def add_implementation(paper):
    paper.heading(NEW_HEADINGS[4], 2)
    paper.para("The supplementary implementation is defined in src/indicator_analysis.py and reproduced by scripts/analyze_indicator_groups.py. A registry check requires the two groups to cover every approved primary predictor once with no overlap. The script applies the existing temporal-label audit and selects only eligible observations in the approved training and validation years. This yields 2,960 training rows and 891 validation rows, including 170 positive validation labels.")
    paper.para("The code fits six pipelines: two estimators for each of the infrastructure, operational, and combined blocks. Each preprocessing transformer receives only the fields requested for its block. An associated preprocessing correction distinguishes an omitted feature list from an explicitly empty list, allowing numeric-only or category-only subsets without reintroducing predictors. Tests exercise both cases and reject a comparison containing a final-holdout year.")
    paper.para("Generated registry, metric, and grouped-association files are written to outputs/tables/indicator_analysis/. The association files attach group definitions to existing statistical outputs rather than introduce new observations. Metadata records the analyzed years, row counts, and source hashes. Hash checks verify that the original CSVs, primary model-selection record, and final-test status have not changed. The comparison does not save replacement primary models or unblind the final test.")
    paper.para("This addition makes the title inspectable in the implementation: a reviewer can move from an indicator definition to its group membership, follow the training-only preprocessing, and compare the same validation outcomes under different input blocks. The registry and result table therefore provide a direct connection between the conceptual wording in Chapter I and the executable analysis.")


def add_results(paper):
    comparison = pd.read_csv(ROOT / "outputs/tables/indicator_analysis/indicator_block_validation.csv")
    paper.heading(NEW_HEADINGS[5], 2)
    paper.para("The supplementary comparison asks whether the two named indicator groups contribute ranking information within the supplied panel. All six fits use the same 2,960 training records and 891 validation records. Validation fault prevalence is 0.1908, which provides the prior-probability reference for average precision. The table reports the executed point estimates at the existing default decision threshold.")
    paper.caption("Table 0. Infrastructure and operational block comparison")
    rows = [[r.indicator_group.title(), "Logistic" if r.model == "logistic_regression" else "Random forest", str(r.predictor_count), f"{r.pr_auc:.3f}", f"{r.recall:.3f}", f"{r.f1:.3f}"] for r in comparison.itertuples()]
    paper.table(["Indicators", "Estimator", "Fields", "AP", "Recall", "F1"], rows, widths=[1.4, 1.35, 0.5, 0.65, 0.65, 0.65], font_size=9)
    paper.para("Logistic regression reaches average precision of 0.2919 with infrastructure indicators, 0.2576 with operational indicators, and 0.3105 with the combined set. The combined logistic model therefore improves the recorded ranking measure relative to either block alone. Its recall of 0.5176 is nevertheless lower than the infrastructure-only logistic recall of 0.5471, showing that ranking and default-threshold fault detection answer different questions.")
    paper.para("Random forest reaches average precision of 0.3266 with infrastructure indicators, 0.2574 with operational indicators, and 0.3171 with the combined set. Infrastructure-only forest has the highest average-precision point estimate in this supplementary check, but combined forest has higher recall and F1 than that restricted forest at the default threshold. These results do not support an automatic claim that adding every operational field improves every model or every metric.")
    paper.para("The observed behavior answers the title at the level the data allow: both infrastructure and operational blocks contain predictive information in the panel, and their combination can be useful, with the outcome depending on estimator and evaluation criterion. The smaller operational block includes operator category, activated capacity, utilization, and current-year fault status; its lower group average precision does not prove that operational telemetry is unimportant in real cable management.")
    paper.para("The original primary model selection remains the comparison among approved candidate models using all 13 predictors. The new block comparison is explanatory development work, not a replacement selection exercise after repeated validation inspection. No confidence interval or independent final-test improvement is claimed for the small difference between the two forest variants. The source's synthetic construction continues to limit generalization to physical systems.")
    paper.para("Individual-field evidence helps describe the blocks but does not explain away these differences. The existing comparisons show higher median age and length among positive-labeled observations, along with higher median utilization and lower route cable count. Those patterns concern configuration and operating conditions together. Some capacity or landing measures have weak unadjusted association, while broad route and chokepoint categories show detectable association. The block results summarize their joint predictive behavior rather than turn each association into a causal explanation.")
    paper.para("The findings are also sensitive to what each metric rewards. Average precision emphasizes ranking positives toward the top of the score distribution. Recall asks how many positives are flagged at one threshold. The combined forest has 69 true positives and 101 false negatives, compared with 65 true positives and 105 false negatives for infrastructure-only forest, despite the latter's higher average precision. This concrete difference helps explain why the indicator discussion retains both ranking and threshold evidence and why operational suitability cannot be inferred from one number alone.")
    paper.para("The indicator table supports a bounded comparison of available inputs. It does not estimate a real cable's remaining life or a verified intervention benefit.")


def add_midterm_results(paper):
    paper.heading(NEW_HEADINGS[5], 2)
    paper.para("The executed supplementary analysis compares infrastructure, operational, and combined inputs using fixed logistic-regression and random-forest pipelines on the same development split. The full result table is provided in Appendix F. Average precision for logistic regression is 0.2919, 0.2576, and 0.3105 respectively. The corresponding forest estimates are 0.3266, 0.2574, and 0.3171. Validation prevalence is 0.1908 across 891 observations.")
    paper.para("Combining the groups improves logistic-regression ranking relative to either block alone. The infrastructure-only forest has a slightly higher average-precision estimate than combined forest, while combined forest improves default-threshold recall and F1. These contrasts clarify the title's indicator categories without claiming that every added input improves performance. The comparison is exploratory because the validation data have already been examined; the final test remains locked.")


def add_appendix(paper, stage):
    paper.page_break()
    paper.heading("Appendix F. Infrastructure and Operational Indicator Guide", 2)
    paper.para("This guide records the specific meaning of the title's predictor groups. Definitions derive from the supplied data dictionary and existing pipeline, rather than new asset measurements. The panel is publisher-declared synthetic; its rows and identifiers do not authenticate real cable condition. Each field must be available when observation year t closes to be eligible for a year t+1 prediction.")
    registry = indicator_registry()
    for group in ("infrastructure", "operational"):
        paper.heading(f"{group.title()} Indicator Definitions", 3)
        paper.caption(f"Table 0. {group.title()} indicator registry")
        rows = [[r.feature.replace("_", " "), r.unit, r.interpretation] for r in registry[registry.indicator_group == group].itertuples()]
        paper.table(["Source field", "Unit", "Meaning in this study"], rows, widths=[2.05, 0.85, 3.35], font_size=9)
    paper.heading("Interpreting Infrastructure Fields", 3)
    paper.para("Route and chokepoint categories supply broad geographic context. They cannot be converted into seabed coordinates, fishing effort, or vessel proximity without a valid spatial source. Total cable length describes extent, while landing-country count describes the number of national connection contexts. Neither substitutes for a landing-station map. Fiber-pair count and design capacity describe configuration and potential throughput, without identifying a particular physical fault mechanism.")
    paper.para("Age is an elapsed-time measure and can motivate lifecycle comparisons, but it does not measure wear or prove that a cable expires at its planning life. The design-life field remains excluded because it is constant in the source. The burial/armor flag is a protection indicator rather than a measurement of burial depth or the fraction of a route protected. Route cable count is contextual multiplicity; genuine restoration depends on alternate-path independence, spare capacity, and the ability to switch traffic.")
    paper.heading("Interpreting Operational Fields", 3)
    paper.para("Operator category supplies organizational context. It should not be presented as measured competence, inspection frequency, maintenance spending, or repair readiness. Lit capacity indicates the capacity placed into service, and utilization is the supplied operating-load percentage. Their reported relationships concern the dataset variables; interpretation as actual carried traffic would require telemetry and a documented utilization denominator.")
    paper.para("Current-year fault status is eligible only under the explicit end-of-year prediction rule. During an earlier point in year t, that complete-year value would be unavailable. The variable can summarize recent fault experience but does not supply failure duration, fault cause, repair quality, or repair completion. The cause field remains excluded because its timing and conditioning could reveal information about a fault event that a prospective model should not use.")
    paper.heading("Reading the Supplementary Group Comparison", 3)
    if stage == "prelim":
        paper.para("For the Prelim phase, the registry defines a planned supplementary comparison for the later development stage. The two single-group inputs and the combined input will be evaluated on the same chronological split using fixed estimators. Group performance must be assessed with both ranking and fault-detection measures, then interpreted alongside the primary candidate comparison and source limitations. Development outcomes are retained in the Midterm, Master, and Final drafts.")
    else:
        comparison = pd.read_csv(ROOT / "outputs/tables/indicator_analysis/indicator_block_validation.csv")
        paper.caption("Table 0. Supplementary indicator comparison metrics")
        rows = [[r.indicator_group.title(), "Logistic" if r.model == "logistic_regression" else "Forest", f"{r.pr_auc:.4f}", f"{r.precision:.4f}", f"{r.recall:.4f}", f"{r.f1:.4f}"] for r in comparison.itertuples()]
        paper.table(["Block", "Model", "AP", "Precision", "Recall", "F1"], rows, widths=[1.25, 0.85, 0.7, 0.85, 0.85, 0.85], font_size=9)
        paper.para("Average precision uses the repository's pr_auc field and should be read against validation prevalence of 0.1908. Precision, recall, and F1 describe the classifier at its default threshold; they can move differently from average precision. The infrastructure-only forest ranks slightly better in this check, whereas the combined forest identifies more positives at that threshold. Point estimates do not establish a statistically reliable advantage on new data.")
    paper.para("The block assignment is a reproducible analytical convention. Capacity and redundancy involve both infrastructure and operations, so a different defensible taxonomy might change a restricted-block comparison. The combined model still uses the same original 13 fields. A future taxonomy review should be documented before evaluating a new independent period and should not be chosen solely to obtain a favorable score on reused validation outcomes.")
    paper.heading("What Authenticated Enrichment Would Add", 3)
    paper.para("Infrastructure enrichment could provide verified geometry, bathymetry, protected-route extent, burial depth, landing-station dependencies, installation history, and independent alternate paths. Operational enrichment could provide time-stamped traffic, capacity activation, maintenance actions, vessel exposure, fault and repair duration, restoration events, and service impact. Each new field needs a source owner, cable identifier or spatial key, observation timestamp, unit, and record of when it became available.")
    paper.para("A future field should be evaluated for both measurement quality and prediction timing. A repair record written after the predicted fault cannot become a pre-fault predictor. A global fishing-fault percentage cannot be assigned to an individual cable-year as though it were measured exposure. External sources already verified by the project provide domain context; empirical enrichment requires a documented crosswalk and evidence that the source covers the same systems and periods.")
    paper.para("Reproduction uses scripts/analyze_indicator_groups.py. The indicator_registry.csv file defines roles and qualifications, indicator_block_validation.csv stores the six comparisons, and indicator_analysis_metadata.json records the development scope and protected-input hashes. The script never generates new cable-year rows or scores the final holdout. The paper distinguishes observed development metrics, domain context, and the empirical measurements that a future operational study would require.")


def add_toc_entry(doc, after_label, new_label):
    candidates = [p for p in doc.paragraphs if "\t" in p.text and norm(p.text.split("\t")[0]) == norm(after_label)]
    if not candidates:
        raise ValueError(f"TOC anchor missing: {after_label}")
    anchor = candidates[0]
    element = deepcopy(anchor._p)
    anchor._p.addnext(element)
    from docx.text.paragraph import Paragraph
    p = Paragraph(element, anchor._parent)
    p.runs[0].text = new_label
    if len(p.runs) < 3:
        raise ValueError("Expected three-run dot-leader entry")
    p.runs[-1].text = "-"


def refresh_table_list(doc):
    captions = []
    for p in doc.paragraphs:
        match = re.match(r"^Table\s+\d+\.\s*(.+)$", p.text)
        if match:
            number = len(captions) + 1
            p.runs[0].text = f"Table {number}. {match.group(1)}"
            for run in p.runs[1:]:
                run.text = ""
            captions.append(p.text)
    lists = []
    within = False
    for p in doc.paragraphs:
        if p.text == "LIST OF TABLES":
            within = True
        elif p.text == "TABLE OF CONTENTS":
            break
        elif within and "\t" in p.text:
            lists.append(p)
    template = deepcopy(lists[0]._p)
    anchor = lists[-1]._p
    from docx.text.paragraph import Paragraph
    for number, caption in enumerate(captions, 1):
        element = deepcopy(template)
        anchor.addnext(element)
        anchor = element
        p = Paragraph(element, lists[0]._parent)
        p.runs[0].text = f"{number}.    {caption.split('. ', 1)[1]}"
        p.runs[-1].text = "-"
    for paragraph in lists:
        paragraph._p.getparent().remove(paragraph._p)


def capture_preserved(path):
    with ZipFile(path) as archive:
        names = [n for n in archive.namelist() if re.match(r"word/(header|footer|styles|numbering|media)", n)]
        return {name: hashlib.sha256(archive.read(name)).hexdigest() for name in names}


def build():
    REVIEW.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for stage in STAGES:
        source = ROOT / f"deliverables/{stage}/Undersea_Cable_Fault_Research_{stage.upper()}_EXPANDED_REFERENCE_FORMATTED.docx"
        if not source.exists() and stage == "prelim":
            # This retained expanded output was removed locally; reconstruct it
            # from the established generator without altering any proposal copy.
            base.build_prelim(base.load_artifacts())
        if not source.exists():
            raise FileNotFoundError(source)
        doc = Document(source)
        paper = base.Paper.__new__(base.Paper)
        paper.doc = doc
        paper.chapter_number = None
        paper.section_number = paper.subsection_number = 0
        paper.status = stage.upper()
        insert_block(paper, find_paragraph(doc, "Target Users and Beneficiaries"), add_title_framework)
        insert_block(paper, find_paragraph(doc, "CHAPTER II: REVIEW OF RELATED LITERATURE AND DATA SCIENCE STUDIES"), lambda p: p.para("The indicator registry provides the next check: a reviewer can inspect each field's definition and timing, then follow its role into the methodology and development comparison. This links the title directly to the study's evidence."))
        insert_block(paper, find_paragraph(doc, "Feature Preparation and Modeling"), lambda p: add_method_framework(p, stage))
        if stage != "prelim":
            insert_block(paper, find_paragraph(doc, "Technical Limitations"), add_implementation)
        if stage in ("master", "final"):
            insert_block(paper, find_paragraph(doc, "Source-Backed Context Indicators"), add_results)
        elif stage == "midterm":
            insert_block(paper, find_paragraph(doc, "Initial Error Analysis and Interpretation"), add_midterm_results)
        rubric_anchor = find_paragraph(doc, "OFFICIAL " + ("FINAL" if stage in ("master", "final") else stage.upper()) + " RUBRICS")
        # Insert before the existing page-break paragraph, preserving the fresh
        # rubric page without creating a double-break blank page.
        from docx.text.paragraph import Paragraph
        prior = rubric_anchor._p.getprevious()
        if prior is not None and prior.tag == qn("w:p") and prior.findall(".//" + qn("w:br")):
            rubric_anchor = Paragraph(prior, rubric_anchor._parent)
        insert_block(paper, rubric_anchor, lambda p: add_appendix(p, stage))
        add_toc_entry(doc, "Significance of the Project", NEW_HEADINGS[1])
        add_toc_entry(doc, "Exploratory and Statistical Analysis", NEW_HEADINGS[3])
        if stage != "prelim":
            add_toc_entry(doc, "Feature Preparation, Models, and Cross-Validation", NEW_HEADINGS[4])
        if stage in ("master", "final"):
            add_toc_entry(doc, "Temporal Stability and Sensitivity", NEW_HEADINGS[5])
        elif stage == "midterm":
            add_toc_entry(doc, "BASELINE, CANDIDATE MODELS, AND INITIAL COMPARISON", NEW_HEADINGS[5])
        add_toc_entry(doc, "GROUP CONTRIBUTION RECORD" if stage == "prelim" else "APPENDICES", "Appendix F. Infrastructure and Operational Indicator Guide")
        refresh_table_list(doc)
        for p in doc.paragraphs:
            if re.match(r"^Table\s+\d+\.\s*", p.text):
                p.paragraph_format.keep_with_next = True
            if p.text == "September 2026":
                p.runs[0].text = "October 2026"
            elif p.text.startswith("The research questions are therefore answered conditionally:"):
                p.runs[0].text = "The title's two indicator groups are now explicit: nine infrastructure predictors and four operational predictors. Their supplementary comparison improves logistic-regression average precision when combined, while infrastructure-only forest has a slightly higher ranking estimate than combined forest. These metric-specific results qualify rather than replace the original full-feature selection. They describe development behavior within the supplied panel; the locked final test remains necessary before a final performance conclusion."
                for run in p.runs[1:]:
                    run.text = ""
        output = new_path(stage)
        doc.save(output)
        preserved = capture_preserved(source)
        require = capture_preserved(output)
        if require != preserved:
            raise RuntimeError(f"{stage}: header/footer/style/numbering/media changed")
        metadata[stage] = dict(source=str(source), output=str(output), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), preserved_parts=preserved)
    META.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Created four indicator-focused copies; original formatted papers preserved.")


def locate(pdf, label, start):
    wanted = norm(label)
    words = r"\s+".join(re.escape(word) for word in label.split())
    pattern = re.compile(r"^\s*(?:CHAPTER\s+[IVX]+:\s*)?" + words + r"\s*$", re.M | re.I)
    for i in range(start, len(pdf)):
        if pattern.search(pdf[i].get_text()):
            return i
        for block in pdf[i].get_text("blocks"):
            text = norm(block[4])
            chapter_title = re.sub(r"^chapter\s+[ivx]+:\s*", "", text)
            if wanted == text or wanted == chapter_title:
                return i
            if any(norm(line) == wanted for line in block[4].splitlines()):
                return i
    raise ValueError(f"Rendered locator missing: {label}")


def paginate(pdf_dir):
    metadata = json.loads(META.read_text(encoding="utf-8"))
    for stage in STAGES:
        output = new_path(stage)
        pdf = pymupdf.open(pdf_dir / stage / f"{output.stem}.pdf")
        first = next(i for i, p in enumerate(pdf) if "CHAPTER I:" in p.get_text() and i > 3 and "TABLE OF CONTENTS" not in p.get_text() and "\t" not in p.get_text())
        # A TOC continuation can contain chapter labels; identify the body start
        # by its explanatory text rather than a page-count assumption.
        first = next(i for i, p in enumerate(pdf) if "CHAPTER I:" in p.get_text() and "Submarine fiber-optic cables form" in p.get_text())
        doc = Document(output)
        captions = {norm(re.sub(r"^Table\s+\d+\.\s*", "", p.text)): p.text for p in doc.paragraphs if re.match(r"^Table\s+\d+\.\s*", p.text)}
        entries = {}
        list_mode = None
        for p in doc.paragraphs:
            if p.text in ("LIST OF FIGURES", "LIST OF TABLES", "TABLE OF CONTENTS"):
                list_mode = p.text
            if "\t" not in p.text or len(p.runs) < 3:
                continue
            label = p.text.split("\t")[0].strip()
            if list_mode == "LIST OF FIGURES":
                wanted = re.sub(r"^\d+\.\s*", "", label)
                wanted = "Figure " + re.match(r"\d+", label).group() + ". " + wanted
            elif list_mode == "LIST OF TABLES":
                wanted = captions[norm(re.sub(r"^\d+\.\s*", "", label))]
            else:
                if label in ("ABSTRACT", "APPROVAL AND EVALUATION PAGE", "LIST OF FIGURES", "LIST OF TABLES", "TABLE OF CONTENTS"):
                    continue
                wanted = label.split(":", 1)[1].strip() if label.startswith("CHAPTER ") else label
            index = locate(pdf, wanted, first)
            value = index - first + 1
            p.runs[-1].text = str(value)
            entries[label] = value
        doc.save(output)
        metadata[stage].update(physical_pages=len(pdf), physical_body_start=first + 1, page_map=entries)
        print(f"{stage}: {len(pdf)} physical pages; main matter begins on {first + 1}")
    META.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "paginate"])
    parser.add_argument("--pdf-dir", type=Path)
    args = parser.parse_args()
    if args.action == "build":
        build()
    else:
        if not args.pdf_dir:
            parser.error("paginate requires --pdf-dir")
        paginate(args.pdf_dir)


if __name__ == "__main__":
    main()
