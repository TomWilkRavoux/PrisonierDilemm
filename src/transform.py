import subprocess
import sys
from pathlib import Path

DBT_DIR = Path(__file__).resolve().parent.parent / "dbt_dilemma"


def main() -> None:
    result = subprocess.run(
        ["dbt", "build", "--profiles-dir", "."],
        cwd=DBT_DIR,
        capture_output=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
