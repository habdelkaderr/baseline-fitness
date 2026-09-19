# Baseline — data privacy, for developers

What this document is: an accurate description of how Baseline handles
user-uploaded fitness and health data **as the code actually stands**, written
from an audit of the implementation rather than from intent. Where something
is a risk, it says so. Where something needs a human or a lawyer, it says that
too.

Last audited against: `baseline.html` / `baseline-web/index.html`, built from
the twelve `.part` sources.

---

## 1. Architecture in one paragraph

Baseline is a single HTML file with no build step, no dependencies, no
package manager and no backend. It is served as a static file (GitHub Pages)
and runs entirely in the browser. **There is no server component, no account,
no database off the device and no API of any kind.** Everything below follows
from that.

Baseline does **not** use the WHOOP API and does not connect to any WHOOP
account. The user exports their own data from WHOOP and chooses the CSV files
from their own device.

---

## 2. Current data flow

```
  User picks CSV files
          │   (<input type="file">, never a drag-drop, never a URL)
          ▼
  importFileCheck(file)          ← extension, MIME, size, name shape
          │
          ▼
  file.text()                    ← read into a JS string, in memory
          │
          ▼
  importWhoopFile(name, text)    ← binary sniff, row cap, header detection,
          │                        parse into typed fields
          ▼
  DB.whoop.{cycles,workouts,journal,imports}
          │                      ← derived figures only; the text is dropped
          ▼
  IndexedDB  (database "baseline", on this device)
          └─ fallback only if IndexedDB is unavailable:
             localStorage key "baseline.tps.v1"
```

The string holding the file contents is a local variable in the change
handler. It is not stored, not copied into `DB`, and is released when the
handler returns.

---

## 3. What is processed, and what is kept

| From the export | Kept? | What is kept |
|---|---|---|
| Recovery score, HRV, resting HR, day strain | Yes | Number + ISO date |
| Sleep duration, sleep performance, sleep need | Yes | Minutes + ISO date |
| Workout rows | Yes | Date, start time, activity name, duration, strain |
| Journal questions | Yes | Date, question text, yes/no |
| **Journal free-text notes** | **No** | Discarded at parse time |
| The CSV file itself | **No** | Never written to storage |
| Filenames | Yes | In the import history, shown back escaped |

`journal_entries.csv` carries a `Notes` column containing whatever the person
wrote about their own drinking, illness, stress or mood. The parser reads
`{key, date, question, yes}` and never touches `Notes`. That is the single
most sensitive field in a WHOOP export and it does not enter storage.

Baseline also stores data the user creates in the app itself: check-ins,
sessions, activities, tests, body measurements, and optional menstrual-cycle
entries. Same device, same database, same deletion routes.

---

## 4. Where processing happens

**In the browser, on the user's device.** Parsing, baseline calculation,
readiness scoring and the training recommendation are all synchronous
JavaScript in the page. Nothing is computed remotely because there is nowhere
remote to compute it.

---

## 5. What is transmitted externally

**Nothing.**

Verified by grep over the built file and enforced by `verify_web.py` on every
release build:

- no `fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket`, `EventSource`
- no `<form action>`, no `<script src>`, `<link href>` or `<img src>` pointing
  off-origin
- no analytics, tag managers, crash reporters or telemetry of any kind
- no `pushManager`, no VAPID key, no push endpoint
- the only external origins named anywhere in the file are the two
  `www.w3.org` XML namespace URLs inside inline SVG, which are identifiers and
  are never fetched

The service worker caches **application shell files only** (`index.html`, the
manifest, the icons). It is GET-only and same-origin. Imported health data is
in IndexedDB, which the Cache API cannot see.

A runtime test replaces `fetch`, `XMLHttpRequest` and `sendBeacon` with
recorders, renders every screen, imports a file and saves — and asserts none
of them was called.

---

## 6. Third-party services

| Category | Used? |
|---|---|
| AI / LLM APIs | None |
| Analytics | None |
| Crash reporting | None |
| Remote logging | None |
| Authentication | None |
| Remote database | None |
| Cloud storage | None |
| Advertising SDKs | None |
| Fonts / CDNs | None — no external resource of any kind |
| npm / third-party libraries | None — zero dependencies |

**The hosting provider (GitHub Pages) serves the application file.** Like any
web host it can observe the request for the page itself: IP address, user
agent, timestamp. It never receives health data, because health data is never
sent anywhere. This is a property of static hosting, not of Baseline, and is
stated in `PRIVACY.md` rather than glossed over.

---

## 7. Retention

| Item | Where | How long |
|---|---|---|
| Imported daily figures | IndexedDB | Until deleted by the user |
| Imported workouts / journal rows | IndexedDB | Until deleted by the user |
| Import history (time + filename + counts) | IndexedDB | Until deleted by the user |
| Computed baselines | IndexedDB | Until deleted or recomputed |
| The uploaded file's contents | Memory only | Until the handler returns |
| Theme preference | localStorage `baseline.prefs` | Until data is erased |
| In-progress workout | localStorage `baseline.prefs` | Until finished, discarded, or erased |
| Whole-DB fallback copy | localStorage `baseline.tps.v1` | Only on devices without IndexedDB |

There is no automatic expiry. Baseline keeps what the user imported until the
user removes it, because a training history that silently deletes itself is
not a training history.

