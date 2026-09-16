# Baseline

A private, local-first training system. It decides what you should train each
day from your recovery, your recent activity and your goals — and it works with
or without WHOOP.

**Live app:** enable GitHub Pages (below), then open the URL it gives you.

## Your data

Everything you enter stays in **your own browser**, in IndexedDB, on the device
you entered it on. This repository hosts the application code and nothing else.

- No accounts, no server, no database, no analytics, no trackers
- Nothing is uploaded anywhere — there is no endpoint to upload to
- WHOOP CSVs are parsed inside the browser and never leave the device
- Each browser on each device keeps a completely separate dataset
- Moving data between devices is a manual JSON export/import

**Never commit your WHOOP export or a backup JSON to this repository.** Anything
committed is permanent and recoverable from git history, and Pages sites are
public even when the repository is private.

## Enable GitHub Pages

    Settings → Pages → Build and deployment
      Source: Deploy from a branch
      Branch: main      Folder: / (root)
      Save

Wait 1–3 minutes, then open `https://<user>.github.io/<repo>/` (keep the
trailing slash).

> On a free GitHub account, Pages requires a **public** repository. GitHub Pro
> allows Pages from a private repo, but the published site is still public
> either way. That is fine here: the code contains no personal data.

## Install it

**iPhone/iPad (Safari):** open the URL → Share (□↑) → **Add to Home Screen**
**Android (Chrome):** menu → **Install app**
**Windows/macOS (Chrome/Edge):** install icon in the address bar
**macOS (Safari):** File → **Add to Dock**

Installed versions share the same local data as the browser tab.

## Offline

After the first successful load the service worker caches the app shell, so it
opens and works with no internet. Your data was never coming from the network
anyway.

## Files

    index.html              the entire application
    manifest.webmanifest    PWA metadata (name, icons, standalone display)
    sw.js                   service worker — offline caching
    .nojekyll               tells GitHub Pages to skip Jekyll
    icons/                  home screen and install icons

## Back up

Settings → **Backup JSON**, weekly. Clearing browser data erases everything, and
no copy exists anywhere else.

---

Not a medical device. It does not diagnose anything. Persistent pain, symptoms
or unusual physiological readings belong with a qualified healthcare
professional, separately from any training decision.
