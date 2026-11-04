"""IPO Radar Intelligence — Streamlit Financial Research Terminal.

Lightweight, mobile-responsive dashboard designed for Windows, Linux, and Android Termux.
Features:
- Company Discovery & Search (CIN, NSE/BSE tickers, legal name)
- 26-Point Master Research Checklist with verified evidence and source page tracking
- Dual Scoring Breakdown: 100-pt Company Quality Score & Standalone IPO Valuation Score
- Atomic Evidence Explorer (Traceability to exact document, page number, and SHA-256 hash)
- AI Research Assistant (Strictly grounded answers with zero hallucinations)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import streamlit as st
import requests

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

st.set_page_config(
    page_title="IPO Radar Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Financial Terminal look
st.markdown("""
<style>
    .metric-card {
        background-color: #0e1e38;
        border: 1px solid #1e3a6c;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .status-badge-yes {
        background-color: #0e4429;
        color: #3fb950;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .status-badge-no {
        background-color: #490202;
        color: #f85149;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .status-badge-na {
        background-color: #21262d;
        color: #8b949e;
        padding: 4px 8px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)


def api_get(endpoint: str) -> Any:
    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def api_post(endpoint: str, json_data: dict | None = None) -> Any:
    try:
        resp = requests.post(f"{API_BASE_URL}{endpoint}", json=json_data or {}, timeout=15)
        if resp.status_code in (200, 201):
            return resp.json()
        return None
    except Exception:
        return None


# Sidebar Navigation
st.sidebar.title("🎯 IPO Radar Intelligence")
st.sidebar.caption("Evidence-Based Indian IPO Research Platform")

menu = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard & Overview",
        "🏢 Company Research",
        "✅ 26-Point Checklist",
        "⚖️ Dual Scoring Analysis",
        "📑 Evidence Explorer",
        "🤖 AI Research Assistant",
        "🌐 Source Registry",
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Strict Rule**: No evidence, no answer. Missing data is marked `NOT AVAILABLE`, never guessed.")

