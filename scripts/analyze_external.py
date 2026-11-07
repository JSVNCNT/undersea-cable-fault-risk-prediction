"""EDA from one acquired external release; no models or invented observations.

python scripts/analyze_external.py --release-dir outputs/external_empirical/RUN
Writes new analysis/ results only; refuses to overwrite an earlier analysis.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_external_pipeline import validate_publication
from src.external.common import write_json
from src.external.processing import validate_dates

GFW_ATTRIBUTION = 'Powered by Global Fishing Watch. https://globalfishingwatch.org'


def monthly_series(rows, start, end):
    """One area/metric only. Missing months are gaps, never zero or interpolation."""
    first, stop = validate_dates(start, end)
    if len({(r['area_id'], r['metric']) for r in rows}) > 1:
        raise ValueError('A monthly plot cannot combine different regions or metrics.')
    by_month = {}
    for row in rows:
        stamp = date.fromisoformat(row['period_start'])
        if not first <= stamp < stop:
            raise ValueError('Monthly observation falls outside the requested chart window.')
        month = stamp.strftime('%Y-%m')
        if month in by_month:
            raise ValueError('Duplicate monthly plot observations are not silently combined.')
        by_month[month] = row['value']
    months = []
    cursor = first.replace(day=1)
    while cursor < stop:
        months.append(cursor.strftime('%Y-%m'))
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    return months, [by_month.get(month) for month in months]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', required=True, type=Path)
    parser.add_argument('--area-id', action='append', default=[], help='Optional exact region ID for individual monthly plots; repeat for selected regions')
    args = parser.parse_args()
    folder = args.release_dir.resolve()
    if not folder.is_relative_to((ROOT / 'outputs/external_empirical').resolve()):
        raise ValueError('Choose an existing independent external release directory.')
    data = validate_publication(json.loads((folder / 'research.json').read_text(encoding='utf-8')))
    area_names = {r['id']: r['name'] for r in data['geographies']}
    if not set(args.area_id) <= set(area_names):
        raise ValueError('Select only region IDs present in the acquired release.')
    out = folder / 'analysis'
    out.mkdir(exist_ok=False)
    figures = []
    activity_plots = []
    if data['infrastructure_summary'] or data['activity']:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        if data['infrastructure_summary']:
            rows = sorted(data['infrastructure_summary'],key=lambda r:(-r['records'],r['country'],r['record_kind']))[:20]
            rows = list(reversed(rows))
            fig, ax = plt.subplots(figsize=(10,7))
            labels=[r['country'] if r['record_kind']=='landing_point' else r['country']+' / '+r['record_kind'] for r in rows]
            bars=ax.barh(labels, [r['records'] for r in rows])
            ax.bar_label(bars,padding=3,fontsize=8)
            ax.set_xlim(0,max(r['records'] for r in rows)*1.12)
            title='Twenty largest source-country landing counts (historical archive)' if data.get('cable_systems') else 'Twenty largest source-country infrastructure counts'
            ax.set(xlabel='Distinct source records', title=title)
            fig.tight_layout(); fig.savefig(out / 'infrastructure_distribution.png', dpi=180); plt.close(fig)
            figures.append('infrastructure_distribution.png')
        if data.get('cable_systems'):
            fig, ax = plt.subplots(figsize=(9,4.5))
            values=[r['landing_point_count'] for r in data['cable_systems']]
            ax.hist(values,bins=range(min(values),max(values)+2),align='left',color='#227c83',edgecolor='white')
            ax.set(xlabel='Distinct source-supplied landing links per cable system',ylabel='Historical cable-system records',title='Connectivity recorded in the historical archive')
            fig.text(.02,.01,'Includes flagged one-sided source links. Not an assessment of operating status or physical network redundancy.',fontsize=8)
            fig.tight_layout(rect=(0,.05,1,1)); fig.savefig(out/'historical_cable_connectivity.png',dpi=180); plt.close(fig)
            figures.append('historical_cable_connectivity.png')
            fig, ax = plt.subplots(figsize=(9,4))
            points=data['infrastructure']
            counts=[sum(r.get('location_to_be_determined') is False for r in points),sum(r.get('location_to_be_determined') is True for r in points),sum(r.get('location_to_be_determined') is None for r in points)]
            ax.bar(['Not marked TBD','Location marked TBD','Flag not supplied'],counts,color=['#227c83','#b57b26','#687587'])
            ax.set(ylabel='Historical landing-point records',title='Source location-certainty flags (not surveyed accuracy)')
            for i,n in enumerate(counts): ax.text(i,n+max(counts)*.02,str(n),ha='center')
            ax.set_ylim(0,max(counts)*1.15)
            fig.tight_layout(); fig.savefig(out/'historical_location_flags.png',dpi=180); plt.close(fig)
            figures.append('historical_location_flags.png')
        if data['activity']:
            # Count region IDs with returned observations, NOT hours summed
            # across overlapping areas. This chart describes source coverage.
            fig,ax=plt.subplots(figsize=(10,4.5))
            months=sorted({r['period_start'][:7] for r in data['activity']})
            for metric in sorted({r['metric'] for r in data['activity']}):
                counts=[len({r['area_id'] for r in data['activity'] if r['metric']==metric and r['period_start'].startswith(m)}) for m in months]
                ax.plot(months,counts,marker='o',label=metric.replace('_',' '))
            ax.set(ylabel='Distinct official region IDs with returned rows',title='Monthly availability of GFW regional activity records')
            ax.legend();ax.tick_params(axis='x',rotation=45)
            fig.text(.02,.05,'Region IDs can overlap. Counts are reporting units, not vessels, faults or deduplicated global vessel-hours.',fontsize=8)
            fig.text(.02,.01,GFW_ATTRIBUTION,fontsize=8)
            fig.tight_layout(rect=(0,.1,1,1));fig.savefig(out/'gfw_monthly_region_coverage.png',dpi=180);plt.close(fig)
            figures.append('gfw_monthly_region_coverage.png')
        # Individual plots only for explicitly selected areas. Avoid hundreds
        # of unrequested images; the website filters all acquired regions.
        for index, (area, metric) in enumerate(sorted({(r['area_id'],r['metric']) for r in data['activity'] if r['area_id'] in args.area_id})):
            rows = sorted((r for r in data['activity'] if r['area_id']==area and r['metric']==metric),key=lambda r:r['period_start'])
            months, values = monthly_series(rows, data['configuration']['gfw']['start_date'], data['configuration']['gfw']['end_date'])
            fig, ax = plt.subplots(figsize=(9,4))
            ax.plot(months,values,marker='o')
            ax.set(ylabel='Vessel-hours (AIS-derived estimate)', title=f'{area_names[area]}: {metric.replace("_"," ")}')
            ax.tick_params(axis='x',rotation=45)
            fig.text(.02,.05,'Gaps mean no returned observation. These activity estimates do not measure cable faults or anchoring.',fontsize=8)
            fig.text(.02,.01,GFW_ATTRIBUTION,fontsize=8)
            fig.tight_layout(rect=(0,.11,1,1))
            name=f'activity_{index+1:03}.png'; fig.savefig(out/name,dpi=180); plt.close(fig); figures.append(name)
            activity_plots.append({'file':name,'area_id':area,'area_name':area_names[area],'metric':metric,'dataset':rows[0]['dataset'],
                                   'reported_months':len(rows),'missing_months':[month for month,value in zip(months,values) if value is None]})
    write_json(out / 'analysis_status.json',{'release_id':data['release_id'],'empirical_analysis_available':data['empirical_analysis_available'],
               'figures':figures,'selected_region_plots':args.area_id,'activity_plots':activity_plots,'message':'Charts use only acquired observations. No deduplicated global hour totals or fault outcomes are inferred. Region-count coverage is not complete vessel coverage.' if figures else 'No empirical observations acquired; no chart or numerical distribution was fabricated.',
               'source_quality': {'one_sided_links':sum(e['relationship_evidence']!='both_directions' for e in data.get('cable_landings',[])),
                 'missing_landing_details':sum(p.get('detail_record_available') is False for p in data['infrastructure']),
                 'source_encoding_flags':sum(r['source_text_quality']!='no_replacement_character' for r in data.get('html_observations',[]))}})
    print(json.dumps({'analysis':str(out),'figures':figures,'status':data['status']}))


if __name__=='__main__': main()
