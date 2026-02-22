# FQA Tool

CLI to unpack and pack **Fibaro QuickApp** (`.fqa`) files for editing in a normal project layout, with HC3-compatible repack.

- **Unpack**: turns an `.fqa` into a folder with human-readable JSON, Lua files, VS Code workspace, and `.gitignore`.
- **Pack**: writes an `.fqa` using the original format (indent/newline) so the HC3 parser accepts it.

Requires **Python 3.7+** (no extra dependencies).

You can run the script with Python or use a Windows executable (see [Building Windows executable](#building-windows-executable)).

## Usage

Run from the folder that contains `fqa.py` (or put `fqa.exe` on your PATH). In Windows CMD, paste and run one line at a time (CMD often drops newlines when pasting).

Unpack an .fqa (prompts if project folder already exists). By default the project folder is created in the current directory; use `-o` / `--output` to specify another directory:

```
python fqa.py unpack MyQuickApp.fqa
fqa unpack MyQuickApp.fqa
python fqa.py unpack MyQuickApp.fqa -o out
python fqa.py unpack MyQuickApp.fqa --output C:\Projects\fqa
```

Pack a project (prompts if .fqa already exists):

```
python fqa.py pack MyQuickApp
fqa pack MyQuickApp
```

## Building Windows executable

One-file executable, no Python required on the target machine:

```bash
pip install -r requirements-build.txt
build.bat
```

Output: `dist\fqa.exe`. Use it like `fqa unpack file.fqa` and `fqa pack project_dir`.

For a release (build exe + checksums): `python release.py`. This produces `dist\fqa.exe` and `dist\SHA256SUMS.txt`. To verify: in `dist\` run `certutil -hashfile fqa.exe SHA256` (Windows) or `sha256sum -c SHA256SUMS.txt` (Linux/WSL) and compare.

Unpacked layout:

- `main.lua` — main script
- `files/*.lua` — other Lua files
- `.fqa_original.json` — project JSON (human-readable)
- `.fqa_meta.json` — schema and file mapping (used by pack)
- `.vscode/` — settings + recommended extensions (Lua, Lua debug, Git Graph)
- `<name>.code-workspace` — open this in VS Code

## HC3 compatibility

Unpack stores the original `.fqa` format (newline and indent). Pack reuses it when writing the `.fqa`, so the result stays compatible with the HC3 parser.

Tested with **HC3 firmware 5.200.13**.

## License

MIT
