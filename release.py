#!/usr/bin/env python3
"""
Build release artifacts for fqa:

- dist/fqa.exe (PyInstaller, Windows console exe)
- dist/fqa-<version>-windows.zip (exe + key source files)
- dist/SHA256SUMS.txt (SHA-256 for all release assets)

Run from project root: python release.py
"""
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

from fqa import VERSION

PROJECT_ROOT = Path(__file__).resolve().parent
DIST = PROJECT_ROOT / "dist"


def build_exe() -> Path:
    """Run PyInstaller to produce dist/fqa.exe, return its path."""
    exe_path = DIST / "fqa.exe"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--onefile", "--name", "fqa", "--console", "fqa.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    if not exe_path.exists():
        raise SystemExit("dist/fqa.exe not found after build")
    return exe_path


def build_zip(exe_path: Path) -> Path:
    """Create dist/fqa-<version>-windows.zip with exe + key source files."""
    DIST.mkdir(parents=True, exist_ok=True)
    version = VERSION.lstrip("v")
    zip_name = f"fqa-{version}-windows.zip"
    zip_path = DIST / zip_name

    sources = [
        (exe_path, "fqa.exe"),
        (PROJECT_ROOT / "fqa.py", "fqa.py"),
        (PROJECT_ROOT / "README.md", "README.md"),
        (PROJECT_ROOT / "LICENSE", "LICENSE"),
    ]

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, arcname in sources:
            if not src.exists():
                print(f"Warning: {src} not found, skipping in zip")
                continue
            zf.write(src, arcname)

    print(f"Wrote {zip_path}")
    return zip_path


def sha256_file(path: Path) -> str:
    """Return hex SHA256 of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(assets):
    """Write dist/SHA256SUMS.txt for the given release assets."""
    DIST.mkdir(parents=True, exist_ok=True)
    lines = []
    for path in assets:
        if not path.exists():
            print(f"Warning: {path} not found, skipping in checksums")
            continue
        digest = sha256_file(path)
        lines.append(f"{digest}  {path.name}")
    if not lines:
        print("No release assets found in dist/")
        return
    out = DIST / "SHA256SUMS.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


def main():
    print(f"Building fqa release for version {VERSION}...")
    exe_path = build_exe()
    zip_path = build_zip(exe_path)
    print("Writing checksums...")
    write_checksums([exe_path, zip_path])
    print("Done. Release assets in dist/")


if __name__ == "__main__":
    main()
