# RiskLens AI — Technical Architecture & System Design

RiskLens AI is an end-to-end financial analytics system and credit underwriting intelligence dashboard designed for auditability, strict data integrity, and forensic transparency.

The platform processes **100,000 credit applications** through an immutable ETL pipeline into an analytical SQLite warehouse, exposes read-only analytical metrics via a FastAPI service, and renders them through a responsive React + TypeScript interface.

---

## 1. System Architecture Diagram

```mermaid
flowchart TD
    subgraph DataIngestion ["1. Data Ingestion & Integrity Layer"]
        RAW["Immutable Raw CSV<br/><code>data/raw/kaggle_original.csv</code><br/>(100,150 rows, 67 columns)<br/>SHA-256 Verified"]
        DEDUP["Deduplication Engine<br/>Full 67-Column Exact Match<br/>(150 duplicates removed)"]
        VAL["Validation & Sanitization Pipeline<br/>• Non-destructive NULL casting<br/>• Audit flag generation<br/>• 3VL SQL boolean logic"]
        RAW --> DEDUP --> VAL
    end

    subgraph StorageLayer ["2. SQLite Analytical Warehouse"]
        direction TB
        FCT["<code>fct_loan_application</code><br/>(100,000 clean rows)<br/>Application-level grain"]
        DIM1["<code>dim_channel</code> (4 channels)"]
        DIM2["<code>dim_loan_purpose</code> (8 categories)"]
        DIM3["<code>dim_residence_property_location</code> (75 locs)"]
        
        VIEWS["Analytical SQL Views<br/>• <code>vw_portfolio_kpis</code><br/>• <code>vw_channel_performance</code><br/>• <code>vw_loan_purpose_analysis</code><br/>• <code>vw_portfolio_haircut_summary</code><br/>• <code>vw_risk_tier_summary</code><br/>• <code>vw_data_quality_metrics</code>"]
        
        QUARANTINE["<code>demo_synthetic_repayment_snapshot</code><br/>(48,596 synthetic rows)<br/>⚠️ STRICTLY QUARANTINED"]
        
        FCT --- DIM1
        FCT --- DIM2
        FCT --- DIM3
        FCT --> VIEWS
    end

    subgraph ServiceLayer ["3. Analytical REST API (FastAPI)"]
        API["FastAPI High-Performance Engine<br/>• Parameterized queries (?)<br/>• Column whitelisting<br/>• Typed Pydantic schemas<br/>• Read-only SQLite connection"]
        
        EP_OVERVIEW["GET /api/v1/overview"]
        EP_CHANNELS["GET /api/v1/channels"]
        EP_PURPOSES["GET /api/v1/loan-purposes"]
        EP_HAIRCUT["GET /api/v1/haircut"]
        EP_RISK["GET /api/v1/risk-tiers"]
        EP_APPS["GET /api/v1/applications"]
        EP_QUALITY["GET /api/v1/data-quality"]
        EP_DEMO["GET /api/v1/demo/servicing-snapshot/{id}"]
        
        VIEWS --> API
        QUARANTINE -.-> EP_DEMO
        API --> EP_OVERVIEW
        API --> EP_CHANNELS
        API --> EP_PURPOSES
        API --> EP_HAIRCUT
        API --> EP_RISK
        API --> EP_APPS
        API --> EP_QUALITY
    end

    subgraph PresentationLayer ["4. Financial Analytics UI (React + TypeScript)"]
        UI_CLIENT["Typed ApiService Client<br/>• Currency Unit (CU) preservation<br/>• Explicit NULL formatting<br/>• Hash-based navigation router"]
        
        V_OVERVIEW["Executive Overview"]
        V_CHANNELS["Origination Channel Analytics"]
        V_PURPOSES["Loan Purpose Segmentation (8 categories)"]
        V_HAIRCUT["Haircut & Underwriting Reductions"]
        V_RISK["Risk Tiers & Uncalibrated Scorecards"]
        V_EXPLORER["Application Explorer (Pagination & Drawer)"]
        V_QUALITY["Data Quality Ledger & Exclusion Audit"]
        V_DEMO["Quarantined Servicing Demonstration"]
        
        UI_CLIENT --> V_OVERVIEW
        UI_CLIENT --> V_CHANNELS
        UI_CLIENT --> V_PURPOSES
        UI_CLIENT --> V_HAIRCUT
        UI_CLIENT --> V_RISK
        UI_CLIENT --> V_EXPLORER
        UI_CLIENT --> V_QUALITY
        UI_CLIENT --> V_DEMO
    end

    VAL -->|Atomic Transaction Commit| FCT
    VAL -->|Isolated Synthetic Seed| QUARANTINE
    ServiceLayer --> PresentationLayer
```

