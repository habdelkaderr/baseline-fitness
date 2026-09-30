// Baseline — Cloudflare/Node build.
//
// WHY THIS EXISTS ALONGSIDE tools/make_web.py
// -------------------------------------------
// make_web.py is the full local packager: it generates the PNG icon set from
// brand/icon-source.png (needs Pillow), writes the manifest and the service
// worker, and assembles site/. Cloudflare's build image has Node but not
// Pillow, and the icons change roughly never.
//
// So the split is by what changes: this script rebuilds the ONE artifact that
// changes on every commit - site/index.html, concatenated from src/*.part -
// and leaves the generated assets (icons/, manifest.webmanifest, sw.js) exactly
// as they were committed. Run make_web.py locally when the icons or the service
// worker change; push, and Cloudflare runs this.
//
// It has no dependencies on purpose. `npm install` has nothing to install, so
// there is nothing in the deploy path that can break.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'src');
const OUT = join(ROOT, 'site');

// The same order cycle.ps1 and make_web.py use. A missing or reordered part
// produces a file that parses and misbehaves, so this list is the contract.
const PARTS = ['p01', 'p02', 'p03', 'p03b', 'p04', 'p04b',
               'p05', 'p06', 'p07', 'p08', 'p09', 'p10'];

// ---------------------------------------------------------------- the app
let html = PARTS.map((n) => {
  const p = join(SRC, `${n}.part`);
  if (!existsSync(p)) throw new Error(`missing source part: ${n}.part`);
  return readFileSync(p, 'utf8');
}).join('');

// icons live in icons/ once packaged; point the document links at them
html = html.replace('href="icon-180.png"', 'href="icons/icon-180.png"');
html = html.replace('href="icon-512.png"', 'href="icons/icon-512.png"');

// ------------------------------------------------ build-time configuration
// Vite bakes VITE_* vars into the bundle at build time. Baseline has no
// bundler, so the same job is done here: a single JSON blob written into the
// document from the build environment.
//
// EMPTY IS THE DEFAULT AND THE SAFE STATE. With no variables set, sync is
// impossible: there is no endpoint to reach and no key to reach it with, so
// the app behaves exactly as it always has - local only, no network.
const cfg = {
  supabaseUrl: (process.env.VITE_SUPABASE_URL || '').replace(/\/+$/, ''),
  supabaseKey: process.env.VITE_SUPABASE_PUBLISHABLE_KEY || '',
  build: process.env.CF_PAGES_COMMIT_SHA || process.env.GITHUB_SHA || '',
};
// Refuse to ship a secret. A service-role or secret key in the browser grants
// every caller full table access regardless of RLS, and pasting one into the
// wrong Cloudflare variable is an easy mistake to make.
if (/^sb_secret_|service_role/i.test(cfg.supabaseKey)) {
  throw new Error(
    'VITE_SUPABASE_PUBLISHABLE_KEY looks like a SECRET key. Only the ' +
    'publishable (sb_publishable_...) or legacy anon key may reach a browser.'
  );
}
const MARK = '/*__BASELINE_CONFIG__*/';
if (html.includes(MARK)) {
  html = html.replace(MARK, `window.BASELINE_CONFIG=${JSON.stringify(cfg)};`);
} else if (cfg.supabaseUrl) {
  throw new Error('config placeholder not found in src/ but Supabase vars are set');
}

if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, 'index.html'), html, 'utf8');

// GitHub Pages compatibility is kept: the repo can still be served from Pages.
writeFileSync(join(OUT, '.nojekyll'), '', 'utf8');

// ------------------------------------------------------------- headers
// Cloudflare reads _headers from the served directory. connect-src is the
// line that matters: it is the allow-list for where this app may send
// anything, and it names Supabase only when Supabase is configured.
const connect = cfg.supabaseUrl
  ? `'self' ${cfg.supabaseUrl} ${cfg.supabaseUrl.replace(/^https:/, 'wss:')}`
  : `'self'`;
writeFileSync(join(OUT, '_headers'), `/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src ${connect}; frame-ancestors 'none'; base-uri 'self'; form-action 'none'

/index.html
  Cache-Control: no-cache

/sw.js
  Cache-Control: no-cache

/icons/*
  Cache-Control: public, max-age=31536000, immutable
`, 'utf8');

const kb = (Buffer.byteLength(html, 'utf8') / 1024).toFixed(1);
console.log(`site/index.html   ${kb} KB  (${PARTS.length} parts)`);
console.log(`site/_headers     connect-src ${connect}`);
console.log(cfg.supabaseUrl
  ? `Supabase          configured (${cfg.supabaseUrl})`
  : `Supabase          not configured - local-only build`);
