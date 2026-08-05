# Editing the graphical abstract yourself

Goal: replace the generated raster with **flat vector-style art**. That single
change removes every compression artifact, because flat art packs losslessly
into PNG. Reference point: the matplotlib build was 33 kB lossless PNG on the
same 672 × 456 canvas. The generated one needed JPEG and still came to 44 kB.

---

## 1. Pick a canvas

Design **large**, export small. Never design at final size.

| Canvas | Use |
|---|---|
| **2688 × 1824 px** | design here (4× final, exact 672:456 ratio) |
| 672 × 456 px | the literal IEEE specification — what you upload |

If your tool works in physical units, set **3.5 in × 2.38 in** and design at
300 dpi or higher. That is the same shape.

> Aspect ratio must stay **1.4737 : 1**. Your current source is 3:2, which is
> 1.8 % off — harmless, but if you rebuild, use the exact ratio and the fitter
> will not have to squeeze anything.

---

## 2. Tools that produce flat output

Any of these are fine. In rough order of ease:

- **Figma** (free, browser) — best choice. Frame at 2688 × 1824, export PNG 1×.
- **PowerPoint / Google Slides** — set slide size to 3.5 × 2.38 in, then
  "Save as Picture" at maximum resolution. Genuinely fine for this.
- **Inkscape** (free) or **Illustrator** — true vector, export PNG at 2688 wide.
- **Canva** — workable, but turn every effect off (see rule list below).

Do **not** edit the generated JPEG in Photoshop and re-save. Painting over
grain leaves grain; you inherit the same problem.

---

## 3. Rules that keep it flat

These are what make the file compress losslessly. Breaking any one of them
re-introduces thousands of colours and forces JPEG again.

- **Solid fills only.** No gradients, anywhere.
- **No drop shadows, glows, blurs, bevels or transparency effects.**
- **No textures, paper grain, noise or "realistic" shading.**
- **Real text objects**, typed in the tool. Never rasterised text, never text
  with effects applied.
- **Flat strokes** of uniform width and solid colour.
- Keep the palette small — roughly the nine colours already in use.

## 4. The palette

> **Colour coding is optional.** Measured on the current export, the two-colour
> scheme is fine: body text at 9.78 : 1 contrast (WCAG AAA) and a greyscale
> render that stays fully readable. IEEE asks for meaning to be carried by shape
> and position as well as colour, so fewer colours is a safe direction, not a
> compromise. Use the palette below if you are building fresh; do not spend time
> reintroducing colour into a design that already works without it.
>
> The one hard rule: **no small text in `#6C8FD8` blue.** It measures 3.26 : 1
> against the background, which passes only for large text. Blue is fine for the
> title band and the pills; body-size text must be the near-black or the brown.

```
#6C8FD8   periwinkle  title band, section pills
#4E6FB4   deep blue   arrows, box outlines
#0072B2   signal blue O1 electrode and its trace
#009E73   teal green  O2 electrode and its trace
#D55E00   vermilion   drowsy state, the +31.7 min accent
#F3F6FB   pale grey   panel fills
#C3D0E6   light grey  panel borders
#1A1A1A   near black  body text
#FFFFFF   white       background, text on blue
```

`#0072B2`, `#009E73` and `#D55E00` are Okabe-Ito — colour-blind safe, and they
stay distinguishable in greyscale. Keep them.

---

## 5. Minimum type sizes

This is where perceived quality actually comes from. Sizes below are **at the
final 672 × 456**; multiply by 4 if you design at 2688 × 1824.

| Element | Minimum at final size | At 4× canvas |
|---|---|---|
| Band title | 16 px | 64 px |
| Band subtitle | 9 px | 36 px |
| Pill labels (SENSING etc.) | 11 px | 44 px |
| Numbers (76.8 %, +31.7 min) | 14 px+ | 56 px+ |
| Box text, footer, captions | **9 px, hard floor** | 36 px |
| Anything smaller | delete it or promote it | — |

The current file has the footer at 13 px (fine) but "headrest" at 6 px and the
coherence caption at 8 px. Those two are what read as low quality.

**If something will not fit at 9 px, cut the words rather than shrink the
type.** Fewer words at a readable size always looks better than more words at
an unreadable one, and IEEE names too-small fonts as a top rejection cause.

---

## 6. Export, then fit

Export PNG at the design size — 2688 px wide, or whatever you built at. Do not
export JPEG; do not pre-shrink. Then:

```
python fit_gagraphic.py <your_export.png>
```

The script measures the artwork and picks the format for you:

- Flat art → **lossless PNG**, `gagraphic.png`, no artifacts.
- Still grainy → JPEG ladder, `gagraphic.jpg`, and it tells you so.

Watch the line it prints:

```
  NNNN unique colours -> flat vector art        <- what you want
  NNNNN unique colours -> generated art (grainy) <- still grainy, keep cleaning
```

Under about 5,000 unique colours means you succeeded. It hard-fails on wrong
dimensions and reports any size overage honestly rather than over-compressing.

---

## 7. Before uploading

- Open the output at 100 %, not zoomed. Read the footer and every small label.
- Re-read all eight values: **76.8 %, 76.6 %, 66.1 %, +31.7 min, 85.7 %,
  56 ms, O1, O2.** These are peer-reviewed claims.
- Check it in greyscale — IEEE converts to JPG and some readers print mono.
- Keep the electrodes on the **lower rim** of the head. They are occipital
  sites; mid-scalp is anatomically wrong and a reviewer will catch it.
- Filename must be `gagraphic`. Caption stays ≤ 30 words.
