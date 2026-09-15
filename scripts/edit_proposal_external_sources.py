"""Apply proposal-stage corrections for the source-backed external-data plan.

The original DOCX is preserved. This deterministic OOXML edit uses only the
Python standard library because the document runtime is unavailable in the
current environment.
"""

from copy import deepcopy
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Undersea_Cable_Fault_Risk_Project_Proposal_REVISED (1).docx"
OUTPUT = ROOT / "Undersea_Cable_Fault_Risk_Project_Proposal_REVISED_WITH_EXTERNAL_DATA.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("w", W)


def text_of(paragraph):
    return "".join(node.text or "" for node in paragraph.findall(".//{%s}t" % W))


def set_text(paragraph, text):
    ppr = paragraph.find("{%s}pPr" % W)
    for child in list(paragraph):
        if child is not ppr:
            paragraph.remove(child)
    run = ET.SubElement(paragraph, "{%s}r" % W)
    t = ET.SubElement(run, "{%s}t" % W)
    if text[:1].isspace() or text[-1:].isspace():
        t.set("{%s}space" % XML, "preserve")
    t.text = text


def direct_paragraphs(body):
    return [child for child in list(body) if child.tag == "{%s}p" % W]


def replace_contains(body, needle, replacement):
    for paragraph in direct_paragraphs(body):
        if needle in text_of(paragraph):
            set_text(paragraph, replacement)
            return
    raise KeyError(f"Paragraph containing {needle!r} was not found")


def insert_before(body, needle, text, style_source):
    children = list(body)
    for index, child in enumerate(children):
        if child.tag == "{%s}p" % W and needle in text_of(child):
            paragraph = deepcopy(style_source)
            set_text(paragraph, text)
            body.insert(index, paragraph)
            return
    raise KeyError(f"Insertion point containing {needle!r} was not found")


