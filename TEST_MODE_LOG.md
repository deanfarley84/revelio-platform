# Test mode rollout log

**Date:** 2026-05-10
**Branch / scope:** `main`, commits `25ac364..251a798` (13 commits across the day)

## Tasks shipped

- [x] Task 1, schema with `is_demo` flag, `25ac364`
- [x] Task 2, `POST /admin/seed-test-data` endpoint, `3de658a`
- [x] Task 3, `DELETE /admin/seed-test-data` endpoint, `3de658a`
- [x] Task 4, amber DEMO tag in admin views, `4e7981e`
- [x] Demo AI fixtures aligned with PDF template schema, `67dacdf`
- [x] ROI page auto-selects the most recent released diagnostic on load, `f9a1484`
- [x] Cost-of-inaction banner: tiered orchestration helper added then call-site dropped per Dean's request, `417913e..f542a86`
- [x] Banner copy reworked to a payment-strategy framing plus a provider-agnostic Strategic AE pitch, `f542a86`
- [x] Task 5, live Anthropic submission against `Live Test (Dean)` org. Diagnostic processed end to end, RVL-2026-0004 released, ROI page populated. Anthropic spend confirmed in console.
- [x] ROI hydration fix: read `estimated_loss_mid` when the singular `estimated_loss` field is absent (production AI output uses the banded fields), `b13bf97`
- [x] WeasyPrint PDF generation fix: pinned `pydyf==0.10.0` to resolve the `'super' object has no attribute 'transform'` AttributeError that was 500-ing every download, `33889b4`
- [x] Diagnostic report PDF: path-forward / pain-bullets / outcomes / contact CTA section appended (hidden on internal-only operator copies), `9d397c2`
- [x] Diagnostic report PDF: zero-cost frame as the lead outcome card, optional add-on services (pricing drift / contract compliance / provider review and negotiation), `page-break-inside: avoid` on every block so the dark contact CTA never splits, `987de65`
- [x] Diagnostic report PDF: lead card reframed to "No fee for diagnosis or visibility" with the small-percent recovery-fee mechanic; "Immediate impact, no integration burden" body now spells out the no-code, hundreds-of-acquirers angle; new italicised positioning line above the dark CTA, `8af29c0`
- [x] ROI summary PDF: same path-forward CTA mirrored across (slightly tighter sizing for A4 fit). Inaction-block pure-recovery copy aligned to the live ROI page, `251a798`
- [x] Task 6, this log

## How to log in

All demo accounts share the same password: `Demo1234!`

| Email | Role | Org | Tier | Diagnostic state | What you can verify |
|---|---|---|---|---|---|
| deanfarley84@gmail.com | super_admin | Vyre Operator | enterprise | n/a | Operator view: every org, every diagnostic, the queue, the ROI page with Acme released as a real selectable option. |
| admin@acme-retail.demo | client_admin | Acme Retail (demo) | core | RVL-DEMO-001 released | Customer view, can see and download their released diagnostic only. |
| viewer@acme-retail.demo | client_viewer | Acme Retail (demo) | core | as above | Read-only customer view. |
| admin@globex-travel.demo | client_admin | Globex Travel (demo) | enterprise | RVL-DEMO-002 pending_review | Customer view. The diagnostic is still in operator review so it should not be visible to the client side until you approve it. |
| viewer@globex-travel.demo | client_viewer | Globex Travel (demo) | enterprise | as above | Read-only. |
| admin@tinker-goods.demo | client_admin | Tinker Goods (demo) | lite | RVL-DEMO-003 draft | Customer view: a half-completed submission flow. |
| viewer@tinker-goods.demo | client_viewer | Tinker Goods (demo) | lite | as above | Read-only. |
| livetest@vyre.io | client_admin | Live Test (Dean) | core | RVL-2026-0004 released | Real Anthropic-processed diagnostic from Task 5. Use to demo the customer download flow against a non-seeded org. Password `Live1234!`. |

Login URL: https://vyre-frontend-38kb.onrender.com/auth/login

**Tip:** the login endpoint is case-sensitive on email today. Lowercase the email when typing or browser-autofill puts a capital first letter and you get `Invalid email or password`.

## What to click through

**Operator view (your existing super_admin login):**
- `/dashboard` and `/results` — Acme RVL-DEMO-001 with the amber DEMO tag.
- `/admin` (overview) — top leakage table shows all three demo orgs and the Live Test diagnostic, pipeline list shows their statuses.
- `/admin/queue` — Globex RVL-DEMO-002 sitting in review, ready for the operator approve/reject flow.
- `/admin/clients` — five orgs listed (three demo + Live Test + Vyre Operator). Demo rows tagged.
- `/roi` — auto-selects RVL-2026-0004 (Live Test) as the most recent released diagnostic; flip the dropdown to RVL-DEMO-001 to see the seeded Acme data instead. Real driver values populate either way.