### The localStorage fallback — read this one

`Store.write()` prefers IndexedDB. If IndexedDB is unavailable or its write
fails, it falls back to writing the **entire dataset**, health data included,
as one JSON string into `localStorage` under `baseline.tps.v1`.

This is not ideal — localStorage is synchronous, size-limited and no more
private than IndexedDB — but removing it would mean the app silently losing
data on browsers where IndexedDB is blocked (private windows in some
browsers, aggressive privacy extensions). Keeping the app working was judged
better than a purity that loses a user's history.

It is disclosed here and in `PRIVACY.md`, and **both delete paths clear it
explicitly**, whether or not the current session is using it. That last part
was a real bug: before this audit, deleting imported data went through the
normal write path, which never touches the fallback while IndexedDB is
working — so a device that had once hit the fallback kept a copy of the health
data after being told it was deleted.

---

## 8. Deletion

Two routes, both in **Settings → Data**:

**"Delete imported data"** — removes imported days, imported workouts, journal
rows and the import history; resets the baselines computed from them; clears
the named data source; purges the localStorage fallback copy. Then shows
exactly what was removed. The user's own sessions, activities, check-ins and
settings are untouched.

**"Erase all data"** — `Store.clearAll()`: wipes every IndexedDB object store,
removes the localStorage fallback blob, and removes the preferences key
(theme, any in-progress workout). The app returns to first-run setup.

Beyond the app, clearing site data in the browser removes everything, because
everything is in the browser.

---

## 9. Security measures in the import path

- **Extension check** — `.csv` / `.txt` only.
- **MIME check** — a declared type outside the CSV/plain-text set is rejected.
  An *empty* type is allowed through to the content checks, because browsers
  genuinely disagree about what to report for a CSV.
- **Size limit** — 25 MB per file. A full multi-year WHOOP export is far under
  this; the limit exists so a huge or hostile file cannot exhaust memory.
- **Binary sniff** — a NUL byte in the first 4 KB rejects the file whatever it
  is named.
- **Row cap** — 200,000 rows.
- **Filename shape** — a name containing a path separator or `..` is rejected.
  Filenames are never used to open, write or resolve anything; this is
  belt-and-braces plus a signal that something is odd.
- **No execution** — no `eval`, no `new Function`, no string `setTimeout`, no
  dynamic `<script>`. Imported values reach the DOM only through `esc()`.
- **Type detection from headers, not filenames** — a renamed file still
  resolves correctly, and an unrecognised one is rejected with a message
  rather than imported as the wrong kind of data.
- **Errors do not echo file contents.** A read failure reports "Could not read
  that file" rather than the browser's message, which can quote a path.
- **No health data in the console.** The single `console.error` at boot logs
  the error *type*, not the exception object.

---

## 10. Known privacy risks that remain

1. **Device access equals data access.** Baseline has no passcode or
   encryption of its own. Anyone who can unlock the device and open the app
   can read the history. Stated plainly in the app and in `PRIVACY.md`.
2. **Backups are unencrypted JSON.** The export produces a plain file
   containing everything. That is what makes it portable and inspectable; it
   also means the user is responsible for where it lands. The UI says so.
3. **The localStorage fallback** — see §7.
4. **A developer's own export lives next to the code.** `Whoop Data/` in this
   working directory holds a real WHOOP export. It is in `.gitignore` and
   `verify_web.py` fails the build if any of it reaches the shipped file, but
   it remains a real file on a real disk and is not needed to build or run the
   app.
5. **The host sees requests for the page.** Inherent to web hosting. §6.
6. **No Subresource Integrity / CSP header.** Static hosting on GitHub Pages
   does not let the app set response headers. A `<meta>` CSP could be added;
   it has not been, and that is a gap rather than a claim.

---

## 11. Requires human or legal review before publication

These are **not** engineering questions and nothing in this repository should
be read as having settled them:

- **WHOOP trademark use.** The app names WHOOP to identify whose export the
  user is importing. Whether that nominative use is acceptable, and in what
  wording, needs review against WHOOP's trademark and brand guidelines.
- **WHOOP's terms covering exported data.** Whether a third-party app may
  process a user's own exported data, and under what conditions, is a
  question about WHOOP's terms of service and developer terms. It has not
  been answered here and should not be assumed either way.
- **Health-data regulation.** Whether GDPR, UK GDPR, HIPAA, CCPA or any
  other regime applies, and in what role, depends on facts not present in
  this repository — who publishes it, where, and to whom.
- **"Not a medical device."** The app says this. Whether that disclaimer is
  sufficient in a given jurisdiction is a legal question.
- **The privacy policy** in `PRIVACY.md` describes the implementation
  accurately but has **placeholder** publisher and contact details, and has
  not been reviewed by a lawyer.
- **App Store / Google Play** — see `STORE-READINESS.md`.

---

## 12. How to re-run this audit

```
python audit_privacy.py      # in the build scratchpad: entry points, network,
                             # storage, logging, third parties, data leakage
python verify_web.py         # gates the shipped folder; fails the build on
                             # personal data, network APIs or push machinery
cycle.ps1                    # the test suite, including the privacy tests
```

`verify_web.py` is the one that matters at release: it reads the *shipped*
file and fails on personal data, on any network API, and on push
infrastructure.
