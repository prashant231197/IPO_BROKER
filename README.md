# IPO Radar — Evidence-Based AI IPO Intelligence

An institutional-grade, evidence-backed Indian IPO Research and Intelligence Platform that investigates prospective and listed companies using real public filings (SEBI RHP/DRHP, Chittorgarh records, BSE/NSE disclosures).

Every conclusion, ratio, and score is strictly anchored to traceable document citations (source title, page number, reported unit, and period).

> ⚠️ **Strict Evidence Rule:** No evidence, no answer. The system never guesses or fabricates financial figures. When public disclosures are missing or unverified, items are explicitly marked `NOT AVAILABLE` or `PENDING VERIFICATION`, and final quality scores remain gated.

---

## Key Features

1. **Deterministic 26-Point Master Research Checklist:**
   - Evaluates Profitability (6 checks), Balance Sheet & Solvency (5 checks), Governance & Promoters (5 checks), Valuation & Structure (5 checks), Business Quality (3 checks), and Legal/Regulatory Risks (2 checks).
   - Traceable page-level citations for every single verified data point.
2. **Dual Rule-Based Scoring Engine:**
   - **Company Quality Score (100 pts):** Weighted multi-category score (Financial Performance 25%, Business Quality 20%, Balance Sheet 15%, Governance 15%, Legal 10%, Industry 10%, Cash Flow 5%). Gated behind an evidence coverage threshold (minimum 35% verified data required for provisional score).
   - **IPO Valuation Score (100 pts):** Evaluates P/E relative to peer median, fresh issue vs OFS ratio, objects of the issue, and equity dilution.
3. **Multi-Tier Source Registry:**
   - Tier 1: SEBI DRHP/RHP filings, MCA ROC company filings.
   - Tier 2: BSE/NSE disclosures, Chittorgarh archival records (1,000+ historical IPOs included out of the box).
   - Tier 3: Industry reports & peer benchmarking.
4. **Pure-Python Lightweight Retrieval Engine:**
   - Built with pure-Python BM25 and pure-NumPy vector cosine similarity fallbacks with zero C++ compilation requirements.
   - Guaranteed full portability across **Android Termux**, **Windows**, **Linux**, and **Docker**.
5. **Interactive Streamlit Research Dashboard & Headless CLI:**
   - Streamlit dashboard (`frontend/streamlit_app.py`) with 7 modules: Overview, Company Research, 26-Point Checklist, Dual Scoring, Evidence Explorer, AI Assistant, and Source Registry.
   - Headless CLI runner (`automation/research_runner.py`) for automated terminal investigations and batch pipelines.

---

## Quickstart — Android Termux

Run the complete research platform directly on your Android phone inside Termux without heavy containers or cloud dependencies:

```bash
# 1. Update packages and install python
pkg update -y && pkg install -y python git libxml2 libxslt

# 2. Run the automated Termux setup script
bash scripts/setup_termux.sh

# 3. Start the Backend API & Streamlit Dashboard
bash scripts/start_termux.sh
```

- Open your phone's browser at **`http://localhost:8501`** for the Streamlit Research UI.
- Backend API runs at **`http://localhost:8000`** (Swagger docs at `/docs`).

For detailed step-by-step Termux instructions, see [`docs/TERMUX_GUIDE.md`](docs/TERMUX_GUIDE.md).

---

## Quickstart — Windows (PowerShell)

### Option A: One-Click PowerShell Script
```powershell
# Setup environment and install dependencies
.\scripts\setup_windows.ps1

# Launch Backend and Streamlit Dashboard
.\scripts\start_windows.ps1
```

### Option B: Headless Terminal Research Runner
Investigate any company directly from your terminal:

```bash
# List all tracked companies
py -3.13 automation/research_runner.py --list

# Run 26-Point Checklist & Scoring on any company
py -3.13 automation/research_runner.py --company "Alpine Texworld Ltd." --execute
py -3.13 automation/research_runner.py --company "Reliance Jio" --execute
```

---

## Architecture & Pipeline

```
SEBI / Chittorgarh / Manual PDF Upload
  │
  ├─► Entity Resolver (CIN normalization, ROC status, MCA verification)
  │
  ├─► Financial Normalizer (Lakh/Crore conversions, restated statement parser)
  │
  ├─► Pure-Python Hybrid Retrieval (BM25 keyword + NumPy vector semantic search)
  │
  ├─► 26-Point Master Research Checklist Engine
  │     └─► Evidence Validator (Source tiers, page numbers, units, conflict checks)
  │
  └─► Dual Rule-Based Scoring Engine
        ├─► Company Quality Score (0-100, gated by evidence coverage)
        └─► IPO Valuation Score (0-100, P/E vs peers, OFS split, dilution)
```

