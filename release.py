#!/usr/bin/env python3
"""
Build fqa.exe and write SHA256SUMS.txt for release assets.
Run from project root: python release.py
"""
import hashlib
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST = PROJECT_ROOT / "dist"
RELEASE_ASSETS = ["fqa.exe"]  # add e.g. "fqa-windows.zip" if you bundle more


def build():
    """Run PyInstaller to produce dist/fqa.exe."""
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--onefile", "--name", "fqa", "--console", "fqa.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def sha256_file(path: Path) -> str:
    """Return hex SHA256 of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums():
    """Write dist/SHA256SUMS.txt for release assets."""
    DIST.mkdir(parents=True, exist_ok=True)
    lines = []
    for name in RELEASE_ASSETS:
        path = DIST / name
        if not path.exists():
            print(f"Warning: {path} not found, skipping")
            continue
        digest = sha256_file(path)
        lines.append(f"{digest}  {name}")
    if not lines:
        print("No release assets found in dist/")
        return
    out = DIST / "SHA256SUMS.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


def main():
    print("Building fqa.exe...")
    build()
    print("Writing checksums...")
    write_checksums()
    print("Done. Release assets in dist/")


if __name__ == "__main__":
    main()
