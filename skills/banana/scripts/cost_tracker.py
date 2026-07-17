#!/usr/bin/env python3
"""Track what image generation actually costs.

    cost_tracker.py log --model M --resolution R --prompt "..."
    cost_tracker.py summary
    cost_tracker.py today
    cost_tracker.py estimate --model M --resolution R --count N
    cost_tracker.py price --model M --resolution R --usd 0.06   # set a rate
    cost_tracker.py reset --confirm

Prices are NOT hardcoded here. They live in pricing.json next to this script,
and every rate carries a `verified` flag. An unverified or missing rate makes
this tool say "unknown" instead of printing a confident wrong number — a cost
tracker that guesses is worse than no cost tracker, because it gets trusted.

Entirely local. Never touches the network.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER_PATH = Path.home() / ".banana" / "costs.json"

# Rates you verify are YOUR data, so they live in your data directory — not
# inside the skill folder, which a reinstall wipes. The copy shipped alongside
# this script is only a template for first run.
PRICING_PATH = Path.home() / ".banana" / "pricing.json"
PRICING_TEMPLATE = Path(__file__).resolve().parent / "pricing.json"

BATCH_DISCOUNT = 0.5

EMPTY_LEDGER = {"total_cost": 0.0, "total_images": 0, "unpriced_images": 0,
                "entries": [], "daily": {}}


def load_pricing():
    """Read the user's rates, falling back to the shipped template on first run."""
    path = PRICING_PATH if PRICING_PATH.exists() else PRICING_TEMPLATE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        print(f"Warning: {path} is not valid JSON. Treating all rates as unknown.",
              file=sys.stderr)
        return {}


def pricing_caveat():
    """One line describing how much the current rates can be trusted."""
    data = load_pricing()
    models = data.get("models", {})
    if not models:
        return ("No rates configured — costs are not being tracked. Set one with: "
                "cost_tracker.py price --model M --resolution R --usd N")
    checked = data.get("verified_on")
    if checked:
        return (f"Rates verified against Google's published pricing on {checked}. "
                f"Some model/resolution pairs Google does not publish are reported "
                f"as unknown rather than estimated.")
    return "Rates present but not marked verified — confirm before trusting totals."


def estimate_one(model, resolution, batch=False):
    """Cost of one image in USD, or None if we genuinely do not know.

    Computed from token count, not a rounded per-image figure: Google publishes
    both, and the rounded ones drift (4K works out to $0.1512, is published as
    $0.151, and Vertex rounds it to $0.15). Over a large batch that gap matters.

    No fuzzy model matching, no falling back to a 'close enough' model's rate.
    Unknown means None, and every caller surfaces None as "unknown".
    """
    data = load_pricing()

    entry = data.get("models", {}).get(model)
    if entry:
        tokens = (entry.get("tokens_per_image") or {}).get(resolution)
        rate = entry.get("usd_per_million_output_tokens")
        if tokens is None or rate is None:
            return None
        cost = float(tokens) * float(rate) / 1_000_000
    else:
        # A flat rate the user set by hand via `price`.
        override = data.get("rates", {}).get(f"{model}:{resolution}")
        if not override or override.get("usd") is None:
            return None
        cost = float(override["usd"])

    discount = data.get("batch_discount", BATCH_DISCOUNT)
    return cost * discount if batch else cost


def load_ledger():
    if not LEDGER_PATH.exists():
        return dict(EMPTY_LEDGER)
    try:
        data = json.loads(LEDGER_PATH.read_text())
    except json.JSONDecodeError:
        print(f"Warning: ledger at {LEDGER_PATH} is corrupt. Starting a fresh one.",
              file=sys.stderr)
        return dict(EMPTY_LEDGER)
    for key, default in EMPTY_LEDGER.items():
        data.setdefault(key, default if not isinstance(default, (list, dict)) else type(default)())
    return data


def save_ledger(ledger):
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False))


