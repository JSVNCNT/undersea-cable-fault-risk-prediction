# Your setup and launch checklist

The website source, exported research snapshot, frozen inference service, SQL, and Render configuration are provided. No cloud accounts, databases, deployments, or paid services were created by this work. Git publication is separate from cloud deployment.

Recommended order: **preview locally → optionally set up Supabase → review/push when you choose → deploy API → deploy frontend → connect and verify.**

## 1. Preview and inspect locally first

Follow [README.md](README.md#start-here). Open all eight pages and test filters and downloads. Start the Python API and try the existing training example on the Prediction demo.

Before sharing, check a narrow phone screen, tablet, and desktop in your browser. Use the menu button on smaller screens, scroll wide tables inside their containers, and verify that chart labels and form controls remain readable. Automated component tests do not prove pixel-perfect real-device layout.

No commit is required to preview. **Do not commit/push until you are ready.** Existing unrelated repository changes must be reviewed separately; do not blindly stage everything.

## 2. Supabase: optional published-data storage

The research pages already work in bundled mode. Use Supabase when you want hosted, queryable published research tables. It does not run sklearn and is not required by the Python inference service.

### Create the project and tables

1. In your own Supabase account, create a new project and keep its database password private.
2. Open **SQL Editor**. Paste the entire contents of `website/supabase/001_research_schema.sql` and run it **once in the new project**. Do not paste a filename or the CSV into the SQL editor. The script is a fresh-project migration, not a general-purpose repeated reset script.
3. In the project's connection/API settings, find the **Project URL**, **publishable key**, and a **secret/admin key**. Dashboard labels can change; use Supabase's [official API-key guide](https://supabase.com/docs/guides/getting-started/api-keys).

The SQL creates these research tables:

| Table                     | One row represents                                              |
| ------------------------- | --------------------------------------------------------------- |
| `dataset_versions`        | One exported release and its dashboard summary/provenance       |
| `cable_year_observations` | One eligible generated cable-year in a release                  |
| `variable_definitions`    | One original variable's definition and treatment                |
| `model_versions`          | One original candidate and its saved settings                   |
| `evaluation_results`      | One performed model/period evaluation, not a placeholder        |
| `source_context`          | One sourced sector statistic with scope and period              |
| `historical_incidents`    | One selected sourced incident; unknown cable counts remain NULL |

`annual_observation_summary` is a read-only descriptive view. It retains caller permissions/RLS; it is not a live performance calculation. The dashboard-summary payload and normalized tables are generated from the same existing exported evidence, not manually invented seed data.

### Import the actual exported records

First, from the repository root, inspect the dry run:

```powershell
python website\scripts\import_supabase.py
```

Expected: 4,315 observations, 21 variable definitions, four models, five performed evaluations, 11 context indicators, and seven selected incidents. A dry run makes no network requests.

When you are ready to write to **your new project**, use process-only environment values. Enter the secret through a masked prompt, not a literal command, file, chat message, or frontend environment variable:

```powershell
$env:SUPABASE_URL = Read-Host 'Supabase project URL (https://YOUR-PROJECT.supabase.co)'
$supabaseSecureKey = Read-Host 'Supabase SECRET/admin key (not publishable)' -AsSecureString
$supabaseCredential = [System.Net.NetworkCredential]::new('', $supabaseSecureKey)
$env:SUPABASE_SECRET_KEY = $supabaseCredential.Password
try {
    python website\scripts\import_supabase.py --publish
} finally {
    Remove-Item Env:SUPABASE_SECRET_KEY -ErrorAction SilentlyContinue
    $supabaseCredential = $null
    $supabaseSecureKey = $null
}
```

This is the command that writes the research records. The importer publishes the release only after table counts reconcile. It refuses to overwrite an already published release. If interrupted while unpublished, fix the reported issue and resume the same approved export; do not delete tables or make up missing rows.

Run `website/supabase/002_verify_access.sql` in SQL Editor. Confirm:

- Training: 2,960 rows / 570 positives; validation: 891 / 170; final test: 464 / 78.
- Four validation evaluations and only one final evaluation, for Random Forest.
- RLS enabled on all seven tables, with public SELECT-only policies/grants.
- Literal `None` stays a chokepoint category; unknown incident counts stay NULL.

### Connect the frontend

In a local ignored `website/.env.local`, or later in the Render **static site's** environment settings, use:

```dotenv
VITE_DATA_MODE=supabase
VITE_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
VITE_API_URL=https://YOUR-API.onrender.com
```

For a local API, use `http://127.0.0.1:8000` instead. Restart local Vite after changes. A deployed static site must be rebuilt after environment changes.

**Only the publishable key goes into `VITE_*`.** Supabase [secret keys bypass RLS](https://supabase.com/docs/guides/getting-started/api-keys) and must never enter browser assets. [RLS and table grants](https://supabase.com/docs/guides/database/postgres/row-level-security) enforce public read-only access; hiding buttons is not security. There are no public write forms, visitor accounts, or scenario persistence.

## 3. Render: deploy the inference API first

When you authorize a later commit/push, make the reviewed `website/` folder and root `render.yaml` available in the Git repository connected to your Render account. Include `website/backend/artifacts/random_forest.joblib` and `manifest.json`; they are the deployable frozen model copy, not the original ignored development-model directory. Never include `.env.local`, secrets, node_modules, caches, or generated `dist`.

Manual creation is easiest for the first launch because you learn each real URL before connecting the services:

1. Render → **New Web Service** → connect your repository/branch.
2. Runtime: **Python**. Root directory: `website/backend`.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1`.
5. Health-check path: `/api/health`.
6. Set `PYTHON_VERSION=3.13.14`, `OMP_NUM_THREADS=1`, and `OPENBLAS_NUM_THREADS=1`.
7. Set `ALLOWED_ORIGINS` to your exact eventual frontend origin, such as `https://YOUR-WEBSITE.onrender.com`. It can initially contain a known temporary/local origin; update it once the actual static-site URL is assigned. Never use `*` or include a page path.
8. Review the available plan and limits yourself. The provided blueprint requests a free API plan; no purchase is needed for local work and none is authorized automatically.
9. After deployment, open `https://YOUR-API.onrender.com/api/health`. Require `status: ready` and the expected model/release fingerprint before relying on the demonstration.

Render's [FastAPI instructions](https://render.com/docs/deploy-fastapi), [Python-version configuration](https://render.com/docs/python-version), and [monorepo root-directory rules](https://render.com/docs/monorepo-support) explain these settings. Files outside the chosen backend root are unavailable to the deployed API; that is why its artifact copy is self-contained.

## 4. Render: deploy the React frontend

1. Render → **New Static Site** → same repository/branch.
2. Root directory: `website`.
3. Build command: `npm ci && npm run build`.
4. Publish directory: `dist` (relative to the root directory).
5. Set `NODE_VERSION=24.15.0` and `VITE_API_URL=https://YOUR-API.onrender.com`.
6. Choose `VITE_DATA_MODE=bundled` for the included immutable snapshot, or `supabase` with the two public Supabase values above. Do not choose Supabase mode before importing/publishing the release.
7. Add a **Rewrite**: source `/*`, destination `/index.html`. This makes direct links such as `/models` and browser refreshes work with React Router.
8. Deploy, copy the **actual** frontend URL, and put that exact origin in the API's `ALLOWED_ORIGINS`. Redeploy/restart the API after that change.

The root `render.yaml` provides the equivalent two-service [Blueprint configuration](https://render.com/docs/blueprint-spec), including SPA routing and basic response headers. If using Blueprints, review resource names first so they do not collide with existing services. Its unsupplied API URL/CORS values still need your real service origins; it cannot invent them.

## 5. Final launch checks

- All eight pages load, including opening `/dataset` or `/models` directly and refreshing.
- Data mode says **Published snapshot** or **Supabase release** as intended.
- Combined filters update descriptive counts and exports. Clearing filters restores 4,315 rows. Model benchmarks remain unchanged.
- Validation comparison includes four models. Final-test comparison shows three **Not evaluated** entries and only the original Random Forest result.
- API health says ready; the training example returns an actual model result. Clearing/changing inputs clears the old result.
- A stopped/unreachable/mismatched API shows **Prediction service unavailable**, never a mock prediction.
- Public Supabase writes are not granted. No secret/admin key appears in any browser variable, repository file, or screenshot.
- Phone/tablet/desktop layout, keyboard menu operation, table scrolling, and chart readability have been checked in your browser.
- Source links, data-origin disclosure, and limitations remain visible.

Render [free web services](https://render.com/docs/free) can spin down after 15 idle minutes and take about a minute to wake. That affects the Python API, not the static analytics frontend. Open the API health page ahead of your defense, allow startup time, and recheck the service in the demonstration. A timeout must stay an unavailable state. Upgrading a plan is your optional account decision, not something this project does automatically.

## Troubleshooting

| Symptom                                | Check                                                                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| PowerShell blocks `npm.ps1`            | Use `npm.cmd`; do not change global execution policy                                                                          |
| Prediction service unavailable locally | Keep both terminals open, verify `/api/health`, set `VITE_API_URL`, restart Vite                                              |
| API health returns 503                 | Check model artifact/manifest inclusion and exact model-library versions in Render logs; do not retrain to resolve deployment |
| Browser CORS error                     | API `ALLOWED_ORIGINS` must exactly match the website origin, without a trailing page path                                     |
| Supabase research data unavailable     | Confirm migration/import/publication, correct release, project URL, publishable key, RLS/grants, and frontend rebuild         |
| Refreshing a route returns 404         | Add the static-site SPA rewrite                                                                                               |
| API cold start                         | Wait for readiness and recheck; do not substitute example scores                                                              |

## Verification limits of this handoff

The production build, typed data checks, API tests, and local PostgreSQL policy test are local checks. No live Supabase gateway, Render build, domain, or billing account has been exercised. Native visual browser verification was unavailable because the preview tool failed to initialize and Chrome access approval timed out. Inspect the running site yourself before public submission. Nothing here re-evaluates the final test or claims a deployed production system.
