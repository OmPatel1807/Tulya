"""
export.py - Exporters for Tulya Audit Reports (JSON, CSV, Markdown).
"""

import io
import csv
import json
from typing import Dict, Any

from backend.app.api.models import AuditReportResponse, LEGAL_DISCLAIMER


def export_as_json(report: AuditReportResponse) -> str:
    """Exports report as formatted JSON string."""
    return json.dumps(report.model_dump(), indent=2, ensure_ascii=False)


def export_as_csv(report: AuditReportResponse) -> str:
    """Exports audit findings as standard CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "finding_id",
        "category",
        "source",
        "severity",
        "quote_en",
        "quote_hi",
        "explanation",
        "confidence",
        "grounded"
    ])

    for f in report.findings:
        writer.writerow([
            f.finding_id,
            f.category.value if hasattr(f.category, "value") else str(f.category),
            f.source.value if hasattr(f.source, "value") else str(f.source),
            f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            f.quote_en or "",
            f.quote_hi or "",
            f.explanation,
            f.confidence,
            f.grounded
        ])

    return output.getvalue()


def export_as_markdown(report: AuditReportResponse) -> str:
    """Exports audit report as structured GitHub-flavored Markdown."""
    lines = [
        f"# Tulya Audit Report: {report.title}",
        "",
        "> **Important Legal Disclaimer**:",
        f"> *{report.disclaimer}*",
        "",
        "---",
        "",
        "## Summary Overview",
        "",
        f"- **Act Identifier**: `{report.act_slug}`",
        f"- **Audit Status**: `{report.status.value if hasattr(report.status, 'value') else report.status}`",
        f"- **Deterministic Fallback Used**: `{'Yes' if report.fallback_used else 'No'}`",
        f"- **Total Clauses Audited**: {report.summary.get('total_pairs', 0)}",
        f"- **Total Discrepancies Flagged**: {report.summary.get('findings_count', 0)}",
        "",
        "### Findings Breakdown by Category",
        "",
        "| Category | Count | Percentage |",
        "| :--- | :--- | :--- |"
    ]

    total_f = report.summary.get("findings_count", len(report.findings))
    by_cat = report.summary.get("by_category", {})
    for cat, count in sorted(by_cat.items()):
        pct = (count / total_f * 100.0) if total_f > 0 else 0.0
        lines.append(f"| **{cat}** | {count} | {pct:.1f}% |")

    lines.extend([
        "",
        "### Stage Attribution Breakdown",
        "",
        "| Stage Source | Count | Description |",
        "| :--- | :--- | :--- |"
    ])

    by_src = report.summary.get("by_source", {})
    lines.append(f"| **Deterministic Only** | {by_src.get('deterministic_only', 0)} | Fact engine verification (numbers, dates, currency, units) |")
    lines.append(f"| **LLM Only** | {by_src.get('llm_only', 0)} | Grounded semantic auditor (modality, scope, conditions) |")
    lines.append(f"| **Both (Confirmed & Merged)** | {by_src.get('both', 0)} | Corroborated and reconciled across both stages |")

    lines.extend([
        "",
        "---",
        "",
        "## Detailed Audit Findings",
        ""
    ])

    if not report.findings:
        lines.append("*No substantive discrepancies detected across audited clauses.*")
    else:
        for idx, f in enumerate(report.findings, start=1):
            cat_val = f.category.value if hasattr(f.category, "value") else str(f.category)
            sev_val = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            src_val = f.source.value if hasattr(f.source, "value") else str(f.source)

            lines.extend([
                f"### {idx}. [{cat_val}] Finding `{f.finding_id}` ({sev_val} Severity | {src_val})",
                f"- **Explanation**: {f.explanation}",
                f"- **English Evidence Quote**: `{f.quote_en or 'None (Omitted in English)'}`",
                f"- **Hindi Evidence Quote**: `{f.quote_hi or 'None (Omitted in Hindi)'}`",
                f"- **Grounding Verified**: {'Yes (Verbatim Substring)' if f.grounded else 'No'}",
                f"- **Confidence**: {f.confidence:.2f}",
                ""
            ])

    lines.extend([
        "---",
        "",
        "## Methodological Disclaimer",
        LEGAL_DISCLAIMER,
        ""
    ])

    return "\n".join(lines)

