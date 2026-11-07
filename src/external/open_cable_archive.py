"""Pinned, noncommercial historical archive. No current licensed API is used.

One bounded repository archive supplies original GeoJSON, individual records,
and the historical reuse declaration together. ZIP members are read in memory,
never extracted to filesystem paths. Repository date is NOT observation date.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

from .common import fetch, store_raw
from .processing import genuine_key, number, reject_target_fields

REVISION = "e7903491e73bcac0d0b013b945897d10928483c4"
REPOSITORY = "https://github.com/stevesong/open_undersea_cable_map"
DOWNLOAD = f"https://codeload.github.com/stevesong/open_undersea_cable_map/zip/{REVISION}"
LICENSE = "https://creativecommons.org/licenses/by-nc-sa/3.0/"
SOURCE_ID = "open_undersea_cable_map"


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Historical archive missing required {field}; no value inferred.")
    return value.strip()


def parse_archive(raw: bytes, revision: str = REVISION):
    if revision != REVISION:
        raise ValueError("Archive revision must be explicitly reviewed before changing it.")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = [item for item in archive.infolist() if not item.is_dir()]
        if len(infos) > 10000 or sum(i.file_size for i in infos) > 64 * 1024 * 1024:
            raise ValueError("Historical archive exceeds bounded expansion limits.")
        prefix = f"open_undersea_cable_map-{revision}/"
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or any(not n.startswith(prefix) or ".." in n.split("/") for n in names):
            raise ValueError("Unexpected or ambiguous historical archive paths.")
        def read(name):
            return archive.read(prefix + name)
        rights = read("LICENSE").decode("utf-8")
        readme = read("README.md").decode("utf-8")
        if "Attribution-NonCommercial-ShareAlike 3.0" not in rights or "late 2022" not in readme or "CC BY-NC-SA 3.0" not in readme:
            raise ValueError("Historical archive license/vintage declaration changed; review required.")
        def objects(folder):
            records = {}
            for name in names:
                relative = name[len(prefix):]
                if re.fullmatch(folder + r"/[a-z0-9-]+\.json", relative) and not relative.endswith(("/all.json", "-geo.json")):
                    row = json.loads(archive.read(name))
                    if not isinstance(row, dict):
                        continue
                    reject_target_fields(row)
                    key = genuine_key(row.get("id"))
                    if relative != f"{folder}/{key}.json" or key in records:
                        raise ValueError("Historical archive key/file mismatch or duplicate.")
                    records[key] = row
            return records
        landings, systems = objects("landing-point"), objects("cable")
        country_lookup = {}
        for country in objects("country").values():
            for key in country.get("landing_points_in_country", []):
                if key in country_lookup and country_lookup[key] != country["name"]:
                    raise ValueError("Ambiguous source-country membership.")
                country_lookup[key] = country["name"]
        geo = json.loads(read("landing-point/landing-point-geo.json"))
        if geo.get("type") != "FeatureCollection" or not geo.get("features") or not systems:
            raise ValueError("Missing historical point collection or individual records.")
        points, seen = [], set()
        for feature in geo["features"]:
            props, geometry = feature.get("properties", {}), feature.get("geometry", {})
            key = genuine_key(props.get("id"))
            if key in seen or geometry.get("type") != "Point":
                raise ValueError("Ambiguous/missing landing identity or point geometry.")
            seen.add(key)
            detail_available = key in landings
            if not detail_available:
                if key not in country_lookup:
                    raise ValueError("GeoJSON point lacks both detail and exact source-country membership.")
                # Exact source-key join, not country guessing from name/coordinates.
                landings[key] = dict(id=key, name=props.get("name"), country=country_lookup[key], cables=[])
            original = landings[key]
            if props.get("name") != original.get("name"):
                raise ValueError("GeoJSON and landing detail names disagree.")
            coords = geometry.get("coordinates", [])
            if len(coords) != 2:
                raise ValueError("Expected one supplied longitude/latitude pair.")
            lon = number(coords[0], minimum=-180, maximum=180)
            lat = number(coords[1], minimum=-90, maximum=90)
            if lon is None or lat is None or not isinstance(props.get("is_tbd"), bool):
                raise ValueError("Missing supplied coordinates or location-certainty flag.")
            points.append(dict(id=key, name=text(original.get("name"), "name"),
                country=text(original.get("country"), "country"), latitude=lat, longitude=lon,
                record_kind="landing_point", source_id=SOURCE_ID, snapshot_date=None,
                coordinate_precision="Cartographic source coordinate; survey accuracy not established. Do not use for narrow hazard buffers.",
                location_to_be_determined=props["is_tbd"], detail_record_available=detail_available,
                country_assignment="individual_landing_record" if detail_available else "exact_source_country_membership"))
        # Some individually listed locations may not have plotted coordinates.
        # Retain them as genuinely missing, rather than discard or geocode them.
        for key in sorted(set(landings) - seen):
            original = landings[key]
            points.append(dict(id=key, name=text(original.get("name"), "name"),
                country=text(original.get("country"), "country"), latitude=None, longitude=None,
                record_kind="landing_point", source_id=SOURCE_ID, snapshot_date=None,
                coordinate_precision="Not plotted in the retained point collection; not geocoded by this project.",
                location_to_be_determined=None, detail_record_available=True, country_assignment="individual_landing_record"))
        cables, connections = [], []
        point_keys = {p["id"] for p in points}
        for key, row in sorted(systems.items()):
            linked = row.get("landing_points")
            if not isinstance(linked, list) or not linked:
                raise ValueError("Cable record missing supplied landing links.")
            linked_keys = [genuine_key(p.get("id")) for p in linked]
            if len(linked_keys) != len(set(linked_keys)) or not set(linked_keys) <= point_keys:
                raise ValueError("Cable landing keys ambiguous or missing from archive.")
            for landing in linked:
                if landing.get("country") != landings[landing["id"]].get("country"):
                    raise ValueError("Cable and landing country declarations disagree.")
                connections.append(dict(cable_id=key, landing_id=landing["id"], source_id=SOURCE_ID))
            cables.append(dict(id=key, name=text(row.get("name"), "cable name"),
                length_reported=row.get("length"), rfs_reported=row.get("rfs"),
                owners_reported=row.get("owners"), suppliers_reported=row.get("suppliers"),
                landing_point_count=len(linked_keys), source_id=SOURCE_ID,
                status_interpretation="Archived description only; not verified current operation"))
        # Independently compare both supplied directions. Retain genuine one-sided
        # links with an explicit flag; do not silently delete/repair source errors.
        forward = {(e["cable_id"], e["landing_id"]) for e in connections}
        reverse = {(genuine_key(c.get("id")), key) for key, row in landings.items() for c in row.get("cables", [])}
        if any(c not in systems or p not in point_keys for c,p in reverse):
            raise ValueError("Reverse source link has a missing cable or landing key.")
        connections = [dict(cable_id=c, landing_id=p, source_id=SOURCE_ID,
            relationship_evidence="both_directions" if (c,p) in forward & reverse else "cable_record_only" if (c,p) in forward else "landing_record_only")
            for c,p in sorted(forward | reverse)]
        for cable in cables:
            cable["landing_point_count"] = sum(e["cable_id"] == cable["id"] for e in connections)
        return sorted(points, key=lambda p: p["id"]), cables, connections


def acquire_archive(raw_dir: Path):
    data, meta = fetch(DOWNLOAD, hosts={"codeload.github.com"})
    record = store_raw(raw_dir, data, meta, ".zip")
    return replay_archive(data, meta["retrieved_at"]), record


def replay_archive(data: bytes, access_date):
    points, cables, connections = parse_archive(data)
    one_sided = sum(e["relationship_evidence"] != "both_directions" for e in connections)
    source = dict(source_id=SOURCE_ID, source_name="Open Undersea Cable Map (historical TeleGeography archive)",
        publisher="TeleGeography (original data); Steve Song (archive maintainer)", source_url=REPOSITORY,
        license="CC BY-NC-SA 3.0 (historical archive declaration)", license_url=LICENSE,
        file_or_endpoint=DOWNLOAD, version=REVISION, original_format="Unchanged repository ZIP containing GeoJSON and JSON",
        access_date=access_date, metadata_updated=None, coverage="Global historical inventory, not a current exhaustive network census",
        period="Maintainer describes late-2022 source vintage; individual observation dates unknown. Commit date is not snapshot date.",
        purpose="Historical infrastructure description and source-supplied cable/landing connectivity",
        status="acquired_historical", limitations=f"Noncommercial attribution and share-alike required. Derivative archive datasets retain CC BY-NC-SA 3.0; unrelated sources keep their own terms. Schematic coordinates are not surveyed cable routes. {one_sided} one-sided cable/landing relationships are retained and flagged, not silently repaired. No authenticated faults or current status.")
    return points, cables, connections, source
