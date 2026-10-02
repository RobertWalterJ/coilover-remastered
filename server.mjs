// Minimal static server for Coilover. No dependencies.
// Serves /docs on http://localhost:8797. Same folder GitHub Pages publishes. localhost is a secure context, so the
// service worker registers and the game installs to the home screen from here.
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, normalize, extname } from 'node:path';
import { networkInterfaces } from 'node:os';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), 'docs');
const PORT = Number(process.env.PORT) || 8797;
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
  '.css': 'text/css; charset=utf-8',
  '.png': 'image/png',
  '.glb': 'model/gltf-binary',
  '.svg': 'image/svg+xml',
};

// Dev only. The page posts a rendered frame here so it can be inspected even
// when the browser tab is backgrounded and the compositor is serving a stale
// surface. Never reached by the published build.
async function saveShot(req, res) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const body = Buffer.concat(chunks).toString('utf8');
  const b64 = body.slice(body.indexOf(',') + 1);
  const q = new URL(req.url, 'http://x').searchParams.get('name') || 'latest';
  const safe = q.replace(/[^a-z0-9_-]/gi, '').slice(0, 40) || 'latest';
  await mkdir(join(dirname(fileURLToPath(import.meta.url)), 'shots'), { recursive: true });
  await writeFile(join(dirname(fileURLToPath(import.meta.url)), 'shots', safe + '.png'),
                  Buffer.from(b64, 'base64'));
  res.writeHead(200, { 'content-type': 'text/plain' }).end('ok');
}

createServer(async (req, res) => {
  try {
    if (req.method === 'POST' && req.url.split('?')[0] === '/shot') { await saveShot(req, res); return; }
    /* dev only: fetch a remote reference image so the page can measure its
       palette. Canvas cannot read a cross origin image, and reading pixels is
       the whole point. Nothing is stored. */
    if (req.url.startsWith('/ref?')) {
      const u = new URL(req.url, 'http://x').searchParams.get('u');
      try {
        const r = await fetch(u);
        const b = Buffer.from(await r.arrayBuffer());
        res.writeHead(200, { 'content-type': r.headers.get('content-type') || 'image/jpeg',
                             'access-control-allow-origin': '*' });
        res.end(b);
      } catch (e) { res.writeHead(502); res.end(String(e)); }
      return;
    }
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p.endsWith('/')) p += 'index.html';
    // join plus normalize collapses any ".." segments; the prefix check below
    // is what actually keeps requests inside /app.
    const file = join(ROOT, normalize(p));
    if (!file.startsWith(ROOT)) { res.writeHead(403).end('forbidden'); return; }
    const body = await readFile(file);
    res.writeHead(200, {
      'content-type': TYPES[extname(file)] || 'application/octet-stream',
      'cache-control': 'no-cache',
    });
    res.end(body);
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain' }).end('not found');
  }
}).listen(PORT, () => {
  console.log(`Coilover  ->  http://localhost:${PORT}`);
  for (const list of Object.values(networkInterfaces())) {
    for (const n of list || []) {
      if (n.family === 'IPv4' && !n.internal) console.log(`  on your phone  ->  http://${n.address}:${PORT}`);
    }
  }
});
