# Revelio - Payments Revenue Leakage Diagnostic Platform

Multi-tenant SaaS platform for identifying hidden revenue loss in payment infrastructure. Powered by Claude AI.

---

## Quick start (local Docker demo)

```bash
# 1. Configure
cp backend/.env.example backend/.env
# Edit backend/.env - set ANTHROPIC_API_KEY (placeholder works for boot;
# only /diagnostics/{id}/submit needs a real key).

# 2. Start all services
docker-compose -f docker-compose.demo.yml up --build

# 3. Seed full demo data (in a new terminal, after ~30s)
docker compose -f docker-compose.demo.yml exec backend python demo/seed_demo.py

# 4. Open browser
open http://localhost:3000
```

**Admin login:** `admin@revelio.io` / `Demo1234!`
**Demo client:** `james@acmeretail.com` / `Demo1234!`

## Production / fresh-deploy bootstrap

A fresh deploy auto-seeds default benchmark configs but starts with no users.
Create the first super_admin via:

```bash
curl -X POST https://your-backend/api/v1/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"<min 8 chars>","full_name":"Your Name","org_name":"Your Org"}'
```

Subsequent calls return 409. After this, log in via the UI normally.

## Deploy health endpoints

- `GET /health` - liveness, returns 200 even if the DB is down (process-only)
- `GET /ready` - readiness, returns 503 if Postgres is unreachable
- `GET /` - service banner

---

## Client workflow

1. Sign in → Upload CSV, XLSX, or PDF payment statement
2. Fields auto-extracted — review and submit
3. Or use Manual entry to type metrics directly
4. Analysis runs in background via Claude AI
5. Operator reviews and approves
6. Report appears in Reports for download

## Operator workflow

1. Sign in as admin → switch to Admin mode
2. Approval queue — review AI output, edit narrative, override values
3. AI review — full assumption log, confidence level, override with audit trail
4. Client intelligence — private notes, stage tracking, follow-up dates, upsell signals
5. Benchmarks — edit all AI assumptions live (auth rates, FX leakage, retry uplift, chargeback costs)
6. Approve → released to client

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, Tailwind CSS |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL 16 |
| Queue | Redis + Celery (paid tier); FastAPI BackgroundTasks (free tier) |
| AI | Claude claude-sonnet-4-20250514 |
| File parsing | pandas, pdfplumber, openpyxl |
| PDF export | WeasyPrint + Jinja2 |
| Storage | AWS S3 |
| Auth | JWT + bcrypt |

---

## Structure

```
revelio/
├── backend/app/
│   ├── main.py               FastAPI app
│   ├── core/                 Config, DB, auth
│   ├── models/               ORM models (11 tables)
│   ├── api/routes/           8 route files
│   ├── services/             AI, file parser, PDF gen, S3
│   ├── workers/              Celery tasks (4 job types)
│   └── prompts/              Claude prompts (Lite/Core/Enterprise)
├── frontend/src/app/
│   ├── dashboard/            Client overview
│   ├── submit/               Upload + manual entry
│   ├── results/              Diagnostic results
│   ├── reports/              Downloads
│   ├── admin/                Full operator layer
│   └── auth/                 Login
├── database/schema.sql       Full PostgreSQL schema
├── scripts/setup.py          DB seeder
└── docker-compose.yml
```
