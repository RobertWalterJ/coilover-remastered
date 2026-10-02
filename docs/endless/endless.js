// Endless: drive a seeded, never ending Coilover world. Roads or off road, the choice is yours.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const $ = (id) => document.getElementById(id);
const say = (t) => { $('msg').textContent = t; $('msg').hidden = !t; };
const fail = (e) => { say('Could not start: ' + (e && e.message || e)); console.error(e); };
addEventListener('error', (e) => fail(e.error || e.message)); addEventListener('unhandledrejection', (e) => fail(e.reason));

// ---------------------------------------------------------------- renderer, scene, light
const canvas = $('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, 1, 0.3, 1400);
const sun = new THREE.DirectionalLight(0xfff0dc, 2.6); sun.castShadow = true;
Object.assign(sun.shadow.camera, { left: -70, right: 70, top: 70, bottom: -70, near: 1, far: 400 }); sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0006;
const hemi = new THREE.HemisphereLight(0xc4d6ea, 0x6b5a48, 0.85);
scene.add(sun, sun.target, hemi);
scene.fog = new THREE.FogExp2(0xbfd0dc, 0.0032);
const world = new THREE.Group(); scene.add(world);                 // everything placed in world coordinates; shifted by the floating origin
let ox = 0, oz = 0;

// ---------------------------------------------------------------- assets
const b64 = (t) => { const s = atob(t.trim()); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u.buffer; };
const loader = new GLTFLoader();
const glb = (name) => fetch('assets/' + name + '.glb.b64.txt').then(r => r.text()).then(t => new Promise((res, rej) => loader.parse(b64(t), '', res, rej)));
say('Loading the models');
const [profiles, floraS, floraD, bodyG, wheelG] = await Promise.all([
  fetch('assets/weather_profiles.json').then(r => r.json()), glb('flora_shield'), glb('flora_desert'), glb('bracken_body'), glb('bracken_wheels')]);
const WX = window.CoiloverWeather.init(THREE, profiles, { biome: 'shield' });

// ---------------------------------------------------------------- the world
let seedText = 'lake effect';
try { seedText = localStorage.getItem('endless-seed') || seedText; } catch (e) {}
let G = window.CoiloverWorld.create(seedText);
const COARSE = matchMedia('(pointer: coarse)').matches;
const CH = 128, NG = 32, RT = COARSE ? 3 : 4, RF = 2;                            // chunk size, grid cells per chunk, terrain and flora rings

const groundMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.96, flatShading: true }); groundMat.userData.role = 'soil';
const waterMat = new THREE.MeshStandardMaterial({ color: 0x2b4a55, roughness: 0.12, metalness: 0.15, transparent: true, opacity: 0.88 }); waterMat.userData.role = 'water';
const waterGeo = new THREE.PlaneGeometry(CH, CH).rotateX(-Math.PI / 2).translate(CH / 2, 0, CH / 2);
const roadMat = { paved: mk(0x3d3b3e, 0.82, 'asphalt'), gravel: mk(0x8a7c69, 0.95, 'soil'), shoulder: mk(0x7d7466, 0.95, 'soil'),
  white: mk(0xe9e5d8, 0.6, 'paint'), yellow: mk(0xe3b13a, 0.6, 'paint'), rail: mk(0xb9bcbf, 0.4, 'metal'), post: mk(0x6b5a4a, 0.85, 'wood'), wall: mk(0xa9a49a, 0.9, 'concrete') };
function mk(c, r, role) { const m = new THREE.MeshStandardMaterial({ color: c, roughness: r, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 }); m.userData.role = role; return m; }
WX.register(new THREE.Mesh(waterGeo, waterMat)); Object.values(roadMat).forEach(m => WX.register(new THREE.Mesh(waterGeo, m)));
WX.register(new THREE.Mesh(waterGeo, groundMat));

