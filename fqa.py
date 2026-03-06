import json
import argparse
import os
import shutil
import sys
import time
from pathlib import Path

VERSION = "1.0.1"

# Default: show progress. Set to True to suppress (e.g. when -silent is used).
SILENT = False


# ============================================================
# JSON Utilities
# ============================================================

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json_crlf(path, data):
    _write_json(path, data, indent=2, newline="\r\n")


def _write_json(path, data, indent=2, newline="\r\n"):
    text = json.dumps(
        data,
        indent=indent,
        sort_keys=False,
        ensure_ascii=False
    )
    if newline != "\n":
        text = text.replace("\n", newline)
    Path(path).write_text(text, encoding="utf-8", newline="")


def _infer_json_format(raw_text):
    """Infer newline and indent from raw JSON so pack can match original .fqa format."""
    out = {"newline": "\r\n", "indent": 2}
    if "\r\n" in raw_text:
        out["newline"] = "\r\n"
    elif "\n" in raw_text:
        out["newline"] = "\n"
    # Infer indent: after first { and newline, count spaces before next non-space
    i = raw_text.find("{")
    if i >= 0:
        j = raw_text.find("\n", i)
        if j >= 0:
            k = j + 1
            while k < len(raw_text) and raw_text[k] in " \t":
                k += 1
            if k > j + 1:
                spaces = len(raw_text[j + 1 : k].expandtabs(4).replace("\t", "    "))
                if spaces > 0:
                    out["indent"] = spaces
    return out


# ============================================================
# Schema Handling
# ============================================================

def detect_schema(data):
    ip = data.get("initialProperties", {})
    ip_files = ip.get("files", [])
    root_files = data.get("files", [])

    if ip_files:
        return "initialProperties"

    if root_files:
        return "rootFiles"

    return None


def extract_files(data, schema):
    if schema == "initialProperties":
        return data["initialProperties"].get("files", [])
    elif schema == "rootFiles":
        return data.get("files", [])
    return []


# ============================================================
# Lua Formatting
# ============================================================

