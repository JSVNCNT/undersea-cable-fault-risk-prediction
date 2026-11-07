"""Isolated fixtures only; never create empirical research rows or query live APIs."""
import csv
import io
import json
from pathlib import Path
from urllib.request import Request
import zipfile
import importlib.util
import sys

import pytest

from src.external import common, gfw, processing, world_bank
from src.external.common import canonical, digest, load_token, safe_url, store_raw, write_csv
from src.external.processing import genuine_key, integrate_activity, load_infrastructure, prepare_areas, validate_dates, validate_polygon
from scripts.run_external_pipeline import validate_publication
from src import evidence


def catalog_fixture():
    # Deliberately minimal HTML fixture, not downloaded infrastructure data.
    dataset = {"dataset_unique_id": "0037968", "name": "Test catalog fixture", "Resources": [
        {"resource_unique_id": "resource-test", "name": "Cable metadata fixture", "description": "Resource descriptor only", "website_url": "https://github.com/telegeography/www.submarinecablemap.com", "isDownload": False, "rFormat": "html"}]}
    linked = {"@type": "Dataset", "license": {"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"}, "dateModified": "2023-01-31"}
    return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({"props": {"pageProps": {"dataset": dataset}}}) + '</script><script type="application/ld+json">' + json.dumps(linked) + '</script>'


def test_scraper_extracts_resource_rows_not_cable_observations():
    source, rows = world_bank.parse_catalog(catalog_fixture())
    assert source['metadata_updated'] == '2023-01-31'
    assert source['period'] == 'Infrastructure observation date not established'
    assert rows[0]['record_kind'] == 'catalog_resource_metadata'
    assert rows[0]['download_available'] is False
    assert rows[0]['resource_license'] == 'Not established'
    assert 'latitude' not in rows[0]


def test_scraper_fails_on_schema_or_identity_change():
    with pytest.raises(ValueError): world_bank.parse_catalog('<html>No descriptors</html>')
    with pytest.raises(ValueError): world_bank.parse_catalog(catalog_fixture().replace('0037968','different'))


def test_robots_denial_stops_catalog_request(monkeypatch, tmp_path):
    calls = []
    def fake(url, **kwargs):
        calls.append(url)
        return b'User-agent: *\nDisallow: /\n', {}
    monkeypatch.setattr(world_bank, 'fetch', fake)
    with pytest.raises(ValueError, match='robots'): world_bank.acquire_catalog(tmp_path)
    assert len(calls) == 1


def test_raw_content_addressing_is_immutable(monkeypatch, tmp_path):
    monkeypatch.setattr(common, 'ROOT', tmp_path)
    folder = tmp_path/'raw'
    first = store_raw(folder,b'original',{},'.csv')
    again = store_raw(folder,b'original',{},'.csv')
    assert first['sha256'] == again['sha256']
    path = tmp_path/first['raw_path']
    path.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='hash'): store_raw(folder,b'original',{},'.csv')


@pytest.mark.parametrize('url', ['http://example.org/data','https://user:pass@example.org/data','https://example.org/data?token=secret','https://other.org/data'])
def test_acquisition_url_never_exposes_credentials_or_changes_host(url):
    with pytest.raises(ValueError): safe_url(url,{'example.org'})


def test_bearer_redirect_cannot_cross_host():
    handler = common.RestrictedRedirect('gateway.api.globalfishingwatch.org')
    with pytest.raises(ValueError):
        handler.redirect_request(Request('https://gateway.api.globalfishingwatch.org/test'),None,302,'',{},'https://other.org/test')


def test_private_token_parser_has_no_interpolation_or_unrelated_settings(tmp_path):
    path=tmp_path/'private.env'
    path.write_text('GFW_API_ACCESS_TOKEN="private-test-value"\n')
    assert load_token({'GFW_API_ACCESS_TOKEN':'old'},path)=='private-test-value'
    path.write_text('SUPABASE_SECRET_KEY=not-supported\n')
    with pytest.raises(ValueError) as error: load_token({},path)
    assert 'not-supported' not in str(error.value)


@pytest.mark.parametrize('key',['CAB0001','world:CAB0001',''])
def test_no_synthetic_crosswalk_keys(key):
    with pytest.raises(ValueError): genuine_key(key)


