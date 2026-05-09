# REVELIO — TEST MODE AND DEMO SANDBOX BRIEF

**Last updated:** 2026-05-09
**Status:** Phase 1 ready to build next session. Phase 2 deferred until client #1 signs.

## Context

The platform is live at:

- Frontend: https://revelio-frontend-38kb.onrender.com
- Backend: https://revelio-backend-r8u3.onrender.com
- Repo: https://github.com/deanfarley84/revelio-platform (main, SSH-authed)
- Working dir: `/Users/deanfarley/Code/revelio-platform/revelio`
- Helper: `./scripts/render-cli.sh` reads `~/.revelio_render_key`

Currently the database has exactly one user (`deanfarley84@gmail.com`, super_admin in the "Revelio Operator" org). Every list view is empty. The ROI calculator runs in its baked-in demo state because there are no released diagnostics.

This brief covers two phases of test/demo capability. Phase 1 is mechanical seeding for now; Phase 2 is a public sandbox for prospects, only worth building once a paying client exists.

## Constraints (carried over from prior briefs)

- British English. **No em dashes anywhere** in code, comments, copy, commit messages, or chat. Use commas or hyphens.
- Match existing code style. Concise comments only when intent is non-obvious.
- Smallest correct change that satisfies acceptance criteria.
- Verify each change builds (`cd frontend && npm run build` and a backend syntax check) before committing.
- One commit per task. Message format: `Test mode: <task>` or `Demo sandbox: <task>` as appropriate.
- Push to `main` after each commit; Render auto-deploys.
- After all tasks, write `TEST_MODE_LOG.md` in repo root with what shipped, deviations, blockers, and next ideas. Don't commit unless asked.

---

## PHASE 1 — Test mode via seeded data (build next session)

### Decisions already taken

| Question | Answer |
|---|---|
| Test password for demo accounts | Single shared password: `Demo1234!` |
| Visual marker for test data | Amber tag on every demo org and diagnostic |
| One-click wipe endpoint | Yes, build it |
| Live Anthropic test submission | Yes, do one against a separate non-seeded org. Budget ~£0.30-£1. |

### Goals

1. Dean can log in as a customer (client_admin) and see the platform from the merchant side.
2. Dean can stay on his super_admin login and see those same orgs from the operator side.
3. Every list view (`/dashboard`, `/admin/queue`, `/admin/clients`, `/results`, `/reports`, `/admin/pipeline`) has populated rows.
4. The ROI calculator at `/roi` shows real released-diagnostic data in the dropdown, not just demo mode.
5. Test data is visually distinct (amber tag) and wipeable in one click.

### Architecture

- **Seed endpoint:** `POST /admin/seed-test-data`. super_admin only. Idempotent: refuses if a non-demo (real) client org already exists. Returns a summary of what was created.
- **Wipe endpoint:** `DELETE /admin/seed-test-data`. super_admin only. Removes only orgs flagged `is_demo=true` and their dependent rows.
- **Demo flag:** add `is_demo: bool` column to `Organisation` (and copy to `Diagnostic.is_demo` denormalised for fast filtering and clear PDF watermarking later if wanted). Default `false`. Existing real orgs untouched.
- **AI output:** seeded diagnostics carry hand-crafted `output` JSON matching the production AI schema (financial_breakdown, annual_leakage_estimate {low, mid, high}, narrative, confidence levels, recommended_priorities). No Anthropic calls. Zero spend.
- **PDF reports:** seeded released diagnostics get one pre-generated PDF entry in `ReportExport` so the download flow works end-to-end without a re-render. Backfill from a one-shot generate call inside the seed endpoint.

### Demo orgs to seed

| Org | Tier | Diagnostic state | Why |
|---|---|---|---|
| Acme Retail (demo) | core | released | Feeds ROI calculator with real driver data; tests the full client-side report flow. |
| Globex Travel (demo) | enterprise | pending_review | Tests the operator approval flow on `/admin/queue`. |
| Tinker Goods (demo) | lite | draft | Tests the submission and processing flow when Dean clicks Submit. |

Each org gets:

- 1 `client_admin` user: `admin@<slug>.demo` / `Demo1234!`
- 1 `client_viewer` user: `viewer@<slug>.demo` / `Demo1234!`

User emails:

- admin@acme-retail.demo
- viewer@acme-retail.demo
- admin@globex-travel.demo
- viewer@globex-travel.demo
- admin@tinker-goods.demo
- viewer@tinker-goods.demo

### Diagnostic content

For each demo org, hand-craft a financial_breakdown that's plausible for the org persona:

- **Acme Retail (mid-market UK retailer, Core tier, released):**
  - Authorisation loss: £480k loss, mid confidence
  - Cross-border performance: £180k loss, medium confidence
  - FX leakage: £220k loss, high confidence
  - Retry logic: £95k loss, high confidence
  - annual_leakage_estimate: low £620k, mid £975k, high £1.32m
  - narrative: 2-3 paragraphs in Dean's voice, British English, no em dashes
- **Globex Travel (enterprise travel marketplace, pending review):**
  - Cross-border performance: £1.2m loss
  - Routing inefficiency: £680k loss
  - Payment method gaps: £540k loss (no LPMs in DACH/Nordics)
  - FX leakage: £310k loss
  - Chargeback admin: £180k loss
  - annual_leakage_estimate: low £2.1m, mid £2.91m, high £3.85m
- **Tinker Goods (small DTC, lite tier, draft):**
  - Empty financial_breakdown; just a started submission with files/a few free-text fields

### Tasks (do in order)

