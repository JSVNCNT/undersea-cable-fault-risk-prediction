"""Admin-only publication of the EXISTING generated website export.

Default is a local dry run. --publish needs SUPABASE_URL and SUPABASE_SECRET_KEY
in process environment; secrets are never CLI arguments, files, or output.
No training, inference, fabricated seed rows, remote deletes, or overwrite of
an already-published release. An interrupted UNPUBLISHED import is resumable.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def load_publication():
    research = json.loads((ROOT / "public/data/research.json").read_text(encoding="utf-8"))
    rows = json.loads((ROOT / "public/data/observations.json").read_text(encoding="utf-8"))
    release = research["release_id"]
    build_release = json.loads((ROOT / "src/release.json").read_text(encoding="utf-8"))
    if release != build_release["release_id"] or research["model_sha256"] != build_release["model_sha256"]:
        raise ValueError("Export does not match the website build release. Re-export/rebuild consistently.")
    if len(rows) != research["counts"]["eligible"] or len({(r["cable_id"],r["year"]) for r in rows}) != len(rows):
        raise ValueError("Export is incomplete or duplicated.")
    for split in research["splits"]:
        selected = [r for r in rows if r["partition"] == split["partition"]]
        if len(selected) != split["rows"] or sum(r["fault_next_year"] for r in selected) != split["positives"]:
            raise ValueError("Export does not reconcile with saved partition counts.")
    metric_keys = ["accuracy","precision","recall","f1","pr_auc","roc_auc"]
    models, evaluations = [], []
    for model in research["models"]:
        models.append({"release_id":release,"model_id":model["id"],"selected":model["selected"],"parameters":model["parameters"]})
        for partition in ["validation","final_test"]:
            metrics = model[partition]
            if metrics is not None:
                evaluations.append({"release_id":release,"model_id":model["id"],"partition":partition,
                                    **{k:metrics[k] for k in metric_keys},**{k.lower():metrics[k] for k in ["TN","FP","FN","TP"]}})
    return research, {
        "cable_year_observations":[{"release_id":release,**row} for row in rows],
        "variable_definitions":[{"release_id":release,"variable":d["variable"],"definition":d} for d in research["dictionary"]],
        "model_versions":models, "evaluation_results":evaluations,
        "source_context":[{"release_id":release,"metric_id":r["metric_id"],"value":r["value"],"reference":r} for r in research["context"]],
        "historical_incidents":[{"release_id":release,"incident_id":r["incident_id"],"telecom_cables_damaged":r["telecom_cables_damaged"],"reference":r} for r in research["incidents"]],
    }


def request(url, key, path, method="GET", body=None, headers=None):
    data = None if body is None else json.dumps(body, allow_nan=False).encode()
    combined = {"apikey":key,"Content-Type":"application/json",**(headers or {})}
    # New sb_secret keys are opaque API keys, not JWT bearer tokens. Legacy service
    # role keys require the bearer header as well.
    if not key.startswith("sb_secret_"):
        combined["Authorization"] = f"Bearer {key}"
    req = Request(url + "/rest/v1/" + path, data=data, method=method, headers=combined)
    try:
        with urlopen(req, timeout=60) as response:
            content = response.read()
            return json.loads(content) if content else None, dict(response.headers)
    except HTTPError as error:
        raise RuntimeError(f"Supabase {method} failed with HTTP {error.code}. Check SQL schema, key role, and project URL. Credentials and response bodies are omitted.") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Authorize writing and publishing this release in the configured Supabase project.")
    args = parser.parse_args()
    research, tables = load_publication()
    print("Release:", research["release_id"])
    for table, records in tables.items():
        print(f"{table}: {len(records)} existing records")
    if not args.publish:
        print("Dry run only. No network requests or database writes.")
        return
    url, key = os.getenv("SUPABASE_URL", "").rstrip("/"), os.getenv("SUPABASE_SECRET_KEY", "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("SUPABASE_URL must be a plain HTTPS project origin.")
    if not key or key.startswith("sb_publishable_"):
        raise ValueError("Use a secret/admin key in SUPABASE_SECRET_KEY, never a browser publishable key.")
    query = "id=eq." + quote(research["release_id"], safe="")
    existing, _ = request(url,key,"dataset_versions?" + query + "&select=id,published,payload")
    if existing and existing[0]["published"]:
        raise ValueError("Release is already published and immutable. Nothing was changed.")
    if existing and existing[0]["payload"] != research:
        raise ValueError("An unpublished release with this ID has different metadata. Nothing was overwritten; review the export before resuming.")
    request(url,key,"dataset_versions?on_conflict=id","POST",[{"id":research["release_id"],"model_sha256":research["model_sha256"],"payload":research,"published":False}],{"Prefer":"resolution=merge-duplicates,return=minimal"})
    for table, records in tables.items():
        for offset in range(0,len(records),250):
            request(url,key,table,"POST",records[offset:offset+250],{"Prefer":"resolution=merge-duplicates,return=minimal"})
        _, headers = request(url,key,f"{table}?release_id=eq.{quote(research['release_id'],safe='')}&select=*","HEAD",headers={"Prefer":"count=exact"})
        count_range = next((v for k,v in headers.items() if k.lower()=="content-range"),"")
        if not count_range.endswith("/" + str(len(records))):
            raise ValueError(f"{table} count mismatch; release remains unpublished.")
    request(url,key,"dataset_versions?" + query,"PATCH",{"published":True})
    print("Published after all table counts verified. Next: run 002_verify_access.sql and test browser read-only access.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