def infrastructure_fixture(monkeypatch,tmp_path,rows=None):
    monkeypatch.setattr(processing,'ROOT',tmp_path)
    raw=tmp_path/'data/external/world_bank/raw'
    raw.mkdir(parents=True)
    path=raw/'fixture.csv'
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['id','name','country','latitude','longitude'])
        writer.writeheader(); writer.writerows(rows or [{'id':'fixture-site','name':'Fixture only','country':'Test','latitude':10,'longitude':120}])
    return dict(path=str(path.relative_to(tmp_path)),source_url=world_bank.CATALOG,license='Test-only license fixture',
                license_url='https://creativecommons.org/licenses/by/4.0/',snapshot_date='2021-01-01',unit_of_analysis='landing_point',field_map={},
                sha256=digest(path.read_bytes()),reuse_confirmed=True,redistribution_confirmed=True)


def test_actual_infrastructure_requires_rights_and_checksum(monkeypatch,tmp_path):
    spec=infrastructure_fixture(monkeypatch,tmp_path)
    rows,_=load_infrastructure(spec)
    assert rows[0]['latitude']==10
    assert 'fault_next_year' not in rows[0]
    for changed in ({'reuse_confirmed':False},{'sha256':'0'*64},{'source_url':'https://unofficial.example/snapshot'}):
        with pytest.raises(ValueError): load_infrastructure({**spec,**changed})


@pytest.mark.parametrize('lat,lon',[('nan',120),(91,120),(10,181),('',120)])
def test_bad_coordinates_rejected_not_imputed(monkeypatch,tmp_path,lat,lon):
    spec=infrastructure_fixture(monkeypatch,tmp_path,[dict(id='fixture-site',name='Fixture',country='Test',latitude=lat,longitude=lon)])
    with pytest.raises(ValueError): load_infrastructure(spec)


def test_duplicate_source_keys_are_not_silently_removed(monkeypatch,tmp_path):
    row=dict(id='fixture-site',name='Fixture',country='Test',latitude='',longitude='')
    spec=infrastructure_fixture(monkeypatch,tmp_path,[row,row])
    with pytest.raises(ValueError,match='Duplicate'): load_infrastructure(spec)


def report(entries, **extra):
    return canonical(dict(entries=entries,nextOffset=0,total=len(entries),**extra))


def test_gfw_aggregates_flags_within_area_month_not_faults():
    rows=gfw.clean_report(report([dict(date='2024-01-01',flag='A',hours=2.5),dict(date='2024-01-01',flag='B',hours=3)]),
                          {'sha256':'0'*64,'x_datasets':'public-global-fishing-effort:v5.0'},
                          {'id':'fixture-region','country':'Test'},'public-global-fishing-effort:v5.0','2024-01-01','2024-02-01')
    assert len(rows)==1 and rows[0]['value']==5.5
    assert rows[0]['metric']=='apparent_fishing_hours'
    assert rows[0]['period_end']=='2024-02-01'
    assert 'fault_next_year' not in rows[0]


@pytest.mark.parametrize('entries',[ [dict(date='2024-01-01',flag='A',hours=None)], [dict(date='2024-01-01',flag='A',hours=-1)],
    [dict(date='2025-01-01',flag='A',hours=1)], [dict(date='2024-01-01',flag='A',hours=1)]*2, [dict(fishing_hours=1)] ])
def test_gfw_rejects_ambiguous_missing_negative_duplicate_or_out_of_period(entries):
    with pytest.raises(ValueError):
        gfw.clean_report(report(entries),{'sha256':'0'*64,'x_datasets':'public-global-fishing-effort:v5.0'},
                         {'id':'fixture','country':'Test'},'public-global-fishing-effort:v5.0','2024-01-01','2024-02-01')


def test_no_response_rows_is_not_zero_activity():
    rows=gfw.clean_report(report([]),{'sha256':'0'*64,'x_datasets':'public-global-fishing-effort:v5.0'},
                          {'id':'fixture','country':'Test'},'public-global-fishing-effort:v5.0','2024-01-01','2024-02-01')
    assert rows==[]


