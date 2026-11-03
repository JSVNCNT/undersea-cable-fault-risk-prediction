-- Paste this entire file into a NEW Supabase project's SQL Editor and Run.
-- No invented records, no credentials, no user accounts, no destructive drops.
-- Public browsers can SELECT published releases only. Only the admin import writes.
begin;

create table if not exists public.dataset_versions (
  id text primary key,
  model_sha256 text not null check (model_sha256 ~ '^[0-9a-f]{64}$'),
  payload jsonb not null,
  published boolean not null default false,
  imported_at timestamptz not null default now(),
  check (payload->>'release_id' = id),
  check (payload->>'model_sha256' = model_sha256)
);
comment on table public.dataset_versions is 'One immutable generated research release. Payload is its exported dashboard summary, not a live model result. Published last after a complete import.';

create table if not exists public.cable_year_observations (
  release_id text not null references public.dataset_versions(id),
  cable_id text not null,
  year integer not null check (year between 2015 and 2025),
  partition text not null check (partition in ('train','validation','final_test')),
  ocean_route text not null,
  operator_type text not null,
  chokepoint text not null,
  age_years integer not null check (age_years >= 0),
  fiber_pairs integer not null check (fiber_pairs > 0),
  length_km double precision not null check (length_km > 0 and length_km < 'Infinity'::float8),
  n_landing_countries integer not null check (n_landing_countries > 0),
  design_capacity_tbps double precision not null check (design_capacity_tbps > 0 and design_capacity_tbps < 'Infinity'::float8),
  lit_capacity_tbps double precision not null check (lit_capacity_tbps >= 0 and lit_capacity_tbps < 'Infinity'::float8),
  utilization_pct double precision not null check (utilization_pct between 0 and 100),
  protected_burial smallint not null check (protected_burial in (0,1)),
  route_redundancy integer not null check (route_redundancy >= 0),
  fault_this_year smallint not null check (fault_this_year in (0,1)),
  fault_next_year smallint not null check (fault_next_year in (0,1)),
  primary key (release_id,cable_id,year),
  check ((partition='train' and year between 2015 and 2022) or (partition='validation' and year in (2023,2024)) or (partition='final_test' and year=2025))
);
comment on table public.cable_year_observations is 'One eligible computer-generated cable-year per release. Not authenticated real cable measurements. No visitor scenarios are stored here.';
comment on column public.cable_year_observations.cable_id is 'Generated publisher ID. Not a real-cable crosswalk and not a predictor.';
comment on column public.cable_year_observations.year is 'Predictor year t; the target refers to t+1. Not a primary predictor.';
comment on column public.cable_year_observations.chokepoint is 'Literal text None is a valid category, not SQL NULL.';
comment on column public.cable_year_observations.fault_next_year is 'Binary next-year label. Target only; never an input.';

create table if not exists public.variable_definitions (
  release_id text not null references public.dataset_versions(id),
  variable text not null,
  definition jsonb not null,
  primary key (release_id,variable)
);
comment on table public.variable_definitions is 'One original-field dictionary entry per release, including role, treatment, and qualifications.';

create table if not exists public.model_versions (
  release_id text not null references public.dataset_versions(id),
  model_id text not null,
  selected boolean not null,
  parameters jsonb not null,
  primary key (release_id,model_id)
);
create unique index if not exists one_selected_model_per_release on public.model_versions(release_id) where selected;

create table if not exists public.evaluation_results (
  release_id text not null,
  model_id text not null,
  partition text not null check (partition in ('validation','final_test')),
  accuracy double precision not null check (accuracy between 0 and 1),
  precision double precision not null check (precision between 0 and 1),
  recall double precision not null check (recall between 0 and 1),
  f1 double precision not null check (f1 between 0 and 1),
  pr_auc double precision not null check (pr_auc between 0 and 1),
  roc_auc double precision not null check (roc_auc between 0 and 1),
  tn integer not null check (tn>=0), fp integer not null check (fp>=0),
  fn integer not null check (fn>=0), tp integer not null check (tp>=0),
  primary key (release_id,model_id,partition),
  foreign key (release_id,model_id) references public.model_versions(release_id,model_id),
  check (partition <> 'final_test' or model_id='random_forest'),
  check ((partition='validation' and tn+fp+fn+tp=891) or (partition='final_test' and tn+fp+fn+tp=464))
);
comment on table public.evaluation_results is 'One previously saved model-period result. No rows for unperformed evaluations.';
comment on column public.evaluation_results.pr_auc is 'sklearn average_precision_score, NOT trapezoidal PR area.';

