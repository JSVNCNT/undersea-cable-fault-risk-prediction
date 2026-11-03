# Undersea Research Analytics

A React/TypeScript research dashboard and Python prediction demonstrator for Group 5 xam.py's Introduction to Data Science study:

**Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems Using Infrastructure and Operational Indicators**

The website is implemented and ready for Git publication. Render and Supabase have **not** been provisioned or connected to your accounts. Publishing the repository does not deploy those services. See [TEAM.md](TEAM.md) for the contribution roles reported by the project owner.

## Start here

Open a PowerShell terminal in the project root:

```powershell
cd C:\Users\Vincent\Documents\undersea-cable-fault-risk-prediction
```

For the frontend, use another terminal:

```powershell
cd C:\Users\Vincent\Documents\undersea-cable-fault-risk-prediction\website
npm.cmd ci
$env:VITE_API_URL = 'http://127.0.0.1:8000'
npm.cmd run dev -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173**. Keep this terminal running. `npm.cmd` works in PowerShell without changing your script execution policy. Node 24 is recommended; the supplied Render configuration pins Node 24.15.0.

The research pages work immediately from the included published snapshot. Actual predictions require the Python service below. Without it, the prediction page explicitly reports that the service is unavailable and never produces a mock result.

## Start the prediction service

The existing project `.venv` already has the model libraries; FastAPI, Pydantic, and Uvicorn were installed during implementation. From the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn website.backend.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Open **http://127.0.0.1:8000/api/health**. Expect `"status":"ready"`. Then open the website's Prediction demo, choose **Load training example**, and choose **Run demonstration**. The example is an existing training record, not a new research observation or a final-test evaluation.

For a clean, separate API environment on another computer, use Python **3.13.14** and the supplied exact model-runtime requirements:

```powershell
py -3.13 -m venv website\backend\.venv
.\website\backend\.venv\Scripts\python.exe -m pip install -r website\backend\requirements.txt
.\website\backend\.venv\Scripts\python.exe -m uvicorn website.backend.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Do not casually upgrade scikit-learn, NumPy, pandas, or joblib for the saved model. Readiness fails closed on incompatible versions or a model fingerprint mismatch. Only the repository-owned, fingerprint-checked artifact is loaded; there is no model-upload endpoint.

## What is included

| Page                 | Working interactions                                                                                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overview             | Year/route/partition filters, linked descriptive charts and counts, exact chart-data table                                                                             |
| Dataset explorer     | Cable-ID search, combined filters, sortable columns, pagination, indicator-column selector, full-record inspection, filtered CSV export, searchable dictionary         |
| Models & results     | Metric selector, validation/final-test switch, saved-results CSV download, explanations of all four models                                                             |
| Prediction demo      | All 13 inputs grouped by indicator type, field explanations, input validation, training-example loader, reset, health recheck, real API request, downloadable scenario |
| Model interpretation | Original/encoded importance views, top-10/all selector, validation/final confusion matrices, exact values and error counts                                             |
| Methodology          | Preparation, missing-value safeguards, temporal eligibility, chronological splits, model selection, frozen final-evaluation policy                                     |
| Research summary     | Evidence-grounded defense explanations, copy/download brief, expandable questions                                                                                      |
| About & sources      | Purpose, intended uses, limitations, separately sourced sector context and historical incidents, provenance export                                                     |

Bootstrap's grid provides responsive breakpoints. Tailwind and locally owned shadcn-style components provide styling/composition; Recharts supplies charts; React Router supplies navigation; Lucide supplies icons. Bootstrap JavaScript is not needed. Forms and native disclosure controls have labels, keyboard support, reduced-motion styling, and readable empty/error states. Mobile navigation closes with Escape.

## Research boundaries

- The publisher declares the dataset **100% computer-generated (synthetic)**. It is not an authenticated real-cable fault registry.
- The original panel has 4,821 rows. This website exposes the 4,315 eligible supervised cable-years: training 2,960, validation 891, final test 464.
- All four candidates have saved validation scores. **Only Random Forest has a final-test score.** Other final evaluations are displayed as **Not evaluated**, never zero.
- The original frozen Random Forest's one-time final evaluation was already completed on **2 November 2026**. This website does not repeat it or change the model-selection decision.
- The 13 source predictors have no missing values. Training-only median/mode imputers are configured safeguards, not evidence that values were replaced. Missing target labels are never imputed.
- `pr_auc` in the saved CSVs means **average precision**, not trapezoidal PR area.
- A model score is not calibrated real-world fault probability, causal evidence, or an operational warning. Source-backed ITU/ICPC/TeleGeography context remains separate from generated cable IDs.
- Visitor scenarios are neither saved to Supabase nor added to the research dataset. They do not alter published results. Dataset filters do not re-score models.

