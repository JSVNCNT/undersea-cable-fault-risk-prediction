"""Create an item-level instructor response and dictionary from verified reports.

No instructor signatures, member contributions, approval dates or unknown
simulator rules are invented. Group review and consultation remain explicit.
"""
from pathlib import Path
import csv
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pypdf import PdfReader
from src import config
from src.data_loading import load_master_data

SOURCE=Path(r"C:\Users\Vincent\Downloads\Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems.pdf")
OUT=ROOT/"docs/revisions/2026-11-05"
REPORT=ROOT/"outputs/revisions/2026-11-05"

# End ID, theme, revised location, concrete evidence, implemented response.
GROUPS=[
 (10,"Provenance and contribution","Cover Abstract Chapters I II VI","docs/source_record/dataset_source_record.md; revision_protocol.json","Explicit synthetic qualification; simulator uncertainty and non-operational contribution"),
 (20,"Final access and prediction timing","Chapter III and Appendix I","outputs/final_evaluation_2026-11-02/protocol.json; final_test_access_record.md","Disclose aggregate exposure and actual user-authorized November 2 run; no repeat; instructor decision requested"),
 (55,"Dataset structure and dictionary","Chapter III and Appendix I","record_reconciliation.csv; annual_panel_coverage.csv; final_data_dictionary.csv","Reconcile populations; annual IDs; units and roles; source metadata limitations"),
 (75,"Cleaning and temporal validity","Chapters III IV and Appendix I","numeric_parsing_audit.csv; development_forward_label_audit.csv; tests/test_revision_safeguards.py","Fail-closed validation, parsing audit, successor agreement and edge-case tests"),
 (98,"Exploratory analysis","Chapters IV V","annual_panel_coverage.csv; outputs/tables/eda; identifier_coverage.csv","Distinguish EDA 3860 from supervised development 3851; per-cable-year summaries and categorical distributions"),
 (124,"Statistical evidence","Chapters III V and Appendix I","numeric_associations_holm.csv; categorical_associations_holm.csv; cable_level_numeric.csv; existing_cluster_robust_logistic_associations.csv","Hypotheses, group sizes, effects, expected counts, Holm family, clustered regression and one-record-per-ID sensitivity"),
 (145,"Preparation and leakage","Chapters III IV and Appendix I","tests/test_revision_safeguards.py; src/preprocessing.py; src/feature_engineering.py","Training-fitted preprocessing; future-perturbation, unseen-category, lag-gap and terminal tests; separate sensitivity data"),
 (166,"Chronological evaluation","Chapters III V and Appendix I","expanding_window_folds.csv; revision_summary.json; final_test_access_record.md","Exact fold years; 424 of 460 validation IDs seen in training; no unseen-asset claim; frozen forest not refitted"),
 (188,"Class imbalance and metrics","Chapters IV V","outputs/tables/model_comparison_validation.csv; validation_subgroup_errors.csv","AP terminology, all candidate confusion matrices, score versus probability, fixed decision rule and error trade-offs"),
 (216,"Models and stability","Chapters IV V and Appendix I","src/modeling.py; validation_cluster_bootstrap.csv; outputs/tables/temporal_cv_scores.csv","Fixed configurations, no invented tuning history, small paired AP difference with conditional cluster uncertainty"),
 (240,"Indicator groups","Chapters I III V and Appendix F","outputs/tables/indicator_analysis/indicator_registry.csv; indicator_block_validation.csv","Retain exhaustive disjoint nine/four registry; explain metric-specific differences and exploratory reused validation"),
 (254,"Feature interpretation","Chapter V and Appendix I","original_predictor_importance.csv; validation_permutation_importance.csv","Grouped impurity importance and validation-only permutation; correlated-feature and non-causal qualifications"),
 (270,"Error and practical interpretation","Chapters V VI and Appendix I","validation_subgroup_errors.csv; revision_summary.json","Year route operator age redundancy errors, denominators, small samples and authenticated future-data requirements"),
 (300,"Reproducibility and code","Chapter IV and Appendix I","scripts/review_research.py; scripts/check_reproduction.py; requirements-research-frozen.txt; execution_guide.md","Complete source and saved evidence; protected outputs; isolated reproduction; distinguish measured verification from claims"),
 (320,"Manuscript and compliance","All chapters and appendices","compliance_matrix.csv; change_record.md; member_review_record.csv; revised DOCX/PDF QA","Consistent terms and AP, source notes, updated navigation, retained formatting, item-level response and genuine review records")]


