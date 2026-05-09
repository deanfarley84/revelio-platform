"""reports.py — Report generation and download"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from jinja2 import BaseLoader, Environment
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from weasyprint import HTML

from app.core.database import get_db
from app.core.auth import get_current_user, require_operator
from app.models.user import Diagnostic, ReportExport, User
from app.services.inline_jobs import generate_report_inline
from app.services.storage import download_file as storage_download

router = APIRouter()


_ROI_PDF_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @page { size: A4; margin: 22mm 18mm; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #0D0C0A; font-size: 12px; line-height: 1.55; }
  .header { border-bottom: 2px solid #1A1830; padding-bottom: 12px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: flex-end; }
  .brand { font-size: 16px; font-weight: 700; color: #1A1830; letter-spacing: -0.02em; }
  .brand-sub { font-size: 9px; color: #95928A; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }
  .ref { font-size: 10px; color: #95928A; text-align: right; }
  .ref strong { color: #0D0C0A; display: block; font-size: 11px; }
  h1 { font-size: 17px; font-weight: 700; color: #1A1830; margin: 4px 0; }
  h2 { font-size: 10px; font-weight: 600; color: #1A1830; margin: 14px 0 8px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #E8E6E0; padding-bottom: 4px; }
  .meta { font-size: 10px; color: #95928A; margin-bottom: 14px; }
  .inaction { background: #F5F4F1; border-left: 3px solid #1A1830; border-radius: 0 6px 6px 0; padding: 10px 14px; font-size: 11px; line-height: 1.55; color: #524F48; margin-bottom: 14px; }
  .inaction-label { font-size: 8.5px; font-weight: 600; color: #1A1830; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 3px; }
  .inaction strong { color: #0D0C0A; }
  .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 14px; }
  .kpi { border: 1px solid #E8E6E0; border-radius: 6px; padding: 9px 11px; }
  .kpi-label { font-size: 8px; color: #95928A; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 4px; }
  .kpi-value { font-size: 15px; font-weight: 600; color: #1A1830; }
  .kpi-value.small { font-size: 12px; }
  .kpi-sub { font-size: 8.5px; color: #95928A; margin-top: 2px; }
  .tag { display: inline-block; background: #DCEFE1; color: #1A6B3C; font-size: 8.5px; font-weight: 600; padding: 1px 6px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.05em; margin-left: 4px; vertical-align: middle; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
  th { font-size: 9px; font-weight: 600; color: #95928A; text-transform: uppercase; letter-spacing: 0.05em; padding: 6px 8px; text-align: left; border-bottom: 1px solid #E8E6E0; }
  td { padding: 6px 8px; font-size: 11px; border-bottom: 1px solid #F0EEE9; }
  tr:last-child td { border-bottom: none; }
  .right { text-align: right; }
  .mono { font-family: monospace; }
  .footer { margin-top: 14px; font-size: 9.5px; color: #95928A; line-height: 1.5; border-top: 1px solid #E8E6E0; padding-top: 9px; }
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">Revelio</div>
      <div class="brand-sub">Revenue Leakage Diagnostics</div>
    </div>
    <div class="ref">
      <strong>{{ company }}</strong>
      ROI summary, {{ generated_at }}
    </div>
  </div>

  <h1>ROI summary</h1>
  <div class="meta">Modelling horizon: {{ timeframe_months }} months</div>

  {% if totals.gross_period_recoverable > 0 %}
  <div class="inaction">
    <div class="inaction-label">Cost of inaction</div>
    Over the next {{ timeframe_months }} months, doing nothing leaves <strong>{{ fmt(totals.gross_period_recoverable) }}</strong> on the table.
    {% if cost_state == "pure_recovery" %}
      Recovering it costs £0, most fixes are configuration changes or conversations with your existing providers.
    {% elif cost_state == "orchestration_only" %}
      Recovering it requires <strong>{{ fmt(totals.orch_annual) }}/year</strong> in orchestration fees, netting <strong>{{ fmt(totals.period_recoverable) }}</strong> over that period.
    {% elif cost_state == "advisory_only" %}
      One-off advisory of <strong>{{ fmt(totals.one_off_cost) }}</strong> recovers <strong>{{ fmt(totals.period_recoverable - totals.one_off_cost) }}</strong> net.
    {% elif cost_state == "both" %}
      <strong>{{ fmt(totals.one_off_cost) }}</strong> advisory plus <strong>{{ fmt(totals.orch_annual) }}/year</strong> fees recover <strong>{{ fmt(totals.period_recoverable - totals.one_off_cost) }}</strong> net.
    {% endif %}
  </div>
  {% endif %}

  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-label">Recoverable ({{ timeframe_months }}m)</div>
      <div class="kpi-value">{{ fmt(totals.period_recoverable) }}</div>
      <div class="kpi-sub">{{ fmt(scenario_range.low_recoverable) }}–{{ fmt(scenario_range.high_recoverable) }} range</div>
    </div>
    {% if cost_state == "pure_recovery" %}
      <div class="kpi">
        <div class="kpi-label">Cost to recover</div>
        <div class="kpi-value">£0<span class="tag">Pure recovery</span></div>
        <div class="kpi-sub">No spend required</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Recovery type</div>
        <div class="kpi-value small">Pure recovery</div>
        <div class="kpi-sub">Configuration and vendor changes</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Recovery starts</div>
        <div class="kpi-value small">Immediately</div>
        <div class="kpi-sub">No payback period</div>
      </div>
    {% else %}
      <div class="kpi">
        <div class="kpi-label">Implementation cost</div>
        <div class="kpi-value">{{ fmt(totals.one_off_cost) }}</div>
        <div class="kpi-sub">{% if totals.orch_annual > 0 %}One-off, plus {{ fmt(totals.orch_annual) }}/yr{% else %}One-off{% endif %}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">ROI multiple</div>
        {% if totals.one_off_cost > 0 %}
          <div class="kpi-value">{% if totals.roi_multiple is not none %}{{ "%.1fx"|format(totals.roi_multiple) }}{% else %}—{% endif %}</div>
          <div class="kpi-sub">{% if scenario_range.low_roi is not none and scenario_range.high_roi is not none %}{{ "%.1fx"|format(scenario_range.low_roi) }}–{{ "%.1fx"|format(scenario_range.high_roi) }} range{% else %}Period return ÷ cost{% endif %}</div>
        {% else %}
          <div class="kpi-value small">Pure recovery (after fees)</div>
          <div class="kpi-sub">{{ fmt(totals.orch_annual) }}/yr orchestration</div>
        {% endif %}
      </div>
      <div class="kpi">
        <div class="kpi-label">Payback</div>
        {% if totals.one_off_cost > 0 %}
          <div class="kpi-value">{{ payback_primary }}</div>
          <div class="kpi-sub">{{ payback_secondary }}</div>
        {% else %}
          <div class="kpi-value small">Immediately</div>
          <div class="kpi-sub">No one-off cost</div>
        {% endif %}
      </div>
    {% endif %}
  </div>

  <h2>Drivers</h2>
  <table>
    <thead>
      <tr>
        <th>Driver</th>
        <th class="right">Annual loss</th>
        <th class="right">Recovery %</th>
        <th class="right">Net annual</th>
      </tr>
    </thead>
    <tbody>
      {% for d in drivers %}
      <tr>
        <td>{{ d.category }}</td>
        <td class="right mono">{{ fmt(d.estimated_loss) }}</td>
        <td class="right mono">{{ d.recovery_rate }}%</td>
        <td class="right mono">{{ fmt(d.net_annual) }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  {% if cost_overlay and (cost_overlay.orchestration_annual_cost is not none or cost_overlay.advisory_fee is not none) %}
  <h2>Cost overlays</h2>
  <table>
    <thead>
      <tr>
        <th>Overlay</th>
        <th>Detail</th>
        <th class="right">Amount</th>
      </tr>
    </thead>
    <tbody>
      {% if cost_overlay.orchestration_annual_cost is not none %}
      <tr>
        <td>Orchestration adoption</td>
        <td>{{ cost_overlay.orchestration_notes or "Recurring per-tx or annual fees" }}</td>
        <td class="right mono">{{ fmt(cost_overlay.orchestration_annual_cost) }}/yr</td>
      </tr>
      {% endif %}
      {% if cost_overlay.advisory_fee is not none %}
      <tr>
        <td>Revelio advisory</td>
        <td>One-off engagement fee</td>
        <td class="right mono">{{ fmt(cost_overlay.advisory_fee) }}</td>
      </tr>
      {% endif %}
    </tbody>
  </table>
  {% endif %}

  <div class="footer">
    <strong style="color:#0D0C0A;">Method:</strong>
    Recoverable revenue = annual loss × recovery rate. Period recoverable scales by timeframe.
    Implementation cost defaults to £0; orchestration adoption applies a recurring annual fee that reduces net recovery; advisory is the only one-off cost.
    ROI multiple = period recoverable ÷ one-off cost (where applicable). Payback = one-off cost ÷ monthly recoverable.
    Low/high band reflects variance around the mid recovery rate; figures are directional and depend on the underlying diagnostic confidence.
  </div>
</body>
</html>
"""


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "scenario"


