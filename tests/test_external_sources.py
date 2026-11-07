"""Small isolated parser fixtures. No fixture is written to research-data roots."""
import io
import json
import zipfile

import pytest

from src.external import ofca, open_cable_archive as archive
from src.external.common import digest


def zipped(*, reverse=True, detail=True, terms=True, coordinate=120, tbd=False):
    prefix = f"open_undersea_cable_map-{archive.REVISION}/"
    payloads = {
        'LICENSE': 'Attribution-NonCommercial-ShareAlike 3.0' if terms else 'No reuse declaration',
        'README.md': 'Historical fixture late 2022 CC BY-NC-SA 3.0',
        'country/fixture-country.json': dict(id='fixture-country',name='Fixture Country',landing_points_in_country=['fixture-site']),
        'landing-point/landing-point-geo.json': dict(type='FeatureCollection',features=[dict(type='Feature',properties=dict(id='fixture-site',name='Fixture source point',is_tbd=tbd),geometry=dict(type='Point',coordinates=[coordinate,10]))]),
        'cable/fixture-cable.json': dict(id='fixture-cable',name='Fixture cable',length='100 km',rfs='2022 planned',owners=None,suppliers=None,landing_points=[dict(id='fixture-site',country='Fixture Country')]),
    }
    if detail:
        payloads['landing-point/fixture-site.json'] = dict(id='fixture-site',name='Fixture source point',country='Fixture Country',cables=[dict(id='fixture-cable')] if reverse else [])
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        for name,value in payloads.items():
            z.writestr(prefix+name,json.dumps(value) if isinstance(value,dict) else value)
    return buffer.getvalue()


def test_archive_joins_original_ids_and_keeps_unknown_dates_and_reported_text():
    sites,cables,edges=archive.parse_archive(zipped())
    assert sites[0]['snapshot_date'] is None
    assert sites[0]['country_assignment']=='individual_landing_record'
    assert cables[0]['rfs_reported']=='2022 planned'
    assert edges[0]['relationship_evidence']=='both_directions'
    assert not any('fault_next_year' in r for r in sites+cables+edges)


def test_one_sided_archive_links_are_flagged_not_fabricated_or_deleted():
    sites,cables,edges=archive.parse_archive(zipped(reverse=False))
    assert len(edges)==1 and edges[0]['relationship_evidence']=='cable_record_only'
    assert cables[0]['landing_point_count']==1


def test_missing_archive_detail_uses_exact_source_country_membership():
    sites,_,edges=archive.parse_archive(zipped(detail=False,tbd=True))
    assert sites[0]['detail_record_available'] is False
    assert sites[0]['location_to_be_determined'] is True
    assert sites[0]['country_assignment']=='exact_source_country_membership'
    assert sites[0]['country']=='Fixture Country'
    assert edges[0]['relationship_evidence']=='cable_record_only'


@pytest.mark.parametrize('kwargs',[dict(terms=False),dict(coordinate=181),dict(tbd=None)])
def test_archive_fails_for_unverified_license_coordinates_or_tbd_schema(kwargs):
    with pytest.raises(ValueError): archive.parse_archive(zipped(**kwargs))


def test_unreviewed_archive_revision_cannot_be_substituted():
    with pytest.raises(ValueError,match='revision'): archive.parse_archive(zipped(),'0'*40)


HTML = '<html><script>Fake cable and private token must not be extracted.</script><p>As at July 2026, Hong Kong has thirteen submarine cable systems, namely, ' + ', '.join(f'Fixture cable {i} ("F{i}")' for i in range(1,13)) + ' and Fixture cable 13 ("F13"). Several other systems are being planned.</p><p>Contact: personal@example.org</p></html>'


def test_ofca_html_prose_records_reconcile_month_count_and_exclude_contacts():
    rows=ofca.parse_context(HTML,digest(HTML.encode()))
    assert len(rows)==13 and rows[0]['reference_period']=='2026-07'
    assert rows[0]['extraction_method']=='HTML prose list extraction'
    assert 'personal@example.org' not in json.dumps(rows)
    assert 'private token' not in json.dumps(rows)
    assert all('latitude' not in r and 'fault_next_year' not in r for r in rows)


def test_ofca_does_not_silently_accept_count_or_structure_changes():
    with pytest.raises(ValueError): ofca.parse_context(HTML.replace('thirteen','fourteen'),'0'*64)
    with pytest.raises(ValueError): ofca.parse_context('<table>No dated list</table>','0'*64)


def test_ofca_keeps_source_encoding_issues_and_flags_them():
    rows=ofca.parse_context(HTML.replace('Fixture cable 1 ', 'Fixture\ufffd cable 1 '),'0'*64)
    assert rows[0]['source_text_quality']=='source_contains_replacement_character'
    assert '\ufffd' in rows[0]['system_name_reported']
    rows=ofca.parse_context(HTML.replace('Fixture cable 1 ', 'Fixture\x93 cable 1 '),'0'*64)
    assert rows[0]['source_text_quality']=='source_contains_nonprinting_control'


def test_ofca_terms_are_not_assumed_from_robots_or_other_sites():
    with pytest.raises(ValueError): ofca.verify_terms('<p>All rights reserved.</p>')
    ofca.verify_terms('<p>may be reproduced or re-disseminated for non-commercial use provided OFCA as the source of information is acknowledged</p>')


def test_ofca_robots_denial_prevents_any_html_request(monkeypatch,tmp_path):
    calls=[]
    def fake(url,**kwargs):
        calls.append(url)
        return b'User-agent: *\nDisallow: /\n',{}
    monkeypatch.setattr(ofca,'fetch',fake)
    with pytest.raises(ValueError,match='robots'): ofca.acquire_context(tmp_path)
    assert len(calls)==1
