#!/usr/bin/env python3
"""Brand and style presets — reusable visual identities.

    presets.py list
    presets.py show NAME
    presets.py create NAME [--colors "#hex,#hex"] [--style "..."] ...
    presets.py delete NAME --confirm

Entirely local. Reads and writes ~/.banana/presets/ and touches nothing else.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PRESETS_DIR = Path.home() / ".banana" / "presets"

# A preset name becomes a filename, so it is reduced to a known-safe charset
# rather than merely checked for "..".
#
# \w under re.UNICODE keeps letters and digits in ANY script — Arabic names work
# — while still dropping every path-dangerous character: / \ . : and null bytes.
# So "../../etc/passwd" collapses to "etcpasswd" and stays inside PRESETS_DIR,
# and "علامة-فاخرة" survives intact as itself.
UNSAFE_NAME_CHARS = re.compile(r"[^\w-]", re.UNICODE)
MAX_NAME_LENGTH = 64


def die(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def safe_name(raw):
    """Reduce an arbitrary string to a filename that cannot escape PRESETS_DIR."""
    cleaned = UNSAFE_NAME_CHARS.sub("", raw)[:MAX_NAME_LENGTH]
    if not cleaned:
        die("Preset name must contain letters, numbers, hyphens or underscores.")
    return cleaned


def preset_path(raw):
    return PRESETS_DIR / f"{safe_name(raw)}.json"


def load(raw):
    path = preset_path(raw)
    if not path.exists():
        die(f"Preset '{raw}' not found. Run 'presets.py list' to see what exists.")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        die(f"Preset file is corrupt: {path}")


def cmd_list(args):
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(PRESETS_DIR.glob("*.json"))
    if not files:
        print("No presets yet. Create one:")
        print('  presets.py create my-brand --colors "#0F2C4C,#C9A24B" --style "clean editorial"')
        return
    print(f"Presets ({len(files)}):\n")
    for path in files:
        try:
            data = json.loads(path.read_text())
            print(f"  {path.stem:24s} {data.get('description', '')}")
        except json.JSONDecodeError:
            print(f"  {path.stem:24s} (corrupt file)")


def cmd_show(args):
    print(json.dumps(load(args.name), indent=2, ensure_ascii=False))


def cmd_create(args):
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    path = preset_path(args.name)
    if path.exists() and not args.force:
        die(f"Preset '{args.name}' already exists. Pass --force to overwrite.")

    preset = {
        "name": safe_name(args.name),
        "description": args.description or f"Preset: {args.name}",
        "colors": [c.strip() for c in args.colors.split(",") if c.strip()],
        "style": args.style,
        "typography": args.typography,
        "lighting": args.lighting,
        "mood": args.mood,
        "default_ratio": args.ratio,
        "default_resolution": args.resolution,
    }
    path.write_text(json.dumps(preset, indent=2, ensure_ascii=False))
    print(f"Created {path}")
    print(json.dumps(preset, indent=2, ensure_ascii=False))


def cmd_delete(args):
    if not args.confirm:
        die("Pass --confirm to delete.")
    path = preset_path(args.name)
    if not path.exists():
        die(f"Preset '{args.name}' not found.")
    path.unlink()
    print(f"Deleted preset '{args.name}'.")


def main():
    parser = argparse.ArgumentParser(description="Manage brand/style presets")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List presets")

    p_show = sub.add_parser("show", help="Show one preset")
    p_show.add_argument("name")

    p_create = sub.add_parser("create", help="Create a preset")
    p_create.add_argument("name")
    p_create.add_argument("--colors", default="", help="Comma-separated hex colors")
    p_create.add_argument("--style", default="", help="Visual style")
    p_create.add_argument("--typography", default="")
    p_create.add_argument("--lighting", default="")
    p_create.add_argument("--mood", default="")
    p_create.add_argument("--description", default="")
    p_create.add_argument("--ratio", default="16:9")
    p_create.add_argument("--resolution", default="2K")
    p_create.add_argument("--force", action="store_true", help="Overwrite if it exists")

    p_delete = sub.add_parser("delete", help="Delete a preset")
    p_delete.add_argument("name")
    p_delete.add_argument("--confirm", action="store_true")

    args = parser.parse_args()
    {"list": cmd_list, "show": cmd_show, "create": cmd_create, "delete": cmd_delete}[args.command](args)


if __name__ == "__main__":
    main()
