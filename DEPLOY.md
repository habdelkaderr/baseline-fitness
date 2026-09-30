# Deploying Baseline

Same architecture as HomeFix: **GitHub → Cloudflare Workers Builds → a static-assets
Worker**, with Supabase reached only from the browser. There are no GitHub
Actions and no manual `wrangler deploy` in the normal loop.

```
   local edit  →  git push  →  Cloudflare builds  →  Worker serves ./site
                                                          │
                                       (only if you turn it on, and encrypted)
                                                          ↓
                                                      Supabase
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
git remote add origin https://github.com/<you>/baseline.git
git push -u origin main
```
Check `git status` shows no `.env` before the first push.

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

### 3. Supabase — only if you want encrypted backup

**Skip this entirely and Baseline still works.** With no variables set it
builds exactly as it always has: no account, no network requests, everything
in the browser.

1. Create a project. Run `supabase/migrations/20260930000000_baseline_init.sql`
   in the SQL Editor. It creates one table with Row Level Security so a
   signed-in user can reach exactly one row — their own.
2. Worker → **Settings → Build → Variables and secrets** (these are *build*
   variables; Vite-style vars are baked in at build time):

   | Name | Value |
   |---|---|
   | `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` |
   | `VITE_SUPABASE_PUBLISHABLE_KEY` | the **publishable** / anon key |

   Never the secret or `service_role` key: it bypasses RLS, so a browser
   holding one could read every user's row. `tools/build.mjs` fails the build
   on purpose if it detects one.
3. Changing a variable needs a new build — push a commit, or
   **Deployments → Retry build**.

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

`verify_web.py` enforces the privacy guarantees mechanically — one network
entry point, gated on being configured; sync off by default; nothing uploaded
that was not encrypted first; no secret key in the bundle.

## Custom domain

The free `*.workers.dev` URL needs no purchase. A custom domain is
Worker → **Settings → Domains & Routes → Add**, and needs the domain on
Cloudflare DNS. Nothing here requires one.
