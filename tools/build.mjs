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
//
// There is no build-time configuration and nothing is injected. Baseline has
// no backend: Cloudflare serves these files and the app then talks to nothing.

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

let html = PARTS.map((n) => {
  const p = join(SRC, `${n}.part`);
  if (!existsSync(p)) throw new Error(`missing source part: ${n}.part`);
  return readFileSync(p, 'utf8');
}).join('');

// icons live in icons/ once packaged; point the document links at them
html = html.replace('href="icon-180.png"', 'href="icons/icon-180.png"');
html = html.replace('href="icon-512.png"', 'href="icons/icon-512.png"');

if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, 'index.html'), html, 'utf8');

// GitHub Pages compatibility is kept: the repo can still be served from Pages.
writeFileSync(join(OUT, '.nojekyll'), '', 'utf8');

// ------------------------------------------------------------------ headers
// Cloudflare reads _headers from the served directory. connect-src is the
// line that matters: 'self' and nothing else, so the browser itself refuses
// any attempt by this page to contact an outside origin. The privacy claim in
// the app is enforced here as well as being true of the code.
writeFileSync(join(OUT, '_headers'), `/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'

/index.html
  Cache-Control: no-cache

/sw.js
  Cache-Control: no-cache

/icons/*
  Cache-Control: public, max-age=31536000, immutable
`, 'utf8');

const kb = (Buffer.byteLength(html, 'utf8') / 1024).toFixed(1);
console.log(`site/index.html   ${kb} KB  (${PARTS.length} parts)`);
console.log(`site/_headers     connect-src 'self' (no external origins)`);
