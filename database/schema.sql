-- ============================================================
-- REVELIO: PAYMENTS REVENUE LEAKAGE DIAGNOSTIC PLATFORM
-- PostgreSQL Schema v1.0
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE user_role AS ENUM ('super_admin','operator_admin','analyst','client_admin','client_viewer');
CREATE TYPE service_tier AS ENUM ('lite','core','enterprise');
CREATE TYPE diagnostic_status AS ENUM ('draft','submitted','validating','processing','ai_complete','pending_review','revision_requested','approved','released','rejected');
CREATE TYPE confidence_level AS ENUM ('low','medium','high');
CREATE TYPE file_status AS ENUM ('uploaded','parsing','parsed','parse_failed','flagged');
CREATE TYPE file_type AS ENUM ('csv','xlsx','xls','pdf','txt');
CREATE TYPE job_status AS ENUM ('queued','running','complete','failed','cancelled');
CREATE TYPE opportunity_stage AS ENUM ('prospect','engaged','diagnostic_in_progress','report_delivered','follow_up','upsell_target','closed_won','closed_lost');

CREATE TABLE organisations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  website TEXT,
  vertical TEXT,
  tier service_tier NOT NULL DEFAULT 'lite',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID REFERENCES organisations(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  role user_role NOT NULL DEFAULT 'client_admin',
  password_hash TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_email ON users(email);

CREATE TABLE benchmark_config (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  category TEXT NOT NULL,
  key TEXT NOT NULL,
  label TEXT NOT NULL,
  value_low NUMERIC(10,4) NOT NULL,
  value_high NUMERIC(10,4) NOT NULL,
  value_default NUMERIC(10,4) NOT NULL,
  unit TEXT NOT NULL DEFAULT 'percent',
  vertical TEXT DEFAULT 'all',
  notes TEXT,
  updated_by UUID REFERENCES users(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(key, vertical)
);

CREATE TABLE diagnostics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  reference TEXT NOT NULL UNIQUE,
  org_id UUID NOT NULL REFERENCES organisations(id),
  submitted_by UUID NOT NULL REFERENCES users(id),
  tier service_tier NOT NULL,
  status diagnostic_status NOT NULL DEFAULT 'draft',
  company_name TEXT NOT NULL,
  website TEXT,
  vertical TEXT NOT NULL,
  monthly_volume NUMERIC(20,2),
  monthly_transactions INTEGER,
  avg_order_value NUMERIC(10,2),
  cross_border_pct NUMERIC(5,2),
  psps_used TEXT[],
  regions JSONB,
  auth_rate NUMERIC(5,2),
  decline_rate NUMERIC(5,2),
  soft_decline_pct NUMERIC(5,2),
  hard_decline_pct NUMERIC(5,2),
  top_decline_reasons TEXT[],
  chargeback_rate NUMERIC(5,2),
  refund_rate NUMERIC(5,2),
  payment_methods TEXT[],
  retry_enabled BOOLEAN,
  retry_notes TEXT,
  checkout_currencies TEXT[],
  settlement_currencies TEXT[],
  pricing_model TEXT,
  mdr NUMERIC(5,4),
  fx_fee_spread NUMERIC(5,4),
  scheme_fee_visibility TEXT,
  acquiring_setup TEXT,
  routing_setup TEXT,
  additional_context TEXT,
  parsed_data JSONB,
  ai_output JSONB,
  ai_model TEXT,
  ai_prompt_version TEXT,
  ai_tokens_used INTEGER,
  ai_run_at TIMESTAMPTZ,
  operator_notes TEXT,
  override_enabled BOOLEAN DEFAULT false,
  override_reason TEXT,
  override_low NUMERIC(20,2),
  override_mid NUMERIC(20,2),
  override_high NUMERIC(20,2),
  override_confidence confidence_level,
  override_by UUID REFERENCES users(id),
  override_at TIMESTAMPTZ,
  approved_by UUID REFERENCES users(id),
  approved_at TIMESTAMPTZ,
  released_at TIMESTAMPTZ,
  rejection_reason TEXT,
  final_output JSONB,
  benchmarks_snapshot JSONB,
  submitted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_diag_org ON diagnostics(org_id);
CREATE INDEX idx_diag_status ON diagnostics(status);
CREATE INDEX idx_diag_ref ON diagnostics(reference);

CREATE TABLE uploaded_files (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  diagnostic_id UUID NOT NULL REFERENCES diagnostics(id) ON DELETE CASCADE,
  org_id UUID NOT NULL REFERENCES organisations(id),
  file_name TEXT NOT NULL,
  file_type file_type NOT NULL,
  file_size_bytes INTEGER NOT NULL,
  storage_key TEXT NOT NULL,
  status file_status NOT NULL DEFAULT 'uploaded',
  parsed_fields JSONB,
  parse_confidence NUMERIC(3,2),
  parse_notes TEXT,
  uploaded_by UUID REFERENCES users(id),
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  parsed_at TIMESTAMPTZ
);
CREATE INDEX idx_files_diag ON uploaded_files(diagnostic_id);

CREATE TABLE client_intel (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES organisations(id) UNIQUE,
  opportunity_stage opportunity_stage DEFAULT 'engaged',
  score INTEGER CHECK (score BETWEEN 0 AND 100),
  notes TEXT,
  tags TEXT[],
  key_contacts JSONB,
  contract_notes TEXT,
  contract_renewal DATE,
  upsell_signals TEXT[],
  follow_up_date DATE,
  total_leakage_identified NUMERIC(20,2),
  diagnostics_count INTEGER DEFAULT 0,
  last_activity_at TIMESTAMPTZ,
  created_by UUID REFERENCES users(id),
  updated_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE client_intel_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES organisations(id),
  note TEXT NOT NULL,
  note_type TEXT DEFAULT 'general',
  created_by UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_intel_log_org ON client_intel_log(org_id);

CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  diagnostic_id UUID REFERENCES diagnostics(id),
  job_type TEXT NOT NULL,
  status job_status NOT NULL DEFAULT 'queued',
  payload JSONB,
  result JSONB,
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);
CREATE INDEX idx_jobs_diag ON jobs(diagnostic_id);
CREATE INDEX idx_jobs_status ON jobs(status);

CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  org_id UUID REFERENCES organisations(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  old_value JSONB,
  new_value JSONB,
  ip_address INET,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  metadata JSONB,
  read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notif_user ON notifications(user_id, read);

CREATE TABLE report_exports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  diagnostic_id UUID NOT NULL REFERENCES diagnostics(id),
  org_id UUID NOT NULL REFERENCES organisations(id),
  export_type TEXT NOT NULL,
  storage_key TEXT NOT NULL,
  generated_by UUID REFERENCES users(id),
  is_internal BOOLEAN DEFAULT false,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- BENCHMARK SEED DATA
INSERT INTO benchmark_config (category, key, label, value_low, value_high, value_default, unit, vertical) VALUES
('auth_rate','auth_rate_retail','Auth rate – Retail',90,95,88,'percent','retail'),
('auth_rate','auth_rate_saas','Auth rate – SaaS/Subscription',92,97,91,'percent','saas'),
('auth_rate','auth_rate_travel','Auth rate – Travel',85,92,85,'percent','travel'),
('auth_rate','auth_rate_marketplace','Auth rate – Marketplace',88,93,87,'percent','marketplace'),
('auth_rate','auth_rate_fintech','Auth rate – Financial Services',91,96,90,'percent','fintech'),
('auth_rate','auth_rate_luxury','Auth rate – Luxury/High-ticket',88,94,88,'percent','luxury'),
('auth_rate','auth_rate_default','Auth rate – Default',90,95,88,'percent','all'),
('leakage','cross_border_penalty','Cross-border approval penalty',2,5,3.2,'percent','all'),
('leakage','fx_leakage','FX leakage (spread)',1,3,1.8,'percent','all'),
('leakage','retry_uplift','Retry uplift opportunity',1,3,2.1,'percent','all'),
('leakage','single_psp_risk','Single PSP risk premium',0.5,2,1.0,'percent','all'),
('leakage','method_gap','Payment method gap (local missing)',0.5,2,1.2,'percent','all'),
('chargeback','cb_admin_cost','Chargeback admin cost per £1',1.5,3.0,2.2,'currency','all'),
('chargeback','cb_revenue_ratio','Chargeback revenue impact ratio',2.5,4.0,3.0,'multiplier','all');
