-- Initial schema for Risk Management & Fraud Detection system.

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(64) NOT NULL UNIQUE,
    account_id VARCHAR(64) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency CHAR(3) NOT NULL,
    merchant_id VARCHAR(64) NOT NULL,
    merchant_category VARCHAR(64),
    ip_address VARCHAR(45),
    country CHAR(2),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW()),
    risk_decision VARCHAR(16),
    CONSTRAINT ck_transactions_amount_positive CHECK (amount >= 0)
);

CREATE INDEX ix_transactions_account_id ON transactions(account_id);
CREATE INDEX ix_transactions_merchant_id ON transactions(merchant_id);
CREATE INDEX ix_transactions_created_at ON transactions(created_at);

CREATE TABLE risk_rules (
    id SERIAL PRIMARY KEY,
    code VARCHAR(64) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    definition TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW()),
    CONSTRAINT uq_risk_rules_code_version UNIQUE (code, version)
);

CREATE TABLE rule_evaluation_results (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    rule_id INTEGER NOT NULL REFERENCES risk_rules(id) ON DELETE RESTRICT,
    passed BOOLEAN NOT NULL,
    score_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
    decision VARCHAR(16),
    details TEXT,
    evaluated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW()),
    CONSTRAINT uq_rule_eval_tx_rule UNIQUE (transaction_id, rule_id)
);

CREATE TABLE fraud_alerts (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    severity VARCHAR(16) NOT NULL,
    title VARCHAR(128) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW()),
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN'
);

CREATE INDEX ix_fraud_alerts_created_at ON fraud_alerts(created_at);

CREATE TABLE cases (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES fraud_alerts(id) ON DELETE RESTRICT,
    assignee VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW()),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW()),
    resolution TEXT
);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,
    entity_id INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW()),
    actor VARCHAR(64),
    case_id INTEGER REFERENCES cases(id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_created_at ON audit_logs(created_at);



