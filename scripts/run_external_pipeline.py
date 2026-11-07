"""Independent empirical workflow; --acquire enables official web access.

Examples (from repository root):
  python scripts/run_external_pipeline.py --acquire --export-website
  python scripts/run_external_pipeline.py --catalog-snapshot PATH --export-website
  python scripts/run_external_pipeline.py --help

Edit config/external_empirical.json to declare a licensed infrastructure snapshot,
actual column mapping, and documented GFW study areas. No fabricated seed data,
fault targets, classifier fitting, final scoring, SQL, or cloud publication.
"""
from __future__ import annotations

import argparse
import json
import platform
import io
import zipfile
from importlib.metadata import version
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evidence import verify_historical_evidence
from src.external.common import canonical, digest, load_token, now, verify_raw_manifest, write_csv, write_json
from src.external.gfw import DATASETS, SOURCE as GFW_SOURCE, acquire_reports
from src.external.processing import infrastructure_summary, integrate_activity, load_infrastructure, prepare_areas, validate_dates
from src.external.world_bank import CATALOG, acquire_catalog, parse_catalog
from src.external import ofca, open_cable_archive, gfw_regions

LIMITATIONS = [
    "Empirical exposure is separate from the synthetic classification experiment. No CAB crosswalk or fault labels exist here.",
    "Scraped catalog resource descriptors are metadata, not measured cable/landing observations.",
    "GFW apparent fishing and presence are AIS-derived estimates, not cable contact, anchoring, faults or fault probabilities.",
    "Infrastructure snapshot dates and activity periods may differ; do not infer historical operation or a time-series inventory.",
    "Country context does not measure exposure along a particular cable. Landing buffers are coastal proxies, not cable routes.",
    "Areas can overlap; their activity totals must not be added as a deduplicated global total.",
    "Absent records/coverage remain unavailable rather than being replaced with zero or imputed coordinates.",
    "Historical archive infrastructure is not World Bank observation data. Source-specific vintage and noncommercial reuse terms are retained.",
    "OFCA HTML records are Hong Kong prose-list observations for their stated month, not HTML table rows or a global cable inventory.",
    "Schematic archived landing coordinates and TBD locations are unsuitable for narrow route/landing hazard buffers. None are generated from this archive.",
    "Global EEZ coverage is not all-ocean coverage: high seas are excluded. Joint/overlapping regimes remain separate and region totals must not be summed into a deduplicated global total.",
    "Exact source-territory label matches provide country context only, not evidence that a landing point or cable lies inside a particular EEZ. Country labels are not harmonized by guesswork.",
]


