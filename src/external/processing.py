"""Strict empirical records and explicit geographical linkage; no fault target."""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .common import ROOT, digest


def number(value, *, minimum=None, maximum=None):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a measurement.")
    n = float(value)
    if not math.isfinite(n) or (minimum is not None and n < minimum) or (maximum is not None and n > maximum):
        raise ValueError("Measurement is non-finite or out of range.")
    return n


def genuine_key(value):
    key = str(value or "").strip()
    if not key or re.search(r"\bCAB\d{4,}\b", key, re.I):
        raise ValueError("Empirical records require a supplied genuine key, never synthetic CAB identifiers.")
    return key


def reject_target_fields(row: dict):
    if any(k in row for k in ("fault_next_year", "fault_this_year", "predicted_risk", "model_probability")):
        raise ValueError("The empirical exposure layer does not accept fault targets or synthetic predictions.")


def validate_dates(start: str, end: str):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if a >= b or a.year < 2012 or b > date.today():
        raise ValueError("GFW requires a completed historical period from 2012, with an exclusive end date.")
    return a, b


def load_infrastructure(spec: dict | None) -> tuple[list[dict], dict | None]:
    if not spec:
        return [], None
    required = ("path", "source_url", "license", "license_url", "snapshot_date", "unit_of_analysis", "field_map", "sha256")
    if any(k not in spec for k in required) or spec.get("reuse_confirmed") is not True or spec.get("redistribution_confirmed") is not True:
        raise ValueError("An infrastructure snapshot needs complete provenance and confirmed reuse/redistribution rights.")
    if spec["unit_of_analysis"] not in ("landing_point", "cable_system", "country"):
        raise ValueError("Declare the actual source record unit.")
    if not spec["license"].strip() or not spec["license_url"].startswith("https://") or not spec["source_url"].startswith("https://"):
        raise ValueError("Source and license URLs are required.")
    host = urlparse(spec["source_url"]).hostname or ""
    if not (host == "worldbank.org" or host.endswith(".worldbank.org")):
        raise ValueError("World Bank adapter requires an official World Bank source URL; alternatives require an explicit adapter/scope review.")
    if spec["snapshot_date"]:
        date.fromisoformat(spec["snapshot_date"])
    path = (ROOT / spec["path"]).resolve()
    raw_root = (ROOT / "data/external/world_bank/raw").resolve()
    if not path.is_relative_to(raw_root) or not path.is_file():
        raise ValueError("Place the unchanged acquired snapshot inside data/external/world_bank/raw/.")
    raw = path.read_bytes()
    if digest(raw) != spec["sha256"]:
        raise ValueError("Infrastructure snapshot does not match its declared checksum.")
    if path.suffix.lower() == ".csv":
        records = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    elif path.suffix.lower() in (".json", ".geojson"):
        value = json.loads(raw)
        if value.get("type") != "FeatureCollection":
            raise ValueError("Expected GeoJSON FeatureCollection.")
        records = []
        for feature in value["features"]:
            row = dict(feature.get("properties") or {})
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Point":
                raise ValueError("This adapter accepts genuine points only; route geometry needs a separate reviewed adapter.")
            coords = geometry["coordinates"]
            row["__longitude"], row["__latitude"] = coords[:2]
            records.append(row)
    else:
        raise ValueError("Infrastructure adapter supports CSV or point GeoJSON only.")
    cleaned, seen = [], set()
    mapping = spec["field_map"]
    for row in records:
        reject_target_fields(row)
        get = lambda key: row.get(mapping.get(key, key))
        key = genuine_key(get("id"))
        if key in seen:
            raise ValueError("Duplicate infrastructure keys require a documented source-specific reconciliation; none was dropped silently.")
        seen.add(key)
        lat = number(row.get("__latitude", get("latitude")), minimum=-90, maximum=90)
        lon = number(row.get("__longitude", get("longitude")), minimum=-180, maximum=180)
        if (lat is None) != (lon is None):
            raise ValueError("A coordinate pair must be complete or entirely missing.")
        country = str(get("country") or "").strip()
        name = str(get("name") or "").strip()
        if not name or not country:
            raise ValueError("Source name and country are required; no geocoding or invented names.")
        cleaned.append({"id": key, "name": name, "country": country, "latitude": lat, "longitude": lon,
                        "record_kind": spec["unit_of_analysis"], "source_id": "world_bank",
                        "snapshot_date": spec["snapshot_date"] or None,
                        "coordinate_precision": spec.get("coordinate_precision", "Not established")})
    if not cleaned:
        raise ValueError("Infrastructure snapshot contains no records.")
    return cleaned, {"source_url": spec["source_url"], "sha256": digest(raw), "raw_path": str(path.relative_to(ROOT)).replace("\\", "/"), "license": spec["license"], "license_url": spec["license_url"], "snapshot_date": spec["snapshot_date"], "rows": len(cleaned)}


