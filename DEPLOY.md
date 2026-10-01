# Deploying Baseline

Baseline is hosted on **GitHub Pages**, served from the **root of `main`**.

```
   local edit  ->  python tools/make_web.py  ->  git push  ->  Pages redeploys
```

Live: https://habdelkaderr.github.io/baseline-fitness/

## Why the root, and why that matters more than it looks

GitHub Pages can serve a branch from its root or from `/docs`, and nothing
else. The root is what has always been used here — and the URL is not a
detail: a browser keys IndexedDB to the origin and path, so every existing
install's training history lives under *that* address. Move the app to a
different path and each user opens a perfectly working, completely empty app
while their data sits where they can no longer see it.

So `tools/make_web.py` writes the deployed files to the repository root:

| | |
|---|---|
| `index.html` | the whole app, concatenated from `src/*.part` |
| `sw.js`, `manifest.webmanifest` | offline shell and install metadata |
| `icons/` | generated from `brand/icon-source.png` (needs Pillow) |
| `.nojekyll` | stops Jekyll touching the output |

It has no `shutil.rmtree`: clearing its own output folder is safe for a
`site/` directory and would delete the repository from here.

## Publishing an update

```bash
python tools/make_web.py     # rebuilds index.html, sw.js, manifest, icons
git add .
git commit -m "..."
git push
```

Pages redeploys within a minute or two. `APP_BUILD` in `src/p02.part` is a
date plus a letter — bump it so Settings -> About can tell today's build from
a cached copy of yesterday's, which is most of the diagnosis when someone
says an update "did not arrive".

The service worker cache name in `tools/make_web.py` (`baseline-vNN`) must
also go up whenever the shell changes, or returning visitors keep the old
files.

## Before pushing a change to the app

```powershell
powershell -File tools/serve.ps1        # local static server on :8801
powershell -File tools/cycle.ps1        # build + unit suite
powershell -File tools/run_layout.ps1   # 11 viewports x 2 themes
cd tools; python make_web.py; python verify_web.py; python audit_privacy.py
```

`verify_web.py` enforces the privacy guarantees mechanically — no `fetch`, no
beacon, no socket, no external origin, and `connect-src 'self'` in the
document's own Content-Security-Policy. It also fails when `index.html` does
not match `src/`, which is how a stale build once passed every other check.

`run_layout.ps1` counts a thrown audit as a failure. It used to print nothing
for a throw and sum a total that a throw never emits, so eleven dead
viewports reported zero issues.

## No response headers on this host

GitHub Pages cannot set headers, so there is no `_headers` file and the CSP
ships as a `<meta http-equiv>` in `src/p01.part`. One consequence worth
knowing: `frame-ancestors` is ignored in a meta element, so clickjacking
cannot be refused from here. Everything else in the policy applies normally.