def dictionary():
    definitions = [
        ("id", "infrastructure/geographies/cable_systems", "Supplied source key or dataset-prefixed official region ID; never an invented real-cable mapping", "identifier", "infrastructure", "source_reported_or_derived_key"),
        ("country", "infrastructure/activity", "Source country or explicitly declared geographic label, not vessel flag", "category", "infrastructure", "source_reported"),
        ("latitude", "infrastructure", "Supplied landing latitude; missing is preserved", "degrees WGS84", "infrastructure", "source_reported"),
        ("longitude", "infrastructure", "Supplied landing longitude; missing is preserved", "degrees WGS84", "infrastructure", "source_reported"),
        ("snapshot_date", "infrastructure", "Documented infrastructure snapshot date, not metadata modification date", "date", "infrastructure", "source_reported"),
        ("records", "infrastructure_summary", "Distinct records within a country AND source record kind", "count", "infrastructure", "derived"),
        ("area_id", "activity", "Explicit study area, with region/polygon and justification in geographies", "identifier", "exposure", "derived"),
        ("apparent_fishing_hours", "activity.metric", "GFW algorithmically estimated apparent fishing time for AIS-covered vessels", "vessel-hours", "exposure", "AIS_estimated"),
        ("vessel_presence_hours", "activity.metric", "GFW AIS vessel presence, not anchoring and not individual vessel tracks", "vessel-hours", "exposure", "AIS_estimated"),
        ("period_start", "activity", "Inclusive requested/report period start", "UTC date", "exposure", "derived"),
        ("period_end", "activity", "Exclusive requested/report period end", "UTC date", "exposure", "derived"),
        ("buffer_km", "geographies/summary", "Explicit buffer sensitivity distance; not a physical hazard zone", "km", "exposure", "derived"),
        ("resource_id", "catalog_resources", "Scraped catalog resource key; describes a resource, not a cable", "identifier", "provenance", "HTML_scraped"),
        ("name", "infrastructure/catalog_resources", "Supplied location/system or catalog resource name, not inferred identity", "text", "infrastructure", "source_reported"),
        ("record_kind", "infrastructure/catalog_resources", "Declared original record unit; metadata and observations must not be mixed", "category", "provenance", "source_reported"),
        ("coordinate_precision", "infrastructure", "Source-documented coordinate precision or explicitly unknown", "text", "provenance", "source_reported"),
        ("source_id", "all", "Source registry key", "identifier", "provenance", "derived"),
        ("source_url", "sources/catalog_resources", "Official dataset/resource URL", "URL", "provenance", "source_reported"),
        ("source_name", "sources", "Official source dataset title", "text", "provenance", "source_reported"),
        ("publisher", "sources", "Source organization", "text", "provenance", "source_reported"),
        ("license", "sources", "Recorded source reuse terms; catalog rights do not imply third-party rights", "text", "provenance", "source_reported"),
        ("license_url", "sources", "Link to the recorded license/terms", "URL", "provenance", "source_reported"),
        ("access_date", "sources/catalog_resources", "Actual successful retrieval timestamp; unknown on unverified replay", "UTC timestamp", "provenance", "derived"),
        ("metadata_updated", "sources", "Catalog metadata update; NOT infrastructure observation date", "date", "provenance", "HTML_scraped"),
        ("coverage", "sources", "Documented source coverage and known exclusions", "text", "provenance", "source_reported"),
        ("period", "sources", "Source period or explicitly requested activity interval", "text", "provenance", "source_reported"),
        ("purpose", "sources", "Permitted analytical role in this supplementary workflow", "text", "provenance", "derived"),
        ("limitations", "sources", "Source-specific interpretation limits", "text", "provenance", "source_reported"),
        ("status", "sources", "Actual acquisition state, not approval or evidence of empirical validity", "category", "provenance", "derived"),
        ("description", "catalog_resources", "Official resource description extracted from HTML", "text", "provenance", "HTML_scraped"),
        ("format", "catalog_resources", "Listed resource format, not a guessed downloadable format", "category", "provenance", "HTML_scraped"),
        ("download_available", "catalog_resources", "Whether the official catalog explicitly lists a direct download", "boolean", "provenance", "HTML_scraped"),
        ("resource_license", "catalog_resources", "Resource-specific rights, or explicitly not established", "text", "provenance", "HTML_scraped"),
        ("html_sha256", "catalog_resources", "Checksum of the exact immutable scraped HTML", "SHA-256", "provenance", "derived"),
        ("year", "activity", "Year derived from the actual report period", "year", "exposure", "derived"),
        ("metric", "activity", "Apparent fishing or vessel presence; never a fault outcome", "category", "exposure", "source_reported"),
        ("value", "activity", "Reported hours summed across flag groups within ONE area and month", "vessel-hours", "exposure", "derived"),
        ("unit", "activity", "Hours across AIS-covered vessels, not a count of fishing trips or faults", "text", "exposure", "source_reported"),
        ("dataset", "activity", "Pinned and response-verified GFW dataset/version", "identifier", "provenance", "source_reported"),
        ("coverage_status", "activity", "Reported AIS estimate; no assertion of complete vessel coverage", "category", "provenance", "derived"),
        ("raw_sha256", "activity", "Checksum linking an aggregate to its immutable API response", "SHA-256", "provenance", "derived"),
        ("infrastructure_records", "summary", "Count of supplied infrastructure keys matched by an explicit site-area key or exact source-territory label. Zero means no supplied match, not proof that no cables exist.", "count", "infrastructure", "derived"),
        ("infrastructure_source_ids", "summary", "Actual source registry keys of matched infrastructure records; separate from the GFW activity source", "identifier list", "provenance", "derived"),
        ("linkage", "summary", "Landing-area, broad country context, or explicitly unlinked activity", "category", "provenance", "derived"),
        ("interpretation", "summary", "Explicit boundary: exposure is not a cable-fault estimate", "text", "provenance", "derived"),
        ("file_or_endpoint", "sources", "Actual acquisition endpoint or immutable source file location", "URL/path", "provenance", "source_reported"),
        ("version", "sources", "Source version or explicit lack of an established version", "text", "provenance", "source_reported"),
        ("original_format", "sources", "Acquired/requested source format, not a guessed infrastructure format", "text", "provenance", "source_reported"),
        ("location_to_be_determined", "infrastructure", "Original GeoJSON TBD flag; unknown remains missing", "boolean", "infrastructure", "source_reported"),
        ("cable_id", "cable_landings", "Supplied historical cable key, never a CAB crosswalk", "identifier", "infrastructure", "source_reported"),
        ("landing_id", "cable_landings", "Supplied historical landing key; both relationship directions reconciled", "identifier", "infrastructure", "source_reported"),
        ("length_reported", "cable_systems", "Original reported length text, not recalculated from schematic geometry", "source text", "infrastructure", "source_reported"),
        ("rfs_reported", "cable_systems", "Original service-date text, possibly planned at archive time; not verified current operation", "source text", "infrastructure", "source_reported"),
        ("owners_reported", "cable_systems", "Original owner description at unknown individual record date", "text", "infrastructure", "source_reported"),
        ("suppliers_reported", "cable_systems", "Original supplier description", "text", "infrastructure", "source_reported"),
        ("landing_point_count", "cable_systems", "Count of distinct supplied landing links for this cable", "count", "infrastructure", "derived"),
        ("status_interpretation", "cable_systems", "Archived description is not evidence of current operation", "text", "provenance", "derived"),
        ("observation_id", "html_observations", "Derived HTML observation key from source/month/list position, NOT a cable-system crosswalk", "identifier", "provenance", "derived"),
        ("system_name_reported", "html_observations", "Complete regulator list entry, preserving combined names and aliases", "text", "infrastructure", "HTML_scraped"),
        ("reference_period", "html_observations", "Month explicitly stated in regulator prose, not an invented day", "YYYY-MM", "provenance", "HTML_scraped"),
        ("extraction_method", "html_observations", "Prose list extraction, not HTML table scraping", "text", "provenance", "derived"),
        ("relationship_evidence", "cable_landings", "Whether supplied relationship is corroborated in both directions, cable record only or landing record only", "category", "provenance", "derived"),
        ("detail_record_available", "infrastructure", "Whether the original individual landing detail file exists", "boolean", "provenance", "derived"),
        ("country_assignment", "infrastructure", "Exact source field or exact-key country membership lookup; never geocoded or name-parsed", "category", "provenance", "derived"),
        ("source_text_quality", "html_observations", "Flags replacement characters or nonprinting C1 controls already present in source HTML; original wording is retained", "category", "provenance", "derived"),
        ("region_category", "geographies", "Flags source EEZ region versus a joint/overlapping regime; not a sovereignty determination", "category", "provenance", "derived"),
        ("iso3", "geographies", "Official GFW region ISO3 metadata, possibly empty/null for joint regimes; never vessel flag", "ISO3", "provenance", "source_reported"),
        ("territory_label", "geographies", "Original territory1 label, retained without speculative country-name harmonization", "text", "provenance", "source_reported"),
        ("sovereignty_iso_codes", "geographies", "Original nonempty isoSov1/2/3 values; joint claims not assigned to a single country", "ISO3 list", "provenance", "source_reported"),
        ("region_metadata_sha256", "geographies", "Checksum of the exact official GFW region definitions used", "SHA-256", "provenance", "derived"),
        ("region_metadata_url", "geographies", "Documented official context-layers endpoint used for region IDs and labels", "URL", "provenance", "source_reported"),
    ]
    return [{"variable": v, "dataset": d, "definition": text, "unit": unit, "indicator_group": group,
             "measurement_kind": kind, "data_type": "number" if v in ("latitude", "longitude", "value", "buffer_km") else "integer" if v in ("records", "year", "infrastructure_records", "landing_point_count") else "boolean" if v in ("download_available", "location_to_be_determined", "detail_record_available") else "array[string]" if v in ("sovereignty_iso_codes", "infrastructure_source_ids") else "string",
             "source": "Global Fishing Watch / Marine Regions context-layer metadata as supplied by GFW" if d == "geographies" else "Global Fishing Watch / declared study geography" if group == "exposure" else "Actual source_id registry: World Bank metadata / historical TeleGeography archive / OFCA HTML / Global Fishing Watch",
             "used_in_synthetic_model": False, "external_analysis_only": True,
             "temporal_meaning": "Source snapshot or declared acquisition period; not a next-year fault outcome",
             "geographic_meaning": "Documented site/country/study area only", "limitations": "No authenticated fault outcome; source coverage and measurement caveats apply."}
            for v, d, text, unit, group, kind in definitions]