---

## REST API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/companies` | List registered companies with pagination & search |
| `POST` | `/api/companies` | Register a new company with CIN validation |
| `POST` | `/api/documents/discover` | Auto-discover filings from SEBI and Chittorgarh |
| `POST` | `/api/documents/upload` | Upload local PDF prospectus / audited statement |
| `POST` | `/api/research/start` | Initialize 26-Point Research Plan for a company |
| `POST` | `/api/research/checklist/execute` | Execute checklist verification against evidence |
| `GET` | `/api/research/checklist/{id}` | Inspect individual checklist item with citations |
| `POST` | `/api/scores/calculate` | Calculate Company Quality & Valuation Scores |
| `GET` | `/api/scores/{company_id}` | Retrieve latest verified score record & warnings |

---

## Running Tests

All unit and integration tests (legacy pipeline + new Phase 1–8 research engines) can be verified with:

```bash
py -3.13 -m pytest tests backend/tests
```

---

# Original RHP Analyst & Historical Dataset

## IPO Radar (self-updating GitHub Pages dashboard)

**Live dashboard: <https://rohanbeingsocial.github.io/ipo-radar/>**

The repo runs itself: a daily GitHub Actions job (`.github/workflows/ipo-radar.yml` →
`automation/update.py`) pulls the latest mainboard IPOs from Chittorgarh's archives
(issue structure, QIB/bNII/sNII/Retail subscription, listing-day prices), finds each new
IPO's RHP in SEBI's Red-Herring filings archive, runs the full deterministic analysis
pipeline on it (no server, no keys — `backend/tools/analyze_standalone.py`), refreshes
real price outcomes from Yahoo, recomputes entry/exit + 6m/12m/24m horizon forecasts,
rebuilds `ipodata/finalipodata_expanded_20yr.xlsx`, and commits the results.
The analysis columns are sourced automatically too: **ROE / ROCE / D-E / PAT + EBITDA
margin / post-issue P/E** are computed by the analyzer from the RHP's restated financials,
**Sector** comes from Yahoo's profile for the listed symbol, the **% QIB / % Retail /
% anchor** reserved split is read from Chittorgarh's issue-structure table (anchor = 60% of
the QIB portion), **LTP Gain** is the current price vs offer, and **GMP** is captured from
the live grey-market feed while an IPO is open (`data/cg_details.csv`, `data/cg_gmp.csv`).
Grey-market premium is third-party and only exists pre-listing, so it is captured going
forward rather than reconstructed for old issues.
**The dashboard** (GitHub Pages, `docs/`) is the analyzer UI as a static site: every
tracked IPO gets a full report page — Overview, Forecast (6m/12m/24m horizons, entry/exit,
subscription, actuals), Valuation, Risks and the rule-by-rule Score trace — rendered from
precomputed report JSONs (`docs/data/reports/`). The upload drop-zone is live too: run the
backend locally (or point the page at any hosted engine via "how do I analyze my own RHP?")
and the same page uploads, polls progress and renders the full live report with market-signal
forecasts and document Q&A. Sources being down never breaks the site; the last committed
data keeps serving.

