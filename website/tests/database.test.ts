import { PGlite } from '@electric-sql/pglite';
import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';

it('executes the Supabase schema and enforces published-only, read-only access in local Postgres', async () => {
  const db = new PGlite();
  try {
    await db.exec(
      'create role anon; create role authenticated; create role service_role bypassrls;',
    );
    await db.exec(
      readFileSync(new URL('../supabase/001_research_schema.sql', import.meta.url), 'utf8'),
    );
    const research = JSON.parse(
      readFileSync(new URL('../public/data/research.json', import.meta.url), 'utf8'),
    );
    const observations = JSON.parse(
      readFileSync(new URL('../public/data/observations.json', import.meta.url), 'utf8'),
    );
    const release = research.release_id;
    await db.query(
      'insert into dataset_versions(id,model_sha256,payload) values($1,$2,$3::jsonb)',
      [release, research.model_sha256, JSON.stringify(research)],
    );
    const cols = [
      'release_id',
      'cable_id',
      'year',
      'partition',
      'ocean_route',
      'operator_type',
      'chokepoint',
      'age_years',
      'fiber_pairs',
      'length_km',
      'n_landing_countries',
      'design_capacity_tbps',
      'lit_capacity_tbps',
      'utilization_pct',
      'protected_burial',
      'route_redundancy',
      'fault_this_year',
      'fault_next_year',
    ];
    const types = cols
      .map(
        (c) =>
          `${c} ${['release_id', 'cable_id', 'partition', 'ocean_route', 'operator_type', 'chokepoint'].includes(c) ? 'text' : ['length_km', 'design_capacity_tbps', 'lit_capacity_tbps', 'utilization_pct'].includes(c) ? 'double precision' : 'integer'}`,
      )
      .join(',');
    await db.query(
      `insert into cable_year_observations(${cols.join(',')}) select ${cols.join(',')} from jsonb_to_recordset($1::jsonb) as x(${types})`,
      [
        JSON.stringify(
          observations.map((r: Record<string, unknown>) => ({ release_id: release, ...r })),
        ),
      ],
    );
    await db.exec('set role anon;');
    expect(
      (await db.query<{ n: number }>('select count(*)::int as n from cable_year_observations'))
        .rows[0].n,
    ).toBe(0);
    expect(
      (await db.query<{ n: number }>('select count(*)::int as n from dataset_versions')).rows[0].n,
    ).toBe(0);
    await expect(db.query('delete from cable_year_observations')).rejects.toThrow(
      /permission denied/,
    );
    await expect(db.query('update dataset_versions set published=true')).rejects.toThrow(
      /permission denied/,
    );
    await db.exec('reset role;');
    await db.query('update dataset_versions set published=true where id=$1', [release]);
    await db.exec('set role anon;');
    expect(
      (await db.query<{ n: number }>('select count(*)::int as n from cable_year_observations'))
        .rows[0].n,
    ).toBe(4315);
    expect(
      (
        await db.query<{ n: number }>(
          'select sum(cable_years)::int as n from annual_observation_summary',
        )
      ).rows[0].n,
    ).toBe(4315);
    expect(
      (
        await db.query<{ n: number }>(
          "select count(*)::int as n from cable_year_observations where chokepoint='None'",
        )
      ).rows[0].n,
    ).toBeGreaterThan(0);
    await db.exec('reset role;');
    const verification = await db.exec(
      readFileSync(new URL('../supabase/003_verify_revision_evidence.sql', import.meta.url), 'utf8'),
    );
    // This fixture intentionally contains no evaluations: the script must detect
    // that incomplete import while confirming the genuine observation counts.
    const verificationRows = verification.flatMap(result => result.rows as Record<string, unknown>[]);
    expect(verificationRows.filter(r => 'passed' in r).map(r => r.passed)).toEqual([true, true, true]);
    expect(verificationRows.find(r => 'eligible_counts_passed' in r)?.eligible_counts_passed).toBe(true);
    expect(verificationRows.find(r => 'existing_evaluation_count_passed' in r)?.existing_evaluation_count_passed).toBe(false);
    await db.exec('set role anon;');
    for (const table of [
      'dataset_versions',
      'cable_year_observations',
      'variable_definitions',
      'model_versions',
      'evaluation_results',
      'source_context',
      'historical_incidents',
    ]) {
      expect(
        (
          await db.query<{ n: number }>(
            "select count(*)::int as n from information_schema.table_privileges where grantee='anon' and table_name=$1 and privilege_type<>'SELECT'",
            [table],
          )
        ).rows[0].n,
      ).toBe(0);
    }
  } finally {
    await db.close();
  }
}, 60000);
