Risk Management & Fraud Detection System
=======================================

This project is a production-grade, rule-based Risk Management and Fraud Detection backend for a bank/fintech, with an internal analyst dashboard. It is designed for auditability, deterministic behavior, and clear separation between ingestion, risk evaluation, alerting, case management, and immutable audit logging.

Key characteristics:

- Backend: FastAPI (Python 3.x)
- Database: PostgreSQL (normalized, strongly constrained, auditable)
- Testing: pytest (TDD-focused, API- and domain-level)
- UI: Internal analyst dashboard using FastAPI + Jinja templates
- 3D Visual: Lightweight CSS 3D rotating credit card (decorative only, optional)

---

Architecture Overview
---------------------

**Core services:**

- **Transaction Ingestion Service**: Idempotent API to ingest financial transactions based on `external_id`. Persists normalized transaction records and triggers risk evaluation.
- **Risk Rules Engine**: Evaluates configurable, versioned rules stored in the `risk_rules` table. Currently supports:
  - **Amount thresholds** via `amount_gt:<value>`
  - **Velocity checks** via `velocity_count:<n>:<window_seconds>`
  - Easily extensible for geo/account mismatch, merchant risk category, etc.
- **Fraud Alert Service**: Aggregates rule outcomes into a single decision (ALLOW / REVIEW / BLOCK) and creates `fraud_alerts` with mapped severity.
- **Case Management Service**: Manages investigation `cases` for alerts (create, assign, update, close).
- **Audit & Compliance Logging**: Immutable `audit_logs` table records key events like case creation/updates with structured JSON payloads.
- **Internal Analyst UI**: Read-only dashboard for analysts to inspect recent transactions and a decorative 3D credit card visual.

**Data flow (lifecycle example):**

1. **Transaction ingestion**
   - `POST /api/v1/transactions` with transaction payload.
   - If `external_id` already exists, returns existing record (HTTP 200) to guarantee idempotency.
   - Otherwise creates a new `transactions` row.
2. **Risk evaluation**
   - Active rules from `risk_rules` are evaluated by the Rules Engine.
   - Outcomes are persisted to `rule_evaluation_results`.
   - A final decision is derived: `ALLOW`, `REVIEW`, or `BLOCK`.
3. **Alert creation**
   - For REVIEW/BLOCK decisions, one or more `fraud_alerts` rows are created with mapped severity.
4. **Case creation**
   - `POST /api/v1/cases` converts a `fraud_alert` into an investigation `case`, optionally assigned to an analyst.
5. **Case resolution & audit**
   - `PATCH /api/v1/cases/{id}` updates status and resolution.
   - Each create/update emits an immutable `audit_logs` entry with JSON payload and optional `actor`.
6. **Analyst UI**
   - `/dashboard` renders recent transactions using API data only (no direct DB access) and shows the rotating 3D credit card.

---

Database Schema
---------------

See `migrations/001_init.sql` for the full schema. Highlights:

- **`transactions`**
  - Strong constraints: PK on `id`, unique `external_id`, `amount` non-negative check.
  - Indexed on `account_id`, `merchant_id`, `created_at` for velocity and reporting queries.
  - `risk_decision` stores the aggregated decision from risk evaluation.
- **`risk_rules`**
  - Versioned via `(code, version)` unique constraint.
  - `definition` is a compact configuration string interpreted by the Rules Engine.
  - `active` flag controls whether the rule participates in evaluation.
- **`rule_evaluation_results`**
  - One row per (transaction, rule).
  - Stores `passed`, `score_delta`, rule-level `decision`, and textual `details`.
- **`fraud_alerts`**
  - Linked to `transactions` (CASCADE on delete).
  - Severity models operational urgency (LOW/MEDIUM/HIGH/CRITICAL).
- **`cases`**
  - Linked to `fraud_alerts` (RESTRICT on delete).
  - Tracks `assignee`, `status`, `resolution`, and timestamps.
