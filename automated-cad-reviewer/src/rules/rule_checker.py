"""
Deterministic compliance checker.

Takes structured CAD feature data (as produced by src/extraction/cad_extractor.py,
or in the MVP, hand-authored JSON standing in for it) and a set of requirement
rules (as produced by the RAG layer, or in the MVP, hand-authored JSON standing
in for it), and returns a pass/fail verdict with reasons.

Design intent: this module must NEVER call an LLM. Numeric/logical compliance
checks should be auditable and deterministic. The agentic/LLM layer sits on
top of this and explains results in natural language -- it does not replace
this logic.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    rule_id: str
    description: str
    severity: str
    passed: bool
    detail: str


@dataclass
class PartReport:
    part_id: str
    part_name: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def critical_failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed and r.severity == "critical"]


def _feature_applies(rule: dict, part: dict) -> bool:
    """Check whether a rule's `applies_to` filter matches this part."""
    applies_to = rule.get("applies_to", {})
    for key, expected in applies_to.items():
        if key == "material" and part.get("material") != expected:
            return False
        if key == "feature_type":
            # handled per-feature in _run_feature_level_rule instead
            continue
    return True


def _run_part_level_rule(rule: dict, part: dict) -> CheckResult:
    check = rule["check"]
    feature_key = rule["feature"]

    if not _feature_applies(rule, part):
        return CheckResult(
            rule_id=rule["id"], description=rule["description"],
            severity=rule["severity"], passed=True,
            detail="Not applicable to this part's material/category."
        )

    actual = part.get(feature_key)

    if check == "min":
        passed = actual is not None and actual >= rule["value"]
        detail = f"{feature_key} = {actual} (required minimum {rule['value']})"
    elif check == "max":
        passed = actual is not None and actual <= rule["value"]
        detail = f"{feature_key} = {actual} (required maximum {rule['value']})"
    elif check == "in_set":
        passed = actual in rule["value"]
        detail = f"{feature_key} = '{actual}' (approved set: {rule['value']})"
    elif check == "bbox_max":
        limits = rule["value"]
        passed = all(dim <= lim for dim, lim in zip(actual, limits))
        detail = f"bounding_box = {actual} (max allowed {limits})"
    else:
        raise ValueError(f"Unknown check type: {check}")

    return CheckResult(
        rule_id=rule["id"], description=rule["description"],
        severity=rule["severity"], passed=passed, detail=detail
    )


def _run_feature_level_rule(rule: dict, part: dict) -> list[CheckResult]:
    """For rules that apply to sub-features (e.g. each mounting hole)."""
    results = []
    target_type = rule["applies_to"].get("feature_type")
    matching_features = [f for f in part.get("features", []) if f.get("type") == target_type]

    if not matching_features:
        results.append(CheckResult(
            rule_id=rule["id"], description=rule["description"],
            severity=rule["severity"], passed=True,
            detail=f"No '{target_type}' features present on this part."
        ))
        return results

    feature_key = rule["feature"]
    check = rule["check"]
    for i, feat in enumerate(matching_features):
        actual = feat.get(feature_key)
        if check == "max":
            passed = actual is not None and actual <= rule["value"]
        elif check == "min":
            passed = actual is not None and actual >= rule["value"]
        else:
            raise ValueError(f"Unknown feature-level check type: {check}")
        detail = f"{target_type} #{i+1}: {feature_key} = {actual} (limit {rule['value']})"
        results.append(CheckResult(
            rule_id=rule["id"], description=rule["description"],
            severity=rule["severity"], passed=passed, detail=detail
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
