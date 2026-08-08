"""Formats PartReport objects into a human-readable Markdown compliance report."""
from __future__ import annotations
from src.rules.rule_checker import PartReport


def generate_markdown_report(reports: list[PartReport]) -> str:
    lines = ["# Automated Design Review — Compliance Report", ""]
    n_pass = sum(1 for r in reports if r.passed)
    lines.append(f"**Summary:** {n_pass}/{len(reports)} parts passed all checks.\n")

    for report in reports:
        status = "PASS" if report.passed else "FAIL"
        lines.append(f"## {report.part_id} — {report.part_name}: **{status}**\n")
        lines.append("| Rule | Description | Severity | Result | Detail |")
        lines.append("|------|-------------|----------|--------|--------|")
        for r in report.results:
            mark = "✅" if r.passed else "❌"
            lines.append(f"| {r.rule_id} | {r.description} | {r.severity} | {mark} | {r.detail} |")
        if not report.passed:
            crit = report.critical_failures
            if crit:
                lines.append(f"\n> ⚠️ {len(crit)} critical failure(s) — part cannot ship as-is.")
        lines.append("")
    return "\n".join(lines)