def prepare_areas(configured: list[dict], infrastructure: list[dict], buffer_spec: dict | None = None) -> list[dict]:
    areas = [dict(area) for area in configured]
    if buffer_spec:
        if not buffer_spec.get("justification") or not buffer_spec.get("snapshot_alignment_note"):
            raise ValueError("Landing-area buffers need a justification and explicit snapshot alignment note.")
        from pyproj import CRS, Transformer
        from shapely.geometry import Point, mapping
        from shapely import transform
        distances = buffer_spec.get("distances_km", [])
        if not distances or len(distances) != len(set(distances)):
            raise ValueError("Supply distinct, justified buffer distances for sensitivity.")
        for site in infrastructure:
            if site["record_kind"] != "landing_point" or site["latitude"] is None:
                continue
            lat, lon = site["latitude"], site["longitude"]
            if abs(lat) > 80 or abs(lon) > 175:
                raise ValueError("Polar/antimeridian buffers require a separately reviewed geometry treatment.")
            crs = CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs")
            back = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform
            for distance in distances:
                km = number(distance, minimum=0.1, maximum=100)
                polygon = transform(Point(0, 0).buffer(km * 1000, quad_segs=64), back, interleaved=False)
                areas.append({"id": f"landing:{site['id']}:{km:g}km", "name": f"{site['name']} ({km:g} km area)",
                              "country": site["country"], "infrastructure_ids": [site["id"]], "buffer_km": km,
                              "geometry": mapping(polygon), "crs": crs.to_string(),
                              "definition": buffer_spec["justification"] + " " + buffer_spec["snapshot_alignment_note"] + " Coastal proxy including land, not a physical cable-risk zone; no area density computed."})
    seen = set()
    keys = {site["id"] for site in infrastructure}
    for area in areas:
        genuine_key(area.get("id"))
        if area["id"] in seen or not area.get("name") or not area.get("country") or not area.get("definition"):
            raise ValueError("Study areas require unique IDs, name, country and a documented definition.")
        seen.add(area["id"])
        if bool(area.get("geometry")) == bool(area.get("region")):
            raise ValueError("Each area must specify exactly one custom polygon or official GFW region.")
        if area.get("geometry"):
            validate_polygon(area["geometry"])
        else:
            region = area["region"]
            if not isinstance(region.get("dataset"), str) or not isinstance(region.get("id"), str):
                raise ValueError("Official GFW region dataset and ID are required.")
        if not set(area.get("infrastructure_ids", [])).issubset(keys):
            raise ValueError("Study area refers to infrastructure not present in the acquired snapshot.")
    return areas


def validate_polygon(geometry: dict):
    if geometry.get("type") != "Polygon":
        raise ValueError("Study area adapter currently supports Polygon only.")
    for ring in geometry.get("coordinates", []):
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("Polygon rings must be closed with at least four coordinates.")
        for lon, lat in ring:
            if number(lon, minimum=-180, maximum=180) is None or number(lat, minimum=-90, maximum=90) is None:
                raise ValueError("Polygon coordinates cannot be missing.")
    if not geometry.get("coordinates"):
        raise ValueError("Empty polygon.")
    from shapely.geometry import shape
    polygon = shape(geometry)
    if not polygon.is_valid or polygon.is_empty or polygon.area <= 0:
        raise ValueError("Invalid, self-intersecting or zero-area study polygon.")


def infrastructure_summary(records: list[dict]) -> list[dict]:
    counts = Counter((r["country"], r["record_kind"]) for r in records)
    return [{"country": country, "record_kind": kind, "records": count} for (country, kind), count in sorted(counts.items())]


def integrate_activity(infrastructure: list[dict], areas: list[dict], activity: list[dict]) -> list[dict]:
    area_index = {area["id"]: area for area in areas}
    output = []
    for row in activity:
        reject_target_fields(row)
        area = area_index[row["area_id"]]
        linked = area.get("infrastructure_ids")
        if not linked:
            linked = [r["id"] for r in infrastructure if r["country"] == area["country"]]
        output.append({**row, "infrastructure_records": len(linked),
                       "infrastructure_source_ids": sorted({r["source_id"] for r in infrastructure if r["id"] in set(linked) and r.get("source_id")}),
                       "linkage": "documented_landing_area" if area.get("infrastructure_ids") else "country_context" if linked else "unlinked_activity",
                       "buffer_km": area.get("buffer_km"),
                       "interpretation": "Maritime exposure only; not faults, fault probabilities or validation of the synthetic model."})
    return output
