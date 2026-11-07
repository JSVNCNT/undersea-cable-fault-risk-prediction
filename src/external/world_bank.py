"""Scrape official catalog HTML, not licensed third-party cable geodata."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser

from .common import fetch, store_raw

CATALOG = "https://datacatalog.worldbank.org/search/dataset/0037968/world-development-report-2021-maps-o-4-and-5-1"
TERMS = "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets"
HOSTS = {"datacatalog.worldbank.org"}


class CatalogHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_id = ""
        self.script_type = ""
        self.parts: list[str] = []
        self.scripts: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            a = dict(attrs)
            self.script_id, self.script_type = a.get("id", ""), a.get("type", "")
            self.parts = []

    def handle_data(self, data):
        if self.script_id or self.script_type:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.scripts.append((self.script_id, self.script_type, "".join(self.parts)))
            self.script_id = self.script_type = ""


def parse_catalog(html: str) -> tuple[dict, list[dict]]:
    parser = CatalogHTML()
    parser.feed(html)
    dataset = None
    linked = {}
    for identity, kind, content in parser.scripts:
        if identity == "__NEXT_DATA__":
            dataset = json.loads(content).get("props", {}).get("pageProps", {}).get("dataset")
        elif kind == "application/ld+json":
            value = json.loads(content)
            for item in value if isinstance(value, list) else [value]:
                if isinstance(item, dict) and item.get("@type") == "Dataset":
                    linked = item
    if not dataset or dataset.get("dataset_unique_id") != "0037968":
        raise ValueError("Catalog structure/identity changed; inspect the retained HTML before updating the parser.")
    license_value = linked.get("license", {})
    if not isinstance(license_value, dict):
        raise ValueError("Catalog license structure changed.")
    metadata = {"source_id": "world_bank", "source_name": dataset.get("name", ""), "publisher": "World Bank",
                "source_url": CATALOG, "license": license_value.get("name", "Not established"),
                "file_or_endpoint": CATALOG, "version": "Retained HTML checksum; infrastructure version not established",
                "original_format": "HTML with embedded public resource metadata",
                "license_url": license_value.get("url", TERMS), "metadata_updated": linked.get("dateModified", ""),
                "coverage": "Global catalog scope; actual infrastructure coverage not yet verified",
                "period": linked.get("temporalCoverage") or "Infrastructure observation date not established",
                "purpose": "Infrastructure source discovery; scraped rows are RESOURCE METADATA, not cable observations",
                "limitations": "Third-party cable geometry/license not established. Catalog update is not an infrastructure observation date."}
    rows = []
    for resource in dataset.get("Resources", []):
        rows.append({"resource_id": resource.get("resource_unique_id") or resource.get("resource_id"),
                     "source_id": "world_bank", "name": resource.get("name", "").strip(),
                     "description": resource.get("description", "").strip(),
                     "source_url": resource.get("url") or resource.get("website_url") or "",
                     "format": resource.get("rFormat") or resource.get("format") or "",
                     "download_available": resource.get("isDownload") is True,
                     "resource_license": resource.get("licenseInfo") or "Not established",
                     "record_kind": "catalog_resource_metadata"})
    if not rows or not metadata["source_name"]:
        raise ValueError("Official catalog has no extractable resource descriptors.")
    return metadata, rows


def acquire_catalog(raw_dir: Path) -> tuple[dict, list[dict], list[dict]]:
    robots_url = "https://datacatalog.worldbank.org/robots.txt"
    robots, robots_meta = fetch(robots_url, hosts=HOSTS)
    rp = RobotFileParser()
    rp.parse(robots.decode("utf-8", "strict").splitlines())
    if not rp.can_fetch("Group5-xam.py-academic-research", CATALOG):
        raise ValueError("Catalog robots rules do not permit this acquisition.")
    # Robots is a technical access check, not a license grant. Dataset-specific
    # permission and third-party rights still gate substantive data/publication.
    robots_record = store_raw(raw_dir, robots, robots_meta, ".robots.txt")
    data, meta = fetch(CATALOG, hosts=HOSTS)
    record = store_raw(raw_dir, data, meta, ".html")
    source, resources = parse_catalog(data.decode("utf-8", "strict"))
    source.update(access_date=meta["retrieved_at"], status="metadata_only")
    for row in resources:
        row.update(access_date=meta["retrieved_at"], html_sha256=record["sha256"])
    return source, resources, [robots_record, record]
