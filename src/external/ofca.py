"""Small permitted HTML context acquisition from the Hong Kong regulator.

Extract named-system list entries from prose, not invented HTML table rows.
No contact details, third-party map images or geocoded coordinates are exported.
"""
from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.robotparser import RobotFileParser

from .common import fetch, store_raw

PAGE = "https://www.ofca.gov.hk/en/industry_focus/infrastructures/submarine_cables/index.html"
TERMS = "https://www.ofca.gov.hk/en/important_notices/index.html"
HOSTS = {"www.ofca.gov.hk"}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("p", "br", "li", "div"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag in ("p", "li", "div"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def visible(html):
    parser = VisibleText()
    parser.feed(html)
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def parse_context(html: str, html_sha256: str):
    content = visible(html)
    match = re.search(r"As at ([A-Za-z]+ \d{4}), Hong Kong has (\w+) submarine cable systems, namely,?\s*(.*?)\.\s*Several other systems are being planned", content)
    if not match:
        raise ValueError("OFCA dated cable-list structure changed; inspect retained HTML.")
    period = datetime.strptime(match[1], "%B %Y").strftime("%Y-%m")
    words = {"ten":10, "eleven":11, "twelve":12, "thirteen":13, "fourteen":14, "fifteen":15,
             "sixteen":16, "seventeen":17, "eighteen":18, "nineteen":19, "twenty":20}
    count = int(match[2]) if match[2].isdigit() else words.get(match[2].lower())
    entries = [e.strip() for e in re.split(r",\s*|(?<=\))\s+and\s+", match[3])]
    if count != len(entries) or len(set(entries)) != len(entries) or any(len(e) < 3 for e in entries):
        raise ValueError("OFCA extracted systems do not reconcile to its explicit published count.")
    return [dict(observation_id=f"ofca:{period}:{i:02}", system_name_reported=name,
        country="Hong Kong", reference_period=period, source_id="ofca",
        record_kind="regulator_named_system", extraction_method="HTML prose list extraction",
        html_sha256=html_sha256, source_url=PAGE,
        source_text_quality="source_contains_replacement_character" if "\ufffd" in name else "source_contains_nonprinting_control" if re.search(r"[\x80-\x9f]",name) else "no_replacement_character",
        interpretation="Named as a cable system by OFCA for the stated month. Not a fault event, route geometry, historical-archive crosswalk, or current status beyond that month.")
        for i, name in enumerate(entries, 1)]


def verify_terms(html: str):
    text = visible(html)
    required = ("may be reproduced or re-disseminated for non-commercial use", "as the source of information is acknowledged")
    if not all(part in text for part in required):
        raise ValueError("OFCA noncommercial reuse terms not established in this acquisition.")


def source(access_date, rows):
    return dict(source_id="ofca", source_name="Landing of Submarine Cables in Hong Kong",
        publisher="Office of the Communications Authority, Hong Kong SAR Government",
        source_url=PAGE, license="OFCA-authored material: noncommercial reuse with attribution", license_url=TERMS,
        file_or_endpoint=PAGE, version="Retained HTML SHA-256", original_format="HTML prose list, not an HTML data table",
        access_date=access_date, metadata_updated=None, coverage="Hong Kong only; independent regional context",
        period=rows[0]["reference_period"], purpose="Substantive HTML-scraping demonstration and separately dated infrastructure context",
        status="html_records_acquired", limitations="A regional named-system list, not global coverage, individual fault data, exact locations or a verified join to the historical archive. Third-party images and contacts are not redistributed. Noncommercial use with OFCA attribution only.")


def acquire_context(raw_dir: Path):
    robots, rm = fetch("https://www.ofca.gov.hk/robots.txt", hosts=HOSTS)
    rp = RobotFileParser()
    rp.parse(robots.decode("utf-8").splitlines())
    if not all(rp.can_fetch("Group5-xam.py-academic-research", u) for u in (PAGE, TERMS)):
        raise ValueError("OFCA robots rules prohibit this acquisition.")
    records = [store_raw(raw_dir, robots, rm, ".robots.txt")]
    terms, tm = fetch(TERMS, hosts=HOSTS)
    records.append(store_raw(raw_dir, terms, tm, ".terms.html"))
    verify_terms(terms.decode("utf-8"))
    data, meta = fetch(PAGE, hosts=HOSTS)
    record = store_raw(raw_dir, data, meta, ".html")
    records.append(record)
    rows = parse_context(data.decode("utf-8"), record["sha256"])
    return rows, source(meta["retrieved_at"], rows), records
