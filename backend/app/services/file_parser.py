"""
File Parser Service
Parses uploaded CSV, XLSX, XLS, PDF files and extracts payment data fields.
Returns structured dict of detected fields with confidence scores.
"""
import io
import re
from typing import Optional
import pandas as pd
import pdfplumber


# Field aliases — maps common column names in PSP exports to our field schema
FIELD_ALIASES = {
    "monthly_volume": [
        "total_volume", "gross_volume", "processing_volume", "total_processed",
        "volume", "total_sales", "gross_sales", "net_volume"
    ],
    "monthly_transactions": [
        "transaction_count", "total_transactions", "num_transactions",
        "count", "transactions", "payment_count", "number_of_transactions"
    ],
    "avg_order_value": [
        "average_order_value", "aov", "avg_transaction_value", "average_transaction",
        "average_value", "mean_order_value"
    ],
    "auth_rate": [
        "authorisation_rate", "authorization_rate", "auth_rate", "approval_rate",
        "success_rate", "approval_ratio", "authorisation_ratio"
    ],
    "decline_rate": [
        "decline_rate", "failure_rate", "rejection_rate", "declined_pct",
        "refusal_rate", "failed_pct"
    ],
    "chargeback_rate": [
        "chargeback_rate", "dispute_rate", "cb_rate", "chargeback_ratio",
        "chargebacks_pct"
    ],
    "refund_rate": [
        "refund_rate", "return_rate", "refund_ratio", "refunds_pct"
    ],
    "cross_border_pct": [
        "cross_border_pct", "international_pct", "cross_border_percentage",
        "international_transactions_pct", "foreign_pct"
    ],
    "fx_fee_spread": [
        "fx_fee", "fx_spread", "fx_rate", "foreign_exchange_fee",
        "currency_conversion_fee", "fx_margin"
    ],
    "mdr": [
        "mdr", "merchant_discount_rate", "processing_fee", "blended_rate",
        "effective_rate"
    ],
}

# PDF text patterns for common PSP statement formats
PDF_PATTERNS = {
    "monthly_volume": [
        r"(?:total|gross)\s+(?:volume|processed)[:\s]+[£$€]?([\d,]+(?:\.\d{2})?)",
        r"[£$€]([\d,]+(?:\.\d{2})?)\s+(?:total|processed|volume)",
    ],
    "auth_rate": [
        r"(?:auth(?:orisation|orization)|approval)\s+rate[:\s]+([\d.]+)%",
        r"([\d.]+)%\s+(?:auth(?:orisation|orization)|approval)\s+rate",
    ],
    "decline_rate": [
        r"(?:decline|failure|rejection)\s+rate[:\s]+([\d.]+)%",
    ],
    "chargeback_rate": [
        r"(?:chargeback|dispute)\s+rate[:\s]+([\d.]+)%",
    ],
    "cross_border_pct": [
        r"(?:cross[\-\s]border|international)\s+(?:transactions|volume)[:\s]+([\d.]+)%",
    ],
}


def normalise_column(col: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", col.lower().strip()).strip("_")


def detect_field(col_normalised: str, aliases: list) -> bool:
    for alias in aliases:
        if alias.replace(" ", "_") in col_normalised or col_normalised in alias.replace(" ", "_"):
            return True
    return False


def parse_numeric(val) -> Optional[float]:
    if val is None:
        return None
    try:
        clean = str(val).replace(",", "").replace("£", "").replace("$", "").replace("€", "").replace("%", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return None


def parse_csv_or_excel(file_bytes: bytes, file_type: str) -> dict:
    """Parse CSV or Excel file and extract payment fields."""
    try:
        if file_type in ("csv", "txt"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        return {"error": str(e), "confidence": 0.0, "fields": {}}

    # Normalise column names
    col_map = {col: normalise_column(col) for col in df.columns}
    df = df.rename(columns=col_map)

    extracted = {}
    detected_cols = []

    for field, aliases in FIELD_ALIASES.items():
        for col in df.columns:
            if detect_field(col, aliases):
                # Take first non-null value or sum/mean depending on field type
                series = df[col].dropna()
                if len(series) == 0:
                    continue
                if field in ("monthly_volume", "monthly_transactions"):
                    val = parse_numeric(series.sum())
                else:
                    val = parse_numeric(series.mean())
                if val is not None:
                    extracted[field] = round(val, 4)
                    detected_cols.append(col)
                break

    confidence = min(1.0, len(extracted) / 5)

    return {
        "fields": extracted,
        "confidence": round(confidence, 2),
        "detected_columns": detected_cols,
        "total_columns": len(df.columns),
        "row_count": len(df),
        "notes": f"Parsed {len(df)} rows, detected {len(extracted)} relevant fields",
    }


def parse_pdf(file_bytes: bytes) -> dict:
    """Parse PDF statement and extract payment fields using pattern matching."""
    extracted = {}
    all_text = ""

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"
    except Exception as e:
        return {"error": str(e), "confidence": 0.0, "fields": {}}

    # Apply patterns
    for field, patterns in PDF_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                val = parse_numeric(match.group(1))
                if val is not None:
                    extracted[field] = val
                break

    # Detect PSP name
    psp_keywords = {
        "stripe": "Stripe", "adyen": "Adyen", "braintree": "Braintree",
        "worldpay": "Worldpay", "checkout": "Checkout.com", "paypal": "PayPal",
        "square": "Square", "klarna": "Klarna", "mollie": "Mollie",
    }
    for keyword, psp_name in psp_keywords.items():
        if keyword in all_text.lower():
            extracted["psp_detected"] = psp_name
            break

    confidence = min(1.0, len(extracted) / 4)

    return {
        "fields": extracted,
        "confidence": round(confidence, 2),
        "text_length": len(all_text),
        "notes": f"Extracted {len(extracted)} fields from PDF via pattern matching",
    }


def parse_file(file_bytes: bytes, file_type: str) -> dict:
    """Main entry — route to appropriate parser."""
    if file_type == "pdf":
        return parse_pdf(file_bytes)
    elif file_type in ("csv", "xlsx", "xls", "txt"):
        return parse_csv_or_excel(file_bytes, file_type)
    else:
        return {"error": f"Unsupported file type: {file_type}", "confidence": 0.0, "fields": {}}


def merge_parsed_fields(parsed_results: list) -> dict:
    """
    Merge parsed fields from multiple files.
    Later files override earlier ones. Keeps track of sources.
    """
    merged = {}
    sources = {}

    for result in parsed_results:
        fields = result.get("fields", {})
        file_name = result.get("file_name", "unknown")
        for field, value in fields.items():
            merged[field] = value
            sources[field] = file_name

    return {"fields": merged, "sources": sources}
