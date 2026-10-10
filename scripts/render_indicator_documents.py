"""Run the document skill renderer with Windows/PyMuPDF adapters.

Keeps the packaged render_docx conversion and file lifecycle, while correcting
Windows profile URIs and using installed PyMuPDF instead of absent Poppler.
QA images/PDFs remain internal under deliverables/review/indicator_revision.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess

import pymupdf
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SKILL_RENDERER = Path("C:/Users/Vincent/.codex/plugins/cache/openai-primary-runtime/documents/26.802.11031/skills/documents/render_docx.py")
SOFFICE = Path("C:/Program Files/LibreOffice/program/soffice.com")


def windows_run(cmd, env, verbose):
    command = list(cmd)
    command[0] = str(SOFFICE)
    for i, arg in enumerate(command):
        if arg.startswith("-env:UserInstallation=file://"):
            command[i] = "-env:UserInstallation=" + Path(arg.split("file://", 1)[1]).resolve().as_uri()
    return subprocess.run(command, check=False, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, env=env,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def mupdf_convert(path, *, dpi, output_folder, **kwargs):
    paths = []
    with pymupdf.open(path) as pdf:
        for i, page in enumerate(pdf, 1):
            destination = Path(output_folder) / f"page0001-{i:03}.png"
            page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), alpha=False).save(destination)
            paths.append(str(destination))
    return paths


def contact_sheets(output, pages):
    directory = output / "contact_sheets"
    directory.mkdir(parents=True, exist_ok=True)
    for batch in range(0, len(pages), 12):
        sheet = Image.new("RGB", (1800, 1944), "#b9b9b9")
        draw = ImageDraw.Draw(sheet)
        for offset, path in enumerate(pages[batch:batch + 12]):
            x, y = (offset % 4) * 450 + 12, (offset // 4) * 648 + 28
            with Image.open(path) as page:
                page.thumbnail((426, 603))
                sheet.paste(page, (x, y))
            draw.text((x, y - 18), f"Page {batch + offset + 1}", fill="black")
        sheet.save(directory / f"sheet_{batch // 12 + 1:02}.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", default="render1")
    parser.add_argument("--revision", choices=["indicator", "rationale", "course_format"], default="indicator")
    parser.add_argument("--stages", nargs="+", default=["master", "final", "midterm", "prelim"])
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("skill_renderer", SKILL_RENDERER)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    renderer._run_cmd = windows_run
    renderer.convert_from_path = mupdf_convert
    for stage in args.stages:
        document = ROOT / f"deliverables/{stage}/Undersea_Cable_Fault_Research_{stage.upper()}_{args.revision.upper()}_REVISED.docx"
        output = ROOT / f"deliverables/review/{args.revision}_revision/{args.iteration}/{stage}"
        pages = renderer.rasterize(str(document), str(output), 110, verbose=False, emit_pdf=True)
        contact_sheets(output, pages)
        print(f"{stage}: rendered {len(pages)} pages", flush=True)


if __name__ == "__main__":
    main()
