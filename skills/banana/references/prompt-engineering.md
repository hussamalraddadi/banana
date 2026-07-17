# Prompt Engineering for Gemini Image Models

The model renders what it can picture. Vague input does not produce a vague
image — it produces a confident, generic one. Every rule below exists to move
the prompt from *concept* to *scene*.

---

## The Five Components

Every brief is built from these, in this order. Missing components get filled
in by the model's defaults, and its defaults are averages.

| # | Component | Question it answers | Weak | Strong |
|---|---|---|---|---|
| 1 | **Subject** | Who or what, in physical detail? | "a woman" | "a woman in her late 30s, sharp jaw, hair pulled back, faint smile lines" |
| 2 | **Action** | What is happening right now? | "posing" | "mid-turn, reaching for a coat on the hook" |
| 3 | **Context** | Where, and when? | "in a room" | "a narrow Riyadh apartment kitchen, 7am, blinds half open" |
| 4 | **Composition** | Where is the camera? | "a photo" | "shot from waist height, 35mm, subject off-centre left, deep focus" |
| 5 | **Style** | What visual language, and lit how? | "nice lighting" | "muted documentary colour, hard side light from the window, deep shadow" |

**Lighting belongs to Style, and it does more work than any other single word.**
"Soft north-facing window light" and "hard midday sun" produce two different
photographs of the same subject.

---

## The Rule Behind the Rules

> **Describe what the camera sees. Never describe what the image means.**

The model cannot render meaning. It renders surfaces, light, and geometry.

| Never write | Because | Write instead |
|---|---|---|
| "a powerful ad about freedom" | Renders nothing. It is a brief for a human. | "a lone figure on an empty coastal road at dawn, arms loose at their sides" |
| "a professional-looking product shot" | "Professional" is not a visual property. | "product centred on brushed concrete, single softbox camera-left, long soft shadow" |
| "make it feel warm and inviting" | A feeling, not a scene. | "late-afternoon sun through a west window, amber cast on the far wall" |
| "a beautiful landscape" | Averages toward a postcard. | "basalt ridge under low cloud, wet rock, single shaft of light on the mid-slope" |

If a phrase in your prompt describes an *intention*, cut it and describe the
thing that would create that intention.

---

## Banned Vocabulary

These words were useful on older diffusion models. On Gemini they either do
nothing or actively pull the image toward generic stock imagery.

| Banned | Why | Use instead |
|---|---|---|
| `8K`, `4K`, `high resolution`, `HD` | Resolution is the `--resolution` flag. In the prompt it just adds noise. | `--resolution 4K` |
| `masterpiece`, `award-winning`, `best quality` | Quality is not a describable attribute. Zero effect. | A real reference: "Magnum photo essay" |
| `ultra-realistic`, `photorealistic` | The model already renders photographically. Redundant. | A camera and a lens |
| `highly detailed`, `intricate` | Applies detail nowhere in particular. | Name the detail: "condensation beading on the glass" |
| `trending on artstation` | Model-specific residue. Means nothing here. | An actual style: "gouache, visible brush texture" |

---

## Specificity Levers

Pull these in order. The first two carry the most weight.

### 1. Name a real camera and lens

This is the single highest-leverage move in photographic prompts. It carries
depth of field, distortion, compression, and colour rendering in three words.

| Write | You get |
|---|---|
| `Sony A7R IV, 85mm at f/1.4` | Compressed portrait, shallow focus, creamy background |
| `Canon EOS R5, 24mm at f/8` | Wide, deep focus, mild edge distortion |
| `iPhone 16 Pro, ultrawide` | Contemporary phone look, high micro-contrast |
| `Hasselblad 500CM, 80mm, Portra 400` | Medium-format film, soft grain, muted skin tones |
| `Leica M6, 35mm, Tri-X pushed to 1600` | Grainy monochrome reportage, hard contrast |

### 2. Anchor to a publication or genre

The model has strong priors for these. One phrase sets colour, framing, and
subject treatment at once.

`Vanity Fair editorial` · `National Geographic cover` · `Kinfolk interior feature`
· `Wallpaper* design spread` · `Bon Appétit food feature` · `Magnum documentary`
· `Architectural Digest` · `criterion-collection film still`

### 3. Add one micro-detail