def normalize_lua_for_disk(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.split("\n")
    new_lines = []

    for line in lines:
        leading = len(line) - len(line.lstrip(" "))
        tabs = leading // 4
        remainder = leading % 4

        new_line = ("\t" * tabs) + (" " * remainder) + line.lstrip(" ")
        new_lines.append(new_line)

    return "\r\n".join(new_lines)


def normalize_lua_for_pack(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ============================================================
# UNPACK
# ============================================================

def _prompt_yes_no(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("", "n", "no"):
            return False


def _progress(msg: str) -> None:
    if not SILENT:
        print(msg)


def _cwd_inside_path(path: Path) -> bool:
    """True if current working directory is the given path or inside it (so rmtree would fail)."""
    try:
        cwd = Path.cwd().resolve()
        target = path.resolve()
        return cwd == target or target in cwd.parents
    except OSError:
        return False


def _rmtree_retry(path: Path, max_attempts: int = 3, delay: float = 0.25) -> None:
    """Remove directory tree; on Windows retries on PermissionError (folder in use)."""
    if _cwd_inside_path(path):
        raise PermissionError(
            f"Cannot remove '{path}': your current directory is inside it. "
            "Change directory first (e.g. cd to parent), then run unpack again."
        )
    last_err = None
    for attempt in range(max_attempts):
        try:
            shutil.rmtree(path)
            return
        except PermissionError as e:
            last_err = e
            if attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                raise PermissionError(
                    f"Cannot remove '{path}': it is in use by another process. "
                    "Close any program using this folder (e.g. Explorer, VS Code, terminal) and try again, or use a different output path."
                ) from e
    if last_err:
        raise last_err


def _get_invocation_command() -> str:
    """Return the command string used to invoke this fqa script/exe (for .fqa-tool-path).
    Uses 'python' from PATH when running as script; full path when running as frozen exe.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'python "{Path(__file__).resolve()}"'


FQA_PACK_PY = r'''# Auto-generated by fqa unpack. Cross-platform pack script.
import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    cfg = root / ".fqa-tool-path"
    if not cfg.exists():
        print("ERROR: .fqa-tool-path not found. Run 'fqa unpack' or create it.", file=sys.stderr)
        sys.exit(1)
    line = cfg.read_text(encoding="utf-8").strip().splitlines()
    line = [l.strip() for l in line if l.strip()]
    if not line:
        print("ERROR: .fqa-tool-path is empty.", file=sys.stderr)
        sys.exit(1)
    # First non-empty line = full command (e.g. "python /path/to/fqa.py" or "/path/to/fqa.exe")
    cmd_str = line[0]
    # Parse respecting quoted parts so paths with spaces work
    import shlex
    parts = shlex.split(cmd_str)
    args = parts + ["pack", "."] + [a for a in sys.argv[1:]]
    subprocess.check_call(args, cwd=root)

if __name__ == "__main__":
    main()
'''

FQA_PACK_BAT = r'''@echo off
python "%~dp0fqa-pack.py" %*
'''

FQA_PACK_SH = r'''#!/usr/bin/env sh
cd "$(dirname "$0")" && python fqa-pack.py "$@"
'''


def _write_fqa_pack_if_missing(project_dir: Path) -> None:
    project_dir = Path(project_dir)
    if not (project_dir / "fqa-pack.py").exists():
        (project_dir / "fqa-pack.py").write_text(FQA_PACK_PY, encoding="utf-8", newline="\n")
    if not (project_dir / "fqa-pack.bat").exists():
        (project_dir / "fqa-pack.bat").write_text(FQA_PACK_BAT, encoding="utf-8", newline="\r\n")
    sh_path = project_dir / "fqa-pack"
    if not sh_path.exists():
        sh_path.write_text(FQA_PACK_SH, encoding="utf-8", newline="\n")
        try:
            sh_path.chmod(0o755)
        except OSError:
            pass


def unpack(fqa_path, output_dir=None, yes=False, silent=False, update=False):
    global SILENT
    SILENT = silent

    fqa_path = Path(fqa_path).resolve()
    if fqa_path.is_dir():
        print(f"'{fqa_path}' is a directory. Pass the path to an .fqa file (e.g. {fqa_path.name}.fqa).")
        return
    if not fqa_path.exists() and fqa_path.suffix != ".fqa":
        with_fqa = fqa_path.with_suffix(".fqa")
        if with_fqa.exists():
            fqa_path = with_fqa
    raw_text = fqa_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    project_name = data.get("name", fqa_path.stem)
    if output_dir is not None:
        project_dir = Path(output_dir).resolve() / project_name
    else:
        project_dir = Path(project_name)

    if project_dir.exists():
        if update:
            if not project_dir.is_dir():
                print(f"ERROR: '{project_dir}' exists and is not a directory. Cannot update.")
                return
            _progress(f"Updating {fqa_path.name} -> {project_dir}")
        else:
            if not yes and not _prompt_yes_no(f"Folder '{project_dir}' already exists. Overwrite it?"):
                print("Unpack cancelled.")
                return
            if project_dir.is_dir():
                _rmtree_retry(project_dir)
            else:
                project_dir.unlink()
            _progress(f"Unpacking {fqa_path.name} -> {project_dir}")
    else:
        _progress(f"Unpacking {fqa_path.name} -> {project_dir}")

    project_dir.mkdir(parents=True, exist_ok=update)
    (project_dir / "files").mkdir(exist_ok=True)
    (project_dir / ".vscode").mkdir(exist_ok=True)

    schema = detect_schema(data)
    if not schema:
        print("No files found in FQA.")
        return

    files = extract_files(data, schema)

    # Store human-readable JSON; remember original format so pack can emit HC3-compatible .fqa
    original_format = _infer_json_format(raw_text)
    write_json_crlf(project_dir / ".fqa_original.json", data)
    _progress("  + .fqa_original.json")

    file_map = {}

    for f in files:
        name = f.get("name")
        content = f.get("content", "")
        is_main = f.get("isMain", False)

        formatted = normalize_lua_for_disk(content)

        if is_main or name in ("main", "main.lua"):
            (project_dir / "main.lua").write_text(
                formatted, encoding="utf-8", newline=""
            )
            file_map["main.lua"] = name
            _progress("  + main.lua")
        else:
            filename = name if "." in name else name + ".lua"
            (project_dir / "files" / filename).write_text(
                formatted, encoding="utf-8", newline=""
            )
            file_map[filename] = name
            _progress(f"  + files/{filename}")

    meta = {
        "_schema": schema,
        "_file_map": file_map,
        "_original_newline": original_format["newline"],
        "_original_indent": original_format["indent"],
    }

    write_json_crlf(project_dir / ".fqa_meta.json", meta)
    _progress("  + .fqa_meta.json")

    # VS Code: workspace + settings for Lua editing
    workspace_name = f"{project_dir.name}.code-workspace"
    workspace = {
        "folders": [{"path": "."}],
        "settings": {
            "files.eol": "\r\n",
            "files.encoding": "utf8",
            "files.insertFinalNewline": True,
            "files.trimTrailingWhitespace": True,
            "Lua.diagnostics.globals": ["fibaro", "QuickApp"],
            "Lua.runtime.version": "Lua 5.3",
            "[lua]": {
                "editor.insertSpaces": False,
                "editor.tabSize": 4
            }
        }
    }
    write_json_crlf(project_dir / workspace_name, workspace)
    _progress(f"  + {workspace_name}")

    vscode_settings = {
        "files.eol": "\r\n",
        "files.encoding": "utf8",
        "files.insertFinalNewline": True,
        "files.trimTrailingWhitespace": True,
        "Lua.diagnostics.globals": ["fibaro", "QuickApp"],
        "Lua.runtime.version": "Lua 5.3",
        "[lua]": {
            "editor.insertSpaces": False,
            "editor.tabSize": 4
        }
    }
    write_json_crlf(project_dir / ".vscode" / "settings.json", vscode_settings)
    write_json_crlf(project_dir / ".vscode" / "extensions.json", {
        "recommendations": [
            "sumneko.lua",
            "actboy168.lua-debug",
            "mhutchie.git-graph"
        ]
    })
    _progress("  + .vscode/settings.json, .vscode/extensions.json")

    # .gitignore for common local/generated artifacts
    gitignore_path = project_dir / ".gitignore"
    gitignore_entries = [
        "# OS / editor",
        ".DS_Store",
        "Thumbs.db",
        ".vscode/*",
        "!.vscode/settings.json",
        "!.vscode/extensions.json",
        "",
        "# Python",
        "__pycache__/",
        "*.py[cod]",
        "",
        "# FQA tool outputs",
        "*.fqa",
        "",
        "# Local fqa tool path (per developer, do not commit)",
        ".fqa-tool-path",
        ""
    ]
    if not gitignore_path.exists():
        gitignore_path.write_text("\r\n".join(gitignore_entries), encoding="utf-8", newline="")
        _progress("  + .gitignore")
    else:
        # Ensure .fqa-tool-path is ignored
        text = gitignore_path.read_text(encoding="utf-8")
        if ".fqa-tool-path" not in text:
            with open(gitignore_path, "a", encoding="utf-8", newline="") as f:
                f.write("\r\n# Local fqa tool path (per developer, do not commit)\r\n.fqa-tool-path\r\n")
            _progress("  + .gitignore (appended .fqa-tool-path)")

    # Per-developer tool path (do not overwrite if exists)
    tool_path_file = project_dir / ".fqa-tool-path"
    if not tool_path_file.exists():
        tool_path_file.write_text(_get_invocation_command(), encoding="utf-8", newline="")
        _progress("  + .fqa-tool-path")

    # Cross-platform pack script and wrappers (do not overwrite if exist)
    _write_fqa_pack_if_missing(project_dir)

    _progress(f"Updated into: {project_dir}" if update else f"Unpacked into: {project_dir}")


# ============================================================
# PACK
# ============================================================

def pack(project_dir, output_path=None, yes=False, silent=False):
    global SILENT
    SILENT = silent

    project_dir = Path(project_dir)

    original_path = project_dir / ".fqa_original.json"
    if not original_path.exists():
        print("Missing .fqa_original.json")
        return

    data = read_json(original_path)
    meta = read_json(project_dir / ".fqa_meta.json")

    schema = meta["_schema"]
    file_map = meta["_file_map"]

    files = extract_files(data, schema)

    # Replace Lua contents
    for f in files:
        original_name = f.get("name")

        for local_name, mapped_name in file_map.items():
            if mapped_name == original_name:
                if local_name == "main.lua":
                    lua_path = project_dir / "main.lua"
                else:
                    lua_path = project_dir / "files" / local_name

                if lua_path.exists():
                    content = lua_path.read_text(encoding="utf-8")
                    f["content"] = normalize_lua_for_pack(content)
                    _progress(f"  read {local_name}")

    default_name = f"{data.get('name', 'output')}.fqa"
    if output_path is not None:
        output_path = Path(output_path).resolve()
        if output_path.is_dir():
            output_path = output_path / default_name
    else:
        output_path = Path(default_name).resolve()

    if output_path.exists():
        if not yes and not _prompt_yes_no(f"Output '{output_path}' already exists. Overwrite it?"):
            print("Pack cancelled.")
            return
        if output_path.is_dir():
            print(f"Cannot overwrite '{output_path}': it is a directory.")
            return

    _progress(f"  writing {output_path.name}")

    use_original_format = "_original_newline" in meta and "_original_indent" in meta
    if use_original_format:
        _write_json(
            output_path,
            data,
            indent=meta["_original_indent"],
            newline=meta["_original_newline"]
        )
    else:
        write_json_crlf(output_path, data)

    _progress(f"Packed into: {output_path}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=f"FQA Tool v{VERSION}",
        epilog="Use '%(prog)s unpack -h' or '%(prog)s pack -h' to see all options for each command.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
        help="Show fqa version and exit",
    )
    sub = parser.add_subparsers(dest="command")

    unpack_parser = sub.add_parser("unpack")
    unpack_parser.add_argument("file")
    unpack_parser.add_argument("-o", "--output", dest="output_dir", metavar="DIR",
                               help="Directory to unpack into (default: current directory)")
    unpack_parser.add_argument("-y", "--yes", action="store_true", help="Overwrite without prompting")
    unpack_parser.add_argument("-silent", action="store_true", help="No progress output")
    unpack_parser.add_argument("--update", action="store_true",
                              help="Update existing folder in place (no delete); skip if folder missing")

    pack_parser = sub.add_parser("pack")
    pack_parser.add_argument("dir")
    pack_parser.add_argument("-o", "--output", dest="output_path", metavar="PATH",
                             help="Output path (file or directory)")
    pack_parser.add_argument("-y", "--yes", action="store_true", help="Overwrite without prompting")
    pack_parser.add_argument("-silent", action="store_true", help="No progress output")

    args = parser.parse_args()

    if args.command == "unpack":
        unpack(
            args.file,
            output_dir=getattr(args, "output_dir", None),
            yes=getattr(args, "yes", False),
            silent=getattr(args, "silent", False),
            update=getattr(args, "update", False),
        )

    elif args.command == "pack":
        pack(
            args.dir,
            output_path=getattr(args, "output_path", None),
            yes=getattr(args, "yes", False),
            silent=getattr(args, "silent", False),
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