def write_rows(path,rows):
    with path.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def extract_items():
    text="\n".join(p.extract_text() for p in PdfReader(SOURCE).pages)
    text=text[text.index("I. CRITICAL"):]
    text=re.split(r"XV\s*\.\s*REQUIRED ACTIONS",text)[0]
    matches=list(re.finditer(r"(?m)^\s*(\d{1,3})\.\s+",text))
    result=[]
    for i,m in enumerate(matches):
        number=int(m[1])
        if number!=len(result)+1: continue
        body=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        # Keep the actual item text and explanatory context, but not a following Roman section heading.
        body=re.split(r"\n\s*[IVX]+\s*\.\s+[A-Z]",body)[0]
        result.append((number,re.sub(r"\s+"," ",body).strip()))
    if [n for n,_ in result]!=list(range(1,321)):
        raise ValueError(f"Expected 320 sequential instructor comments, found {len(result)}")
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    summary=json.loads((REPORT/"revision_summary.json").read_text())
    rows=[]
    limits={7,8,19,22,30,45,51,90}
    consultation={11,12,13,14,15,16,17,18,165,166,200,216}
    manual={271,284,285,300,318,320}
    for number,text in extract_items():
        end,theme,location,evidence,response=next(g for g in GROUPS if number<=g[0])
        status="Addressed in revision; group verification pending"
        note="Evidence is local implementation/reporting, not instructor sign-off."
        if number in limits:
            status="Source limitation documented"
            note="Exact publisher version, generation rules or causal reason cannot be established; no value or explanation invented."
        if number in consultation:
            status="Addressed with historical disclosure; consultation pending"
            note="Original test is exposed; instructor treatment of November 2 evaluation and any new design must be confirmed. Fixed settings are not a tuning history."
        if number in {160,186}:
            status="Conditional extension not adopted"
            note="No new-system claim or operational threshold claim is made. Preserve original experiment; obtain approval before a separate evaluation design."
        if number in {284,285} and (REPORT/"clean_copy_reproduction.json").exists():
            result=json.loads((REPORT/"clean_copy_reproduction.json").read_text())
            status="Clean working-copy reproduction verified" if result["returncode"]==0 and result["comparisons"] else "Reproduction requires review"
            note="Existing compatible environment, not an independently provisioned environment or instructor reproduction."
            if number==284 and result["returncode"]==0:
                status="Working-copy reproduction verified; fresh environment not verified"
        if number==271:
            status="Repository prepared; submission pending"
            note="Executable source is present locally. No commit, push or submission upload was performed, as requested."
        if number==318:
            status="Correction record populated; member verification pending"
            note="Actual assisted changes recorded. Member signatures, individual work dates and instructor decisions cannot be fabricated."
        rows.append(dict(feedback_id=number,feedback=text,theme=theme,action=response,revised_location=location,
                         supporting_artifact=evidence,status=status,group_owner="Group 5 xam.py",member_reviewer="Assignment pending group confirmation",
                         implementation_date="2026-11-05",group_review_date="",verification_note=note))
    write_rows(OUT/"compliance_matrix.csv",rows)
    import pandas as pd
    raw=load_master_data(); registry=pd.read_csv(ROOT/"outputs/tables/indicator_analysis/indicator_registry.csv",keep_default_na=False).set_index("feature")
    descriptions={r["column"]:r["description"] for r in csv.DictReader((ROOT/"UnderseaCableRisk/data_dictionary.csv").open(encoding="utf-8-sig"))}
    extra_units={"year":"calendar year","cable_id":"identifier","rfs_year":"calendar year","design_life_years":"years","is_low_redundancy":"0/1","vulnerability_index":"index 0-100","fault_cause":"category","fault_next_year":"0/1 nullable"}
    dictionary=[]
    exclusions={"year":"Partitioning only; not a primary predictor","cable_id":"Generated grouping key, not an authenticated real identity","rfs_year":"Excluded; age plus year redundancy","design_life_years":"Constant 25 in source; not discriminative","is_low_redundancy":"Verified equal to route_redundancy < 40; duplicate representation","vulnerability_index":"Undocumented composite formula; excluded","fault_cause":"Current-fault-conditioned field; excluded for timing/conditioning concerns"}
    for col in raw.columns:
        primary=col in config.PREDICTORS
        s=raw[col]
        dictionary.append(dict(variable=col,description=descriptions[col],unit=registry.loc[col,"unit"] if primary else extra_units.get(col,"category"),
            role="primary predictor" if primary else "forward target" if col==config.TARGET_COLUMN else "audit or grouping only",
            indicator_group=registry.loc[col,"indicator_group"] if primary else "not a primary input",
            missing_count=int(s.isna().sum()),observed_values=f"{s.min()} to {s.max()}" if pd_numeric(s) else " | ".join(sorted(s.astype(str).unique())),
            availability="end of observation year t" if primary else "following calendar year t+1; NEVER an input" if col==config.TARGET_COLUMN else "audit only",
            treatment=registry.loc[col,"qualification"] if primary else exclusions.get(col,"Never impute the target; require consecutive successor"),
            provenance="publisher-declared synthetic source; generation rule not independently established"))
    write_rows(REPORT/"final_data_dictionary.csv",dictionary)
    audit_fields=[dict(variable=v,meaning=m,predictor=False) for v,m in [
        ("next_observed_year","Next available row year within identifier; audit only, not necessarily t+1"),
        ("has_consecutive_next_year","Next row is calendar year t+1"),("label_temporally_valid","Populated target and consecutive successor"),
        ("exclusion_reason","Unlabeled terminal observation or populated non-consecutive predecessor; mutually exclusive by target presence")]]
    write_rows(REPORT/"added_audit_dictionary.csv",audit_fields)
    write_rows(OUT/"member_review_record.csv",[dict(member=name,review_assignment=task,actual_work_date="",evidence_to_verify=evidence,review_status="Pending member verification",signature="") for name,task,evidence in [
        ("Bayoguing Jose Vincent III","Coordinate feedback and final-test consultation","compliance_matrix.csv; final_test_access_record.md"),
        ("Cruz Aurum Fuego","Review website explanations and responsive presentation","website/src/components/revision-evidence.tsx; website tests"),
        ("Sapio John Rey","Review Python safeguards and analytical interpretation","tests/test_revision_safeguards.py; revision reports")]])
    payload=dict(items=320,source_pdf_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),feedback_source=str(SOURCE),
                 generated_date="2026-11-05",all_items_signed_off=False,reported_dataset_acceptance=True,final_test_instructor_acceptance=False,
                 statuses={s:sum(r["status"]==s for r in rows) for s in sorted({r["status"] for r in rows})})
    (OUT/"compliance_summary.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(json.dumps(payload,indent=2))


def pd_numeric(series):
    import pandas as pd
    return pd.api.types.is_numeric_dtype(series)


if __name__=="__main__":main()
