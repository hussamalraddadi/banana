#!/usr/bin/env python3
"""Turn a CSV of requests into a generation plan.

    batch.py --csv path/to/file.csv

Columns: prompt (required); ratio, resolution, model, preset (optional).

This script plans and prices — it does not generate. It prints JSON that Claude
reads before running generate.py per row, so the cost is visible and approved
before any money is spent.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from cost_tracker import estimate_one, pricing_caveat

DEFAULT_MODEL = "gemini-3.1-flash-image"
DEFAULT_RESOLUTION = "1K"
DEFAULT_RATIO = "1:1"

MAX_ROWS = 500


def main():
    parser = argparse.ArgumentParser(description="Plan a CSV batch of generations")
    parser.add_argument("--csv", required=True, help="Path to the CSV file")
    args = parser.parse_args()

    path = Path(args.csv).expanduser().resolve()
    if not path.exists():
        print(json.dumps({"error": True, "message": f"CSV not found: {path}"}))
        sys.exit(1)

    rows, problems = [], []
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "prompt" not in reader.fieldnames:
                print(json.dumps({
                    "error": True,
                    "message": "CSV needs a 'prompt' column. Found: "
                               f"{reader.fieldnames or '(no header)'}",
                }))
                sys.exit(1)

            for line_number, row in enumerate(reader, start=2):
                if len(rows) >= MAX_ROWS:
                    problems.append(f"Stopped at {MAX_ROWS} rows — the rest was ignored.")
                    break
                prompt = (row.get("prompt") or "").strip()
                if not prompt:
                    problems.append(f"Row {line_number}: empty prompt, skipped.")
                    continue
                rows.append({
                    "row": line_number,
                    "prompt": prompt,
                    "ratio": (row.get("ratio") or "").strip() or DEFAULT_RATIO,
                    "resolution": (row.get("resolution") or "").strip() or DEFAULT_RESOLUTION,
                    "model": (row.get("model") or "").strip() or DEFAULT_MODEL,
                    "preset": (row.get("preset") or "").strip() or None,
                })
    except (csv.Error, UnicodeDecodeError) as exc:
        print(json.dumps({"error": True, "message": f"Could not parse CSV: {exc}"}))
        sys.exit(1)

    if not rows:
        print(json.dumps({"error": True, "message": "No usable rows.", "problems": problems}))
        sys.exit(1)

    total = sum(estimate_one(r["model"], r["resolution"]) or 0 for r in rows)
    priced = all(estimate_one(r["model"], r["resolution"]) is not None for r in rows)

    print(json.dumps({
        "rows": rows,
        "total_count": len(rows),
        "estimated_cost_usd": round(total, 3) if priced else None,
        "cost_caveat": pricing_caveat(),
        "problems": problems,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
