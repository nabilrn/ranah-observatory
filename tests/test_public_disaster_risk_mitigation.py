from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_disaster_risk_mitigation_contract() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_public_disaster_risk_mitigation.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"risk_rows": 124' in result.stdout
    assert '"recommendation_actions": 49' in result.stdout
