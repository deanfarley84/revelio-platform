#!/usr/bin/env python3
"""
Vyre Demo Seed Script
Creates realistic demo data for a live demo or client presentation.

Accounts created:
  ADMIN:   admin@vyre.io        / Demo1234!  (Super Admin)
  CLIENT1: james@acmeretail.com    / Demo1234!  (Core · Released report)
  CLIENT2: sarah@voltaapp.com      / Demo1234!  (Core · Pending approval)
  CLIENT3: tom@kestrelmarket.io    / Demo1234!  (Enterprise · Processing)
  CLIENT4: anna@greenmile.co       / Demo1234!  (Enterprise · Low confidence)
"""

import os, sys, uuid, json
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from passlib.context import CryptContext

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vyre:vyre_demo@localhost:5432/vyre")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
PW_HASH = pwd.hash("Demo1234!")


def conn():
    for attempt in range(10):
        try:
            return psycopg2.connect(DATABASE_URL)
        except Exception as e:
            if attempt == 9:
                raise
            import time; time.sleep(2)


def now():
    return datetime.now(timezone.utc)


def days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


ACME_AI_OUTPUT = {
    "executive_summary": "Acme Retail Ltd is experiencing material payment leakage driven primarily by an authorisation rate 3.8 percentage points below the retail benchmark. Single-PSP dependency on Stripe creates structural exposure in cross-border markets, particularly Germany and France, where local issuer preferences reduce approval probability. The absence of configured retry logic leaves an estimated 60–70% of soft declines unrecovered. Combined, these three vectors represent £1.4M–£3.3M of annual preventable revenue loss.",
    "confidence_level": "high",
    "confidence_explanation": "Auth rate, volume, decline rate, cross-border %, PSP, and retry status all directly observed. Chargeback rate provided. Only FX spread and scheme fees are inferred from benchmarks.",
    "annual_leakage_estimate": {"low": 1420000, "mid": 2140000, "high": 3280000, "currency": "GBP"},
    "revenue_impact_pct": {"low": 2.5, "mid": 3.8, "high": 5.8},
    "primary_drivers": [
        {"rank": 1, "driver": "Authorisation loss", "estimated_impact_low": 890000, "estimated_impact_mid": 1050000, "estimated_impact_high": 1200000, "confidence": "high", "basis": "observed", "calculation_basis": "(90% benchmark - 86.2% actual) × £56.4M annual volume", "explanation": "Auth rate 3.8pp below retail benchmark. Primary cause likely issuer friction on UK Stripe routing for European cards."},
        {"rank": 2, "driver": "Cross-border performance drag", "estimated_impact_low": 380000, "estimated_impact_mid": 500000, "estimated_impact_high": 620000, "confidence": "medium", "basis": "inferred", "calculation_basis": "34% cross-border × £56.4M × 3.2% cross-border penalty (benchmark)", "explanation": "34% of volume is cross-border through a single UK acquirer. EU issuers prefer local acquirers, causing avoidable decline uplift."},
        {"rank": 3, "driver": "Retry logic weakness", "estimated_impact_low": 280000, "estimated_impact_mid": 385000, "estimated_impact_high": 490000, "confidence": "high", "basis": "observed", "calculation_basis": "13.8% decline rate × estimated 65% soft × 2.1% retry recovery (benchmark) × £56.4M", "explanation": "No retry logic configured. Industry data suggests 40–65% of soft declines are recoverable with a properly configured retry sequence."},
        {"rank": 4, "driver": "Payment method gaps", "estimated_impact_low": 110000, "estimated_impact_mid": 190000, "estimated_impact_high": 280000, "confidence": "medium", "basis": "inferred", "calculation_basis": "EU volume × estimated conversion uplift from iDEAL/SEPA", "explanation": "No iDEAL or SEPA Direct Debit available for NL and DE markets. These are the dominant payment methods in those regions."},
        {"rank": 5, "driver": "Chargeback admin cost", "estimated_impact_low": 85000, "estimated_impact_mid": 115000, "estimated_impact_high": 160000, "confidence": "high", "basis": "observed", "calculation_basis": "0.82% CB rate × £56.4M × £2.20 admin cost ratio", "explanation": "Chargeback rate above 0.6% threshold. Admin cost estimate based on industry standard handling costs plus revenue impact."},
    ],
    "financial_breakdown": [
        {"category": "Authorisation loss", "estimated_loss_low": 890000, "estimated_loss_mid": 1050000, "estimated_loss_high": 1200000, "confidence": "high", "basis": "observed"},
        {"category": "Cross-border drag", "estimated_loss_low": 380000, "estimated_loss_mid": 500000, "estimated_loss_high": 620000, "confidence": "medium", "basis": "inferred"},
        {"category": "Retry logic", "estimated_loss_low": 280000, "estimated_loss_mid": 385000, "estimated_loss_high": 490000, "confidence": "high", "basis": "observed"},
        {"category": "Payment method gaps", "estimated_loss_low": 110000, "estimated_loss_mid": 190000, "estimated_loss_high": 280000, "confidence": "medium", "basis": "inferred"},
        {"category": "Chargeback admin", "estimated_loss_low": 85000, "estimated_loss_mid": 115000, "estimated_loss_high": 160000, "confidence": "high", "basis": "observed"},
    ],
    "recommended_fix_priorities": {
        "immediate": [
            {"action": "Configure cascade retry with 12–24hr delay on soft declines", "rationale": "Highest ROI fix. No infrastructure change required. Estimated recovery: £280K–£490K annually.", "estimated_recovery": "£280K–£490K"},
            {"action": "Request top-5 decline code breakdown from Stripe and investigate Do Not Honour pattern", "rationale": "Likely reveals fixable issuer friction. Free to investigate.", "estimated_recovery": "Diagnostic — informs next steps"},
        ],
        "mid_term": [
            {"action": "Evaluate EU acquiring relationship (Adyen or Worldpay) for cross-border routing", "rationale": "Local EU acquiring typically reduces cross-border decline rate by 2–4pp.", "estimated_recovery": "£380K–£620K"},
            {"action": "Enable iDEAL and SEPA Direct Debit for NL and DE checkout", "rationale": "iDEAL is used in 60%+ of NL online transactions. Not offering it loses conversions.", "estimated_recovery": "£110K–£280K"},
        ],
        "structural": [
            {"action": "Commission full payment architecture review including routing strategy and acquiring contract renegotiation", "rationale": "Stripe blended rate may be 20–30bps above market for this volume. Renegotiation or competition likely yields savings.", "estimated_recovery": "£200K–£500K (estimated)"},
        ],
    },
    "data_gaps": [
        "FX spread not provided — FX leakage category excluded from this analysis",
        "Soft vs hard decline split not provided — inferred from retail sector norms (65/35)",
        "Acquirer contract terms not available — MDR comparison not modelled",
        "Scheme fee breakdown not provided — routing cost model uses benchmark approximation",
    ],
    "assumptions_used": [
        "Retail benchmark auth rate: 90% (operator-configured)",
        "Cross-border approval penalty: 3.2% (operator-configured benchmark)",
        "Retry uplift opportunity: 2.1% of volume (operator-configured benchmark)",
        "Chargeback admin cost: £2.20 per £1 of chargebacks (operator-configured benchmark)",
        "Soft decline proportion: 65% of total declines (inferred from retail sector norms)",
        "Annual volume: £56.4M (derived from £4.7M monthly × 12)",
    ],
    "_meta": {"model": "claude-sonnet-4-20250514", "prompt_version": "v1.0", "input_tokens": 2847, "output_tokens": 1203},
}