// ---- terrain chunks, built a few rows per frame
const chunks = new Map();
function* buildChunk(ci, cj) {
  const x0 = ci * CH, z0 = cj * CH, n = NG + 1, st = CH / NG, S = new Array(n * n);
  for (let j = 0; j < n; j++) { for (let i = 0; i < n; i++) S[j * n + i] = G.sample(x0 + i * st, z0 + j * st); yield; }
  const pos = new Float32Array(NG * NG * 6 * 3), col = new Float32Array(NG * NG * 6 * 3); let p = 0, minH = 1e9;
  const put = (i, j, c) => { const s = S[j * n + i]; pos[p] = i * st; pos[p + 1] = s.h; pos[p + 2] = j * st; col[p] = c[0] ** 2.2; col[p + 1] = c[1] ** 2.2; col[p + 2] = c[2] ** 2.2; p += 3; minH = Math.min(minH, s.h); };
  for (let j = 0; j < NG; j++) for (let i = 0; i < NG; i++) {
    const a = S[j * n + i], b = S[j * n + i + 1], c = S[(j + 1) * n + i], d = S[(j + 1) * n + i + 1];
    const slope = Math.min(1, (Math.abs(a.h - d.h) + Math.abs(b.h - c.h)) / (2 * st * 1.414));
    const s0 = { h: (a.h + b.h + c.h + d.h) / 4, b: a.b, sand: (a.sand + d.sand) / 2, kind: a.kind };
    const cc = G.colour(x0 + (i + 0.5) * st, z0 + (j + 0.5) * st, s0, slope);
    if (Math.abs(a.h - d.h) < Math.abs(b.h - c.h)) { put(i, j, cc); put(i, j + 1, cc); put(i + 1, j + 1, cc); put(i, j, cc); put(i + 1, j + 1, cc); put(i + 1, j, cc); }
    else { put(i, j, cc); put(i, j + 1, cc); put(i + 1, j, cc); put(i + 1, j, cc); put(i, j + 1, cc); put(i + 1, j + 1, cc); }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.computeVertexNormals();
  const m = new THREE.Mesh(g, groundMat); m.position.set(x0, 0, z0); m.receiveShadow = true;
  const grp = new THREE.Group(); grp.add(m);
  if (minH < G.WATER) { const w = new THREE.Mesh(waterGeo, waterMat); w.position.set(x0, G.WATER, z0); w.receiveShadow = true; grp.add(w); }
  return grp;
}
// ---- flora: one InstancedMesh per variant part, shared by every chunk
const LIBS = { shield: floraS.scene, desert: floraD.scene };
const DESERT_KINDS = new Set(['sage', 'creosote', 'dry_grass', 'saguaro', 'juniper', 'sandstone', 'prickly_pear', 'barrel', 'ocotillo', 'hoodoo', 'scree', 'deadwood', 'slab', 'spiketree', 'tumbleweed']);
const SHADOW = /spruce|fir|pine|birch|maple|aspen|tamarack|snag|saguaro|juniper_\d|spiketree|hoodoo|sandstone|boulder|alder/;
const pools = new Map();
function variant(kind, v, biome) {
  const lib = (biome === 'desert' && DESERT_KINDS.has(kind)) || !LIBS.shield.getObjectByName(kind + '_0') ? 'desert' : 'shield';
  let root = LIBS[lib].getObjectByName(kind + '_' + v) || LIBS[lib].getObjectByName(kind + '_0');
  return root ? { key: lib + ':' + root.name, root } : null;
}
function pool(key, root) {
  if (pools.has(key)) return pools.get(key);
  root.updateMatrixWorld(true);
  const inv = new THREE.Matrix4().copy(root.matrixWorld).invert(), parts = [], cap = /grass|fern|blueberry|sage|creosote|dry_grass|shrub|juniper_mat|reeds|cattails/.test(root.name) ? 3000 : 1600;
  root.traverse(o => {
    if (!o.isMesh) return;
    let layer = 'main', q = o; while (q && q !== root) { const m = /_(snow|leaves|main)$/.exec(q.name); if (m) { layer = m[1]; break; } q = q.parent; }
    const im = new THREE.InstancedMesh(o.geometry, o.material, cap); im.count = 0; im.frustumCulled = false;
    im.castShadow = SHADOW.test(root.name) && layer !== 'snow'; im.receiveShadow = true;
    // weather.js toggles nodes named *_snow and *_leaves; the main part gets a neutral name
    const holder = new THREE.Group(); holder.name = layer === 'main' ? root.name + '_body' : root.name + '_' + layer;
    im.name = holder.name + '_im'; holder.add(im); world.add(holder);
    parts.push({ im, local: new THREE.Matrix4().copy(inv).multiply(o.matrixWorld), holder });
    WX.register(holder);
  });
  const P = { parts, cap, free: [], top: 0 }; pools.set(key, P); return P;
}
const tmpM = new THREE.Matrix4(), tmpQ = new THREE.Quaternion(), tmpS = new THREE.Vector3(), tmpP = new THREE.Vector3(), ZERO = new THREE.Matrix4().makeScale(0, 0, 0), UP = new THREE.Vector3(0, 1, 0);
function plant(it, biome) {
  const vr = variant(it.kind, it.v, biome); if (!vr) return null;
  const P = pool(vr.key, vr.root);
  const idx = P.free.length ? P.free.pop() : (P.top < P.cap ? P.top++ : -1); if (idx < 0) return null;
  tmpM.compose(tmpP.set(it.x, it.y - 0.05, it.z), tmpQ.setFromAxisAngle(UP, it.yaw), tmpS.setScalar(it.s));
  for (const pt of P.parts) { pt.im.setMatrixAt(idx, new THREE.Matrix4().multiplyMatrices(tmpM, pt.local)); pt.im.count = Math.max(pt.im.count, P.top); pt.im.instanceMatrix.needsUpdate = true; }
  return [P, idx];
}
function unplant(list) { for (const [P, idx] of list) { for (const pt of P.parts) { pt.im.setMatrixAt(idx, ZERO); pt.im.instanceMatrix.needsUpdate = true; } P.free.push(idx); } }

// ---- roads, rails and towns, per cell
const roads = new Map(), towns = new Map();
function ribbon(R, l0, l1, lift, mat, keep) {
  const P = [], I = []; let prev = -1;
  for (let q = 0; q <= R.n; q++) {
    const qa = Math.max(0, q - 1), qb = Math.min(R.n, q + 1); let tx = R.x[qb] - R.x[qa], tz = R.z[qb] - R.z[qa]; const tl = Math.hypot(tx, tz); tx /= tl; tz /= tl;
    const nx = tz, nz = -tx, ok = !keep || keep(q);
    const base = P.length / 3;
    P.push(R.x[q] + nx * l0 - R.x[0], R.y[q] + lift, R.z[q] + nz * l0 - R.z[0], R.x[q] + nx * l1 - R.x[0], R.y[q] + lift, R.z[q] + nz * l1 - R.z[0]);
    if (q > 0 && ok && prev >= 0) I.push(prev, base, prev + 1, prev + 1, base, base + 1);
    prev = base;
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setIndex(I); g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat); m.receiveShadow = true; return m;
}
function buildRoad(R) {
  const g = new THREE.Group(); g.position.set(R.x[0], 0, R.z[0]); const h = R.half;
  g.add(ribbon(R, -h - 1.8, h + 1.8, 0.02, roadMat.shoulder));
  g.add(ribbon(R, -h, h, 0.06, R.paved ? roadMat.paved : roadMat.gravel));
  if (R.paved) {
    for (const s of [-1, 1]) g.add(ribbon(R, s * (h - 0.35), s * (h - 0.2), 0.075, roadMat.white));
    g.add(ribbon(R, -0.2, -0.08, 0.075, roadMat.yellow)); g.add(ribbon(R, 0.08, 0.2, 0.075, roadMat.yellow));
  } else for (const s of [-1, 1]) g.add(ribbon(R, s * 1.2 - 0.3, s * 1.2 + 0.3, 0.07, roadMat.shoulder));
  // rails where the road is built up: over water a low concrete parapet, on high fills a guard rail on posts
  const over = (q) => R.raw[q] < G.WATER + 0.4, fill = (q) => R.y[q] - R.raw[q] > 2.6 && !over(q);
  for (const s of [-1, 1]) {
    const wall = ribbon(R, s * (h + 0.35), s * (h + 0.6), 0.85, roadMat.wall, over); g.add(wall);
    g.add(ribbon(R, s * (h + 0.6), s * (h + 0.6) + s * 0.001, 0.0, roadMat.wall, over));
    g.add(ribbon(R, s * (h + 0.7), s * (h + 0.78), 0.72, roadMat.rail, fill));
  }
  const posts = []; for (let q = 0; q <= R.n; q++) if (fill(q)) posts.push(q);
  if (posts.length) {
    const pg = new THREE.BoxGeometry(0.12, 0.8, 0.12).translate(0, 0.4, 0), im = new THREE.InstancedMesh(pg, roadMat.post, posts.length * 2); let k = 0;
    for (const q of posts) for (const s of [-1, 1]) {
      const qb = Math.min(R.n, q + 1), qa = Math.max(0, q - 1); let tx = R.x[qb] - R.x[qa], tz = R.z[qb] - R.z[qa]; const tl = Math.hypot(tx, tz);
      im.setMatrixAt(k++, tmpM.makeTranslation(R.x[q] + (tz / tl) * s * (h + 0.74) - R.x[0], R.y[q], R.z[q] - (tx / tl) * s * (h + 0.74) - R.z[0]));
    }
    g.add(im);
  }
  // over water the deck sits on piers so it reads as a bridge from the shore
  const piers = []; for (let q = 0; q <= R.n; q += 3) if (R.raw[q] < G.WATER - 0.8) piers.push(q);
  if (piers.length) {
    const pg = new THREE.BoxGeometry(1.2, 1, 2 * h + 1.4).translate(0, -0.5, 0), im = new THREE.InstancedMesh(pg, roadMat.wall, piers.length); let k = 0;
    for (const q of piers) {
      const qb = Math.min(R.n, q + 1), qa = Math.max(0, q - 1), yaw = Math.atan2(R.x[qb] - R.x[qa], R.z[qb] - R.z[qa]);
      const depth = R.y[q] - R.raw[q] + 0.5;
      im.setMatrixAt(k++, tmpM.compose(tmpP.set(R.x[q] - R.x[0], R.y[q] - 0.05, R.z[q] - R.z[0]), tmpQ.setFromAxisAngle(UP, yaw + Math.PI / 2), tmpS.set(1, depth, 1)));
    }
    g.add(im);
  }
  WX.register(g); return g;
}
const HOUSE = { house: [0xe7dcc6, 0xb8c9c8, 0xd9a07a, 0xcfd3c4, 0xe2c27e], store: [0xe8e2d4], barn: [0xa8432f], garage: [0x9aa1a3], chapel: [0xf1ece2] };
const roof = mk(0x5a4a44, 0.7, 'metal'), roofTin = mk(0x8a9296, 0.45, 'metal'), door = mk(0x5c3d2e, 0.8, 'wood'), win = mk(0x28343c, 0.2, 'glass');
const wallMats = {}; function wallMat(c) { return wallMats[c] || (wallMats[c] = (() => { const m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.88 }); m.userData.role = 'paint'; return m; })()); }
function buildTown(T) {
  const g = new THREE.Group();
  for (const hs of T.houses) {
    const y = G.height(hs.x, hs.z), h = new THREE.Group(), pal = HOUSE[hs.kind], c = pal[Math.floor(G.hash(Math.round(hs.x), Math.round(hs.z), 9) * pal.length)];
    const w = hs.w, d = hs.d, ht = hs.kind === 'barn' ? hs.h + 2 : hs.h;
    const body = new THREE.Mesh(new THREE.BoxGeometry(w, ht + 2, d).translate(0, ht / 2 - 1, 0), wallMat(c)); body.castShadow = body.receiveShadow = true; h.add(body);
    const rise = hs.kind === 'garage' || hs.kind === 'store' ? 0.6 : d * 0.38;
    const rg = new THREE.BufferGeometry(); const hw = w / 2 + 0.3, hd = d / 2 + 0.4;
    rg.setAttribute('position', new THREE.Float32BufferAttribute([-hw, ht, -hd, hw, ht, -hd, hw, ht + rise, 0, -hw, ht, -hd, hw, ht + rise, 0, -hw, ht + rise, 0,
      -hw, ht, hd, -hw, ht + rise, 0, hw, ht + rise, 0, -hw, ht, hd, hw, ht + rise, 0, hw, ht, hd,
      -hw, ht, -hd, -hw, ht + rise, 0, -hw, ht, hd, hw, ht, -hd, hw, ht, hd, hw, ht + rise, 0], 3)); rg.computeVertexNormals();
    const r = new THREE.Mesh(rg, hs.kind === 'barn' || hs.kind === 'garage' ? roofTin : roof); r.castShadow = true; h.add(r);
    const dr = new THREE.Mesh(new THREE.BoxGeometry(1.1, 2.1, 0.08).translate(0, 1.05, d / 2 + 0.03), door); h.add(dr);
    for (const s of [-1, 1]) h.add(new THREE.Mesh(new THREE.BoxGeometry(1.3, 1.1, 0.06).translate(s * w * 0.3, ht * 0.55, d / 2 + 0.03), win));
    if (hs.kind === 'chapel') h.add(new THREE.Mesh(new THREE.BoxGeometry(1.8, 4.5, 1.8).translate(0, ht + rise + 1.4, d * 0.3), wallMat(c)));
    h.position.set(hs.x, y, hs.z); h.rotation.y = hs.yaw; g.add(h);
  }
  WX.register(g); return g;
}

