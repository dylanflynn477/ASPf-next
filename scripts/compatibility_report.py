"""Render the historical compatibility matrix from its executable manifest."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "historical_compat" / "manifest.json"


def _feature_status(cases: list[dict[str, Any]]) -> str:
    if all(case["disposition"] == "passing" for case in cases):
        restrictions = any("restriction" in case["expected_aspf_next_status"] for case in cases)
        return "PASS (restricted)" if restrictions else "PASS"
    if any(case["expected_aspf_next_status"] == "unresolved" for case in cases):
        return "XFAIL (unresolved)"
    return "XFAIL"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = data["cases"]
    features: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        features[case["feature"]].append(case)

    print("Historical Clingo{f} compatibility matrix")
    print(f"Target: {data['target']}")
    print()
    for feature in sorted(features):
        print(f"  {feature:<48} {_feature_status(features[feature])}")

    passing = sum(case["disposition"] == "passing" for case in cases)
    restricted = sum(
        case["disposition"] == "passing" and "restriction" in case["expected_aspf_next_status"]
        for case in cases
    )
    invalid = sum(case["expected_historical_status"] == "invalid" for case in cases)
    deferred = sum(case["disposition"] == "intentionally-deferred" for case in cases)
    unsupported = sum(case["expected_aspf_next_status"] == "unsupported" for case in cases)
    unresolved = sum(case["expected_aspf_next_status"] == "unresolved" for case in cases)
    baseline = sum(case["baseline_aspf_next_status"] in {"passing", "rejected"} for case in cases)

    print()
    print("Historical compatibility cases")
    print(f"  baseline matching cases: {baseline}")
    print(f"  passing:                {passing}")
    print(f"    with restriction:     {restricted}")
    print(f"    invalid-and-rejected: {invalid}")
    print(f"  expected unsupported:   {unsupported}")
    print(f"    intentionally deferred: {deferred}")
    print(f"  unresolved:             {unresolved}")
    print(f"  total target cases:     {len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
