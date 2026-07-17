# Presets — Reusable Visual Identities

A preset is a saved fragment of a brief: colours, style, typography, lighting,
mood. It exists so that twelve images made for one brand across six sessions
look like they came from one brand.

---

## The Problem It Solves

Without a preset, every image is re-invented from scratch. The user says
"another one for the same brand," and the model — given no palette, no light
direction, no stylistic anchor — falls back on its defaults, and its defaults
are averages. Image 1 is warm and soft. Image 2 is cool and hard. Both are
fine. Together they are not a brand.

A preset is the answer to *"what did we decide the last image looked like?"*
It is not a style transfer and it is not enforced by any script. It is a note
Claude reads and folds into the brief it writes.

---

## Storage

| Fact | Value |
|---|---|
| Directory | `~/.banana/presets/` |
| One preset | `~/.banana/presets/<safe-name>.json` |
| Format | JSON, UTF-8, `ensure_ascii=False` (Arabic survives intact) |
| Scope | Entirely local. `presets.py` reads and writes this directory and nothing else. |

Created on demand — `list` and `create` both `mkdir(parents=True, exist_ok=True)`.

---

## Schema

These are the exact keys `cmd_create` writes. There are nine, and no others.

| Key | Type | Set by | Example | Role in the prompt |
|---|---|---|---|---|
| `name` | string | positional arg, sanitised | `"aurum-dark"` | None. Filename and lookup key only. |
| `description` | string | `--description` | `"Dark luxury packaging line"` | None. Shown in `list` output so a human can pick. |
| `colors` | list of strings | `--colors` | `["#111111", "#F5F0E6"]` | Palette. Goes into the **Style** component as an explicit colour list. |
| `style` | string | `--style` | `"clean editorial"` | The visual-language anchor — medium, genre, publication reference. **Style** component. |
| `typography` | string | `--typography` | `"high-contrast serif, tight tracking"` | Letterform description. Only relevant when the image bears text. |
| `lighting` | string | `--lighting` | `"single softbox camera-left"` | **Style** component. Highest-leverage field in the file. |
| `mood` | string | `--mood` | `"restrained, still"` | **Style** component — but must be translated into visible scene facts before use. See below. |
| `default_ratio` | string | `--ratio` (default `"16:9"`) | `"16:9"` | Never in the prompt. A hint for the `--aspect-ratio` flag. |
| `default_resolution` | string | `--resolution` (default `"2K"`) | `"2K"` | Never in the prompt. A hint for the `--resolution` flag. |

### What the code does not do

Documented so it is not assumed:

- **No validation.** `--colors "not-a-colour"` is stored verbatim. Hex format is unchecked. `default_ratio: "banana"` is accepted and will be rejected later by `generate.py`'s `choices`.
- **Omitted flags become `""`, not absent.** Every string field defaults to the empty string, so a preset always has all nine keys. An empty field means "no opinion" — skip it, do not write "lighting: " into a brief.
- **`--colors ""` produces `[]`.** The split drops empty segments.
- **`description` defaults to `f"Preset: {name}"`** using the *raw* name, while `name` stores the *sanitised* one. They can differ.
- **`FIELDS` at module top is dead.** It is defined and never referenced. Do not treat it as a contract.

---

## Name Sanitisation

A preset name becomes a filename, so it is reduced to a known-safe charset
rather than merely checked for `..`.

```python
SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]")
MAX_NAME_LENGTH = 64
cleaned = SAFE_NAME.sub("", raw)[:MAX_NAME_LENGTH]
```

| Rule | Behaviour |
|---|---|
| Allowed characters | `a-z` `A-Z` `0-9` `_` `-` — everything else is **dropped, not replaced** |
| Order | Strip first, truncate second. A 70-char name with spaces may survive as fewer than 64 chars. |
| Length cap | 64 characters, hard truncation |
| Empty result | `presets.py create "علامة"` → all characters dropped → dies with *"Preset name must contain letters, numbers, hyphens or underscores."* |
| Collisions | Silent. `my.brand` and `my brand` both resolve to `mybrand.json`. |
| Non-Latin names | Cannot be preset names. Put them in `--description`, which is unsanitised. |

Overwrite and delete are both guarded:

```bash
presets.py create aurum-dark --style "..."          # dies if aurum-dark.json exists
presets.py create aurum-dark --style "..." --force  # overwrites, no diff, no backup
presets.py delete aurum-dark                        # dies: "Pass --confirm to delete."
presets.py delete aurum-dark --confirm              # unlinks the file
```

`--force` overwrites the whole file. It does not merge into the existing preset —
every field not passed on that command line reverts to its default. To change one
field, run `show`, then re-`create` with the full set.

---

## Merge Behaviour

> **The preset fills gaps. The user's explicit instruction always wins.**

There is no merge code. `generate.py` and `edit.py` do not know presets exist;
`batch.py` carries a `preset` column through into its plan JSON without
resolving it. **Merging happens in Claude's head, at brief-writing time.**
The rule below is a policy, not a function.

Resolution order for any single attribute:

| Priority | Source | Example |
|---|---|---|
| 1 | What the user said in this turn | "hard shadows" |
| 2 | The preset field | `lighting: "soft north window light"` |
| 3 | Nothing — omit it and let the prompt's own specificity carry | — |

