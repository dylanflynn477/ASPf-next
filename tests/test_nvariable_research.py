from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


def test_nvariable_probe_records_semantic_match_and_grounding_growth() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "research/nvariable_reference_probe.py",
            "--sizes",
            "2",
            "4",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "2,6,8,2,4,6,2" in result.stdout
    assert "4,8,12,4,8,12,4" in result.stdout
    assert "relation-copy model check: 2/2 copied" in result.stdout
    assert "fake-placeholder model check: 0/2 copied" in result.stdout
    assert "not grounder-inert n-variable support" in result.stdout