def cmd_log(args):
    ledger = load_ledger()
    cost = estimate_one(args.model, args.resolution, args.batch)
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    ledger["entries"].append({
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": args.model,
        "resolution": args.resolution,
        "cost": cost,
        "prompt": args.prompt[:120],
    })
    ledger["total_images"] += 1

    if cost is None:
        ledger["unpriced_images"] += 1
    else:
        ledger["total_cost"] = round(ledger["total_cost"] + cost, 4)
        day = ledger["daily"].setdefault(today, {"count": 0, "cost": 0.0})
        day["count"] += 1
        day["cost"] = round(day["cost"] + cost, 4)

    save_ledger(ledger)
    print(json.dumps({
        "logged": True,
        "cost": cost,
        "total_cost": ledger["total_cost"],
        "total_images": ledger["total_images"],
        "unpriced_images": ledger["unpriced_images"],
    }, ensure_ascii=False))
    if cost is None:
        print(f"Note: no rate for {args.model}:{args.resolution} — logged without a cost.",
              file=sys.stderr)


def cmd_summary(args):
    ledger = load_ledger()
    print(f"Images generated: {ledger['total_images']}")
    print(f"Tracked cost:     ${ledger['total_cost']:.3f}")
    if ledger["unpriced_images"]:
        print(f"Untracked:        {ledger['unpriced_images']} image(s) had no known rate — "
              f"the real total is higher.")
    daily = ledger.get("daily", {})
    if daily:
        print("\nLast 7 days:")
        for day in sorted(daily, reverse=True)[:7]:
            d = daily[day]
            print(f"  {day}: {d['count']:3d} images   ${d['cost']:.3f}")
    print(f"\n{pricing_caveat()}")


def cmd_today(args):
    ledger = load_ledger()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day = ledger.get("daily", {}).get(today, {"count": 0, "cost": 0.0})
    print(f"Today ({today}): {day['count']} images, ${day['cost']:.3f}")


def cmd_estimate(args):
    per = estimate_one(args.model, args.resolution, args.batch)
    print(f"Model:      {args.model}")
    print(f"Resolution: {args.resolution}")
    print(f"Count:      {args.count}")
    if per is None:
        print("Cost/image: unknown — no rate configured for this model+resolution.")
        print(f"\n{pricing_caveat()}")
        return
    print(f"Cost/image: ${per:.4f}")
    print(f"Total est:  ${per * args.count:.3f}")
    if not args.batch:
        print(f"Batch est:  ${per * BATCH_DISCOUNT * args.count:.3f} (50% discount)")
    print(f"\n{pricing_caveat()}")


def cmd_price(args):
    """Record a rate you have confirmed yourself."""
    data = load_pricing()
    data.setdefault("rates", {})
    data["rates"][f"{args.model}:{args.resolution}"] = {
        "usd": args.usd,
        "verified": True,
        "source": args.source,
    }
    data["verified_on"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    PRICING_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRICING_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Set {args.model} @ {args.resolution} = ${args.usd:.4f}/image (verified).")
    print(f"Written to {PRICING_PATH} — this survives reinstalls.")


def cmd_reset(args):
    if not args.confirm:
        print("Error: pass --confirm to wipe the ledger.", file=sys.stderr)
        sys.exit(1)
    save_ledger(dict(EMPTY_LEDGER))
    print("Ledger reset.")


def main():
    parser = argparse.ArgumentParser(description="Image generation cost tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    p_log = sub.add_parser("log", help="Record one generation")
    p_log.add_argument("--model", required=True)
    p_log.add_argument("--resolution", required=True)
    p_log.add_argument("--prompt", required=True)
    p_log.add_argument("--batch", action="store_true")

    sub.add_parser("summary", help="Totals and last 7 days")
    sub.add_parser("today", help="Today only")

    p_est = sub.add_parser("estimate", help="Estimate a batch")
    p_est.add_argument("--model", required=True)
    p_est.add_argument("--resolution", required=True)
    p_est.add_argument("--count", required=True, type=int)
    p_est.add_argument("--batch", action="store_true")

    p_price = sub.add_parser("price", help="Set a verified rate")
    p_price.add_argument("--model", required=True)
    p_price.add_argument("--resolution", required=True)
    p_price.add_argument("--usd", required=True, type=float, help="Cost per image in USD")
    p_price.add_argument("--source", default="https://ai.google.dev/gemini-api/docs/pricing")

    p_reset = sub.add_parser("reset", help="Wipe the ledger")
    p_reset.add_argument("--confirm", action="store_true")

    args = parser.parse_args()
    {
        "log": cmd_log, "summary": cmd_summary, "today": cmd_today,
        "estimate": cmd_estimate, "price": cmd_price, "reset": cmd_reset,
    }[args.command](args)


if __name__ == "__main__":
    main()
