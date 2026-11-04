# ARCHITECTURE AUDIT: EXISTING IPO RADAR CODEBASE & SYSTEM UPGRADE MATRIX

**Document Version:** 1.0  
**Audit Date:** 2026-11-04  
**Project:** IPO Radar Upgrade to Evidence-Based Indian IPO Research & Scoring Intelligence  
**Auditor:** Principal Software & AI Systems Architect  

---

## 1. EXECUTIVE SUMMARY

The existing **`ipo-radar-main`** repository is a mature, specialized, and mathematically disciplined IPO tracking and RHP analysis system. Rather than being a static mock or generic dashboard, it already features:
1. An automated **PDF prospectus analysis pipeline** that processes digital Red Herring Prospectuses (RHPs) and extracts sections, restated financial statements, valuation metrics, risk factors, and promoter details.
2. A deterministic **10-category scoring engine** that computes an explainable fundamental quality score (0–100) based strictly on prospectus evidence.
3. An **automation suite** syncing with Chittorgarh, SEBI filings, InvestorGain GMPs, Nifty 50 benchmarks, and Dhan market data, managing an append-only historical corpus of over **1,003 analyzed IPO reports** and a 20-year expanded dataset.
4. A **Next.js 16 / React 19** frontend and a **FastAPI** backend supporting both SQLite (zero-config) and PostgreSQL (production).
5. A tested suite of pipeline verification unit tests (`backend/tests/test_pipeline.py`) running with 29/29 tests passing.

### The Core Gap & Transformation Objective
The existing system is primarily **single-document centric** (it analyzes one uploaded or downloaded RHP PDF) and utilizes regex/heuristic section-parsing and single-pass table extraction. 
The upgrade transforms IPO Radar into an **Evidence-Based Multi-Source Research Intelligence Platform**:
- Automated **company legal identity discovery** (distinguishing subsidiaries, parent entities, CINs, BSE/NSE codes).
- Multi-document collection (SEBI DRHP/RHP, NSE/BSE filings, MCA public master data, Credit Rating agency rationales from CRISIL/ICRA/CARE, and verified investor presentations).
- Multi-modal retrieval combining **SQL structured financial retrieval**, **BM25 keyword search**, and **vector semantic search** (FAISS/Chroma for lightweight/Termux mode, pgvector for full mode).
- A 26+ point **Research Checklist Engine** where every check requires verifiable evidence (exact document hash, page, reporting period, unit normalization, standalone vs consolidated distinction) before marking status `YES`, `NO`, `PARTIAL`, `PENDING`, `NOT AVAILABLE`, `CONFLICT`, or `NOT APPLICABLE`.
- Separation between **Company Quality Score** and **IPO Valuation Score**, completely rule-based and version-controlled with zero arbitrary hallucinated marks.
- Support for dual execution modes: **Mode A: Lightweight Local Mode** (Python + SQLite + Streamlit + FAISS, optimized for Windows and Android Termux) and **Mode B: Full Research Server Mode** (PostgreSQL/pgvector + FastAPI + Next.js).

---

## 2. AUDIT OF EXISTING MODULES & COMPONENTS

### 2.1 Backend Core (`backend/app/`)