VOLTA_AI_OUTPUT = {
    "executive_summary": "Volta Subscriptions has above-benchmark authorisation performance (91.3%) with a clean chargeback record. The primary leakage opportunity is the complete absence of retry logic, which in a subscription context — where recurring billing declines are common — represents a significant recoverable revenue gap. The stated FX spread of 2.4% on 28% cross-border volume is materially above the 1.8% benchmark, creating a compounding drag. Combined, the estimated annual leakage is £1.9M–£4.6M.",
    "confidence_level": "high",
    "confidence_explanation": "Auth rate, volume, FX spread, retry status, and chargeback rate all directly observed or stated. Cross-border volume inferred from stated 28% ratio.",
    "annual_leakage_estimate": {"low": 1900000, "mid": 3100000, "high": 4600000, "currency": "GBP"},
    "revenue_impact_pct": {"low": 3.1, "mid": 5.0, "high": 7.4},
    "primary_drivers": [
        {"rank": 1, "driver": "Retry logic weakness", "estimated_impact_low": 800000, "estimated_impact_mid": 1100000, "estimated_impact_high": 1400000, "confidence": "high", "basis": "observed", "calculation_basis": "SaaS recurring billing decline rate × retry recovery opportunity", "explanation": "No retry configured on subscription billing. In SaaS, passive churn from failed payments is typically 20–30% of total churn. Retry sequences recover 40–70% of initial declines."},
        {"rank": 2, "driver": "FX leakage (spread)", "estimated_impact_low": 700000, "estimated_impact_mid": 1050000, "estimated_impact_high": 1400000, "confidence": "high", "basis": "observed", "calculation_basis": "£25.2M annual volume × 28% cross-border × 2.4% stated spread vs 1.8% benchmark", "explanation": "FX spread of 2.4% is 60bps above benchmark. On £7.1M annual cross-border volume, this represents approximately £85K in excess FX cost annually — scaling to £1M+ in revenue equivalent when factored into pricing impact."},
        {"rank": 3, "driver": "Cross-border performance drag", "estimated_impact_low": 280000, "estimated_impact_mid": 420000, "estimated_impact_high": 580000, "confidence": "medium", "basis": "inferred", "calculation_basis": "28% cross-border × £25.2M annual × 3.2% cross-border penalty", "explanation": "28% cross-border through single PSP setup. European SaaS customers will face issuer friction on UK-routed payments."},
    ],
    "financial_breakdown": [
        {"category": "Retry logic weakness", "estimated_loss_low": 800000, "estimated_loss_mid": 1100000, "estimated_loss_high": 1400000, "confidence": "high", "basis": "observed"},
        {"category": "FX leakage", "estimated_loss_low": 700000, "estimated_loss_mid": 1050000, "estimated_loss_high": 1400000, "confidence": "high", "basis": "observed"},
        {"category": "Cross-border drag", "estimated_loss_low": 280000, "estimated_loss_mid": 420000, "estimated_loss_high": 580000, "confidence": "medium", "basis": "inferred"},
        {"category": "Authorisation marginal gap", "estimated_loss_low": 120000, "estimated_loss_mid": 200000, "estimated_loss_high": 280000, "confidence": "medium", "basis": "inferred"},
    ],
    "recommended_fix_priorities": {
        "immediate": [
            {"action": "Implement subscription retry logic with network tokenisation and smart scheduling", "rationale": "Single highest-ROI action available. Tools: Stripe Smart Retries, Recurly, or custom logic.", "estimated_recovery": "£800K–£1.4M"},
            {"action": "Renegotiate FX spread with current payment provider or benchmark against alternatives", "rationale": "2.4% spread is significantly above market. Stripe Adaptive Pricing or Adyen FX may offer 50–100bps reduction.", "estimated_recovery": "£350K–£700K"},
        ],
        "mid_term": [
            {"action": "Implement dunning management workflow for failed subscription payments", "rationale": "Reduces involuntary churn. Email sequence plus payment update flows typically recover 15–25% of at-risk MRR.", "estimated_recovery": "£200K–£400K"},
        ],
        "structural": [
            {"action": "Upgrade to Enterprise diagnostic for full FX and routing architecture analysis", "rationale": "With £3.1M estimated leakage, Enterprise tier ROI is compelling. Full MDR, scheme fee, and contract review available.", "estimated_recovery": "Additional precision — not modelled at Core tier"},
        ],
    },
    "data_gaps": [
        "MDR not provided — merchant discount rate comparison not available",
        "Scheme fee visibility: none — routing cost model approximated",
        "Pricing model not specified — IC++ vs blended comparison not available",
    ],
    "assumptions_used": [
        "SaaS auth rate benchmark: 92% (operator-configured)",
        "Cross-border penalty: 3.2% (operator-configured benchmark)",
        "FX benchmark spread: 1.8% (operator-configured benchmark)",
        "Annual volume: £25.2M (£2.1M monthly × 12)",
        "SaaS soft decline proportion: 75% of declines (sector norm)",
    ],
    "_meta": {"model": "claude-sonnet-4-20250514", "prompt_version": "v1.0", "input_tokens": 2654, "output_tokens": 1087},
}

