# Local verification

## Revision checks on 5 November 2026

- 83 Python research/document/API/publication tests passed. One non-failing Starlette/AnyIO deprecation warning remains.
- 32 frontend/database tests passed, including explicit synthetic provenance, supplementary view controls, and SELECT-only SQL 003 detecting an incomplete evaluation fixture correctly.
- TypeScript/Vite production build passed. Existing third-party Zod annotation warnings remain non-failing.
- Removed deprecated `baseUrl` from `tsconfig.app.json`; the relative `@/*` path mapping and Vite alias remain. TypeScript checking, the production build and all 32 frontend/database tests passed again after this configuration change.
- A fresh temporary working-copy development run reproduced the original validation metrics, temporal CV and split summaries within numerical tolerance. Only temporary fixed candidates were fitted; the original frozen model and final predictions were unchanged.
- New paired identifier-bootstrap, permutation and subgroup reports use validation only. Original source/results/model and the Supabase research release remain fingerprint-identical.
- No Supabase SQL, import, cloud deployment, commit or push was performed. Browser/mobile visual review is reported separately; DOM tests still mock charts.

## Historical local verification on 3 November 2026

## Passed

- Production TypeScript/Vite build.
- 31 frontend/database tests: 8 data/provenance/CSV checks, 18 page/component interaction checks, 4 presentation/contrast checks, and one local PostgreSQL-compatible schema/RLS integration test. The overview uses a compact source/limitations link instead of the large warning banner; detailed origin and study limitations remain available. All three chart tooltips receive white headers and pale-yellow values, and the site branding identifies Group 5 xam.py. Original research records are unchanged; displayed terminology uses the plain-language equivalent "computer-generated."
- 42 Python API/publication/configuration tests, including real frozen-pipeline inference on an existing **training** example, strict invalid-input handling, unavailable startup, model hash mismatch, runtime mismatch, concurrency/rate limits, feature-importance consistency, unchanged source fingerprints, and 19 local credential-file/CLI checks that use only fake temporary credentials and make no network requests.
- A real local HTTP prediction request using the exported training example returned class 0 from the frozen service. This was an inference smoke test, not a repeat of the final evaluation.
- Local frontend HTTP response: 200. Local API health: ready with the expected research release/model fingerprint.
- Supabase import dry run: 4,315 observations, 21 variable definitions, four original models, five performed evaluations, 11 context indicators, and seven incidents. No database requests were made.
- Both real local configuration files are ignored and untracked. The frontend build succeeds with the separate local publishable-key settings; Vite environment inspection exposes no administrator credential variables. The admin file lives outside the frontend application and is read only by the import CLI.
- Production dependency audit at verification: zero reported vulnerabilities. This is a point-in-time package audit, not a general security guarantee.

The generated research export and original frozen model are fingerprint-checked. Original data files, research outputs, and the one-time final-evaluation artifacts were not re-fitted, re-scored, or modified by this website implementation. API integrity checks run before deserializing the repository-owned joblib artifact.

## User-reported hosted checks

The project owner reported that the Supabase release was published after all six table counts matched, then reported that the hosted access checks and site connection passed. The assistant did not independently authenticate to the hosted project or repeat publication.

## Not yet independently verified

- Actual Render deployment, custom domains, account settings, and cold-start behavior in the user's account.
- Actual Supabase gateway, hosted migration/import, and public-key access in the user's account beyond the owner's reported checks above. The automated SQL/RLS test used local PostgreSQL-compatible PGlite; it does not replace hosted verification.
- Native visual layout on real phones, tablets, and desktop browsers. The in-app browser failed to initialize; Chrome access approval timed out. Component tests mock Recharts and therefore do not establish chart-rendering fidelity or screen-size layout.

Bootstrap breakpoints, responsive CSS, accessible form labels, keyboard menu behavior, exact chart-data alternatives, and reduced-motion rules are implemented. Inspect the site visually before public submission, as described in DEPLOYMENT.md.

One non-failing API-test warning concerns Starlette's deprecated AnyIO BlockingPortal alias. Build output also contains third-party Zod comment-annotation warnings. Neither prevented the successful tests/build.

No cloud resources or paid services were created during verification. Git publication is a separate, subsequently authorized step and does not establish a live deployment.