| File | Size / LOC | Current Functionality | Reuse / Upgrade Strategy |
| :--- | :--- | :--- | :--- |
| `main.py` | 32 LOC | FastAPI entrypoint, CORS configuration, SQLite/PostgreSQL `init_db()` on startup, router registration. | **Reuse & Extend:** Retain existing `/api` endpoints; mount new modular routers for `/companies`, `/research`, `/checklist`, `/financials`, `/scoring`, `/evidence`. |
| `config.py` | 48 LOC | Configuration for database URL, upload directories, Anthropic API/CLI options, CORS origins, disclaimers. | **Reuse & Extend:** Add settings for Termux mode, embeddings provider, vector DB paths, scraping rate limits, source credentials. |
| `db.py` | 39 LOC | SQLAlchemy engine, session maker (`SessionLocal`), base class, schema inspection and lightweight column migrations. | **Reuse & Extend:** Keep SQLAlchemy Base and session factory. Create migration scripts and abstract storage adapters for SQLite/PostgreSQL. |
| `models.py` | 163 LOC | SQLAlchemy models: `Document`, `Analysis`, `Section`, `Financial`, `IssueDetails`, `Score`, `RiskFinding`, `Report`, `MarketSignal`. | **Preserve & Extend:** Maintain full backward compatibility with existing analysis tables. Introduce new normalized entity models: `Company`, `CompanyIdentifier`, `ResearchPlan`, `ChecklistTemplate`, `ChecklistItem`, `ChecklistExecution`, `EvidenceRecord`, `SourceCitation`. |
| `api/routes.py` | 219 LOC | Endpoints for `/health`, `/documents` (upload), `/analyses`, `/analyses/{id}`, `/report`, `/market-signals`, `/qa`, `/listing-forecast`, `/similar`. | **Preserve & Wrap:** Retain all existing analysis endpoints so the current frontend and automation never break. Add new versioned API routers. |

### 2.2 Prospectus Extraction Pipeline (`backend/app/pipeline/`)

| File | Size | Capabilities | Upgrade Pathway |
| :--- | :--- | :--- | :--- |
| `pdf_processor.py` | 1.6 KB | Uses PyMuPDF (`fitz`) to load pages, compute text readability ratio, and extract embedded Table of Contents (TOC). | **Reuse & Upgrade:** Add page hash caching, OCR fallbacks for scanned annexures, and layout-aware chunking. |
| `section_extractor.py` | 10 KB | Regex and TOC scanner identifying 12 canonical RHP chapters (Risk Factors, Objects, Basis of Offer Price, Financial Statements, Litigation, Promoter Details, MD&A, etc.). | **Reuse:** Highly effective domain heuristics. Retain and expose as part of `document_engine/classifier.py`. |
| `financial_extractor.py` | 30 KB | Multi-year table parser extracting restated P&L, Balance Sheet, Cash Flow statements; handles lakh-to-crore conversion, fiscal year sorting, source page tracking. | **Reuse & Extend:** Integrate with the new `financial_engine/extractor.py` and `normalizer.py`. Add standalone vs consolidated disambiguation and GAAP/Ind-AS schema validation. |
| `entity_extractor.py` | 27 KB | Extracts issuer name, price band, issue size (fresh vs OFS), peer comparison tables, objects of offer, litigation summaries, auditor remarks, pledging disclosures. | **Reuse:** Domain regexes for Indian IPO filings are exceptionally thorough. Connect directly to research checklist evidence gatherers. |
| `forensic.py` | 5.2 KB | Checks financial statement integrity: CFO vs PAT drift, revenue vs receivables divergence, sudden pre-IPO margin expansion, auditor changes. | **Reuse:** Integrate directly into the Research Checklist Engine under Category C (Cash Flow Quality) and Category J (Auditor Qualifications). |
| `risk_analyzer.py` | 10 KB | Categorizes risk factors (customer concentration, regulatory litigations, debt covenants, currency risks), computes risk penalty scores. | **Reuse:** Wire directly into Category K (Litigation) and Category L (Regulatory Risks) checklist executors. |
| `promoter_analyzer.py` | 2.9 KB | Analyzes promoter experience claims, board composition, promoter lock-in pledging, group company conflicts. | **Reuse:** Power Category F (Promoter Background) and Category H (Corporate Governance). |
| `valuation.py` | 6.5 KB | Computes CAGR, margins, ROE, ROCE, P/E vs peer median, price-to-book ratios, and produces valuation calls. | **Reuse & Extend:** Split into pure financial ratio calculations and the new standalone IPO Valuation Scoring Engine. |
| `scoring.py` | 20 KB | Implements a 10-category deterministic scoring algorithm with evidence tracking, confidence evaluation, and penalty capping. | **Reuse & Adapt:** Keep as the legacy scoring engine; create new versioned scoring framework `scoring_engine/company_score.py` matching the user's weighted architecture. |
| `llm_layer.py` | 10 KB | Optional narrative generator and Q&A engine supporting Anthropic API and headless Claude CLI; strictly constrained to extracted RHP evidence. | **Reuse & Generalize:** Abstract LLM interface to support local models, remote APIs, and offline rule-based fallbacks. |
| `listing_predictor.py` | 22 KB | Gradient boosted tree / heuristic predictor forecasting listing day premium and medium-term post-listing trajectories. | **Preserve:** Keep intact for market outcome modeling. |
| `report_builder.py` | 11 KB | Consolidates all pipeline outputs into a structured JSON report document. | **Reuse & Extend:** Keep backward compatible output for existing frontend while exporting comprehensive Evidence Dossiers. |
| `orchestrator.py` | 11 KB | Sequential stage runner coordinating the 10 stages with background status updates and graceful degradation on sub-stage failure. | **Reuse & Extend:** Provide unified orchestration for both single-PDF pipeline and full multi-source company research. |