// ---------------------------------------------------------------- the truck (Coilover's Bracken, remastered)
const V = { track: 2.06, wb: 3.10, rb: 0.5, wheelR: 0.55, rest: 0.60, bodyY: -0.18 };
const truck = new THREE.Group(); truck.rotation.order = 'YXZ'; scene.add(truck);
const body = bodyG.scene; body.position.y = V.bodyY; body.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); truck.add(body);
const corners = [];
for (let k = 0; k < 4; k++) {
  const mx = (k % 2 === 0 ? 1 : -1) * V.track / 2, mz = k < 2 ? V.wb * V.rb : -V.wb * (1 - V.rb);
  const hub = new THREE.Group(), spin = new THREE.Group(); hub.add(spin);
  const w = wheelG.scene.clone(true); w.traverse(o => { if (o.isMesh) o.castShadow = true; });
  ['wheel', 'rim', 'disc'].forEach(n => { const o = w.getObjectByName('bracken_' + n); if (o) spin.add(o); });
  const cal = w.getObjectByName('bracken_caliper'); if (cal) hub.add(cal);
  if (mx < 0) hub.scale.x = -1;
  hub.position.set(mx, -0.06 - V.rest * 0.6, mz); truck.add(hub);
  corners.push({ mx, mz, hub, spin, len: V.rest * 0.6 });
}
const car = { x: 0, z: 0, y: 0, vy: 0, yaw: 0, v: 0, steer: 0, pitch: 0, roll: 0, spin: 0, air: false, lastT: 0 };
function spawn() {
  const R = G.cellRoads(0, 0)[0], q = 6;
  car.x = R.x[q]; car.z = R.z[q]; car.yaw = Math.atan2(R.x[q + 1] - R.x[q], R.z[q + 1] - R.z[q]);
  const rx = -Math.cos(car.yaw), rz = Math.sin(car.yaw); car.x += rx * 1.9; car.z += rz * 1.9;            // the right hand lane
  car.y = G.height(car.x, car.z) + 1.2; car.v = 0; car.vy = 0; car.lastT = car.y;
  ox = Math.round(car.x / 256) * 256; oz = Math.round(car.z / 256) * 256; world.position.set(-ox, 0, -oz);
}

