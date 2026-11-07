"""Authorized GFW report API only; no HTML scraping or visitor-held tokens."""
from __future__ import annotations

import io
import json
import re
import math
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from .common import ROOT, MAX_BYTES, canonical, digest, fetch, store_raw
from .processing import number, validate_dates

ENDPOINT = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
DATASETS = {"public-global-fishing-effort:v5.0": "apparent_fishing_hours",
            "public-global-presence:v5.0": "vessel_presence_hours"}
SOURCE = {"source_id": "global_fishing_watch", "source_name": "AIS apparent fishing activity and vessel presence",
          "publisher": "Global Fishing Watch", "source_url": "https://globalfishingwatch.org/our-apis/documentation/docs/v3/4wings/report",
          "file_or_endpoint": ENDPOINT, "version": "Requested v5.0; resolved x-datasets header verified for each successful report",
          "original_format": "Requested JSON regional report; original response/ZIP retained when acquired",
          "license": "CC BY-NC 4.0; dataset-specific caveats also apply",
          "license_url": "https://globalfishingwatch.org/our-apis/documentation/docs/license-rate-limits",
          "coverage": "AIS-covered vessels and queried geographies only, not all vessels",
          "purpose": "Supplementary empirical maritime-exposure description; not fault prediction",
          "limitations": "AIS coverage varies. Fishing is apparent, algorithmically inferred activity; presence is not anchoring or cable contact. No authenticated fault labels."}


