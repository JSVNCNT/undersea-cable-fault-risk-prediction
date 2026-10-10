"""Explain the research purpose in retained-format, separate manuscript copies.

No model fitting, new cable observations, dataset joins or holdout scoring.
Build, render, paginate, re-render and verify before delivery.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_research_documents as base
from scripts import revise_indicator_documents as retained

STAGES = retained.STAGES
REVIEW = ROOT / "deliverables/review/rationale_revision"
META = REVIEW / "revision_manifest.json"
NEW_HEADINGS = retained.NEW_HEADINGS
RATIONALE_HEADINGS = (
    "Why This Research Matters",
    "How the Analyses Answer the Research Problem",
    "What the Findings Mean for Cable Resilience",
    "From Research Findings to Practical Use",
)
NEW_REFERENCES = (
    "International Telecommunication Union. (2022, February 10). Restoring connectivity in Tonga through collaborative disaster response. https://www.itu.int/hub/2022/02/restoring-connectivity-tonga-internet/",
    "World Bank. (2025, July 2). Unlocking the Philippines' digital transformation by increasing internet connectivity. https://www.worldbank.org/en/results/2025/07/02/unlocking-the-philippines-digital-transformation-by-increasing-internet-connectivity",
)


def new_path(stage):
    return ROOT / f"deliverables/{stage}/Undersea_Cable_Fault_Research_{stage.upper()}_RATIONALE_REVISED.docx"


def replace_paragraph(doc, prefix, text):
    matches = [p for p in doc.paragraphs if p.text.startswith(prefix) and "\t" not in p.text]
    if len(matches) != 1:
        raise ValueError(f"Expected one prose slot for {prefix!r}; found {len(matches)}")
    p = matches[0]
    p.runs[0].text = text
    for run in p.runs[1:]:
        run.text = ""


def add_rationale(p):
    p.heading(RATIONALE_HEADINGS[0], 2)
    p.para("This research begins with a practical concern: people depend on connections they cannot see. Undersea cables connect national networks to services and information overseas. When those links are damaged, the consequences can extend beyond a slower connection to interrupted communication and difficulty reaching important online services. ITU (2025b) identifies financial transactions, cloud services and government communication among the activities supported by these cables. Studying their resilience is therefore a way of studying the reliability of an essential part of everyday digital life.")
    p.para("The problem is not only whether a cable can break, but whether a network can continue serving people after it does. ITU (2025a) explains that repairs may be delayed for weeks or months by permission requirements, customs procedures and restrictions on repair operations. A spare route may help carry traffic while repairs are arranged, but only if that route is genuinely independent and has usable capacity. This makes preparation important. A useful research question is what information could help teams recognize conditions that deserve closer review before a disruption occurs.")
    p.para("A documented example makes the consequences easier to understand. ITU (2022) describes how Tonga lost its main international cable connection after the volcanic disaster and required temporary satellite support for essential services and emergency communication. This example shows why alternative connections and coordinated recovery matter. It does not imply that the present model could have predicted that disaster: the supplied data contain neither the relevant volcanic measurements nor authenticated Tonga cable records. The case motivates the research question rather than providing a model-validation result.")
    p.para("The topic also has a clear connection to Philippine Information Technology education. The World Bank (2025) links the country's digital development to healthcare, education, financial inclusion and disaster resilience, and describes investment in the national fiber backbone and connections to schools and health facilities. Reliable international links are one part of that broader connectivity challenge. This study is not an assessment of Philippine cable performance, and submarine faults are not presented as the cause of all local internet problems. Its relevance is the need to understand and protect the connections on which digital services depend.")
    p.para("We study infrastructure and operational indicators together because they answer different parts of the same question. Infrastructure describes the system: its age, extent, protection and route setting. Operations describes the recorded conditions at the time of assessment: activated capacity, utilization and recent fault experience. Comparing them asks whether knowing both adds useful information beyond knowing only one. This is more specific than simply applying an algorithm to a table: it tests the two ideas named in the approved title and explains where the available evidence is informative or incomplete.")
    p.para("The present contribution is a transparent way to organize that investigation. It checks the records, explains the indicators, compares patterns and evaluates how often models find or miss fault-labeled observations. In a future study with verified operational records, such a workflow could support a review queue, guide questions about route alternatives and identify missing maintenance information. Those are possible uses, not benefits already demonstrated here. The current panel is publisher-declared synthetic, so its scores cannot identify real cables needing repair or prove that the research has reduced outages.")


def add_analysis_purpose(p, stage):
    p.heading(RATIONALE_HEADINGS[1], 2)
    p.para("Each analysis has a job in answering the research problem. First we ask whether the records can be trusted for this task. Next we describe what they contain, examine which indicators differ between the two outcome groups and compare methods for recognizing later fault labels. Finally we count the errors. The table below explains those purposes in ordinary language so that the figures and calculations can be read as evidence, rather than as a collection of technical outputs.")
    p.caption("Table 0. Purpose of the research analyses")
    p.table(
        ["Analysis", "Question it answers", "Why it is needed"],
        [
            ["Record and timing checks", "Are values and next-year labels usable?", "Avoid conclusions from missing or future information."],
            ["Counts and distribution graphs", "What systems and years are represented?", "Understand coverage before comparing outcomes."],
            ["Fault-label prevalence", "How uncommon is the positive outcome?", "Expose why a high accuracy score can miss faults."],
            ["Indicator associations", "Which recorded conditions differ between groups?", "Identify relationships to examine, not prove causes."],
            ["Infrastructure/operations comparison", "Does each group add useful information?", "Test the two concepts named in the title."],
            ["Model and later-year comparisons", "Does a method work on later observations?", "Check usefulness beyond the records used to fit it."],
            ["Missed faults and false flags", "What does the method get wrong?", "Make the limits and potential review burden visible."],
        ],
        widths=[1.55, 2.10, 2.60], font_size=10,
    )
    p.para("The year-based split has a simple reason: an assessment made today should not benefit from tomorrow's information. Older records are used for learning and later records for checking. Likewise, a fault reported during the current year can be used only after that year has ended. These rules do not make the data more authentic, but they make the experiment fairer and keep it aligned with the approved next-year question.")
    p.para("The key measures also have practical meanings. Recall means the share of fault-labeled observations the model finds; precision means the share of its flags that actually have a fault label. Average precision summarizes how well fault-labeled observations are placed near the top of a ranked list as the cutoff changes. None is an estimate of repair savings. Reading them together helps distinguish a method that finds more cases from one that produces fewer unnecessary flags.")
    if stage == "prelim":
        p.para("At the Prelim stage, the record checks and descriptive figures establish the foundation. Model comparison and detailed error review are planned for later development, not presented as completed Prelim findings. The same purpose table therefore explains both the work already available and the work that will be needed to answer the remaining approved questions.")
    else:
        p.para("The development results answer these questions only within the supplied panel. They are useful for comparing the chosen methods and explaining their weaknesses, but the validation records have already been examined. The reserved final test remains locked. A final manuscript must distinguish these development findings from an independent test result and from a claim that a method works on real submarine cables.")


def add_practical_results(p):
    p.heading(RATIONALE_HEADINGS[2], 2)
    p.para("The clearest result is not that one model solves cable failure. It is that different information groups and methods make different trade-offs. Combining infrastructure and operations improves the logistic model's ranking measure in this development check, while the infrastructure-only forest has a slightly higher ranking measure than the combined forest. This answers why both groups were examined: it tests whether more information helps, instead of assuming that adding every field must improve the result.")
    p.para("The error counts show why a ranking score alone is not enough. Among the same 170 positive validation labels, the infrastructure-only forest identifies 65 and misses 105; the combined forest identifies 69 and misses 101. The two models also produce 163 and 162 false flags respectively. These are existing development counts, not newly collected incidents. They show that a method can rank slightly better yet find fewer positives at a particular cutoff. Both forests still miss many labeled cases, which rules out presenting either as a dependable stand-alone warning system.")
    p.para("For a future operator-led study, this comparison could help frame a concrete question: is a modest improvement in finding cases worth collecting the additional operational fields? Answering it would require verified measurements, the cost and consequences of errors, available review staff and an agreed decision cutoff. The current findings identify that question and demonstrate how to examine it. They do not establish a financial saving, predict a named asset's condition or show that altering utilization or protection will prevent a fault.")


def add_practical_use(p):
    p.heading(RATIONALE_HEADINGS[3], 2)
    p.para("The reason to do this research is to improve the quality of questions and evidence available before a disruption, not to claim that a model can replace cable protection or repair work. The study links the importance of reliable connectivity to a manageable investigation: define the available indicators, check their timing, compare later outcomes and show what the methods miss. Its immediate value is a reproducible research process and a clearer understanding of the limits of the supplied information.")
    p.para("The practical pathway would begin with an operator checking the original measurements behind any flag. Engineers would then consider the actual route, protection, recent incidents, alternate paths and service dependencies before deciding whether further inspection or planning is justified. A low score would not certify a cable as safe. Emergency repair and routing decisions would continue to rely on current engineering information and the responsible team's procedures. This human-review pathway is a proposed future use, not an implemented system in this project.")
    p.para("A future empirical study should show whether that pathway helps before claiming success. Useful checks would include performance on an unseen period, the proportion of real faults found, the number of unnecessary reviews, the time needed to verify a flag and whether decisions changed in a beneficial way. Repair duration and service-impact records would be needed to connect fault analysis to recovery and continuity. Until those records and checks exist, the appropriate conclusion is that the project provides a research foundation, not a proven solution to the industry's problems.")


def add_method_summary(p):
    p.para("A useful way to read the results is to follow one question at a time. The inventory asks what is represented; the pattern checks ask what differs; the comparison asks what the model can recognize; and the error review asks what a user would still miss. If a method performs poorly, that is evidence about the limits of the available information, not a reason to hide the result. If it performs well, the next question is whether the advantage remains on data the researchers have not already used to make choices.")
    p.para("This sequence also explains why the paper keeps engineering questions separate from the present classification task. A positive label does not tell us how long a connection was lost, how many people were affected or whether repairs were delayed. Those questions require different outcomes and additional records. The current analysis should first establish what it can measure reliably. A later study can then add verified service and repair information to ask whether screening improves preparation or recovery, using a design agreed before examining the new results rather than retrofitting a success claim.")


FIGURE_PURPOSES = {
    "Reproducible project workflow": "Why this figure is included: it shows how the research question leads to record checks, analysis and evaluation. It helps the reader trace a conclusion back to its supporting work; it is not a live cable-monitoring architecture.",
    "Annual cable-year records": "Why this figure is included: it shows how many observations are available in each year. Uneven coverage can change a comparison, so counts must be understood before interpreting apparent changes in fault-label frequency.",
    "Annual next-year fault prevalence": "Why this figure is included: it shows how common the positive label is across observation years. This helps explain changing evaluation difficulty; it does not report actual worldwide fault rates or prove that real cables became safer or less safe.",
    "Route-redundancy distribution": "Why this figure is included: it describes the supplied count of cables sharing a route-year. It raises questions about alternatives, but a count alone cannot establish that paths are independent or can carry traffic after a failure.",
}


def add_figure_explanations(paper):
    doc = paper.doc
    for paragraph in list(doc.paragraphs):
        match = re.match(r"^Figure\s+\d+\.\s*(.*)$", paragraph.text)
        if not match or match.group(1) not in FIGURE_PURPOSES:
            continue
        next_element = paragraph._p.getnext()
        if next_element is None or next_element.tag != qn("w:p"):
            raise ValueError("Expected prose after figure caption")
        retained.insert_block(paper, Paragraph(next_element, paragraph._parent),
                              lambda p, t=FIGURE_PURPOSES[match.group(1)]: p.para(t))


def add_references(paper, stage, baseline_references):
    doc = paper.doc
    if stage in ("master", "final"):
        last_reference = next(p for p in doc.paragraphs if p.text.startswith("United Nations. (n.d.)"))
        # Insert in author/date order without reconstructing the existing list.
        first_itu_2005 = next(p for p in doc.paragraphs if p.text.startswith("International Telecommunication Union. (2005)"))
        retained.insert_block(paper, first_itu_2005,
                              lambda p: p.para(NEW_REFERENCES[0], indent=False))
        following = Paragraph(last_reference._p.getnext(), last_reference._parent)
        retained.insert_block(paper, following, lambda p: p.para(NEW_REFERENCES[1], indent=False))
        # Move the Tonga entry after the 2005 entry, retaining its paragraph style.
        tonga = next(p for p in doc.paragraphs if p.text == NEW_REFERENCES[0])
        first_itu_2005._p.addnext(tonga._p)
        return
    anchor = retained.find_paragraph(doc, "APPENDICES")
    previous = anchor._p.getprevious()
    if previous is not None and previous.tag == qn("w:p") and previous.findall(".//" + qn("w:br")):
        anchor = Paragraph(previous, anchor._parent)
    def writer(p):
        p.page_break()
        p.heading("REFERENCES", 1)
        for text in sorted([*baseline_references, *NEW_REFERENCES], key=str.casefold):
            p.para(text, indent=False)
    retained.insert_block(paper, anchor, writer)
    retained.add_toc_entry(doc, "GROUP CONTRIBUTION RECORD" if stage == "prelim" else "PRELIM AND MIDTERM CORRECTION RECORDS", "REFERENCES")


def build():
    REVIEW.mkdir(parents=True, exist_ok=True)
    metadata = {}
    reference_doc = Document(retained.new_path("master"))
    start = next(i for i, p in enumerate(reference_doc.paragraphs) if p.text == "REFERENCES")
    end = next(i for i, p in enumerate(reference_doc.paragraphs) if i > start and p.text == "APPENDICES")
    baseline_references = [p.text for p in reference_doc.paragraphs[start + 1:end] if p.text]
    reference_format = deepcopy(reference_doc.paragraphs[start + 1]._p.pPr)
    for stage in STAGES:
        source = retained.new_path(stage)
        doc = Document(source)
        paper = base.Paper.__new__(base.Paper)
        paper.doc = doc
        paper.chapter_number = None
        paper.section_number = paper.subsection_number = 0
        paper.status = stage.upper()
        replace_paragraph(doc, "The project examines this infrastructure-resilience problem", "This project asks a straightforward question: can information about a cable system and its recorded operating conditions help distinguish observations with a fault label in the next year? We study the question to understand whether the available indicators offer useful information for review, and where they fall short. The experiment compares methods under the same rules and reports their mistakes. It is a research exercise, not an engineering diagnosis or an operational warning service.")
        replace_paragraph(doc, "The working data represent repeated cable-year observations", "The real-world concern is how to prepare for cable damage and maintain dependable connections. The research problem is narrower: determine whether the available infrastructure and operational fields help distinguish next-year fault labels, and whether their predictions are useful enough to justify further study. The supplied cable identifiers are synthetic, not verified real assets. We therefore examine patterns within this panel while checking record quality, keeping years in order and making the limits of the evidence clear.")
        replace_paragraph(doc, "The academic contribution is a reproducible example", "The study matters because reliable connectivity requires more than knowing that cables are important. It requires organized information about systems, their operating conditions and the weaknesses of any proposed screening method. This project provides a repeatable way to examine those questions and makes missed cases visible alongside successful predictions. Its present contribution is academic and methodological; it does not certify a real cable, estimate a verified worldwide failure rate or replace engineering inspection.")
        replace_paragraph(doc, "The methodological value is the connection", "The analysis follows a simple evidence chain. We check where the records came from, define what each field means, use only information available before the predicted outcome and compare predictions with later labels. Because most labels are negative, we also check whether a model actually finds the less common positive cases. These steps explain why the research needs a complete workflow rather than only a high accuracy score or an attractive graph.")
        retained.insert_block(paper, retained.find_paragraph(doc, "Statement of the Problem"), add_rationale)
        retained.insert_block(paper, retained.find_paragraph(doc, "Feature Preparation and Modeling"), lambda p: add_analysis_purpose(p, stage))
        # Accessible chapter synthesis, retained at the methodology boundary.
        method_end = "DATA DICTIONARY" if stage == "prelim" else "CHAPTER IV: IMPLEMENTATION AND ANALYTICAL DEVELOPMENT"
        method_anchor = retained.find_paragraph(doc, method_end)
        if stage == "prelim":
            prev = method_anchor._p.getprevious()
            if prev is not None and prev.tag == qn("w:p") and prev.findall(".//" + qn("w:br")):
                method_anchor = Paragraph(prev, method_anchor._parent)
        retained.insert_block(paper, method_anchor, add_method_summary)
        if stage in ("master", "final"):
            retained.insert_block(paper, retained.find_paragraph(doc, "Source-Backed Context Indicators"), add_practical_results)
            retained.insert_block(paper, retained.find_paragraph(doc, "Responsible-Use Statement"), add_practical_use)
            retained.insert_block(paper, retained.find_paragraph(doc, "CHAPTER VI: CONCLUSIONS, LIMITATIONS, AND RECOMMENDATIONS"), lambda p: p.para("The practical reading is therefore cautious: the study helps explain which recorded information is useful and where predictions remain weak. It does not show that a cable can be protected by acting on a model score. Moving from a comparison to a useful service would require real outcomes, independent checks and evidence that human review of the flags improves a clearly defined decision."))
            ref_anchor = retained.find_paragraph(doc, "REFERENCES")
            prev = ref_anchor._p.getprevious()
            if prev is not None and prev.tag == qn("w:p") and prev.findall(".//" + qn("w:br")):
                ref_anchor = Paragraph(prev, ref_anchor._parent)
            retained.insert_block(paper, ref_anchor, lambda p: p.para("In short, this research exists because dependable digital services depend on infrastructure that can be damaged and can be difficult to restore. Its contribution is to make the evidence and the unanswered questions clearer. Better information could support better preparation, but that benefit must be tested with the people responsible for real systems. The paper therefore ends with a practical research pathway and measured limits, not a promise of automatic fault prevention."))
        elif stage == "midterm":
            retained.insert_block(paper, retained.find_paragraph(doc, "Initial Error Analysis and Interpretation"), add_practical_results)
        if stage != "prelim":
            replace_paragraph(doc, "Finally, the implementation maintains a separation", "The tables and figures come from saved analysis outputs. Formatting and page numbering do not change the calculations. We can therefore improve explanations and chapter layout while preserving the checked counts, model results and evidence record.")
        add_figure_explanations(paper)
        add_references(paper, stage, baseline_references)
        for paragraph in doc.paragraphs:
            if paragraph.text in [*baseline_references, *NEW_REFERENCES]:
                # Clone the retained hanging-indent reference role, rather
                # than leave new entries with normal justified-body settings.
                if paragraph._p.pPr is not None:
                    paragraph._p.remove(paragraph._p.pPr)
                paragraph._p.insert(0, deepcopy(reference_format))
        retained.add_toc_entry(doc, "Background of the Project", RATIONALE_HEADINGS[0])
        retained.add_toc_entry(doc, NEW_HEADINGS[3], RATIONALE_HEADINGS[1])
        if stage != "prelim":
            retained.add_toc_entry(doc, NEW_HEADINGS[5], RATIONALE_HEADINGS[2])
        if stage in ("master", "final"):
            retained.add_toc_entry(doc, "Recommendations", RATIONALE_HEADINGS[3])
        retained.refresh_table_list(doc)
        for paragraph in doc.paragraphs:
            if re.match(r"^Table\s+\d+\.\s*", paragraph.text):
                paragraph.paragraph_format.keep_with_next = True
            # A double-spaced empty break paragraph can itself spill to a new
            # page before issuing its break. Collapse only this nonprinting
            # spacer; all actual body prose retains the reference spacing.
            if not paragraph.text.strip() and paragraph._p.findall(".//" + qn("w:br")):
                paragraph.paragraph_format.line_spacing = Pt(1)
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.size = Pt(1)
        output = new_path(stage)
        doc.save(output)
        parts = retained.capture_preserved(source)
        assert retained.capture_preserved(output) == parts
        metadata[stage] = dict(source=str(source), output=str(output), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), preserved_parts=parts)
    META.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Created four rationale-focused copies; retained manuscripts and analytical data unchanged.")


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
        retained.META = META
        retained.new_path = new_path
        retained.paginate(args.pdf_dir)


if __name__ == "__main__":
    main()
