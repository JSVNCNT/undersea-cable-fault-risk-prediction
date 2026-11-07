import { PGlite } from '@electric-sql/pglite';
import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';

it('adds an independent schema, publishes last, enforces RLS and freezes published external records', async () => {
  const db = new PGlite();
  try {
    await db.exec(
      'create role anon; create role authenticated; create role service_role bypassrls;',
    );
    await db.exec(readFileSync('supabase/001_research_schema.sql', 'utf8'));
    const sql = readFileSync('supabase/004_external_empirical_schema.sql', 'utf8');
    await db.exec(sql);
    await db.exec(sql); // Additive migration is rerunnable without destructive drops.
    const reviewedSql = readFileSync('supabase/006_reviewed_external_sources.sql', 'utf8');
    await db.exec(reviewedSql);
    await db.exec(reviewedSql);
    const payload = JSON.parse(readFileSync('public/external-data/research.json', 'utf8'));
    const id = payload.release_id;
    await db.query(
      'insert into external_releases(id,manifest_sha256,payload) values($1,$2,$3::jsonb)',
      [id, payload.manifest_sha256, JSON.stringify(payload)],
    );
    await expect(
      db.query('update external_releases set published=true where id=$1', [id]),
    ).rejects.toThrow(/incomplete/);
    for (const source of payload.sources)
      await db.query('insert into external_sources values($1,$2,$3::jsonb)', [
        id,
        source.source_id,
        JSON.stringify(source),
      ]);
    for (const variable of payload.variables)
      await db.query('insert into external_variables values($1,$2,$3::jsonb)', [
        id,
        variable.variable,
        JSON.stringify(variable),
      ]);
    await db.query(
      `insert into external_infrastructure(release_id,id,source_id,name,country,latitude,longitude,record_kind,snapshot_date,record)
      select $1,r->>'id',r->>'source_id',r->>'name',r->>'country',(r->>'latitude')::float8,(r->>'longitude')::float8,r->>'record_kind',(r->>'snapshot_date')::date,r from jsonb_array_elements($2::jsonb) r`,
      [id, JSON.stringify(payload.infrastructure)],
    );
    await db.query(
      `insert into external_cable_systems(release_id,id,source_id,record)
      select $1,r->>'id',r->>'source_id',r from jsonb_array_elements($2::jsonb) r`,
      [id, JSON.stringify(payload.cable_systems)],
    );
    await db.query(
      `insert into external_cable_landings(release_id,cable_id,landing_id,source_id,record)
      select $1,r->>'cable_id',r->>'landing_id',r->>'source_id',r from jsonb_array_elements($2::jsonb) r`,
      [id, JSON.stringify(payload.cable_landings)],
    );
    // Even when the original six tables reconcile, HTML records still gate publication.
    await expect(
      db.query('update external_releases set published=true where id=$1', [id]),
    ).rejects.toThrow(/incomplete/);
    await db.query(
      `insert into external_html_observations(release_id,observation_id,source_id,record)
      select $1,r->>'observation_id',r->>'source_id',r from jsonb_array_elements($2::jsonb) r`,
      [id, JSON.stringify(payload.html_observations)],
    );
    await db.query(
      `insert into external_geographies(release_id,id,record) select $1,r->>'id',r from jsonb_array_elements($2::jsonb) r`,
      [id, JSON.stringify(payload.geographies)],
    );
    await db.query(
      `insert into external_activity(release_id,area_id,source_id,period_start,period_end,metric,dataset,value,unit,record)
      select $1,r->>'area_id',r->>'source_id',(r->>'period_start')::date,(r->>'period_end')::date,r->>'metric',r->>'dataset',(r->>'value')::float8,r->>'unit',r from jsonb_array_elements($2::jsonb) r`,
      [id, JSON.stringify(payload.activity)],
    );
    await expect(
      db.query(
        "insert into external_infrastructure(release_id,id,name,country,latitude,longitude,record_kind,record) values($1,'CAB0001','Fixture','Fixture',10,120,'landing_point','{}')",
        [id],
      ),
    ).rejects.toThrow(/check constraint/);
    await expect(
      db.query(
        "insert into external_infrastructure(release_id,id,name,country,latitude,longitude,record_kind,record) values($1,'fixture','Fixture','Fixture',91,120,'landing_point','{}')",
        [id],
      ),
    ).rejects.toThrow(/check constraint/);
    await db.exec('set role anon');
    expect(
      (await db.query<{ n: number }>('select count(*)::int as n from external_releases')).rows[0].n,
    ).toBe(0);
    expect(
      (await db.query<{ n: number }>('select count(*)::int as n from external_sources')).rows[0].n,
    ).toBe(0);
    await expect(db.exec('update external_releases set published=true')).rejects.toThrow(
      /permission denied/,
    );
    await db.exec('reset role');
    await db.query('update external_releases set published=true where id=$1', [id]);
    await expect(
      db.query('update external_releases set published=false where id=$1', [id]),
    ).rejects.toThrow(/immutable/);
    await expect(
      db.query('delete from external_sources where release_id=$1', [id]),
    ).rejects.toThrow(/immutable/);
    await db.exec('set role anon');
    expect(
      (await db.query<{ n: number }>('select count(*)::int as n from external_sources')).rows[0].n,
    ).toBe(payload.sources.length);
    for (const table of [
      'external_releases',
      'external_sources',
      'external_variables',
      'external_infrastructure',
      'external_geographies',
      'external_activity',
      'external_cable_systems',
      'external_cable_landings',
      'external_html_observations',
    ]) {
      await expect(db.exec(`delete from ${table}`)).rejects.toThrow(/permission denied/);
      const grants = await db.query<{ allowed: boolean }>(
        "select has_table_privilege('anon',$1,'INSERT,UPDATE,DELETE') as allowed",
        [table],
      );
      expect(grants.rows[0].allowed).toBe(false);
    }
    await db.exec('reset role');
    const result = await db.exec(
      readFileSync('supabase/005_verify_external_empirical.sql', 'utf8'),
    );
    const rows = result.flatMap((r) => r.rows as Record<string, unknown>[]);
    expect(
      rows.find((r) => 'has_published_external_release' in r)?.has_published_external_release,
    ).toBe(true);
    expect(rows.find((r) => 'source_counts_passed' in r)?.source_counts_passed).toBe(true);
    expect(
      rows.find((r) => 'infrastructure_counts_passed' in r)?.infrastructure_counts_passed,
    ).toBe(true);
    expect(rows.find((r) => 'browser_read_only_passed' in r)?.browser_read_only_passed).toBe(true);
    const extended = (
      await db.exec(readFileSync('supabase/007_verify_reviewed_sources.sql', 'utf8'))
    ).flatMap((r) => r.rows as Record<string, unknown>[]);
    expect(extended.find((r) => 'html_counts_passed' in r)?.html_counts_passed).toBe(true);
    expect(extended.find((r) => 'link_counts_passed' in r)?.link_counts_passed).toBe(true);
    // Original tables remain empty in this fixture: the new import never seeds them.
    expect(
      (await db.query<{ n: number }>('select count(*)::int as n from cable_year_observations'))
        .rows[0].n,
    ).toBe(0);
    expect(
      rows.find((r) => 'original_observations_preserved' in r)?.original_observations_preserved,
    ).toBe(false);
  } finally {
    await db.close();
  }
}, 60000);