1. **Schema:** add `is_demo: bool DEFAULT false` to `Organisation`. Migrate via `Base.metadata.create_all` since Alembic isn't wired (consistent with prior pattern). Build, push.
2. **Seed endpoint:** `POST /admin/seed-test-data` creates the three demo orgs, six users, three diagnostics, and the report exports. Returns a JSON summary of what was created. Refuses if a real org exists. Idempotent: if demo orgs already present, regenerates them in place after deleting the old ones (clean re-seed).
3. **Wipe endpoint:** `DELETE /admin/seed-test-data` removes everything flagged `is_demo=true`. Cascades to users, diagnostics, files, reports, notifications. Returns count of rows removed.
4. **Amber tag UI:** add a `tag-amber` next to the org name wherever an org appears in admin views (Dashboard, Queue, Clients, Reports list, Diagnostic detail header). On the diagnostic list view, prepend a small "DEMO" tag to the row. Backend serialisers expose `is_demo` on org and diagnostic responses.
5. **Live Anthropic test:** create a separate, non-seeded org (`Live Test (Dean)`), submit a small diagnostic, watch it run end to end through `submit -> processing -> ai_complete -> pending_review -> released`. Confirm cost in Anthropic console. Budget cap on Anthropic key should already be set (Dean's call).
6. **Documentation:** write `TEST_MODE_LOG.md` summarising what shipped, the credentials Dean uses to log in as each persona, and any deviations. Don't commit unless asked.

### Acceptance for Phase 1

- `POST /admin/seed-test-data` returns `{"created": {...}}` with the three orgs, six users, three diagnostics, and one PDF report export.
- Logging in as `admin@acme-retail.demo` / `Demo1234!` shows only Acme's diagnostics; admin nav is hidden.
- Logging back in as `deanfarley84@gmail.com` shows all three demo orgs in the operator views with amber `DEMO` tags.
- The ROI calculator dropdown lists the released Acme diagnostic; selecting it hydrates the drivers from the financial_breakdown.
- `DELETE /admin/seed-test-data` returns to the empty state cleanly. Real users (Dean) untouched.
- The Live Test org is unaffected by the wipe.

---

## PHASE 2 — Guest demo sandbox (build when client #1 signs)

### Trigger

The moment a real, paying client puts real data in the production DB. Not before. Pre-revenue, the seeded demo orgs above are the same outcome with less infra overhead.

### Why this becomes worth building then

1. Real client data must not be visible to demo activity. The risk of misclicking on a "demo" filter and showing a prospect a real client's diagnostic is a credibility-killer.
2. Self-serve sandbox is a stronger sales asset than a screenshare. Prospect lands on the link, clicks around, sees the workflow.

### Architecture

Single deployment, no second instance. Add a public guest route plus a scheduled reseed:

- **Route:** `GET /demo` on the frontend. Renders a one-click "Try as a merchant" button (and optionally a "Try as an operator" button for Dean's outbound).
- **Auto-login:** clicking either button calls a backend `POST /auth/demo-token` that returns a short-lived JWT scoped to a frozen demo org with `read_only=true` enforced server-side.
- **Permissions:** `demo_viewer` and `demo_operator` roles, both read-only. They can navigate, read every page, but every write endpoint returns 403.
- **Reseed:** a `POST /admin/seed-demo-sandbox` endpoint, called from a Render cron job nightly at 02:00 UTC. Wipes the sandbox org and reseeds it with fresh demo data. Keeps it clean between prospects.
- **Visual identity:** the sandbox org is named "Try Revelio (sandbox)" and shows a persistent banner: `Sandbox mode, read-only. Real platform at revelio.io.`

### Tasks (do later)

1. Add `read_only` and `is_sandbox` flags to `Organisation` and `User`.
2. Backend middleware that 403s any write request from a `read_only` user.
3. `POST /auth/demo-token` minting short-lived (15 min) JWTs for `demo_viewer` / `demo_operator`.
4. Frontend `/demo` route with the two CTAs and the persistent sandbox banner once logged in.
5. Render cron job that hits the reseed endpoint nightly.
6. Decision: bind the sandbox to `revelio.io/demo` once domain lands, or keep on `revelio-frontend-38kb.onrender.com/demo`.

### Effort

3-4 hours of focused work. Add the brief to that session, do not bundle with Phase 1.

### Acceptance for Phase 2

- Anonymous prospect hits `/demo`, clicks "Try as a merchant", lands inside the platform as `demo_viewer` against the sandbox org.
- They can read every page; any write attempt 403s.
- Banner persistently visible.
- Token expires in 15 min, frontend redirects them back to `/demo` with a friendly message.
- Cron reseed runs at 02:00 UTC, sandbox is fresh again the next morning.
- Sandbox is fully isolated from the real client orgs created since Phase 1 shipped.

---

## What this brief explicitly does NOT cover

- Phase 1 does not touch the AI pipeline. Seeded diagnostics carry hand-crafted output; there is no Anthropic call during seeding.
- Phase 2 does not introduce a second Render deployment, a second database, or schema drift. Single deployment, single DB, sandbox is just a flagged org.
- Neither phase introduces real billing or payments. Both are demo-state plumbing.
- Neither phase changes the existing super_admin login or the live ROI calculator behaviour for real released diagnostics. The ROI calculator already correctly hydrates from any released diagnostic; seeded data flows through the same path.

## Pre-flight checks before starting Phase 1

Confirm with Dean if any of these have changed since 2026-05-09:

1. Anthropic API key still active and budget cap set sensibly.
2. Render free tier still acceptable (hibernation 502s during demos still tolerable for now).
3. No real client orgs to protect yet (i.e. seeding can land safely).
4. Working tree on `main` is clean before starting (`git status` should be empty modulo `TEST_MODE_BRIEF.md` and the existing untracked `ROI_IMPROVEMENTS_LOG.md`).
