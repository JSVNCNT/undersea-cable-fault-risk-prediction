"""Dry-run-first independent empirical publication. Never runs SQL or imports synthetic rows.

python website/scripts/import_external_supabase.py
python website/scripts/import_external_supabase.py --publish
Metadata-only/incomplete releases additionally need --allow-incomplete-status.
Uses the existing private admin configuration only when --publish is explicit.
"""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.run_external_pipeline import validate_publication
from import_supabase import load_admin_credentials
from src.external.common import RestrictedRedirect


def request(url,key,path,method='GET',body=None,headers=None):
    """Administrator requests never forward credentials across an HTTP redirect."""
    combined={'apikey':key,'Content-Type':'application/json',**(headers or {})}
    if not key.startswith('sb_secret_'):
        combined['Authorization']='Bearer '+key
    req=Request(url+'/rest/v1/'+path,data=None if body is None else json.dumps(body,allow_nan=False).encode(),method=method,headers=combined)
    try:
        with build_opener(RestrictedRedirect(urlparse(url).hostname or '')).open(req,timeout=60) as response:
            content=response.read()
            return json.loads(content) if content else None,dict(response.headers)
    except HTTPError as error:
        code=error.code; error.close()
        raise RuntimeError(f'External Supabase {method} failed with HTTP {code}; credentials and response bodies omitted.') from None
    except (URLError,TimeoutError):
        raise RuntimeError('External Supabase endpoint could not be reached; release remains unpublished unless a publication request completed. Verify before retrying.') from None


def load_publication():
    payload = validate_publication(json.loads((ROOT / 'website/public/external-data/research.json').read_text(encoding='utf-8')))
    build = json.loads((ROOT / 'website/src/externalRelease.json').read_text(encoding='utf-8'))
    if any(build[k] != payload[k] for k in ('release_id', 'manifest_sha256')):
        raise ValueError('External website build and exported release differ.')
    release = payload['release_id']
    tables = {
        'external_sources': [dict(release_id=release, source_id=r['source_id'], record=r) for r in payload['sources']],
        'external_variables': [dict(release_id=release, variable=r['variable'], record=r) for r in payload['variables']],
        'external_infrastructure': [dict(release_id=release, **{k:r[k] for k in ('id','source_id','name','country','latitude','longitude','record_kind','snapshot_date')}, record=r) for r in payload['infrastructure']],
        'external_geographies': [dict(release_id=release, id=r['id'], record=r) for r in payload['geographies']],
        'external_activity': [dict(release_id=release, **{k:r[k] for k in ('area_id','source_id','period_start','period_end','metric','dataset','value','unit')}, record=r) for r in payload['activity']],
        'external_cable_systems': [dict(release_id=release,id=r['id'],source_id=r['source_id'],record=r) for r in payload.get('cable_systems',[])],
        'external_cable_landings': [dict(release_id=release,cable_id=r['cable_id'],landing_id=r['landing_id'],source_id=r['source_id'],record=r) for r in payload.get('cable_landings',[])],
        'external_html_observations': [dict(release_id=release,observation_id=r['observation_id'],source_id=r['source_id'],record=r) for r in payload.get('html_observations',[])],
    }
    return payload, tables


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--allow-incomplete-status', action='store_true', help='Explicitly publish a truthful source-status release even though empirical acquisition is incomplete')
    args = parser.parse_args()
    payload, tables = load_publication()
    print('External release:', payload['release_id'], 'status:', payload['status'])
    for name, rows in tables.items():
        print(f'{name}: {len(rows)} records')
    if not args.publish:
        print('DRY RUN. No credentials loaded, network requests or database writes. Run SQL 004 then 006 before a future authorized publication; 005 and 007 verify afterward. 003 is optional read-only original-evidence verification.')
        return
    if not payload['empirical_analysis_available'] and not args.allow_incomplete_status:
        raise ValueError('Empirical acquisition is incomplete. Complete it first, or explicitly authorize publishing source-status only with --allow-incomplete-status.')
    url, key = load_admin_credentials()
    query = 'id=eq.' + quote(payload['release_id'], safe='')
    existing, _ = request(url,key,'external_releases?' + query + '&select=id,published,payload')
    if existing and existing[0]['published']:
        raise ValueError('External release already published and immutable; nothing overwritten.')
    if existing and existing[0]['payload'] != payload:
        raise ValueError('Unpublished external release metadata differs; do not resume a different payload.')
    request(url,key,'external_releases?on_conflict=id','POST',[dict(id=payload['release_id'],manifest_sha256=payload['manifest_sha256'],payload=payload,published=False)],{'Prefer':'resolution=merge-duplicates,return=minimal'})
    for name, rows in tables.items():
        for offset in range(0,len(rows),250):
            request(url,key,name,'POST',rows[offset:offset+250],{'Prefer':'resolution=merge-duplicates,return=minimal'})
        _, headers = request(url,key,f"{name}?release_id=eq.{quote(payload['release_id'],safe='')}&select=*",'HEAD',headers={'Prefer':'count=exact'})
        count = next((v for k,v in headers.items() if k.lower()=='content-range'),'')
        if not count.endswith('/'+str(len(rows))):
            raise ValueError(f'{name} count mismatch. External release remains unpublished.')
    request(url,key,'external_releases?' + query,'PATCH',{'published':True})
    print('Separate external release published after reconciliation. Run SQL 005 and 007. Original experiment was not imported or updated.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)
