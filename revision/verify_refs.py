"""Verify every entry in references.bib against Crossref.

Reports, per entry: whether Crossref finds a title-matching record, and any
disagreement in author family names, venue, volume, issue, pages or year.
Writes a JSON report. Makes no changes to the .bib.
"""
import io, re, json, time, difflib, urllib.request, urllib.parse

BIB = r"c:/Users/muham/Documents/Antigravity/DMS_Drafting/Pro-Active-Driver-Monitoring-System-Using-EEG/submission/references.bib"
OUT = "ref_verification.json"
UA = {"User-Agent": "refcheck/1.0 (mailto:muhammedraslan.t2022@vitstudent.ac.in)"}


def strip_tex(s):
    s = re.sub(r"\\[a-zA-Z]+\s*", " ", s)
    s = s.replace("{", "").replace("}", "").replace("--", "-")
    return re.sub(r"\s+", " ", s).strip()


def parse_bib(text):
    out = []
    for m in re.finditer(r"@(\w+)\{([^,]+),", text):
        start = m.start()
        i, depth = text.index("{", start), 0
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i + 1]
        fields = {}
        for fm in re.finditer(r"[\n,]\s*(\w+)\s*=\s*\{", body):
            k = fm.group(1).lower()
            j, d = fm.end() - 1, 0
            while j < len(body):
                if body[j] == "{":
                    d += 1
                elif body[j] == "}":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            fields[k] = body[fm.end():j]
        out.append({"type": m.group(1), "key": m.group(2).strip(), "fields": fields})
    return out


def crossref(title, rows=4):
    q = urllib.parse.urlencode({
        "query.bibliographic": strip_tex(title),
        "rows": rows,
        "select": "title,author,container-title,volume,issue,page,issued,DOI,type",
    })
    req = urllib.request.Request("https://api.crossref.org/works?" + q, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=45))["message"]["items"]


def sim(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


bib = parse_bib(io.open(BIB, encoding="utf-8").read())
print(f"parsed {len(bib)} entries\n")

report = []
for e in bib:
    f = e["fields"]
    title = f.get("title", "")
    if not title:
        continue
    bib_auth = [strip_tex(a).split(",")[0].strip()
                for a in f.get("author", "").split(" and ")] if f.get("author") else []
    rec = {"key": e["key"], "bib_title": strip_tex(title),
           "bib_authors": bib_auth,
           "bib_venue": strip_tex(f.get("journal") or f.get("booktitle") or f.get("institution", "")),
           "bib_volume": f.get("volume", ""), "bib_issue": f.get("number", ""),
           "bib_pages": strip_tex(f.get("pages", "")), "bib_year": f.get("year", ""),
           "bib_doi": f.get("doi", "")}
    try:
        items = crossref(title)
    except Exception as ex:
        rec["status"] = "LOOKUP-FAILED: %s" % ex
        report.append(rec); print(f"  !! {e['key']}: {ex}"); continue

    best, bestscore = None, 0.0
    for it in items:
        t = (it.get("title") or [""])[0]
        sc = sim(strip_tex(title), strip_tex(t))
        if sc > bestscore:
            best, bestscore = it, sc

    if best is None or bestscore < 0.72:
        rec["status"] = "NO-TITLE-MATCH"
        rec["best_score"] = round(bestscore, 2)
        rec["closest"] = strip_tex((best.get("title") or [""])[0]) if best else ""
        report.append(rec); print(f"  ?? {e['key']}: no confident match ({bestscore:.2f})"); continue

    cr_auth = [a.get("family", "?") for a in best.get("author", [])]
    rec.update({
        "status": "MATCHED", "match_score": round(bestscore, 2),
        "cr_authors": cr_auth,
        "cr_venue": (best.get("container-title") or [""])[0],
        "cr_volume": best.get("volume", ""), "cr_issue": best.get("issue", ""),
        "cr_pages": best.get("page", ""),
        "cr_year": str((best.get("issued", {}).get("date-parts") or [[""]])[0][0]),
        "cr_doi": best.get("DOI", ""),
    })

    problems = []
    # author check: first bib surname should appear among Crossref surnames
    if bib_auth and cr_auth:
        b0 = bib_auth[0].lower().replace("{", "").replace("}", "")
        if not any(b0 in c.lower() or c.lower() in b0 for c in cr_auth):
            problems.append("AUTHOR-MISMATCH")
        elif len(cr_auth) > len(bib_auth) and "others" not in f.get("author", ""):
            problems.append("AUTHOR-COUNT (bib %d vs crossref %d)" % (len(bib_auth), len(cr_auth)))
    if "others" in f.get("author", ""):
        problems.append("TRUNCATED-AUTHORS")
    if rec["bib_venue"] and rec["cr_venue"] and sim(rec["bib_venue"], rec["cr_venue"]) < 0.45:
        problems.append("VENUE-MISMATCH")
    if rec["bib_volume"] and rec["cr_volume"] and rec["bib_volume"] != rec["cr_volume"]:
        problems.append("VOLUME-MISMATCH")
    if rec["bib_year"] and rec["cr_year"] and rec["bib_year"] != rec["cr_year"]:
        problems.append("YEAR-MISMATCH")
    if rec["bib_pages"] and rec["cr_pages"] and \
       rec["bib_pages"].replace(" ", "") != rec["cr_pages"].replace(" ", ""):
        problems.append("PAGES-MISMATCH")
    if not rec["bib_issue"] and rec["cr_issue"]:
        problems.append("MISSING-ISSUE (crossref has %s)" % rec["cr_issue"])
    if not rec["bib_doi"]:
        problems.append("MISSING-DOI")

    rec["problems"] = problems
    flag = "OK  " if not problems else "FLAG"
    print(f"  {flag} {e['key']:26s} {','.join(p.split()[0] for p in problems)}")
    report.append(rec)
    time.sleep(0.6)

io.open(OUT, "w", encoding="utf-8").write(json.dumps(report, indent=1, ensure_ascii=False))
print(f"\nwrote {OUT}  ({len(report)} entries)")
