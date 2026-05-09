# Revelio — Demo Script
## Payments Revenue Leakage Diagnostic Platform

**Duration:** 15–20 minutes  
**Audience:** Head of Payments, CFO, Founder, or payments operator  
**Goal:** Show the platform is real, working, and commercially sharp

---

## Before you start

1. Run `./demo/start.sh` — wait until terminal shows "Revelio is running"
2. Open `http://localhost:3000` in a clean browser window
3. Have a second tab ready with `http://localhost:3000` for the admin view
4. Keep this script open on a second screen

---

## Opening (60 seconds)

**Say:**  
> "Most businesses have no idea how much revenue they're losing inside their payment stack. Not from fraud, not from pricing — from the infrastructure itself. Auth rates, retry logic, routing, FX spread, chargeback handling. The average e-commerce business loses 2–6% of revenue here, silently.  
> Revelio is a diagnostic engine that surfaces exactly that — with financial estimates, prioritised fixes, and a report you can put in front of a CFO."

---

## ACT 1 — Client experience (5 minutes)

**Login as the client:**  
Email: `james@acmeretail.com` / Password: `Demo1234!`

### 1.1 — Dashboard overview

Point out:
- **£2.14M annual leakage estimate** — mid estimate, immediately visible
- The four KPI cards — auth rate vs benchmark, chargeback rate
- The leakage driver breakdown — ranked and quantified
- The executive summary — AI-generated, commercially written, operator-reviewed

**Say:**  
> "This is what a client sees when they log in. Not a chatbot. Not a prompt box. A structured diagnostic output with financial estimates and a clear priority order."

### 1.2 — Show the results detail page

Click "My results" → click "View →" on RVL-2025-0018

Point out:
- Low/mid/high estimate range
- Category-level financial breakdown with confidence indicators
- Immediate vs medium-term vs structural fix priorities with estimated recovery per action
- The "Assumptions used" section at the bottom

**Say:**  
> "Every number is traceable. The client can see what was observed from their data, what was inferred from benchmarks, and what confidence level each finding has. Nothing is a black box."

### 1.3 — Show the upload flow

Click "Upload & analyse" in the sidebar

**Say:**  
> "For a new client, the flow is this: upload their PSP statement, Excel export, or PDF. We extract the fields automatically."

Click the drop zone — show it accepts CSV, XLSX, PDF

> "Or they can enter it manually if they don't have files. Either way, it goes into the analysis engine."

---

## ACT 2 — The submission and AI analysis (2 minutes)

**Say:**  
> "When data is submitted, it goes into a background pipeline. File parsing, data normalisation, confidence classification, then Claude runs the analysis. The output comes back as structured JSON — financial estimates, driver breakdown, priorities, assumption log.  
> Critically — nothing reaches the client until I've reviewed and approved it."

---

## ACT 3 — Operator control layer (8 minutes)

**Switch to Admin mode** — click "Admin" in the mode toggle in the sidebar

OR open a new tab and log in as: `admin@revelio.io` / `Demo1234!`

### 3.1 — Command centre

Point out the four KPIs:
- 47 active clients
- 3 pending approval
- £84.2M total leakage identified
- 2 low confidence flags

The pipeline status — four diagnostics at different stages  
The top leakage opportunities table — Kestrel at £12.4M, GreenMile at £8.7M

**Say:**  
> "This is my operator view. I can see every client, every diagnostic, every leakage estimate across the whole portfolio. The top opportunities table tells me where to focus."

### 3.2 — Approval queue

Click "Approval queue" in the sidebar

Show the Volta Subscriptions card:
- AI confidence: High
- Low/mid/high estimate
- AI executive summary — read a line or two
- The assumption log — point out observed vs inferred

**Say:**  
> "Before anything reaches a client, it sits here. I can read the AI output, check the assumption log, see exactly what was observed from their data vs what was inferred from benchmarks."

Scroll down to show the override controls:

> "If I disagree with any values — or want to adjust for context I know that the AI doesn't — I can override. Every override is logged with a reason. Full audit trail."