One concrete, physical, slightly imperfect detail does more for realism than
ten adjectives. It works because perfection reads as synthetic.

Steam bending away from a cup · a fingerprint on brushed steel · dust caught
in a light shaft · a wrinkle where the sleeve was pushed up · chipped paint on
a door edge · condensation ring on wood

### 4. Use ALL CAPS for hard constraints

The model treats capitalised constraints as near-instructions:

```
MUST contain exactly three figures. The logo MUST be fully legible.
NO text anywhere in the frame.
```

### 5. For products, say "prominently displayed"

An unreliable but well-documented lever for keeping the product from getting
buried in its own scene.

---

## Templates

### Photographic / editorial

```
[Subject: age, build, expression, hair], wearing [garment with fabric and cut],
[specific action] in [location, time of day]. [One micro-detail].
Shot on [camera], [focal length] at [aperture]. [Light source, direction,
quality]. [Publication anchor].
```

### Product / commercial

```
[Product, named] on [surface material], [dynamic element: condensation,
motion, glow]. Logo prominently displayed. [Light setup: key, fill, direction].
[Background treatment]. Commercial product photography. [Publication anchor].
```

### Illustrated / stylised

```
A [medium: gouache, vector, cel-shaded] [format] of [subject].
[Line quality] with [shading method]. Palette: [3-4 colours].
Background: [treatment]. [Mood].
```

### Text-bearing assets

Keep rendered text **under 25 characters**. Beyond that, accuracy collapses.

```
A [asset type] with the text "[exact string]" in [font character].
[Placement, size, weight]. [Layout]. [Palette]. [Supporting elements].
```

### Architecture / interior

```
[Space type] in [architectural idiom], [key materials]. [Camera height and
angle], [focal length]. [Primary light source and direction], [secondary].
[One human trace: a folded throw, an open book]. [Publication anchor].
```

---

## When Google Blocks It

Gemini's output filter inspects the **generated image**, not just your prompt.
A clean prompt can still be blocked because of how the model interpreted it.
The filter cannot be turned off, and the only route forward is to change what
you are asking for.

**This is not about slipping content past a filter. It is about the fact that
most blocks are false positives on innocent requests, and the fix is to say
what you actually meant more precisely.**

| Blocked | Usually why | Rework |
|---|---|---|
| "a dog fighting" | "fighting" reads as violence | "two golden retrievers wrestling playfully on grass, tails up, action shot" |
| "surgery scene" | reads as gore | "a modern operating theatre seen from the observation gallery, empty, blue surgical lights" |
| "portrait of [real person]" | real public figures are restricted | "a distinguished man in his 60s, silver hair, navy suit, editorial studio portrait" |
| "a scary monster" | reads as horror/violence | "a creature from a folk tale, elongated limbs, bioluminescent markings, concept art" |
| "a soldier firing" | weapons plus violence | "a soldier standing watch at dawn, rifle slung on the shoulder, mist over the valley" |

**Four working strategies:**

1. **Shift the moment.** Before or after, instead of during. Aftermath instead of act.
2. **Reframe the genre.** Documentary, educational, or archival context instead of dramatic.
3. **Replace the identity.** An archetype instead of a named person.
4. **Move the concept, not the words.** If rephrasing fails twice, the issue is the
   subject itself. Change what is in the frame.

**If Gemini returns `PROHIBITED_CONTENT`, stop.** That is a category refusal,
not a phrasing problem. Retrying is a waste of quota. Tell the user plainly
that the concept is off-limits and offer a different one.

---

## Diagnosing a Weak Result

| Symptom | Cause | Fix |
|---|---|---|
| Generic, stock-looking | Prompt described intent, not scene | Add camera, lens, light direction, one micro-detail |
| Wrong mood entirely | Lighting unspecified | Name the source, direction, and hardness |
| Subject lost in the scene | No composition | State camera height, distance, and where the subject sits in frame |
| Text garbled | Over 25 characters, or unspecified font | Shorten it, describe the letterforms |
| Too clean, reads synthetic | No imperfection | Add one flaw: dust, a wrinkle, a smudge |
| Composition ignored | Competing instructions | Cut to one clear spatial idea |

**The first question when a result disappoints is always: did I describe a
scene, or did I describe an idea?**
