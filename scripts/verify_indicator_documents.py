"""Verify revised paper fidelity, numbering, content and chapter spacing."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

from docx import Document
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.revise_indicator_documents import META, NEW_HEADINGS, STAGES, capture_preserved, locate, new_path, norm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", required=True, type=Path)
    parser.add_argument("--check-pages", action="store_true")
    parser.add_argument("--revision", choices=["indicator", "rationale"], default="indicator")
    args = parser.parse_args()
    if args.revision == "rationale":
        from scripts.revise_research_rationale import META as selected_meta, new_path as selected_path, RATIONALE_HEADINGS
    else:
        selected_meta, selected_path = META, new_path
    manifest = json.loads(selected_meta.read_text(encoding="utf-8"))
    result = {}
    errors = []
    for stage in STAGES:
        info = manifest[stage]
        source = Path(info["source"])
        path = selected_path(stage)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == info["source_sha256"]
        assert capture_preserved(path) == info["preserved_parts"]
        with ZipFile(path) as archive:
            assert archive.testzip() is None
        doc = Document(path)
        assert len(doc.sections) == len(Document(source).sections)
        assert doc.styles["Normal"].font.name == "Times New Roman"
        assert doc.styles["Normal"].font.size.pt == 12
        assert doc.styles["Normal"].paragraph_format.line_spacing == 2
        for section in doc.sections:
            assert abs(section.page_width.cm - 21) < 0.03
            assert abs(section.page_height.cm - 29.7) < 0.03
            assert all(abs(m.inches - 1) < .02 for m in [section.top_margin, section.bottom_margin, section.left_margin, section.right_margin])
        raw_text = " ".join(p.text for p in doc.paragraphs)
        assert "synthetic" in raw_text.lower()
        assert NEW_HEADINGS[1] in raw_text and NEW_HEADINGS[3] in raw_text
        if args.revision == "rationale":
            assert all(label in raw_text for label in RATIONALE_HEADINGS[:2])
            assert "World Bank. (2025, July 2)" in raw_text
            assert "International Telecommunication Union. (2022, February 10)" in raw_text
        for paragraph in doc.paragraphs:
            if paragraph.text in NEW_HEADINGS.values() and "\t" not in paragraph.text:
                assert all(run.font.name == "Times New Roman" for run in paragraph.runs)
        tables = [p.text for p in doc.paragraphs if re.match(r"^Table\s+\d+\.\s*", p.text)]
        assert all(p.paragraph_format.keep_with_next for p in doc.paragraphs if p.text in tables)
        assert [int(re.match(r"Table (\d+)", t).group(1)) for t in tables] == list(range(1, len(tables) + 1))
        source_rubrics = [[cell.text for row in t.rows for cell in row.cells] for t in Document(source).tables[-3:]]
        output_rubrics = [[cell.text for row in t.rows for cell in row.cells] for t in doc.tables[-3:]]
        assert source_rubrics == output_rubrics
        pdf = pymupdf.open(args.pdf_dir / stage / f"{path.stem}.pdf")
        first = next(i for i, p in enumerate(pdf) if "CHAPTER I:" in p.get_text() and "Submarine fiber-optic cables form" in p.get_text())
        gaps = []
        for i in range(first, len(pdf)):
            page = pdf[i]
            text = page.get_text()
            assert len(norm(text)) > 50, f"Blank page: {stage} {i + 1}"
            assert any(72 <= block[1] and block[3] < 780 and norm(block[4])
                       for block in page.get_text("blocks")), f"Header/footer-only page: {stage} {i + 1}"
            assert "\ufffd" not in text
            assert abs(page.rect.width - 595.3) < 2 and abs(page.rect.height - 841.9) < 2
            footer_numbers = [span for block in page.get_text("dict")["blocks"] if "lines" in block
                              for line in block["lines"] for span in line["spans"]
                              if span["bbox"][1] > 800 and span["text"].strip().isdigit()]
            assert len(footer_numbers) == 1 and footer_numbers[0]["text"].strip() == str(i - first + 1), f"Footer numbering drift: {stage} {i + 1}"
            assert footer_numbers[0]["size"] == 12 and "TimesNewRoman" in footer_numbers[0]["font"]
            for block in page.get_text("blocks"):
                assert block[2] <= page.rect.width + 1
            match = re.search(r"CHAPTER (II|III|IV|V|VI):", text)
            if not match:
                continue
            chapter_block = next(b for b in page.get_text("blocks") if match.group(0) in b[4])
            assert chapter_block[1] < 120
            prior = pdf[i - 1]
            bottom = max(b[3] for b in prior.get_text("blocks") if b[1] > 75 and b[3] < 780)
            gap = prior.rect.height - 72 - bottom
            gaps.append({"chapter": match.group(1), "physical_start": i + 1, "previous_gap_pt": round(gap, 1)})
            if gap > 96:
                errors.append(f"{stage}: chapter {match.group(1)} gap {gap:.1f} pt before page {i + 1}")
        if args.revision == "rationale" or stage in ("master", "final"):
            ending_heading = "DATA DICTIONARY" if stage == "prelim" else "UPDATED DATA DICTIONARY AND DATA-QUALITY REPORT" if stage == "midterm" else "REFERENCES"
            reference_page = locate(pdf, ending_heading, first)
            prior = pdf[reference_page - 1]
            bottom = max(b[3] for b in prior.get_text("blocks") if b[1] > 75 and b[3] < 780)
            gap = prior.rect.height - 72 - bottom
            last_chapter = "III" if stage == "prelim" else "IV" if stage == "midterm" else "VI"
            gaps.append({"chapter": last_chapter + " end", "physical_start": reference_page + 1, "previous_gap_pt": round(gap, 1)})
            if gap > 96:
                errors.append(f"{stage}: chapter {last_chapter} ending gap {gap:.1f} pt before {ending_heading}")
        if args.check_pages:
            assert len(pdf) == info["physical_pages"]
            assert first + 1 == info["physical_body_start"]
            toc_numbers = []
            in_toc = False
            for paragraph in doc.paragraphs:
                if paragraph.text == "TABLE OF CONTENTS":
                    in_toc = True
                elif paragraph.text.startswith("CHAPTER I:") and "\t" not in paragraph.text:
                    break
                if in_toc and "\t" in paragraph.text and paragraph.runs[-1].text.isdigit():
                    toc_numbers.append(int(paragraph.runs[-1].text))
            assert toc_numbers == sorted(toc_numbers), f"Contents order does not match body: {stage}"
            for label, numbered in info["page_map"].items():
                wanted = label.split(":", 1)[1].strip() if label.startswith("CHAPTER ") else label
                if re.match(r"^\d+\.", wanted):
                    for kind in ("Table", "Figure"):
                        caption = f"{kind} " + re.sub(r"^(\d+)\.\s*", r"\1. ", wanted)
                        try:
                            caption_page = locate(pdf, caption, first)
                        except ValueError:
                            continue
                        assert caption_page - first + 1 == numbered, f"Caption map drift: {stage} {label}"
                        break
                    else:
                        raise AssertionError(f"Caption missing: {stage} {label}")
                    continue
                assert locate(pdf, wanted, first) - first + 1 == numbered, f"Map drift: {stage} {label}"
        result[stage] = {"pages": len(pdf), "tables": len(tables), "chapter_transitions": gaps}
    report = {"status": "PASS" if not errors else "LAYOUT ITERATION REQUIRED", "documents": result, "errors": errors}
    target = selected_meta.parent / "structural_qa.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
