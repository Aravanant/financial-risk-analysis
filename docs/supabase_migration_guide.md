# RiskLens AI — Supabase PostgreSQL Production Migration Runbook

This guide documents the architecture, schema creation, data import, verification, and deployment procedures for running RiskLens AI with Supabase PostgreSQL in production while preserving SQLite for local development.

---

## 1. Architecture Overview

RiskLens AI employs a **dual-database backend architecture**:

```
                       ┌─────────────────────────────────────────┐
                       │           React 19 + Vite UI            │
                       │           (frontend/ on Vercel)         │
                       └───────────────────┬─────────────────────┘
                                           │
                                           │ HTTP / JSON
                                           │ (VITE_API_BASE_URL)
                                           ▼
                       ┌─────────────────────────────────────────┐
                       │          FastAPI REST API               │
                       │             (src/api/)                  │
                       └───────────────────┬─────────────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        │ DATABASE_URL is set?               │
                        ▼                                     ▼
               ┌─────────────────┐                   ┌─────────────────┐
               │       YES       │                   │       NO        │
               │   (Production)  │                   │(Local / Testing)│
               ▼                 ▼                   ▼                 ▼
   ┌───────────────────────┐            ┌───────────────────────┐
   │  Supabase PostgreSQL  │            │     Local SQLite      │
   │  Port 6543 (Pooler)   │            │ risklens_analytics.db │
   │  SSL (sslmode=require)│            │ Read-only URI mode    │
   └───────────────────────┘            └───────────────────────┘
```

