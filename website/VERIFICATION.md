# Local verification — 3 November 2026

## Passed

- Production TypeScript/Vite build.
- 24 frontend/database tests: 8 data/provenance/CSV checks, 15 page/component interaction checks, and one local PostgreSQL-compatible schema/RLS integration test.
- 23 Python API/publication tests, including real frozen-pipeline inference on an existing **training** example, strict invalid-input handling, unavailable startup, model hash mismatch, runtime mismatch, concurrency/rate limits, feature-importance consistency, and unchanged source fingerprints.
- A real local HTTP prediction request using the exported training example returned class 0 from the frozen service. This was an inference smoke test, not a repeat of the final evaluation.
- Local frontend HTTP response: 200. Local API health: ready with the expected research release/model fingerprint.
- Supabase import dry run: 4,315 observations, 21 variable definitions, four original models, five performed evaluations, 11 context indicators, and seven incidents. No database requests were made.
- Production dependency audit at verification: zero reported vulnerabilities. This is a point-in-time package audit, not a general security guarantee.

The generated research export and original frozen model are fingerprint-checked. Original data files, research outputs, and the one-time final-evaluation artifacts were not re-fitted, re-scored, or modified by this website implementation. API integrity checks run before deserializing the repository-owned joblib artifact.

## Not yet verified

- Actual Render deployment, custom domains, account settings, and cold-start behavior in the user's account.
- Actual Supabase gateway, hosted migration/import, and public-key access in the user's account. The SQL/RLS test used local PostgreSQL-compatible PGlite; it does not replace hosted verification.
- Native visual layout on real phones, tablets, and desktop browsers. The in-app browser failed to initialize; Chrome access approval timed out. Component tests mock Recharts and therefore do not establish chart-rendering fidelity or screen-size layout.

Bootstrap breakpoints, responsive CSS, accessible form labels, keyboard menu behavior, exact chart-data alternatives, and reduced-motion rules are implemented. Inspect the site visually before public submission, as described in DEPLOYMENT.md.

One non-failing API-test warning concerns Starlette's deprecated AnyIO BlockingPortal alias. Build output also contains third-party Zod comment-annotation warnings. Neither prevented the successful tests/build.

No cloud resources or paid services were created during verification. Git publication is a separate, subsequently authorized step and does not establish a live deployment.