- **`audit_logs`**
  - Immutable append-only style (no hard deletes).
  - Stores `entity_type`, `entity_id`, `event_type`, and JSON payload as text.
  - Indexed on `created_at` for time-based lookups.

---

API Contracts (v1)
------------------

Base path: `/api/v1`

- **Health**
  - `GET /health` → `{ "status": "ok" }`

- **Transactions**
  - `POST /api/v1/transactions`
    - In: transaction payload (`external_id`, `account_id`, `amount`, `currency`, `merchant_id`, optional fields).
    - Out: `TransactionWithRiskResponse`
      - `transaction`: normalized transaction object.
      - `decision`: `ALLOW` | `REVIEW` | `BLOCK`.
      - `alerts`: list of related alerts (may be empty for ALLOW).
      - `rules_fired`: list of rule outcomes including `code`, `version`, and any rule-level `decision`.
    - Behavior:
      - `201 Created` on first ingestion.
      - `200 OK` with same transaction on duplicate `external_id` (idempotency).
  - `GET /api/v1/transactions?limit=&offset=`
    - Pagination for analyst tools and back-office processes.
    - Out: `{ "total": int, "items": [TransactionOut, ...] }`

- **Cases**
  - `POST /api/v1/cases`
    - In: `{ "alert_id": int, "assignee": "analyst-id" | null }`
    - Out: `CaseOut` (status initially `OPEN`).
  - `PATCH /api/v1/cases/{case_id}`
    - In: any subset of `{ "assignee", "status", "resolution" }`.
    - Out: updated `CaseOut`.
    - Side-effect: appends `CASE_UPDATED` entry in `audit_logs`.

- **Audit**
  - `GET /api/v1/audit?entity_type=Case&entity_id={id}`
    - Out: list of audit log entries for the entity.

The OpenAPI schema is exposed at `/api/openapi.json` and browsable at `/api/docs`.

---

Internal Analyst UI
-------------------

- Entry point: `GET /dashboard`
  - Server-side rendered via Jinja template `templates/dashboard.html`.
  - Uses `httpx.AsyncClient` with the FastAPI `app` to fetch data from `/api/v1/transactions`.
  - Displays:
    - Total transaction count.
    - Table of recent transactions (with decision and timestamp).
    - **CSS 3D rotating credit card** visual (purely decorative).

- **3D credit card visual**
  - Implemented in `static/css/dashboard.css` using CSS 3D transforms (`transform-style: preserve-3d`, `@keyframes rotateCard`).
  - Rotates around the Y-axis in a continuous loop.
  - Marked explicitly in the UI as non-functional/decorative.
  - Can be disabled by omitting `show_3d_card` from the template context or overriding CSS.

---

Running & Testing
-----------------

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Apply database migrations**

   - Create a PostgreSQL database (e.g. `fraud_db`).
   - Run the SQL file:

   ```bash
   psql -d fraud_db -f migrations/001_init.sql
   ```

3. **Configure DB URL**

   - Update `app/db.py:get_database_url()` to read from your environment (e.g. `DATABASE_URL`) and point to your PostgreSQL instance.

4. **Run the API & UI**

   ```bash
   uvicorn app.main:app --reload
   ```

   - API docs: `http://localhost:8000/api/docs`
   - Dashboard: `http://localhost:8000/dashboard`

5. **Run tests (TDD)**

   ```bash
   pytest
   ```

   Tests use an in-memory SQLite database and do not require PostgreSQL.

---

Extensibility Notes
-------------------

- New rules can be added by:
  - Inserting new rows into `risk_rules` with higher `version`.
  - Extending `app/services/rules_engine.py` to interpret new `definition` patterns (e.g. geo/account mismatch, merchant category risk).
- The architecture is intentionally modular:
  - API layer (FastAPI routers under `app/api_v1/`).
  - Domain services (`app/services/`) for rules, cases, audit.
  - Persistence (`app/models.py` and `migrations/`).
  - UI (`app/ui.py`, `templates/`, `static/`).

All changes that affect risk decisions or cases should be observable in the audit log, supporting regulatory and internal audit requirements.



