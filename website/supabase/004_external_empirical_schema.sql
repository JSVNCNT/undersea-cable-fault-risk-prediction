-- ADDITIVE schema only. Run after 001; 003 is optional baseline verification.
-- No seed observations, synthetic-data updates, or external fault predictions.
-- Then use the dry-run-first import_external_supabase.py, not CSV guessing.
begin;

create table if not exists public.external_releases (
  id text primary key check (id ~ '^external-[0-9a-f]{16}$'),
  manifest_sha256 text not null check (manifest_sha256 ~ '^[0-9a-f]{64}$'),
  payload jsonb not null,
  published boolean not null default false,
  imported_at timestamptz not null default now(),
  check (payload->>'release_id' = id),
  check (payload->>'manifest_sha256' = manifest_sha256),
  check (payload->>'status' in ('blocked','partial','available')),
  check (payload->>'schema_version' = '1')
);
create table if not exists public.external_sources (
  release_id text not null references public.external_releases(id),
  source_id text not null check (source_id in ('world_bank','global_fishing_watch')),
  record jsonb not null,
  primary key (release_id,source_id),
  check (record->>'source_id' = source_id),
  check (record->>'source_url' like 'https://%'),
  check (length(record->>'license') > 0)
);
create table if not exists public.external_variables (
  release_id text not null references public.external_releases(id),
  variable text not null,
  record jsonb not null,
  primary key (release_id,variable),
  check (record->>'variable' = variable),
  check (record->>'used_in_synthetic_model' = 'false'),
  check (record->>'external_analysis_only' = 'true'),
  check (record->>'indicator_group' in ('infrastructure','exposure','provenance'))
);
create table if not exists public.external_infrastructure (
  release_id text not null,
  id text not null check (id !~* '^CAB[0-9]{4,}$'),
  source_id text not null default 'world_bank' check (source_id='world_bank'),
  name text not null check (length(trim(name))>0),
  country text not null check (length(trim(country))>0),
  latitude double precision check (latitude between -90 and 90),
  longitude double precision check (longitude between -180 and 180),
  record_kind text not null check (record_kind in ('landing_point','cable_system','country')),
  snapshot_date date,
  record jsonb not null,
  primary key (release_id,id),
  foreign key (release_id,source_id) references public.external_sources(release_id,source_id),
  check ((latitude is null) = (longitude is null)),
  check (not (record ? 'fault_next_year'))
);
create table if not exists public.external_geographies (
  release_id text not null references public.external_releases(id),
  id text not null check (id !~* '^CAB[0-9]{4,}$'),
  record jsonb not null,
  primary key (release_id,id),
  check (record->>'id' = id),
  check (length(record->>'definition')>0)
);
create table if not exists public.external_activity (
  release_id text not null,
  area_id text not null,
  source_id text not null default 'global_fishing_watch' check (source_id='global_fishing_watch'),
  period_start date not null check (period_start >= date '2012-01-01'),
  period_end date not null,
  metric text not null check (metric in ('apparent_fishing_hours','vessel_presence_hours')),
  dataset text not null check (dataset in ('public-global-fishing-effort:v5.0','public-global-presence:v5.0')),
  value double precision not null check (value>=0 and value<'Infinity'::float8),
  unit text not null check (unit='vessel-hours'),
  record jsonb not null,
  primary key (release_id,area_id,period_start,period_end,metric,dataset),
  foreign key (release_id,area_id) references public.external_geographies(release_id,id),
  foreign key (release_id,source_id) references public.external_sources(release_id,source_id),
  check (period_end>period_start),
  check ((metric='apparent_fishing_hours') = (dataset='public-global-fishing-effort:v5.0')),
  check (not (record ? 'fault_next_year'))
);

-- Immutable after publication, including against accidental administrator edits.
create or replace function public.guard_external_release() returns trigger
language plpgsql set search_path=public,pg_temp as $$
begin
  if tg_table_name='external_releases' then
    if tg_op<>'INSERT' and old.published then
      raise exception 'Published external release is immutable';
    end if;
    if tg_op<>'DELETE' and new.published then
      if (select count(*) from public.external_sources where release_id=new.id)<>jsonb_array_length(new.payload->'sources')
        or (select count(*) from public.external_variables where release_id=new.id)<>jsonb_array_length(new.payload->'variables')
        or (select count(*) from public.external_infrastructure where release_id=new.id)<>(new.payload->'counts'->>'infrastructure')::int
        or (select count(*) from public.external_geographies where release_id=new.id)<>(new.payload->'counts'->>'geographies')::int
        or (select count(*) from public.external_activity where release_id=new.id)<>(new.payload->'counts'->>'activity')::int then
        raise exception 'External import incomplete; publish only after reconciliation';
      end if;
    end if;
  else
    if tg_op<>'INSERT' and exists(select 1 from public.external_releases where id=old.release_id and published) then
      raise exception 'Published external child records are immutable';
    end if;
    if tg_op<>'DELETE' and exists(select 1 from public.external_releases where id=new.release_id and published) then
      raise exception 'Published external child records are immutable';
    end if;
  end if;
  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;
revoke all on function public.guard_external_release() from public;

do $$
declare t text;
begin
  foreach t in array array['external_releases','external_sources','external_variables','external_infrastructure','external_geographies','external_activity'] loop
    execute format('revoke all on public.%I from anon,authenticated',t);
    execute format('grant select on public.%I to anon,authenticated',t);
    execute format('grant all on public.%I to service_role',t);
    execute format('alter table public.%I enable row level security',t);
    if not exists(select 1 from pg_policies where schemaname='public' and tablename=t and policyname='read_published_external') then
      if t='external_releases' then
        execute format('create policy read_published_external on public.%I for select to anon,authenticated using (published)',t);
      else
        execute format('create policy read_published_external on public.%I for select to anon,authenticated using (exists(select 1 from public.external_releases e where e.id=release_id and e.published))',t);
      end if;
    end if;
    if not exists(select 1 from pg_trigger where tgname='guard_external_'||t) then
      execute format('create trigger %I before insert or update or delete on public.%I for each row execute function public.guard_external_release()', 'guard_external_'||t,t);
    end if;
  end loop;
end $$;
comment on table public.external_releases is 'Separate empirical/source-status release. BLOCKED and metadata-only are honest states, not empirical observations. No synthetic model FK or final-test mutation.';
comment on table public.external_activity is 'AIS-derived maritime exposure only. Never actual faults, anchoring proof, or fault probabilities. Areas can overlap; do not sum them as a deduplicated global total.';
commit;