**Customer view (log out, log in as e.g. `admin@acme-retail.demo` or `livetest@vyre.io`):**
- The admin nav (Queue, Clients, Pipeline, etc.) is hidden.
- `/dashboard` shows only that org's released diagnostic.
- `/results/{id}` shows the merchant-side report.
- `Download PDF` works end to end now (pydyf pin) and the rendered PDF closes with the new path-forward CTA.

## Customer-facing PDFs all carry the CTA

Two code paths produce PDFs that go to a customer; both close with the same path-forward / contact CTA:

| Endpoint | Generator | CTA included |
|---|---|---|
| `POST /reports/{diag}/generate` (download from `/reports`) | `report_generator.py` `generate_pdf` | Yes; hidden only when `is_internal=True`, used for operator-internal copies |
| `POST /reports/roi/pdf` (download from `/roi`) | inline render in `reports.py` | Yes; ROI exports are always client-facing so no internal carve-out |

CSV exports do not carry the CTA; raw data only. No email/attachment path exists in the codebase today.

## Deviations from the brief

- **Schema migration.** Brief said `Base.metadata.create_all` covers it. In practice that only creates missing tables, it does not add columns to existing ones, so an idempotent `ALTER TABLE ADD COLUMN IF NOT EXISTS` step runs alongside it in the lifespan. Pragmatic stand-in until Alembic is wired.
- **Fixture shape.** Brief told me the AI output JSON should match production schema. Did so, but on the first seed run the report-template render threw on string vs dict mismatches in `primary_drivers` and an unexpected `mid` key in `recommended_fix_priorities` (production uses `mid_term`). Fixed in commit `67dacdf` by reshaping primary_drivers to dicts and using `immediate / mid_term / structural` keys with action + estimated_recovery dicts.
- **PDF generation: fixed.** Initial seed runs threw `'super' object has no attribute 'transform'` from `weasyprint/pdf/stream.py`. Confirmed root cause was a pydyf 0.11+ resolution: WeasyPrint 62.3's Stream subclass calls `super().transform()` against pydyf's parent class, which removed the method in 0.11. Pinned `pydyf==0.10.0` in `33889b4`. Already-seeded demo orgs may have `report_exports: 0` because they were seeded before the fix; re-running `DELETE /admin/seed-test-data` then `POST /admin/seed-test-data` regenerates them with PDFs included.
- **ROI hydration field name.** ROI page only read `estimated_loss` per driver; production AI output writes `estimated_loss_low / mid / high`. So the live test diagnostic showed £0 across every driver until `b13bf97` taught the page to fall back to `estimated_loss_mid`.
- **Strategic AE pitch wording.** Cost tier estimate was added then removed at Dean's request: he wanted the conversation kept warmer rather than quoting numbers up front. Helper function stays in the code for later use.

## Useful commands while testing

```bash
# Seed (idempotent, will wipe-and-replay if demo orgs already exist)
TOKEN=$(curl -sS -X POST https://vyre-backend-r8u3.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  --data-raw '{"email":"deanfarley84@gmail.com","password":"?Vyreadmin84"}' | jq -r '.access_token')
curl -sS -X POST https://vyre-backend-r8u3.onrender.com/api/v1/admin/seed-test-data \
  -H "Authorization: Bearer $TOKEN"

# Wipe everything is_demo=true
curl -sS -X DELETE https://vyre-backend-r8u3.onrender.com/api/v1/admin/seed-test-data \
  -H "Authorization: Bearer $TOKEN"
```

## Suggested next round

1. **Login email lowercase fix.** Cheapest sales-credibility win. `auth.py` `login` does an exact-match query while `bootstrap` lowercases. Browser autofill puts a capital first letter and the user gets `Invalid email or password`. One-line fix.
2. **Demo PDF pre-fetch in the UI.** When a customer clicks `/results/RVL-DEMO-001`, the page should call `POST /reports/{id}/generate` if no export exists, then download. Removes the seed-time pre-gen requirement entirely. Probably 30 minutes of frontend work.
3. **Operator-mintable client orgs.** Live Test creation went through the unauthenticated `register-org` endpoint; not ideal long term. Add a super_admin endpoint that creates an org and seed user without leaking the public registration path.
4. **Brand-level contact routing.** CTA contact card is hardcoded to Dean's personal email, phones and LinkedIn. Move to a brand-level inbox and number once `vyre.io` and shared comms are stood up.
5. **Phase 2 sandbox sketch.** When client #1 signs, the brief in `TEST_MODE_BRIEF.md` covers the public sandbox. Worth re-reading and refining before that day.
