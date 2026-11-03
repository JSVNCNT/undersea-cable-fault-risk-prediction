-- Run in SQL Editor AFTER the admin import. Read-only checks; no data mutation.
select id,published,payload->'counts' as expected_counts from public.dataset_versions;
select release_id,partition,count(*) as rows,sum(fault_next_year) as positives
from public.cable_year_observations group by release_id,partition order by partition;
-- Expect train 2960/570; validation 891/170; final_test 464/78.
select model_id,partition,pr_auc,tp,fp,fn,tn from public.evaluation_results order by partition,model_id;
-- Expect 4 validation rows + ONE final_test row (Random Forest), no placeholder zeros.
select tablename,rowsecurity from pg_tables where schemaname='public' and tablename in
('dataset_versions','cable_year_observations','variable_definitions','model_versions','evaluation_results','source_context','historical_incidents');
select tablename,policyname,cmd from pg_policies where schemaname='public' and tablename in
('dataset_versions','cable_year_observations','variable_definitions','model_versions','evaluation_results','source_context','historical_incidents');
-- All RLS=true. All our policies SELECT only.
select table_name,privilege_type from information_schema.role_table_grants
where table_schema='public' and grantee='anon' and table_name in
('dataset_versions','cable_year_observations','variable_definitions','model_versions','evaluation_results','source_context','historical_incidents','annual_observation_summary');
-- Must show SELECT only. Run below as anon to confirm visible published counts.
begin;
set local role anon;
select count(*) as published_rows from public.cable_year_observations;
select * from public.annual_observation_summary order by year limit 5;
rollback;