A second workflow (`.github/workflows/kaggle-publish.yml` → `automation/kaggle_publish.py`)
publishes the refreshed dataset (the expanded Excel + the four canonical CSVs) to
**[Kaggle](https://www.kaggle.com/datasets/rohandeogaonkar/india-mainboard-ipos-20yr)**
as a new dataset version **every Monday**. It needs a `KAGGLE_API_TOKEN`
repo secret (access token from <https://www.kaggle.com/settings> → API); until it is
set the workflow skips harmlessly.

## How it works

```
PDF upload
  └─ Document processing        PyMuPDF text + bookmarks, pdfplumber tables, optional OCR
  └─ Section extraction         27 chapters per SEBI ICDR Schedule VI (bookmarks → printed TOC → heading scan)
  └─ Financial extraction       restated P&L / BS / CF, Indian number formats, lakh→crore normalization
  └─ Entity extraction          price band, fresh/OFS split, objects, peers, litigation, RPT, pledging
  └─ Risk analysis              13 risk classes, quantified severities, boilerplate detection
  └─ Valuation                  ratios, CAGRs, issue P/E vs peer median → valuation call
  └─ Forensic screens           Beneish-style flags, Piotroski-style strength checks (high flag caps score at 55)
  └─ Promoter & governance      names, experience, holdings, board signals, pledging
  └─ Scoring                    ~25 rules across 10 categories; missing data is excluded, never zeroed
  └─ Report                     verdict, bull/bear/neutral cases, red/green flags, questions to ask
```

Scoring is fully deterministic. The Anthropic API is **optional** and only rewrites narrative
text and answers document Q&A — always constrained to extracted evidence with page citations.

`GET /api/analyses/{id}/listing-forecast[?llm=1]` adds a pre-listing **hype-cycle forecast**
(listing-open premium, break-below-offer odds and window, bottom window anchored on SEBI
lock-in expiries, recovery windows) from RHP-only features — no GMP or subscription data.
`?llm=1` adds the AI engine's view from the same **anonymized** features. Heuristic research
output with wide error bars; model training lives in `automation/retrain.py`.

**Horizon forecasts (the "drop in an RHP, add day-1 signals" workflow):** upload the RHP,
then `POST /api/analyses/{id}/market-signals` with whatever is knowable in the first 2–3
days of listing — `gmp`, `sub_qib`, `sub_bnii`, `sub_snii`, `sub_rii`, `day1_gain` (listing-day
close vs offer, %). The forecast endpoint then returns `ml_horizons`: predicted return vs
offer at **6m / 12m / 24m** with P(above offer), an **entry** read (expected bottom session
and depth) and an **exit** read (best horizon, expected peak). Model: gradient-boosted trees
trained on ~20 years of NSE/BSE mainboard IPOs (Chittorgarh archives + Yahoo price paths +
this app's RHP features); retrain with `tools/train_horizon_model.py` after refreshing the
expanded dataset (`ipodata/finalipodata_expanded_20yr.xlsx`). Long-horizon training data
skews to survivors; direction and timing bands are the reliable read, not the point estimate.

## Quickstart (local)

Backend (Python 3.11+):

```bash
cd backend
pip install -r requirements.txt
python -m app.seed_demo        # builds a synthetic sample RHP and analyzes it
python -m uvicorn app.main:app --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

The landing page links to the sample report (fictional company, synthetic prospectus).
Run tests with `cd backend && python -m pytest tests/`.

## Quickstart (Docker)

```bash
docker compose up --build      # frontend :3000, backend :8000, PostgreSQL
```

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite `backend/rhp.db` | Set `postgresql+psycopg2://user:pass@host/db` for PostgreSQL |
| `ANTHROPIC_API_KEY` | _(empty)_ | Enables AI narrative + Q&A; everything else works without it |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Model for the AI layer (API provider) |
| `LLM_PROVIDER` | `auto` | `api` (SDK + key), `claude_cli` (headless Claude Code on a Pro/Max **subscription**, no API key), or `auto` |
| `CLAUDE_CLI_MODEL` | `sonnet` | Model alias passed to `claude -p` (Pro includes Sonnet) |
| `CLAUDE_CLI_CONFIG_DIR` | _(empty)_ | Optional `CLAUDE_CONFIG_DIR` to pin a specific logged-in Claude account |
| `CLAUDE_CLI_TIMEOUT` | `180` | Seconds before a CLI call is abandoned |
| `ENABLE_OCR` | `0` | Set `1` for scanned PDFs (requires `tesseract` + `pytesseract`) |
| `UPLOAD_DIR` | `backend/uploads` | Where PDFs and extracted section texts are stored |
| `MAX_UPLOAD_MB` | `300` | Upload size limit |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend → backend base URL (build-time, frontend) |

## Repository layout

```
backend/    FastAPI app: pipeline stages in app/pipeline/, API in app/api/, tests/
frontend/   Next.js App Router UI: report tabs in src/components/report/
docs/       The ten project deliverables (see below)
```

## Project documentation (deliverables)

1. [Competitor analysis](docs/01-competitor-analysis.md)
2. [Feature gap analysis & differentiation](docs/02-feature-gap-analysis.md)
3. [Architecture](docs/03-architecture.md)
4. [Database schema](docs/04-database-schema.md)
5. [Scoring methodology](docs/05-scoring-methodology.md)
6. [Extraction methodology](docs/06-extraction-methodology.md)
7. [UI wireframes](docs/07-ui-wireframes.md)
8. [Development roadmap](docs/08-roadmap.md)
9. [Monetization opportunities](docs/09-monetization.md)
10. [Risks & limitations](docs/10-risks-limitations.md)