**Worked example.** Preset `aurum-dark` holds `lighting: "soft north window light"`.
The user asks for *"the bottle on stone, hard shadows."*

```
Preset lighting : soft north window light
User instruction: hard shadows
Result          : hard shadows
```

The user overrode lighting and said nothing about colour or style, so
`colors` and `style` still apply. Overriding one field does not discard the
preset — it discards that field. Never argue for the preset value, never
average the two ("soft light with hard shadows" is incoherent and the model
will render one of them at random), and do not mention the override unless the
user is likely to have forgotten the preset had an opinion.

An empty preset field is not a value. It is silence. Skip it.

---

## Injection Into the Five Components

See `references/prompt-engineering.md` for the components themselves. Presets
touch **one** of the five.

| Component | Fed by | Why |
|---|---|---|
| 1 Subject | — | The user's request. A preset never knows what is in frame. |
| 2 Action | — | The user's request. |
| 3 Context | — | The user's request. |
| 4 Composition | — | The user's request. `default_ratio` shapes the flag, not the sentence. |
| 5 **Style** | `colors` · `style` · `typography` · `lighting` · `mood` | This is what a preset *is*: the visual language and the light. |

The two `default_*` fields bypass the prompt entirely and become CLI flags:

```bash
generate.py --prompt "..." --aspect-ratio "$default_ratio" --resolution "$default_resolution"
```

Nothing reads them for you. If the preset says `16:9` and you do not pass
`--aspect-ratio 16:9`, `generate.py` uses its own default of `1:1`. The
preset's silent default of `16:9` and `generate.py`'s `1:1` do not agree —
pass the flag explicitly.

### Writing the Style component from a preset

Do not paste the JSON into the prompt. Translate it into scene language, and
obey the rule behind the rules: *describe what the camera sees, never what the
image means.*

Given:

```json
{
  "colors": ["#111111", "#F5F0E6", "#8A7A5C"],
  "style": "still-life, Wallpaper* design spread",
  "lighting": "single hard key camera-left, deep falloff",
  "mood": "restrained, expensive"
}
```

Wrong — the fields transcribed, `mood` left as an abstraction the model cannot render:

```
...in the style of restrained, expensive. Colors: #111111, #F5F0E6, #8A7A5C. Lighting: soft.
```

Right — the same fields as a scene:

```
...Palette held to near-black, warm bone white, and muted brass. Single hard
key camera-left, deep falloff into black on the right third. Still-life
treatment, Wallpaper* design spread. One micro-detail: a fingerprint on the
brushed cap.
```

`mood: "restrained, expensive"` did not survive as words — it survived as
falloff, palette discipline, and a tight frame. That is the correct handling.
`typography` enters only when the image carries text, and then it describes
letterforms, keeping the rendered string under 25 characters.

---

## Examples

Three shapes that cover most requests. Names and palettes are generic.

### Dark luxury

```bash
presets.py create luxe-noir \
  --description "Dark luxury — packaging and still life" \
  --colors "#111111,#F5F0E6,#8A7A5C" \
  --style "still-life product photography, Wallpaper* design spread, matte surfaces, negative space" \
  --typography "high-contrast serif, wide letter-spacing, small caps" \
  --lighting "single hard key camera-left, deep falloff to black, no fill" \
  --mood "restrained, unhurried, expensive" \
  --ratio "4:5" \
  --resolution "4K"
```

### Clean tech

```bash
presets.py create bright-systems \
  --description "Clean tech — UI, hardware, docs" \
  --colors "#FFFFFF,#1B1F24,#3A7BFD" \
  --style "flat vector, geometric, generous whitespace, thin uniform strokes" \
  --typography "geometric sans, medium weight, tight tracking, lowercase" \
  --lighting "flat even ambient, no cast shadow" \
  --mood "precise, legible, calm" \
  --ratio "16:9" \
  --resolution "2K"
```

### Editorial fashion

```bash
presets.py create atelier-press \
  --description "Editorial fashion — lookbook and campaign" \
  --colors "#EDE7E1,#2B2B2B,#B8442F" \
  --style "Vanity Fair editorial, Hasselblad 500CM 80mm on Portra 400, soft grain" \
  --typography "condensed serif headline, generous leading" \
  --lighting "north-facing window, camera-right, soft falloff, one bounce card" \
  --mood "poised mid-motion, caught not posed" \
  --ratio "2:3" \
  --resolution "4K"
```

Read one back before using it:

```bash
presets.py show atelier-press
```

---

## When Not to Use a Preset

| Situation | Why |
|---|---|
| Exploration | The user is looking for a direction. A preset pre-decides the answer and every option comes back the same. Generate wide, then save the winner as a preset. |
| Deliberate departure | "Same product, but bright and playful this time." The request is the brief. Do not reach for the preset and do not warn them off it. |
| One-off, no reuse | A preset that is used once is overhead. Write the brief. |
| Preset fights the subject | `lighting: "single hard key"` on a request for an overcast landscape. Drop the conflicting field, keep the rest. |
| No preset exists | Do not invent one to fill the gap. Ask, or write the brief from the request alone. |

A preset is a memory of a decision, not a rule. When the user's request and the
preset disagree, the request is the newer decision.
