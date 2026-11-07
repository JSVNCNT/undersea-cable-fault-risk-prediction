"""Official GFW EEZ-region definitions; no invented boundaries or country mapping."""
import json
import re

from .common import fetch, store_raw, digest

ENDPOINT = "https://gateway.api.globalfishingwatch.org/v3/datasets/public-eez-areas/context-layers"
DOCUMENTATION = "https://globalfishingwatch.org/our-apis/documentation/docs/v3/datasets/regions"


def parse_regions(data, metadata):
    rows = json.loads(data)
    if not isinstance(rows,list) or not rows:
        raise ValueError("Official EEZ metadata must be a nonempty list.")
    seen, areas = set(), []
    for row in rows:
        identity = str(row.get("id", ""))
        label = row.get("label")
        if not identity.isdigit() or identity in seen or not isinstance(label,str) or not label.strip():
            raise ValueError("Missing/duplicate official GFW region identifier or label.")
        seen.add(identity)
        joint = bool(row.get("isoSov2") or row.get("isoSov3") or re.search("overlap|joint",label,re.I))
        territory = row.get("territory1")
        # This is a SOURCE geographic label, not a spatial assignment of any
        # landing point to an EEZ. Joint regimes are never assigned one country.
        country = territory if isinstance(territory,str) and territory.strip() and not joint else label
        areas.append(dict(id="gfw-eez:"+identity,name=label,country=country,
            region={"dataset":"public-eez-areas","id":identity},
            region_category="joint_or_overlapping" if joint else "source_eez_region",
            iso3=row.get("iso3"),territory_label=territory,
            sovereignty_iso_codes=[row[k] for k in ("isoSov1","isoSov2","isoSov3") if row.get(k)],
            region_metadata_sha256=metadata["sha256"], region_metadata_url=ENDPOINT,
            definition=f"Official GFW public-eez-areas region {identity}: {label}. Full source EEZ region, not a cable corridor or landing buffer. Source label retained without country-name harmonization. Joint/overlapping regimes are separate and totals across regions must not be summed. High seas are outside this EEZ study. Definition source: {DOCUMENTATION}."))
    return sorted(areas,key=lambda r:(r["name"],r["id"]))


def acquire_regions(token, raw_dir):
    data,meta = fetch(ENDPOINT,hosts={"gateway.api.globalfishingwatch.org"},token=token)
    record = store_raw(raw_dir,data,{**meta,"method":"GET","purpose":"Official geographic definitions, not activity observations"},".regions.json")
    return parse_regions(data,record),record
