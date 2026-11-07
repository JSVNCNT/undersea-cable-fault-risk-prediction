"""Read-only external acquisition/CSV/hash verification; no inference or cloud access."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_external_pipeline import CSV_DATASETS, validate_publication
from src.external.common import canonical, digest, verify_raw_manifest
from src.evidence import verify_historical_evidence


def verify(folder: Path, website=False):
    folder=folder.resolve()
    if not folder.is_relative_to((ROOT/'outputs/external_empirical').resolve()):
        raise ValueError('Choose an independent external release directory.')
    payload=validate_publication(json.loads((folder/'research.json').read_text(encoding='utf-8')))
    acquisition=json.loads((folder/'acquisition_manifest.json').read_text(encoding='utf-8'))
    if acquisition['release_id']!=payload['release_id']:
        raise ValueError('Acquisition manifest and release differ.')
    verify_raw_manifest(acquisition['downloads'])
    expected=json.loads((ROOT/'outputs/revisions/2026-11-05/revision_protocol.json').read_text(encoding='utf-8'))['protected_sha256']
    verify_historical_evidence(expected)
    for name,sha in acquisition.get('packages',{}).items():
        if name!='historical_infrastructure.zip' or digest((folder/name).read_bytes())!=sha:
            raise ValueError('Attributed archive download bundle missing or changed.')
        if website and (folder/name).read_bytes()!=(ROOT/'website/public/external-data'/name).read_bytes():
            raise ValueError('Website attributed archive bundle differs from verified release.')
    parser_version=payload.get('runtime',{}).get('parser_version')
    expected_exports = set(CSV_DATASETS) - ({'external_geographies.csv'} if parser_version=='2' else set())
    if parser_version in ('2','3') and set(acquisition.get('exports',{})) != expected_exports:
        raise ValueError('Missing or unknown external CSV export provenance.')
    for filename,checksum in acquisition.get('exports',{}).items():
        if filename not in CSV_DATASETS:
            raise ValueError('Unknown external export path.')
        key=CSV_DATASETS[filename]
        if key=='world_bank_infrastructure' and key not in payload:
            key='infrastructure'  # Historical version-1 release had World Bank only.
        with (folder/filename).open(encoding='utf-8',newline='') as stream:
            rows=list(csv.DictReader(stream))
        if len(rows)!=len(payload[key]):
            raise ValueError(f'CSV row count mismatch: {filename}')
        if checksum!=digest((folder/filename).read_bytes()):
            raise ValueError(f'CSV content/checksum mismatch or missing export provenance: {filename}')
        if website and (folder/filename).read_bytes()!=(ROOT/'website/public/external-data'/filename).read_bytes():
            raise ValueError('Website CSV differs from the verified release.')
    # For completed global runs, reproduce both geographic definitions and
    # every measured aggregate from exactly the retained raw manifest. No
    # token, network, replacement data, model imports or writes are involved.
    raw_reprocessing=False
    if parser_version=='3' and payload['empirical_analysis_available']:
        from src.external.gfw_regions import ENDPOINT,parse_regions
        from src.external.gfw import acquire_reports
        areas=payload['geographies']
        if payload['configuration']['gfw'].get('region_selection')=='all_official_eez_regions':
            regions=[r for r in acquisition['downloads'] if r['source_url']==ENDPOINT]
            if len(regions)!=1:
                raise ValueError('Completed global release lacks a unique official region-definition snapshot.')
            record=regions[0]
            areas=parse_regions((ROOT/record['raw_path']).read_bytes(),record)
            if canonical(areas)!=canonical(payload['geographies']):
                raise ValueError('Published geographic definitions differ from retained official metadata.')
        measured,_,events=acquire_reports(payload['configuration']['gfw'],areas,'',ROOT/'data/external/global_fishing_watch/raw',offline=True,retained=acquisition['downloads'])
        if canonical(measured)!=canonical(payload['activity']) or any(e['status']=='blocked' for e in events) or len(events)!=len(areas)*len(payload['configuration']['gfw']['datasets']):
            raise ValueError('Published activity does not reproduce from its exact raw checkpoints.')
        raw_reprocessing=True
    if website:
        public=validate_publication(json.loads((ROOT/'website/public/external-data/research.json').read_text(encoding='utf-8')))
        if canonical(public)!=canonical(payload):
            raise ValueError('Website and verified external release differ.')
    result=dict(release_id=payload['release_id'],status=payload['status'],counts=payload['counts'],
                original_evidence_unchanged=True,raw_hashes_verified=True,csv_counts_verified=True,website_checked=website,raw_reprocessing_verified=raw_reprocessing)
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir',required=True,type=Path)
    parser.add_argument('--website',action='store_true')
    args=parser.parse_args()
    verify(args.release_dir,args.website)
