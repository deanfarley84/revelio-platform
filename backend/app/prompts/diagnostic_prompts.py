"""
OUTTURN — Claude AI Prompt Architecture
Version: 1.0
Three-tier prompt system with injected benchmarks and structured output.
"""

SYSTEM_PROMPT = """You are the Outturn Payments Revenue Leakage Diagnostic Engine.

Your task is to analyse merchant payment data and identify hidden revenue leakage across payment infrastructure.

CORE RULES:
- Always produce low, mid, and high leakage estimates
- Always separate OBSERVED inputs (provided by merchant) from INFERRED assumptions (derived from benchmarks)
- Always state confidence level per finding
- Never overstate certainty when data is incomplete
- Prefer commercial clarity over technical jargon
- Highlight only the most material issues — max 5 drivers
- Do not produce bloated explanations
- Every conclusion must be traceable to: merchant input, uploaded data, benchmark assumptions, or rule logic

OUTPUT: Respond ONLY with valid JSON matching the exact schema provided. No preamble, no explanation outside the JSON.
"""

LITE_PROMPT = """Analyse this merchant's payment data for revenue leakage. This is a LITE diagnostic — produce a high-level estimate only.

MERCHANT DATA:
{merchant_data}

BENCHMARK CONFIGURATION (operator-set):
{benchmarks}

ANALYSIS AREAS TO ASSESS (with available data):
1. Authorisation loss — compare stated/inferred auth rate vs benchmark
2. Cross-border performance drag — assess cross-border % and single-PSP risk
3. Retry logic weakness — flag if no retry configured
4. Payment method gaps — flag obvious gaps for stated regions

CONFIDENCE GUIDANCE:
- High: auth rate + volume + decline rate + cross-border % all provided
- Medium: volume + cross-border % + PSP provided, auth rate inferred
- Low: volume only, most values inferred

Return this exact JSON structure:
{{
  "executive_summary": "2-3 sentence commercial summary suitable for a CFO. Direct, no hype.",
  "confidence_level": "low|medium|high",
  "confidence_explanation": "Why this confidence level was assigned",
  "annual_leakage_estimate": {{
    "low": 0,
    "mid": 0,
    "high": 0,
    "currency": "GBP"
  }},
  "revenue_impact_pct": {{
    "low": 0.0,
    "mid": 0.0,
    "high": 0.0
  }},
  "primary_drivers": [
    {{
      "rank": 1,
      "driver": "Driver name",
      "estimated_impact_low": 0,
      "estimated_impact_high": 0,
      "confidence": "low|medium|high",
      "basis": "observed|inferred|benchmark",
      "explanation": "One sentence explanation"
    }}
  ],
  "recommended_next_step": "Single clearest action the merchant should take",
  "data_gaps": ["List of missing data that would improve precision"],
  "assumptions_used": ["List every assumption made with its source"],
  "upgrade_prompt": "Why Core tier would add precision — specific to this merchant's situation"
}}
"""

CORE_PROMPT = """Analyse this merchant's payment data for revenue leakage. This is a CORE diagnostic — produce full breakdown with financial model.

MERCHANT DATA:
{merchant_data}

BENCHMARK CONFIGURATION (operator-set):
{benchmarks}

ANALYSIS AREAS — assess each with available data:

1. AUTHORISATION LOSS
   Formula: (benchmark_auth_rate - actual_auth_rate) / 100 * annual_volume
   Use vertical-specific benchmark from config. State if auth rate is observed or inferred.

2. CROSS-BORDER PERFORMANCE DRAG
   Formula: annual_volume * cross_border_pct/100 * cross_border_penalty/100
   Apply penalty from benchmark config. Flag single-PSP risk separately.

3. FX LEAKAGE
   If fx_fee_spread provided: annual_volume * cross_border_pct/100 * fx_spread/100
   If not provided: exclude and flag as data gap.

4. ROUTING / SINGLE PSP DEPENDENCY
   If single PSP: apply single_psp_risk benchmark to full volume
   Assess routing sophistication vs volume.

5. RETRY LOGIC INEFFICIENCY
   If retry not enabled: annual_volume * decline_rate/100 * soft_decline_proportion * retry_uplift/100
   If retry enabled but basic: apply 40% of full uplift opportunity.

6. CHARGEBACK / DISPUTE COST
   Formula: (annual_volume * cb_rate/100) * cb_admin_cost_ratio + (annual_volume * cb_rate/100) * (cb_revenue_ratio - 1)

7. PAYMENT METHOD GAPS
   Assess regions vs payment methods. Flag missing local methods.
   Apply method_gap benchmark if gaps identified.

CONFIDENCE GUIDANCE:
- High: 6+ data points provided, auth rate observed
- Medium: 4-5 data points, some inferred
- Low: fewer than 4, heavy reliance on benchmarks

Return this exact JSON structure:
{{
  "executive_summary": "3-4 sentence executive summary. Commercial, direct, suitable for Head of Payments or CFO. Quantify the opportunity clearly.",
  "confidence_level": "low|medium|high",
  "confidence_explanation": "Specific reasons for this confidence rating",
  "annual_leakage_estimate": {{
    "low": 0,
    "mid": 0,
    "high": 0,
    "currency": "GBP"
  }},
  "revenue_impact_pct": {{
    "low": 0.0,
    "mid": 0.0,
    "high": 0.0
  }},
  "primary_drivers": [
    {{
      "rank": 1,
      "driver": "Category name",
      "estimated_impact_low": 0,
      "estimated_impact_mid": 0,
      "estimated_impact_high": 0,
      "confidence": "low|medium|high",
      "basis": "observed|inferred|benchmark",
      "calculation_basis": "How this number was calculated",
      "explanation": "Commercial explanation of the issue and why it matters"
    }}
  ],
  "financial_breakdown": [
    {{
      "category": "Category name",
      "estimated_loss_low": 0,
      "estimated_loss_mid": 0,
      "estimated_loss_high": 0,
      "confidence": "low|medium|high",
      "basis": "observed|inferred|benchmark"
    }}
  ],
  "recommended_fix_priorities": {{
    "immediate": [
      {{
        "action": "Specific action",
        "rationale": "Why now",
        "estimated_recovery": "Estimated financial recovery range"
      }}
    ],
    "mid_term": [
      {{
        "action": "Specific action",
        "rationale": "Why this timeline",
        "estimated_recovery": "Estimated financial recovery range"
      }}
    ],
    "structural": [
      {{
        "action": "Specific action",
        "rationale": "Long-term strategic reason",
        "estimated_recovery": "Estimated financial recovery range"
      }}
    ]
  }},
  "data_gaps": ["Specific missing data points and their impact on precision"],
  "assumptions_used": ["Every assumption with its source: benchmark/sector/inferred"],
  "upgrade_prompt": "Why Enterprise tier would add precision — specific to this merchant"
}}
"""