KESTREL_AI_OUTPUT = {
    "executive_summary": "Kestrel Marketplace operates at scale with material exposure across multiple leakage categories. The authorisation rate of 84.1% is 4–5pp below marketplace benchmark, with the high cross-border volume (52%) amplifying this impact significantly. Chargeback rate of 1.12% is nearly double the acceptable threshold, generating both direct revenue loss and operational cost drag. Single-PSP dependency on Adyen — while better than most single-PSP setups — limits routing optimisation. Estimated annual leakage: £7.8M–£15.2M.",
    "confidence_level": "medium",
    "confidence_explanation": "Auth rate and volume observed. Cross-border %, chargeback rate, and PSP confirmed. MDR, FX spread, scheme fees, and routing detail not provided — Enterprise analysis degraded.",
    "annual_leakage_estimate": {"low": 7800000, "mid": 12400000, "high": 15200000, "currency": "GBP"},
    "revenue_impact_pct": {"low": 3.1, "mid": 4.9, "high": 6.0},
    "primary_drivers": [
        {"rank": 1, "driver": "Authorisation loss", "estimated_impact_low": 3200000, "estimated_impact_mid": 4500000, "estimated_impact_high": 5800000, "confidence": "high", "basis": "observed", "calculation_basis": "(88% benchmark - 84.1% actual) × £100.8M annual volume", "explanation": "4pp below marketplace benchmark. At this volume, each percentage point of auth rate improvement is worth approximately £1M annually."},
        {"rank": 2, "driver": "Chargeback cost", "estimated_impact_low": 2100000, "estimated_impact_mid": 3200000, "estimated_impact_high": 4200000, "confidence": "high", "basis": "observed", "calculation_basis": "1.12% CB rate × £100.8M × 3.0 revenue impact ratio", "explanation": "Chargeback rate of 1.12% is 87% above the 0.6% threshold. At marketplace scale, this is a major drag. Includes admin cost, scheme penalties, and revenue loss from disputed transactions."},
        {"rank": 3, "driver": "Cross-border performance drag", "estimated_impact_low": 1800000, "estimated_impact_mid": 2800000, "estimated_impact_high": 3600000, "confidence": "medium", "basis": "inferred", "calculation_basis": "52% cross-border × £100.8M × 3.2% cross-border penalty", "explanation": "52% cross-border through a single acquirer setup is unusually high exposure. Multi-currency, multi-acquirer routing would materially improve approval rates on EU, US, and APAC transactions."},
    ],
    "financial_breakdown": [
        {"category": "Authorisation loss", "estimated_loss_low": 3200000, "estimated_loss_mid": 4500000, "estimated_loss_high": 5800000, "confidence": "high", "basis": "observed"},
        {"category": "Chargeback cost", "estimated_loss_low": 2100000, "estimated_loss_mid": 3200000, "estimated_loss_high": 4200000, "confidence": "high", "basis": "observed"},
        {"category": "Cross-border drag", "estimated_loss_low": 1800000, "estimated_loss_mid": 2800000, "estimated_loss_high": 3600000, "confidence": "medium", "basis": "inferred"},
        {"category": "Routing inefficiency", "estimated_loss_low": 700000, "estimated_loss_mid": 1900000, "estimated_loss_high": 1600000, "confidence": "low", "basis": "inferred"},
    ],
    "recommended_fix_priorities": {
        "immediate": [
            {"action": "Implement chargeback prevention tooling and dispute resolution workflow", "rationale": "1.12% rate risks Visa VAMP and Mastercard MATCH listing. Immediate remediation required.", "estimated_recovery": "£1M–£2M in avoided scheme penalties and admin cost"},
            {"action": "Activate Adyen intelligent routing with issuer-level rules", "rationale": "Adyen supports granular routing logic. Issuer-specific rules for EU and US can recover 1–2pp of auth rate.", "estimated_recovery": "£1M–£2M"},
        ],
        "mid_term": [
            {"action": "Add secondary acquirer for US and APAC routing", "rationale": "Local acquiring in target regions reduces cross-border penalties. Consider Braintree (US) or Stripe (APAC).", "estimated_recovery": "£800K–£1.8M"},
        ],
        "structural": [
            {"action": "Commission full Enterprise diagnostic with MDR, FX spread, and scheme fee analysis", "rationale": "At £100.8M volume, contract renegotiation alone could yield £500K–£1.5M in annual savings.", "estimated_recovery": "£500K–£1.5M (contract) + full model precision"},
        ],
    },
    "data_gaps": [
        "MDR not provided — merchant discount rate comparison not available at Core tier",
        "FX spread not provided — FX leakage not modelled",
        "Scheme fee breakdown absent — routing cost optimisation cannot be fully assessed",
        "Routing rules detail not provided — Adyen routing configuration unknown",
    ],
    "assumptions_used": [
        "Marketplace auth rate benchmark: 88% (operator-configured)",
        "Cross-border penalty: 3.2% (operator-configured benchmark)",
        "Chargeback revenue impact ratio: 3.0× (operator-configured benchmark)",
        "Annual volume: £100.8M (£8.4M monthly × 12)",
    ],
    "_meta": {"model": "claude-sonnet-4-20250514", "prompt_version": "v1.0", "input_tokens": 3102, "output_tokens": 1356},
}


