"""Formats PartReport objects into a human-readable Markdown compliance report."""
from __future__ import annotations
from src.rules.rule_checker import PartReport, Status

_MARKS = {
    Status.PASS: "✅",
    Status.FAIL: "❌",
    Status.MANUAL_REVIEW: "🟡",
}


def generate_markdown_report(reports: list[PartReport]) -> str:
    lines = ["# Automated Design Review — Compliance Report", ""]
    n_pass = sum(1 for r in reports if r.passed)
    n_review = sum(1 for r in reports if r.needs_manual_review)
    lines.append(f"**Summary:** {n_pass}/{len(reports)} parts passed all automated checks. "
                 f"{n_review} part(s) have at least one item requiring manual review.\n")

    for report in reports:
        status = "PASS" if report.passed else "FAIL"
        lines.append(f"## {report.part_id} — {report.part_name}: **{status}**\n")
        lines.append("| Rule | Description | Severity | Result | Detail |")
        lines.append("|------|-------------|----------|--------|--------|")
        for r in report.results:
            mark = _MARKS[r.status]
            lines.append(f"| {r.rule_id} | {r.description} | {r.severity} | {mark} {r.status.value} | {r.detail} |")

        crit = report.critical_failures
        if crit:
            lines.append(f"\n> ⚠️ {len(crit)} critical failure(s) — part cannot ship as-is.")

        review = report.needs_manual_review
        if review:
            lines.append(f"\n> 🟡 {len(review)} item(s) could not be automatically verified "
                          f"from CAD geometry alone and require manual/drawing review.")
        lines.append("")
    return "\n".join(lines)