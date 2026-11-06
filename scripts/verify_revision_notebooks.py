"""Execute read-only notebook copies with the caller's model-compatible kernel."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from review_research import protected_fingerprints

ROOT=Path(__file__).resolve().parents[1]


def main():
    before=protected_fingerprints()
    parent=ROOT/'tmp/notebook_verification';parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='executed-',dir=parent))
    kernel=work/'kernels/research-revision';kernel.mkdir(parents=True)
    (kernel/'kernel.json').write_text(json.dumps(dict(argv=[sys.executable,'-B','-m','ipykernel_launcher','-f','{connection_file}'],display_name='Research revision verification',language='python')),encoding='utf-8')
    previous=os.environ.get('JUPYTER_PATH')
    os.environ['JUPYTER_PATH']=str(work)+(os.pathsep+previous if previous else '')
    results=[]
    try:
        for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
            notebook=nbformat.read(path,as_version=4)
            nbformat.validate(notebook)
            client=NotebookClient(notebook,timeout=180,kernel_name='research-revision',resources={'metadata':{'path':str(ROOT)}})
            client.execute()
            nbformat.write(notebook,work/path.name)
            results.append(dict(notebook=path.name,status='executed without cell errors',execution_copy=str(work/path.name)))
            print(path.name,'passed',flush=True)
    finally:
        if previous is None:os.environ.pop('JUPYTER_PATH',None)
        else:os.environ['JUPYTER_PATH']=previous
    assert protected_fingerprints()==before
    report=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),notebooks=results,protected_evidence_unchanged=True,
                original_classifier_fit=False,final_test_inference=False,scope='Read-only notebook copies; separate development fitting verified by check_reproduction.py')
    (ROOT/'outputs/revisions/2026-11-05/notebook_execution.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
