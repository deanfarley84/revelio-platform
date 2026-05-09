# REVELIO PLATFORM — CLAUDE CODE HANDOFF

**Date:** 2026-05-09
**Operator:** Dean Farley (deanfarley84)
**Working directory:** `/Users/deanfarley/Code/revelio-platform/revelio`
**GitHub:** https://github.com/deanfarley84/revelio-platform (private, SSH-authed)
**Render:** Blueprint deployed, currently failing — blocker is missing Render API key for diagnostics

---

## CONTEXT: WHAT REVELIO IS

Multi-tenant SaaS: Payments Revenue Leakage Diagnostic Platform. Merchants submit payment data, AI (Claude Sonnet) analyses it, operator reviews, client receives report. Three tiers (Lite/Core/Enterprise). Built originally in a separate Claude chat session.

**Stack:**
- Frontend: Next.js 14, Tailwind, React Hook Form, Recharts
- Backend: FastAPI (Python 3.12), SQLAlchemy 2.0 async, asyncpg
- DB: Postgres 16
- Cache/Broker: Redis (currently unused — workers disabled)
- AI: Anthropic API, model `claude-sonnet-4-20250514`
- Files: pandas, openpyxl, pdfplumber for parsing; WeasyPrint for PDF reports
- Auth: JWT (HS256) + bcrypt
- Storage: AWS S3 (optional, has local fallback)
- Local dev: Docker Compose with `docker-compose.demo.yml`

**Repo state:**
- Branch: `main`
- Latest commit: `d071344` — "Run jobs inline (free-tier deploy)"
- Three commits total:
  - `61edc80` — Initial commit (78 files + ROI calculator + .gitignore)
  - `f8ee2ff` — Add Render deployment config (render.yaml, fixes)
  - `d071344` — Run jobs inline (free-tier refactor)

---

## DEPLOYMENT STATE

### Render Blueprint
- URL: https://dashboard.render.com/blueprint/exs-d7vg8br7uimc73eo0a0g
- Resources created successfully:
  - ✅ Env group `revelio-shared`
  - ✅ Database `revelio-db` (Postgres, free tier — expires 90 days)
  - ✅ Key Value `revelio-redis` (Redis, free tier, currently unused)