def report_json(data: bytes) -> dict:
    if data.startswith(b"PK"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if sum(m.file_size for m in members) > MAX_BYTES:
                raise ValueError("Uncompressed API report is too large; request a smaller period/area.")
            candidates = []
            for member in members:
                if member.filename.lower().endswith(".json"):
                    value = json.loads(archive.read(member))
                    if isinstance(value, dict) and "entries" in value:
                        candidates.append(value)
            if len(candidates) != 1:
                raise ValueError("Report archive schema changed: expected exactly one entries JSON. Raw bytes retained for inspection.")
            return candidates[0]
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("Expected the documented GFW report object.")
    return value


def clean_report(data: bytes, metadata: dict, area: dict, dataset: str, start: str, end: str) -> list[dict]:
    if dataset not in DATASETS:
        raise ValueError("Use an explicitly supported pinned GFW dataset, not latest.")
    a, b = validate_dates(start, end)
    payload = report_json(data)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("GFW report has no entries array; do not guess its measurements.")
    # Fail on pagination instead of silently truncating large reports.
    if payload.get("nextOffset") or (isinstance(payload.get("total"), int) and payload["total"] > len(entries)):
        raise ValueError("Incomplete/paginated GFW report; narrow the acquisition period before analysis.")
    version = metadata.get("x_datasets", "")
    if dataset not in {item.strip() for item in version.split(',')}:
        raise ValueError("GFW returned no matching resolved dataset-version header; provenance review required.")
    # Live v3 reports wrap rows under the resolved dataset key. The generic
    # documentation also shows flat entries; support both strictly, never mix.
    if entries and all(isinstance(e,dict) and e and set(e)<=set(DATASETS) and all(value is None or isinstance(value,list) for value in e.values()) for e in entries):
        # Verified empty live responses use {dataset: null}; preserve no rows,
        # not a zero measurement and not complete AIS coverage.
        selected = [group[dataset] for group in entries if dataset in group]
        if len(selected) != 1:
            raise ValueError("Report must contain exactly one row group for the requested dataset.")
        entries = selected[0] or []
    totals = defaultdict(list)
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or "hours" not in entry or "date" not in entry or "flag" not in entry:
            raise ValueError("Unsupported GFW row schema; expected date, flag and hours from a FLAG/MONTHLY report.")
        raw_date = str(entry["date"])
        if re.fullmatch(r"\d{4}-\d{2}", raw_date):
            stamp = date.fromisoformat(raw_date + "-01")
        elif re.fullmatch(r"\d{4}-\d{2}-01",raw_date):
            stamp = date.fromisoformat(raw_date)
        else:
            raise ValueError("Monthly report requires YYYY-MM or the first day of a month; do not guess periods.")
        if not a <= stamp < b:
            raise ValueError("GFW row falls outside the requested period.")
        key = (stamp.year, stamp.month, str(entry["flag"]))
        if key in seen:
            raise ValueError("Duplicate flag/month report rows; aggregation would double-count activity.")
        seen.add(key)
        hours = number(entry["hours"], minimum=0)
        if hours is None:
            raise ValueError("Missing fishing/presence hours are not zero.")
        totals[(stamp.year, stamp.month)].append(hours)
    output = []
    for (year, month), value in sorted(totals.items()):
        first = date(year, month, 1)
        next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        output.append({"area_id": area["id"], "country": area["country"],
                       "period_start": max(first, a).isoformat(), "period_end": min(next_month, b).isoformat(),
                       "year": year, "metric": DATASETS[dataset], "value": math.fsum(value), "unit": "vessel-hours",
                       "source_id": "global_fishing_watch", "dataset": dataset,
                       "coverage_status": "reported_AIS_estimate", "raw_sha256": metadata["sha256"]})
    return output


def request_key(query, area):
    location = {"geometry":area["geometry"]} if area.get("geometry") else {"region":area["region"]}
    return digest(canonical({"query":query, **location}))


def retained_reports(raw_dir, explicit=None):
    index = {}
    records = explicit if explicit is not None else [json.loads(path.read_text(encoding="utf-8")) for path in sorted(raw_dir.glob("*.retrieval.json"))]
    for record in records:
        if record.get("method") != "POST" or not record.get("query") or not record.get("study_area"):
            continue
        key = request_key(record["query"],record["study_area"])
        if key not in index or record.get("retrieved_at","") > index[key].get("retrieved_at",""):
            index[key] = record
    return index


def acquire_reports(settings: dict, areas: list[dict], token: str, raw_dir: Path, *, offline=False, progress=None, retained=None) -> tuple[list[dict], list[dict], list[dict]]:
    start, end = settings["start_date"], settings["end_date"]
    validate_dates(start, end)
    if not token and not offline:
        raise ValueError("GFW personal API token missing. Set GFW_API_ACCESS_TOKEN privately; do not share it.")
    records, downloads, events = [], [], []
    cache = retained_reports(raw_dir,retained)
    consecutive_errors, downloaded = 0, set()
    requested = settings['datasets']
    if any(dataset not in DATASETS for dataset in requested):
        raise ValueError("Unsupported or unpinned GFW dataset.")
    base_query = {"date-range":f"{start},{end}","format":"JSON","group-by":"FLAG","temporal-resolution":"MONTHLY","spatial-aggregation":"true"}
    def scope(query,area):
        return request_key({k:v for k,v in query.items() if not k.startswith('datasets[')},area)
    candidates = defaultdict(list)
    for item in cache.values():
        candidates[scope(item['query'],item['study_area'])].append(item)
    for area in areas:  # One serial report/user; both metrics share one request.
        available = {}
        prior = candidates.get(scope(base_query,area),[])
        for dataset in requested:
            matches = [r for r in prior if dataset in [v for k,v in r['query'].items() if k.startswith('datasets[')]]
            if matches:
                available[dataset] = {**max(matches,key=lambda r:r.get('retrieved_at','')),'cache_reused':True}
        missing = [dataset for dataset in requested if dataset not in available]
        acquisition_error = None
        if missing and not offline:
            params = {**base_query,**{f'datasets[{i}]':dataset for i,dataset in enumerate(missing)}}
            body = {"geojson":json.dumps({"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":area['geometry']}]})} if area.get('geometry') else {"region":area['region']}
            try:
                data,meta = fetch(ENDPOINT+'?'+urlencode(params),hosts={'gateway.api.globalfishingwatch.org'},token=token,body=body)
                record = store_raw(raw_dir,data,{**meta,'query':params,'study_area':area,'method':'POST','request_key':request_key(params,area)},'.report')
                for dataset in missing:
                    available[dataset] = record
            except (ValueError,RuntimeError) as error:
                acquisition_error = str(error)
        for dataset in requested:
            try:
                record = available.get(dataset)
                if not record:
                    raise ValueError(acquisition_error or 'No verified raw report cached for this region/period/metric.')
                path = (ROOT/record['raw_path']).resolve()
                if not path.is_relative_to(raw_dir.resolve()) or not path.is_file():
                    raise ValueError('Cached report path is missing or outside its source root.')
                data = path.read_bytes()
                if digest(data) != record['sha256']:
                    raise ValueError('Cached raw report changed; no network fallback masks tampering.')
                identity = (record['raw_path'],record.get('source_url'),area['id'])
                if identity not in downloaded:
                    downloads.append(record); downloaded.add(identity)
                cleaned = clean_report(data,record,area,dataset,start,end)
                records.extend(cleaned)
                consecutive_errors = 0
                events.append(dict(stage='gfw_report',status='acquired' if cleaned else 'no_records_returned',area_id=area['id'],dataset=dataset,rows=len(cleaned),message='Empty/null result is not converted into zero activity.' if not cleaned else 'Monthly flags summed within one geography and metric; no vessel identities exported.'))
            except (ValueError,RuntimeError,json.JSONDecodeError,zipfile.BadZipFile) as error:
                events.append(dict(stage='gfw_report',status='blocked',area_id=area['id'],dataset=dataset,rows=0,message='Report acquisition/schema validation failed: '+str(error)))
                consecutive_errors += 1
            if progress:
                progress(dict(completed_queries=len(events),planned_queries=len(areas)*len(requested),**events[-1]))
            if consecutive_errors >= 3:
                return records, downloads, events
    return records, downloads, events
