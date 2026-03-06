@echo off
REM Build PyPI sdist + wheel and upload to PyPI.
REM Run from project root. Requires .pypirc in this directory with [pypi] token.
setlocal
cd /d "%~dp0"

if not exist ".pypirc" (
    echo ERROR: .pypirc not found in %~dp0
    echo Create it with [pypi] username = __token__ and password = pypi-YOUR_TOKEN
    exit /b 1
)

echo Building sdist and wheel...
python -m build
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Uploading to PyPI...
python -m twine upload --config-file "%~dp0.pypirc" dist\*.tar.gz dist\*.whl
if errorlevel 1 (
    echo Upload failed.
    exit /b 1
)

echo Done. Package uploaded to PyPI.
endlocal
