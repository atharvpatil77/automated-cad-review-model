"""
Deterministic compliance checker.

Takes structured CAD feature data (as produced by src/extraction/cad_extractor.py)
and a set of requirement rules (as produced by the RAG layer, or currently
hand-authored JSON standing in for it), and returns a pass/fail/manual-review
verdict per rule with reasons.

Design intent: this module must NEVER call an LLM. Numeric/logical compliance
checks should be auditable and deterministic. The agentic/LLM layer sits on
top of this and explains results in natural language -- it does not replace
this logic.

Three-state result, not just pass/fail:
- PASS / FAIL: the required feature was extracted and the check ran.
- MANUAL_REVIEW: the required feature is not present in the extracted data
  at all (e.g. hole tolerance, which geometry alone cannot provide -- it
  lives in drawing PMI/manufacturing specs, not the nominal 3D model).
  This is NOT the same as a failure -- it means "this system cannot verify
  this requirement automatically," which must be surfaced honestly rather
  than silently reported as either a pass or a fail.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass
class CheckResult:
    rule_id: str
    description: str
    severity: str
    status: Status
    detail: str

    @property
    def passed(self) -> bool:
        """Kept for backward compatibility with report_generator.py."""
        return self.status == Status.PASS


@dataclass
class PartReport:
    part_id: str
    part_name: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.status != Status.FAIL for r in self.results)

    @property
    def critical_failures(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == Status.FAIL and r.severity == "critical"]

    @property
    def needs_manual_review(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == Status.MANUAL_REVIEW]


def _feature_applies(rule: dict, part: dict) -> bool:
    """Check whether a rule's `applies_to` filter matches this part."""
    applies_to = rule.get("applies_to", {})
    for key, expected in applies_to.items():
        if key == "material" and part.get("material") != expected:
            return False
        if key == "feature_type":
            continue
    return True


def _run_part_level_rule(rule: dict, part: dict) -> CheckResult:
    check = rule["check"]
    feature_key = rule["feature"]

    if not _feature_applies(rule, part):
        return CheckResult(
            rule_id=rule["id"], description=rule["description"],
            severity=rule["severity"], status=Status.PASS,
            detail="Not applicable to this part's material/category."
        )

    actual = part.get(feature_key)

    if actual is None:
        return CheckResult(
            rule_id=rule["id"], description=rule["description"],
            severity=rule["severity"], status=Status.MANUAL_REVIEW,
            detail=f"{feature_key} not available from extracted geometry -- "
                   f"requires manual review (e.g. drawing/PMI data)."
        )

    if check == "min":
        status = Status.PASS if actual >= rule["value"] else Status.FAIL
        detail = f"{feature_key} = {actual} (required minimum {rule['value']})"
    elif check == "max":
        status = Status.PASS if actual <= rule["value"] else Status.FAIL
        detail = f"{feature_key} = {actual} (required maximum {rule['value']})"
    elif check == "in_set":
        status = Status.PASS if actual in rule["value"] else Status.FAIL
        detail = f"{feature_key} = '{actual}' (approved set: {rule['value']})"
    elif check == "bbox_max":
        limits = rule["value"]
        ok = all(dim <= lim for dim, lim in zip(actual, limits))
        status = Status.PASS if ok else Status.FAIL
        detail = f"bounding_box = {actual} (max allowed {limits})"
    else:
        raise ValueError(f"Unknown check type: {check}")

    return CheckResult(
        rule_id=rule["id"], description=rule["description"],
        severity=rule["severity"], status=status, detail=detail
    )


def _run_feature_level_rule(rule: dict, part: dict) -> list[CheckResult]:
    """For rules that apply to sub-features (e.g. each mounting hole)."""
    results = []
    target_type = rule["applies_to"].get("feature_type")
    matching_features = [f for f in part.get("features", []) if f.get("type") == target_type]

    if not matching_features:
        results.append(CheckResult(
            rule_id=rule["id"], description=rule["description"],
            severity=rule["severity"], status=Status.PASS,
            detail=f"No '{target_type}' features present on this part."
        ))
        return results

    feature_key = rule["feature"]
    check = rule["check"]
    for i, feat in enumerate(matching_features):
        actual = feat.get(feature_key)

        if actual is None:
            results.append(CheckResult(
                rule_id=rule["id"], description=rule["description"],
                severity=rule["severity"], status=Status.MANUAL_REVIEW,
                detail=f"{target_type} #{i+1}: {feature_key} not available from "
                       f"extracted geometry -- requires manual review."
            ))
            continue

        if check == "max":
            status = Status.PASS if actual <= rule["value"] else Status.FAIL
        elif check == "min":
            status = Status.PASS if actual >= rule["value"] else Status.FAIL
        else:
            raise ValueError(f"Unknown feature-level check type: {check}")
        detail = f"{target_type} #{i+1}: {feature_key} = {actual} (limit {rule['value']})"
        results.append(CheckResult(
            rule_id=rule["id"], description=rule["description"],
            severity=rule["severity"], status=status, detail=detail
        ))
    return results


def check_part(part: dict, rules: list[dict]) -> PartReport:
    report = PartReport(part_id=part["part_id"], part_name=part["part_name"])
    for rule in rules:
        if "feature_type" in rule.get("applies_to", {}):
            report.results.extend(_run_feature_level_rule(rule, part))
        else:
            report.results.append(_run_part_level_rule(rule, part))
    return report


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def check_part_file(part_path: str | Path, rules_path: str | Path) -> PartReport:
    part = load_json(part_path)
    ruleset = load_json(rules_path)
    return check_part(part, ruleset["rules"])