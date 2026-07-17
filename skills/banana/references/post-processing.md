# Post-Processing Reference (ImageMagick)

Read this when an image has already been generated and needs resizing, cropping, background removal, format conversion, or compositing.

Audience: Claude. Every command below is meant to be run as-is after substituting paths.

---

## 0. Preflight — MANDATORY before any command

Never run an ImageMagick command without first proving the binary exists. Two generations coexist:

- **v7** → `magick` (single dispatcher: `magick`, `magick identify`, `magick montage`, ...)
- **v6** → separate binaries: `convert`, `identify`, `montage`, `composite`, `mogrify`

Run this shim once per session and reuse `$IM` / `$IDENTIFY`:

```bash
if command -v magick >/dev/null 2>&1; then
  IM="magick"; IDENTIFY="magick identify"; MONTAGE="magick montage"
elif command -v convert >/dev/null 2>&1; then
  IM="convert"; IDENTIFY="identify"; MONTAGE="montage"
else
  IM=""
fi
[ -n "$IM" ] && $IM -version | head -1
```

Prefer `magick` when both exist. `convert` still ships in many v7 builds as a deprecated alias, but some 7.1.x packages drop it — do not rely on it if `magick` is present.

### If neither binary exists

Do **not** silently skip post-processing, and do **not** run an installer on your own. Report exactly this to the user:

> ImageMagick is not installed, so I generated the image but could not post-process it.
> Install it on macOS with:
> `brew install imagemagick`
> Then tell me to re-run the post-processing step.

Then stop the post-processing step and still hand over the raw generated file path.

### Safety rules for every recipe below

| Rule | Reason |
| --- | --- |
| Output path ≠ input path | ImageMagick reads lazily; same-file writes can truncate or corrupt the original |
| Keep the original generated file | It is the only lossless master; all edits are derivatives |
| Quote geometry containing `^`, `!`, `>`, `<` | zsh (the default macOS shell) treats `^` as a glob operator with `EXTENDED_GLOB`, and `>`/`<` are redirections |
| Inspect before acting | See §1 |

---

## 1. Inspect first

```bash
$IDENTIFY -format '%f  %wx%h  %m  %[channels]  %b\n' input.png
```

| Token | Meaning |
| --- | --- |
| `%w` `%h` | pixel width / height |
| `%m` | format (PNG, JPEG, WEBP, ...) |
| `%[channels]` | e.g. `srgb` (no alpha) vs `srgba` (has alpha) |
| `%b` | file size on disk |

Use this to decide: does it already have alpha? Is it big enough for the target size (never upscale a generated image — regenerate at the larger size instead)?

---

## 2. Crop to exact dimensions, aspect preserved

The canonical three-part recipe (equivalent to CSS `object-fit: cover`):

```bash
$IM input.png -resize '1080x1080^' -gravity center -extent 1080x1080 +repage output.png
```

### Why `^` is required

| Geometry | Behaviour | Result for a 1600×900 source → 1080×1080 box |
| --- | --- | --- |
| `1080x1080` | Fit **inside** the box; both dimensions ≤ target | 1080×608, then `-extent` **pads** with background → letterboxed |
| `1080x1080^` | Box is a **minimum**; both dimensions ≥ target (fills/covers) | 1920×1080, then `-extent` **crops** the overflow → full bleed |
| `1080x1080!` | Force exact, ignore aspect | 1080×1080 **distorted** — never use on photos or faces |

So: `^` makes the image cover the box, `-gravity` decides which part survives, `-extent` performs the actual cut, `+repage` clears the leftover virtual-canvas offset (without it, some viewers and later operations honour a stale page geometry).

### Gravity choices

| Subject | Gravity |
| --- | --- |
| Generic / centred composition | `center` |
| Portraits, people, anything with heads | `north` |
| Product on a surface, reflections | `south` |

### Manual crop (known box)

```bash
$IM input.png -crop 800x600+120+40 +repage output.png
```

`+repage` is mandatory after `-crop`, otherwise the output keeps a `+120+40` canvas offset.

### Downscale only, never upscale