def validate_publication(payload: dict):
    core = {k: v for k, v in payload.items() if k not in ("release_id", "manifest_sha256")}
    sha = digest(canonical(core))
    if payload.get("manifest_sha256") != sha or payload.get("release_id") != "external-" + sha[:16]:
        raise ValueError("External release hash mismatch.")
    source_ids = {s["source_id"] for s in payload["sources"]}
    if not {"world_bank", "global_fishing_watch"} <= source_ids or not source_ids <= {"world_bank", "global_fishing_watch", "open_undersea_cable_map", "ofca"} or len(source_ids) != len(payload["sources"]):
        raise ValueError("External release requires distinct reviewed source status records.")
    keys = ("catalog_resources", "infrastructure", "activity", "geographies", "cable_systems", "cable_landings", "html_observations")
    if payload["counts"] != {key:len(payload[key]) for key in keys if key in payload}:
        raise ValueError("External release counts do not reconcile.")
    if any(any(field in row for field in ("fault_next_year", "fault_this_year", "predicted_risk", "model_probability")) for key in keys + ("summary",) for row in payload.get(key, [])):
        raise ValueError("Fault targets are prohibited in the empirical layer.")
    sites = payload["infrastructure"]
    cables = payload.get("cable_systems", [])
    edges = payload.get("cable_landings", [])
    for rows, field in ((sites, "id"), (cables, "id"), (payload.get("html_observations", []), "observation_id")):
        if len({r[field] for r in rows}) != len(rows):
            raise ValueError("Duplicate empirical source key.")
    site_keys, cable_keys = {r["id"] for r in sites}, {r["id"] for r in cables}
    edge_keys = {(e["cable_id"], e["landing_id"]) for e in edges}
    if len(edge_keys) != len(edges) or any(c not in cable_keys or p not in site_keys for c,p in edge_keys):
        raise ValueError("Cable/landing foreign keys do not reconcile.")
    for key in keys:
        if any(row.get("source_id") not in source_ids for row in payload.get(key, []) if "source_id" in row):
            raise ValueError("Observation source absent from the registry.")
    if (payload['status']=='available') != payload['empirical_analysis_available'] or payload['empirical_analysis_available'] and not (sites and payload['activity']):
        raise ValueError('Empirical availability requires actual infrastructure and activity observations.')
    if payload['empirical_analysis_available']:
        expected={(a['id'],dataset) for a in payload['geographies'] for dataset in payload['configuration']['gfw']['datasets']}
        reports=[e for e in payload['events'] if e['stage']=='gfw_report']
        actual={(e.get('area_id'),e.get('dataset')) for e in reports if e['status'] in ('acquired','no_records_returned')}
        if actual!=expected or len(reports)!=len(expected):
            raise ValueError('Empirical availability cannot omit, duplicate or fail requested region/metric checks.')
    return payload


