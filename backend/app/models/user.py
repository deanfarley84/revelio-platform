from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Integer, Text, ARRAY, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Organisation(Base):
    __tablename__ = "organisations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    website = Column(Text)
    vertical = Column(Text)
    tier = Column(Text, nullable=False, default="lite")
    is_active = Column(Boolean, nullable=False, default=True)
    is_demo = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="organisation")
    diagnostics = relationship("Diagnostic", back_populates="organisation")
    intel = relationship("ClientIntel", back_populates="organisation", uselist=False)


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"))
    email = Column(Text, nullable=False, unique=True)
    full_name = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default="client_admin")
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organisation = relationship("Organisation", back_populates="users")


class BenchmarkConfig(Base):
    __tablename__ = "benchmark_config"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(Text, nullable=False)
    key = Column(Text, nullable=False)
    label = Column(Text, nullable=False)
    value_low = Column(Numeric(10, 4), nullable=False)
    value_high = Column(Numeric(10, 4), nullable=False)
    value_default = Column(Numeric(10, 4), nullable=False)
    unit = Column(Text, nullable=False, default="percent")
    vertical = Column(Text, default="all")
    notes = Column(Text)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Diagnostic(Base):
    __tablename__ = "diagnostics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference = Column(Text, nullable=False, unique=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tier = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="draft")
    is_demo = Column(Boolean, nullable=False, default=False, server_default="false")
    company_name = Column(Text, nullable=False)
    website = Column(Text)
    vertical = Column(Text, nullable=False)
    monthly_volume = Column(Numeric(20, 2))
    monthly_transactions = Column(Integer)
    avg_order_value = Column(Numeric(10, 2))
    cross_border_pct = Column(Numeric(5, 2))
    psps_used = Column(ARRAY(Text))
    regions = Column(JSONB)
    auth_rate = Column(Numeric(5, 2))
    decline_rate = Column(Numeric(5, 2))
    soft_decline_pct = Column(Numeric(5, 2))
    hard_decline_pct = Column(Numeric(5, 2))
    top_decline_reasons = Column(ARRAY(Text))
    chargeback_rate = Column(Numeric(5, 2))
    refund_rate = Column(Numeric(5, 2))
    payment_methods = Column(ARRAY(Text))
    retry_enabled = Column(Boolean)
    retry_notes = Column(Text)
    checkout_currencies = Column(ARRAY(Text))
    settlement_currencies = Column(ARRAY(Text))
    pricing_model = Column(Text)
    mdr = Column(Numeric(5, 4))
    fx_fee_spread = Column(Numeric(5, 4))
    scheme_fee_visibility = Column(Text)
    acquiring_setup = Column(Text)
    routing_setup = Column(Text)
    additional_context = Column(Text)
    parsed_data = Column(JSONB)
    ai_output = Column(JSONB)
    ai_model = Column(Text)
    ai_prompt_version = Column(Text)
    ai_tokens_used = Column(Integer)
    ai_run_at = Column(DateTime(timezone=True))
    operator_notes = Column(Text)
    override_enabled = Column(Boolean, default=False)
    override_reason = Column(Text)
    override_low = Column(Numeric(20, 2))
    override_mid = Column(Numeric(20, 2))
    override_high = Column(Numeric(20, 2))
    override_confidence = Column(Text)
    override_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    override_at = Column(DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    released_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    final_output = Column(JSONB)
    benchmarks_snapshot = Column(JSONB)
    submitted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organisation = relationship("Organisation", back_populates="diagnostics")
    files = relationship("UploadedFile", back_populates="diagnostic")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnostic_id = Column(UUID(as_uuid=True), ForeignKey("diagnostics.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False)
    file_name = Column(Text, nullable=False)
    file_type = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    storage_key = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="uploaded")
    parsed_fields = Column(JSONB)
    parse_confidence = Column(Numeric(3, 2))
    parse_notes = Column(Text)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    parsed_at = Column(DateTime(timezone=True))

    diagnostic = relationship("Diagnostic", back_populates="files")


class ClientIntel(Base):
    __tablename__ = "client_intel"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False, unique=True)
    opportunity_stage = Column(Text, default="engaged")
    score = Column(Integer)
    notes = Column(Text)
    tags = Column(ARRAY(Text))
    key_contacts = Column(JSONB)
    contract_notes = Column(Text)
    contract_renewal = Column(Text)
    upsell_signals = Column(ARRAY(Text))
    follow_up_date = Column(Text)
    total_leakage_identified = Column(Numeric(20, 2))
    diagnostics_count = Column(Integer, default=0)
    last_activity_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organisation = relationship("Organisation", back_populates="intel")


class ClientIntelLog(Base):
    __tablename__ = "client_intel_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False)
    note = Column(Text, nullable=False)
    note_type = Column(Text, default="general")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnostic_id = Column(UUID(as_uuid=True), ForeignKey("diagnostics.id"))
    job_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="queued")
    payload = Column(JSONB)
    result = Column(JSONB)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"))
    action = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(UUID(as_uuid=True))
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    ip_address = Column(INET)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text)
    extra_metadata = Column("metadata", JSONB)  # 'metadata' is reserved on DeclarativeBase; map to a safe attr name
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReportExport(Base):
    __tablename__ = "report_exports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnostic_id = Column(UUID(as_uuid=True), ForeignKey("diagnostics.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False)
    export_type = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_internal = Column(Boolean, default=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