def main():
    with zipfile.ZipFile(SOURCE, "r") as source_zip:
        document = ET.fromstring(source_zip.read("word/document.xml"))
        body = document.find("{%s}body" % W)
        paragraphs = direct_paragraphs(body)
        body_style = next(p for p in paragraphs if text_of(p).startswith("The proposed study addresses"))
        reference_style = next(p for p in paragraphs if text_of(p).startswith("Breiman,"))

        replace_contains(body, "Submarine fiber-optic cables form", "Submarine fiber-optic cables form a physical layer of international digital connectivity by linking landing stations and carrying traffic between countries and regions. The International Telecommunication Union (ITU, 2025b) reports that submarine cables carry approximately 99% of the world's international data traffic, while its Global Connectivity Report records that about 86% of cable faults result from human activities such as fishing and anchoring (ITU, 2025a). These figures are sector-level context from published references, not observations in the project's cable-year panel. Cable resilience also depends on physical protection, route diversity, restoration arrangements, and the ability to repair faults when they occur (Carter et al., 2009; Malecki, 2002; Starosielski, 2015).")
        replace_contains(body, "The proposed study addresses that concern", "The proposed study addresses that concern as a data-science problem rather than as an engineering-diagnosis problem. The supplied cable-year data include route and operator categories, cable age and length, fiber pairs, landing-country count, capacity, utilization, burial protection, route redundancy, vulnerability, and current-year fault information. These variables support descriptive analysis, statistical association testing, and forward classification. To add credible sector context without fabricating observations, the proposal also defines a separate source-backed evidence layer containing published indicators and selected documented incidents. Those files will be summarized descriptively and will not be joined to the model panel or used as predictors. Because the next-year fault class is imbalanced, the study will not judge models by accuracy alone; precision, recall, F1-score, ROC-AUC, and precision-recall AUC will be used to evaluate how well the minority fault class is identified (He & Garcia, 2009; Saito & Rehmsmeier, 2015).")
        replace_contains(body, "The working dataset", "The working dataset, Undersea Cables and Global Digital Infrastructure, contains 4,821 cable-year observations, 500 synthetic cable identifiers, and 21 variables covering observation years 2015-2026. Kaggle metadata verifies that these records are procedurally generated synthetic data, not authenticated measurements of real cable systems. The proposal therefore treats the panel as a clearly labeled educational study subject to explicit instructor approval and will create no new synthetic records. Real-world context and incidents will remain separately sourced, cited, and non-joinable unless a valid cable-name or geometry crosswalk is later approved. The forward target, fault_next_year, indicates whether a fault is observed in the following cable-year. The study will define prediction at the end of year t and will use only information available by that time to predict the outcome in year t+1.")
        replace_contains(body, "Files supplied:", "Files supplied for the modeling panel: undersea_cables_master.csv, cables_reference.csv, and data_dictionary.csv. Additional source-backed files are stored separately in data/external/context_indicators.csv and data/external/historical_incidents.csv. The external files contain published ITU, ICPC, and TeleGeography context and documented incidents; they are not fabricated, are not training rows, and are not joined to CAB#### records.")
        replace_contains(body, "Access requirements and license:", "Access requirements and license: Kaggle metadata records the modeling dataset as CC0 (Public Domain); the source record preserves the access date, hashes, and synthetic-data status. Each external reference retains its public URL, access date, scope, period, and source-use notes. External source terms will be checked before redistribution or extraction beyond the documented factual fields.")
        replace_contains(body, "Source-verification status and decision rule:", "Source-verification status and decision rule: the supplied data dictionary calls cable_id a synthetic cable system ID, and Kaggle metadata verifies that the observations themselves are synthetic. The group will state this boundary explicitly and seek written instructor approval for the educational synthetic-data branch. No synthetic external rows, synthetic incidents, or invented traffic statistics will be generated. Published real-world indicators and selected incidents will be kept in data/external/ as context only; replacing the panel with empirical row-level data remains a separate approved branch.")
        replace_contains(body, "The group will preserve the original Kaggle archive", "The group will preserve the original Kaggle archive and the three supplied CSV files in the immutable UnderseaCableRisk raw-data directory. Source-backed contextual indicators and documented incidents will be stored in a dedicated data/external/ directory, with one CSV per evidence type and a companion source record in docs/source_record/external_reference_sources.md. The runner will inventory and hash both external files but will not join them to the synthetic CAB#### panel. Python and pandas will import the files, and no manual spreadsheet edits or generated replacement rows will be used.")
        replace_contains(body, "Cleaning will preserve the raw dataset", "Cleaning will preserve the raw dataset and create a separate analytical copy by code. The group will validate column names, data types, allowed binary values, year ranges, duplicate cable-year rows, impossible numeric values, and missingness. The 500 rows with missing fault_next_year will be retained as unlabeled final observations but excluded from supervised model training and evaluation. External context and incident files will receive schema, duplicate-ID, required-source-URL, scope, and missingness checks but will remain outside the modeling table. cable_id will be used only as an identifier/grouping field and will not be treated as a numeric predictor. After confirming the data-dictionary meaning, blank chokepoint values will be recoded to an explicit None category rather than silently imputed.")
        replace_contains(body, "Exploratory analysis will report", "Exploratory analysis will report the number of cable-year observations and unique cables by year, route, operator category, and fault status; the positive-class prevalence; and missingness by variable. It will also provide a separately labeled context summary for the published traffic-share, fault-cause, design-life, capacity-growth, and incident indicators in data/external/. These real-world values will not be merged into synthetic panel distributions. Numeric predictors will be summarized with count, mean, median, standard deviation, interquartile range, minimum, and maximum as appropriate. Planned visualizations include histograms or density plots for age, length, capacity, utilization, redundancy, and vulnerability; bar charts for route, operator type, chokepoint, burial protection, and fault classes; annual fault-rate and capacity trends within the panel; and selected correlation or association displays.")
        replace_contains(body, "No synthetic oversampling is planned", "No synthetic oversampling is planned for the primary analysis; class weighting is preferred so that the original observation counts remain intact. More broadly, no synthetic records, incidents, traffic statistics, or external covariates will be generated. Any missing external value will remain missing or be explicitly documented rather than invented.")
        replace_contains(body, "The supplied dataset contains no names", "The supplied dataset contains no names, private addresses, government identifiers, financial credentials, medical information, or other direct personal records. The primary ethical risks are source authenticity, licensing, model misuse, and overstatement of what synthetic records represent. The separate data/external files contain only cited public facts and documented incident metadata; they will retain source URLs and access dates, and will not be used to imply row-level validation of the synthetic panel.")
        replace_contains(body, "Data coverage: the supplied master dataset", "Data coverage: the supplied master dataset contains 4,821 synthetic cable-year observations, 500 synthetic cable identifiers, 21 variables, and observation years 2015-2026 across nine broad global route categories. A separate data/external/ evidence layer contains source-backed context indicators and selected historical incidents with their original scope and reference periods.")
        replace_contains(body, "Analytical scope: source documentation", "Analytical scope: source documentation, data-quality audit, cleaning, descriptive and exploratory analysis, inferential association testing, a dummy baseline, logistic regression, decision tree, random forest, chronological validation, model comparison, interpretability analysis, a separate source-backed context/incident summary, and responsible reporting in Python.")
        replace_contains(body, "Provenance and license: the supplied files", "Provenance and license: the modeling panel is verified synthetic and cannot support real-cable estimates. The separate external files retain named public references and URLs, but their statistics and selected incidents have their own scope and limitations and are not row-level validation of the panel.")
        replace_contains(body, "Synthetic-identifier ambiguity:", "Synthetic-data boundary: the modeling records are procedurally generated and will be reported as synthetic-data analysis, not as measurements of named cables. The project will not create synthetic external records. Real-world contextual indicators and historical incidents remain in data/external/ and will be presented only with their original sources, periods, and caveats.")
        replace_contains(body, "Missing engineering context:", "Missing engineering context: neither the synthetic panel nor the separate context/incident files provide a validated cable-name/geometry crosswalk, seabed conditions, repair and maintenance logs, real-time traffic, vessel activity, weather, detailed physical inspection, or repair urgency. These remain requirements for any future empirical model.")
        replace_contains(body, "Corrected and approved project proposal", "Corrected and approval-ready project proposal, with consultation corrections and the synthetic-data decision documented.")
        replace_contains(body, "Verified dataset-source record containing", "Verified dataset-source record containing the Kaggle page, download date, exact license/permitted use, synthetic-data status, hashes, and the separate external-reference source record.")
        insert_before(body, "17. Printed Project Proposal Rubric", "Additional source-backed context and incident files in data/external/, with provenance validation and no generated observations.", body_style)
        references = [
            "International Cable Protection Committee. (2009). Damage to submarine cables caused by anchors. https://www.iscpc.org/documents/?id=139",
            "International Telecommunication Union. (2005). ITU-T Supplement 41: Design guidelines for optical fibre submarine cable systems. https://www.itu.int/rec/dologin_pub.asp?id=T-REC-G.Sup41-200505-S%21%21PDF-E&lang=e&type=items",
            "International Telecommunication Union. (2025a). Global Connectivity Report 2025: Chapter 3. https://www.itu.int/itu-d/reports/statistics/2025/11/17/gcr-2025-chapter-3/",
            "International Telecommunication Union. (2025b). Strengthening the world's digital backbone. https://www.itu.int/hub/2025/02/strengthening-the-worlds-digital-backbone/",
            "International Telecommunication Union. (2026). Submarine cable resilience. https://www.itu.int/en/mediacentre/backgrounders/Pages/submarine-cable-resilience.aspx",
            "TeleGeography. (n.d.). Written testimony on submarine cable security. https://resources.telegeography.com/hubfs/Tim%20Stronge%20Written%20Congressional%20Testimony%20%7C%20TeleGeography.pdf",
        ]
        for reference in reversed(references):
            insert_before(body, "17. Printed Project Proposal Rubric", reference, reference_style)

        with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as output_zip:
            for item in source_zip.infolist():
                payload = source_zip.read(item.filename)
                if item.filename == "word/document.xml":
                    payload = ET.tostring(document, encoding="utf-8", xml_declaration=True)
                output_zip.writestr(item, payload)
    print(OUTPUT)


if __name__ == "__main__":
    main()