def export_website(payload: dict, output: Path):
    validate_publication(payload)
    # Generated public assets are intentionally replaced together; raw sources and
    # the original synthetic release are never overwritten.
    destination = ROOT / "website/public/external-data"
    destination.mkdir(parents=True, exist_ok=True)
    for name in CSV_DATASETS:
        (destination / name).write_bytes((output / name).read_bytes())
    if payload.get("cable_systems"):
        (destination / "historical_infrastructure.zip").write_bytes((output / "historical_infrastructure.zip").read_bytes())
    (destination / "research.json").write_bytes(canonical(payload))
    (ROOT / "website/src/externalRelease.json").write_bytes(canonical({"release_id": payload["release_id"], "manifest_sha256": payload["manifest_sha256"]}))


CSV_DATASETS = {
    "external_source_registry.csv":"sources", "external_data_dictionary.csv":"variables",
    "scraped_catalog_resources.csv":"catalog_resources", "cleaned_world_bank_infrastructure.csv":"world_bank_infrastructure",
    "cleaned_infrastructure.csv":"infrastructure", "cleaned_gfw_activity.csv":"activity", "external_empirical_summary.csv":"summary",
    "historical_cable_systems.csv":"cable_systems", "historical_cable_landings.csv":"cable_landings",
    "scraped_ofca_systems.csv":"html_observations",
    "external_geographies.csv":"geographies",
}


def archive_download_bundle(output, downloads):
    """Keep the original license and explicit changes with derivative CSVs."""
    record = next(r for r in downloads if r["source_url"] == open_cable_archive.DOWNLOAD)
    raw = (ROOT / record["raw_path"]).read_bytes()
    if digest(raw) != record["sha256"]:
        raise ValueError("Archive checksum changed before creating attributed download.")
    with zipfile.ZipFile(io.BytesIO(raw)) as original:
        license_text = original.read(f"open_undersea_cable_map-{open_cable_archive.REVISION}/LICENSE")
    attribution = (
        "Open Undersea Cable Map. Original data: TeleGeography. Archive maintained by Steve Song.\n"
        f"Source: {open_cable_archive.REPOSITORY}\nRevision: {open_cable_archive.REVISION}\n"
        f"License: CC BY-NC-SA 3.0, {open_cable_archive.LICENSE}\n"
        "Academic processing: Group 5 xam.py. Changes: JSON/GeoJSON converted to CSV, exact original keys joined, "
        "source discrepancies and unknown dates flagged. No invented infrastructure/fault data. "
        "Derivative archive datasets retain CC BY-NC-SA 3.0. No endorsement implied.\n"
        "Maintainer describes late-2022 source vintage. Individual observation dates unknown. "
        "Not a current inventory, surveyed cable route or cable-fault dataset.\n"
        "The independent World Bank, OFCA and GFW sources are NOT included or relicensed by this archive bundle.\n"
    )
    path = output / "historical_infrastructure.zip"
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in ("cleaned_infrastructure.csv", "historical_cable_systems.csv", "historical_cable_landings.csv"):
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, (output / name).read_bytes())
        bundle.writestr(zipfile.ZipInfo("LICENSE.txt",date_time=(1980,1,1,0,0,0)), license_text)
        bundle.writestr(zipfile.ZipInfo("ATTRIBUTION.txt",date_time=(1980,1,1,0,0,0)), attribution.encode("utf-8"))
    return {path.name: digest(path.read_bytes())}