### 2.3 Automation Scripts (`automation/`)

| Script | Purpose & Data Flow | Status & Upgrade Plan |
| :--- | :--- | :--- |
| `update.py` (50 KB) | Master daily runner: Chittorgarh data sync, SEBI AJAX filings scrape, Yahoo finance historical prices, RHP analysis, `docs/data/ipos.json` build. | **Preserve & Modernize:** Keep working as the daily sync script. Wrap scraping routines into reusable connectors (`collectors/sebi.py`, `collectors/chittorgarh.py`). |
| `cg_record.py` (10 KB) | Extracts Next.js flight data (`self.__next_f.push`) from Chittorgarh detail pages, capturing pre/post shareholding, face value, KPIs, and restated financials. | **Preserve & Reuse:** Highly efficient scraping logic. Move parsing utilities to backend collector services while preserving the CLI script. |
| `backfill_rhp.py` (12 KB) | Walks SEBI's historical filings archive via AJAX endpoint (`getnewslistinfo.jsp`) back to 2007 to download and analyze past prospectuses. | **Preserve & Reuse:** Critical connector for official SEBI documents. Integrate into `collectors/sebi.py`. |
| `finalsheet.py` (27 KB) | Compiles `ipodata/finalipodata.xlsx` (47 columns) matching the canonical financial spreadsheet format. | **Preserve:** Retain intact. Ensure all new financial extractions feed into this workbook format seamlessly. |
| `build_dataset.py` (11 KB) | Rebuilds `ipodata/finalipodata_expanded_20yr.xlsx` across 20 years of Indian IPO history. | **Preserve:** Keep intact. |
| `gmp_history.py` (4.3 KB) | Scrapes InvestorGain and IPOWatch historical grey-market premiums into `data/ig_gmp.csv`. | **Preserve:** Maintain for historical market sentiment records. |
| `track_rule.py` (7.8 KB) | Forward-tests the frozen quantitative hypothesis "institutions keen, retail cold" into `data/rule_ledger.json`. | **Preserve:** Maintain forward research audit integrity. |
| `retrain.py` (38 KB) | Retrains LightGBM/GBM models with forward-chaining time-ordered cross validation. | **Preserve:** Keep intact. |
| `nifty.py` & `dhan.py` | Benchmark index tracking (Nifty 50) and Dhan broker LTP data. | **Preserve:** Keep intact. |

### 2.4 Existing Datasets (`data/` & `ipodata/`)

- `data/cg_records.json` (2.28 MB): Detailed records for hundreds of Indian IPOs with share capital and financial restatements.
- `data/cg_issue.csv`, `cg_listing.csv`, `cg_subs.csv`, `cg_details.csv`: Canonical Chittorgarh tables covering issue timelines, listing performance, and subscription statistics.
- `docs/data/reports/*.json`: Over **1,003 analyzed RHP reports** with rule breakdown and page citations.
- `ipodata/finalipodata.xlsx` & `finalipodata_expanded_20yr.xlsx`: Complete 20-year structured datasets.
- **Rule:** Under no circumstances will these datasets be deleted or overwritten with fake sample data.

