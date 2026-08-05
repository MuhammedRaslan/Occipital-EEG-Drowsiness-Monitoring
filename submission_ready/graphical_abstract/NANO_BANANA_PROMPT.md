# Nano Banana prompt — IEEE Sensors graphical abstract

Paste the block below. Ask for **3:2 landscape** and the **highest resolution
offered**; it gets fitted to the IEEE 672 × 456 spec afterwards by
`fit_gagraphic.py`.

---

## The prompt

```
Create a professional scientific graphical abstract for a peer-reviewed IEEE
Sensors Journal paper on EEG-based driver drowsiness monitoring. Landscape
orientation, 3:2 aspect ratio, print-quality, pure white background.

=== VISUAL STYLE ===
Modern academic conference-poster infographic. Flat 2D vector illustration.
Crisp geometric shapes, thin clean outlines, generous white space, everything
sharply aligned to a grid. Absolutely no photorealism, no 3D, no bevels, no
drop shadows, no glow, no texture, no gradient backgrounds. It must look like
it was drawn in Adobe Illustrator by a journal's production department, not
like AI art.

Colour palette, use these and nothing else:
  periwinkle blue  #6C8FD8   title band, section header pills
  deep blue        #4E6FB4   arrows, box outlines
  signal blue      #0072B2   the O1 electrode and its EEG trace
  teal green       #009E73   the O2 electrode and its EEG trace
  vermilion        #D55E00   the drowsy state and the alert accent
  pale blue-grey   #F3F6FB   panel fills
  light blue-grey  #C3D0E6   panel borders
  near black       #1A1A1A   body text
  white                      text on blue, and the page background

Typography: a Times-like serif for the title band and the section header pills,
a clean sans-serif (Helvetica or Arial style) for every small label. All text
must be perfectly spelled, horizontal, and large enough to read. Never rotate,
warp, curve or stylise text.

=== LAYOUT: five zones, top to bottom ===

--- ZONE 1: TITLE BAND ---
A solid periwinkle blue #6C8FD8 rectangle spanning the full width, occupying
the top 14% of the image. Square corners, flush to the top, left and right
edges. Two lines of centred white serif text inside it:
  Line 1, large and bold:
    Pro-Active Driver Drowsiness Monitoring
  Line 2, roughly half that size, regular weight:
    Inter-hemispheric occipital coherence from two headrest electrodes

--- ZONE 2: THREE SECTION HEADER PILLS ---
Directly under the band, three horizontally centred rounded-rectangle "pills"
in periwinkle blue #6C8FD8, fully rounded ends, evenly spaced across the width,
each about 30% of the image width. Centred white bold serif text inside:
  left pill:    SENSING
  middle pill:  PIPELINE
  right pill:   RESULTS

--- ZONE 3: THREE PANELS ---
Below the pills, three rounded-corner panels aligned under their own pill,
filled pale blue-grey #F3F6FB with a thin #C3D0E6 border. They occupy the
middle 60% of the image height. Between panel 1 and 2, and between panel 2 and
3, place a single bold deep-blue #4E6FB4 right-pointing triangular arrow,
vertically centred, showing left-to-right flow.

PANEL 1 — SENSING. Two stacked elements.
  Upper element: a simple flat schematic of a human head seen from directly
  above, drawn as a clean dark-grey circle outline with a small triangular
  nose bump at the top. The nose marks the front of the head; the bottom of
  the circle is therefore the back of the head, the occiput.
  Two small filled circles represent occipital EEG electrodes. Place them ON
  the lower rim of the head circle, very close to the bottom outline, just
  left and right of the vertical centre line, symmetric about it. They must
  sit at the very back of the head, near the bottom edge, NOT in the middle
  of the scalp and NOT above the centre of the circle -- these are occipital
  sites and their position is anatomically meaningful. The left one is signal
  blue #0072B2 and is labelled "O1"; the right one is teal green #009E73 and
  is labelled "O2". Put each label just outside the head circle, beside its
  own electrode, not above it.
  A short horizontal dashed deep-blue line connects the two electrodes,
  representing the coupling between them. Directly beneath the head, a light
  grey rounded rectangle labelled "headrest" in small grey text, drawn so the
  back of the head rests against it, with the two electrodes sandwiched
  between the occiput and the headrest surface. This is a car seat headrest
  with the electrodes built into it.
  Lower element: two small EEG waveform panels stacked vertically. Each shows
  two overlaid squiggly EEG lines, one signal blue and one teal green, dense
  and irregular like real electroencephalogram traces, no axes, no gridlines.
  The upper waveform panel is labelled "awake" in small bold near-black text.
  The lower one is labelled "drowsy" in small bold vermilion text. Draw the
  drowsy traces as visibly higher-amplitude and slower than the awake traces.
  Beneath both, small bold deep-blue text:
    O1-O2 coherence falls with drowsiness

PANEL 2 — PIPELINE. Three white rounded-rectangle boxes with thin deep-blue
outlines, stacked vertically, evenly spaced, each spanning nearly the panel
width, joined by short downward-pointing deep-blue arrows. Small centred
near-black sans-serif text, exactly:
  box 1, three lines:
    10 lean features
    entropy, 1/f slope
    O1-O2 coherence
  box 2, two lines:
    shrinkage LDA
    p(drowsy)
  box 3, three lines:
    causal EMA smoother
    per-driver
    calibrated threshold

PANEL 3 — RESULTS. Two stacked elements, both made of flat text blocks. Do NOT
draw any chart, graph, plot, axis or curve anywhere in this panel.
  Upper element: a row of three small white rounded rectangles with thin
  deep-blue outlines. Each holds a large bold number above a small label:
    first box:   76.8%   with the label below it: F1
    second box:  76.6%   with the label below it: AUC
    third box:   66.1%   with the label below it: pooled F1
  Above that row, a small bold near-black centred caption:
    subject-independent LOSO
  Lower element: one wide white rounded rectangle with a thin vermilion
  #D55E00 outline, containing two centred lines. The first line very large and
  bold in vermilion:
    +31.7 min
  the second line small and near-black:
    median warning before behavioural onset

--- ZONE 4: FOOTER STRIP ---
A single full-width pale blue-grey #F3F6FB rounded rectangle with a thin
#C3D0E6 border across the bottom of the image, containing one centred line of
small near-black sans-serif text, exactly:
  31 subjects, two public datasets  |  85.7% of sessions warned early  |  56 ms per epoch

=== HARD CONSTRAINTS ===
Render only the text specified above, word for word, with exactly that spelling
and those digits. Do not invent, add, alter or round any number. Do not add any
title, caption, axis label, legend, arrow label, footnote, citation, author
name, institution, logo, watermark, signature or page number that is not listed
above. Do not add decorative icons such as cars, steering wheels, coffee cups,
warning triangles, brains, lightning bolts or sleeping faces. No human face, no
photograph, no realistic person. Keep every element inside the canvas with a
clear margin; nothing may be cropped by the edges or overlap another element.
Keep the composition uncluttered and strictly symmetrical about the vertical
centre line of the three panels.
```

---

## After it generates

1. **Proofread every character.** Image models drift on digits and hyphens.
   The values must read exactly: 76.8%, 76.6%, 66.1%, +31.7 min, 85.7%,
   56 ms, O1, O2. If any is wrong, regenerate rather than accepting it —
   these are peer-reviewed technical claims.
2. **Check nothing was invented** — no stray icons, no extra text, no chart.
3. **Fit it to the IEEE spec:**
   ```
   python fit_gagraphic.py <downloaded_image>
   ```
   That resizes to exactly 672 × 456 px, strips any alpha channel, and
   compresses under the 45 kB ceiling, writing `gagraphic.png`.
4. The caption in `gagraphic_caption.txt` (26 words) still applies unchanged.

## If it keeps failing

The usual failure is the model garbling small text. Two ways out:

- Regenerate the panels one at a time at large size and assemble them.
- Ask it for the schematic half only (title band, pills, panels 1 and 2, empty
  panel 3), then drop the real results in afterwards — that also removes the
  fabricated-data risk entirely.

Nothing here beats a fabricated chart past a reviewer, so if the model insists
on drawing one, delete it rather than shipping it.