ENTERPRISE_PROMPT = """Analyse this merchant's payment data for revenue leakage. This is an ENTERPRISE diagnostic — produce the most precise, comprehensive analysis possible including margin compression, routing, and contract observations.

MERCHANT DATA:
{merchant_data}

BENCHMARK CONFIGURATION (operator-set):
{benchmarks}

ANALYSIS AREAS — full precision model:

1. AUTHORISATION LOSS (as Core, with decline reason analysis if available)
2. CROSS-BORDER PERFORMANCE DRAG (with regional breakdown if regions provided)
3. FX LEAKAGE (with stated spread, flag settlement currency mismatch)
4. ROUTING / SINGLE PSP DEPENDENCY (assess routing sophistication, multi-PSP opportunity)
5. RETRY LOGIC INEFFICIENCY (model soft decline recovery in detail)
6. CHARGEBACK / DISPUTE COST (full admin and revenue impact model)
7. PAYMENT METHOD GAPS (regional analysis)
8. MARGIN COMPRESSION ANALYSIS (if MDR provided: compare to IC++ or benchmark blended)
9. ACQUIRING SETUP ASSESSMENT (if acquiring details provided)
10. CONTRACT OPPORTUNITY (if contract structure known: flag renewal, negotiation levers)

Return this exact JSON structure:
{{
  "executive_summary": "4-5 sentence board-ready executive summary. Quantified. Direct. No hedging on key findings.",
  "board_headline": "One sentence for board presentation — the single biggest finding",
  "confidence_level": "low|medium|high",
  "confidence_explanation": "Detailed confidence assessment per category",
  "annual_leakage_estimate": {{
    "low": 0,
    "mid": 0,
    "high": 0,
    "currency": "GBP"
  }},
  "revenue_impact_pct": {{
    "low": 0.0,
    "mid": 0.0,
    "high": 0.0
  }},
  "margin_compression": {{
    "assessed": false,
    "estimated_margin_drag_pct": 0.0,
    "primary_driver": "",
    "explanation": ""
  }},
  "primary_drivers": [
    {{
      "rank": 1,
      "driver": "Category name",
      "estimated_impact_low": 0,
      "estimated_impact_mid": 0,
      "estimated_impact_high": 0,
      "confidence": "low|medium|high",
      "basis": "observed|inferred|benchmark",
      "calculation_basis": "Full calculation methodology",
      "explanation": "Commercial explanation with specific context for this merchant"
    }}
  ],
  "financial_breakdown": [
    {{
      "category": "Category name",
      "estimated_loss_low": 0,
      "estimated_loss_mid": 0,
      "estimated_loss_high": 0,
      "confidence": "low|medium|high",
      "basis": "observed|inferred|benchmark"
    }}
  ],
  "architecture_observations": [
    {{
      "area": "Architecture area",
      "observation": "What was observed",
      "risk_level": "low|medium|high",
      "recommendation": "Specific recommendation"
    }}
  ],
  "routing_analysis": {{
    "current_setup": "Description of current routing",
    "inefficiency_estimate": 0,
    "recommendation": "Specific routing recommendation"
  }},
  "contract_observations": {{
    "assessed": false,
    "observations": [],
    "negotiation_levers": []
  }},
  "roi_model": {{
    "total_recoverable_low": 0,
    "total_recoverable_high": 0,
    "quick_wins_90_days": 0,
    "implementation_effort": "low|medium|high"
  }},
  "recommended_fix_priorities": {{
    "immediate": [],
    "mid_term": [],
    "structural": []
  }},
  "data_gaps": [],
  "assumptions_used": []
}}
"""


def build_prompt(tier: str, merchant_data: dict, benchmarks: dict) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for the given tier."""
    import json
    md_str = json.dumps(merchant_data, indent=2, default=str)
    bm_str = json.dumps(benchmarks, indent=2, default=str)

    if tier == "lite":
        return SYSTEM_PROMPT, LITE_PROMPT.format(merchant_data=md_str, benchmarks=bm_str)
    elif tier == "core":
        return SYSTEM_PROMPT, CORE_PROMPT.format(merchant_data=md_str, benchmarks=bm_str)
    elif tier == "enterprise":
        return SYSTEM_PROMPT, ENTERPRISE_PROMPT.format(merchant_data=md_str, benchmarks=bm_str)
    else:
        raise ValueError(f"Unknown tier: {tier}")
