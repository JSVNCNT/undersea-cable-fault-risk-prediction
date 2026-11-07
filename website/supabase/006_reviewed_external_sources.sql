-- Run AFTER 004. Additive reviewed historical/HTML sources only.
-- No observations seeded, no original experiment tables touched.
-- Rerunnable; existing published external releases remain immutable.
begin;
alter table public.external_sources drop constraint if exists external_sources_source_id_check;
alter table public.external_sources add constraint external_sources_source_id_check
  check (source_id in ('world_bank','global_fishing_watch','open_undersea_cable_map','ofca'));
alter table public.external_infrastructure drop constraint if exists external_infrastructure_source_id_check;
alter table public.external_infrastructure add constraint external_infrastructure_source_id_check
  check (source_id in ('world_bank','open_undersea_cable_map'));

create table if not exists public.external_cable_systems (
  release_id text not null,
  id text not null check(id !~* '^CAB[0-9]{4,}$'),
  source_id text not null check(source_id='open_undersea_cable_map'),
  record jsonb not null,
  primary key(release_id,id),
  foreign key(release_id,source_id) references public.external_sources(release_id,source_id),
  check(record->>'id'=id),
  check(not(record ?| array['fault_next_year','fault_this_year','predicted_risk','model_probability']))
);
create table if not exists public.external_cable_landings (
  release_id text not null,
  cable_id text not null,
  landing_id text not null,
  source_id text not null check(source_id='open_undersea_cable_map'),
  record jsonb not null,
  primary key(release_id,cable_id,landing_id),
  foreign key(release_id,cable_id) references public.external_cable_systems(release_id,id),
  foreign key(release_id,landing_id) references public.external_infrastructure(release_id,id),
  foreign key(release_id,source_id) references public.external_sources(release_id,source_id),
  check(record->>'cable_id'=cable_id and record->>'landing_id'=landing_id),
  check(record->>'relationship_evidence' in ('both_directions','cable_record_only','landing_record_only')),
  check(not(record ?| array['fault_next_year','fault_this_year','predicted_risk','model_probability']))
);
create table if not exists public.external_html_observations (
  release_id text not null,
  observation_id text not null,
  source_id text not null check(source_id='ofca'),
  record jsonb not null,
  primary key(release_id,observation_id),
  foreign key(release_id,source_id) references public.external_sources(release_id,source_id),
  check(record->>'observation_id'=observation_id),
  check(record->>'country'='Hong Kong'),
  check(record->>'reference_period' ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
  check(record->>'extraction_method'='HTML prose list extraction'),
  check(record->>'html_sha256' ~ '^[0-9a-f]{64}$'),
  check(not(record ?| array['fault_next_year','fault_this_year','predicted_risk','model_probability']))
);

-- Extend the existing publish-last guard to reconcile all new record units.
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
        or (select count(*) from public.external_activity where release_id=new.id)<>(new.payload->'counts'->>'activity')::int
        or (select count(*) from public.external_cable_systems where release_id=new.id)<>coalesce((new.payload->'counts'->>'cable_systems')::int,0)
        or (select count(*) from public.external_cable_landings where release_id=new.id)<>coalesce((new.payload->'counts'->>'cable_landings')::int,0)
        or (select count(*) from public.external_html_observations where release_id=new.id)<>coalesce((new.payload->'counts'->>'html_observations')::int,0) then
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
  foreach t in array array['external_cable_systems','external_cable_landings','external_html_observations'] loop
    execute format('revoke all on public.%I from anon,authenticated',t);
    execute format('grant select on public.%I to anon,authenticated',t);
    execute format('grant all on public.%I to service_role',t);
    execute format('alter table public.%I enable row level security',t);
    if not exists(select 1 from pg_policies where schemaname='public' and tablename=t and policyname='read_published_external') then
      execute format('create policy read_published_external on public.%I for select to anon,authenticated using (exists(select 1 from public.external_releases e where e.id=release_id and e.published))',t);
    end if;
    if not exists(select 1 from pg_trigger where tgname='guard_external_'||t) then
      execute format('create trigger %I before insert or update or delete on public.%I for each row execute function public.guard_external_release()', 'guard_external_'||t,t);
    end if;
  end loop;
end $$;
comment on table public.external_cable_systems is 'Historical archived descriptions, CC BY-NC-SA 3.0. Not current operating status, World Bank observations, surveyed routes or fault events.';
comment on table public.external_html_observations is 'OFCA-authored Hong Kong dated prose list, noncommercial attribution terms. Not an HTML table, global census or historical archive crosswalk.';
commit;
