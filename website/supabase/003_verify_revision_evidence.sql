-- OPTIONAL VERIFICATION ONLY. Paste after the existing schema/import/access checks.
-- No migration, new tables, data updates, deletion, fitting, or publication.
-- Run as a project administrator; queries temporarily use the public anon role.
-- Every passed column should be true for the existing frozen research release.
begin read only;
set local role anon;

select current_user = 'anon' as checking_public_role;

with expected(partition, expected_rows, expected_positives) as (
  values ('train',2960,570),('validation',891,170),('final_test',464,78)
), actual as (
  select partition,count(*)::int as rows,sum(fault_next_year)::int as positives
  from public.cable_year_observations
  where release_id='final-2026-11-02-56200c1c9706' group by partition
)
select e.partition,e.expected_rows,coalesce(a.rows,0) as actual_rows,
       e.expected_positives,coalesce(a.positives,0) as actual_positives,
       coalesce(a.rows=e.expected_rows and a.positives=e.expected_positives,false) as passed
from expected e left join actual a using(partition) order by e.partition;

select count(*)=4315 and coalesce(sum(fault_next_year),0)=818 as eligible_counts_passed,
       count(*)=count(distinct(cable_id,year)) as unique_keys_passed,
       count(*) filter(where year=2025 and partition<>'final_test')=0 as partition_timing_passed
from public.cable_year_observations where release_id='final-2026-11-02-56200c1c9706';

select count(*)=1 as published_frozen_release_passed
from public.dataset_versions where id='final-2026-11-02-56200c1c9706' and published
and model_sha256='4228e0bb067a895e4035229a275d0eb77007afc65c8f832b5ff8461673b56bfb';

select count(*)=5 as existing_evaluation_count_passed,
       count(*) filter(where partition='final_test')=1 as only_one_final_result_passed,
       count(*) filter(where partition='final_test' and model_id='random_forest'
                       and tn=318 and fp=68 and fn=49 and tp=29)=1 as frozen_final_counts_passed
from public.evaluation_results where release_id='final-2026-11-02-56200c1c9706';

-- Supplemental reports are static aggregate downloads, not additional evaluation rows.
-- This checks result consistency, not proof of an unblinded-access history or authorization.
rollback;
