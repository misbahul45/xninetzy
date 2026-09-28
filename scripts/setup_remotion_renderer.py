"""Bootstrap the canonical Remotion renderer project.

Copies ``xninetzy/renderers/remotion/`` to ``~/.local/share/xninetzy/video/remotion``
(default overridable via ``XNINETZY_REMOTION_PROJECT_ROOT``) and runs
``npm install`` once. Idempotent: re-running with the same destination
only re-installs when ``node_modules`` is missing.

CPU-only. No GPU packages.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_DEST: Path = Path.home() / ".local" / "share" / "xninetzy" / "video" / "remotion"
SOURCE_ROOT: Path = Path(__file__).resolve().parents[1] / "xninetzy" / "renderers" / "remotion"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path(os.environ.get("XNINETZY_REMOTION_PROJECT_ROOT", DEFAULT_DEST)),
        help="Destination directory for the Remotion project",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite destination if it exists")
    parser.add_argument("--skip-install", action="store_true", help="Skip npm install")
    args = parser.parse_args()

    src = SOURCE_ROOT
    if not (src / "package.json").is_file():
        print(f"ERROR: source Remotion template missing under {src}", file=sys.stderr)
        return 1

    dest: Path = args.dest.resolve()
    if dest.exists() and any(dest.iterdir()):
        if args.force:
            print(f"forcing remove of {dest}")
            shutil.rmtree(dest)
        else:
            print(
                f"ERROR: destination {dest} is non-empty; use --force to overwrite",
                file=sys.stderr,
            )
            return 2

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("node_modules", ".cache", "dist"))
    print(f"copied template -> {dest}")

    if args.skip_install:
        print("skipped npm install (--skip-install)")
        return 0

    if shutil.which("npm") is None:
        print("ERROR: npm not on PATH; install Node 18+ first", file=sys.stderr)
        return 3

    env = dict(os.environ)
    env.setdefault("CHROMIUM_FLAGS", "--no-sandbox --disable-gpu --disable-software-rasterizer")
    proc = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund"],
        cwd=str(dest),
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        print("ERROR: npm install failed", file=sys.stderr)
        return 4

    print(f"installed dependencies under {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
