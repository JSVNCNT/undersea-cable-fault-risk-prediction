"""Global-context and live-format fixtures; no network or production seed rows."""
import json
import pytest

from src.external import common, gfw, gfw_regions
from src.external.common import canonical,digest,store_raw

DATASET='public-global-fishing-effort:v5.0'
META={'sha256':'0'*64,'x_datasets':DATASET}
AREA={'id':'fixture-region','country':'Fixture','region':{'dataset':'public-eez-areas','id':'123'}}


def nested(rows):
    return canonical(dict(total=1,entries=[{DATASET:rows}],nextOffset=None))


def test_live_nested_monthly_report_is_aggregated_only_within_one_region():
    rows=gfw.clean_report(nested([dict(date='2024-01',flag='A',hours=2),dict(date='2024-01',flag='',hours=3)]),META,AREA,DATASET,'2024-01-01','2025-01-01')
    assert len(rows)==1 and rows[0]['value']==5
    assert rows[0]['period_start']=='2024-01-01' and rows[0]['period_end']=='2024-02-01'
    assert rows[0]['country']=='Fixture'


def test_verified_null_dataset_report_produces_no_imputed_zero():
    assert gfw.clean_report(nested(None),META,AREA,DATASET,'2024-01-01','2025-01-01')==[]


def test_multi_dataset_wrappers_do_not_mix_fishing_and_presence_values():
    presence='public-global-presence:v5.0'
    raw=canonical(dict(total=2,entries=[{DATASET:[dict(date='2024-01',flag='A',hours=2)]},{presence:[dict(date='2024-01',flag='A',hours=9)]}]))
    meta={**META,'x_datasets':DATASET+','+presence}
    assert gfw.clean_report(raw,meta,AREA,DATASET,'2024-01-01','2025-01-01')[0]['value']==2
    assert gfw.clean_report(raw,meta,AREA,presence,'2024-01-01','2025-01-01')[0]['value']==9


@pytest.mark.parametrize('stamp',['2024','2024-01-12','2024-13','2024-00','2024-01-01T00:00:00Z'])
def test_monthly_date_formats_are_not_guessed(stamp):
    with pytest.raises(ValueError):gfw.clean_report(nested([dict(date=stamp,flag='A',hours=1)]),META,AREA,DATASET,'2024-01-01','2025-01-01')


def test_wrong_dataset_wrapper_is_not_silently_used():
    with pytest.raises(ValueError):gfw.clean_report(canonical(dict(entries=[{'wrong:v5.0':[]}],total=1)),META,AREA,DATASET,'2024-01-01','2025-01-01')


def test_region_catalog_preserves_joint_regimes_without_single_country_guess():
    raw=canonical([dict(id=1,label='Fixture EEZ',iso3='AAA',territory1='Fixture Country',isoSov1='AAA'),dict(id=2,label='Joint regime fixture',iso3=None,territory1='First Country',isoSov1='AAA',isoSov2='BBB')])
    rows=gfw_regions.parse_regions(raw,{'sha256':digest(raw)})
    assert len(rows)==2
    assert rows[0]['country']=='Fixture Country' and rows[0]['region']['id']=='1'
    assert rows[1]['country']=='Joint regime fixture'
    assert rows[1]['region_category']=='joint_or_overlapping'
    assert rows[1]['sovereignty_iso_codes']==['AAA','BBB']
    assert all('geometry' not in r and 'infrastructure_ids' not in r for r in rows)


def test_duplicate_official_region_ids_are_rejected():
    raw=canonical([dict(id=1,label='Fixture')]*2)
    with pytest.raises(ValueError):gfw_regions.parse_regions(raw,{'sha256':digest(raw)})


def test_cached_report_reuses_verified_raw_bytes_without_network_or_token(monkeypatch,tmp_path):
    monkeypatch.setattr(common,'ROOT',tmp_path)
    monkeypatch.setattr(gfw,'ROOT',tmp_path)
    raw_dir=tmp_path/'data/external/global_fishing_watch/raw'
    query={'datasets[0]':DATASET,'date-range':'2024-01-01,2025-01-01','format':'JSON','group-by':'FLAG','temporal-resolution':'MONTHLY','spatial-aggregation':'true'}
    record=store_raw(raw_dir,nested([dict(date='2024-01',flag='A',hours=0)]),{**META,'query':query,'study_area':AREA,'method':'POST'},'.report')
    def forbidden(*a,**k):raise AssertionError('Cached replay must not request network')
    monkeypatch.setattr(gfw,'fetch',forbidden)
    rows,downloads,events=gfw.acquire_reports({'start_date':'2024-01-01','end_date':'2025-01-01','datasets':[DATASET]},[AREA],'',raw_dir,offline=True,retained=[record])
    assert rows[0]['value']==0 and downloads[0]['cache_reused'] is True
    (tmp_path/record['raw_path']).write_bytes(b'changed')
    rows,_,events=gfw.acquire_reports({'start_date':'2024-01-01','end_date':'2025-01-01','datasets':[DATASET]},[AREA],'',raw_dir,offline=True,retained=[record])
    assert rows==[] and events[0]['status']=='blocked'
