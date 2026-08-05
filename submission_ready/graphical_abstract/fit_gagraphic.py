"""
Fit an image to the IEEE Sensors Journal graphical-abstract specification.

From the IEEE Sensors Council "Graphical Abstract Instructions":

    Dimensions:          672 pixels x 456 pixels (3.5" x 2.38")
    File Types:          JPG, TIFF, PNG, GIF, Word, PDF, PS, EPS, BMP
    Recommended File Size: < 45 kB
    NOTE: All images for the Graphical Abstract will be converted to JPG.

Note the wording. The dimensions are a specification and this script enforces
them exactly. The 45 kB figure is explicitly *recommended*, so it is treated as
a target to approach, not a wall to destroy the artwork against -- an
unreadable 44 kB file fails the actual requirement, which is that the graphical
abstract be a legible visual summary and survive peer review as technical
content.

Format is chosen by what the artwork is:

  * Flat vector-style art (a matplotlib build) is a handful of solid colours
    and packs losslessly into PNG well under the target.
  * Generated art carries diffusion grain across every region -- tens of
    thousands of unique colours in what looks like flat fill. PNG cannot pack
    that, so it goes out as JPEG, which is what IEEE converts it to anyway, so
    nothing extra is lost by encoding it that way now.

Usage:
    python fit_gagraphic.py path/to/image.png
    python fit_gagraphic.py path/to/image.png --target-kb 45 --min-quality 80
    python fit_gagraphic.py path/to/image.png --no-crop   # squeeze, never crop
    python fit_gagraphic.py path/to/image.png --no-clean  # skip denoising
"""

import argparse
import io
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(HERE, "gagraphic.png")
OUT_JPG = os.path.join(HERE, "gagraphic.jpg")

TARGET_W, TARGET_H = 672, 456
TARGET_AR = TARGET_W / TARGET_H              # 1.4737
SQUEEZE_TOLERANCE = 0.06                     # accept up to 6 % aspect distortion
NOISY_COLOURS = 5000                         # above this, treat as generated art

ap = argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--target-kb", type=float, default=45.0)
ap.add_argument("--min-quality", type=int, default=80,
                help="lowest JPEG quality allowed; below this, legibility of "
                     "small labels starts to go before the file does")
ap.add_argument("--no-crop", action="store_true")
ap.add_argument("--no-clean", action="store_true")
args = ap.parse_args()

MAX_BYTES = args.target_kb * 1024

if not os.path.isfile(args.source):
    sys.exit(f"no such file: {args.source}")


def nbytes(img, fmt, **kw):
    b = io.BytesIO()
    img.save(b, format=fmt, **kw)
    return len(b.getvalue())


im = Image.open(args.source)
print(f"source: {im.size[0]}x{im.size[1]} px, mode={im.mode}, "
      f"aspect {im.size[0] / im.size[1]:.3f} (target {TARGET_AR:.3f})")

# --- flatten any transparency onto white -------------------------------------
if im.mode in ("RGBA", "LA", "P"):
    rgba = im.convert("RGBA")
    flat = Image.new("RGB", rgba.size, "white")
    flat.paste(rgba, mask=rgba.split()[-1])
    im = flat
else:
    im = im.convert("RGB")

# --- is this flat art or generated art? --------------------------------------
# Measured on the SOURCE, before any resize. Downscaling flat art with Lanczos
# legitimately invents intermediate tones along every edge -- that is
# anti-aliasing, not grain -- so counting colours after the resize misreads
# clean vector art as noisy and triggers a smoothing pass that blurs it.
src_colours = len(np.unique(np.asarray(im).reshape(-1, 3), axis=0))
noisy = src_colours > NOISY_COLOURS
print(f"  source has {src_colours} unique colours -> "
      f"{'generated art (grainy)' if noisy else 'flat vector art'}")

