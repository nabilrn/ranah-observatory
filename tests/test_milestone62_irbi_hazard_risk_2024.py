from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_milestone62_validator_passes() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_milestone62_irbi_hazard_risk_2024.py")],
        cwd=ROOT,
        check=True,
    )
