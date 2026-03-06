# PyPI package: build and upload workflow

This document describes how to build the **PyPI-compatible** package (sdist + wheel) and upload it to [PyPI](https://pypi.org/project/fqa/). For the **Windows executable** and zip bundle, see [Building Windows executable](../README.md#building-windows-executable) and `release.py`.

---

## Prerequisites

- Python 3.7+ with `build` and `twine` installed:
  ```bash
  pip install build twine
  ```
- **Version** in `fqa.py` and `pyproject.toml` bumped for the release (e.g. `1.0.1`).
- **PyPI API token** stored in `.pypirc` in the project root (or in `~/.pypirc`).  
  `.pypirc` is in `.gitignore`; create it with:
  ```ini
  [pypi]
  username = __token__
  password = pypi-YOUR_API_TOKEN
  ```
  Create a token at [pypi.org/manage/account/token/](https://pypi.org/manage/account/token/).

---

## Workflow (manual)

From the **project root** (`d:\HomeAutomation\fqa` or repo root):

1. **Build** the sdist and wheel:
   ```bash
   python -m build
   ```
   This produces:
   - `dist/fqa-<version>.tar.gz` (source distribution)
   - `dist/fqa-<version>-py3-none-any.whl` (wheel)

2. **Upload** only the PyPI artifacts (do **not** upload the Windows zip/exe/checksums):
   ```bash
   python -m twine upload --config-file "D:\HomeAutomation\fqa\.pypirc" dist/*.tar.gz dist/*.whl
   ```
   If the script is run from the repo root, you can use a path relative to the repo, or use the `.bat` below.

3. **Tag and release** (optional but recommended):
   - Commit any version bumps, then:
     ```bash
     git tag v1.0.1
     git push origin v1.0.1
     ```
   - Create a GitHub Release for that tag and attach `dist/fqa.exe`, `dist/fqa-<version>-windows.zip`, and `dist/SHA256SUMS.txt` if you built them with `release.py`.

---

## One-shot: build + upload (Windows)

From the project root, run:

```batch
publish-pypi.bat
```

This script:

1. Changes to the directory where the script lives (repo root).
2. Runs `python -m build`.
3. Runs `python -m twine upload --config-file "<repo-root>\.pypirc" dist\*.tar.gz dist\*.whl`.

Ensure `.pypirc` exists in the repo root with your PyPI token before running.

---

## Automated upload on GitHub Release

The workflow `.github/workflows/publish-pypi.yml` runs when you **publish a GitHub Release**. It builds the sdist and wheel and uploads them to PyPI using the repository secret **`PYPI_API_TOKEN`**. No local `.pypirc` or `publish-pypi.bat` is needed for that path.

---

## Summary

| Goal                         | Command / action                                      |
|-----------------------------|--------------------------------------------------------|
| Build sdist + wheel only     | `python -m build`                                     |
| Upload to PyPI (local)      | `publish-pypi.bat` or `twine upload --config-file ...`|
| Build exe + zip + checksums | `python release.py`                                   |
| Upload to PyPI (CI)         | Publish a GitHub Release; workflow uses `PYPI_API_TOKEN` |
