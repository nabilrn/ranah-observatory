from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_milestone65_irbi_krb_lookup_bridge_contract() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_milestone65_irbi_krb_lookup_bridge.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"authorized_bridges": 9' in result.stdout
    assert '"risk_lookup_rows": 124' in result.stdout
