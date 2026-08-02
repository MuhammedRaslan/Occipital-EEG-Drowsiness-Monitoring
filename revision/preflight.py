"""Pre-flight validation for the Chemori revision.

No LaTeX toolchain is available, so this substitutes static analysis for a
compile. Checks LaTeX integrity, revision-markup safety, bibliography health,
cross-file consistency, and traceability against all 15 review items.
"""
import io, os, re, collections

ROOT = r"c:/Users/muham/Documents/Antigravity/DMS_Drafting/Pro-Active-Driver-Monitoring-System-Using-EEG"
TEX = os.path.join(ROOT, "submission/main.tex")
BIB = os.path.join(ROOT, "submission/references.bib")

tex = io.open(TEX, encoding="utf-8").read()
bib = io.open(BIB, encoding="utf-8").read()

FAIL, WARN = [], []


def sec(t):
    print("\n" + "=" * 72 + "\n" + t + "\n" + "=" * 72)


def ck(cond, ok, bad, hard=True):
    if cond:
        print("  PASS  " + ok)
    else:
        print(("  FAIL  " if hard else "  WARN  ") + bad)
        (FAIL if hard else WARN).append(bad)


def braces(s):
    """Count braces ignoring \{ \} escapes and % comments."""
    d = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            i += 2; continue
        if c == "%":
            j = s.find("\n", i); i = len(s) if j == -1 else j; continue
        if c == "{": d += 1
        elif c == "}": d -= 1
        i += 1
    return d


def arg_at(s, i):
    """Return (arg, end_index) for a brace group starting at s[i]=='{'."""
    d = 0
    j = i
    while j < len(s):
        if s[j] == "\\":
            j += 2; continue
        if s[j] == "{": d += 1
        elif s[j] == "}":
            d -= 1
            if d == 0:
                return s[i + 1:j], j + 1
        j += 1
    return None, len(s)


# ---------------------------------------------------------------- LaTeX
sec("1. LATEX INTEGRITY")
labels = re.findall(r"\\label\{([^}]*)\}", tex)
refs = re.findall(r"\\(?:ref|autoref|eqref)\{([^}]*)\}", tex)
dups = [k for k, v in collections.Counter(labels).items() if v > 1]
broken = sorted(set(r for r in refs if r not in set(labels)))
ck(not broken, "all %d \\ref targets resolve" % len(set(refs)), "broken refs: %s" % broken)
ck(not dups, "no duplicate labels (%d total)" % len(labels), "duplicate labels: %s" % dups)
ck(braces(tex) == 0, "braces balanced", "brace imbalance: %d" % braces(tex))

envs = collections.Counter()
for e in re.findall(r"\\begin\{([^}]*)\}", tex): envs[e] += 1
for e in re.findall(r"\\end\{([^}]*)\}", tex): envs[e] -= 1
bad = {k: v for k, v in envs.items() if v}
ck(not bad, "all %d environments balanced" % len(envs), "unbalanced: %s" % bad)

# ------------------------------------------------------- markup safety
sec("2. REVISION-MARKUP SAFETY  (soul \\hl cannot take math, \\cite, or \\par)")
ck("\\DeclareRobustCommand{\\add}" in tex and "\\DeclareRobustCommand{\\chg}" in tex,
   "markup macros are robust (safe in \\title/\\section moving arguments)",
   "markup macros use \\newcommand - will break in moving arguments")

spans = []
for m in re.finditer(r"\\(add|del|chg)\{", tex):
    a1, e1 = arg_at(tex, m.end() - 1)
    if a1 is None: continue
    args = [a1]
    if m.group(1) == "chg" and e1 < len(tex) and tex[e1] == "{":
        a2, e2 = arg_at(tex, e1); args.append(a2)
    spans.append((m.group(1), tex.count("\n", 0, m.start()) + 1, args))
print("  %d markup spans found" % len(spans))

