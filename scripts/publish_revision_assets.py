"""Copy selected, aggregate revision evidence to local website assets only.

No cloud request, database write, model execution, or change to the published
research release. Re-run after an approved revision report is generated.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/"outputs/revisions/2026-11-05"
PUBLIC = ROOT/"website/public/revision-evidence"


def main():
    summary = json.loads((SOURCE/"revision_summary.json").read_text())
    release = json.loads((ROOT/"website/src/release.json").read_text())
    research = json.loads((ROOT/"website/public/data/research.json").read_text())
    if not summary["protected_evidence_unchanged"] or summary["new_classifier_fit"] or summary["new_final_inference"]:
        raise ValueError("Only verified, non-replacement revision evidence may be exported")
    if summary["original_model_sha256"] != research["model_sha256"]:
        raise ValueError("Revision evidence belongs to a different frozen model")
    if release["release_id"] != research["release_id"]:
        raise ValueError("Frontend and research release identifiers differ")
    names = ["record_reconciliation.csv", "validation_subgroup_errors.csv", "validation_cluster_bootstrap.csv", "original_predictor_importance.csv", "validation_permutation_importance.csv", "annual_panel_coverage.csv", "expanding_window_folds.csv", "final_data_dictionary.csv", "added_audit_dictionary.csv", "numeric_associations_holm.csv", "categorical_associations_holm.csv"]
    PUBLIC.mkdir(parents=True,exist_ok=True)
    files = []
    for name in names:
        source = SOURCE/name
        if not source.exists():
            raise FileNotFoundError(f"Required revision evidence missing: {name}")
        shutil.copy2(source,PUBLIC/name)
        files.append(dict(name=name,href=f"/revision-evidence/{name}",sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    payload = dict(revision_date="2026-11-05", release_id=research["release_id"], model_sha256=summary["original_model_sha256"],
                   scope="Supplementary development evidence; original published release and frozen final results unchanged",
                   reconciliation=summary["record_reconciliation"], intervals=summary.get("validation_cluster_bootstrap",[]),
                   forward_checkable=summary["development_forward_checkable"],forward_disagreements=summary["development_forward_disagreements"],
                   numeric_parse_failures=summary["numeric_parse_failures"],shared_validation_ids=summary["train_validation_shared_ids"],
                   validation_ids=summary["validation_unique_ids"],files=files)
    (ROOT/"website/src/revisionEvidence.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(f"Prepared {len(files)} local revision downloads. No Supabase publication or deployment.")


if __name__ == "__main__":
    main()
