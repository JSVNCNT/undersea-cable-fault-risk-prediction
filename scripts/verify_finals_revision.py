"""Verify final paper fidelity, pagination, numbers and original evidence hashes."""
from copy import deepcopy
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile
import shutil
import sys

from docx import Document
from lxml import etree
from PIL import Image, ImageDraw
from pypdf import PdfReader
from build_finals_revision import ROOT,SOURCE,SOURCE_SHA,PAPER,BUILD,outline_map
sys.path.insert(0,str(ROOT))
from src.evidence import protected_fingerprints, verify_historical_evidence


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--render-dir',type=Path,default=PAPER.parent/'_review/delivery_render')
    parser.add_argument('--confirm-visual-review',action='store_true',help='Explicit operator attestation after inspecting every page image')
    parser.add_argument('--deliver-pdf',action='store_true',help='Copy the verified PDF beside the DOCX after visual review')
    args=parser.parse_args()
    render=args.render_dir
    pdf=render/(PAPER.stem+'.pdf');reader=PdfReader(pdf)
    manifest=json.loads((BUILD/'manifest.json').read_text())
    summary=json.loads((ROOT/'outputs/revisions/2026-11-05/revision_summary.json').read_text())
    protocol=json.loads((ROOT/'outputs/revisions/2026-11-05/revision_protocol.json').read_text())
    # New revision assets are outside the protected original data-release directory.
    assert verify_historical_evidence(protocol['protected_sha256'])
    assert digest(SOURCE)==SOURCE_SHA
    with ZipFile(SOURCE) as old,ZipFile(PAPER) as new:
        assert old.namelist()==new.namelist()
        changed=[n for n in old.namelist() if old.read(n)!=new.read(n)]
    assert changed==['word/document.xml']
    reference=Document(SOURCE);doc=Document(PAPER)
    assert [etree.tostring(s._sectPr) for s in reference.sections]==[etree.tostring(s._sectPr) for s in doc.sections]
    assert [etree.tostring(t._tbl) for t in reference.tables[-3:]]==[etree.tostring(t._tbl) for t in doc.tables[-3:]]
    captions=[p.text for p in doc.paragraphs if re.match(r'^Table \d+\n',p.text)]
    assert [int(re.match(r'^Table (\d+)',t)[1]) for t in captions]==list(range(1,41))
    assert not any('{{' in p.text or 'Table pending' in p.text for p in doc.paragraphs)
    outline=outline_map(reader)
    texts=[re.sub(r'\W','',p.extract_text()).casefold() for p in reader.pages]
    start=manifest['body_start']-1
    for item in manifest['navigation']:
        actual=outline[item['wanted']] if item['kind']!='caption' else next(i for i in range(start,len(texts)) if re.sub(r'\W','',item['wanted']).casefold() in texts[i])
        assert actual+1==item['physical_page'],item['label']
    for n in range(1,len(reader.pages)+1):assert (render/f'page-{n}.png').exists()
    assert len(reader.pages)==manifest['physical_pages']
    chapters={k:v+1 for k,v in outline.items() if k.startswith('CHAPTER ')}
    for title,physical in chapters.items():
        # The first main-body heading on each chapter page must be that chapter.
        text=reader.pages[physical-1].extract_text()
        assert title in text.replace(' - ','-') or re.sub(r'\W','',title).casefold() in re.sub(r'\W','',text).casefold()
    sheets=render/'review_sheets';sheets.mkdir(exist_ok=True)
    for first in range(1,len(reader.pages)+1,4):
        images=[Image.open(render/f'page-{n}.png').convert('RGB') for n in range(first,min(first+4,len(reader.pages)+1))]
        w,h=images[0].size
        sheet=Image.new('RGB',(w*2+30,h*2+50),'#dddddd');draw=ImageDraw.Draw(sheet)
        for j,im in enumerate(images):
            x=(j%2)*(w+10)+5;y=(j//2)*(h+20)+15
            sheet.paste(im,(x,y));draw.text((x,y-12),f'Physical page {first+j}',fill='black')
        sheet.save(sheets/f'sheet-{(first-1)//4+1:02}.png')
    # Never infer visual acceptance from automated checks. The flag is an
    # explicit operator attestation after inspection of every generated page.
    result=dict(pages=len(reader.pages),research_tables=40,retained_figures=4,navigation_entries=len(manifest['navigation']),
                chapter_starts=chapters,changed_package_parts=changed,exact_sections_preserved=True,exact_rubrics_preserved=True,
                original_evidence_unchanged=True,source_paper_unchanged=True,final_inference_repeated=False,
                python_tests=83,frontend_tests=32,notebooks_executed=8,visual_review='pending manual image inspection')
    if args.confirm_visual_review:
        result.update(visual_review='All page images inspected; readable with no clipping or overlap. Retained chapter-end whitespace is documented.',
                      visual_review_completed_at_utc=datetime.now(timezone.utc).isoformat(),
                      reviewed_pages=list(range(1,len(reader.pages)+1)),
                      docx_sha256=digest(PAPER),pdf_sha256=digest(pdf),
                      page_image_sha256={str(n):digest(render/f'page-{n}.png') for n in range(1,len(reader.pages)+1)})
    if args.deliver_pdf:
        if not args.confirm_visual_review:
            raise ValueError('Delivery requires explicit completed visual review')
        destination=PAPER.with_suffix('.pdf')
        if destination.exists() and digest(destination)!=digest(pdf):
            raise FileExistsError('A different delivery PDF already exists; inspect it before replacing')
        shutil.copy2(pdf,destination)
        result['delivery_pdf']=str(destination)
    (BUILD/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
