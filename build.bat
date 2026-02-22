@echo off
REM Build Windows executable. Requires: pip install -r requirements-build.txt
python -m PyInstaller --onefile --name fqa --console fqa.py
echo.
echo Executable: dist\fqa.exe
