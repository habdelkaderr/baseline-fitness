# -*- coding: utf-8 -*-
"""A real audit of where uploaded health data can go, from the source itself.

Nothing here assumes the architecture is what the comments claim. Every
question in the brief is answered by grepping the actual built file and the
parts it is built from.
"""
import io, os, re, sys
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
PROJECT = _os.path.dirname(_HERE)


SP = os.path.dirname(os.path.abspath(__file__))
PROJ = PROJECT
PARTS = ["p01.part", "p02.part", "p03.part", "p03b.part", "p04.part", "p04b.part",
         "p05.part", "p06.part", "p07.part", "p08.part", "p09.part", "p10.part"]
SRC = {f: io.open(os.path.join(PROJECT, "src", f), encoding="utf-8").read() for f in PARTS}
BUILT = io.open(os.path.join(PROJ, "build", "baseline.html"), encoding="utf-8").read()
SHIPPED = io.open(os.path.join(PROJ, "site", "index.html"), encoding="utf-8").read()
SW = io.open(os.path.join(PROJ, "baseline-web", "sw.js"), encoding="utf-8").read()


def hits(label, pattern, text=None, flags=re.I):
    print("\n### " + label)
    found = False
    if text is not None:
        for m in re.finditer(pattern, text, flags):
            line = text[:m.start()].count("\n") + 1
            print("    built:%d  %s" % (line, text[max(0, m.start()-50):m.end()+50].replace("\n", " ")[:130]))
            found = True
    else:
        for f, t in SRC.items():
            for m in re.finditer(pattern, t, flags):
                line = t[:m.start()].count("\n") + 1
                seg = t[m.start():m.end()+90].replace("\n", " ")
                print("    %s:%d  %s" % (f, line, seg[:140]))
                found = True
    if not found:
        print("    (none)")
    return found


print("=" * 72)
print("1. WHERE UPLOADED FILES ENTER")
print("=" * 72)
hits("file inputs in markup", r"<input[^>]*type=[\"']file[\"'][^>]*>")
hits("FileReader / file APIs", r"FileReader|\.files\b|readAsText|readAsArrayBuffer|createObjectURL|URL\.createObjectURL")
hits("drag and drop", r"ondrop|dataTransfer|dragover")
hits("import entry points", r"function importWhoopFile|function importFile|function handleFiles")

print("\n" + "=" * 72)
print("2. NETWORK: CAN ANYTHING LEAVE THE DEVICE?")
print("=" * 72)
hits("fetch / XHR / beacon / socket", r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|new WebSocket|EventSource|navigator\.connection")
hits("form submission", r"<form[^>]*action=|\.submit\s*\(")
hits("external origins referenced", r"https?://[a-z0-9.\-]+", BUILT)
hits("script/style/img loaded from elsewhere", r"<(script|link|img|iframe)[^>]+(src|href)=[\"']https?:", BUILT)
hits("service worker: any push/upload path", r"pushManager|fetch\([^)]*http|postMessage\(", SW)

print("\n" + "=" * 72)
print("3. STORAGE: WHERE DOES IT REST?")
print("=" * 72)
hits("localStorage", r"localStorage\.[a-z]+\s*\(|localStorage\[")
hits("sessionStorage", r"sessionStorage")
hits("IndexedDB", r"indexedDB\.|objectStore|createObjectStore|transaction\(")
hits("cookies", r"document\.cookie")
hits("cache API", r"caches\.(open|match|delete|keys)")

print("\n" + "=" * 72)
print("4. LOGGING AND LEAKAGE")
print("=" * 72)
hits("console.*", r"console\.(log|info|warn|error|debug|table|dir)\s*\(")
hits("alert / prompt", r"\balert\s*\(|\bprompt\s*\(")
hits("data written into the URL", r"location\.(hash|search|href)\s*=|history\.(pushState|replaceState)\s*\([^)]{40,}")
hits("innerHTML from raw imported text", r"innerHTML\s*=\s*[^;]*\b(raw|csv|text|contents)\b")

print("\n" + "=" * 72)
print("5. THIRD PARTIES")
print("=" * 72)
hits("analytics / trackers / AI endpoints",
     r"gtag|dataLayer|googletagmanager|_paq|mixpanel|segment\.|sentry|bugsnag|amplitude|"
     r"openai|anthropic|openrouter|api\.[a-z]+\.(com|ai|io)")
hits("any import/require of a package", r"^\s*(import|require)\s*[\(\'\"]", None, re.M)

print("\n" + "=" * 72)
print("6. IS THE USER'S OWN DATA IN THE BUILT OR SHIPPED FILE?")
print("=" * 72)
wd = os.path.join(PROJ, "private", "whoop-data")
if os.path.isdir(wd):
    for f in sorted(os.listdir(wd)):
        p = os.path.join(wd, f)
        raw = io.open(p, encoding="utf-8", errors="replace").read()
        lines = [l for l in raw.splitlines() if l.strip()]
        print("\n  %s : %d lines, %.1f KB" % (f, len(lines), os.path.getsize(p) / 1024.0))
        print("    header: " + (lines[0][:120] if lines else "(empty)"))
        # take a few distinctive data values and look for them in the builds
        probes = []
        for l in lines[1:6]:
            for cell in l.split(","):
                cell = cell.strip().strip('"')
                if len(cell) >= 6 and not cell.replace(".", "").isdigit():
                    probes.append(cell)
        probes = probes[:6]
        for pr in probes:
            where = []
            if pr in BUILT:
                where.append("baseline.html")
            if pr in SHIPPED:
                where.append("baseline-web/index.html")
            if where:
                print("    *** LEAK: %r found in %s" % (pr[:40], ", ".join(where)))
        if not probes:
            print("    (no distinctive text probes available)")
else:
    print("  no 'Whoop Data' directory")

print("\n" + "=" * 72)
print("7. WHAT THE PARSER ACCEPTS")
print("=" * 72)
hits("file type / size validation", r"accept=|\.type\s*===|\.size\s*[<>]|MAX_[A-Z_]*SIZE|endsWith\(\s*['\"]\.csv")
hits("eval-ish execution paths", r"\beval\s*\(|new Function\s*\(|setTimeout\s*\(\s*[\"']|\.outerHTML\s*=")

print("\n" + "=" * 72)
print("8. WHAT IS KEPT FROM AN IMPORT")
print("=" * 72)
hits("the whoop store shape", r"whoop\s*:\s*\{[^}]*\}")
hits("imports ledger", r"imports\s*:\s*\[|\.imports\.push")
hits("journal handling", r"journal")
print()
