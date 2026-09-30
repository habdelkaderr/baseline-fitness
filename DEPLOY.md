# Deploying Baseline

Same hosting architecture as HomeFix: **GitHub → Cloudflare Workers Builds → a
static-assets Worker**. There are no GitHub Actions and no manual
`wrangler deploy` in the normal loop.

Baseline has **no backend**. Cloudflare serves the files; the app then talks to
nothing. There is no database, no account and no API to configure.

```
   local edit  →  git push  →  Cloudflare builds  →  Worker serves ./site
```

## How this differs from HomeFix, and why

HomeFix is a React/Vite app: `npm run build` compiles `src/` into `dist/`.
Baseline is one static HTML file assembled from `src/*.part`, and its icon set
is generated from `brand/icon-source.png` by `tools/make_web.py`, which needs
Pillow. Cloudflare's build image has Node but not Pillow, and the icons change
roughly never — so the build is split by what changes:

| Artifact | Built by | When |
|---|---|---|
| `site/index.html` | `tools/build.mjs` (Node, no dependencies) | every push |
| `site/_headers` | `tools/build.mjs` | every push |
| `site/icons/`, `manifest.webmanifest`, `sw.js` | `tools/make_web.py` (local) | when icons or the service worker change |

`tools/build.mjs` produces output byte-identical to `tools/make_web.py` for
`index.html` (verified), so pushing a `src/*.part` edit deploys correctly
without running Python. `site/` is committed because it holds those generated
assets.

## One-time setup

### 1. GitHub
```bash
git remote add origin https://github.com/habdelkaderr/baseline-fitness.git
git push -u origin main
```

### 2. Cloudflare
Dashboard → **Workers & Pages → Create → Workers → Import a repository**, pick
the repo, and set:

| Setting | Value |
|---|---|
| Build command | `npm run build` |
| Deploy command | `npx wrangler deploy` |
| Root directory | *(leave empty)* |

`wrangler.jsonc` serves `./site` with `not_found_handling:
"single-page-application"`. The `name` there must match the Worker's name in
the dashboard. Do not add a `_redirects` file with `/* /index.html 200` —
Workers reject it as an infinite loop.

`npm install` has nothing to install: `package.json` declares no dependencies
on purpose, so there is nothing in the deploy path that can break or need
auditing.

`.node-version` pins Node 22 for the build.

## Publishing an update

```bash
git add .
git commit -m "..."
git push
```

Cloudflare rebuilds and deploys in about a minute. Every push to another branch
gets its own preview URL. Rollback: **Deployments → pick an older one →
Rollback**.

If you changed the icons or the service worker, run `python tools/make_web.py`
first so the regenerated assets are in the commit.

## Before pushing a change to the app itself

The verification chain is unchanged and still the gate:

```powershell
powershell -File tools/serve.ps1        # local static server on :8801
powershell -File tools/cycle.ps1        # build + unit suite
powershell -File tools/run_layout.ps1   # 11 viewports x 2 themes
cd tools; python make_web.py; python verify_web.py; python audit_privacy.py
```

`verify_web.py` enforces the privacy guarantees mechanically — no `fetch`, no
beacon, no socket, no external origin, and `connect-src 'self'` in the shipped
headers so the browser refuses an outbound connection even if one were added by
mistake. It also fails if `site/` is older than `src/`, which is how a stale
build once passed every other check.

## Custom domain

The free `*.workers.dev` URL needs no purchase. A custom domain is
Worker → **Settings → Domains & Routes → Add**, and needs the domain on
Cloudflare DNS. Nothing here requires one.