### 2.5 Existing Frontend (`frontend/`)

- Built with **Next.js 16 (App Router)**, React 19, Tailwind CSS, Lucide icons, and Recharts.
- Pages:
  - `/`: Main dashboard with upload zone and recent analyses.
  - `/analyses`: Historical and ongoing analysis runs.
  - `/analysis/[id]`: Comprehensive report viewer with 7 distinct analytical tabs (Overview, Financials, Valuation, Promoters, Risks, Score, Q&A).
- Component architecture: Modular tabs in `components/report/`.
- **Upgrade Strategy:** Keep the Next.js frontend intact and add new pages/components for the multi-source Research Plan, Checklist Progress, and Evidence Explorer. In parallel, deliver the **Streamlit dashboard** for Mode A (lightweight Termux and portable zero-npm deployments).

---

## 3. IDENTIFIED COMPATIBILITY RISKS & MITIGATION

1. **Windows Application Control (WDAC / AppLocker) in `.venv`:**
   - *Risk:* Binary wheels (like `pandas._libs.indexing` or `fitz`) placed in local directory virtual environments can trigger `ImportError: DLL load failed: An Application Control policy has blocked this file` if the folder lacks execution trust.
   - *Mitigation:* System Python (`C:\Users\SUSHANT KUMAR\AppData\Local\Programs\Python\Python313`) is verified and runs all C-extensions cleanly. The platform will support execution via both system Python launcher (`py -3.13`) and virtual environments.
2. **PyMuPDF Version Deprecation:**
   - *Risk:* `import fitz` prints a deprecation warning in PyMuPDF 2.x recommending `import pymupdf`.
   - *Mitigation:* Ensure all new document engine code uses `import pymupdf as fitz` or `import pymupdf` directly to eliminate warnings.
3. **Database Schema Backward Compatibility:**
   - *Risk:* Modifying existing tables (`analyses`, `documents`, `financials`, `reports`) could break existing stored reports or Next.js API calls.
   - *Mitigation:* Leave existing tables intact. Create new relationally linked tables (`companies`, `research_plans`, `checklist_executions`, `evidence_records`) that reference or extend existing records via foreign keys.
4. **Scraping Rate Limits & Fragility:**
   - *Risk:* Official sites (SEBI, BSE, NSE) may intermittently block high-frequency scraping or alter DOM structures.
   - *Mitigation:* Implement caching (`data/cache/`), exponential backoff retries, request header rotation, and a **manual PDF/document upload fallback** for every connector.

---

## 4. ARCHITECTURAL UPGRADE ROADMAP

The target architecture seamlessly unifies the existing RHP analysis engine with an **Evidence-Based Company Research & Checklist Verification System**:

```
                       ┌───────────────────────────────────────────────┐
                       │          IPO Radar Research Platform          │
                       └───────────────────────┬───────────────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
    Mode A: Lightweight Local (Termux/PC)                           Mode B: Full Research Server
    (FastAPI + Streamlit + SQLite + FAISS)                          (FastAPI + Next.js + Postgres/pgvector)
               │                                                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 ▼                           ▼
                     Existing Pipeline & Data      New Research Architecture
                     - 1,003+ Historical Reports   - Company Legal Identity Discovery
                     - 20-Year IPODATA Workbook    - Multi-Source Connectors (SEBI, Exchanges, MCA)
                     - RHP Extraction Engine       - Hybrid Retrieval (SQL + BM25 + Vector)
                     - Chittorgarh & GMP Sync      - Research Checklist Engine (26 Checks)
                     - Predictor & Rule Ledger     - Evidence Verification & Scoring Engine
```

This audit confirms that the existing repository provides an outstanding foundation of domain logic and historical data. We will proceed strictly by reusing and extending these assets without breaking any existing functionality.

