"""One command to produce a distributable build on any platform.

Usage:  python packaging/build.py [--skip-frontend]

Always builds the frontend first unless explicitly skipped, because a stale
src/norefund/web/ produces a build that looks fine and ships the wrong UI.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
WEB_DIR = PROJECT_ROOT / "src" / "norefund" / "web"
SPEC_PATH = PROJECT_ROOT / "packaging" / "norefund.spec"
MACOS_SETUP = PROJECT_ROOT / "packaging" / "macos_setup.py"


def _run(cmd: list[str], *, cwd: Path) -> None:
    print(f"== {' '.join(cmd)} (in {cwd}) ==")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"FAILED: {' '.join(cmd)}", file=sys.stderr)
        raise SystemExit(result.returncode)


def build_frontend() -> None:
    _run(["npm", "ci"], cwd=FRONTEND_DIR)
    _run(["npm", "run", "build"], cwd=FRONTEND_DIR)


def verify_frontend_fresh() -> None:
    index_html = WEB_DIR / "index.html"
    if not index_html.exists():
        raise SystemExit(
            f"{index_html} does not exist. Run the frontend build first "
            "(omit --skip-frontend)."
        )
    newest_src = max(
        (p.stat().st_mtime for p in (FRONTEND_DIR / "src").rglob("*") if p.is_file()),
        default=0.0,
    )
    if index_html.stat().st_mtime < newest_src:
        raise SystemExit(
            f"{index_html} is older than the newest file in frontend/src/ -- "
            "the built UI is stale. Rebuild the frontend (omit --skip-frontend)."
        )


def build_pyinstaller() -> Path:
    _run(
        [
            "pyinstaller",
            str(SPEC_PATH),
            "--distpath",
            "dist",
            "--workpath",
            "build",
            "--noconfirm",
        ],
        cwd=PROJECT_ROOT,
    )
    return PROJECT_ROOT / "dist" / "NoRefund"


def build_macos() -> Path:
    _run([sys.executable, str(MACOS_SETUP), "py2app"], cwd=PROJECT_ROOT)
    return PROJECT_ROOT / "dist" / "NoRefund.app"


def dir_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def fmt_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip the npm build and use the frontend already at src/norefund/web/",
    )
    args = parser.parse_args()

    if not args.skip_frontend:
        build_frontend()
    verify_frontend_fresh()

    if sys.platform == "darwin":
        output = build_macos()
    elif sys.platform in ("win32", "linux"):
        if shutil.which("pyinstaller") is None:
            raise SystemExit(
                "pyinstaller not found. Install the dev extras: pip install -e '.[dev]'"
            )
        output = build_pyinstaller()
    else:
        raise SystemExit(f"Unsupported platform: {sys.platform}")

    if not output.exists():
        raise SystemExit(f"Build reported success but {output} does not exist.")

    size = dir_size(output)
    print("== Build complete ==")
    print(f"Output: {output}")
    print(f"Size:   {fmt_size(size)}")


if __name__ == "__main__":
    main()
