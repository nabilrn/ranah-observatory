from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_milestone63_validator_passes() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_milestone63_bpbd_mitigation_plan_2026.py")],
        cwd=ROOT,
        check=True,
    )
