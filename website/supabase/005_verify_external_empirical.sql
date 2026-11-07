-- Read-only checks after 004 + explicit external import. Does NOT import data.
-- Run existing 003 separately for the full original-release baseline checks.
begin read only;
set local role anon;
select count(*)>0 as has_published_external_release from public.external_releases;
select e.id,e.payload->>'status' as acquisition_status,
  e.payload->>'empirical_analysis_available' as empirical_analysis_available,
  (select count(*) from public.external_sources s where s.release_id=e.id)=jsonb_array_length(e.payload->'sources') as source_counts_passed,
  (select count(*) from public.external_variables v where v.release_id=e.id)=jsonb_array_length(e.payload->'variables') as dictionary_counts_passed,
  (select count(*) from public.external_infrastructure i where i.release_id=e.id)=(e.payload->'counts'->>'infrastructure')::int as infrastructure_counts_passed,
  (select count(*) from public.external_geographies g where g.release_id=e.id)=(e.payload->'counts'->>'geographies')::int as geography_counts_passed,
  (select count(*) from public.external_activity a where a.release_id=e.id)=(e.payload->'counts'->>'activity')::int as activity_counts_passed
from public.external_releases e;
select not exists(select 1 from information_schema.table_privileges
  where grantee in ('anon','authenticated') and table_schema='public'
  and table_name like 'external\_%' escape '\' and privilege_type<>'SELECT') as browser_read_only_passed;
select count(*)=4315 and coalesce(sum(fault_next_year),0)=818 as original_observations_preserved
from public.cable_year_observations where release_id='final-2026-11-02-56200c1c9706';
select count(*)=1 as original_model_preserved from public.dataset_versions
where id='final-2026-11-02-56200c1c9706' and published
and model_sha256='4228e0bb067a895e4035229a275d0eb77007afc65c8f832b5ff8461673b56bfb';
rollback;