def _fmt_currency(v):
    try:
        v = float(v if v is not None else 0)
    except (TypeError, ValueError):
        return "£0"
    sign = "-" if v < 0 else ""
    return f"{sign}£{abs(v):,.0f}"


def _fmt_payback(weeks):
    if weeks is None:
        return ("—", "No cost entered")
    days = weeks * 7
    months = weeks / 4.33
    if days < 14:
        return (f"{round(days)}d", f"~{weeks:.1f} weeks")
    if weeks < 52:
        return (f"{weeks:.1f}w", f"~{months:.1f} months")
    return (f"{months:.1f}mo", f"~{months/12:.1f} years")


_VALID_COST_STATES = {"pure_recovery", "orchestration_only", "advisory_only", "both"}


@router.post("/roi/pdf")
async def generate_roi_pdf(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Render the ROI calculator state as a single-page A4 PDF."""
    company = (payload.get("companyName") or "Scenario").strip() or "Scenario"
    timeframe_months = int(payload.get("timeframeMonths") or 12)
    drivers_in = payload.get("drivers") or []
    totals_in = payload.get("totals") or {}
    scenario_range_in = payload.get("scenarioRange") or {}
    cost_overlay_in = payload.get("costOverlay")
    cost_state = payload.get("costState") or "pure_recovery"
    if cost_state not in _VALID_COST_STATES:
        cost_state = "pure_recovery"

    drivers = []
    for d in drivers_in:
        try:
            loss = float(d.get("estimatedLoss") or 0)
            rate = float(d.get("recoveryRate") or 0)
        except (TypeError, ValueError):
            continue
        recoverable = loss * rate / 100
        drivers.append({
            "category": d.get("category") or "—",
            "estimated_loss": loss,
            "recovery_rate": int(round(rate)),
            "net_annual": recoverable,
        })

    payback_primary, payback_secondary = _fmt_payback(totals_in.get("paybackWeeks"))

    cost_overlay = None
    if isinstance(cost_overlay_in, dict):
        cost_overlay = {
            "orchestration_annual_cost": cost_overlay_in.get("orchestrationAnnualCost"),
            "orchestration_notes": cost_overlay_in.get("orchestrationNotes") or "",
            "advisory_fee": cost_overlay_in.get("advisoryFee"),
        }

    env = Environment(loader=BaseLoader(), autoescape=True)
    template = env.from_string(_ROI_PDF_TEMPLATE)
    html_str = template.render(
        company=company,
        generated_at=datetime.utcnow().strftime("%d %b %Y"),
        timeframe_months=timeframe_months,
        drivers=drivers,
        totals={
            "gross_period_recoverable": float(totals_in.get("grossPeriodRecoverable") or 0),
            "period_recoverable": float(totals_in.get("periodRecoverable") or 0),
            "total_cost": float(totals_in.get("totalCost") or 0),
            "orch_annual": float(totals_in.get("orchAnnual") or 0),
            "one_off_cost": float(totals_in.get("oneOffCost") or 0),
            "roi_multiple": totals_in.get("roiMultiple"),
        },
        scenario_range={
            "low_recoverable": float(scenario_range_in.get("lowRecoverable") or 0),
            "high_recoverable": float(scenario_range_in.get("highRecoverable") or 0),
            "low_roi": scenario_range_in.get("lowRoi"),
            "high_roi": scenario_range_in.get("highRoi"),
        },
        cost_overlay=cost_overlay,
        cost_state=cost_state,
        payback_primary=payback_primary,
        payback_secondary=payback_secondary,
        fmt=_fmt_currency,
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    filename = f"revelio-roi-{_slug(company)}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{diagnostic_id}/generate")
async def trigger_report_generation(
    diagnostic_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diag = await db.get(Diagnostic, diagnostic_id)
    if not diag:
        raise HTTPException(404, "Diagnostic not found")

    is_admin = current_user.role in ("super_admin", "operator_admin", "analyst")
    is_internal = payload.get("internal", False) and is_admin
    export_type = payload.get("type", "pdf")

    if not is_admin and diag.status != "released":
        raise HTTPException(403, "Report not yet released")

    result = await generate_report_inline(db, diagnostic_id, export_type, str(current_user.id), is_internal)
    if result.get("error"):
        raise HTTPException(500, result["error"])
    return {"status": "generated", "type": export_type, "storage_key": result.get("storage_key")}


@router.get("/{diagnostic_id}/exports")
async def list_exports(
    diagnostic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ReportExport)
        .where(ReportExport.diagnostic_id == diagnostic_id)
        .order_by(desc(ReportExport.generated_at))
    )
    exports = result.scalars().all()
    is_admin = current_user.role in ("super_admin", "operator_admin", "analyst")
    return [
        {
            "id": str(e.id),
            "export_type": e.export_type,
            "is_internal": e.is_internal,
            "generated_at": e.generated_at.isoformat() if e.generated_at else None,
        }
        for e in exports
        if is_admin or not e.is_internal
    ]


@router.get("/{diagnostic_id}/exports/{export_id}/download")
async def download_export(
    diagnostic_id: str,
    export_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    export = await db.get(ReportExport, export_id)
    if not export or str(export.diagnostic_id) != diagnostic_id:
        raise HTTPException(404, "Export not found")

    is_admin = current_user.role in ("super_admin", "operator_admin", "analyst")
    if export.is_internal and not is_admin:
        raise HTTPException(403, "Access denied")

    try:
        content = await storage_download(export.storage_key)
        if not content:
            raise HTTPException(404, "Export file not found in storage")
        media_type = "application/pdf" if export.export_type == "pdf" else "text/csv"
        filename = f"revelio_{export.diagnostic_id}_{export.export_type}.{export.export_type}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Download failed: {str(e)}")
