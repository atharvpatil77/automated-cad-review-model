"""
End-to-end demo: real STEP extraction -> deterministic rule check -> LLM
explanation -> Markdown report.

Requires: cadquery (pip install cadquery), google-genai (pip install google-genai)
Requires: GEMINI_API_KEY environment variable set (or pass --no-llm to skip)

Usage:
    python scripts/run_real_demo.py path/to/part.step [material] [--no-llm]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.extraction.cad_extractor import extract_features
from src.rules.rule_checker import check_part, load_json
from src.report.report_generator import generate_markdown_report


RULES_PATH = ROOT / "src" / "rules" / "rules_bracket.json"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_real_demo.py <step_file> [material] [--no-llm]")
        sys.exit(1)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    skip_llm = "--no-llm" in sys.argv

    step_path = args[0]
    material = args[1] if len(args) > 1 else "Aluminum 6061"

    part = extract_features(
        step_path=step_path,
        part_id="REAL-001",
        part_name=Path(step_path).stem,
        material=material,
    )

    print("Extracted features:")
    for k, v in part.items():
        print(f"  {k}: {v}")
    print()

    rules = load_json(RULES_PATH)["rules"]
    report = check_part(part, rules)

    print(f"{report.part_id} ({report.part_name}): {'PASS' if report.passed else 'FAIL'}")
    for r in report.results:
        print(f"   [{r.status.value}] [{r.rule_id}] {r.detail}")

    md = generate_markdown_report([report])

    if not skip_llm:
        try:
            from src.agent.agent import explain_compliance
            print("\nGenerating LLM explanation...")
            narrative = explain_compliance(report)
            print(f"\n--- LLM Summary ---\n{narrative}\n")
            md += f"\n## AI-Generated Summary\n\n{narrative}\n"
        except Exception as e:
            print(f"\n[LLM explanation skipped: {e}]")

    out_path = ROOT / "real_compliance_report.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    main()