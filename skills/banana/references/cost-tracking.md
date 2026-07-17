# Cost Tracking

Every generated image costs real money. This skill tracks that, and refuses to
guess at it.

---

## The Design Rule

> **A cost tracker that guesses is worse than no cost tracker, because it gets
> trusted.**

Prices are therefore **not hardcoded in code**. They live in `pricing.json`, each
carrying a `verified` flag and a `verified_on` date. When a model/resolution pair
has no published figure, the tracker reports **`unknown`** rather than borrowing
a nearby number.

This is not caution for its own sake. The upstream project this skill descends
from priced `gemini-3.1-flash-image` at **$0.039/image** while its own model
reference said **~$0.067** and a third file conceded the real figure was probably
higher. Anyone trusting its totals was under-counting by roughly 40%. The tracker
here would have said "unknown" instead — correct, and far less expensive.

---

## Cost Is Computed From Tokens

Google publishes both a per-million-token rate and a token count per image, and
separately publishes rounded per-image prices. **The token count is the source of
truth**, because the rounded figures drift:

| | 4K on `gemini-3.1-flash-image` |
|---|---|
| Computed: 2,520 × $60 ÷ 1M | **$0.1512** |
| Google AI Studio prints | $0.151 |
| Vertex AI prints | $0.15 |

A tenth of a cent is nothing on one image and real money across ten thousand. So:

```
cost = tokens_per_image[resolution] × usd_per_million_output_tokens ÷ 1,000,000
```

**Token counts are per model.** `gemini-3-pro-image` charges 2,000 tokens for 4K
where `gemini-3.1-flash-image` charges 2,520, and prices 1K and 2K identically.
Never carry a token count from one model to another.

---

## Commands

```bash
# After every successful generation
cost_tracker.py log --model MODEL --resolution RES --prompt "short description"

# Before a batch — always show this to the user first
cost_tracker.py estimate --model MODEL --resolution RES --count N

# Totals and the last 7 days
cost_tracker.py summary

# Today only
cost_tracker.py today

# Record a rate you verified yourself
cost_tracker.py price --model MODEL --resolution RES --usd 0.067

# Wipe the ledger
cost_tracker.py reset --confirm
```

---

## Where Things Live

| Path | What | Survives reinstall? |
|---|---|---|
| `~/.banana/costs.json` | Your ledger | **Yes** |
| `~/.banana/pricing.json` | Rates you verified | **Yes** |
| `<skill>/scripts/pricing.json` | Shipped template | No — replaced on install |

Rates you confirm are **your** data, so they live in your directory. The copy
inside the skill folder is only a first-run template.

---

## When A Rate Is Unknown

`estimate_one()` returns `None`, and every command surfaces that as `unknown`
rather than a number.

`summary` then separates the two honestly:

```
Images generated: 40
Tracked cost:     $2.680
Untracked:        6 image(s) had no known rate — the real total is higher.
```

**If the user asks what something costs and no rate is set, say it is not
configured.** Do not estimate from memory, and do not quote a figure from a blog.
Point them at `cost_tracker.py price` and Google's pricing page.

---

## Verified Rates — 17 July 2026

Read from https://ai.google.dev/gemini-api/docs/pricing. Full tables and the
published gaps are in `references/gemini-models.md`.

| Model | Rate | 1K | 2K | 4K |
|---|---|---|---|---|
| `gemini-3.1-flash-image` | $60/1M | $0.067 | **$0.101** | $0.151 |
| `gemini-3-pro-image` | $120/1M | $0.134 | $0.134 | $0.24 |
| `gemini-3.1-flash-lite-image` | $30/1M | $0.0336 | unknown | unknown |
| `gemini-2.5-flash-image` | $30/1M | $0.039 | unknown | unknown |

**Batch API: 50% off, on every model.**

---

## No Free Tier

Image generation is **not available** on Google's free tier — the pricing page
says so explicitly for every image model. Billing must be enabled or nothing
generates.

Tell the user to set a **spend cap** in the Google console. This skill tracks
spending; it cannot stop it. Only Google can.

---

## Practical Habits

- **Draft cheap, finish expensive.** Iterate at `512` or `1K`, regenerate the
  winner at `2K` or `4K`. 4K costs 3.4× what 512 does.
- **Always estimate before a batch, and get approval.** Twenty 4K images is $3.02,
  not a rounding error.
- **Use Batch for anything not needed right now.** Half price, same output.
- **Log every generation.** An untracked image makes the whole ledger a lie.
