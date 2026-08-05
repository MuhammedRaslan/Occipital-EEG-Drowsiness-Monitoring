r"""
Expand the revision macros the way \revmode{clean} will, then look for text
that the deletions broke.

Why this exists: in clean mode \del{...} removes its argument outright. If a
sentence was edited as "the old wording \del{, which was clumsy,} and so on",
the deletion can leave a doubled comma, a doubled space, a space before a full
stop, or a repeated word -- none of which any of the other checks would catch,
and all of which survive into the submitted PDF.

This is not a compile. It expands the three macros with a brace-matching
parser, strips the remaining LaTeX, and greps the result for damage.

Usage:
    python check_clean_render.py [--source submission_compact] [--show N]
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="submission_compact")
ap.add_argument("--show", type=int, default=6, help="max examples per issue")
args = ap.parse_args()

tex = open(os.path.join(REPO, args.source, "main.tex"), encoding="utf-8").read()


def read_group(s, i):
    """s[i] must be '{'. Return (inner, index_after_closing_brace)."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def expand(s):
    """Apply clean-mode semantics: add->keep, del->drop, chg{a}{b}->b."""
    out, i = [], 0
    while i < len(s):
        m = re.compile(r"\\(add|del|chg)\{").match(s, i)
        if not m:
            out.append(s[i])
            i += 1
            continue
        kind = m.group(1)
        a, j = read_group(s, m.end() - 1)
        if kind == "add":
            out.append(expand(a))
        elif kind == "del":
            pass                                  # deletions vanish
        else:                                     # chg{old}{new}
            if j < len(s) and s[j] == "{":
                b, j = read_group(s, j)
                out.append(expand(b))
        i = j
    return "".join(out)


clean = expand(tex)
clean = re.sub(r"(?<!\\)%.*", "", clean)          # drop comments

# keep only the body, and strip maths and the float bodies so their alignment
# characters do not masquerade as prose damage
body = clean
m = re.search(r"\\maketitle(.*?)\\end\{document\}", clean, re.S)
if m:
    body = m.group(1)
body = re.sub(r"\$[^$]*\$", " MATH ", body)
body = re.sub(r"\\begin\{(table|figure|tabular)\*?\}.*?\\end\{\1\*?\}", " FLOAT ",
              body, flags=re.S)

CHECKS = [
    ("space before punctuation", r"[A-Za-z0-9] +([,.;:])(?=\s|$)"),
    ("doubled punctuation", r"([,;:]) *\1|\.\s*\."),
    ("comma then full stop", r", *\."),
    # exclude the MATH/FLOAT placeholders this script substitutes in above,
    # otherwise two adjacent floats read as a repeated word
    ("repeated word", r"\b(?!MATH|FLOAT)([A-Za-z]{3,})\s+\1\b"),
    ("empty braces left behind", r"(?<!\\)\{\s*\}"),
    ("orphaned conjunction before punctuation", r"\b(and|or|but|which|that)\s*[,.]"),
    ("double space inside a sentence", r"[a-z]  +[a-z]"),
]

total = 0
for name, pat in CHECKS:
    hits = list(re.finditer(pat, body))
    if not hits:
        print(f"  PASS  {name}")
        continue
    total += len(hits)
    print(f"  WARN  {name}: {len(hits)}")
    for h in hits[:args.show]:
        ctx = re.sub(r"\s+", " ", body[max(0, h.start() - 55):h.end() + 55]).strip()
        print(f"          ...{ctx}...")
    if len(hits) > args.show:
        print(f"          ({len(hits) - args.show} more)")

n_add = len(re.findall(r"\\add\{", tex))
n_del = len(re.findall(r"\\del\{", tex))
n_chg = len(re.findall(r"\\chg\{", tex))
print(f"\n  revision macros expanded: {n_add} add, {n_del} del, {n_chg} chg")
print(f"  clean-mode body: {len(body.split())} words")
print(f"\n  {total} candidate issues -- each needs a human look; the patterns "
      f"flag plausible damage, not certain damage.")
sys.exit(0)
