# Gemini Image Models — Routing, Cost, Limits

Every figure on this page was read directly from Google's published pricing
page on **17 July 2026**. Nothing here is inferred. Where Google publishes
nothing, this page says so instead of filling the gap.

> **Source:** https://ai.google.dev/gemini-api/docs/pricing (page last updated 2026-07-09)
> Re-read it before trusting these numbers months from now.

---

## There Is No Free Tier For Images

**Image generation is not available on Google's free tier.** The pricing page
prints "Not available" in the Free Tier column for every image model, on both
input and output. This is deliberate on Google's part — text models in the same
table say "Free of charge".

**Consequence:** billing must be enabled on the Google Cloud project or nothing
generates at all. If the user has not enabled it, `generate.py` returns HTTP 400
`FAILED_PRECONDITION`. That is not a bug and not retryable — tell them to enable
billing and set a spend cap.

---

## The Models

| Identifier | Known as | Output rate | Use for |
|---|---|---|---|
| `gemini-3.1-flash-image` | Nano Banana 2 | $60 / 1M tokens | **Default.** Most work. |
| `gemini-3.1-flash-lite-image` | Nano Banana 2 Lite | $30 / 1M tokens | Cheap iteration at 1K |
| `gemini-3-pro-image` | Nano Banana Pro | $120 / 1M tokens | Hardest asks: text rendering, complex composition |
| `gemini-2.5-flash-image` | Nano Banana (legacy) | $30 / 1M tokens | Legacy. Google recommends moving off it. |

### A note on the identifier

Google's pricing and image-generation docs (updated 2026-07-09) both use
`gemini-3.1-flash-image` with **no `-preview` suffix**, and list the model under
Stable rather than Preview. An older rate-limits page (2026-07-03) still shows
"Preview" display names.

This skill defaults to the un-suffixed identifier because it comes from the newer
and more authoritative pages. **Whether `-preview` still resolves as an alias was
not verified** — it would need a live `ListModels` call. If a request 404s on the
model name, that is the first thing to check.

---

## Cost Per Image

Cost is a function of **output tokens**, and token count varies by both model and
resolution. Compute rather than memorise: `tokens × rate ÷ 1,000,000`.

### `gemini-3.1-flash-image` — the default

| Resolution | Tokens | Standard | Batch (50%) |
|---|---|---|---|
| `512` | 747 | **$0.045** | $0.022 |
| `1K` | 1,120 | **$0.067** | $0.034 |
| `2K` | 1,680 | **$0.101** | $0.050 |
| `4K` | 2,520 | **$0.151** | $0.076 |

### `gemini-3-pro-image`

| Resolution | Tokens | Standard | Batch (50%) |
|---|---|---|---|
| `1K` | 1,120 | **$0.134** | $0.067 |
| `2K` | 1,120 | **$0.134** | $0.067 |
| `4K` | 2,000 | **$0.24** | $0.12 |

Note the curve is different: 1K and 2K cost the same, and 4K is 2,000 tokens
rather than 2,520. **Never carry a token count across models.**

### `gemini-3.1-flash-lite-image`

| Resolution | Tokens | Standard | Batch (50%) |
|---|---|---|---|
| `1K` | 1,120 | **$0.0336** | $0.0168 |
| `512` / `2K` / `4K` | *not published* | **unknown** | **unknown** |

### `gemini-2.5-flash-image` — legacy

| Resolution | Tokens | Standard | Batch (50%) |
|---|---|---|---|
| up to `1K` | 1,290 | **$0.039** | $0.0195 |
| above `1K` | *not published* | **unknown** | **unknown** |

### The gaps are real

Google does not publish token counts for the cells marked unknown. `pricing.json`
leaves them `null` and the cost tracker reports "unknown" rather than
extrapolating. Do not estimate them from a neighbouring model — `gemini-3-pro-image`
proves the curve differs per model.

---

## Routing

| Situation | Model | Resolution | Cost |
|---|---|---|---|
| Exploring an idea | `gemini-3.1-flash-lite-image` | `1K` | $0.034 |
| Quick draft | `gemini-3.1-flash-image` | `512` | $0.045 |
| **Most real work** | `gemini-3.1-flash-image` | `2K` | **$0.101** |
| Social / web delivery | `gemini-3.1-flash-image` | `1K` | $0.067 |
| Print, hero asset | `gemini-3.1-flash-image` | `4K` | $0.151 |
| Heavy text in image | `gemini-3-pro-image` | `2K`, `--thinking high` | $0.134 |
| Complex composition | `gemini-3-pro-image` | `2K` | $0.134 |

**Resolution is the cost dial.** 4K costs 3.4× what 512 does on the same model.
Draft at low resolution, then regenerate the winner high. Do not default to 4K
because it sounds better — most assets never need it.

---

## Aspect Ratios

Pass via `--aspect-ratio`. Rejected values fail before the request is sent.

| Ratio | For |
|---|---|
| `1:1` | Social square, avatar |
| `16:9` | Blog header, YouTube thumbnail, slide |
| `9:16` | Story, Reel, mobile full-screen |
| `4:5` | Instagram portrait |
| `3:4` · `2:3` | Portrait, poster, pin |
| `4:3` · `3:2` | Product, classic camera |
| `5:4` | Large-format landscape |
| `4:1` · `8:1` | Site banner strip |
| `21:9` | Cinematic ultrawide |

Resolution values are **case-sensitive**: `512`, `1K`, `2K`, `4K`. Lowercase is
rejected silently by the API, which is why `generate.py` constrains the choice.

---

## Rate Limits

**Google no longer publishes per-model RPM/RPD figures.** The rate-limits page
(2026-07-03) says limits "depend on a variety of factors (such as your usage
tier) and can be viewed in Google AI Studio".

What *is* published:

- **IPM (images per minute)** exists as a dimension for image models, but its
  values are not published.
- Spend limits per rolling 10-minute window: Tier 1 = $10 · Tier 2 = $200 · Tier 3 = $200
- Limits apply **per project**, not per API key. RPD resets at midnight Pacific.
- Priority tier gets 0.3× the standard rate limit.

**Do not hardcode any RPM/RPD number.** It would be a guess. On repeated 429s,
point the user at their AI Studio console.

---

## Batch API

**50% off, confirmed across every model** ($60→$30, $120→$60, $0.039→$0.0195).

Worth it for non-urgent bulk. For `gemini-3-pro-image` and `gemini-2.5-flash-image`,
the **Flex** tier gives the same 50%. Flex is not offered on the 3.1 Flash models.

---

## Flags

| Flag | Values | Notes |
|---|---|---|
| `--resolution` | `512` `1K` `2K` `4K` | The cost dial. Case-sensitive. |
| `--aspect-ratio` | see table | Validated before sending |
| `--model` | see identifiers | Defaults to `gemini-3.1-flash-image` |
| `--thinking` | `minimal` `low` `medium` `high` | Costs thinking tokens. Worth it for text and complex layout. |
| `--image-only` | flag | Skips the model's text commentary |

---

## What Was Not Verified

Stated plainly rather than papered over:

- Whether `gemini-3.1-flash-image-preview` still resolves. Needs a live API call.
- Token counts for the cells marked *not published* above.
- Per-image cost on the Priority tier for `gemini-3-pro-image` (only $216/1M is published).
- All RPM/RPD/IPM values.

If a number you need is not on this page, **say you do not know and point at the
console.** Do not estimate. A wrong cost figure gets trusted and turns into a
surprise bill.
