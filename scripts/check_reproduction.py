"""Reproduce DEVELOPMENT outputs in a fresh, retained temporary working copy.

This fits new temporary copies of the unchanged candidate configurations. It
does not load, refit, replace, or evaluate the original frozen final model.
Uses the caller's recorded environment, not a claim of a new package install.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from review_research import protected_fingerprints


def main():
    import pandas as pd
    import numpy as np
    baseline = protected_fingerprints()
    parent = ROOT/"tmp/reproduction_checks"; parent.mkdir(parents=True,exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="clean-copy-",dir=parent))
    for item in ["src","UnderseaCableRisk"]:
        shutil.copytree(ROOT/item,work/item,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    (work/"scripts").mkdir()
    shutil.copy2(ROOT/"scripts/run_pipeline.py",work/"scripts/run_pipeline.py")
    shutil.copytree(ROOT/"data/external",work/"data/external")
    (work/"requirements.txt").write_bytes((ROOT/"requirements.txt").read_bytes())
    destination = work/"tmp/development-run"
    log_path = work/"execution.log"
    with log_path.open("w",encoding="utf-8") as log:
        run = subprocess.run([sys.executable,"-B",str(work/"scripts/run_pipeline.py"),"--output-root",str(destination)],cwd=work,stdout=log,stderr=subprocess.STDOUT)
    report = dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),working_copy=str(work),
                  returncode=run.returncode,environment="Existing model-compatible project environment, not a fresh dependency installation",
                  temporary_development_fits=True,original_frozen_model_refit=False,final_test_inference=False,comparisons=[])
    if run.returncode == 0:
        for relative in ["outputs/tables/model_comparison_validation.csv","outputs/tables/temporal_cv_scores.csv","outputs/tables/data_split_summary.csv"]:
            original = pd.read_csv(ROOT/relative)
            reproduced = pd.read_csv(destination/relative)
            pd.testing.assert_frame_equal(original,reproduced,check_exact=False,atol=1e-12,rtol=1e-10)
            report["comparisons"].append(dict(artifact=relative,status="matches within numerical tolerance"))
        assert not (destination/"outputs/final_evaluation_2026-11-02").exists()
    report["protected_evidence_unchanged"] = protected_fingerprints()==baseline
    if not report["protected_evidence_unchanged"]:
        raise RuntimeError("Protected original evidence changed")
    target=ROOT/"outputs/revisions/2026-11-05/clean_copy_reproduction.json"
    target.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    if run.returncode:
        print(log_path.read_text(encoding="utf-8")[-6000:])
        raise SystemExit(run.returncode)


if __name__ == "__main__":
    main()