def seed(db):
    cur = db.cursor()

    # ── Check already seeded ──────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
    if cur.fetchone()[0] > 0:
        print("  Demo data already seeded — skipping")
        cur.close()
        return

    print("  Seeding users and organisations...")

    # ── Admin user ────────────────────────────────────────────────
    admin_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO users (id, email, full_name, role, password_hash, is_active)
        VALUES (%s, 'admin@vyre.io', 'Operator Admin', 'super_admin', %s, true)
    """, (admin_id, PW_HASH))

    # ── Client 1: Acme Retail — Core, Released ────────────────────
    org1 = str(uuid.uuid4())
    user1 = str(uuid.uuid4())
    cur.execute("INSERT INTO organisations (id, name, website, vertical, tier) VALUES (%s,'Acme Retail Ltd','acmeretail.com','retail','core')", (org1,))
    cur.execute("INSERT INTO users (id, org_id, email, full_name, role, password_hash, is_active) VALUES (%s,%s,'james@acmeretail.com','James Mitchell','client_admin',%s,true)", (user1, org1, PW_HASH))

    # ── Client 2: Volta Subscriptions — Core, Pending Approval ───
    org2 = str(uuid.uuid4())
    user2 = str(uuid.uuid4())
    cur.execute("INSERT INTO organisations (id, name, website, vertical, tier) VALUES (%s,'Volta Subscriptions','voltaapp.com','saas','core')", (org2,))
    cur.execute("INSERT INTO users (id, org_id, email, full_name, role, password_hash, is_active) VALUES (%s,%s,'sarah@voltaapp.com','Sarah Chen','client_admin',%s,true)", (user2, org2, PW_HASH))

    # ── Client 3: Kestrel Marketplace — Enterprise, AI Complete ──
    org3 = str(uuid.uuid4())
    user3 = str(uuid.uuid4())
    cur.execute("INSERT INTO organisations (id, name, website, vertical, tier) VALUES (%s,'Kestrel Marketplace','kestrelmarket.io','marketplace','enterprise')", (org3,))
    cur.execute("INSERT INTO users (id, org_id, email, full_name, role, password_hash, is_active) VALUES (%s,%s,'tom@kestrelmarket.io','Tom Ashworth','client_admin',%s,true)", (user3, org3, PW_HASH))

    # ── Client 4: GreenMile Logistics — Enterprise, Low Confidence
    org4 = str(uuid.uuid4())
    user4 = str(uuid.uuid4())
    cur.execute("INSERT INTO organisations (id, name, website, vertical, tier) VALUES (%s,'GreenMile Logistics','greenmile.co','logistics','enterprise')", (org4,))
    cur.execute("INSERT INTO users (id, org_id, email, full_name, role, password_hash, is_active) VALUES (%s,%s,'anna@greenmile.co','Anna Petrov','client_admin',%s,true)", (user4, org4, PW_HASH))

    db.commit()
    print("  Users and orgs created")

    # ── Diagnostics ───────────────────────────────────────────────
    print("  Seeding diagnostics...")

    # Acme — RELEASED
    d1 = str(uuid.uuid4())
    submitted1 = days_ago(8)
    released1 = days_ago(6)
    cur.execute("""
        INSERT INTO diagnostics (
            id, reference, org_id, submitted_by, tier, status,
            company_name, website, vertical,
            monthly_volume, monthly_transactions, avg_order_value,
            cross_border_pct, psps_used, regions,
            auth_rate, decline_rate, soft_decline_pct, hard_decline_pct,
            chargeback_rate, refund_rate, payment_methods,
            retry_enabled, checkout_currencies, settlement_currencies,
            ai_output, final_output, benchmarks_snapshot,
            ai_model, ai_prompt_version, ai_tokens_used, ai_run_at,
            operator_notes, approved_by, approved_at, released_at,
            submitted_at
        ) VALUES (
            %s,'RVL-2025-0018',%s,%s,'core','released',
            'Acme Retail Ltd','acmeretail.com','retail',
            4700000,82400,57.06,
            34,ARRAY['Stripe'],
            '[{"region":"UK","pct":66},{"region":"DE","pct":18},{"region":"FR","pct":16}]',
            86.2,13.8,9.2,4.6,
            0.82,4.1,ARRAY['Visa','Mastercard','Apple Pay'],
            false,ARRAY['GBP','EUR'],ARRAY['GBP'],
            %s,%s,'{}',
            'claude-sonnet-4-20250514','v1.0',4050,%s,
            'Strong candidate for Enterprise upgrade — Stripe contract renewal in Dec 2025. James Mitchell is technically engaged and will implement retry fix himself. Follow-up booked 15 Apr.',
            %s,%s,%s,%s
        )
    """, (
        d1, org1, user1,
        json.dumps(ACME_AI_OUTPUT), json.dumps(ACME_AI_OUTPUT),
        days_ago(7), admin_id, days_ago(6), released1, submitted1
    ))

    # Volta — PENDING REVIEW
    d2 = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO diagnostics (
            id, reference, org_id, submitted_by, tier, status,
            company_name, website, vertical,
            monthly_volume, monthly_transactions, avg_order_value,
            cross_border_pct, psps_used,
            auth_rate, decline_rate, chargeback_rate, refund_rate,
            payment_methods, retry_enabled,
            checkout_currencies, settlement_currencies,
            fx_fee_spread,
            ai_output, benchmarks_snapshot,
            ai_model, ai_prompt_version, ai_tokens_used, ai_run_at,
            submitted_at
        ) VALUES (
            %s,'RVL-2025-0019',%s,%s,'core','pending_review',
            'Volta Subscriptions','voltaapp.com','saas',
            2100000,18500,113.51,
            28,ARRAY['Stripe'],
            91.3,8.7,0.41,2.8,
            ARRAY['Visa','Mastercard','Apple Pay','Google Pay'],false,
            ARRAY['GBP','EUR','USD'],ARRAY['GBP'],
            0.024,
            %s,'{}',
            'claude-sonnet-4-20250514','v1.0',3741,%s,
            %s
        )
    """, (d2, org2, user2, json.dumps(VOLTA_AI_OUTPUT), days_ago(2), days_ago(3)))

    # Kestrel — AI_COMPLETE (just finished, waiting to move to pending_review)
    d3 = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO diagnostics (
            id, reference, org_id, submitted_by, tier, status,
            company_name, website, vertical,
            monthly_volume, monthly_transactions, avg_order_value,
            cross_border_pct, psps_used,
            auth_rate, decline_rate, chargeback_rate, refund_rate,
            payment_methods, retry_enabled,
            checkout_currencies, settlement_currencies,
            ai_output, benchmarks_snapshot,
            ai_model, ai_prompt_version, ai_tokens_used, ai_run_at,
            submitted_at
        ) VALUES (
            %s,'RVL-2025-0021',%s,%s,'enterprise','pending_review',
            'Kestrel Marketplace','kestrelmarket.io','marketplace',
            8400000,145000,57.93,
            52,ARRAY['Adyen'],
            84.1,15.9,1.12,5.2,
            ARRAY['Visa','Mastercard','Amex','PayPal','Apple Pay'],true,
            ARRAY['GBP','EUR','USD','AUD'],ARRAY['GBP'],
            %s,'{}',
            'claude-sonnet-4-20250514','v1.0',4458,%s,
            %s
        )
    """, (d3, org3, user3, json.dumps(KESTREL_AI_OUTPUT), days_ago(1), days_ago(1)))

    # GreenMile — PENDING_REVIEW, low confidence
    d4 = str(uuid.uuid4())
    low_conf_output = {
        "executive_summary": "GreenMile Logistics has provided insufficient data for a high-precision Enterprise analysis. Based on available volume data, estimated annual leakage is £4.2M–£9.8M — however confidence is low due to missing auth rate, FX spread, MDR, and acquirer detail. This range is primarily benchmark-driven.",
        "confidence_level": "low",
        "confidence_explanation": "Only monthly volume and PSP provided. Auth rate, decline rate, chargeback rate, FX spread, and MDR all missing. All estimates derived from logistics sector benchmarks.",
        "annual_leakage_estimate": {"low": 4200000, "mid": 6800000, "high": 9800000, "currency": "GBP"},
        "revenue_impact_pct": {"low": 2.8, "mid": 4.5, "high": 6.5},
        "primary_drivers": [
            {"rank": 1, "driver": "Auth rate (inferred)", "estimated_impact_low": 2000000, "estimated_impact_mid": 3200000, "estimated_impact_high": 4500000, "confidence": "low", "basis": "inferred", "explanation": "Auth rate inferred from logistics sector average (84%). Actual rate not provided."},
        ],
        "financial_breakdown": [],
        "recommended_fix_priorities": {"immediate": [], "mid_term": [], "structural": [{"action": "Provide auth rate, MDR, FX spread, and chargeback data to enable full Enterprise analysis", "rationale": "Current data insufficient for actionable recommendations.", "estimated_recovery": "Analysis precision improvement"}]},
        "data_gaps": ["Auth rate not provided", "Decline rate not provided", "Chargeback rate not provided", "FX spread not provided", "MDR not provided", "Acquirer contract not provided", "Routing setup not provided"],
        "assumptions_used": ["All estimates derived from logistics sector benchmarks", "Volume: £74.4M annual"],
    }
    cur.execute("""
        INSERT INTO diagnostics (
            id, reference, org_id, submitted_by, tier, status,
            company_name, website, vertical,
            monthly_volume, psps_used,
            ai_output, benchmarks_snapshot,
            ai_model, ai_prompt_version, ai_tokens_used, ai_run_at,
            submitted_at
        ) VALUES (
            %s,'RVL-2025-0020',%s,%s,'enterprise','pending_review',
            'GreenMile Logistics','greenmile.co','logistics',
            6200000,ARRAY['Worldpay'],
            %s,'{}',
            'claude-sonnet-4-20250514','v1.0',1842,%s,
            %s
        )
    """, (d4, org4, user4, json.dumps(low_conf_output), days_ago(1), days_ago(2)))

    db.commit()
    print("  Diagnostics seeded")

    # ── Client intelligence ───────────────────────────────────────
    print("  Seeding client intelligence...")

    for org_id, data in [
        (org1, {
            "opportunity_stage": "report_delivered",
            "score": 68,
            "notes": "Head of Payments (James Mitchell) is primary contact. Technically engaged — will implement retry fix himself. Strong candidate for Enterprise upgrade once auth rate issue is addressed. Follow-up call booked 15 Apr 2025.",
            "tags": ["upsell-candidate", "stripe-contract-dec-25", "retry-fix-in-progress"],
            "key_contacts": [{"name": "James Mitchell", "title": "Head of Payments", "email": "james@acmeretail.com", "notes": "Technical, decision maker for payments stack"}],
            "contract_notes": "Currently on Stripe blended rate. Contract expires Dec 2025. Good negotiation leverage — they're processing £4.7M/mo. Could move 20–30bps.",
            "contract_renewal": "2025-12-01",
            "upsell_signals": ["Stripe contract renewal Dec 2025", "High cross-border exposure suits Enterprise", "Auth rate fix will reveal FX leakage as next priority"],
            "follow_up_date": "2025-04-15",
            "total_leakage_identified": 2140000,
            "diagnostics_count": 2,
        }),
        (org2, {
            "opportunity_stage": "diagnostic_in_progress",
            "score": 82,
            "notes": "CEO Sarah Chen is personally engaged. Wants board-ready output. FX fix alone could recover ~£400K/yr. Strong candidate for immediate upsell to Enterprise for full FX and routing analysis. Report pending approval.",
            "tags": ["ceo-engaged", "fx-exposure", "upsell-to-enterprise", "board-presentation"],
            "key_contacts": [{"name": "Sarah Chen", "title": "CEO", "email": "sarah@voltaapp.com", "notes": "Founder-led. Commercially sharp. Wants clear ROI before any action."}],
            "contract_notes": "SaaS on Stripe. No visibility on MDR breakdown. FX exposure significant — 2.4% spread is 60bps above market.",
            "upsell_signals": ["CEO engagement signals strong conversion probability", "FX exposure creates clear Enterprise diagnostic value", "Retry fix is fast win — builds trust for larger engagement"],
            "follow_up_date": "2025-04-08",
            "total_leakage_identified": 3100000,
            "diagnostics_count": 1,
        }),
        (org3, {
            "opportunity_stage": "diagnostic_in_progress",
            "score": 74,
            "notes": "CFO Tom Ashworth engaged directly. Board presentation scheduled Apr 2025. Contract renewal due Jul 2025 — critical upsell window. Auth rate dropped from 87% in Q3 to 84% in Q4, likely related to scheme rule change. High chargeback rate is a risk — could face Visa VAMP if not addressed.",
            "tags": ["cfp-engaged", "board-presentation-apr25", "contract-renewal-jul25", "chargeback-risk", "high-value"],
            "key_contacts": [{"name": "Tom Ashworth", "title": "CFO", "email": "tom@kestrelmarket.io", "notes": "Finance-led buyer. Needs clear financial model and ROI case."}],
            "contract_notes": "Adyen Enterprise contract. Renewal Jul 2025. Processing £8.4M/mo — significant negotiation leverage. Scheme fee visibility partial.",
            "contract_renewal": "2025-07-01",
            "upsell_signals": ["Adyen contract renewal July 2025", "£12.4M estimated leakage — compelling Enterprise ROI", "Chargeback rate risks scheme penalties — urgency driver"],
            "follow_up_date": "2025-04-20",
            "total_leakage_identified": 12400000,
            "diagnostics_count": 1,
        }),
        (org4, {
            "opportunity_stage": "engaged",
            "score": 42,
            "notes": "Minimal data provided. Need to re-engage and get proper inputs before Enterprise analysis is meaningful. Low confidence output — do not release without requesting auth rate, chargeback rate, and FX data first.",
            "tags": ["low-data", "re-engage-required", "do-not-release"],
            "upsell_signals": ["Large volume (£6.2M/mo) suggests significant leakage potential", "Logistics sector typically has high cross-border exposure"],
            "follow_up_date": "2025-04-05",
            "total_leakage_identified": 6800000,
            "diagnostics_count": 1,
        }),
    ]:
        intel_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO client_intel (
                id, org_id, opportunity_stage, score, notes, tags,
                key_contacts, contract_notes, contract_renewal,
                upsell_signals, follow_up_date, total_leakage_identified,
                diagnostics_count, created_by, updated_by, last_activity_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            intel_id, org_id,
            data.get("opportunity_stage"), data.get("score"),
            data.get("notes"), data.get("tags", []),
            json.dumps(data.get("key_contacts", [])),
            data.get("contract_notes"), data.get("contract_renewal"),
            data.get("upsell_signals", []), data.get("follow_up_date"),
            data.get("total_leakage_identified"), data.get("diagnostics_count", 1),
            admin_id, admin_id, now().isoformat()
        ))

    db.commit()
    print("  Client intelligence seeded")

    # ── Intel log entries ─────────────────────────────────────────
    for org_id, entries in [
        (org1, [
            ("Intro call completed — James confirmed retry logic is next priority. Will implement via Stripe in April.", "call"),
            ("Report released. James has already reviewed — positive response. Booked follow-up for 15 Apr.", "update"),
            ("Stripe contract confirmed Dec 2025 expiry. Flag for contract renegotiation conversation in Q3.", "note"),
        ]),
        (org2, [
            ("CEO Sarah Chen reached out directly after referral from Acme. High urgency on FX issue.", "call"),
            ("Diagnostic submitted. FX spread confirmed 2.4% — significant. Board presentation planned for May.", "note"),
        ]),
        (org3, [
            ("CFO Tom Ashworth engaged. Auth rate decline Q3→Q4 flagged as board-level concern.", "call"),
            ("Kestrel processing £8.4M/mo. Chargeback rate at 1.12% — escalation risk. Flagged urgency.", "note"),
            ("Enterprise diagnostic submitted. Adyen contract renewal Jul 2025 confirmed — key leverage point.", "update"),
        ]),
    ]:
        for note, note_type in entries:
            cur.execute("""
                INSERT INTO client_intel_log (id, org_id, note, note_type, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (str(uuid.uuid4()), org_id, note, note_type, admin_id))

    db.commit()
    print("  Intel log entries seeded")

    cur.close()
    print("\n  ✓ Demo data ready")
    print("  Admin:   admin@vyre.io / Demo1234!")
    print("  Client1: james@acmeretail.com / Demo1234! (Core · Released report)")
    print("  Client2: sarah@voltaapp.com / Demo1234! (Core · Pending approval)")
    print("  Client3: tom@kestrelmarket.io / Demo1234! (Enterprise · In review)")
    print("  Client4: anna@greenmile.co / Demo1234! (Enterprise · Low confidence)")


if __name__ == "__main__":
    print("\nVyre Demo Seed")
    print("=" * 40)
    try:
        db = conn()
        print("Database connected")
        seed(db)
        db.close()
    except Exception as e:
        print(f"Seed failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