Show the operator notes field:

> "And I can add private notes. These are stored in the client intelligence layer and are never shown to the client."

**Click "Approve & release"** on Volta — watch it disappear from the queue.

> "One click. Report is now visible to the client. They get an in-app notification."

### 3.3 — Client intelligence

Click "Client intelligence"

Point to Kestrel Marketplace:
- Score: 74
- Stage: diagnostic_in_progress
- Tags: cfp-engaged, board-presentation-apr25, contract-renewal-jul25
- Intel note about CFO engagement and Adyen contract renewal

**Say:**  
> "This is the intelligence layer. Every commercial insight I gather about a client — contacts, contract dates, upsell signals, relationship context — stored here. Permanently. Private. Never shown to the client.  
> Kestrel's Adyen contract renews in July. That's a live commercial lever. The platform flags it."

Click Acme Retail intel:

> "For Acme — I can see the Stripe contract expires December 2025, James is technically engaged and implementing the retry fix himself, and I have a follow-up call booked for April 15th. This is a CRM built specifically for this product."

### 3.4 — Benchmarks

Click "Benchmarks"

**Say:**  
> "Every assumption the AI uses is operator-editable. Auth rate benchmarks by vertical, FX leakage assumptions, retry uplift, chargeback cost ratios.  
> These are injected live into the Claude prompt at the time of analysis. If I change the retail auth rate benchmark from 90% to 91%, every future retail diagnostic uses the updated number. No code changes, no redeployment."

Point to a value and change it:

> "And these feed directly into the financial model — if I adjust the cross-border penalty from 3.2% to 4%, every pending diagnostic recalculates automatically."

### 3.5 — Show GreenMile low confidence

Click "Approval queue" → scroll to GreenMile

**Say:**  
> "This is the gatekeeping in action. GreenMile submitted with minimal data — just volume and PSP. The AI ran but confidence is Low, and I've flagged it for more data rather than releasing a weak report.  
> The client gets a 'data requested' notification. The report stays internal until I'm satisfied with the precision."

---

## ACT 4 — Closing (2 minutes)

**Say:**  
> "Three things to summarise.  
>   
> One — this is a real product running real AI analysis. Not a mockup, not a demo environment with fake outputs. Claude is doing the analysis, the numbers are calculated from the inputs, the PDF is generated server-side.  
>   
> Two — the operator layer gives me complete control. Nothing reaches a client without my review. I can edit, override, annotate, and approve. The client only ever sees what I've signed off.  
>   
> Three — the intelligence layer compounds over time. Every client interaction, every contract date, every insight stored and searchable. It becomes a commercial operating system for the diagnostics business."

---

## Common questions

**"How accurate are the estimates?"**  
> "High confidence diagnostics use observed data wherever possible — the AI separates observed from inferred in the assumption log. Low confidence outputs are flagged and not released to clients. The benchmark thresholds are operator-editable, so we can calibrate them as we gather more data."

**"What does the client actually receive?"**  
> "A downloadable PDF report — board-ready, executive-grade. Plus a CSV financial breakdown. The PDF includes the executive summary, leakage estimates, category breakdown, and fix priority list. Nothing from the operator layer is included."

**"Can clients submit their own data?"**  
> "Yes — they can upload CSVs, Excel files, or PDFs from their PSP, and we extract the fields automatically. Or they use the manual entry form. Either way the data goes into the same analysis pipeline."

**"What happens if the AI gets something wrong?"**  
> "That's exactly why the operator approval layer exists. Everything sits in the review queue before release. I can override any value, edit the narrative, adjust confidence levels, and add context the AI doesn't have. The AI does the heavy lifting — I stay in control of what the client sees."

---

## After the demo

1. Show them the PDF export if they want to see the report format
2. Offer to run a real diagnostic on their own payment data
3. Point them to the tier comparison — Lite is free/low cost entry, Core is the main product, Enterprise for larger merchants

---

*Revelio — Payments Revenue Leakage Diagnostic Platform*