# --- aspect ------------------------------------------------------------------
src_ar = im.size[0] / im.size[1]
distortion = abs(src_ar - TARGET_AR) / TARGET_AR
if distortion > SQUEEZE_TOLERANCE and not args.no_crop:
    w, h = im.size
    if src_ar > TARGET_AR:
        nw = int(round(h * TARGET_AR))
        box = ((w - nw) // 2, 0, (w - nw) // 2 + nw, h)
    else:
        nh = int(round(w / TARGET_AR))
        box = (0, (h - nh) // 2, w, (h - nh) // 2 + nh)
    print(f"  aspect {distortion * 100:.1f} % off target -- centre-cropping to "
          f"{box[2] - box[0]}x{box[3] - box[1]}; check nothing was cut.")
    im = im.crop(box)
else:
    print(f"  aspect within tolerance ({distortion * 100:.1f} %) -- direct resize.")

im = im.resize((TARGET_W, TARGET_H), Image.LANCZOS)

# --- denoise, grainy sources only --------------------------------------------
if noisy and not args.no_clean:
    # Snap near-white to pure white and lightly smooth, to strip the
    # generator's grain out of what should be solid fill. Never applied to flat
    # art: the smoothing would blur clean edges for no benefit.
    arr = np.asarray(im).astype(int)
    before = len(np.unique(arr.reshape(-1, 3), axis=0))
    arr[arr.min(axis=2) >= 244] = 255
    im = Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.SMOOTH)
    after = len(np.unique(np.asarray(im).reshape(-1, 3), axis=0))
    print(f"  denoised: {before} -> {after} unique colours at final size")
else:
    print(f"  no denoising: flat art, edges left sharp")

# --- format ladder -----------------------------------------------------------
chosen = None

if not noisy:
    n = nbytes(im, "PNG", optimize=True)
    if n <= MAX_BYTES:
        chosen = (OUT_PNG, "PNG", {"optimize": True}, n, "PNG, lossless")
    if chosen is None:
        for c in (256, 192, 128, 96, 64):
            q = im.quantize(colors=c, method=Image.MEDIANCUT,
                            dither=Image.Dither.NONE)
            n = nbytes(q, "PNG", optimize=True)
            if n <= MAX_BYTES:
                im = q
                chosen = (OUT_PNG, "PNG", {"optimize": True}, n,
                          f"PNG, {c}-colour palette")
                break

if chosen is None:
    # Search quality first, then chroma subsampling. Glyph sharpness lives in
    # the luma channel, so trading chroma resolution away costs far less
    # legibility than dropping quality does -- 4:2:0 at q80 reads better than
    # 4:4:4 at q70 and is smaller.
    SS = {0: "4:4:4", 1: "4:2:2", 2: "4:2:0"}
    best = None
    for q in (95, 92, 90, 88, 85, 82, 80, 78, 75, 72):
        row = []
        for ss in (0, 1, 2):
            n = nbytes(im, "JPEG", quality=q, optimize=True, subsampling=ss)
            row.append(f"{SS[ss]} {n / 1024:5.1f}")
            if best is None or q >= args.min_quality:
                best = (q, ss, n)
            if n <= MAX_BYTES:
                best = (q, ss, n)
                break
        print(f"  JPEG q{q}: " + "  ".join(row))
        if best[2] <= MAX_BYTES or q <= args.min_quality:
            break
    q, ss, n = best
    chosen = (OUT_JPG, "JPEG",
              {"quality": q, "optimize": True, "subsampling": ss}, n,
              f"JPEG, quality {q}, {SS[ss]} chroma")

path, fmt, kw, size, note = chosen
im.save(path, format=fmt, dpi=(192, 192), **kw)
size = os.path.getsize(path)

# never leave both formats behind: the upload slot takes one file
stale = OUT_JPG if path == OUT_PNG else OUT_PNG
if os.path.exists(stale):
    os.remove(stale)

final = Image.open(path)
dims_ok = final.size == (TARGET_W, TARGET_H)
size_ok = size <= MAX_BYTES

print(f"\nwrote {path}")
print(f"  {final.size[0]}x{final.size[1]} px, mode={final.mode}, "
      f"{size / 1024:.1f} kB -- {note}")
print(f"  dimensions 672x456 (specification) : {'OK' if dims_ok else 'FAIL'}")
print(f"  size < {args.target_kb:.0f} kB (recommendation): "
      f"{'OK' if size_ok else f'over by {(size - MAX_BYTES) / 1024:.0f} kB'}")

if not dims_ok:
    sys.exit("dimensions are a specification, not a recommendation -- do not upload")
if not size_ok:
    print("\n  The size line is IEEE's word 'Recommended', not a limit, and they")
    print("  re-encode every graphical abstract to JPG on ingest. Compressing")
    print("  further would blur the smallest labels, which fails a requirement")
    print("  that is real. Shipping slightly over is the better trade.")

print("\nProofread the rendered text before uploading:")
print("  76.8%   76.6%   66.1%   +31.7 min   85.7%   56 ms   O1   O2")
print("  These are peer-reviewed claims; a mistyped digit is a data error.")
