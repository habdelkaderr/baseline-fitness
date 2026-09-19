import io, re, os, json
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
PROJECT = _os.path.dirname(_HERE)

# The published files are at the project root — see the note in make_web.py.
W=PROJECT
idx=os.path.join(W,"index.html")
t=io.open(idx,encoding="utf-8").read()

print("="*64)
print("BASELINE — GitHub Pages deployment verification")
print("="*64)

print("\n-- FILES --")
need=["index.html","manifest.webmanifest","sw.js",".nojekyll","README.md",
      "icons/icon-180.png","icons/icon-192.png","icons/icon-512.png","icons/icon-512-maskable.png"]
allok=True
for f in need:
    p=os.path.join(W,f.replace("/",os.sep))
    e=os.path.exists(p)
    allok &= e
    print("  %-30s %s  %s" % (f, "OK " if e else "MISSING", ("%.1f KB"%(os.path.getsize(p)/1024)) if e else ""))
extra=[]
for root,d,fs in os.walk(W):
    for f in fs:
        rel=os.path.relpath(os.path.join(root,f),W).replace("\\","/")
        if rel not in need: extra.append(rel)
print("  unexpected extra files:", extra or "none")

print("\n-- NO PERSONAL DATA IN SHIPPED CODE --")
checks=[
 ("HRV baseline is null",      re.search(r"hrv:\s*null", t) is not None),
 ("RHR baseline is null",      re.search(r"rhr:\s*null", t) is not None),
 ("recovery baseline is null", re.search(r"recovery:\s*null", t) is not None),
 ("no 83 ms HRV seeded",       "hrv:83" not in t.replace(" ","")),
 ("no 53.9 RHR seeded",        "rhr:53.9" not in t.replace(" ","")),
 ("no 2026 export date range", "2026-03-18" not in t),
 ("no user name embedded",     "egcert" not in t.lower()),
 ("no WHOOP CSV rows embedded",t.count("Cycle start time")<=3),
]
for n,v in checks: print("  %-30s %s" % (n, "OK" if v else "*** FAIL ***"))

# Menstrual cycle data is the most sensitive thing this app can hold, so the
# shipped file is checked for it specifically: the feature's CODE must be
# present, any ENTRY must not be.
print("\n-- NO CYCLE DATA IN SHIPPED CODE --")
flat = t.replace(" ", "")
cyc = [
 ("cycle tracking ships off",   "mcycle:{on:false" in flat),
 ("no seeded period dates",     re.search(r"starts:\s*\[\s*['\"]", t) is None),
 ("no bleeding entry",          "bleeding:true" not in flat),
 ("no flow entry",              not re.search(r"flow:\s*['\"](Light|Medium|Heavy)", t)),
 ("no cramps value",            not re.search(r"cramps:\s*[1-9]", flat)),
 ("no symptom list",            not re.search(r"symptoms:\s*\[\s*['\"]", t)),
 ("no typical length seeded",   "typicalLen:null" in flat),
 ("no typical period seeded",   "typicalPeriod:null" in flat),
 ("no feel entry",              not re.search(r"feel:\s*['\"](strong|low|discomfort)", t)),
 # the feature itself must still be there
 ("the feature is present",     "function mcPhase" in t and "function mcAdjust" in t),
 ("the cap is present",         "MC_MAX_ADJUST" in t),
]
for n,v in cyc:
    print("  %-30s %s" % (n, "OK" if v else "*** FAIL ***"))