## Supabase and Render

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for the exact steps on your end, SQL to paste, import command, key separation, Render settings, and launch checklist. Supabase is optional for preview: bundled mode is an intentional published snapshot, not a fabricated fallback. In Supabase mode, failures are reported rather than silently switching data sources.

## Configuration

`website/.env.example` documents the available frontend values. If desired, copy it to `.env.local`, which is ignored by Git. Restart Vite after changing it; rebuild a hosted frontend after environment changes.

| Variable                        | Meaning                                                                             |
| ------------------------------- | ----------------------------------------------------------------------------------- |
| `VITE_DATA_MODE`                | `bundled` (default) or `supabase`                                                   |
| `VITE_API_URL`                  | Python service origin, e.g. `http://127.0.0.1:8000`; blank disables live inference  |
| `VITE_SUPABASE_URL`             | HTTPS project origin, only needed for Supabase mode                                 |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Browser-safe publishable key; never an admin/secret key                             |
| `ALLOWED_ORIGINS`               | Backend-only comma-separated exact frontend origins; default allows local port 5173 |

All `VITE_*` values become public browser assets. Never put a Supabase secret, service-role key, database password, or private API credential there.

For convenient local setup, fill the two ignored files separately:

- Repository-root `.supabase-admin.local.env`: `SUPABASE_URL` and `SUPABASE_SECRET_KEY`, read only by the administrator importer. This file takes precedence over old PowerShell values. If missing, create it from `.supabase-admin.local.env.example`.
- `website/.env.local`: `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` only. After a successful import, set `VITE_DATA_MODE=supabase` and restart Vite. Its initial bundled mode preserves the working preview until data is ready.

From the repository root, run `python website/scripts/import_supabase.py --check-config` to check settings without displaying credentials or connecting. Use `--publish` only when you intend to import. Git-ignore prevents normal Git staging, not local plaintext access; keep the admin file private. Neither real file belongs in a commit, and no secret belongs in `.env.example`.

## Files to open when explaining the implementation

| File                               | Purpose                                                                            |
| ---------------------------------- | ---------------------------------------------------------------------------------- |
| `src/App.tsx`                      | Navigation, research loading, routing, failure states                              |
| `src/pages.tsx`                    | Eight research pages and their controls                                            |
| `src/lib/data.ts`                  | Typed schemas, dataset loading, filters, CSV output                                |
| `src/lib/api.ts`                   | Typed client and prediction-service checks                                         |
| `backend/app.py`                   | Input validation and frozen sklearn pipeline inference                             |
| `scripts/export_research.py`       | Copies existing research evidence into a website release; no fitting or evaluation |
| `scripts/import_supabase.py`       | Dry-run by default; explicit admin publication only with `--publish`               |
| `supabase/001_research_schema.sql` | Tables, indexes, comments, public read-only RLS, safe summary view                 |
| `../render.yaml`                   | Separate static frontend and Python service configuration                          |

Generated website data are in `public/data/research.json` and `observations.json`. Each observation is one cable-year; each research/model record retains its period and meaning. The model copy and manifest live in `backend/artifacts/`, outside the public static directory.

## Verification commands

From `website`:

```powershell
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest website\backend -q
python website\scripts\import_supabase.py
```

The last command is a **local dry run**, with no network or database mutation. The frontend tests include a local PostgreSQL-compatible SQL/RLS test and DOM interaction tests. Test-only inference fixtures are not published research results. These tests do not substitute for a real-device visual review or verification in your actual Supabase/Render accounts.

Do **not** run `scripts/run_pipeline.py` or the final-holdout evaluation runner just to start this website. Those belong to the separate research workflow. If intentionally republishing an existing approved release, `python website/scripts/export_research.py` only reads the source files and writes website publication assets; review the release and rebuild/import consistently.