def test_gfw_version_and_pagination_must_be_verified():
    data=report([dict(date='2024-01-01',flag='A',hours=0)])
    for version in ('','public-global-fishing-effort:v4.0'):
        with pytest.raises(ValueError,match='version'): gfw.clean_report(data,{'x_datasets':version},{},'public-global-fishing-effort:v5.0','2024-01-01','2024-02-01')
    payload=json.loads(data); payload['nextOffset']=100
    with pytest.raises(ValueError,match='paginated'): gfw.clean_report(canonical(payload),{}, {},'public-global-fishing-effort:v5.0','2024-01-01','2024-02-01')


def test_report_zip_reads_without_extracting_paths():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:
        archive.writestr('../does-not-extract.json',report([]))
    assert gfw.report_json(buffer.getvalue())['entries']==[]


def test_gfw_token_missing_cannot_trigger_html_scraping(tmp_path):
    with pytest.raises(ValueError,match='token'):
        gfw.acquire_reports({'start_date':'2024-01-01','end_date':'2024-02-01'},[], '',tmp_path)


def test_country_linkage_is_only_context_not_synthetic_join():
    sites=[dict(id='real-source-key-fixture',country='Test')]
    areas=[dict(id='area-fixture',country='Test')]
    rows=integrate_activity(sites,areas,[dict(area_id='area-fixture',value=1)])
    assert rows[0]['linkage']=='country_context'
    assert rows[0]['infrastructure_records']==1
    with pytest.raises(ValueError): integrate_activity(sites,areas,[dict(area_id='area-fixture',fault_next_year=1)])


def test_projected_buffers_are_configured_and_not_degree_distances():
    pytest.importorskip('pyproj'); pytest.importorskip('shapely')
    sites=[dict(id='fixture-site',name='Fixture',country='Test',record_kind='landing_point',latitude=10,longitude=120)]
    with pytest.raises(ValueError): prepare_areas([],sites,{'distances_km':[1]})
    areas=prepare_areas([],sites,{'distances_km':[1,2],'justification':'Fixture sensitivity only','snapshot_alignment_note':'Test snapshot'})
    assert len(areas)==2 and areas[0]['buffer_km']==1
    from pyproj import Geod
    lon,lat=areas[0]['geometry']['coordinates'][0][0]
    assert Geod(ellps='WGS84').inv(120,10,lon,lat)[2]==pytest.approx(1000,rel=.001)


@pytest.mark.parametrize('geometry',[{'type':'Polygon','coordinates':[]},{'type':'Polygon','coordinates':[[[0,0],[1,1],[0,0]]]}, {'type':'Polygon','coordinates':[[[None,0],[1,1],[2,0],[None,0]]]}])
def test_invalid_polygons_do_not_create_fake_areas(geometry):
    with pytest.raises(ValueError): validate_polygon(geometry)


def test_baseline_hashes_allow_only_separate_empirical_additions(monkeypatch):
    monkeypatch.setattr(evidence,'protected_fingerprints',lambda:{'data/original.csv':'old','data/external/world_bank/raw/new.csv':'new'})
    assert evidence.verify_historical_evidence({'data/original.csv':'old'})
    with pytest.raises(AssertionError): evidence.verify_historical_evidence({'data/original.csv':'changed'})
    monkeypatch.setattr(evidence,'protected_fingerprints',lambda:{'data/original.csv':'old','data/unknown.csv':'new'})
    with pytest.raises(AssertionError): evidence.verify_historical_evidence({'data/original.csv':'old'})


def test_current_export_reconciles_and_has_no_empirical_seed_rows():
    payload=json.loads(Path('website/public/external-data/research.json').read_text(encoding='utf-8'))
    validate_publication(payload)
    assert payload['configuration'].get('infrastructure') is None  # No local source-file paths published.
    assert all(not r['used_in_synthetic_model'] for r in payload['variables'])
    changed={**payload,'manifest_sha256':'0'*64}
    with pytest.raises(ValueError): validate_publication(changed)


def test_csv_export_prevents_spreadsheet_formula_injection(tmp_path):
    path=tmp_path/'safe.csv'
    write_csv(path,[{'name':'=HYPERLINK("https://example.org")','hours':0}],['name','hours'])
    row=next(csv.DictReader(path.open()))
    assert row['name'].startswith("'=") and row['hours']=='0'


