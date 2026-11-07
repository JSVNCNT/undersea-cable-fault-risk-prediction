-- Read-only checks after 004 + 006 and an explicitly authorized import.
begin read only;
set local role anon;
select e.id,
  (select count(*) from public.external_cable_systems s where s.release_id=e.id)=coalesce((e.payload->'counts'->>'cable_systems')::int,0) as cable_counts_passed,
  (select count(*) from public.external_cable_landings s where s.release_id=e.id)=coalesce((e.payload->'counts'->>'cable_landings')::int,0) as link_counts_passed,
  (select count(*) from public.external_html_observations s where s.release_id=e.id)=coalesce((e.payload->'counts'->>'html_observations')::int,0) as html_counts_passed,
  e.payload->>'status' as acquisition_status,
  e.payload->>'empirical_analysis_available' as infrastructure_activity_integration_complete
from public.external_releases e order by imported_at desc;
select 'public.'||t as table_name, not has_table_privilege('anon','public.'||t,'INSERT,UPDATE,DELETE') as browser_read_only_passed
from unnest(array['external_cable_systems','external_cable_landings','external_html_observations']) t;
rollback;