- **Local Development & Automated Tests**: When `DATABASE_URL` is unset, the system connects directly to the local SQLite database ([`data/processed/risklens_analytics.db`](file:///home/anant-singh/Desktop/Financial%20Risk%20Analysis/data/processed/risklens_analytics.db)).
- **Production (Supabase)**: When `DATABASE_URL` is set, the API connects to PostgreSQL using `psycopg2-binary`, enforcing `sslmode=require`, per-request connection isolation, autocommit mode, and safe parameter adaptation.
- **Serverless-Safe**: Uses connection opening/closing per request (or transaction pooler) with zero open transaction leaks, optimal for Supavisor/pgBouncer in transaction mode.

---

## 2. Prerequisites & Driver Installation

Install the PostgreSQL driver alongside the core requirements:

```bash
pip install -r requirements.txt
# or explicitly:
pip install "psycopg2-binary>=2.9.9"
```

---

## 3. Supabase Connection Configuration

### 3.1 Obtaining the Connection String

In the [Supabase Dashboard](https://supabase.com/dashboard):
1. Navigate to **Project Settings** -> **Database**.
2. Under **Connection string**, select **URI**.
3. Choose the appropriate connection mode:
   - **Transaction Pooler (Port 6543)** *(Recommended for serverless & Vercel)*:
     ```
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
     ```
   - **Direct Session (Port 5432)**:
     ```
     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require
     ```

> [!IMPORTANT]
> Always set `DATABASE_URL` strictly as a backend environment variable. Never prefix with `VITE_` or expose it to the React frontend.

---

## 4. Migration & Import Runbook

All database initialization and migrations are driven explicitly via [`scripts/migrate_to_supabase.py`](file:///home/anant-singh/Desktop/Financial%20Risk%20Analysis/scripts/migrate_to_supabase.py). The FastAPI API server **never** runs DDL or destructive operations at startup.

### Step 1: Set the Environment Variable

```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require"
```

### Step 2: Create Schema, Tables, Indexes, and Views

Apply the table DDL, constraints (`chk_decision_consistency`), conformed foreign keys, performance indexes, and all 7 analytical views:

```bash
python3 scripts/migrate_to_supabase.py --schema-only
```

#### The 7 Conformed Analytical Views Created:
1. `vw_portfolio_kpis`: Core portfolio totals, approval/rejection rates, requested/sanctioned CU, quality flags.
2. `vw_channel_performance`: 4-channel breakdown (Online, Branch, Mobile App, Agent).
3. `vw_loan_purpose_analysis`: 8-category breakdown with haircut metrics.
4. `vw_underwriting_haircut`: Purpose-level aggregate haircut calculations.
5. `vw_portfolio_haircut_summary`: Portfolio aggregate haircut percentage and full exclusion arithmetic.
6. `vw_risk_tier_summary`: Distribution across source-provided Default_Risk tiers.
7. `vw_data_quality_metrics`: Audit flags, missingness ledger, and genuine zero tracking.

### Step 3: Stream Cleaned Analytical Data from SQLite to PostgreSQL

Stream the 100,000 verified clean fact records, conformed lookup dimensions, and 48,596 quarantined demo servicing records:

```bash
python3 scripts/migrate_to_supabase.py --import-data --batch-size 5000
```

> [!NOTE]
> If `fct_loan_application` already has data, `--import-data` automatically skips insertion to prevent accidental duplicate rows.

### Step 4: Verify 100.000% Analytical Reconciliation

Run automated side-by-side reconciliation between SQLite and Supabase PostgreSQL:

```bash
python3 scripts/migrate_to_supabase.py --verify
```

---

## 5. Authoritative Baseline Reconciliation Targets

The `--verify` command compares every value against the verified SQLite baseline:

| Metric / Table | Baseline Target | Validation Rule |
| :--- | :--- | :--- |
| **`fct_loan_application` rows** | `100,000` | Exact match |
| **`dim_channel` rows** | `4` | Exact match |
| **`dim_loan_purpose` rows** | `8` | Exact match |
| **`dim_residence_property_location` rows** | `75` | Exact match |
| **`demo_synthetic_repayment_snapshot` rows** | `48,596` | Exact match (quarantined) |
| **Total Applications** | `100,000` | Conservation across channels |
| **Approved Applications** | `49,171` | Exact match |
| **Rejected Applications** | `50,829` | Exact match |
| **Approval Rate** | `49.171%` | `(49171 / 100000) * 100` |
| **Rejection Rate** | `50.829%` | `(50829 / 100000) * 100` |
| **Total Requested Principal** | `14,208,864,987.26 CU` | Sum of requested loan amount |
| **Total Sanctioned Principal** | `5,429,935,281.88 CU` | Sum of approved amount |
| **Invalid Financials Count** | `104` | Negative balances sanitized |
| **Missing Sanctioned Count** | `1,206` | Null approved amounts |
| **Haircut Eligible Count** | `48,022` | Approved with positive requested & sanctioned |
| **Total Haircut Volume** | `1,366,702,750.08 CU` | Requested minus sanctioned difference |
| **Aggregate Haircut Percentage** | `20.3155%` | `(1.0 - (sanctioned / requested)) * 100` |
| **Haircut Excluded Count** | `51,978` | 50,829 rejected + 575 approved missing + 574 zero/negative |

---

## 6. Full One-Step Migration Command

To run the complete workflow in sequence:

```bash
python3 scripts/migrate_to_supabase.py
```

### Resetting the Target Database (Destructive Safeguard)

If you need to re-create the schema from scratch, explicit confirmation is required:

```bash
python3 scripts/migrate_to_supabase.py --reset --confirm-reset
```

---

## 7. Verifying Deployment & Health Check

### Health Check Endpoint

Query `/health` or `/api/v1/health`:

```bash
curl -s http://127.0.0.1:8000/health | jq
```

Expected Response:
```json
{
  "status": "healthy",
  "connected": true,
  "database_backend": "postgresql",
  "database_size_bytes": 48123904,
  "schema_version": "2.0.0",
  "record_counts": {
    "fct_count": 100000,
    "channel_count": 4,
    "purpose_count": 8,
    "location_count": 75,
    "demo_servicing_count": 48596
  },
  "error": null
}
```

### Credential Protection Guarantee
- If a connection error occurs, `sanitize_db_error` automatically redacts database passwords and user credentials:
  `postgresql://postgres:***@db.projectref.supabase.co:5432/postgres`
- FastAPI startup logs display `settings.masked_database_url` (passwords masked with `***`).
- The React frontend receives only analytical data; zero database credentials or connection strings are ever sent over HTTP.
