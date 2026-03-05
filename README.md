# FQA Tool

Current version: **v1.0.0**

CLI to unpack and pack **Fibaro QuickApp** (`.fqa`) files for editing in a normal project layout, with HC3-compatible repack.

- **Unpack**: turns an `.fqa` into a folder with human-readable JSON, Lua files, VS Code workspace, `.gitignore`, and optional pack scripts (`.fqa-tool-path`, `fqa-pack.py`, wrappers).
- **Pack**: writes an `.fqa` using the original format (indent/newline) so the HC3 parser accepts it.

Requires **Python 3.7+** (no extra dependencies).

You can run the script with Python or use a Windows executable (see [Building Windows executable](#building-windows-executable)).

## Usage

Run from the folder that contains `fqa.py` (or put `fqa.exe` on your PATH). In Windows CMD, paste and run one line at a time (CMD often drops newlines when pasting).

To see the installed `fqa` version:

```bash
python fqa.py --version
fqa --version
```

### Unpack

Unpack an .fqa. By default the project folder is created in the current directory; use `-o` / `--output` to specify another directory. If the project folder already exists, you are prompted to overwrite unless you use `-y` / `--yes` or `--update`.

- **`-o` / `--output` DIR** — Unpack into this directory (default: current directory).
- **`-y` / `--yes`** — Overwrite existing folder without prompting.
- **`--update`** — Update existing folder in place (no delete). Use this to refresh from a new .fqa without removing the folder (avoids "folder in use" on Windows).
- **`-silent`** — No progress output.

Unpack prints progress (files added/updated) unless `-silent` is used.

```
python fqa.py unpack MyQuickApp.fqa
fqa unpack MyQuickApp.fqa
python fqa.py unpack MyQuickApp.fqa -o out
python fqa.py unpack MyQuickApp.fqa -o test --update
python fqa.py unpack MyQuickApp.fqa -y -silent
```

### Pack

Pack a project into an `.fqa`. Output is written to the current directory as `{name}.fqa` unless `-o` / `--output` is given.

- **`-o` / `--output` PATH** — Output path: file (e.g. `dist/App.fqa`) or directory (writes `{name}.fqa` there).
- **`-y` / `--yes`** — Overwrite existing .fqa without prompting.
- **`-silent`** — No progress output.

```
python fqa.py pack MyQuickApp
fqa pack MyQuickApp
python fqa.py pack . -o dist -y
```

### Pack from an unpacked project (fqa-pack)

After unpacking, the project contains a small script and wrappers so you can pack without calling the fqa tool by path. They use a local config file (not committed):

- **`.fqa-tool-path`** — One line: command to run fqa (e.g. `python "C:\path\to\fqa.py"`). Created by `unpack`; add to `.gitignore` (done automatically).
- **`fqa-pack.py`** — Cross-platform script: reads `.fqa-tool-path` and runs `fqa pack .` with your args.
- **`fqa-pack.bat`** (Windows), **`fqa-pack`** (Mac/Linux) — Wrappers that run `fqa-pack.py`.

From the **project root** (the unpacked folder):

```
python fqa-pack.py
python fqa-pack.py -y -o dist
fqa-pack.bat          # Windows
./fqa-pack            # Mac/Linux
```

If `.fqa-tool-path` is missing (e.g. you cloned the repo and didn’t run `unpack`), create it with one line: the command you use to run fqa (e.g. `python "D:\path\to\fqa.py"`).

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
- `.fqa-tool-path` — local path to fqa (created by unpack; in `.gitignore`)
- `fqa-pack.py`, `fqa-pack.bat`, `fqa-pack` — pack script and wrappers (forward e.g. `-y`, `-silent`, `-o`)

## HC3 compatibility

Unpack stores the original `.fqa` format (newline and indent). Pack reuses it when writing the `.fqa`, so the result stays compatible with the HC3 parser.

Tested with **HC3 firmware 5.200.13**.

## License

MIT