# Alerts are the obvious place for a privacy promise to break by accident: a
# real Web Push setup needs a subscription endpoint for this device sitting on
# somebody else's server. The LOCAL notification the app uses needs none of
# that, so none of it may appear - in the app or in the service worker.
print("\n-- ALERTS ARE LOCAL, NOT PUSH --")
sw = io.open(os.path.join(W,"sw.js"), encoding="utf-8").read()
both = t + "\n" + sw
psh = [
 ("no push subscription",      "pushManager" not in both),
 ("no VAPID key",              not re.search(r"applicationServerKey|vapid", both, re.I)),
 ("no push event listener",    not re.search(r"addEventListener\(\s*['\"]push['\"]", both)),
 ("no push endpoint",          not re.search(r"fcm\.googleapis|web\.push\.apple|push\.services", both)),
 # and the local alert path must actually be there
 ("local alerts are present",  "function notify(" in t and "showNotification" in t),
 ("off until asked for",       "notify:false" in t.replace(" ","")),
 ("permission only on a tap",  "function notifyAsk" in t),
 ("a tapped alert reopens it", "notificationclick" in sw),
 ("audio is synthesised",      "createOscillator" in t),
 ("no audio files shipped",    not re.search(r"[\w/-]\.(mp3|wav|ogg|m4a)\b", t)),   # a PATH, not a mention in a comment
]
for n,v in psh: print("  %-30s %s" % (n, "OK" if v else "*** FAIL ***"))

# The import path is the only door health data comes in through, and the
# claims made to the user about it have to be true of the file being shipped.
print("\n-- IMPORTED HEALTH DATA STAYS ON THE DEVICE --")
imp = [
 # the guard exists and runs
 ("upload type is validated",   "function importFileCheck" in t),
 ("upload size is capped",      "IMPORT_MAX_BYTES" in t and "IMPORT_MAX_MB" in t),
 ("binary files are rejected",  "function importLooksBinary" in t),
 ("row count is capped",        "IMPORT_MAX_ROWS" in t),
 ("the guard is actually called","importFileCheck(f)" in t.replace(" ", "")
                                 or "importFileCheck(f)" in t),
 # the user is told, before they hand anything over
 ("consent text before import", "used to personalise Baseline" in t),
 ("says data can be deleted",   "delete your imported data at any time" in t),
 ("has a how-it-is-used panel", 'id="impHow' in t),
 # deletion reaches everything
 ("delete-imported action",     "function deleteImportedData" in t),
 ("delete clears the fallback", "purgeLegacy" in t),
 ("erase-all clears storage",   "clearAll" in t),
 # free text from a journal export must never be stored
 ("journal notes are not kept", "col(r,'Notes')" not in t and '"Notes"' not in t),
 # no health data in the console
 ("no console.log at all",      "console.log(" not in t),
 ("console.error logs no object", "console.error('boot failed',e)" not in t),
 # labelling: user-provided data, not an integration
 ("no 'connect' wording",       "Connect WHOOP" not in t and "WHOOP integration" not in t),
 ("no affiliation claim",       not re.search(r"official|endorsed|sponsored by|in partnership", t, re.I)),
]
for n, v in imp:
    print("  %-30s %s" % (n, "OK" if v else "*** FAIL ***"))

# The one that cannot be faked: take the developer's own export and look for it
# in the file about to be published.
print("\n-- THE DEVELOPER'S OWN EXPORT IS NOT IN THE BUILD --")
own = []
wd = os.path.join(PROJECT, "private", "whoop-data")
if not os.path.isdir(wd):
    own.append(("no local export to check against", True))
else:
    leaked = []
    checked = 0
    for fn in sorted(os.listdir(wd)):
        if not fn.lower().endswith(".csv"):
            continue
        raw = io.open(os.path.join(wd, fn), encoding="utf-8", errors="replace").read()
        rows = [r for r in raw.splitlines() if r.strip()][1:]
        # whole data rows, and timestamps: values that cannot occur by accident
        for r in rows[:400]:
            cells = [c.strip().strip('"') for c in r.split(",")]
            for c in cells:
                # a full timestamp, or any long free-text cell
                if len(c) >= 16 and (":" in c or " " in c):
                    checked += 1
                    if c in t:
                        leaked.append("%s: %r" % (fn, c[:48]))
            if len(r) > 40:
                checked += 1
                if r in t:
                    leaked.append("%s: whole row" % fn)
    own.append(("checked %d values from the export" % checked, True))
    own.append(("none of it is in the shipped file", not leaked))
    if leaked:
        for l in leaked[:5]:
            print("      *** " + l)
