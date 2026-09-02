from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_milestone64_krb_recommendations_validate() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_milestone64_krb_recommendations.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
