"""Native Word read-only export plus current managed canonical rasterizer.

No user LibreOffice is used. The owned Word application stays hidden, macros
are disabled, documents open read-only and never save, and owned objects close.
"""
import argparse
import importlib.util
from pathlib import Path

from build_finals_revision import PAPER, ROOT, sha

DEPENDENCIES=Path('C:/Users/Vincent/.cache/codex-runtimes/codex-primary-runtime/dependencies')
RENDERER=Path('C:/Users/Vincent/.codex/plugins/cache/openai-primary-runtime/documents/26.1030.10813/skills/documents/render_docx.py')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--input',type=Path,default=PAPER);parser.add_argument('--layout-only',action='store_true');parser.add_argument('--dpi',type=int,default=105)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    paper=args.input.resolve()
    adapter=load('owned_word_export',ROOT/'deliverables/finals_2026-11-02/_build/render_with_word.py')
    before=sha(paper)
    if args.layout_only:
        result,_=adapter.word_export(str(paper),None,str(args.output.resolve()),paper.stem)
        print(result,flush=True)
    else:
        renderer=load('canonical_revision_renderer',RENDERER)
        renderer.convert_to_pdf=adapter.word_export
        original=renderer.convert_from_path
        renderer.convert_from_path=lambda *a,**kw:original(*a,poppler_path=str(DEPENDENCIES/'native/poppler/Library/bin'),**kw)
        paths=renderer.rasterize(str(paper),str(args.output),args.dpi,verbose=False,emit_pdf=True)
        print(f'Rendered {len(paths)} pages with native read-only Word and bundled Poppler.',flush=True)
    assert sha(paper)==before


if __name__=='__main__':main()