bad_par, bad_math, bad_cite = [], [], []
for kind, ln, args in spans:
    for a in args:
        if a is None: continue
        if re.search(r"\n[ \t]*\n", a): bad_par.append((ln, kind))
        for mm in re.finditer(r"\\\(", a):
            pre = a[max(0, mm.start() - 60):mm.start()]
            if "\\mbox{" not in pre: bad_math.append((ln, kind)); break
        for mc in re.finditer(r"\\cite\{", a):
            pre = a[max(0, mc.start() - 12):mc.start()]
            if "\\mbox{" not in pre: bad_cite.append((ln, kind)); break
ck(not bad_par, "no markup span crosses a paragraph break",
   "paragraph break inside markup at lines %s" % sorted(set(l for l, _ in bad_par)))
ck(not bad_math, "all inline math inside markup is \\mbox-wrapped",
   "unwrapped math inside markup at lines %s" % sorted(set(l for l, _ in bad_math)))
ck(not bad_cite, "all \\cite inside markup is \\mbox-wrapped",
   "unwrapped \\cite inside markup at lines %s" % sorted(set(l for l, _ in bad_cite)))

# markup inside captions (fragile: moving argument + often contains math)
capbad = []
for m in re.finditer(r"\\caption\{", tex):
    a, _ = arg_at(tex, m.end() - 1)
    if a and re.search(r"\\(add|del|chg)\{", a):
        capbad.append(tex.count("\n", 0, m.start()) + 1)
ck(not capbad, "no markup inside \\caption", "markup in captions at lines %s" % capbad)

# math-mode environments must contain no markup
mathbad = []
for m in re.finditer(r"\\begin\{(equation|align|eqnarray)\*?\}(.*?)\\end\{\1\*?\}", tex, re.S):
    if re.search(r"\\(add|del|chg)\{", m.group(2)):
        mathbad.append(tex.count("\n", 0, m.start()) + 1)
ck(not mathbad, "no markup inside equation environments",
   "markup inside math at lines %s" % mathbad)

# ------------------------------------------------------------- bibliography
sec("3. BIBLIOGRAPHY")
cited = set()
for m in re.findall(r"\\cite\{([^}]*)\}", tex):
    cited |= {k.strip() for k in m.split(",") if k.strip()}
defined = {m.group(1).strip() for m in re.finditer(r"@\w+\{([^,]+),", bib)}
missing = sorted(cited - defined)
unused = sorted(defined - cited)
ck(not missing, "every \\cite key exists in the .bib (%d cited)" % len(cited),
   "cited but undefined (renders '[?]'): %s" % missing)
ck(len(cited) >= 35, "%d references will print (target >= 35)" % len(cited),
   "only %d references will print" % len(cited), hard=False)
ck(braces(bib) == 0, "bib braces balanced", "bib brace imbalance: %d" % braces(bib))

sensors = re.findall(r"@\w+\{([^,]+),(?:(?!\n\}).)*?journal\s*=\s*\{\{IEEE\} Sensors J\.\}", bib, re.S)
sens_cited = [k.strip() for k in sensors if k.strip() in cited]
ck(len(sens_cited) >= 2, "item 13: %d IEEE Sensors Journal papers cited (%s)"
   % (len(sens_cited), ", ".join(sens_cited)),
   "item 13 NOT met: only %d IEEE Sensors Journal papers cited" % len(sens_cited))

for ghost in ("nguyen2021biomed", "lin2020generalised"):
    ck(ghost not in cited, "fabricated entry '%s' is not cited" % ghost,
       "fabricated entry '%s' still cited" % ghost)
ck("and others}" not in bib.replace("% ", ""),
   "no remaining 'and others' truncations outside comments",
   "'and others' still present", hard=False)
print("  note: %d defined-but-uncited entries: %s" % (len(unused), ", ".join(unused) or "none"))

# ------------------------------------------------------- cross-file consistency
sec("4. CROSS-FILE CONSISTENCY")
TITLE = "Inter-Hemispheric Occipital Coherence for Subject-Independent Driver Drowsiness Monitoring and Advance Prediction"
for f in ("submission/cover_letter.md", "submission/README.md", "submission/references.bib"):
    t = io.open(os.path.join(ROOT, f), encoding="utf-8").read()
    ck(TITLE in t, "new title present in %s" % f, "new title MISSING from %s" % f)

