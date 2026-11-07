"""Bounded HTTPS acquisition, immutable storage and credential-free provenance."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "Group5-xam.py-academic-research/1.0"
MAX_BYTES = 32 * 1024 * 1024


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        def cell(value):
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                return "'" + value  # Spreadsheet-safe export; immutable raw bytes stay untouched.
            return value
        writer.writerows({key: cell(value) for key, value in row.items()} for row in rows)


def safe_url(url: str, hosts: set[str]) -> str:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in hosts or p.username or p.password or p.fragment or p.port not in (None, 443):
        raise ValueError("Acquisition URL must use an explicitly allowed HTTPS host without credentials.")
    if re.search(r"(?:token|api.?key|secret|password)=", p.query, re.I):
        raise ValueError("Credentials must never appear in URLs.")
    return url


class RestrictedRedirect(HTTPRedirectHandler):
    def __init__(self, host: str):
        self.host = host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl, {self.host})  # Never forward a Bearer token across hosts.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, *, hosts: set[str], token: str | None = None, body: dict | None = None, attempts: int = 2) -> tuple[bytes, dict]:
    safe_url(url, hosts)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/html,text/plain,*/*"}
    if token:
        if any(c.isspace() for c in token):
            raise ValueError("Invalid access token; no credential value was logged.")
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=canonical(body) if body is not None else None, headers=headers)
    opener = build_opener(RestrictedRedirect(urlparse(url).hostname or ""))
    for attempt in range(attempts):
        try:
            with opener.open(request, timeout=110 if token else 25) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("Download exceeded the size limit; request a smaller area/period.")
                # Whitelist response metadata; never persist request headers or cookies.
                meta = {"source_url": url, "retrieved_at": now(), "http_status": response.status,
                        "content_type": response.headers.get("Content-Type", ""),
                        "etag": response.headers.get("ETag", ""),
                        "last_modified": response.headers.get("Last-Modified", ""),
                        "x_datasets": response.headers.get("x-datasets", ""), "sha256": digest(data), "bytes": len(data)}
                return data, meta
        except HTTPError as error:
            code = error.code
            error.close()
            if code in (429, 503) and attempt + 1 < attempts:
                time.sleep(2)
                continue
            raise RuntimeError(f"Official endpoint returned HTTP {code}; no response body or credential was logged.") from None
        except (URLError, TimeoutError, OSError):
            if attempt + 1 == attempts:
                raise RuntimeError("Official endpoint could not be reached; retry later. No replacement data were created.") from None
    raise RuntimeError("Acquisition did not complete.")


def store_raw(folder: Path, data: bytes, metadata: dict, suffix: str) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    sha = digest(data)
    path = folder / f"{sha}{suffix}"
    if path.exists():
        if digest(path.read_bytes()) != sha:
            raise ValueError("Existing raw snapshot hash mismatch.")
    else:
        with path.open("xb") as stream:
            stream.write(data)
    # Retrieval events are separate from immutable, content-addressed raw bytes.
    record = {**metadata, "sha256": sha, "raw_path": str(path.relative_to(ROOT)).replace("\\", "/")}
    # Keep successful retrieval provenance even when a later parser rejects it.
    event = folder / f"{sha}.{digest(canonical(record))[:16]}.retrieval.json"
    if not event.exists():
        write_json(event, record)
    return record


def load_token(environ=None, path: Path | None = None) -> str:
    environ = os.environ if environ is None else environ
    path = ROOT / ".external-data.local.env" if path is None else path
    if not path.exists():
        return environ.get("GFW_API_ACCESS_TOKEN", "").strip()
    settings = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key.strip() != "GFW_API_ACCESS_TOKEN" or key.strip() in settings:
            raise ValueError("External credential file accepts one GFW_API_ACCESS_TOKEN setting only.")
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("Unclosed quote in external credential file.")
            value = value[1:-1]
        settings[key.strip()] = value
    return settings.get("GFW_API_ACCESS_TOKEN", "").strip()


def verify_raw_manifest(records: list[dict]) -> bool:
    allowed = [(ROOT / f"data/external/{provider}/raw").resolve() for provider in
               ("world_bank", "global_fishing_watch", "open_undersea_cable_map", "ofca")]
    for record in records:
        path = (ROOT / record["raw_path"]).resolve()
        if not any(path.is_relative_to(root) for root in allowed) or not path.is_file() or digest(path.read_bytes()) != record["sha256"]:
            raise ValueError("External raw snapshot missing, changed, or outside its immutable source root.")
    return True
