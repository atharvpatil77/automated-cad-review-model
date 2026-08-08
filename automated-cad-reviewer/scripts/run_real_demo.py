"""
End-to-end demo using REAL STEP file extraction (src/extraction/cad_extractor.py)
instead of the hand-authored JSON stand-ins in data/sample_parts/.

Requires cadquery to be installed (pip install cadquery) -- this will not
run in an environment without it.

Usage:
    python scripts/run_real_demo.py path/to/part.step
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
        print("Usage: python scripts/run_real_demo.py <step_file> [material]")
        sys.exit(1)

    step_path = sys.argv[1]
    material = sys.argv[2] if len(sys.argv) > 2 else "Aluminum 6061"

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
    out_path = ROOT / "real_compliance_report.md"
    out_path.write_text(md)
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    main()