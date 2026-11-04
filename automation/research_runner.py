"""CLI Research Runner for Automated Company Investigation & Checklist Verification.

Usage:
    python automation/research_runner.py --company "Reliance Jio" --cin "L64200GJ2019PLC108044" --execute
    python automation/research_runner.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from tabulate import tabulate

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import SessionLocal, init_db
from app.database.repository import ResearchRepository
from app.research_engine.checklist_templates import seed_master_templates
from app.research_engine.checklist_executor import ChecklistExecutor
from app.scoring_engine.company_score import CompanyScoreEngine
from app.scoring_engine.valuation_score import IPOValuationScoreEngine


def run_company_research(company_name: str, cin: str | None = None, execute: bool = True) -> None:
    init_db()
    db = SessionLocal()
    try:
        repo = ResearchRepository(db)
        seed_master_templates(repo)

        print(f"\n=======================================================")
        print(f"🎯 IPO RADAR INTELLIGENCE: RESEARCH RUNNER")
        print(f"Company: {company_name}")
        if cin:
            print(f"CIN:     {cin}")
        print(f"=======================================================")

        company = repo.create_company(name=company_name, cin=cin)
        plan = repo.create_or_get_research_plan(company.id)

        if execute:
            print("\n-> Executing 26-Point Master Research Checklist...")
            executor = ChecklistExecutor(db)
            res = executor.execute_plan(plan.id)

            print(f"-> Completed Checks: {res['completed_checks']}/{res['total_checks']}")
            print(f"-> Verified YES:     {res['passed_checks']}")
            print(f"-> Negative NO:      {res['failed_checks']}")
            print(f"-> Missing / N/A:    {res['missing_checks']}")
            print(f"-> Progress:         {int(res['progress'] * 100)}%\n")

            # Fetch items and display table
            from sqlalchemy import select
            from app.database.schema import ChecklistExecution, ChecklistTemplate
            items = db.execute(
                select(ChecklistExecution, ChecklistTemplate)
                .join(ChecklistTemplate, ChecklistTemplate.id == ChecklistExecution.template_id)
                .where(ChecklistExecution.research_plan_id == plan.id)
                .order_by(ChecklistTemplate.display_order.asc())
            ).all()

            table_rows = []
            checklist_dicts = []
            for ex, tmpl in items:
                table_rows.append([
                    tmpl.display_order,
                    tmpl.category.replace("_", " ").title()[:15],
                    tmpl.question[:45] + "...",
                    ex.status,
                    (ex.result_value or "Pending")[:25],
                    ex.evidence_count,
                ])
                checklist_dicts.append({
                    "id": ex.id,
                    "template_id": tmpl.id,
                    "category": tmpl.category,
                    "status": ex.status,
                    "is_mandatory": tmpl.is_mandatory,
                    "weight": tmpl.weight,
                })

            headers = ["#", "Category", "Question", "Status", "Verified Result", "Evidence"]
            print(tabulate(table_rows, headers=headers, tablefmt="grid"))

            # Calculate and display scores
            print("\n=== DUAL RULE-BASED SCORING RESULTS ===")
            q_res = CompanyScoreEngine.calculate_score(checklist_dicts)
            val_res = IPOValuationScoreEngine.calculate_valuation_score({})

            print(f"🏢 Company Quality Score:  {q_res.company_quality_score or 'Pending'}/100")
            print(f"🏷️  IPO Valuation Score:    {val_res.valuation_score or 'Pending'}/100 ({val_res.valuation_call})")
            print(f"📈 Evidence Coverage:       {q_res.research_coverage_pct}%")
            print(f"⚖️  Score Status:           {q_res.score_status}")

            if q_res.warnings:
                print("\n⚠️ Warnings:")
                for w in q_res.warnings:
                    print(f"   - {w}")

    finally:
        db.close()


def list_companies() -> None:
    init_db()
    db = SessionLocal()
    try:
        repo = ResearchRepository(db)
        companies = repo.list_companies(limit=50)
        if not companies:
            print("No companies found in database.")
            return

        rows = [[c.name, c.legal_name or "-", c.cin or "Unlisted", c.industry or "General", c.status] for c in companies]
        print(tabulate(rows, headers=["Name", "Legal Name", "CIN", "Industry", "Status"], tablefmt="grid"))
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="IPO Radar Research Runner")
    parser.add_argument("--company", type=str, help="Company name to research")
    parser.add_argument("--cin", type=str, help="MCA Corporate Identity Number")
    parser.add_argument("--execute", action="store_true", help="Execute checklist verification")
    parser.add_argument("--list", action="store_true", help="List registered companies")

    args = parser.parse_args()
    if args.list:
        list_companies()
    elif args.company:
        run_company_research(args.company, cin=args.cin, execute=args.execute)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