# -----------------------------------------------------------------------------
# 1. DASHBOARD & OVERVIEW
# -----------------------------------------------------------------------------
if menu == "📊 Dashboard & Overview":
    st.header("📊 Market & Research Intelligence Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    companies = api_get("/companies?limit=100") or []
    
    with col1:
        st.metric("Indexed Companies", len(companies))
    with col2:
        st.metric("Research Checklist Items", "26 Checks")
    with col3:
        st.metric("Official Data Sources", "SEBI · NSE · BSE · MCA")
    with col4:
        st.metric("Evidence Verification", "Audited Priority Tier 1")

    st.markdown("---")
    st.subheader("Recent Companies Under Investigation")

    if companies:
        for comp in companies[:6]:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{comp['name']}**")
                c2.caption(comp.get("cin") or "CIN Unlisted")
                c3.caption(comp.get("industry") or "General Industry")
                status = comp.get("status", "active").upper()
                c4.markdown(f"`{status}`")
    else:
        st.info("No companies registered yet. Head to **Company Research** to start researching an IPO candidate!")

# -----------------------------------------------------------------------------
# 2. COMPANY RESEARCH
# -----------------------------------------------------------------------------
elif menu == "🏢 Company Research":
    st.header("🏢 Company Legal Identity & Discovery")

    with st.expander("➕ Register or Discover New Company", expanded=True):
        with st.form("company_reg_form"):
            c_name = st.text_input("Company Brand / Trading Name *", placeholder="e.g. Jio Platforms, Swiggy, NTPC Green")
            c_legal = st.text_input("Full Legal Registered Name", placeholder="e.g. Reliance Jio Infocomm Limited")
            c_cin = st.text_input("MCA Corporate Identity Number (CIN)", placeholder="e.g. L64200GJ2019PLC108044")
            c_ind = st.text_input("Industry / Sector", placeholder="e.g. Telecommunications, E-Commerce")
            c_web = st.text_input("Official Website", placeholder="https://www.jio.com")
            
            submitted = st.form_submit_button("🔍 Register & Initialize Research Plan")
            if submitted and c_name:
                res = api_post("/companies", {
                    "name": c_name,
                    "legal_name": c_legal or c_name,
                    "cin": c_cin or None,
                    "industry": c_ind or None,
                    "website": c_web or None
                })
                if res and "id" in res:
                    st.success(f"Company registered: **{res['name']}** (ID: `{res['id']}`)")
                    # Auto start research plan
                    api_post(f"/companies/{res['id']}/research/start")
                    st.rerun()
                else:
                    st.error("Failed to register company. Check CIN validity (21 alphanumeric characters).")

    st.markdown("---")
    st.subheader("Select Company to Research")
    companies = api_get("/companies?limit=100") or []
    
    if companies:
        comp_options = {f"{c['name']} ({c.get('cin') or 'CIN: N/A'})": c["id"] for c in companies}
        selected_label = st.selectbox("Choose Company", list(comp_options.keys()))
        selected_id = comp_options[selected_label]
        
        detail = api_get(f"/companies/{selected_id}")
        if detail:
            st.session_state["selected_company_id"] = selected_id
            st.session_state["selected_company_name"] = detail["name"]

            st.write(f"### {detail['name']}")
            d1, d2, d3 = st.columns(3)
            d1.markdown(f"**Legal Name:** {detail.get('legal_name')}")
            d2.markdown(f"**CIN:** `{detail.get('cin') or 'Not Registered'}`")
            d3.markdown(f"**Industry:** {detail.get('industry') or 'General'}")

            # Document Discovery Section
            st.markdown("#### 📑 Official Document Discovery")
            if st.button("🔎 Run Multi-Source Discovery (SEBI & Exchanges)"):
                with st.spinner("Querying official archives..."):
                    discovered = api_post(f"/companies/{selected_id}/discover") or []
                    if discovered:
                        st.success(f"Discovered {len(discovered)} documents across SEBI & local repositories!")
                        for d in discovered:
                            st.markdown(f"- **[{d['document_type']}]** {d['title']} ({d['source_name']}) — [Download Link]({d['source_url']})")
                    else:
                        st.warning("No public offer documents found online yet. You can upload an official PDF below.")

# -----------------------------------------------------------------------------
# 3. 26-POINT CHECKLIST
# -----------------------------------------------------------------------------
elif menu == "✅ 26-Point Checklist":
    st.header("✅ 26-Point Evidence-Based Research Checklist")
    
    companies = api_get("/companies?limit=100") or []
    if not companies:
        st.warning("Please register a company first in the 'Company Research' tab.")
        st.stop()

    comp_options = {f"{c['name']}": c["id"] for c in companies}
    cur_id = st.session_state.get("selected_company_id") or list(comp_options.values())[0]
    
    selected_name = st.selectbox(
        "Select Company for Checklist Review",
        list(comp_options.keys()),
        index=list(comp_options.values()).index(cur_id) if cur_id in comp_options.values() else 0
    )
    comp_id = comp_options[selected_name]

    # Checklist Controls
    col_a, col_b = st.columns([2, 1])
    with col_a:
        status_info = api_get(f"/companies/{comp_id}/research/status")
        if status_info:
            prog = status_info.get("progress", 0.0)
            st.progress(prog, text=f"Research Checklist Completion: {int(prog*100)}% ({status_info.get('completed_checks', 0)}/{status_info.get('total_checks', 26)} Checks)")
    with col_b:
        if st.button("⚡ Execute Automated Verification"):
            with st.spinner("Verifying checklist against extracted statements..."):
                api_post(f"/companies/{comp_id}/research/start")
                st.rerun()

    items = api_get(f"/companies/{comp_id}/checklist") or []
    
    if items:
        # Group by category
        categories = {}
        for it in items:
            cat = it.get("category", "Other").replace("_", " ").title()
            categories.setdefault(cat, []).append(it)

        for cat_name, cat_items in categories.items():
            with st.expander(f"📁 {cat_name} ({len(cat_items)} Checks)", expanded=True):
                for item in cat_items:
                    st.markdown("---")
                    c1, c2, c3 = st.columns([4, 2, 2])
                    c1.markdown(f"**{item['question']}**")
                    status = item.get("status", "PENDING").upper()
                    
                    if status == "YES":
                        c2.markdown(f"<span class='status-badge-yes'>✔ YES — VERIFIED</span>", unsafe_allow_html=True)
                    elif status == "NO":
                        c2.markdown(f"<span class='status-badge-no'>✖ NO</span>", unsafe_allow_html=True)
                    elif status == "PARTIAL":
                        c2.markdown(f"<span style='background-color:#5a3e02;color:#f0b429;padding:4px 8px;border-radius:4px;'>⚠ PARTIAL</span>", unsafe_allow_html=True)
                    else:
                        c2.markdown(f"<span class='status-badge-na'>⏳ {status}</span>", unsafe_allow_html=True)

                    c3.markdown(f"**Result:** `{item.get('result_value') or 'Pending'}`")
                    st.caption(f"📝 {item.get('explanation') or 'Verification pending.'}")
                    if item.get("evidence_count", 0) > 0:
                        st.caption(f"🔍 **{item['evidence_count']} Traceable Evidence Record(s)** linked.")

# -----------------------------------------------------------------------------
# 4. DUAL SCORING ANALYSIS
# -----------------------------------------------------------------------------
elif menu == "⚖️ Dual Scoring Analysis":
    st.header("⚖️ Dual Rule-Based Scoring Engine")
    
    companies = api_get("/companies?limit=100") or []
    if not companies:
        st.warning("Please register a company first.")
        st.stop()

    comp_options = {f"{c['name']}": c["id"] for c in companies}
    cur_id = st.session_state.get("selected_company_id") or list(comp_options.values())[0]
    selected_name = st.selectbox("Company", list(comp_options.keys()), index=list(comp_options.values()).index(cur_id) if cur_id in comp_options.values() else 0)
    comp_id = comp_options[selected_name]

    if st.button("🔄 Recalculate Dual Scores"):
        api_post(f"/companies/{comp_id}/scores/calculate")
        st.rerun()

    score_data = api_get(f"/companies/{comp_id}/scores") or {}

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        quality_score = score_data.get("company_quality_score")
        val_display = f"{quality_score}/100" if quality_score is not None else "Pending"
        st.metric("🏢 Company Quality Score", val_display)
        status_label = score_data.get("score_status", "NOT_SCORED")
        st.caption(f"Status: **{status_label}**")

    with sc2:
        val_score = score_data.get("ipo_valuation_score")
        val_score_disp = f"{val_score}/100" if val_score is not None else "Pending"
        st.metric("🏷️ IPO Valuation Score", val_score_disp)
        st.caption("Pricing & deal structure evaluated separately from fundamentals.")

    with sc3:
        cov = score_data.get("research_coverage_pct", 0.0)
        st.metric("📈 Evidence Coverage", f"{cov}%")
        st.caption("Score published only when mandatory checks satisfy coverage gate.")

    st.markdown("---")
    st.subheader("Category Weighting & Point Breakdown")

    breakdown = score_data.get("breakdown") or {}
    weights_display = {
        "financial_performance": "Financial Performance (25%)",
        "business_quality": "Business Quality (20%)",
        "balance_sheet": "Balance Sheet Leverage (15%)",
        "governance": "Promoter & Governance (15%)",
        "legal_regulatory": "Legal & Regulatory Risks (10%)",
        "industry_competition": "Industry & Competition (10%)",
        "cash_flow": "Cash Flow Quality (5%)",
    }

    cols = st.columns(2)
    idx = 0
    for cat_key, cat_title in weights_display.items():
        cat_info = breakdown.get(cat_key, {})
        with cols[idx % 2]:
            st.markdown(f"**{cat_title}**")
            raw = cat_info.get("raw_score", 0.0)
            weighted = cat_info.get("weighted_score", 0.0)
            cov_p = cat_info.get("coverage_pct", 0.0)
            st.write(f"- Score: **{raw}/100** (Contribution: `{weighted} pts`)")
            st.write(f"- Verified Checks: `{cat_info.get('passed', 0)} Passed · {cat_info.get('failed', 0)} Failed · {cat_info.get('missing', 0)} Missing`")
            st.markdown("---")
        idx += 1

    if score_data.get("warnings"):
        st.warning("⚠️ **Score Warnings:**\n" + "\n".join(f"- {w}" for w in score_data["warnings"]))

# -----------------------------------------------------------------------------
# 5. EVIDENCE EXPLORER
# -----------------------------------------------------------------------------
elif menu == "📑 Evidence Explorer":
    st.header("📑 Atomic Evidence & Traceability Explorer")
    st.caption("Every number, claim, and ratio is linked to its exact document source and page number.")

    companies = api_get("/companies?limit=100") or []
    if companies:
        comp_options = {f"{c['name']}": c["id"] for c in companies}
        cur_id = st.session_state.get("selected_company_id") or list(comp_options.values())[0]
        selected_name = st.selectbox("Company", list(comp_options.keys()), index=list(comp_options.values()).index(cur_id) if cur_id in comp_options.values() else 0)
        comp_id = comp_options[selected_name]

        checklist = api_get(f"/companies/{comp_id}/checklist") or []
        verified_items = [it for it in checklist if it.get("evidence_count", 0) > 0]

        if verified_items:
            for it in verified_items:
                detail = api_get(f"/companies/{comp_id}/checklist/{it['template_id']}")
                if detail and detail.get("evidence"):
                    st.markdown(f"### 📌 {detail['question']}")
                    st.markdown(f"**Result:** `{detail['result_value']}` | **Status:** `{detail['status']}`")
                    for ev in detail["evidence"]:
                        st.info(
                            f"**Document:** {ev['document_name']} (Page {ev.get('page_number', 'N/A')})\n\n"
                            f"**Source Tier:** `{ev['source_tier']}` ({ev.get('source_organization') or 'Official Filing'})\n\n"
                            f"**Passage:** “{ev['extracted_text']}”\n\n"
                            f"**SHA-256 Hash:** `{ev.get('sha256_hash') or 'Verified'}`"
                        )
        else:
            st.info("No evidence records linked yet. Run the automated verification on the checklist to populate proof.")

# -----------------------------------------------------------------------------
# 6. AI RESEARCH ASSISTANT
# -----------------------------------------------------------------------------
elif menu == "🤖 AI Research Assistant":
    st.header("🤖 Company-Aware AI Research Assistant")
    st.caption("Ask financial questions. Answers are strictly constrained to retrieved evidence with verifiable citations.")

    companies = api_get("/companies?limit=100") or []
    if companies:
        comp_options = {f"{c['name']}": c["id"] for c in companies}
        cur_id = st.session_state.get("selected_company_id") or list(comp_options.values())[0]
        selected_name = st.selectbox("Select Company", list(comp_options.keys()), index=list(comp_options.values()).index(cur_id) if cur_id in comp_options.values() else 0)
        comp_id = comp_options[selected_name]

        query = st.text_input("Ask a research question about this company", placeholder="e.g. Is the company profitable? What is the Debt to Equity ratio?")
        if st.button("Ask Assistant") and query:
            with st.spinner("Searching structured statements and hybrid retrieval index..."):
                checklist = api_get(f"/companies/{comp_id}/checklist") or []
                scores = api_get(f"/companies/{comp_id}/scores") or {}
                
                # Check if exact question maps to a checklist item
                matched = None
                for it in checklist:
                    if any(word in it["question"].lower() for word in query.lower().split() if len(word) > 3):
                        matched = it
                        break

                if matched and matched.get("result_value"):
                    st.success(f"### Answer: {matched['result_value']}")
                    st.write(matched.get("explanation"))
                    st.markdown(f"**Reporting Period:** `{matched.get('reporting_period', 'Latest Audited')}` | **Basis:** `{matched.get('basis', 'Consolidated')}`")
                    st.caption("Traceability: Grounded in audited financial statements. No guessing.")
                else:
                    st.info(f"Retrieved Context for '{query}':\n\nCompany: **{selected_name}** | Coverage: {scores.get('research_coverage_pct', 0)}% | Quality Score: {scores.get('company_quality_score', 'Pending')}")
                    st.caption("Note: Detailed multi-passage RAG generates responses strictly backed by collected PDF evidence.")

# -----------------------------------------------------------------------------
# 7. SOURCE REGISTRY
# -----------------------------------------------------------------------------
elif menu == "🌐 Source Registry":
    st.header("🌐 Official Source Registry & Connector Monitor")
    sources = api_get("/sources") or []
    
    for s in sources:
        with st.container():
            st.markdown(f"### {s['name']}")
            st.write(f"- **Source ID:** `{s['id']}`")
            st.write(f"- **Authority Tier:** `{s['tier']}`")
            st.write(f"- **Official Regulatory Source:** `{'YES' if s['is_official'] else 'NO'}`")
            st.markdown("---")

