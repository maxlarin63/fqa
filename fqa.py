import json
import argparse
import shutil
from pathlib import Path

VERSION = "1.0.0"


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


def unpack(fqa_path, output_dir=None):
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
        if not _prompt_yes_no(f"Folder '{project_dir}' already exists. Overwrite it?"):
            print("Unpack cancelled.")
            return
        if project_dir.is_dir():
            shutil.rmtree(project_dir)
        else:
            project_dir.unlink()

    project_dir.mkdir(parents=True, exist_ok=False)
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
        else:
            filename = name if "." in name else name + ".lua"
            (project_dir / "files" / filename).write_text(
                formatted, encoding="utf-8", newline=""
            )
            file_map[filename] = name

    meta = {
        "_schema": schema,
        "_file_map": file_map,
        "_original_newline": original_format["newline"],
        "_original_indent": original_format["indent"],
    }

    write_json_crlf(project_dir / ".fqa_meta.json", meta)

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

    # .gitignore for common local/generated artifacts
    gitignore_path = project_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_text = "\r\n".join([
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
            ""
        ])
        gitignore_path.write_text(gitignore_text, encoding="utf-8", newline="")

    print(f"Unpacked into: {project_dir}")


# ============================================================
# PACK
# ============================================================

def pack(project_dir):
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

    output_file = f"{data.get('name','output')}.fqa"
    output_path = Path(output_file)
    if output_path.exists():
        if not _prompt_yes_no(f"Output '{output_path}' already exists. Overwrite it?"):
            print("Pack cancelled.")
            return
        if output_path.is_dir():
            print(f"Cannot overwrite '{output_path}': it is a directory.")
            return

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

    print(f"Packed into: {output_file}")


# ============================================================
# CLI
# ============================================================

def main():
    print(f"FQA Tool v{VERSION}")
    parser = argparse.ArgumentParser(description=f"FQA Tool v{VERSION}")
    sub = parser.add_subparsers(dest="command")

    unpack_parser = sub.add_parser("unpack")
    unpack_parser.add_argument("file")
    unpack_parser.add_argument("-o", "--output", dest="output_dir", metavar="DIR",
                               help="Directory to unpack into (default: current directory)")

    pack_parser = sub.add_parser("pack")
    pack_parser.add_argument("dir")

    args = parser.parse_args()

    if args.command == "unpack":
        unpack(args.file, output_dir=getattr(args, "output_dir", None))

    elif args.command == "pack":
        pack(args.dir)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