def importer(monkeypatch):
    folder=Path('website/scripts').resolve()
    monkeypatch.syspath_prepend(str(folder))
    spec=importlib.util.spec_from_file_location('external_importer_fixture',folder/'import_external_supabase.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_import_dry_run_does_not_read_credentials_or_make_requests(monkeypatch,capsys):
    module=importer(monkeypatch)
    def forbidden(*args,**kwargs): raise AssertionError('Credential/network access is forbidden in dry run')
    monkeypatch.setattr(module,'load_admin_credentials',forbidden)
    monkeypatch.setattr(module,'request',forbidden)
    monkeypatch.setattr(sys,'argv',['import_external_supabase.py'])
    module.main()
    assert 'DRY RUN' in capsys.readouterr().out


def test_incomplete_publication_requires_separate_explicit_authority(monkeypatch):
    module=importer(monkeypatch)
    monkeypatch.setattr(module,'load_publication',lambda:({'empirical_analysis_available':False,'release_id':'fixture','status':'partial'},{}))
    def forbidden(): raise AssertionError('Must reject before credentials are loaded')
    monkeypatch.setattr(module,'load_admin_credentials',forbidden)
    monkeypatch.setattr(sys,'argv',['import_external_supabase.py','--publish'])
    with pytest.raises(ValueError,match='incomplete'): module.main()


def test_import_targets_external_tables_only_and_publishes_last(monkeypatch):
    module=importer(monkeypatch)
    payload,tables=module.load_publication()
    calls=[]
    def fake(url,key,path,method='GET',body=None,headers=None):
        calls.append((path,method,body))
        assert path.startswith('external_')
        if method=='GET': return [],{}
        if method=='HEAD':
            table=path.split('?')[0]
            return None,{'Content-Range':f'*/{len(tables[table])}'}
        return None,{}
    monkeypatch.setattr(module,'request',fake)
    monkeypatch.setattr(module,'load_admin_credentials',lambda:('https://example.supabase.co','fixture-key-not-real'))
    monkeypatch.setattr(sys,'argv',['import_external_supabase.py','--publish','--allow-incomplete-status'])
    module.main()
    assert calls[-1][1:] == ('PATCH',{'published':True})
    assert sum(c[1]=='HEAD' for c in calls)==len(tables)


def test_gfw_adapter_serializes_queries_and_never_logs_token(monkeypatch,tmp_path):
    monkeypatch.setattr(common,'ROOT',tmp_path)
    monkeypatch.setattr(gfw,'ROOT',tmp_path)
    calls=[]
    def fake(url,hosts,token,body):
        from urllib.parse import parse_qs,urlparse
        query=parse_qs(urlparse(url).query)
        datasets=[v[0] for k,v in query.items() if k.startswith('datasets[')]
        calls.append((url,body))
        return report([{dataset:[dict(date='2024-01',flag='Fixture',hours=0)]} for dataset in datasets]),{'x_datasets':','.join(datasets),'retrieved_at':'2026-11-07T00:00:00Z','source_url':url}
    monkeypatch.setattr(gfw,'fetch',fake)
    areas=[dict(id='fixture-area',country='Fixture',region={'dataset':'fixture-region','id':'fixture-id'})]
    rows,downloads,events=gfw.acquire_reports({'start_date':'2024-01-01','end_date':'2024-02-01','datasets':list(gfw.DATASETS)},areas,'not-a-real-token',tmp_path/'data/external/global_fishing_watch/raw')
    assert len(calls)==1 and len(rows)==2
    assert all(r['value']==0 for r in rows)
    assert 'not-a-real-token' not in json.dumps(downloads+events)


def test_raw_manifest_rechecks_downloads_after_acquisition(monkeypatch,tmp_path):
    monkeypatch.setattr(common,'ROOT',tmp_path)
    folder=tmp_path/'data/external/world_bank/raw'
    record=store_raw(folder,b'fixture',{},'.html')
    assert common.verify_raw_manifest([record])
    (tmp_path/record['raw_path']).write_bytes(b'changed')
    with pytest.raises(ValueError): common.verify_raw_manifest([record])