for n, v in own:
    print("  %-40s %s" % (n, "OK" if v else "*** FAIL ***"))

print("\n-- PRIVACY / NETWORK --")
net=[
 ("no XMLHttpRequest", "XMLHttpRequest" not in t),
 ("no WebSocket",      "new WebSocket" not in t),
 ("no sendBeacon",     "sendBeacon" not in t),
 ("no EventSource",    "EventSource" not in t),
 ("no analytics calls",not re.search(r"gtag\(|dataLayer|_paq|googletagmanager", t)),
 ("no external <script src>", not re.search(r'<script[^>]+src=', t)),
]
for n,v in net: print("  %-30s %s" % (n, "OK" if v else "*** FAIL ***"))
origins=set(re.findall(r"https?://[a-z0-9.\-]+", t, re.I))
allowed={"http://www.w3.org","https://www.w3.org"}
bad=[o for o in origins if o not in allowed]
print("  external origins referenced :", bad or "none")

print("\n-- PWA --")
man=json.loads(io.open(os.path.join(W,"manifest.webmanifest"),encoding="utf-8").read())
pwa=[
 ("manifest is valid JSON", True),
 ("start_url relative ('./')", man.get("start_url")=="./"),
 ("scope relative ('./')",     man.get("scope")=="./"),
 ("display standalone",        man.get("display")=="standalone"),
 ("theme + background colour", bool(man.get("theme_color") and man.get("background_color"))),
 ("192 + 512 icons present",   {i["sizes"] for i in man["icons"]} >= {"192x192","512x512"}),
 ("maskable icon present",     any(i.get("purpose")=="maskable" for i in man["icons"])),
 ("icons point at icons/",     all(i["src"].startswith("icons/") for i in man["icons"])),
 ("manifest linked in html",   'rel="manifest" href="manifest.webmanifest"' in t),
 ("apple-touch-icon linked",   'rel="apple-touch-icon" href="icons/icon-180.png"' in t),
 ("apple web-app meta",        'name="apple-mobile-web-app-capable"' in t),
 ("no data: URL manifest",     "application/manifest+json," not in t),
 ("sw registered relatively",  "register('sw.js'" in t),
]
for n,v in pwa: print("  %-30s %s" % (n, "OK" if v else "*** FAIL ***"))

sw=io.open(os.path.join(W,"sw.js"),encoding="utf-8").read()
print("  shell entries cached       :", len(re.findall(r"'\./", sw)))
print("  relative shell paths       :", "OK" if "'./index.html'" in sw else "*** FAIL ***")

print("\n-- APP INTEGRITY --")
app=[
 ("single <script> block",   t.count("<script")==1 and t.count("</script>")==1),
 ("single <style> block",    t.count("<style")==1),
 ("ends with </html>",       t.rstrip().endswith("</html>")),
 ("IndexedDB schema",        "const DB_VERSION" in t),
 ("versioned migrations",    "SCHEMA_VERSION" in t),
 ("setup wizard",            "function startSetup" in t),
 ("equipment tiers",         "const TIERS=" in t),
 ("two modes",               "function whoopMode" in t or "whoopMode =" in t),
 ("desktop sidebar css",     "min-width:900px" in t),
 ("service worker hook",     "function registerSW" in t),
]
for n,v in app: print("  %-30s %s" % (n, "OK" if v else "*** FAIL ***"))
print("  exercises defined          :", len(re.findall(r"\{id:'[a-z]{1,2}\d{2}',name:'", t)))
print("  workouts defined           :", len(re.findall(r"\{id:'w_", t)))
print("  activity types             :", len(re.findall(r"^\s{2}\w+:\s+\{name:'", t, re.M)))
print("  index.html size            : %.1f KB" % (os.path.getsize(idx)/1024))

fails = [n for n,v in checks+cyc+psh+imp+own+net+pwa+app if not v] + ([ "missing files" ] if not allok else []) + ([ "external origins" ] if bad else [])
print("\n" + "="*64)
print("RESULT:", "ALL CHECKS PASSED" if not fails else ("FAILED: "+", ".join(fails)))
print("="*64)
