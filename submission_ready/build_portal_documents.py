"""
Typeset the cover letter, declarations and suggested-reviewer list as PDFs.

These three documents exist in three forms, and each form has a job:

  submission_compact/*.md          the authored source -- edit here
  submission_ready/portal_text/*.txt   Markdown stripped, CRLF, for pasting
                                       into the portal's own text fields
  submission_ready/portal_text/*.pdf   typeset, for attaching to the portal or
                                       sending to a co-author to read

Markdown is not a submission format: IEEE takes PDF, TXT or DOC. The .txt files
are produced by build_package.py; this script produces the .pdf files, using the
same tectonic binary that builds the manuscript, so there is no second toolchain.

The converter handles exactly the Markdown these three files use -- headings,
bullets, bold, code spans, horizontal rules -- and raises on anything it does
not recognise rather than silently dropping it.

Run:  python submission_ready/build_portal_documents.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(HERE, "portal_text")
TECTONIC = os.path.join(os.environ.get("LOCALAPPDATA", ""), "tectonic",
                        "tectonic.exe")

DOCS = [
    ("cover_letter.md", "Cover letter"),
    ("declarations.md", "Declarations"),
    ("suggested_reviewers.md", "Suggested and excluded reviewers"),
]

# Applied after LaTeX escaping, so the replacements survive intact.
UNICODE = [
    ("—", "---"),                    # em dash
    ("–", "--"),                     # en dash
    ("é", r"\'e"),                   # e acute
    ("è", r"\`e"),                   # e grave
    ("₁", r"\textsubscript{1}"),
    ("₂", r"\textsubscript{2}"),
    ("×", r"$\times$"),
    ("∪", r"$\cup$"),
    ("’", "'"),
    ("‘", "`"),
    ("“", "``"),
    ("”", "''"),
    (" ", "~"),
]

PREAMBLE = r"""\documentclass[11pt,letterpaper]{article}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[margin=1in]{geometry}
\usepackage{parskip}
\usepackage{enumitem}
% [hyphens] lets \url break the repository URL at its hyphens as well as its
% slashes. Without it that one unbreakable 58-character run overflows the
% margin by 405 pt in the cover letter.
\usepackage[hyphens]{url}
\usepackage[hidelinks]{hyperref}
\setlist[itemize]{topsep=2pt,itemsep=1pt,parsep=0pt,leftmargin=1.4em}
\setcounter{secnumdepth}{0}
\pagestyle{plain}
% Absorbs the last couple of points on an awkward line rather than letting a
% single hyphenated compound push into the margin.
\emergencystretch=2em
\begin{document}
"""


def esc(s):
    """Escape LaTeX specials in plain text."""
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}")):
        s = s.replace(a, b)
    s = s.replace("^", r"\textasciicircum{}").replace("~", r"\textasciitilde{}")
    # A literal " sets as a RIGHT double quote at both ends, so the opening
    # quote around the manuscript title in the cover letter faced the wrong way.
    s = re.sub(r'"([^"]*)"', r"``\1''", s)
    s = s.replace('"', "''")
    for a, b in UNICODE:
        s = s.replace(a, b)
    return s


URL_RE = re.compile(r"^(?:https?://|www\.)\S+$")


def inline(s):
    """Convert **bold**, `code` and URLs, escaping each run for its context."""
    out = []
    # Bare URLs are split out too, not just backticked ones -- \url is the only
    # thing that will break them across a line.
    for part in re.split(r"(\*\*.+?\*\*|`[^`]+`|https?://\S+)", s):
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(r"\textbf{" + esc(part[2:-2]) + "}")
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            inner = part[1:-1]
            # \url takes its argument verbatim, so it must not be escaped.
            out.append(r"\url{" + inner + "}" if URL_RE.match(inner)
                       else r"\texttt{" + esc(inner) + "}")
        elif URL_RE.match(part):
            trail = ""
            while part and part[-1] in ".,;:)":       # keep sentence punctuation
                trail = part[-1] + trail              # outside the link
                part = part[:-1]
            out.append(r"\url{" + part + "}" + esc(trail))
        else:
            out.append(esc(part))
    return "".join(out)


def to_latex(md, title):
    body, in_list = [], False

    def close_list():
        nonlocal in_list
        if in_list:
            body.append(r"\end{itemize}")
            in_list = False

    for raw in md.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            close_list()
            body.append("")
            continue

        if re.fullmatch(r"-{3,}", stripped):
            close_list()
            body.append(r"\medskip\hrule\medskip")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_list()
            level = len(m.group(1))
            cmd = {1: "section", 2: "subsection"}.get(level, "subsubsection")
            body.append("\\%s*{%s}" % (cmd, inline(m.group(2))))
            continue

        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if not in_list:
                body.append(r"\begin{itemize}")
                in_list = True
            body.append(r"  \item " + inline(m.group(1)))
            continue

        if stripped.startswith("|"):
            raise SystemExit(f"table found in {title}; the converter does not "
                             f"handle tables -- extend it rather than let the "
                             f"row vanish:\n  {stripped}")

        close_list()
        body.append(inline(stripped) + r"\\")

    close_list()
    # A trailing \\ on the line before a blank line is a LaTeX error, so drop
    # the break wherever a paragraph ends.
    txt = "\n".join(body)
    txt = re.sub(r"\\\\\n(\n|$)", r"\n\1", txt)
    txt = re.sub(r"\\\\\n(?=\\(?:section|subsection|subsubsection|medskip|begin))",
                 "\n", txt)
    return PREAMBLE + txt + "\n\\end{document}\n"


def main():
    if not os.path.isfile(TECTONIC):
        sys.exit(f"tectonic not found at {TECTONIC}")
    os.makedirs(OUT, exist_ok=True)

    for name, title in DOCS:
        src = os.path.join(REPO, "submission_compact", name)
        md = open(src, encoding="utf-8").read()
        tex = to_latex(md, title)

        build = tempfile.mkdtemp(prefix="doc_")
        stem = name[:-3]
        open(os.path.join(build, stem + ".tex"), "w",
             encoding="utf-8").write(tex)
        r = subprocess.run([TECTONIC, "-X", "compile",
                            os.path.join(build, stem + ".tex"),
                            "--outdir", build, "--keep-logs"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-2500:])
            sys.exit(f"compile FAILED for {name}")

        log = open(os.path.join(build, stem + ".log"), encoding="utf-8",
                   errors="replace").read()
        pages = int(re.search(r"Output written on .*?\((\d+) pages?",
                              log).group(1))
        overfull = len(re.findall(r"Overfull \\hbox \(", log))

        dst = os.path.join(OUT, stem + ".pdf")
        shutil.copy2(os.path.join(build, stem + ".pdf"), dst)
        shutil.rmtree(build, ignore_errors=True)
        print(f"  {stem + '.pdf':28s} {pages} page(s)  "
              f"{os.path.getsize(dst) / 1024:6.1f} kB"
              + (f"  {overfull} overfull box(es)" if overfull else ""))

    print(f"\nwrote {OUT}")
    print("  .pdf  attach to the portal, or send to a co-author")
    print("  .txt  paste into the portal's text fields (build_package.py)")


if __name__ == "__main__":
    main()