create table if not exists public.source_context (
  release_id text not null references public.dataset_versions(id),
  metric_id text not null,
  value double precision not null,
  reference jsonb not null,
  primary key (release_id,metric_id),
  check (reference->>'source_url' like 'https://%')
);
create table if not exists public.historical_incidents (
  release_id text not null references public.dataset_versions(id),
  incident_id text not null,
  telecom_cables_damaged integer check (telecom_cables_damaged>=0),
  reference jsonb not null,
  primary key (release_id,incident_id),
  check (reference->>'source_url' like 'https://%')
);
comment on table public.source_context is 'Source-backed sector context. Preserve period and scope. NO cable-ID join or model validation implied.';
comment on table public.historical_incidents is 'Selected documented incidents, not a census. Unknown cable counts stay NULL. NO generated cable-ID mapping.';

create index if not exists observation_filters on public.cable_year_observations(release_id,year,ocean_route,partition);

-- Supabase may supply broad default grants. Revoke them explicitly before RLS.
revoke all on public.dataset_versions, public.cable_year_observations, public.variable_definitions, public.model_versions, public.evaluation_results, public.source_context, public.historical_incidents from anon,authenticated;
grant usage on schema public to anon,authenticated,service_role;
grant select on public.dataset_versions, public.cable_year_observations, public.variable_definitions, public.model_versions, public.evaluation_results, public.source_context, public.historical_incidents to anon,authenticated;
grant all on public.dataset_versions, public.cable_year_observations, public.variable_definitions, public.model_versions, public.evaluation_results, public.source_context, public.historical_incidents to service_role;

alter table public.dataset_versions enable row level security;
alter table public.cable_year_observations enable row level security;
alter table public.variable_definitions enable row level security;
alter table public.model_versions enable row level security;
alter table public.evaluation_results enable row level security;
alter table public.source_context enable row level security;
alter table public.historical_incidents enable row level security;

-- Deliberately no public INSERT, UPDATE, or DELETE policies.
create policy "read_published_versions" on public.dataset_versions for select to anon,authenticated using (published);
create policy "read_published_observations" on public.cable_year_observations for select to anon,authenticated using (exists(select 1 from public.dataset_versions d where d.id=release_id and d.published));
create policy "read_published_definitions" on public.variable_definitions for select to anon,authenticated using (exists(select 1 from public.dataset_versions d where d.id=release_id and d.published));
create policy "read_published_models" on public.model_versions for select to anon,authenticated using (exists(select 1 from public.dataset_versions d where d.id=release_id and d.published));
create policy "read_published_evaluations" on public.evaluation_results for select to anon,authenticated using (exists(select 1 from public.dataset_versions d where d.id=release_id and d.published));
create policy "read_published_context" on public.source_context for select to anon,authenticated using (exists(select 1 from public.dataset_versions d where d.id=release_id and d.published));
create policy "read_published_incidents" on public.historical_incidents for select to anon,authenticated using (exists(select 1 from public.dataset_versions d where d.id=release_id and d.published));

-- Invoker views retain caller grants and RLS (Postgres 15+).
create or replace view public.annual_observation_summary with (security_invoker=true) as
select release_id,year,partition,ocean_route,count(*) as cable_years,
       sum(fault_next_year) as positive_labels,
       avg(fault_next_year::numeric) as positive_label_prevalence
from public.cable_year_observations group by release_id,year,partition,ocean_route;
comment on view public.annual_observation_summary is 'Descriptive label counts in the generated panel, not empirical fault frequencies. Do not join to evaluation scores and call them filtered performance.';
revoke all on public.annual_observation_summary from anon,authenticated;
grant select on public.annual_observation_summary to anon,authenticated,service_role;
commit;
