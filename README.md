# Revelio — Payments Revenue Leakage Diagnostic Platform

Multi-tenant SaaS platform for identifying hidden revenue loss in payment infrastructure. Powered by Claude AI.

---

## Quick start

```bash
# 1. Configure
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY, POSTGRES_PASSWORD, JWT_SECRET

# 2. Start all services
docker-compose up --build

# 3. Seed database (in new terminal, after ~30s)
pip install psycopg2-binary passlib[bcrypt] python-dotenv
python scripts/setup.py

# 4. Open browser
open http://localhost:3000
```

**Admin login:** `admin@revelio.io` / `Admin1234!`
**Demo client:** `james@acmeretail.com` / `demo1234`

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
| Queue | Redis + Celery |
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
