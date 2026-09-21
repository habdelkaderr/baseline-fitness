"""Build the GitHub Pages deployment folder for Baseline."""
import io, os, json, zlib, struct, shutil, math
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
PROJECT = _os.path.dirname(_HERE)


SRC = _os.path.join(PROJECT,"build","baseline.html")
OUT = _os.path.join(PROJECT,"site")
ICO = os.path.join(OUT, "icons")
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(ICO, exist_ok=True)

SRC_ICON = _os.path.join(PROJECT,"brand","icon-source.png")
_PLATE_CACHE = {}

def _plate_square():
    """The artwork cropped to its plate and squared off, corners filled.

    Cached: this runs four times otherwise, and it is a per-pixel pass.
    """
    if "img" in _PLATE_CACHE:
        return _PLATE_CACHE["img"]
    from PIL import Image
    if not os.path.isfile(SRC_ICON):
        raise SystemExit("icon source missing: " + SRC_ICON)
    im = Image.open(SRC_ICON).convert("RGB")
    W, H = im.size
    px = im.load()

    def lum(c):
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    # the plate is anything brighter than the surrounding letterbox
    floor = lum(px[2, 2]) + 6.0
    x0, y0, x1, y1 = W, H, -1, -1
    for y in range(H):
        for x in range(W):
            if lum(px[x, y]) > floor:
                if x < x0: x0 = x
                if y < y0: y0 = y
                if x > x1: x1 = x
                if y > y1: y1 = y
    if x1 < 0:
        raise SystemExit("icon source looks blank")

    # square the crop on the longer side, centred
    w, h = x1 - x0 + 1, y1 - y0 + 1
    s = max(w, h)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0 = max(0, cx - s // 2); y0 = max(0, cy - s // 2)
    crop = im.crop((x0, y0, x0 + s, y0 + s))

    # plate colour: average a ring just inside its edge, so a gradient does
    # not produce a visible seam where the corners get filled
    cp = crop.load()
    inset = max(6, s // 40)
    pts = [(inset, s // 2), (s - 1 - inset, s // 2), (s // 2, inset), (s // 2, s - 1 - inset),
           (inset, inset * 3), (s - 1 - inset, inset * 3),
           (inset, s - 1 - inset * 3), (s - 1 - inset, s - 1 - inset * 3)]
    r = g = b = 0
    for (x, y) in pts:
        c = cp[x, y]; r += c[0]; g += c[1]; b += c[2]
    plate = (r // len(pts), g // len(pts), b // len(pts))

    # fill the corner exterior: only the letterbox is this dark, the plate
    # interior sits around 18-27 and the figure is far brighter
    for y in range(s):
        for x in range(s):
            if lum(cp[x, y]) < 8.0:
                cp[x, y] = plate

    _PLATE_CACHE["img"] = crop
    _PLATE_CACHE["plate"] = plate
    return crop

def png(path, size, maskable=False):
    """Resize the squared plate. Requires Pillow."""
    from PIL import Image
    src = _plate_square()
    if not maskable:
        # full bleed: iOS and Android round the corners themselves
        out = src.resize((size, size), Image.LANCZOS)
    else:
        # a maskable icon may be cropped to any shape, so keep the mark inside
        # the middle 80% on a plate-coloured field
        inner = int(size * 0.80)
        out = Image.new("RGB", (size, size), _PLATE_CACHE["plate"])
        out.paste(src.resize((inner, inner), Image.LANCZOS), ((size - inner) // 2,) * 2)
    out.save(path, "PNG", optimize=True)
    return os.path.getsize(path)

icons = [("icon-180.png", 180, False), ("icon-192.png", 192, False),
         ("icon-512.png", 512, False), ("icon-512-maskable.png", 512, True)]
for name, size, mask in icons:
    n = png(os.path.join(ICO, name), size, mask)
    print("  icons/%-22s %dx%-4d %5.1f KB" % (name, size, size, n / 1024))

# ---------------------------------------------------------------- manifest
manifest = {
    "name": "Baseline — Training System",
    "short_name": "Baseline",
    "description": "Private, local-first training system. Decides what to train each day from your recovery and activity history.",
    "start_url": "./",
    "scope": "./",
    "id": "./",
    "display": "standalone",
    "display_override": ["standalone", "fullscreen"],
    "orientation": "any",
    "background_color": "#FBFBF9",
    "theme_color": "#FBFBF9",
    "categories": ["health", "fitness", "sports"],
    "icons": [
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
    ]
}
io.open(os.path.join(OUT, "manifest.webmanifest"), "w", encoding="utf-8").write(
    json.dumps(manifest, indent=2))
print("  manifest.webmanifest")

# ---------------------------------------------------------------- service worker
SW = r"""/* Baseline service worker — offline support for the app shell.
   No user data passes through here. WHOOP files are parsed in the page and
   training data lives in IndexedDB, neither of which the Cache API can see.
   Nothing is ever sent anywhere: there is no server to send it to. */
const CACHE = 'baseline-v17';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-180.png',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-512-maskable.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      // add individually: addAll aborts the whole install if any one file 404s
      .then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;     // never touch cross-origin

  // Navigations: network first so updates are picked up, cache as the fallback.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put('./index.html', copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match('./index.html').then(r => r || caches.match('./')))
    );
    return;
  }

  // Everything else: cache first, then network, caching what comes back.
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res && res.status === 200 && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
      }
      return res;
    }).catch(() => hit))
  );
});

self.addEventListener('message', e => { if (e.data === 'skipWaiting') self.skipWaiting(); });

/* Notifications the PAGE raised through this worker — a rest timer finishing
   while the screen is off. There is deliberately no 'push' listener: there is
   no push service, no subscription and no server, so nothing can arrive from
   outside. All this does is bring the app back to the front when tapped. */
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(list => {
        for (const c of list) { if ('focus' in c) return c.focus(); }
        if (self.clients.openWindow) return self.clients.openWindow('./');
      })
      .catch(() => {})
  );
});
"""
io.open(os.path.join(OUT, "sw.js"), "w", encoding="utf-8").write(SW)
print("  sw.js")

# ---------------------------------------------------------------- app
html = io.open(SRC, encoding="utf-8").read()
# icons now live in icons/ — point the document links at them
html = html.replace('href="icon-180.png"', 'href="icons/icon-180.png"')
html = html.replace('href="icon-512.png"', 'href="icons/icon-512.png"')
io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
print("  index.html  (%.1f KB)" % (len(html.encode('utf-8')) / 1024))

# GitHub Pages: skip Jekyll processing entirely
io.open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8").write("")
print("  .nojekyll")

README = """# Baseline

A training app that decides what you should do **today** — from how recovered
you are, what you have actually been doing, and the kit you actually own.
Everything stays on your own device.

Most plans tell you what to do on a Tuesday, decided weeks ago, whether or not
you slept badly or played a match yesterday. This one decides each morning,
gives you one session, and tells you what it ruled out and why.

## How a day works

1. Open the app. It greets you and shows one number: **readiness**.
2. **Check in** — about a minute. Sleep, and four sliders for how you feel.
   The sliders start where you left them yesterday, so an unchanged day is
   barely any input at all. If you wear a tracker, whatever it reports is
   filled in for you.
3. You get **one session**. Name, duration, intensity. Nothing else competes
   with it on the screen.
4. Tap **Why this?** if you want the reasoning — what counted for it, and what
   was ruled out. Tap **Change today's plan** if you disagree; overriding is
   recorded and adapted to, not punished.
5. **Start session.** The screen becomes the workout: one exercise at a time,
   what you lifted last time, plus and minus buttons for reps and weight — no
   keyboard — and a rest timer that starts itself when you finish a set.
6. Played football instead? **Log activity** is three answers — what, how
   long, how hard — and feeds straight into tomorrow's recommendation.
   Anything not in the list, you can just type, and it suggests as you go.

## Finding your way around

Four sections along the bottom. Each one **opens with the thing it is for**,
and keeps everything else one tap away rather than on the same screen.

| | Opens with | One tap away |
|---|---|---|
| **Today** | Today's session, and one Start button | Why this · Change the plan · Readiness detail |
| **Train** | This week's targets, and which of the 8 progression weeks you are in | Workouts · Exercises · Warm-ups · History |
| **Activity** | Log an activity, then what you have done recently | All activity · Totals · your sport |
| **Progress** | How the week went, and the load chart | Strength · Tests · Physique · Patterns |

**Settings** is the gear in the top right, grouped as **Profile · Training ·
Wearables · Data · Appearance · Cycle · About**.

Wearable numbers and trends live behind the readiness row on Today, so if you
do not use a tracker you never see an empty chart. Nothing about cycle
tracking appears anywhere unless you switch it on.

Every screen has a back button, and the phone's own back gesture works too.

## What it does

- **One recommendation a day**, with its reasoning shown — including the
  options it rejected and the reason for each
- **Nothing is assumed.** No sport, no equipment, no goal, no wearable, no
  injuries — every one of those starts empty, and empty is a valid answer. The
  app never makes you undo a choice you did not make
- **Any wearable, or none.** WHOOP, Garmin, Oura, Fitbit, Apple Watch, Samsung,
  Polar, COROS, or nothing at all. It asks only for the numbers your device
  actually reports, and works from a short daily check-in without one
- **Built around your sport**, not a fixed template. 18 sports, each with its
  own warm-up, priorities and weekly targets — or none, which is also fine
- **Only exercises you can do.** 173 exercises tagged with the equipment they
  need; tick nothing and you still get a full bodyweight programme
- **Logs anything.** A match, a hike, a kickabout. Unplanned activity is not a
  missed workout — the engine adapts around it
- **Shows what you lifted last time**, under each exercise, while you are
  standing in front of it
- **Progression is earned, not scheduled.** Miss a fortnight and the plan waits
  rather than marching you into a peak week you have not worked for
- **Injuries persist.** Name an area and a date and it routes around the
  movements that load it until then, keeping everything else
- **It grades its own advice.** After enough days it will tell you whether
  following the recommendation actually went better for you — including when
  the honest answer is "no difference"
- Light or dark, following your system setting

## Setting up

Seven questions, and you can skip or leave empty any of them: your name, what
you are training for, your sport, your equipment, how often you train, your
tracker, and your age and measurements. The last three are explicitly optional
— the button says **Skip** rather than pretending you must answer.

If you close it half way through, it reopens where you left off.

## Your data

Everything you enter, and everything you import, stays in **your own browser**
on the device you used. This repository hosts the application code and nothing
else.

- No account, no server, no database, no analytics, no trackers
- No third-party libraries at all — nothing is loaded from anywhere else
- Nothing is uploaded, because there is no endpoint to upload to
- Each browser on each device keeps a completely separate dataset
- Anyone opening the same link gets an empty copy of the app, not your data

You can check this in ten seconds: open the app in a private browsing window.
You will get an empty app and the setup wizard.

### What happens to a wearable export

You export your own data from WHOOP, Garmin, Oura, Fitbit or similar and pick
the CSV files yourself. Baseline is **not connected to any of those services**,
uses no API, and never sees an account or a password.

When you choose a file:

1. It is checked first — `.csv` only, 25 MB limit, and it has to actually be
   text. Anything else is refused with a reason.
2. It is read into memory and parsed **in the browser**.
3. The figures the engine uses are kept: date, recovery, HRV, resting heart
   rate, sleep, strain, and your workouts.
4. **The file itself is never stored.** The text is released when the import
   finishes.
5. **Free-text journal notes are never stored.** A WHOOP journal export
   contains what you wrote about alcohol, illness and stress; Baseline reads
   the question and the yes/no and skips the note.

Imported figures live in your browser's IndexedDB. On a browser where
IndexedDB is unavailable, Baseline falls back to local storage so your history
is not silently lost — the same data, the same device, and both delete actions
below clear it either way.

### Deleting it

**Settings → Data**

- **Delete imported data** — removes imported days, workouts, journal rows and
  import history, resets the baselines calculated from them, and tells you
  exactly what was removed. Your own sessions, activities and check-ins stay.
- **Erase all data** — removes everything on the device and returns the app to
  a first run.

Clearing the site's data in your browser does the same thing, because
everything is in the browser.

### What this does not protect against

Baseline has no passcode of its own — anyone who can unlock your device and
open the app can read your history. A backup you export is plain, unencrypted
JSON.

### Never commit an export

A real wearable export is months of health data. `.gitignore` in this project
excludes `Whoop Data/`, loose export CSVs and backup JSON, and `verify_web.py`
fails the build if any of it reaches the shipped file. Anything actually
committed is permanent and recoverable from git history, and Pages sites are
public even when the repository is private.

Full detail: **DATA-PRIVACY.md** (how it works) and **PRIVACY.md** (the
policy). **STORE-READINESS.md** lists what still needs doing — including legal
and trademark review — before this could go to an app store.

## Install it

**iPhone/iPad (Safari):** open the URL → Share (□↑) → **Add to Home Screen**
**Android (Chrome):** menu → **Install app**
**Windows/macOS (Chrome/Edge):** install icon in the address bar
**macOS (Safari):** File → **Add to Dock**

On iPhone this matters more than it looks: left as an ordinary Safari tab, iOS
may clear the app's stored data after about a week of not opening it. Added to
the Home Screen it is treated as a real app and kept.

Installed versions share the same local data as the browser tab.

## Cycle tracking (optional)

Off unless you turn it on, in **Settings → Cycle**. Nothing cycle-related
appears anywhere in the app until you do.

What it does:

- One row on Today: *"Day 12 · Estimated follicular"*, and a short daily log —
  bleeding, how today feels, cramps, symptoms, a note. All optional, and it
  does not ask again for energy or soreness because the check-in already did.
- Period start dates are worked out from the days you mark as bleeding, so
  marking "bleeding today" is the only input a cycle needs.
- Phases are **estimates**, labelled as such, with a confidence. If your
  history is thin or your cycle length varies, it says *"phase estimate
  unavailable"* rather than guessing.

What it deliberately does **not** do:

- It has no rule saying a phase means train less. Nothing like *"luteal =
  reduce volume"* exists in the code.
- Cycle context changes your readiness score **only** once your own logs show
  a repeated association for one particular phase — at least two recorded
  cycles, a cycle regular enough for phases to mean anything, at least six
  logged days in that phase, and an effect too large to be noise. Until all of
  that holds, the effect is exactly zero and your recommendations are
  identical to having the feature off.
- When it does apply, it is capped at **5 points out of 100**, and only one
  phase can ever carry it.
- It can never lift a pain cap. Report moderate or significant pain and the
  session is reduced regardless of anything cycle-related.
- What you report about today outranks any estimate. *"Feeling strong"* raises
  the score even in a phase your history flags; *"significant discomfort"*
  lowers it in one it does not.
- It never estimates fertility or ovulation dates as fact, never infers
  pregnancy, and never diagnoses anything.

Anything the app observes is described as a correlation in your own logs. It
will say *"you have tended to report a harder time around this phase"* — never
that hormones are causing anything.

Privacy is the same as everything else, which is to say total: it is stored in
your browser on your device, it is never uploaded, and it is not in this
repository. A backup file lists **MENSTRUAL CYCLE DATA** in its header when it
contains any, so you know what you are sending if you ever send one.
**Settings → Cycle → Delete all cycle data** removes every entry and date and
keeps your training history.

## Back up

**Settings → Data → Backup** writes one file containing everything;
**Restore** reads it back. Clearing browser data erases the lot, and no copy
exists anywhere else. Worth doing every few weeks and before changing phones.

The same screen has **Erase all data**, which deletes everything on this device
and cannot be undone. **Reset programme to defaults** sits next to it and is
much milder: it restores the stock workouts and exercises and keeps all of your
history.

## Offline

After the first successful load the service worker caches the app shell, so it
opens and works with no internet. Your data was never coming from the network
anyway.

## Reporting a problem

**Settings → About** shows the build number and a **Copy diagnostics** button.
That copies device, browser, storage state and how many things you have logged —
counts only, never what you entered. Paste it into your bug report; the build
number is most of the diagnosis.

## Updating

Replace the files below and commit. Then close the app fully and reopen it
**twice** — a service worker hands over on the second launch. Confirm the new
build under **Settings → About**.

## Deploying your own copy

    Settings → Pages → Build and deployment
      Source: Deploy from a branch
      Branch: main      Folder: / (root)
      Save

Wait 1–3 minutes, then open `https://<user>.github.io/<repo>/` (keep the
trailing slash). Every path in the app is relative, so it also works at a
domain root or any subpath.

> On a free GitHub account, Pages requires a **public** repository. GitHub Pro
> allows Pages from a private repo, but the published site is public either way.
> That is fine here: the code contains no personal data.

## Files

    index.html              the entire application
    manifest.webmanifest    PWA metadata (name, icons, standalone display)
    sw.js                   service worker — offline caching
    .nojekyll               tells GitHub Pages to skip Jekyll
    icons/                  home screen and install icons

---

Not a medical device. It does not diagnose anything. Persistent pain, symptoms
or unusual physiological readings belong with a qualified healthcare
professional, separately from any training decision.
"""
io.open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(README)
print("  README.md")

print("\nDeploy folder:", OUT)
for root, dirs, files in os.walk(OUT):
    for f in sorted(files):
        p = os.path.join(root, f)
        rel = os.path.relpath(p, OUT).replace("\\", "/")
        print("   %-28s %7.1f KB" % (rel, os.path.getsize(p) / 1024))