```bash
$IM input.png -resize '2048x2048>' output.png
```

`>` = shrink only if larger than the geometry. Quote it in zsh/bash.

---

## 3. Transparent background

Two approaches. They are not interchangeable — pick by how the image was produced.

### (A) Colour keying an already-generated image — `-transparent`

```bash
$IM input.png -alpha set -fuzz 12% -transparent white output.png
```

`-fuzz N%` widens the match tolerance around the target colour. Typical usable range: 8–20%.

**Real limitations — read before using:**

1. `-transparent` is **global**, not spatial. Every pixel within tolerance of white disappears, *including white pixels inside the subject*: shirt highlights, eye whites, teeth, product labels, specular highlights. The subject ends up with holes.
2. Raising `-fuzz` to catch the off-white background gradient eats more of the subject. Lowering it leaves a halo ring.
3. Anti-aliased edges are blends of subject and background, so they neither key out nor stay clean — you get a fringe.
4. Generated images rarely have a mathematically uniform background (soft gradients, JPEG artifacts, subtle vignetting), which forces exactly the fuzz trade-off above.

**Better variant when the background is contiguous** — flood-fill from the corners instead of matching globally. This only affects pixels *connected* to the seed point, so interior whites survive:

```bash
$IM input.png -alpha set -fuzz 15% -fill none \
  -draw 'color 0,0 floodfill' \
  output.png
```

Or with the dedicated operator, seeding each corner (repeat `-floodfill` per corner; `%[fx:w-1]` style offsets are not accepted here, so use literal coordinates):

```bash
W=$($IDENTIFY -format '%w' input.png); H=$($IDENTIFY -format '%h' input.png)
$IM input.png -alpha set -fuzz 15% -fill none \
  -floodfill +0+0 white \
  -floodfill "+$((W-1))+0" white \
  -floodfill "+0+$((H-1))" white \
  -floodfill "+$((W-1))+$((H-1))" white \
  output.png
```

Flood-fill fails when the background is visible in disconnected pockets (between an arm and the torso, inside a handle) — those pockets stay opaque and must be seeded individually.

**Use (A) when:** the image already exists and cannot be regenerated, the background is flat and clearly distinct from the subject, and the subject contains no large areas of the key colour.

### (B) Green-screen pipeline — generate for the key, then pull it

This is the accurate method. It moves the hard part from post-processing into the prompt.

**Step 1 — force the background at generation time.** Add to the prompt, explicitly:

> Subject isolated on a solid, uniform, fully saturated chroma-key green background (#00B140). Flat even studio lighting on the background, no gradient, no shadows cast on the background, no green light spill on the subject, no green in the subject's clothing or props.

Pure green `#00FF00` also works; `#00B140` is the broadcast chroma-key green and tends to be reproduced more consistently by generators. Use **magenta** (`#FF00FF`) instead if the subject is green (foliage, green garments).

**Step 2 — key it out:**

```bash
$IM input.png -alpha set -fuzz 25% -transparent '#00B140' output.png
```

A higher fuzz is safe here because no natural part of the subject is near that hue — which is the entire point.

**Step 3 — tighten the matte (removes the 1px fringe):**

```bash
$IM output.png -channel A -morphology Erode Disk:1 +channel output-clean.png
```

`Disk:1` eats roughly one pixel off the alpha edge. Use `Disk:2` only if a fringe survives; more than that visibly gnaws the silhouette.

**Step 4 — despill (only if a green rim remains on the subject).** Clamp green to the average of red and blue:

```bash
$IM output-clean.png -channel G -fx 'min(u,(r+b)/2)' +channel output-final.png
```

*Verify visually.* `-fx` is per-pixel and slow on large images, and this clamp shifts genuinely green pixels in the subject. If the subject legitimately contains green, skip this step and fix the fringe with `Erode` alone.

**Step 5 — verify alpha actually exists:**

```bash
$IDENTIFY -format '%[channels]\n' output-final.png   # expect: srgba
```

**Use (B) when:** you control generation, and you need a clean cutout for compositing, a logo, a product on a coloured layout, or any deliverable where fringing would be visible.

### Method comparison

| | (A) `-transparent` on an existing image | (B) Green-screen pipeline |
| --- | --- | --- |
| Requires regeneration | No | Yes |
| Interior same-colour pixels | Destroyed | Safe |
| Edge quality | Halo / fringe | Clean after `Erode` |
| Usable fuzz | 8–20%, fragile | ~25%, robust |
| Verdict | Fallback only | Default when you can regenerate |

### Flattening alpha back onto a colour

```bash
$IM input.png -background white -alpha remove -alpha off output.png
```

---

## 4. Format conversion

### PNG → WebP (lossy, default for web delivery)

```bash
$IM input.png -strip -quality 85 output.webp
```

### PNG → WebP (lossless — keeps alpha exact, still smaller than PNG)

```bash
$IM input.png -strip -define webp:lossless=true -define webp:method=6 output.webp
```

`webp:method` is 0–6; 6 is slowest and smallest.

### PNG → JPEG (alpha must be removed explicitly)

```bash
$IM input.png -background white -alpha remove -alpha off \
  -strip -quality 88 -sampling-factor 4:2:0 -interlace Plane output.jpg
```

Skipping `-alpha remove` on a transparent PNG produces an unpredictable (often black) background. Always state the background colour.

Use `-sampling-factor 4:4:4` instead when the image contains fine text, thin coloured lines, or hard colour edges — 4:2:0 smears chroma detail.

### JPEG/WebP → PNG

```bash
$IM input.jpg output.png
$IM input.webp output.png
```

### PNG re-compression without visual change

```bash
$IM input.png -strip -define png:compression-level=9 output.png
```

### Hard file-size target for JPEG

```bash
$IM input.png -strip -define jpeg:extent=300kb output.jpg
```

ImageMagick searches for the quality that lands under the limit. Confirm the result actually looks acceptable.

### Format selection

| Need | Format | Quality setting |
| --- | --- | --- |
| Transparency required | PNG, or lossless WebP | `png:compression-level=9` / `webp:lossless=true` |
| Photographic, web delivery, size matters | WebP (lossy) | `-quality 80–90` |
| Photographic, maximum compatibility (email, older tools, some CMS uploads) | JPEG | `-quality 82–90` |
| Master / archive / further editing | PNG | lossless |
| Flat colour, logos, screenshots, text | PNG | lossless (JPEG creates ringing artifacts on hard edges) |
| Platform upload where spec is unknown | JPEG or PNG | never WebP — support is inconsistent |

Do not re-encode a lossy file repeatedly. Always go back to the original PNG master and produce each derivative from it once.

---

## 5. Platform sizes

**Read this first:** platform specs change and are not versioned publicly. The table lists only sizes I hold with confidence, and flags the rest. When exactness matters (a paid ad, a client deliverable), tell the user to verify the current spec on the platform's own help page rather than trusting this table.

| Target | Pixels | Ratio | Confidence |
| --- | --- | --- | --- |
| Instagram square | 1080×1080 | 1:1 | Known |
| Instagram portrait | 1080×1350 | 4:5 | Known |
| Instagram Story / Reels | 1080×1920 | 9:16 | Known |
| Instagram landscape | 1080×566 | ~1.91:1 | **Verify current spec** (1080×608 at 16:9 is also in circulation) |
| YouTube thumbnail | 1280×720 | 16:9 | Known — min width 640, max file size 2 MB, JPG/PNG/GIF |
| Open Graph / Facebook shared link | 1200×630 | ~1.91:1 | Widely used OG default — **verify current spec** |
| LinkedIn shared image | 1200×627 | ~1.91:1 | **Verify current spec** |
| Twitter / X in-stream image | 1200×675 | 16:9 | **Verify current spec** — X has changed crop behaviour repeatedly |

Sizes I do **not** state: profile pictures, cover/banner images, ad-unit specs, carousel specs, and anything Story-sticker related. If asked, say so and point the user to the platform spec.

### Ready commands

```bash
# Instagram square 1:1
$IM input.png -resize '1080x1080^' -gravity center -extent 1080x1080 +repage -strip -quality 90 ig-square.jpg

# Instagram portrait 4:5
$IM input.png -resize '1080x1350^' -gravity north -extent 1080x1350 +repage -strip -quality 90 ig-portrait.jpg

# Instagram Story / Reels 9:16
$IM input.png -resize '1080x1920^' -gravity center -extent 1080x1920 +repage -strip -quality 90 ig-story.jpg

# Instagram landscape (verify spec)
$IM input.png -resize '1080x566^' -gravity center -extent 1080x566 +repage -strip -quality 90 ig-landscape.jpg

# LinkedIn shared image (verify spec)
$IM input.png -resize '1200x627^' -gravity center -extent 1200x627 +repage -strip -quality 90 linkedin.jpg

# Twitter / X in-stream (verify spec)
$IM input.png -resize '1200x675^' -gravity center -extent 1200x675 +repage -strip -quality 90 x-post.jpg

# Facebook / Open Graph (verify spec)
$IM input.png -resize '1200x630^' -gravity center -extent 1200x630 +repage -strip -quality 90 og.jpg

# YouTube thumbnail — must stay under 2 MB
$IM input.png -resize '1280x720^' -gravity center -extent 1280x720 +repage \
  -strip -define jpeg:extent=1900kb youtube-thumb.jpg
$IDENTIFY -format '%wx%h %b\n' youtube-thumb.jpg
```

Batch one master into a full set:

```bash
for spec in 1080x1080:ig-square 1080x1350:ig-portrait 1080x1920:ig-story; do
  dim="${spec%%:*}"; name="${spec##*:}"
  $IM input.png -resize "${dim}^" -gravity center -extent "$dim" +repage \
    -strip -quality 90 "${name}.jpg"
done
```

If the source is smaller than the target, `^` **upscales** and softens the image. Check dimensions with §1 first; if the source is too small, regenerate at the higher resolution rather than enlarging.

---

## 6. Web size optimization without visible loss

```bash
# JPEG
$IM input.png -strip -quality 85 -sampling-factor 4:2:0 -interlace Plane output.jpg

# WebP
$IM input.png -strip -quality 85 -define webp:method=6 output.webp

# PNG (keeps alpha)
$IM input.png -strip -define png:compression-level=9 output.png
```

| Flag | Effect |
| --- | --- |
| `-strip` | Removes EXIF, ICC profile, comments. Often 10–60 KB on generated images and zero visual cost — **but** it also removes the colour profile; if the image is not already sRGB, run `-colorspace sRGB` before `-strip` |
| `-quality 85` | Practical floor for photographic content before artifacts become visible at 100% zoom. Below ~75, banding and blocking appear in gradients and skies |
| `-interlace Plane` | Progressive JPEG — same bytes roughly, better perceived load |
| `-sampling-factor 4:2:0` | ~15–25% smaller; do not use on text or hard colour edges |

Safe order when the source may not be sRGB:

```bash
$IM input.png -colorspace sRGB -strip -quality 85 output.jpg
```

Always measure, never assume:

```bash
$IDENTIFY -format '%f %wx%h %b\n' input.png output.jpg
```

If the "optimized" file is not meaningfully smaller, keep the original and say so.

---

## 7. Compositing

### Side-by-side before / after

```bash
# Same height already
$IM before.png after.png +append comparison.png

# Different heights — normalize first, centre-align
$IM before.png after.png -resize x1024 -background white -gravity center +append comparison.png
```

`+append` = horizontal, `-append` = vertical.

### Side-by-side with a gutter and labels

```bash
$MONTAGE before.png after.png \
  -tile 2x1 -geometry '512x512+12+12' \
  -background white -label '%f' -pointsize 18 \
  comparison.png
```

`-geometry 'WxH+dx+dy'` sets the thumbnail box and the padding around each cell. `-label '%f'` prints the filename under each tile; replace with literal text per file if the filenames are meaningless.

### Variation grid (2×2, 3×3)

```bash
$MONTAGE v1.png v2.png v3.png v4.png \
  -tile 2x2 -geometry '640x640+8+8' -background '#ffffff' grid-2x2.png

$MONTAGE variation-*.png \
  -tile 3x3 -geometry '512x512+8+8' -background '#ffffff' grid-3x3.png
```

`-tile 3x` (rows omitted) lets the row count grow to fit however many inputs there are — use it when the count is unknown.

### Divider line between two images

```bash
$IM before.png -background '#000000' -splice 4x0 after.png +append comparison.png
```

`-splice 4x0` inserts a 4px background-coloured column on the left edge of the following image.

### Overlay one image on another (watermark, logo on a keyed cutout)

```bash
$IM background.png cutout.png -gravity southeast -geometry +40+40 -composite result.png
```

`-composite` uses the last two images on the stack. `-geometry +X+Y` is the offset **from the gravity corner**, not from the origin.

### Add a caption strip below

```bash
$IM input.png -background white -fill black -pointsize 28 \
  -gravity center label:'Before' -append output.png
```

---

## 8. Common errors and fixes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `magick: command not found` | v6-only install, or no ImageMagick | Fall back to `convert`; if neither, tell the user `brew install imagemagick` (§0) |
| `convert: command not found` on a v7 box | v7 dropped the `convert` alias | Use `magick` |
| `zsh: no matches found: 1080x1080^` | zsh glob-expands `^` | Quote it: `'1080x1080^'` |
| Output is letterboxed / padded instead of cropped | `^` missing from `-resize` | Add `^` (§2) |
| Output is stretched or squashed | `!` used in the geometry | Use `^` + `-extent`, not `!` |
| Image looks correct but has a stale offset, or later ops misalign | `-crop` / `-extent` without `+repage` | Append `+repage` |
| JPEG has a black background | Transparent PNG flattened without a stated background | `-background white -alpha remove -alpha off` before writing |
| Holes inside the subject after `-transparent white` | `-transparent` matches globally, not spatially | Use `-floodfill` from the corners, or regenerate on green screen (§3B) |
| White/coloured halo around the cutout | Anti-aliased edge pixels, fuzz too low | Raise fuzz slightly, then `-channel A -morphology Erode Disk:1 +channel` |
| Green rim on a keyed subject | Spill light from the green background | `Erode` the alpha; despill with the `-fx` clamp only if needed (§3B step 4) |
| `%[channels]` reports `srgb` after keying | Alpha channel was never enabled | Add `-alpha set` before `-transparent` |
| Enlarged image is soft / mushy | Source smaller than target; ImageMagick interpolated | Regenerate at the target size — no resampler recovers detail that was never there |
| `no decode delegate for this image format` | Missing delegate library (HEIC, AVIF, sometimes WebP on v6) | Check the real format with `$IDENTIFY`; on macOS reinstall via `brew install imagemagick`, which bundles the common delegates |
| `not authorized` (PDF, PS, EPS) | `policy.xml` security policy blocks that coder | Do not edit system policy silently — report it and convert from a raster source instead |
| Colours shift after conversion | Source was CMYK or carried a non-sRGB profile that `-strip` discarded | `-colorspace sRGB` **before** `-strip` |
| Output file is 0 bytes or the input is destroyed | Input and output paths are identical | Always write to a new filename |
| Quality flag seems ignored | `-quality` placed after the output filename, or applied to a lossless format | Settings must precede the output path; `-quality` on PNG controls compression/filter, not visual quality |
| Command hangs on a large image | `-fx` is per-pixel and interpreted | Restrict `-fx` to small images, or use `-morphology` / channel ops instead |
| `-fuzz` seems to do nothing | It was placed after `-transparent` | `-fuzz` is a setting: it must come **before** the operator it modifies |

---

## 9. Delivery checklist

Before reporting done:

1. `$IDENTIFY -format '%f %wx%h %m %[channels] %b\n'` on every output — confirm the dimensions, format, alpha, and size are what was asked for.
2. Confirm the original generated master still exists and was not overwritten.
3. If any platform size came from a **verify current spec** row (§5), say so explicitly instead of presenting it as authoritative.
4. If ImageMagick was unavailable, hand over the raw file and state that post-processing did not run.
