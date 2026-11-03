"""Admin-only publication of the EXISTING generated website export.

Default is a local dry run. --publish reads SUPABASE_URL and SUPABASE_SECRET_KEY
from the Git-ignored repository-root .supabase-admin.local.env, or from process
environment if that file is absent. Secrets are never CLI arguments or output.
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
ADMIN_ENV_PATH = ROOT.parent / ".supabase-admin.local.env"


def load_admin_credentials(env_path=None, environ=None):
    """Read only the two supported admin settings, without executing dotenv text.

    A present local file is authoritative, including blank/missing values, so
    stale PowerShell credentials cannot accidentally override a newly edited file.
    No interpolation, shell commands, frontend settings, or value logging.
    """
    env_path = ADMIN_ENV_PATH if env_path is None else Path(env_path)
    environ = os.environ if environ is None else environ
    allowed = {"SUPABASE_URL", "SUPABASE_SECRET_KEY"}
    if env_path.is_file():
        settings = {}
        for number, raw in enumerate(env_path.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name, separator, value = line.partition("=")
            name, value = name.strip(), value.strip()
            if not separator or name not in allowed:
                raise ValueError(f"Invalid admin configuration on line {number}. Use only SUPABASE_URL=value and SUPABASE_SECRET_KEY=value; do not paste PowerShell commands.")
            if name in settings:
                raise ValueError(f"Duplicate admin configuration on line {number}. Keep each setting once.")
            if value.startswith(("'", '"')):
                if len(value) < 2 or value[-1] != value[0]:
                    raise ValueError(f"Unclosed quote in admin configuration on line {number}.")
                value = value[1:-1].strip()
            settings[name] = value
    else:
        settings = {name: environ.get(name, "").strip() for name in allowed}
    url = settings.get("SUPABASE_URL", "").strip().rstrip("/")
    key = settings.get("SUPABASE_SECRET_KEY", "").strip()
    if not url:
        raise ValueError("Missing SUPABASE_URL. Fill the Git-ignored repository-root .supabase-admin.local.env file.")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment or any(char.isspace() for char in url):
        raise ValueError("SUPABASE_URL must be a plain HTTPS project origin, such as https://PROJECT-REFERENCE.supabase.co; not a dashboard, /rest/v1, or database URL.")
    if not key:
        raise ValueError("Missing SUPABASE_SECRET_KEY. Fill the blank secret-key line in .supabase-admin.local.env; do not use .env.example or a VITE_* setting.")
    if key.startswith(("sb_publishable_", "http://", "https://", "postgres://", "postgresql://")):
        raise ValueError("SUPABASE_SECRET_KEY must be an admin/secret key, not a publishable key, project URL, or database URL.")
    return url, key


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
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--publish", action="store_true", help="Authorize writing and publishing this release in the configured Supabase project.")
    actions.add_argument("--check-config", action="store_true", help="Validate local admin configuration without printing credentials or making network requests.")
    args = parser.parse_args()
    if args.check_config:
        load_admin_credentials()
        print("Admin URL and key are configured. Local format checks only; key authentication was not tested. No credentials printed and no network requests made.")
        return
    research, tables = load_publication()
    print("Release:", research["release_id"])
    for table, records in tables.items():
        print(f"{table}: {len(records)} existing records")
    if not args.publish:
        print("Dry run only. No network requests or database writes.")
        return
    url, key = load_admin_credentials()
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