---

## 2. Component Architecture Breakdown

### 2.1 Layer 1: Ingestion & Integrity Engine
- **Immutability Guarantee:** The raw dataset (`data/raw/kaggle_original.csv`) is cryptographically fingerprinted before and after every pipeline execution (`SHA-256: 027a120ef9bb38697331dd6f58dc06a84d86ac59fddcd388e3d37c6222ee076c`). It is opened exclusively in read-only mode and is never modified.
- **Deduplication:** A full 67-column identity check identifies exactly 150 duplicate records out of 100,150 raw rows. All 150 duplicates have identical `Application_ID` values and identical data across all 67 columns with zero field collisions. 100,000 unique records are retained.
- **Sanitization Without Destruction:** Negative financial balances and impossible ages are nullified and flagged rather than silently dropped or forced positive with `ABS()`.

### 2.2 Layer 2: SQLite Warehouse Schema
- **Storage Engine:** SQLite 3 with WAL (Write-Ahead Logging) and enforced foreign-key constraints (`PRAGMA foreign_keys = ON`).
- **Star-Schema Dimensional Model:**
  - `fct_loan_application`: Central fact table containing 100,000 applications.
  - `dim_channel`: 4 conformed channels (`Online`, `Branch`, `Mobile App`, `Agent`).
  - `dim_loan_purpose`: 8 verified loan-purpose categories (`Business`, `Car`, `Debt Consolidation`, `Education`, `Home`, `Medical`, `Personal`, `Vehicle`).
  - `dim_residence_property_location`: 75 distinct geographic combinations.
- **Analytical Views:** Seven views encapsulate aggregations, eliminating join fan-out and providing stable query surfaces.

### 2.3 Layer 3: FastAPI Backend Service
- **Read-Only Access:** The database connection is opened in read-only URI mode (`file:... ?mode=ro`) to eliminate write risk.
- **Injection Defense:** All parameter filters and pagination bounds use parameterized SQLite placeholders (`?`). Sort fields are strictly matched against a static column whitelist.
- **Type Contracts:** Pydantic v2 schemas serialize responses with exact field types, preserving `null` values and enforcing `CU` currency labeling.

### 2.4 Layer 4: React + TypeScript Frontend
- **Framework:** React 18, TypeScript, and Vite, styled with custom Vanilla CSS tailored for financial intelligence.
- **Deep-Linkable Navigation:** Hash routing (`#overview`, `#purposes`, `#haircut`, `#quality`, etc.) allows direct URL linking and automated headless capture without external routing dependencies.
- **Data Fidelity:** Components consume live API responses directly. No mock metrics are presented as real portfolio data.

---

## 3. The Underwriting vs. Servicing Separation Boundary

A key design requirement in institutional credit systems is the strict separation between pre-origination underwriting data and post-origination servicing records:

| Dimension | Primary Underwriting Warehouse | Simulated Servicing Demonstration |
| :--- | :--- | :--- |
| **Database Table** | `fct_loan_application` | `demo_synthetic_repayment_snapshot` |
| **Row Count** | 100,000 records | 48,596 records |
| **Data Nature** | Cleaned applicant origination records | Synthetic downstream repayment simulation |
| **API Namespace** | `/api/v1/overview`, `/api/v1/applications`, etc. | `/api/v1/demo/servicing-snapshot/{id}` |
| **UI Placement** | Primary navigation tabs | Dedicated amber tab labeled "DEMO" |
| **Audit Status** | Production underwriting analytics | Demonstration data notice prominently displayed |

Post-origination servicing records are **strictly quarantined** to prevent them from leaking into origination models, haircut calculations, or executive KPI cards.