// ---------------------------------------------------------------- input
const keys = {}, touch = { gas: 0, brake: 0, left: 0, right: 0 };
addEventListener('keydown', e => { keys[e.code] = true; if (e.code === 'KeyC') toggleCruise(); if (/Arrow/.test(e.code)) e.preventDefault(); });
addEventListener('keyup', e => { keys[e.code] = false; });
document.querySelectorAll('[data-pad]').forEach(b => {
  const k = b.dataset.pad, on = (e) => { e.preventDefault(); touch[k] = 1; b.classList.add('on'); b.setPointerCapture(e.pointerId); }, off = () => { touch[k] = 0; b.classList.remove('on'); };
  b.addEventListener('pointerdown', on); b.addEventListener('pointerup', off); b.addEventListener('pointercancel', off); b.addEventListener('lostpointercapture', off);
});
let camYaw = 0, drag = null;
canvas.addEventListener('pointerdown', e => { drag = { x: e.clientX }; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener('pointermove', e => { if (!drag) return; camYaw -= (e.clientX - drag.x) * 0.006; drag.x = e.clientX; });
canvas.addEventListener('pointerup', () => drag = null);

// ---------------------------------------------------------------- cruise: follow the road network, choosing at each junction
const AP = { on: false, road: null, dir: 1, q: 0, turns: 0 };
function toggleCruise(force) {
  AP.on = force !== undefined ? force : !AP.on;
  if (AP.on) {
    const nr = G.nearestRoad(car.x, car.z, 60);
    if (!nr.road) { AP.on = false; flash('No road close by. Drive to one first.'); }
    else { AP.road = nr.road; AP.q = nr.q; const tx = nr.road.x[nr.q + 1] - nr.road.x[nr.q], tz = nr.road.z[nr.q + 1] - nr.road.z[nr.q]; AP.dir = tx * Math.sin(car.yaw) + tz * Math.cos(car.yaw) >= 0 ? 1 : -1; }
  }
  $('cruise').setAttribute('aria-pressed', String(AP.on));
}
$('cruise').onclick = () => toggleCruise();
function cruise() {
  let R = AP.road, best = AP.q, bd = 1e9;
  for (let k = -4; k <= 14; k++) { const q = AP.q + k * AP.dir; if (q < 0 || q > R.n) continue; const d = Math.hypot(R.x[q] - car.x, R.z[q] - car.z); if (d < bd) { bd = d; best = q; } }
  AP.q = best;
  if (bd > 40) { toggleCruise(false); flash('Left the road, so cruise is off.'); return null; }
  let tq = AP.q + AP.dir * 3;
  if (tq < 0 || tq > R.n) {                                                 // a junction: pick the next road
    const nd = AP.dir > 0 ? R.b : R.a, legs = G.nodeRoads(nd.i, nd.j).filter(l => l.road.id !== R.id);
    const hx = Math.sin(car.yaw), hz = Math.cos(car.yaw);
    const opts = legs.map(l => { const r = l.road, q0 = l.from === 'a' ? 0 : r.n, q1 = l.from === 'a' ? 4 : r.n - 4; const dx = r.x[q1] - r.x[q0], dz = r.z[q1] - r.z[q0], dl = Math.hypot(dx, dz); return { l, dot: (dx * hx + dz * hz) / dl }; }).filter(o => o.dot > -0.3);
    const pickFrom = opts.length ? opts : legs.map(l => ({ l }));
    const choice = pickFrom[Math.floor(G.hash(nd.i, nd.j, 900 + AP.turns++) * pickFrom.length)].l;
    AP.road = R = choice.road; AP.dir = choice.from === 'a' ? 1 : -1; AP.q = choice.from === 'a' ? 0 : R.n; tq = AP.q + AP.dir * 3;
  }
  tq = Math.max(0, Math.min(R.n, tq));
  const qa = Math.max(0, tq - 1), qb = Math.min(R.n, tq + 1); let tx = (R.x[qb] - R.x[qa]) * AP.dir, tz = (R.z[qb] - R.z[qa]) * AP.dir; const tl = Math.hypot(tx, tz); tx /= tl; tz /= tl;
  const lane = 1.9, gx = R.x[tq] - tz * lane, gz = R.z[tq] + tx * lane;      // right hand lane: right of travel is (-tz, tx)
  let diff = Math.atan2(gx - car.x, gz - car.z) - car.yaw; diff = Math.atan2(Math.sin(diff), Math.cos(diff));
  const fq = Math.max(0, Math.min(R.n, AP.q + AP.dir * 9)); let d2 = Math.atan2(R.x[fq] - car.x, R.z[fq] - car.z) - car.yaw; d2 = Math.abs(Math.atan2(Math.sin(d2), Math.cos(d2)));
  const want = (R.paved ? 25 : 17) * (1 - Math.min(0.65, d2 * 1.3));
  return { steer: Math.max(-1, Math.min(1, diff * 2.4)), throttle: Math.max(-1, Math.min(1, (want - car.v) * 0.35)) };
}

// ---------------------------------------------------------------- driving
const g = 9.8;
function cornerGround() { const c = Math.cos(car.yaw), s = Math.sin(car.yaw); return corners.map(k => G.height(car.x + k.mx * c + k.mz * s, car.z - k.mx * s + k.mz * c)); }
function drive(dt) {
  let thr = (keys.KeyW || keys.ArrowUp || touch.gas ? 1 : 0) - (keys.KeyS || keys.ArrowDown || touch.brake ? 1 : 0);
  let st = (keys.KeyA || keys.ArrowLeft || touch.left ? 1 : 0) - (keys.KeyD || keys.ArrowRight || touch.right ? 1 : 0);
  if (AP.on && (st !== 0 || thr < 0)) toggleCruise(false);
  if (AP.on) { const a = cruise(); if (a) { st = a.steer; thr = Math.max(thr, a.throttle); } }
  const surf = G.surface(car.x, car.z), L = WX.light;
  let grip = surf.grip * (1 - 0.3 * Math.min(1, (L.snowDepth || 0) * 2.5)) * (1 - (L.ice || 0) * (surf.kind === 'paved' || surf.kind === 'gravel' ? 0.72 : 0.45)) * (surf.kind === 'paved' && (L.rain || 0) > 0.2 ? 0.86 : 1);
  let drag = surf.drag + (L.snowDepth || 0) * 0.12 + (surf.kind !== 'paved' && surf.kind !== 'gravel' ? (L.ponding || 0) * 0.03 : 0);
  const gr = cornerGround(), front = (gr[0] + gr[1]) / 2, rear = (gr[2] + gr[3]) / 2, left = (gr[0] + gr[2]) / 2, right = (gr[1] + gr[3]) / 2;
  const target = (gr[0] + gr[1] + gr[2] + gr[3]) / 4 + V.wheelR + 0.06 + V.rest * 0.55 + 0.18;
  car.vy -= g * dt; car.y += car.vy * dt;
  if (car.y <= target) {
    const gv = (target - car.lastT) / dt;
    if (car.air && car.vy < -6) { car.v *= 0.92; }
    car.y = target; car.vy = Math.min(14, Math.max(car.vy, gv)); car.air = false;
  } else car.air = car.y - target > 0.25;
  car.lastT = target;
  const pT = Math.atan2(front - rear, V.wb), rT = Math.atan2(left - right, V.track);
  const k = car.air ? 0.02 : Math.min(1, dt * 12); car.pitch += (pT - car.pitch) * k; car.roll += (rT - car.roll) * k;
  car.steer += (st * 0.55 / (1 + Math.abs(car.v) * 0.055) - car.steer) * Math.min(1, dt * 6);
  if (!car.air) {
    let a = 0;
    if (thr > 0) a = (car.v < 0 ? 14 : 7.8) * thr * grip;
    else if (thr < 0) a = car.v > 0.5 ? -13 * grip : -4.2;
    a -= g * Math.sin(car.pitch) * 0.9;
    a -= car.v * drag * 2.2 + 0.0042 * car.v * Math.abs(car.v);
    if (thr === 0) a -= Math.sign(car.v) * Math.min(Math.abs(car.v) / dt, 0.35);
    car.v += a * dt;
    if (surf.water > 1.2) car.v = Math.max(-2.5, Math.min(2.5, car.v));
    car.yaw += car.v * Math.tan(car.steer) / V.wb * (0.55 + 0.45 * grip) * dt;
  }
  car.x += Math.sin(car.yaw) * car.v * dt; car.z += Math.cos(car.yaw) * car.v * dt;
  car.spin += car.v / V.wheelR * dt;
  // suspension: each hub reaches for its ground
  for (let i = 0; i < 4; i++) {
    const c = corners[i], want = gr[i] + V.wheelR - car.y;
    c.len = Math.max(0.12, Math.min(V.rest, -0.06 - want)); if (car.air) c.len = V.rest;
    c.hub.position.y = -0.06 - c.len; c.spin.rotation.x = car.spin; c.hub.rotation.y = i < 2 ? car.steer : 0;
  }
  return surf;
}

// ---------------------------------------------------------------- streaming
const queue = []; let gen = null, genKey = null;
function want() {
  const ci = Math.floor(car.x / CH), cj = Math.floor(car.z / CH), need = [];
  for (let dj = -RT; dj <= RT; dj++) for (let di = -RT; di <= RT; di++) {
    if (di * di + dj * dj > (RT + 0.5) * (RT + 0.5)) continue;
    const key = (ci + di) + ',' + (cj + dj), ring = Math.max(Math.abs(di), Math.abs(dj));
    const c = chunks.get(key);
    if (!c) need.push({ key, ci: ci + di, cj: cj + dj, d: di * di + dj * dj, kind: 'ground' });
    else if (ring <= RF && !c.flora) need.push({ key, ci: ci + di, cj: cj + dj, d: di * di + dj * dj + 0.5, kind: 'flora' });
  }
  need.sort((a, b) => a.d - b.d); queue.length = 0; queue.push(...need);
  for (const [key, c] of chunks) {
    const [i, j] = key.split(',').map(Number), di = i - ci, dj = j - cj, ring = Math.max(Math.abs(di), Math.abs(dj));
    if (di * di + dj * dj > (RT + 1.6) * (RT + 1.6)) { world.remove(c.grp); c.grp.traverse(o => { if (o.geometry && o.geometry !== waterGeo) o.geometry.dispose(); }); if (c.flora) unplant(c.flora); chunks.delete(key); }
    else if (ring > RF + 1 && c.flora) { unplant(c.flora); c.flora = null; }
  }
  // roads and towns by cell
  const Ci = Math.floor(car.x / G.CELL), Cj = Math.floor(car.z / G.CELL), live = new Set(), liveT = new Set();
  for (let di = -2; di <= 2; di++) for (let dj = -2; dj <= 2; dj++) {
    for (const R of G.cellRoads(Ci + di, Cj + dj)) {
      const b = R.box, near = car.x > b[0] - 700 && car.x < b[1] + 700 && car.z > b[2] - 700 && car.z < b[3] + 700;
      if (!near) continue; live.add(R.id);
      if (!roads.has(R.id)) { const m = buildRoad(R); world.add(m); roads.set(R.id, m); }
    }
    if (Math.abs(di) <= 1 && Math.abs(dj) <= 1) { const T = G.town(Ci + di, Cj + dj); if (T) { const k = (Ci + di) + ',' + (Cj + dj); liveT.add(k); if (!towns.has(k)) { const m = buildTown(T); world.add(m); towns.set(k, m); } } }
  }
  for (const [id, m] of roads) if (!live.has(id)) { world.remove(m); m.traverse(o => o.geometry && o.geometry.dispose()); roads.delete(id); }
  for (const [k, m] of towns) if (!liveT.has(k)) { world.remove(m); m.traverse(o => o.geometry && o.geometry.dispose()); towns.delete(k); }
}
function stream(budgetMs) {
  const t0 = performance.now();
  while (performance.now() - t0 < budgetMs) {
    if (!gen) {
      const job = queue.shift(); if (!job) return;
      if (job.kind === 'ground') { if (chunks.has(job.key)) continue; gen = buildChunk(job.ci, job.cj); genKey = job; }
      else {
        const c = chunks.get(job.key); if (!c || c.flora) continue;
        const items = G.scatter(job.ci * CH, job.cj * CH, CH, 1), list = [];
        for (const it of items) { const r = plant(it, it.biome); if (r) list.push(r); }
        c.flora = list; continue;
      }
    }
    const r = gen.next();
    if (r.done) { const grp = r.value; world.add(grp); chunks.set(genKey.key, { grp, flora: null }); gen = null; }
  }
}

// ---------------------------------------------------------------- weather, HUD
const STATES = ['sunny', 'overcast', 'rain', 'storm', 'snow', 'snow_fog', 'freezing_rain', 'fog', 'autumn'];
const LABEL = { snow_fog: 'snow and fog', freezing_rain: 'freezing rain' };

STATES.forEach(s => { const b = document.createElement('button'); b.textContent = LABEL[s] || s; b.dataset.s = s; b.setAttribute('aria-pressed', String(s === 'sunny')); b.onclick = () => { WX.set(s, 3.0); [...$('states').children].forEach(c => c.setAttribute('aria-pressed', String(c === b))); }; $('states').appendChild(b); });
$('wxbtn').onclick = () => { const p = $('wxpanel'); p.hidden = !p.hidden; $('wxbtn').setAttribute('aria-expanded', String(!p.hidden)); };
$('seed').value = seedText;
$('seedform').onsubmit = (e) => { e.preventDefault(); newWorld($('seed').value.trim() || 'lake effect'); };
$('dice').onclick = () => { const W1 = ['north', 'cedar', 'rust', 'quiet', 'long', 'amber', 'cold', 'salt', 'high', 'blue']; const W2 = ['line', 'water', 'acre', 'mile', 'pass', 'country', 'shore', 'grade', 'basin', 'run']; const s = W1[Math.floor(Math.random() * 10)] + ' ' + W2[Math.floor(Math.random() * 10)]; $('seed').value = s; newWorld(s); };
let flashT = 0; function flash(t) { $('note').textContent = t; $('note').hidden = false; flashT = 3.5; }
function newWorld(s) {
  seedText = s; try { localStorage.setItem('endless-seed', s); } catch (e) {}
  for (const [, c] of chunks) { world.remove(c.grp); if (c.flora) unplant(c.flora); } chunks.clear();
  for (const [, m] of roads) world.remove(m); roads.clear(); for (const [, m] of towns) world.remove(m); towns.clear();
  gen = null; queue.length = 0; G = window.CoiloverWorld.create(s); toggleCruise(false); spawn(); warm();
}
function warm() { want(); for (let i = 0; i < 400 && (queue.length || gen); i++) stream(50); }

function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.fov = innerWidth < innerHeight ? 68 : 55; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();
spawn(); say('Building the first stretch of road'); await new Promise(r => setTimeout(r, 30)); warm(); say('');

const sky = new THREE.Color(), base = new THREE.Color(0xbfd2e6), camPos = new THREE.Vector3(), look = new THREE.Vector3();
const N = 5000, pp = new Float32Array(N * 3); for (let i = 0; i < N; i++) { pp[i * 3] = (Math.random() - .5) * 60; pp[i * 3 + 1] = Math.random() * 30; pp[i * 3 + 2] = (Math.random() - .5) * 60; }
const pgeo = new THREE.BufferGeometry(); pgeo.setAttribute('position', new THREE.BufferAttribute(pp, 3));
const pmat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.09, transparent: true, opacity: 0, depthWrite: false }); const precip = new THREE.Points(pgeo, pmat); precip.frustumCulled = false; scene.add(precip);
let last = performance.now(), frame = 0, lastBiome = 'shield', hudT = 0;
camPos.set(car.x - ox - Math.sin(car.yaw) * 9.5, car.y + 3.6, car.z - oz - Math.cos(car.yaw) * 9.5);
window.endless = { car, get G() { return G; }, spawnAt(x, z, yaw) { car.x = x; car.z = z; car.yaw = yaw || 0; car.v = 0; car.y = G.height(x, z) + 1.2; car.lastT = car.y; ox = Math.round(x / 256) * 256; oz = Math.round(z / 256) * 256; world.position.set(-ox, 0, -oz); camPos.set(x - ox - Math.sin(car.yaw) * 9.5, car.y + 3.6, z - oz - Math.cos(car.yaw) * 9.5); warm(); } };
renderer.setAnimationLoop((now) => {
  const dt = Math.min(0.05, (now - last) / 1000); last = now; frame++;
  const surf = drive(dt / 2) && drive(dt / 2);
  if (Math.abs(car.x - ox) > 600 || Math.abs(car.z - oz) > 600) { ox = Math.round(car.x / 256) * 256; oz = Math.round(car.z / 256) * 256; world.position.set(-ox, 0, -oz); }
  if (frame % 20 === 0) want();
  stream(6);
  WX.update(dt);
  const b = G.biome(car.x, car.z).name, wb = b === 'desert' ? 'desert' : 'shield';
  if (wb !== lastBiome) { lastBiome = wb; WX.setBiome(wb); }
  truck.position.set(car.x - ox, car.y, car.z - oz); truck.rotation.set(-car.pitch, car.yaw, car.roll);
  // chase camera
  const cy = car.yaw + camYaw; if (!drag) camYaw *= Math.pow(0.4, dt);
  const want3 = new THREE.Vector3(car.x - ox - Math.sin(cy) * 9.5, car.y + 3.6, car.z - oz - Math.cos(cy) * 9.5);
  const gh = G.height(want3.x + ox, want3.z + oz) + 1.2; if (want3.y < gh) want3.y = gh;
  camPos.lerp(want3, 1 - Math.pow(0.02, dt)); camera.position.copy(camPos);
  look.set(car.x - ox + Math.sin(car.yaw) * 4, car.y + 1.0, car.z - oz + Math.cos(car.yaw) * 4); camera.lookAt(look);
  // light and sky
  const L = WX.light;
  sun.position.set(truck.position.x + 60, truck.position.y + 110, truck.position.z + 45); sun.target.position.copy(truck.position);
  sun.intensity = 2.7 * L.sun + 0.15; hemi.intensity = 0.8 * L.ambient;
  sky.copy(L.sky).multiply(base); scene.background = sky; scene.fog.color.copy(sky); scene.fog.density = (COARSE ? 0.0031 : 0.0024) * Math.sqrt(L.fog);
  const rain = L.rain || 0, snow = L.snowfall || 0, p = pgeo.attributes.position;
  pmat.opacity = Math.max(rain * 0.55, snow * 0.9); pmat.size = snow > rain ? 0.16 : 0.07; pmat.color.set(snow > rain ? 0xffffff : 0xb9c6d0);
  precip.position.set(camera.position.x, camera.position.y - 12, camera.position.z);
  const fall = snow > rain ? 2.2 : 18; for (let i = 0; i < N; i++) { let y = p.array[i * 3 + 1] - fall * dt; if (y < 0) y += 30; p.array[i * 3 + 1] = y; } p.needsUpdate = true;
  // HUD: where you are, not how long
  if ((hudT -= dt) < 0) {
    hudT = 0.4; const T = G.townNear(car.x, car.z);
    $('where').textContent = (T ? T.name + ', ' : '') + G.NAMES[b];
    $('on').textContent = (WX.light.ice || 0) > 0.4 && (surf.kind === 'paved' || surf.kind === 'gravel') ? 'Black ice on the ' + (surf.kind === 'paved' ? 'highway' : 'road') : AP.on ? 'Cruising the ' + (surf.kind === 'paved' ? 'highway' : 'road') : surf.kind === 'paved' ? 'On the highway' : surf.kind === 'gravel' ? 'On a gravel road' : surf.kind === 'water' ? 'In the water' : surf.kind === 'sand' ? 'In deep sand' : 'Off road';
  }
  if (flashT > 0 && (flashT -= dt) <= 0) $('note').hidden = true;
  renderer.render(scene, camera);
});
