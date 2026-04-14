from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"
SHARED_DIRS = ("service", "etl")
IGNORE_NAMES = shutil.ignore_patterns(
    ".venv",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "local.settings.json",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)


def _copy_api_root(destination: Path) -> None:
    for path in API_ROOT.iterdir():
        if path.name in {".venv", "__pycache__", "local.settings.json"}:
            continue
        target = destination / path.name
        if path.is_dir():
            shutil.copytree(path, target, ignore=IGNORE_NAMES)
        else:
            shutil.copy2(path, target)


def stage_function_app(destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    _copy_api_root(destination)
    for name in SHARED_DIRS:
        shutil.copytree(REPO_ROOT / name, destination / name, ignore=IGNORE_NAMES)


def validate_import(destination: Path) -> None:
    subprocess.run(
        [sys.executable, "-c", "import function_app; print('function_app import ok')"],
        cwd=destination,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage the Azure Function app with shared repo modules.")
    parser.add_argument("--dest", required=True, help="Destination directory for the staged bundle.")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip the isolated function_app import smoke check.",
    )
    args = parser.parse_args()

    destination = Path(args.dest).resolve()
    stage_function_app(destination)
    if not args.skip_validate:
        validate_import(destination)
    print(f"Staged Function app bundle at {destination}")


if __name__ == "__main__":
    main()
