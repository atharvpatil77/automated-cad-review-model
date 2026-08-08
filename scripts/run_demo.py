"""
MVP demo: run the deterministic compliance checker across all sample parts
and produce a Markdown report. No RAG, no LLM -- this proves the core
extraction-schema -> rule-checker -> report loop works before we add AI.

Usage:
    python scripts/run_demo.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rules.rule_checker import check_part_file
from src.report.report_generator import generate_markdown_report

RULES_PATH = ROOT / "src" / "rules" / "rules_bracket.json"
PARTS_DIR = ROOT / "data" / "sample_parts"
OUTPUT_PATH = ROOT / "compliance_report.md"


def main():
    part_files = sorted(PARTS_DIR.glob("*.json"))
    if not part_files:
        print(f"No sample part files found in {PARTS_DIR}")
        return

    reports = [check_part_file(p, RULES_PATH) for p in part_files]

    for report in reports:
        status = "PASS" if report.passed else "FAIL"
        print(f"{report.part_id} ({report.part_name}): {status}")
        for r in report.results:
            if not r.passed:
                print(f"   ❌ [{r.rule_id}] {r.detail}")

    md = generate_markdown_report(reports)
    OUTPUT_PATH.write_text(md)
    print(f"\nFull report written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