- Resources failing or missing:
  - ❌ `revelio-backend` (web service) — deploy failed, root cause unknown
  - ❌ `revelio-frontend` (web service) — deploy failed, root cause unknown
  - ⚠️ `revelio-worker` and `revelio-beat` — REMOVED from render.yaml (free tier doesn't support workers; jobs now run inline)

### Last user-side action
Manual sync triggered, returned "Resources already up to date". Latest commit `d071344` is on GitHub but unclear whether Render auto-deployed the backend/frontend with the new code. **The actual deploy logs were never read** — that's the immediate blocker.

### Pending env vars (sync: false in render.yaml)
Set these in Render dashboard once you have working URLs:
- `revelio-shared` env group:
  - `ANTHROPIC_API_KEY` — production Anthropic key (Dean said use placeholder for now; he'll add it)
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — only if S3 enabled (not needed for first deploy)
- `revelio-backend`:
  - `CORS_ORIGINS` — set to `["https://revelio-frontend.onrender.com"]` (or actual frontend URL after deploy)
- `revelio-frontend`:
  - `NEXT_PUBLIC_API_URL` — set to `https://revelio-backend.onrender.com` (or actual backend URL)

---

## YOUR JOB IN THIS SESSION

**Primary objective:** get backend and frontend deployed and reachable on `*.onrender.com` URLs. Surface any blockers Dean needs to handle on his return.

**Constraints from Dean:**
- "I authorise everything except billing/payments." Don't upgrade plans, don't add paid services, don't enter credit card info anywhere.
- Don't add external API keys or services that cost money.
- Don't push breaking changes — verify before commit.
- British English. No em dashes in code comments or commit messages. Match existing code style.

---

## IMMEDIATE NEXT STEPS

### Step 1: Get a Render API key
Dean is leaving and may or may not paste an API key. Check the chat history for a string starting with `rnd_`. If present, use it. If not, you cannot drive Render's API — proceed to Step 4 (do what you can locally) and leave a clear status note.

If you have the key, store it in `~/.revelio_render_key` (chmod 600) so it's not committed:
```bash
chmod 600 ~/.revelio_render_key
echo "RENDER_API_KEY=rnd_..." > ~/.revelio_render_key
```

### Step 2: Get deploy logs via Render API

```bash
RENDER_KEY=$(grep RENDER_API_KEY ~/.revelio_render_key | cut -d= -f2)

# List services to get IDs
curl -s -H "Authorization: Bearer $RENDER_KEY" \
  "https://api.render.com/v1/services?limit=20" | jq '.[] | {id: .service.id, name: .service.name, type: .service.type, status: .service.suspended}'

# Get most recent backend deploy (replace SRV_ID)
curl -s -H "Authorization: Bearer $RENDER_KEY" \
  "https://api.render.com/v1/services/SRV_ID/deploys?limit=5" | jq

# Get logs for a specific deploy
curl -s -H "Authorization: Bearer $RENDER_KEY" \
  "https://api.render.com/v1/services/SRV_ID/deploys/DEPLOY_ID" | jq
```

API docs: https://api-docs.render.com/

### Step 3: Diagnose

Common likely causes for backend deploy failure:

1. **WeasyPrint missing system libs** — Dockerfile already installs `libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf2.0-0`, `libffi-dev`. Should be fine, but check the build log.
2. **`asyncpg` connection error** — Render's `DATABASE_URL` starts with `postgres://` but asyncpg needs `postgresql+asyncpg://`. The code in `backend/app/core/database.py` does the rewrite (`postgresql://` → `postgresql+asyncpg://`), but if Render gives `postgres://` (older Postgres URL prefix), the rewrite misses it. Fix: handle both `postgres://` and `postgresql://`.
3. **Pydantic Settings env file missing** — `Settings.Config.env_file = ".env"` looks for `.env` in working dir. On Render, env comes from env vars, but pydantic-settings may complain. Usually harmless.
4. **Health check timing** — `/health` route exists in `main.py`. But the lifespan does table-create which can be slow on first boot; if it exceeds Render's health check timeout (default 30s), deploy fails.
5. **Missing model imports** — Lifespan does `from app.models import user` to register models with Base. All 11 tables are in `user.py` so a single import is fine.
6. **Frontend `npm ci` cache miss** — `package-lock.json` was generated locally with Node 20.20.2 npm 10.8.2. Render Docker uses `node:20-alpine`. Should be compatible.

### Step 4: Push fixes

If the diagnosis points to a code fix:
```bash
cd /Users/deanfarley/Code/revelio-platform/revelio
# edit files
git add .
git commit -m "Fix: <what>"
git push
```

Render auto-deploys on push (autoDeploy: true in render.yaml). No need to manually trigger.

### Step 5: Trigger redeploy if needed

If you've pushed but Render hasn't picked up the change:
```bash
curl -X POST -H "Authorization: Bearer $RENDER_KEY" \
  "https://api.render.com/v1/services/SRV_ID/deploys" \
  -H "Content-Type: application/json" \
  -d '{"clearCache": "do_not_clear"}'
```

### Step 6: Set env vars via API once URLs are known

```bash
# Update CORS_ORIGINS on backend
curl -X PUT -H "Authorization: Bearer $RENDER_KEY" \
  "https://api.render.com/v1/services/BACKEND_SRV_ID/env-vars" \
  -H "Content-Type: application/json" \
  -d '[{"key":"CORS_ORIGINS","value":"[\"https://revelio-frontend.onrender.com\"]"}]'

# Update NEXT_PUBLIC_API_URL on frontend
curl -X PUT -H "Authorization: Bearer $RENDER_KEY" \
  "https://api.render.com/v1/services/FRONTEND_SRV_ID/env-vars" \
  -H "Content-Type: application/json" \
  -d '[{"key":"NEXT_PUBLIC_API_URL","value":"https://revelio-backend.onrender.com"}]'
```

---

## FILE STRUCTURE OVERVIEW

```
/Users/deanfarley/Code/revelio-platform/revelio/
├── render.yaml                 # Render blueprint (services, db, redis, env group)
├── docker-compose.demo.yml     # Local demo via Docker
├── .gitignore
├── README.md
├── Makefile
├── backend/
│   ├── Dockerfile              # Python 3.12-slim + Cairo/Pango for WeasyPrint
│   ├── requirements.txt
│   ├── alembic/                # Migrations dir (NO migrations generated yet)
│   └── app/
│       ├── main.py             # FastAPI app + lifespan that auto-creates tables
│       ├── core/
│       │   ├── config.py       # Pydantic Settings, reads env vars
│       │   ├── database.py     # SQLAlchemy async engine, postgresql:// → postgresql+asyncpg://
│       │   └── auth.py         # JWT + bcrypt
│       ├── models/
│       │   └── user.py         # ALL 11 tables in one file (Organisation, User, Diagnostic, BenchmarkConfig, UploadedFile, ClientIntel, ClientIntelLog, Job, AuditLog, Notification, ReportExport)
│       ├── api/routes/
│       │   ├── auth.py
│       │   ├── diagnostics.py  # Refactored: uses inline_jobs (no Celery)
│       │   ├── files.py        # Refactored: uses inline_jobs
│       │   ├── reports.py      # Refactored: uses inline_jobs
│       │   ├── admin.py
│       │   ├── benchmarks.py
│       │   ├── intel.py
│       │   └── notifications.py
│       ├── services/
│       │   ├── ai_service.py
│       │   ├── file_parser.py
│       │   ├── report_generator.py
│       │   ├── storage.py      # S3 with local fallback
│       │   └── inline_jobs.py  # NEW: parse/analyse/report/notify functions, async
│       ├── workers/            # Celery code retained but not running
│       │   ├── celery_app.py
│       │   └── tasks.py        # Wraps inline_jobs functions when workers re-enabled
│       └── prompts/
│           └── diagnostic_prompts.py  # The Claude system prompt for analysis
├── frontend/
│   ├── Dockerfile              # node:20-alpine, multi-stage, expects standalone output
│   ├── package.json
│   ├── package-lock.json       # Generated for deterministic builds
│   ├── next.config.js          # output: 'standalone'
│   └── src/
│       ├── app/
│       │   ├── dashboard/      # Client overview
│       │   ├── submit/         # Upload + manual entry
│       │   ├── results/        # Diagnostic list + detail
│       │   ├── reports/
│       │   ├── roi/page.tsx    # NEW: ROI calculator (343 lines)
│       │   ├── admin/          # Operator dashboard (queue, intel, clients, benchmarks, ai-review, pipeline, roles)
│       │   └── auth/
│       ├── components/
│       │   ├── layout/         # AppShell, Sidebar (with ROI nav entry), Topbar
│       │   ├── ui/, charts/, forms/
│       └── lib/
│           ├── api.ts          # axios + endpoint helpers
│           └── auth-context.tsx
├── database/                   # SQL seed scripts (used by docker-compose demo)
├── demo/                       # Demo seeds (4 demo orgs, all passwords Demo1234!)
├── docker/
├── docs/
└── scripts/
```

---

## KEY GOTCHAS DOCUMENTED

### 1. `Notification.metadata` reserved name
SQLAlchemy `DeclarativeBase` reserves `metadata`. Original code had `metadata = Column(JSONB)` which fails at class construction. **Already fixed** in commit `f8ee2ff`:
```python
extra_metadata = Column("metadata", JSONB)  # column name preserved, attr renamed
```
References updated in `routes/notifications.py` and `workers/tasks.py`. API still returns key `"metadata"` to clients for compatibility.

### 2. `postgres://` vs `postgresql://`
Render's older Postgres URLs may use `postgres://`. Current code:
```python
async_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
```
This misses `postgres://` prefix. **Likely fix needed:**
```python
async_url = settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)
```
Worth checking the actual `DATABASE_URL` Render provides via the API before changing.

### 3. Lifespan auto-creates tables
`backend/app/main.py` lifespan calls `Base.metadata.create_all` on startup. Early-stage convenience — should be replaced with proper Alembic migrations before real customer data lands. NOT a blocker for first deploy.

### 4. Workers disabled
Free tier doesn't support background workers. `render.yaml` has them commented out. All async jobs run synchronously inside API requests via `app/services/inline_jobs.py`. POST /diagnostics/{id}/submit will block 10–30s during AI analysis. To re-enable: uncomment worker blocks in render.yaml AND upgrade plan to Starter.

### 5. ANTHROPIC_API_KEY placeholder
Dean did not provide a production key. Backend will boot fine but `/diagnostics/{id}/submit` calls will fail when Claude is invoked. This is expected. Don't try to "fix" by providing a fake key — the placeholder doesn't matter until someone actually tries to submit a diagnostic.

### 6. CORS
Backend's `CORS_ORIGINS` is empty until set. Frontend will hit CORS errors on API calls until backend's CORS list includes the frontend URL. Order matters: deploy first, get URLs, then set CORS, then test.

---

## DEMO CREDENTIALS (for local demo, not relevant to Render deploy)

- Admin: `admin@revelio.io` / `Demo1234!`
- Demo client: `james@acmeretail.com` / `Demo1234!`
- All demo passwords: `Demo1234!`

These come from `backend/demo/seed_demo.py`. Run on Render via shell tab in service:
```bash
cd /app && python demo/seed_demo.py
```

But: don't auto-seed prod. Only seed if Dean specifically asks.

---

## DEAN'S OPERATING PREFERENCES (BAKED IN)

- British English. No em dashes (use hyphens or commas).
- Direct, no fluff. Lead with the point.
- Cite uncertainty. If you don't know, say so. Don't fabricate.
- Revenue filter: every action should protect/generate/scale revenue.
- Decision gate: anything over £5k or reputational exposure → wait for Dean.
- "AI drafts, I decide. AI structures, I validate. AI accelerates, I verify."
- Dean is in Marbella. ADHD-aware: short sections, lead with point, flag decisions.

---

## STATUS REPORT FORMAT (LEAVE THIS WHEN DONE)

When Dean returns, leave a `HANDOFF_STATUS.md` in `/Users/deanfarley/Code/revelio-platform/revelio/` with:

```markdown
# Status as of <timestamp>

## What worked
- ...

## What's still failing
- ...

## Diagnosis (if any failure)
- Root cause:
- Fix attempted:
- Result:

## Next decision needed from Dean
- ...
```

Don't fill it with reassurance. Be blunt about what works and what doesn't.

---

## RENDER API CHEATSHEET

```bash
# All endpoints require: -H "Authorization: Bearer $RENDER_KEY"
BASE="https://api.render.com/v1"

# Services
GET  $BASE/services?limit=20
GET  $BASE/services/SRV_ID
GET  $BASE/services/SRV_ID/env-vars
PUT  $BASE/services/SRV_ID/env-vars        # body: array of {key, value}

# Deploys
GET  $BASE/services/SRV_ID/deploys?limit=10
GET  $BASE/services/SRV_ID/deploys/DEP_ID
POST $BASE/services/SRV_ID/deploys          # trigger redeploy

# Blueprint syncs
GET  $BASE/blueprints
POST $BASE/blueprints/BP_ID/syncs           # trigger sync

# Logs (newer endpoint)
GET  $BASE/logs?ownerId=OWNER&resource=SRV_ID&startTime=...&endTime=...
```

Workspace ID: `tea-d7vg50egvqtc73clfn4g`
Blueprint ID: `exs-d7vg8br7uimc73eo0a0g`

---

## END OF HANDOFF