def run(args):
    protocol = json.loads((ROOT / "outputs/revisions/2026-11-05/revision_protocol.json").read_text(encoding="utf-8"))
    verify_historical_evidence(protocol["protected_sha256"])
    settings = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if settings.get("schema_version") != 1 or set(settings) - {"schema_version", "infrastructure", "gfw", "landing_area_buffers", "historical_archive", "html_context"}:
        raise ValueError("Unsupported external configuration schema.")
    use_archive = settings.get("historical_archive", False)
    use_context = settings.get("html_context", False)
    if not isinstance(use_archive, bool) or not isinstance(use_context, bool):
        raise ValueError("Reviewed alternative-source switches must be booleans.")
    if use_archive and settings.get("infrastructure"):
        raise ValueError("Do not silently mix historical archive and World Bank observation inventories.")
    if use_archive and settings.get("landing_area_buffers"):
        raise ValueError("Archive cartographic coordinates have no established survey precision; use reviewed broader regions, not landing buffers.")
    replay = None
    if args.replay_release:
        from scripts.verify_external_release import verify
        verify(Path(args.replay_release))
        replay_folder = Path(args.replay_release)
        replay = json.loads((replay_folder / "acquisition_manifest.json").read_text(encoding="utf-8"))
    def retained(url):
        matches = [r for r in replay["downloads"] if r["source_url"] == url] if replay else []
        if len(matches) != 1:
            raise ValueError("Retained acquisition requires exactly one verified raw source response.")
        return matches[0], (ROOT / matches[0]["raw_path"]).read_bytes()
    gfw = settings["gfw"]
    if set(gfw) - {"start_date", "end_date", "datasets", "areas", "period_rationale", "region_selection"}:
        raise ValueError("Unsupported GFW setting; keep personal credentials OUT of the configuration JSON.")
    validate_dates(gfw["start_date"], gfw["end_date"])
    if not gfw["datasets"] or len(gfw["datasets"]) != len(set(gfw["datasets"])) or any(d not in DATASETS for d in gfw["datasets"]):
        raise ValueError("Declare distinct supported, pinned GFW datasets.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = Path(args.output_root or ROOT / "outputs/external_empirical" / stamp).resolve()
    if not output.is_relative_to((ROOT / "outputs/external_empirical").resolve()) or output.exists():
        raise ValueError("Use a NEW directory inside outputs/external_empirical/; existing runs are immutable.")
    output.mkdir(parents=True)
    for provider in ("world_bank", "global_fishing_watch", "open_undersea_cable_map", "ofca"):
        for role in ("raw", "processed", "metadata"):
            (ROOT / "data/external" / provider / role).mkdir(parents=True, exist_ok=True)
    downloads, events, resources = [], [], []
    wb = {"source_id": "world_bank", "source_name": "World Development Report 2021 - Maps O.4 and 5.1", "publisher": "World Bank",
          "source_url": CATALOG, "license": "Not verified in this run", "license_url": "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets",
          "file_or_endpoint": CATALOG, "version": "Not acquired", "original_format": "Not acquired",
          "access_date": None, "metadata_updated": None, "coverage": "Actual infrastructure coverage not established", "period": "Not established",
          "purpose": "Infrastructure source discovery", "status": "not_acquired", "limitations": "No authenticated infrastructure file acquired."}
    if args.acquire:
        try:
            wb, resources, records = acquire_catalog(ROOT / "data/external/world_bank/raw")
            downloads.extend(records)
            events.append({"stage": "html_scraping", "status": "metadata_acquired", "rows": len(resources), "message": "Actual resource descriptors extracted from official HTML; these are NOT infrastructure observations."})
        except (ValueError, RuntimeError, json.JSONDecodeError):
            events.append({"stage": "html_scraping", "status": "blocked", "rows": 0, "message": "Official catalog access, robots, or schema check failed; no metadata was invented."})
    elif args.catalog_snapshot or replay:
        retained_wb = retained(CATALOG)[0] if replay else None
        snapshot = (ROOT / retained_wb["raw_path"]).resolve() if replay else Path(args.catalog_snapshot).resolve()
        if not snapshot.is_relative_to((ROOT / "data/external/world_bank/raw").resolve()):
            raise ValueError("Replay only an unchanged catalog snapshot in the raw directory.")
        data = snapshot.read_bytes()
        if snapshot.stem != digest(data):
            raise ValueError("Retained content-addressed HTML was modified; do not replay it.")
        wb, resources = parse_catalog(data.decode("utf-8"))
        snapshot_hash = digest(data)
        known_retrievals = []
        for prior in (ROOT / "outputs/external_empirical").glob("*/acquisition_manifest.json"):
            for entry in json.loads(prior.read_text(encoding="utf-8")).get("downloads", []):
                if entry.get("sha256") == snapshot_hash and entry.get("source_url") == CATALOG and entry.get("retrieved_at"):
                    known_retrievals.append(entry["retrieved_at"])
        recorded_access = retained_wb.get("retrieved_at") if retained_wb else min(known_retrievals) if known_retrievals else None
        wb.update(access_date=recorded_access, status="metadata_only")
        for resource in resources:
            resource.update(access_date=recorded_access, html_sha256=snapshot_hash)
        downloads.append({"source_url": CATALOG, "sha256": snapshot_hash, "raw_path": str(snapshot.relative_to(ROOT)).replace("\\", "/"), "method": "offline_replay", "retrieved_at": recorded_access})
        events.append({"stage": "html_scraping", "status": "metadata_replayed", "rows": len(resources), "message": "Replayed retained HTML. Original access timestamp is not guessed."})
    else:
        events.append({"stage": "html_scraping", "status": "not_requested", "rows": 0, "message": "Use --acquire for official HTML scraping, or --catalog-snapshot for offline replay."})
    infrastructure, snapshot_meta = load_infrastructure(settings.get("infrastructure"))
    wb_infrastructure = list(infrastructure)
    sources, cables, connections, html_rows = [wb], [], [], []
    if use_archive:
        if args.acquire:
            (infrastructure, cables, connections, archive_source), archive_record = open_cable_archive.acquire_archive(ROOT / "data/external/open_undersea_cable_map/raw")
        elif replay:
            archive_record, data = retained(open_cable_archive.DOWNLOAD)
            infrastructure, cables, connections, archive_source = open_cable_archive.replay_archive(data, archive_record.get("retrieved_at"))
        else:
            raise ValueError("Enabled historical acquisition needs --acquire or --replay-release; no substitute records generated.")
        downloads.append(archive_record)
        sources.append(archive_source)
        events.append({"stage":"historical_infrastructure", "status":"acquired", "rows":len(infrastructure), "message":"Pinned licensed historical archive. Original source-key joins only. Observation dates are not inferred from commit date."})
        events.append({"stage":"archive_source_discrepancies", "status":"flagged", "rows":sum(e["relationship_evidence"] != "both_directions" for e in connections), "message":"One-sided source links are retained and flagged. Missing landing details use exact original country-membership keys where available, never inferred countries."})
    if use_context:
        if args.acquire:
            html_rows, context_source, context_records = ofca.acquire_context(ROOT / "data/external/ofca/raw")
        elif replay:
            context_record, data = retained(ofca.PAGE)
            terms_record, terms = retained(ofca.TERMS)
            ofca.verify_terms(terms.decode("utf-8"))
            html_rows = ofca.parse_context(data.decode("utf-8"), context_record["sha256"])
            context_source = ofca.source(context_record.get("retrieved_at"), html_rows)
            context_records = [context_record, terms_record]
        else:
            raise ValueError("Enabled HTML context needs --acquire or --replay-release.")
        downloads.extend(context_records)
        sources.append(context_source)
        events.append({"stage":"html_observations", "status":"acquired", "rows":len(html_rows), "message":"Named cable entries extracted from OFCA HTML prose and reconciled against its published count. Not HTML table rows, global inventory or fault events."})
    if snapshot_meta:
        downloads.append(snapshot_meta)
        wb.update(status="acquired", source_url=snapshot_meta["source_url"], license=snapshot_meta["license"], license_url=snapshot_meta["license_url"], period=snapshot_meta["snapshot_date"] or "Snapshot date unknown",
                  file_or_endpoint=snapshot_meta["source_url"], version="Snapshot SHA-256 " + snapshot_meta["sha256"], original_format=Path(snapshot_meta["raw_path"]).suffix.lstrip("."))
    events.append({"stage": "infrastructure", "status": "acquired" if infrastructure else "blocked", "rows": len(infrastructure),
                   "message": "Verified unchanged, licensed infrastructure snapshot loaded." if infrastructure else "No licensed infrastructure snapshot configured. Catalog links are not cable observations; obtain the official resource and reuse rights first."})
    token = load_token() if args.acquire else ""
    configured_areas = gfw["areas"]
    if gfw.get("region_selection"):
        if gfw["region_selection"] != "all_official_eez_regions" or configured_areas or settings.get("landing_area_buffers"):
            raise ValueError("Global EEZ selection cannot silently mix arbitrary regions or landing buffers.")
        if args.acquire:
            configured_areas, region_record = gfw_regions.acquire_regions(token,ROOT / "data/external/global_fishing_watch/raw")
        elif replay:
            region_record, data = retained(gfw_regions.ENDPOINT)
            configured_areas = gfw_regions.parse_regions(data,region_record)
        else:
            raise ValueError("Global official region selection requires live acquisition or a verified complete replay manifest.")
        downloads.append(region_record)
        events.append({"stage":"gfw_geographies","status":"acquired","rows":len(configured_areas),"message":"All officially listed EEZ context regions selected before examining activity. Joint/overlapping areas retained separately; high seas excluded."})
    areas = prepare_areas(configured_areas, infrastructure, settings.get("landing_area_buffers"))
    activity, gfw_downloads, gfw_events = [], [], []
    if (args.acquire and token or replay) and areas:
        def report_progress(event):
            if event["completed_queries"] % 10 == 0 or event["status"] == "blocked":
                print(json.dumps({"gfw_progress":event}),flush=True)
        activity, gfw_downloads, gfw_events = acquire_reports(gfw, areas, token, ROOT / "data/external/global_fishing_watch/raw",offline=bool(replay),progress=report_progress,retained=replay["downloads"] if replay else None)
        downloads.extend(gfw_downloads)
        events.extend(gfw_events)
    else:
        reasons = []
        if not args.acquire: reasons.append("Network acquisition not requested")
        if not token: reasons.append("Personal GFW token not configured")
        if not areas: reasons.append("Documented study areas not configured")
        events.append({"stage": "gfw_report", "status": "blocked", "rows": 0, "message": "; ".join(reasons) + ". No GFW website scraping or replacement activity records."})
    source_gfw = {**GFW_SOURCE, "access_date": max(r["retrieved_at"] for r in gfw_downloads) if gfw_downloads else None,
                  "metadata_updated": None, "period": gfw["start_date"] + " to " + gfw["end_date"] + " (end exclusive; requested, not proof of coverage)",
                  "status": "acquired_partial" if activity and any(e["status"]=="blocked" for e in gfw_events) else "acquired" if activity else "blocked",
                  "coverage":f"{len(areas)} requested official/study regions. AIS-covered vessels only; high seas outside EEZ coverage; joint and overlapping regions are not additive."}
    summary = integrate_activity(infrastructure, areas, activity)
    fields = dictionary()
    complete = bool(infrastructure and activity and len(gfw_events)==len(areas)*len(gfw["datasets"]) and all(e["status"] in ("acquired", "no_records_returned") for e in gfw_events))
    runtime = {"python": platform.python_version(), "parser_version": "3"}
    if any(area.get("geometry") for area in areas):
        runtime["shapely"] = version("shapely")
    if settings.get("landing_area_buffers"):
        runtime["pyproj"] = version("pyproj")
    core = {"schema_version": 1, "created_at": now(), "runtime": runtime,
            "status": "available" if complete else "partial" if infrastructure or activity else "blocked",
            "empirical_analysis_available": complete, "scope": "Independent empirical infrastructure and maritime exposure, not external fault-model validation",
            "sources": sources + [source_gfw], "catalog_resources": resources, "infrastructure": infrastructure,
            "world_bank_infrastructure": wb_infrastructure, "cable_systems": cables, "cable_landings": connections, "html_observations": html_rows,
            "geographies": areas, "activity": activity, "summary": summary, "infrastructure_summary": infrastructure_summary(infrastructure),
            "variables": fields, "events": events, "limitations": LIMITATIONS,
            "configuration": {"gfw": {k:gfw.get(k, "") for k in ("start_date", "end_date", "datasets", "period_rationale", "region_selection")},
                              "historical_archive": use_archive, "html_context": use_context,
                              "infrastructure_snapshot_date": settings["infrastructure"].get("snapshot_date") if settings.get("infrastructure") else None},
            "counts": {"catalog_resources": len(resources), "infrastructure": len(infrastructure), "activity": len(activity), "geographies": len(areas),
                       "cable_systems": len(cables), "cable_landings": len(connections), "html_observations": len(html_rows)}}
    sha = digest(canonical(core))
    payload = {**core, "release_id": "external-" + sha[:16], "manifest_sha256": sha}
    validate_publication(payload)
    verify_raw_manifest(downloads)
    write_json(output / "research.json", payload)
    write_json(output / "external_data_quality_report.json", {"release_id": payload["release_id"], "counts": payload["counts"], "analysis_available": complete,
               "raw_hashes_verified": True,
               "gfw_coverage": {"planned_region_metric_checks":len(areas)*len(gfw['datasets']),"attempted_checks":len(gfw_events),
                 "returned_record_checks":sum(e['status']=='acquired' for e in gfw_events),"no_records_checks":sum(e['status']=='no_records_returned' for e in gfw_events),
                 "failed_checks":sum(e['status']=='blocked' for e in gfw_events),"not_attempted_checks":len(areas)*len(gfw['datasets'])-len(gfw_events),
                 "retained_response_snapshots":len(gfw_downloads),"hours_imputed_for_missing_records":False},
               "duplicate_policy": "Reject ambiguous duplicate source keys; do not silently drop or average records", "imputation": "No missing identities, coordinates, activity or faults are manufactured", "events": events})
    outputs = {
        "external_source_registry.csv": (payload["sources"], list(wb)),
        "external_data_dictionary.csv": (fields, list(fields[0])),
        "scraped_catalog_resources.csv": (resources, ["resource_id", "source_id", "name", "description", "source_url", "format", "download_available", "resource_license", "record_kind", "access_date", "html_sha256"]),
        "cleaned_world_bank_infrastructure.csv": (wb_infrastructure, ["id", "name", "country", "latitude", "longitude", "record_kind", "source_id", "snapshot_date", "coordinate_precision"]),
        "cleaned_infrastructure.csv": (infrastructure, ["id", "name", "country", "latitude", "longitude", "record_kind", "source_id", "snapshot_date", "coordinate_precision", "location_to_be_determined", "detail_record_available", "country_assignment"]),
        "historical_cable_systems.csv": (cables, ["id", "name", "length_reported", "rfs_reported", "owners_reported", "suppliers_reported", "landing_point_count", "source_id", "status_interpretation"]),
        "historical_cable_landings.csv": (connections, ["cable_id", "landing_id", "source_id", "relationship_evidence"]),
        "scraped_ofca_systems.csv": (html_rows, ["observation_id", "system_name_reported", "country", "reference_period", "source_id", "record_kind", "extraction_method", "html_sha256", "source_url", "source_text_quality", "interpretation"]),
        "cleaned_gfw_activity.csv": (activity, ["area_id", "country", "period_start", "period_end", "year", "metric", "value", "unit", "source_id", "dataset", "coverage_status", "raw_sha256"]),
        "external_empirical_summary.csv": (summary, ["area_id", "country", "period_start", "period_end", "year", "metric", "value", "unit", "source_id", "dataset", "coverage_status", "raw_sha256", "infrastructure_records", "infrastructure_source_ids", "linkage", "buffer_km", "interpretation"]),
        "external_geographies.csv": (areas,["id","name","country","region_category","iso3","territory_label","sovereignty_iso_codes","region","region_metadata_sha256","region_metadata_url","definition"]),
    }
    for name, (rows, columns) in outputs.items():
        write_csv(output / name, rows, columns)
    packages = archive_download_bundle(output, downloads) if cables else {}
    provider_files = [("world_bank", "cleaned_world_bank_infrastructure.csv"), ("global_fishing_watch", "cleaned_gfw_activity.csv")]
    if use_archive:
        provider_files.append(("open_undersea_cable_map", "cleaned_infrastructure.csv"))
    if use_context:
        provider_files.append(("ofca", "scraped_ofca_systems.csv"))
    for provider, filename in provider_files:
        data_dir = ROOT / "data/external" / provider / "processed" / payload["release_id"]
        data_dir.mkdir(parents=True)
        provider_exports = [filename] + (["historical_cable_systems.csv", "historical_cable_landings.csv"] if provider == "open_undersea_cable_map" else ["external_geographies.csv"] if provider == "global_fishing_watch" else [])
        for name in provider_exports:
            with (data_dir / name).open("xb") as stream:
                stream.write((output / name).read_bytes())
        write_json(ROOT / "data/external" / provider / "metadata" / (payload["release_id"] + ".json"),
                   {"release_id": payload["release_id"], "source": next(s for s in payload["sources"] if s["source_id"] == provider),
                    "observation_rows": len(outputs[filename][0]),
                    "observations_available": bool(outputs[filename][0]),
                    "processed_sha256": digest((output / filename).read_bytes()),
                    "processed_exports": {name:digest((output / name).read_bytes()) for name in provider_exports}})
    derived_dir = ROOT / "data/derived/external_empirical" / payload["release_id"]
    derived_dir.mkdir(parents=True)
    with (derived_dir / "external_empirical_summary.csv").open("xb") as stream:
        stream.write((output / "external_empirical_summary.csv").read_bytes())
    write_json(output / "acquisition_manifest.json", {"release_id": payload["release_id"], "downloads": downloads, "events": events,
               "exports": {name:digest((output / name).read_bytes()) for name in outputs},
               "packages": packages,
               "original_evidence_unchanged": verify_historical_evidence(protocol["protected_sha256"])})
    if args.export_website:
        export_website(payload, output)
    print(json.dumps({"output": str(output), "release_id": payload["release_id"], "status": payload["status"], "counts": payload["counts"], "event_counts":{status:sum(e["status"]==status for e in events) for status in {e["status"] for e in events}},"events":events if len(events)<25 else "Full events retained in acquisition_manifest.json"}, indent=2))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=ROOT / "config/external_empirical.json")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--acquire", action="store_true", help="Explicitly enable World Bank HTML and authorized GFW API requests")
    parser.add_argument("--catalog-snapshot", type=Path, help="Replay retained World Bank HTML without network")
    parser.add_argument("--replay-release", type=Path, help="Verify and reprocess retained raw infrastructure/HTML without network or credentials")
    parser.add_argument("--export-website", action="store_true", help="Update separate generated external website assets, never the original synthetic release")
    args = parser.parse_args()
    if sum(bool(v) for v in (args.acquire, args.catalog_snapshot, args.replay_release)) > 1:
        parser.error("Choose live acquisition OR offline replay, not both")
    run(args)
