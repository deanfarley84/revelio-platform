"""
Report Generator Service
Generates PDF (via WeasyPrint + Jinja2) and CSV exports.
"""
import csv
import io
from datetime import datetime
from jinja2 import Environment, BaseLoader
from weasyprint import HTML

PDF_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #0D0C0A; font-size: 12px; line-height: 1.6; }
  .page { padding: 48px 52px; max-width: 800px; margin: 0 auto; }
  .header { border-bottom: 2px solid #1A1830; padding-bottom: 20px; margin-bottom: 28px; display: flex; justify-content: space-between; align-items: flex-end; }
  .brand { font-size: 18px; font-weight: 700; color: #1A1830; letter-spacing: -0.02em; }
  .brand-sub { font-size: 10px; color: #95928A; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }
  .ref { font-size: 11px; color: #95928A; text-align: right; }
  .ref strong { color: #0D0C0A; display: block; font-size: 12px; }
  h1 { font-size: 22px; font-weight: 700; color: #1A1830; margin-bottom: 4px; }
  h2 { font-size: 14px; font-weight: 600; color: #1A1830; margin: 24px 0 10px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #E8E6E0; padding-bottom: 5px; }
  .meta { font-size: 11px; color: #95928A; margin-bottom: 24px; }
  .leakage-block { background: #1A1830; color: white; border-radius: 10px; padding: 24px 28px; margin: 20px 0; }
  .leakage-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
  .leakage-value { font-size: 36px; font-weight: 300; color: rgba(255,255,255,0.95); line-height: 1; }
  .leakage-sub { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 4px; }
  .range-row { display: flex; gap: 24px; margin-top: 14px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.1); }
  .range-item .rl { font-size: 9px; color: rgba(255,255,255,0.35); margin-bottom: 2px; }
  .range-item .rv { font-size: 15px; font-weight: 600; color: rgba(255,255,255,0.85); font-family: monospace; }
  .narrative { background: #F5F4F1; border-left: 3px solid #1A1830; border-radius: 0 6px 6px 0; padding: 14px 16px; font-size: 12px; color: #524F48; line-height: 1.7; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  th { font-size: 10px; font-weight: 600; color: #95928A; text-transform: uppercase; letter-spacing: 0.05em; padding: 8px 10px; text-align: left; border-bottom: 1px solid #E8E6E0; }
  td { padding: 9px 10px; font-size: 12px; border-bottom: 1px solid #F0EEE9; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  .mono { font-family: monospace; }
  .conf-high { color: #1A6B3C; font-weight: 600; }
  .conf-med { color: #7A4C08; font-weight: 600; }
  .conf-low { color: #8C2020; font-weight: 600; }
  .priority-section { margin-bottom: 14px; }
  .priority-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px; }
  .priority-label.immediate { color: #8C2020; }
  .priority-label.mid { color: #7A4C08; }
  .priority-label.structural { color: #1B5DB5; }
  .priority-item { display: flex; gap: 8px; padding: 5px 0; font-size: 12px; }
  .priority-num { width: 18px; height: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 700; flex-shrink: 0; background: #F0EEE9; color: #524F48; }
  .gap-item { padding: 4px 0; font-size: 11.5px; color: #524F48; }
  .gap-item::before { content: "○ "; color: #95928A; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #E8E6E0; font-size: 10px; color: #95928A; display: flex; justify-content: space-between; }
  .internal-banner { background: #FDF2DC; border: 1px solid rgba(122,76,8,0.25); border-radius: 6px; padding: 10px 14px; font-size: 11px; color: #7A4C08; margin-bottom: 20px; font-weight: 600; }
  .internal-notes { background: #FDF2DC; border-left: 3px solid #7A4C08; border-radius: 0 6px 6px 0; padding: 12px 14px; font-size: 11.5px; color: #524F48; margin-top: 8px; }
  .cta-section { margin-top: 28px; padding-top: 22px; border-top: 1px solid #E8E6E0; }
  .cta-pain-narrative { background: #F5F4F1; border-left: 3px solid #1A1830; border-radius: 0 6px 6px 0; padding: 14px 16px; font-size: 12px; color: #524F48; line-height: 1.65; margin-bottom: 14px; }
  .cta-subheader { font-size: 11.5px; color: #524F48; margin-bottom: 6px; }
  .cta-pain-list { list-style: none; padding: 0; margin: 0 0 18px 0; }
  .cta-pain-list li { padding: 4px 0 4px 16px; position: relative; font-size: 11.5px; color: #524F48; line-height: 1.55; }
  .cta-pain-list li::before { content: "—"; position: absolute; left: 0; color: #95928A; }
  .cta-outcome { padding: 10px 14px; border: 1px solid #E8E6E0; border-radius: 6px; margin-bottom: 8px; page-break-inside: avoid; break-inside: avoid; }
  .cta-outcome-label { font-size: 11px; font-weight: 700; color: #1A1830; margin-bottom: 3px; }
  .cta-outcome-body { font-size: 11px; color: #524F48; line-height: 1.55; }
  .cta-outcome-zero { border: 1px solid #1A6B3C; background: #F0F8F2; }
  .cta-outcome-zero .cta-outcome-label { color: #1A6B3C; }
  .cta-addon-section { margin-top: 16px; padding-top: 14px; border-top: 1px dashed #E8E6E0; page-break-inside: avoid; break-inside: avoid; }
  .cta-addon-title { font-size: 10.5px; font-weight: 700; color: #95928A; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 8px; }
  .cta-addon-item { padding: 8px 12px; background: #F8F7F3; border-radius: 4px; margin-bottom: 6px; font-size: 11px; color: #524F48; line-height: 1.5; page-break-inside: avoid; break-inside: avoid; }
  .cta-addon-item strong { color: #1A1830; }
  .cta-positioning { font-size: 11.5px; color: #524F48; line-height: 1.6; font-style: italic; margin-top: 18px; padding: 12px 14px; background: #FAF9F5; border-radius: 6px; border-left: 2px solid #95928A; page-break-inside: avoid; break-inside: avoid; }
  .cta-block { background: #1A1830; color: white; border-radius: 8px; padding: 18px 22px; margin-top: 14px; page-break-inside: avoid; break-inside: avoid; }
  .cta-headline { font-size: 14px; font-weight: 700; color: white; margin-bottom: 6px; letter-spacing: -0.01em; }
  .cta-body { font-size: 11.5px; color: rgba(255,255,255,0.78); line-height: 1.55; margin-bottom: 12px; }
  .cta-contact-row { font-size: 11px; color: rgba(255,255,255,0.88); margin: 3px 0; }
  .cta-contact-label { color: rgba(255,255,255,0.5); display: inline-block; width: 60px; }
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div>
      <div class="brand">Revelio</div>
      <div class="brand-sub">Revenue Leakage Diagnostic Platform</div>
    </div>
    <div class="ref">
      <strong>{{ reference }}</strong>
      {{ tier | upper }} Diagnostic &nbsp;·&nbsp; {{ report_date }}
    </div>
  </div>

  {% if is_internal %}
  <div class="internal-banner">INTERNAL COPY — OPERATOR USE ONLY — NOT FOR CLIENT DISTRIBUTION</div>
  {% endif %}

  <h1>{{ company_name }}</h1>
  <div class="meta">{{ vertical | title }} &nbsp;·&nbsp; Prepared {{ report_date }} &nbsp;·&nbsp; Confidence: <strong>{{ confidence | upper }}</strong></div>

  <div class="leakage-block">
    <div class="leakage-label">Annual revenue leakage — mid estimate</div>
    <div class="leakage-value">{{ currency }}{{ leakage_mid | int | format_number }}</div>
    <div class="leakage-sub">{{ revenue_impact_mid }}% of annual processing volume</div>
    <div class="range-row">
      <div class="range-item"><div class="rl">Conservative</div><div class="rv">{{ currency }}{{ leakage_low | int | format_number }}</div></div>
      <div class="range-item"><div class="rl">Base case</div><div class="rv">{{ currency }}{{ leakage_mid | int | format_number }}</div></div>
      <div class="range-item"><div class="rl">Upside</div><div class="rv">{{ currency }}{{ leakage_high | int | format_number }}</div></div>
    </div>
  </div>

  <h2>Executive summary</h2>
  <div class="narrative">{{ executive_summary }}</div>

  {% if primary_drivers %}
  <h2>Primary leakage drivers</h2>
  <table>
    <thead><tr><th>#</th><th>Driver</th><th>Est. impact (low–high)</th><th>Confidence</th><th>Basis</th></tr></thead>
    <tbody>
    {% for d in primary_drivers %}
    <tr>
      <td class="mono">{{ d.rank }}</td>
      <td>{{ d.driver }}</td>
      <td class="mono">{{ currency }}{{ d.estimated_impact_low | int | format_number }} – {{ currency }}{{ d.estimated_impact_high | int | format_number }}</td>
      <td class="{{ 'conf-' + d.confidence }}">{{ d.confidence | title }}</td>
      <td>{{ d.basis | title }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}

  {% if financial_breakdown %}
  <h2>Financial breakdown by category</h2>
  <table>
    <thead><tr><th>Category</th><th>Low estimate</th><th>Mid estimate</th><th>High estimate</th><th>Confidence</th></tr></thead>
    <tbody>
    {% for r in financial_breakdown %}
    <tr>
      <td>{{ r.category }}</td>
      <td class="mono">{{ currency }}{{ r.estimated_loss_low | int | format_number }}</td>
      <td class="mono">{{ currency }}{{ r.estimated_loss_mid | int | format_number }}</td>
      <td class="mono">{{ currency }}{{ r.estimated_loss_high | int | format_number }}</td>
      <td class="{{ 'conf-' + r.confidence }}">{{ r.confidence | title }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}

  {% if fix_priorities %}
  <h2>Recommended fix priorities</h2>
  {% if fix_priorities.immediate %}
  <div class="priority-section">
    <div class="priority-label immediate">Immediate (0–30 days)</div>
    {% for item in fix_priorities.immediate %}
    <div class="priority-item"><div class="priority-num">{{ loop.index }}</div><div>{{ item.action }}{% if item.estimated_recovery %} — <em>est. recovery: {{ item.estimated_recovery }}</em>{% endif %}</div></div>
    {% endfor %}
  </div>
  {% endif %}
  {% if fix_priorities.mid_term %}
  <div class="priority-section">
    <div class="priority-label mid">Medium-term (30–90 days)</div>
    {% for item in fix_priorities.mid_term %}
    <div class="priority-item"><div class="priority-num">{{ loop.index }}</div><div>{{ item.action }}</div></div>
    {% endfor %}
  </div>
  {% endif %}
  {% if fix_priorities.structural %}
  <div class="priority-section">
    <div class="priority-label structural">Structural (90+ days)</div>
    {% for item in fix_priorities.structural %}
    <div class="priority-item"><div class="priority-num">{{ loop.index }}</div><div>{{ item.action }}</div></div>
    {% endfor %}
  </div>
  {% endif %}
  {% endif %}

  {% if data_gaps %}
  <h2>Data gaps / what would improve precision</h2>
  {% for gap in data_gaps %}
  <div class="gap-item">{{ gap }}</div>
  {% endfor %}
  {% endif %}

  {% if is_internal and operator_notes %}
  <h2>Operator notes (internal only)</h2>
  <div class="internal-notes">{{ operator_notes }}</div>
  {% endif %}

  {% if not is_internal %}
  <div class="cta-section">
    <h2>The path forward</h2>
    <div class="cta-pain-narrative">
      You have seen where revenue is leaking. The harder question is what to do about it without committing your engineering roadmap to a six-month build, or putting trust in a provider whose commercial incentives may not fully align with yours.
    </div>
    <div class="cta-subheader">You are likely sitting with a familiar set of frustrations:</div>
    <ul class="cta-pain-list">
      <li>Multiple PSPs, each pulling in a slightly different direction.</li>
      <li>An authorisation rate you cannot quite explain, let alone improve.</li>
      <li>A board or CFO asking pointed questions, with no defensible answer.</li>
      <li>A tech team whose backlog is already full.</li>
      <li>A creeping sense that the stack has not had an honest, independent review in years.</li>
    </ul>

    <h2>What Revelio delivers</h2>
    <div class="cta-outcome cta-outcome-zero">
      <div class="cta-outcome-label">No fee for diagnosis or visibility</div>
      <div class="cta-outcome-body">The diagnostic and ongoing visibility into your payments stack carry no fee. Revelio only monetises on a small percentage of realised revenue recovery, paid once the strategy is live and the savings are validated. NDA and exclusivity during the engagement; you retain final approval on every recommendation.</div>
    </div>
    <div class="cta-outcome">
      <div class="cta-outcome-label">Provider-agnostic by design</div>
      <div class="cta-outcome-body">No commercial relationship with any PSP, orchestrator, or acquirer. The strategy works for you, not the providers.</div>
    </div>
    <div class="cta-outcome">
      <div class="cta-outcome-label">Immediate impact, no integration burden</div>
      <div class="cta-outcome-body">You do not need to commit internal engineering resources. The providers we recommend connect with no code and are already integrated with hundreds of global acquirers, PSPs, APMs and local payment methods. Your team stays on the roadmap; we handle the payments strategy and partner orchestration.</div>
    </div>
    <div class="cta-outcome">
      <div class="cta-outcome-label">Right tool, right time</div>
      <div class="cta-outcome-body">When new infrastructure is genuinely the answer, we connect you with the partner that fits your specific shape, not whoever pays the highest referral fee.</div>
    </div>
    <div class="cta-outcome">
      <div class="cta-outcome-label">Numbers you can take to a board</div>
      <div class="cta-outcome-body">Documented methodology, confidence-rated estimates, defensible under scrutiny.</div>
    </div>

    <div class="cta-addon-section">
      <div class="cta-addon-title">Optional add-on services</div>
      <div class="cta-addon-item"><strong>Pricing drift detection.</strong> Continuous monitoring for unannounced rate changes from your providers, flagged as soon as they hit your statements.</div>
      <div class="cta-addon-item"><strong>Contract compliance.</strong> Audit your fee statements against signed terms, surface reconciliation gaps and recoverable overcharges.</div>
      <div class="cta-addon-item"><strong>Enhanced provider pricing review and negotiation.</strong> Independent review of your pricing schedule with hands-on negotiation support, benchmarked against the market.</div>
    </div>

    <div class="cta-positioning">
      Revelio identifies where commercial leakage exists at no cost. We only monetise when deeper optimisation, execution, or realised recovery is required.
    </div>

    <div class="cta-block">
      <div class="cta-headline">Next step: speak with Revelio</div>
      <div class="cta-body">A 30-minute conversation with Dean Farley, founder. We take away the pain of building a new payments strategy and connect you with the right partners for maximum optimisation. Independent, provider-agnostic, focused on outcomes you can defend at board level.</div>
      <div class="cta-contact-row"><span class="cta-contact-label">Email</span> deanfarley84@gmail.com</div>
      <div class="cta-contact-row"><span class="cta-contact-label">UK</span> +44 (0) 7583 002 267</div>
      <div class="cta-contact-row"><span class="cta-contact-label">Spain</span> +34 711 018 011</div>
      <div class="cta-contact-row"><span class="cta-contact-label">LinkedIn</span> linkedin.com/in/df2024</div>
    </div>
  </div>
  {% endif %}

  <div class="footer">
    <span>Revelio &nbsp;·&nbsp; Payments Revenue Leakage Diagnostic Platform</span>
    <span>{{ reference }} &nbsp;·&nbsp; {{ report_date }}</span>
  </div>
</div>
</body>
</html>
"""


def _fmt_num(n):
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


async def generate_pdf(diagnostic, output: dict, is_internal: bool = False) -> tuple:
    estimate = output.get("annual_leakage_estimate", {})
    impact = output.get("revenue_impact_pct", {})

    env = Environment(loader=BaseLoader())
    env.filters["format_number"] = _fmt_num
    template = env.from_string(PDF_TEMPLATE)

    html_str = template.render(
        reference=diagnostic.reference,
        company_name=diagnostic.company_name,
        vertical=diagnostic.vertical or "",
        tier=diagnostic.tier,
        confidence=output.get("confidence_level", "medium"),
        report_date=datetime.now().strftime("%d %b %Y"),
        currency="£",
        leakage_low=estimate.get("low", 0),
        leakage_mid=estimate.get("mid", 0),
        leakage_high=estimate.get("high", 0),
        revenue_impact_mid=round(float(impact.get("mid", 0)), 1),
        executive_summary=output.get("executive_summary", ""),
        primary_drivers=output.get("primary_drivers", []),
        financial_breakdown=output.get("financial_breakdown", []),
        fix_priorities=output.get("recommended_fix_priorities", {}),
        data_gaps=output.get("data_gaps", []),
        is_internal=is_internal,
        operator_notes=diagnostic.operator_notes if is_internal else "",
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes, "application/pdf"


async def generate_csv(diagnostic, output: dict) -> tuple:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    estimate = output.get("annual_leakage_estimate", {})
    writer.writerow(["Revelio — Financial Breakdown Export"])
    writer.writerow(["Reference", diagnostic.reference])
    writer.writerow(["Company", diagnostic.company_name])
    writer.writerow(["Tier", diagnostic.tier])
    writer.writerow(["Date", datetime.now().strftime("%d %b %Y")])
    writer.writerow([])

    writer.writerow(["Annual Leakage Estimate", "Low", "Mid", "High"])
    writer.writerow(["GBP", estimate.get("low", 0), estimate.get("mid", 0), estimate.get("high", 0)])
    writer.writerow([])

    breakdown = output.get("financial_breakdown", [])
    if breakdown:
        writer.writerow(["Category Breakdown", "Low (£)", "Mid (£)", "High (£)", "Confidence", "Basis"])
        for row in breakdown:
            writer.writerow([
                row.get("category", ""), row.get("estimated_loss_low", 0),
                row.get("estimated_loss_mid", 0), row.get("estimated_loss_high", 0),
                row.get("confidence", ""), row.get("basis", ""),
            ])
        writer.writerow([])

    drivers = output.get("primary_drivers", [])
    if drivers:
        writer.writerow(["Primary Drivers", "Rank", "Low (£)", "High (£)", "Confidence"])
        for d in drivers:
            writer.writerow([
                d.get("driver", ""), d.get("rank", ""),
                d.get("estimated_impact_low", 0), d.get("estimated_impact_high", 0),
                d.get("confidence", ""),
            ])

    csv_bytes = buffer.getvalue().encode("utf-8")
    return csv_bytes, "text/csv"