for f in ("submission/main.tex", "submission/cover_letter.md",
          "submission/declarations.md", "submission/README.md"):
    t = io.open(os.path.join(ROOT, f), encoding="utf-8").read()
    ck("Chemori" in t, "Chemori present in %s" % f, "Chemori MISSING from %s" % f)

ck("Pal,~\\IEEEmembership{Member,~IEEE}" not in tex.replace("\\chg{Abhishek Rudra Pal,~\\IEEEmembership{Member,~IEEE},}", ""),
   "Pal's false IEEE grade removed from the rendered author block",
   "Pal still carries an IEEE membership grade")
ck(tex.count("\\IEEEmembership{Senior Member,~IEEE}") == 1,
   "exactly one IEEE grade claimed (Chemori, Senior Member)",
   "unexpected number of IEEEmembership claims")

cl = io.open(os.path.join(ROOT, "submission/cover_letter.md"), encoding="utf-8").read()
ck("avoids direct scalp-electrode contact with hair" not in cl,
   "cover letter no longer claims the headrest avoids hair contact",
   "cover letter still contains the reversed hair-contact claim")
ck("unspecified or per-subject-fitted behavioural thresholds" not in cl,
   "cover letter novelty paragraph matches the corrected manuscript claim",
   "cover letter still asserts the removed prior-literature claim")

# ------------------------------------------------------------- figures
sec("5. FIGURES")
figs = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", tex)
for f in figs:
    p = os.path.join(ROOT, "submission/figures", f)
    ck(os.path.exists(p), "%s exists (%d KB)" % (f, os.path.getsize(p) // 1024 if os.path.exists(p) else 0),
       "MISSING figure file: %s" % f)
ck(len(figs) == len(set(figs)), "no figure included twice", "duplicate includegraphics")

# ------------------------------------------------------- item traceability
sec("6. TRACEABILITY - CHEMORI'S 15 ITEMS")
checks = [
 (1,  "title reworked",            "Inter-Hemispheric Occipital Coherence" in tex),
 (2,  "Chemori added; Pal still corresponding", "Chemori" in tex and "Corresponding author: A.~R.~Pal" in tex),
 (3,  "bib normalised",            "Item 3 (A. Chemori review" in bib),
 (4,  "I+II merged",               "\\section{Related Work}" not in tex and "Prior Work on Single- and Few-Channel" in tex),
 (5,  "related work broadened",    len(cited) >= 35),
 (6,  "III.E lead-in added",       "The pipeline is assessed on two tasks" in tex),
 (7,  "sections renamed",          "Data, Signal Processing, and Evaluation Design" in tex),
 (8,  "Fig 2 legend fixed",        "upper left" in io.open(os.path.join(ROOT, "reviewer_revision_analysis.py"), encoding="utf-8").read()),
 (9,  "Fig 3 + script fixed",      "figsize=(7.6, 6.0)" in io.open(os.path.join(ROOT, "v17_roc.py"), encoding="utf-8").read()),
 (10, "future work added",         "textbf{Future work.}" in tex),
 (11, "IEEE Sensors keyword gone", "IEEE Sensors.\n\\end{IEEEkeywords}" not in tex),
 (12, "results restructured",      "Causal Smoothing and Operating-Point Selection" in tex),
 (13, "2x IEEE Sensors J cited",   len(sens_cited) >= 2),
 (14, "symbol collisions fixed",   "\\lambda \\, p_t" in tex and "\\eta=0.50" in tex),
 (15, "acronym list added",        "IEEEdescription" in tex and "PERCLOS" in tex),
]
for n, name, ok in checks:
    ck(ok, "item %-2d  %s" % (n, name), "item %-2d  %s  -- NOT SATISFIED" % (n, name))

# ------------------------------------------------------------------ summary
sec("SUMMARY")
print("  FAILURES : %d" % len(FAIL))
for f in FAIL: print("     - " + f)
print("  WARNINGS : %d" % len(WARN))
for w in WARN: print("     - " + w)
print()
print("  VERDICT  : " + ("READY TO PACKAGE" if not FAIL else "DO NOT PACKAGE - fix failures above"))
