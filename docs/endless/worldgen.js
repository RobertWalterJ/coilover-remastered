/* worldgen.js: an endless, seeded Coilover world. Pure functions, no three.js, no modules (works beside r128 or r160).

   var W = CoiloverWorld.create('lake effect');   // any string or number; the same seed always makes the same world
   W.height(x, z)        ground height in metres (roads, causeways and town pads included), the one function physics reads
   W.surface(x, z)       { kind, grip, drag, water, sand, biome }   kind: 'paved', 'gravel', 'shield', 'desert', 'prairie', 'sand', 'water'
   W.biome(x, z)         { shield, desert, prairie } weights summing to 1, and .name (the dominant one)
   W.roadsAround(x, z)   every road whose bounds come within reach of the point (see Road below)
   W.cellRoads(i, j)     the roads that start in cell (i, j): always one east, usually one south
   W.nodeRoads(i, j)     every road meeting at the junction of cell (i, j)
   W.town(i, j)          null or { x, z, houses: [{ x, z, yaw, w, d, h, kind }] }
   W.scatter(cx, cz, size, density)   flora and rock placements for a square: [{ kind, x, y, z, yaw, s }]

   The world is a grid of cells CELL metres across. Each cell holds one junction at a jittered spot. Every junction joins
   its east neighbour, and most join the one to the south, so the network is contiguous in every direction forever.
   Each road is a gentle curve between two junctions with its own smoothed grade; the ground is cut and filled to meet
   it, and over water it rides a causeway. Biomes drift across the land on a scale of kilometres: Pike country (rock,
   spruce and lakes), Ochre country (mesas, washes and deep sand) and Tallgrass (rolling prairie with shelterbelts).
   Doubles are fine to any distance; renderers should keep a floating origin. */
(function (root) {
  var CELL = 720, SAMPLE = 8, WATER = 0;

  function makeHash(seed) {
    var s = 0x9e3779b9 ^ seed;
    return function (x, y, k) {
      var h = (Math.imul((x | 0) ^ s, 0x27d4eb2d) ^ Math.imul((y | 0) + 0x165667b1, 0x85ebca6b) ^ Math.imul((k | 0) + 0x2c1b3c6d, 0xc2b2ae35)) | 0;
      h = Math.imul(h ^ (h >>> 15), 0x2c1b3c6d); h = Math.imul(h ^ (h >>> 12), 0x297a2d39); h ^= h >>> 15;
      return (h >>> 0) / 4294967296;
    };
  }
  function seedOf(v) {
    if (typeof v === 'number') return v | 0;
    var h = 2166136261; v = String(v);
    for (var i = 0; i < v.length; i++) { h ^= v.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h | 0;
  }
  function sstep(a, b, t) { t = (t - a) / (b - a); t = t < 0 ? 0 : t > 1 ? 1 : t; return t * t * (3 - 2 * t); }
  function lerp(a, b, t) { return a + (b - a) * t; }

  function create(seedIn) {
    var seed = seedOf(seedIn), H = makeHash(seed);
    function vnoise(x, y, k) {
      var xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
      var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
      return lerp(lerp(H(xi, yi, k), H(xi + 1, yi, k), u), lerp(H(xi, yi + 1, k), H(xi + 1, yi + 1, k), u), v);
    }
    function fbm(x, y, oct, k) {
      var s = 0, a = 0.5, f = 1, n = 0;
      for (var i = 0; i < oct; i++) { s += a * vnoise(x * f, y * f, k + i * 7); n += a; a *= 0.5; f *= 2.03; }
      return s / n;
    }

    // ---------------------------------------------------------------- biomes
    function biome(x, z) {
      var t = fbm(x * 0.00028 + 11.3, z * 0.00028 - 4.1, 3, 101);      // dry to wet, a few kilometres per swing
      var d = sstep(0.545, 0.655, t), s = 1 - sstep(0.385, 0.495, t), p = Math.max(0, 1 - d - s);
      var name = d > 0.5 ? 'desert' : s > 0.5 ? 'shield' : 'prairie';
      return { shield: s, desert: d, prairie: p, name: name };
    }
    var NAMES = { shield: 'Pike country', desert: 'Ochre country', prairie: 'Tallgrass' };

    // ---------------------------------------------------------------- natural ground (no roads)
    function hShield(x, z) {
      var broad = fbm(x * 0.0042, z * 0.0042, 3, 201) * 36 - 16.2;
      var hum = fbm(x * 0.016, z * 0.016, 3, 211) * 7 - 3.5;
      var knob = Math.pow(sstep(0.62, 0.8, fbm(x * 0.009, z * 0.009, 2, 221)), 2) * 12;   // granite domes
      return broad + hum + knob;
    }
    function hDesert(x, z) {
      var base = 7 + fbm(x * 0.003, z * 0.003, 3, 301) * 16;
      var m = fbm(x * 0.0055, z * 0.0055, 3, 311);
      var mesa = sstep(0.58, 0.63, m) * 24 + sstep(0.69, 0.72, m) * 12;              // tables with stepped cliffs
      var wash = (1 - sstep(0.0, 0.05, Math.abs(fbm(x * 0.004, z * 0.004, 2, 321) - 0.5))) * 3.5;
      return base + mesa - wash + (vnoise(x * 0.06, z * 0.06, 331) - 0.5) * 0.5;
    }
    function hPrairie(x, z) {
      return 3 + fbm(x * 0.0021, z * 0.0021, 3, 401) * 13 + fbm(x * 0.011, z * 0.011, 2, 411) * 2.4
        - sstep(0.72, 0.8, vnoise(x * 0.011, z * 0.011, 431)) * 6
        - (1 - sstep(0.0, 0.035, Math.abs(fbm(x * 0.0035, z * 0.0035, 2, 421) - 0.5))) * 6;   // coulees with sloughs
    }
    function natural(x, z) {
      var b = biome(x, z), h = 0;
      if (b.shield > 0) h += b.shield * hShield(x, z);
      if (b.desert > 0) h += b.desert * hDesert(x, z);
      if (b.prairie > 0) h += b.prairie * hPrairie(x, z);
      return h;
    }

    // ---------------------------------------------------------------- road network
    function node(i, j) {
      return { i: i, j: j, x: (i + 0.5 + (H(i, j, 1) - 0.5) * 0.5) * CELL, z: (j + 0.5 + (H(i, j, 2) - 0.5) * 0.5) * CELL };
    }
    var roadCache = {}, roadCount = 0;
    function buildRoad(a, b, dir) {
      var dx = b.x - a.x, dz = b.z - a.z, L = Math.sqrt(dx * dx + dz * dz), nx = -dz / L, nz = dx / L;
      var k = dir === 'e' ? 11 : 12, bow1 = (H(a.i, a.j, k) - 0.5) * 0.3 * L, bow2 = (H(a.i, a.j, k + 10) - 0.5) * 0.3 * L;
      var c1 = { x: a.x + dx / 3 + nx * bow1, z: a.z + dz / 3 + nz * bow1 }, c2 = { x: a.x + dx * 2 / 3 + nx * bow2, z: a.z + dz * 2 / 3 + nz * bow2 };
      var n = Math.max(8, Math.round(L * 1.25 / SAMPLE)), xs = [], zs = [], ys = [];
      for (var q = 0; q <= n; q++) {
        var t = q / n, u = 1 - t;
        xs.push(u * u * u * a.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t * t * t * b.x);
        zs.push(u * u * u * a.z + 3 * u * u * t * c1.z + 3 * u * t * t * c2.z + t * t * t * b.z);
      }
      // the grade: the natural ground along the line, smoothed twice, held above the water
      var raw = []; for (q = 0; q <= n; q++) raw.push(natural(xs[q], zs[q]));
      var sm = raw;
      for (var pass = 0; pass < 3; pass++) {
        var out = [], W = 7;
        for (q = 0; q <= n; q++) { var s = 0, c = 0; for (var r = -W; r <= W; r++) { var qq = Math.min(n, Math.max(0, q + r)); s += sm[qq]; c++; } out.push(s / c); }
        sm = out;
      }
      // the junction ends meet exactly at the junction's own height so every road at a node agrees
      var ya = nodeY(a), yb = nodeY(b);
      for (q = 0; q <= n; q++) {
        var t2 = q / n, w = sstep(0, 0.12, t2) * (1 - sstep(0.88, 1, t2));
        ys.push(Math.max(WATER + 1.6, lerp(lerp(ya, yb, t2), sm[q], w)));
      }
      var paved = H(a.i, a.j, dir === 'e' ? 21 : 22) < 0.55;
      var bx0 = 1e18, bx1 = -1e18, bz0 = 1e18, bz1 = -1e18;
      for (q = 0; q <= n; q++) { bx0 = Math.min(bx0, xs[q]); bx1 = Math.max(bx1, xs[q]); bz0 = Math.min(bz0, zs[q]); bz1 = Math.max(bz1, zs[q]); }
      return { id: a.i + ',' + a.j + dir, a: a, b: b, x: xs, z: zs, y: ys, n: n, paved: paved, half: paved ? 3.8 : 3.1,
               box: [bx0, bx1, bz0, bz1], raw: raw };
    }
    function nodeY(nd) {
      if (nd.y === undefined) {
        var s = 0, c = 0;
        for (var a = 0; a < 6; a++) for (var r = 0; r <= 60; r += 30) { s += natural(nd.x + Math.cos(a) * r, nd.z + Math.sin(a) * r); c++; }
        nd.y = Math.max(WATER + 1.6, s / c);
      }
      return nd.y;
    }
    var nodeCache = {};
    function nodeAt(i, j) { var k = i + ',' + j; return nodeCache[k] || (nodeCache[k] = node(i, j)); }
    function hasSouth(i, j) { return H(i, j, 31) < 0.68; }
    function cellRoads(i, j) {
      var k = i + ',' + j;
      if (roadCache[k]) return roadCache[k];
      var a = nodeAt(i, j), list = [buildRoad(a, nodeAt(i + 1, j), 'e')];
      if (hasSouth(i, j)) list.push(buildRoad(a, nodeAt(i, j + 1), 's'));
      roadCount++;
      if (roadCount > 400) { roadCache = {}; roadCount = 0; }               // keep memory bounded on long drives
      return (roadCache[k] = list);
    }
    function nodeRoads(i, j) {
      var out = [], own = cellRoads(i, j);
      out.push({ road: own[0], from: 'a' });
      if (own[1]) out.push({ road: own[1], from: 'a' });
      out.push({ road: cellRoads(i - 1, j)[0], from: 'b' });
      var n = cellRoads(i, j - 1); if (n[1]) out.push({ road: n[1], from: 'b' });
      return out;
    }
    function roadsAround(x, z, reach) {
      reach = reach || 40;
      var ci = Math.floor(x / CELL), cj = Math.floor(z / CELL), out = [];
      for (var di = -1; di <= 1; di++) for (var dj = -1; dj <= 1; dj++) {
        var rs = cellRoads(ci + di, cj + dj);
        for (var q = 0; q < rs.length; q++) {
          var b = rs[q].box;
          if (x > b[0] - reach && x < b[1] + reach && z > b[2] - reach && z < b[3] + reach) out.push(rs[q]);
        }
      }
      return out;
    }
    // nearest point on any road: distance, road height there, the road, segment index and the fraction along it
    function nearestRoad(x, z, reach) {
      var rs = roadsAround(x, z, reach), best = { d: 1e9 };
      for (var k = 0; k < rs.length; k++) {
        var R = rs[k], X = R.x, Z = R.z;
        for (var q = 0; q < R.n; q++) {
          var ax = X[q], az = Z[q], bx = X[q + 1], bz = Z[q + 1];
          if (Math.abs(x - ax) > reach + 12 && Math.abs(x - bx) > reach + 12) continue;
          if (Math.abs(z - az) > reach + 12 && Math.abs(z - bz) > reach + 12) continue;
          var ex = bx - ax, ez = bz - az, t = ((x - ax) * ex + (z - az) * ez) / (ex * ex + ez * ez);
          t = t < 0 ? 0 : t > 1 ? 1 : t;
          var px = ax + ex * t - x, pz = az + ez * t - z, d = Math.sqrt(px * px + pz * pz);
          if (d < best.d) best = { d: d, y: lerp(R.y[q], R.y[q + 1], t), road: R, q: q, t: t };
        }
      }
      return best;
    }

    // ---------------------------------------------------------------- towns
    var townCache = {};
    function town(i, j) {
      var k = i + ',' + j;
      if (k in townCache) return townCache[k];
      if (H(i, j, 41) > 0.3) return (townCache[k] = null);
      var nd = nodeAt(i, j), houses = [], legs = nodeRoads(i, j), want = 6 + Math.floor(H(i, j, 42) * 12);
      for (var h = 0; h < want * 3 && houses.length < want; h++) {
        var leg = legs[h % legs.length], R = leg.road;
        var q = 3 + Math.floor(H(i, j, 50 + h) * 14); if (leg.from === 'b') q = R.n - q;
        q = Math.max(1, Math.min(R.n - 1, q));
        var tx = R.x[q + 1] - R.x[q - 1], tz = R.z[q + 1] - R.z[q - 1], tl = Math.sqrt(tx * tx + tz * tz); tx /= tl; tz /= tl;
        var side = H(i, j, 90 + h) < 0.5 ? -1 : 1, w = 8 + H(i, j, 130 + h) * 8, d = 7 + H(i, j, 170 + h) * 6, off = R.half + 9 + d / 2;
        var hx = R.x[q] - tz * side * off, hz = R.z[q] + tx * side * off;
        var ok = true;
        for (var o = 0; o < houses.length; o++) if (Math.hypot(houses[o].x - hx, houses[o].z - hz) < 16) { ok = false; break; }
        if (!ok) continue;
        var kinds = ['house', 'house', 'house', 'store', 'barn', 'garage', 'chapel'];
        houses.push({ x: hx, z: hz, yaw: Math.atan2(-tz * side, tx * side) + Math.PI / 2, w: w, d: d, h: 3.2 + H(i, j, 210 + h) * 3.5,
                      kind: kinds[Math.floor(H(i, j, 250 + h) * kinds.length)], y: R.y[q], road: R.id });
      }
      return (townCache[k] = { x: nd.x, z: nd.z, y: nodeY(nd), houses: houses, name: townName(i, j) });
    }
    var SYL = ['Ash', 'Bram', 'Cor', 'Dun', 'Elm', 'Fen', 'Gar', 'Hol', 'Ivy', 'Jas', 'Kel', 'Lark', 'Mar', 'Nor', 'Oak', 'Pell', 'Quill', 'Rook', 'Sedge', 'Tarn', 'Vale', 'Wick', 'Yarrow'];
    var END = ['ford', 'by', 'stead', 'ton', 'well', ' Crossing', ' Junction', 'brook', ' Flats', ' Siding', 'mere', 'field'];
    function townName(i, j) { return SYL[Math.floor(H(i, j, 61) * SYL.length)] + END[Math.floor(H(i, j, 62) * END.length)]; }
    function townNear(x, z) {
      var ci = Math.floor(x / CELL), cj = Math.floor(z / CELL), best = null, bd = 1e9;
      for (var di = -1; di <= 1; di++) for (var dj = -1; dj <= 1; dj++) {
        var t = town(ci + di, cj + dj); if (!t) continue;
        var d = Math.hypot(t.x - x, t.z - z); if (d < bd) { bd = d; best = t; }
      }
      return best && bd < 260 ? best : null;
    }

    // ---------------------------------------------------------------- ground with roads, causeways and pads
    function sandAt(x, z, b) {
      if (b.desert < 0.3) return 0;
      return b.desert * sstep(0.6, 0.7, fbm(x * 0.012, z * 0.012, 3, 501)) * (0.25 + 0.6 * fbm(x * 0.05, z * 0.05, 2, 511));
    }
    function sample(x, z) {
      var b = biome(x, z), h0 = natural(x, z), nr = nearestRoad(x, z, 26), h = h0, kind = 'off';
      if (nr.d < 26) {
        var half = nr.road.half, w = 1 - sstep(half + 0.8, half + 20, nr.d);
        h = lerp(h0, nr.y, w);
        if (nr.d < half + 0.6) { h = nr.y; kind = nr.road.paved ? 'paved' : 'gravel'; }
        else if (nr.d < half + 2.2) { h = nr.y - 0.05; kind = 'shoulder'; }
      }
      var sand = kind === 'off' ? sandAt(x, z, b) : 0;
      return { h: h + sand * 0.6, h0: h0, b: b, road: nr, kind: kind, sand: sand };
    }
    function height(x, z) { return sample(x, z).h; }
    function surface(x, z) {
      var s = sample(x, z), water = Math.max(0, WATER - s.h);
      if (s.kind === 'paved') return { kind: 'paved', grip: 1.0, drag: 0.012, water: 0, sand: 0, biome: s.b.name };
      if (s.kind === 'gravel' || s.kind === 'shoulder') return { kind: 'gravel', grip: 0.82, drag: 0.03, water: 0, sand: 0, biome: s.b.name };
      if (water > 0.05) return { kind: 'water', grip: 0.5, drag: 0.25 + water * 0.6, water: water, sand: 0, biome: s.b.name };
      if (s.sand > 0.15) return { kind: 'sand', grip: 0.62, drag: 0.08 + s.sand * 0.3, water: 0, sand: s.sand, biome: s.b.name };
      var g = s.b.name === 'desert' ? 0.86 : s.b.name === 'prairie' ? 0.8 : 0.74;
      return { kind: s.b.name, grip: g, drag: 0.045, water: 0, sand: 0, biome: s.b.name };
    }

    // ---------------------------------------------------------------- ground colour (for vertex colours)
    var PAL = {
      shield: [[0.42, 0.44, 0.36], [0.36, 0.40, 0.29], [0.50, 0.49, 0.46]],       // forest floor, moss, granite
      desert: [[0.78, 0.55, 0.36], [0.66, 0.40, 0.30], [0.86, 0.68, 0.47]],       // hardpan, red slope, sand
      prairie: [[0.62, 0.61, 0.38], [0.52, 0.56, 0.32], [0.70, 0.62, 0.42]]       // dry grass, green grass, stubble
    };
    function colour(x, z, s, slope) {
      var b = s.b, out = [0, 0, 0], n = fbm(x * 0.03, z * 0.03, 2, 601), n2 = vnoise(x * 0.2, z * 0.2, 611);
      ['shield', 'desert', 'prairie'].forEach(function (k) {
        var w = b[k]; if (w <= 0) return;
        var P = PAL[k], c = P[0].slice();
        for (var i = 0; i < 3; i++) c[i] = lerp(c[i], P[1][i], n);
        var rock = sstep(0.12, 0.3, slope); for (i = 0; i < 3; i++) c[i] = lerp(c[i], P[2][i] * (k === 'desert' ? 0.85 : 1), k === 'prairie' ? rock * 0.4 : rock);
        if (k === 'desert' && s.sand > 0.05) for (i = 0; i < 3; i++) c[i] = lerp(c[i], P[2][i], sstep(0.05, 0.25, s.sand));
        for (i = 0; i < 3; i++) out[i] += c[i] * w * (0.92 + 0.16 * n2);
      });
      if (s.h < WATER + 0.6) { var wet = sstep(WATER + 0.6, WATER - 0.4, s.h); for (var i2 = 0; i2 < 3; i2++) out[i2] = lerp(out[i2], out[i2] * 0.55, wet); }
      if (s.kind === 'shoulder') for (var i3 = 0; i3 < 3; i3++) out[i3] = lerp(out[i3], 0.55, 0.5);
      return out;
    }

    // ---------------------------------------------------------------- flora and rocks
    var FLORA = {
      shield: [['spruce', 0.30], ['balsam_fir', 0.12], ['white_pine', 0.08], ['birch', 0.1], ['aspen', 0.07], ['maple', 0.05], ['boulder', 0.07], ['shrub', 0.06], ['blueberry', 0.06], ['fern', 0.05], ['grass', 0.04]],
      desert: [['sage', 0.2], ['creosote', 0.14], ['dry_grass', 0.16], ['saguaro', 0.06], ['juniper', 0.08], ['sandstone', 0.1], ['prickly_pear', 0.06], ['barrel', 0.04], ['ocotillo', 0.05], ['hoodoo', 0.02], ['scree', 0.05], ['deadwood', 0.04]],
      prairie: [['grass', 0.42], ['shrub', 0.14], ['aspen', 0.1], ['birch', 0.04], ['boulder', 0.05], ['juniper_mat', 0.06], ['dry_grass', 0.15], ['alder', 0.04]]
    };
    var LAKE = [['cattails', 0.4], ['reeds', 0.35], ['lily_pads', 0.25]];
    function pick(table, r) { var s = 0; for (var i = 0; i < table.length; i++) { s += table[i][1]; if (r < s) return table[i][0]; } return table[table.length - 1][0]; }
    function scatter(cx, cz, size, density) {
      var out = [], step = 7 / Math.sqrt(density || 1), nx = Math.ceil(size / step);
      for (var a = 0; a < nx; a++) for (var c = 0; c < nx; c++) {
        var gx = Math.floor((cx + a * step) / step), gz = Math.floor((cz + c * step) / step);
        var x = (gx + H(gx, gz, 701)) * step, z = (gz + H(gx, gz, 702)) * step;
        if (x < cx || x >= cx + size || z < cz || z >= cz + size) continue;
        var s = sample(x, z), b = s.b, r = H(gx, gz, 703);
        if (s.kind !== 'off' || (s.road.road && s.road.d < s.road.road.half + 6)) continue;
        var t = townNear(x, z); if (t) { var near = false; for (var k = 0; k < t.houses.length; k++) if (Math.hypot(t.houses[k].x - x, t.houses[k].z - z) < t.houses[k].w * 0.8 + 3) near = true; if (near) continue; }
        var sl = Math.abs(height(x + 2, z) - height(x - 2, z)) + Math.abs(height(x, z + 2) - height(x, z - 2));
        var kind = null, biomeOf = b.name;
        if (s.h < WATER - 0.05) { if (s.h > WATER - 1.4 && b.shield + b.prairie > 0.5 && r < 0.35) kind = pick(LAKE, H(gx, gz, 704)); }
        else if (s.h < WATER + 0.7 && b.desert < 0.5 && r < 0.5) kind = pick([['cattails', 0.4], ['reeds', 0.4], ['shrub', 0.2]], H(gx, gz, 704));
        else {
          var rb = H(gx, gz, 709), bn = rb < b.desert ? 'desert' : rb < b.desert + b.shield ? 'shield' : 'prairie';   // ecotones mix their plants
          var dens = bn === 'shield' ? 0.15 + 0.85 * sstep(0.35, 0.6, fbm(x * 0.006, z * 0.006, 2, 801))
                   : bn === 'prairie' ? 0.06 + 0.5 * sstep(0.62, 0.7, fbm(x * 0.01, z * 0.01, 2, 811)) : 0.22;
          if (sl > 3.2 && bn !== 'desert') dens *= 0.4;
          if (s.sand > 0.2) dens *= 0.25;
          if (r < dens) kind = pick(FLORA[bn], H(gx, gz, 705));
          if (kind) biomeOf = bn;
        }
        if (!kind) continue;
        out.push({ kind: kind, biome: biomeOf, x: x, y: s.h, z: z, yaw: H(gx, gz, 706) * 6.283, s: 0.8 + H(gx, gz, 707) * 0.45, v: Math.floor(H(gx, gz, 708) * 4) });
      }
      return out;
    }

    return {
      seed: seed, CELL: CELL, WATER: WATER, NAMES: NAMES,
      height: height, sample: sample, surface: surface, biome: biome, natural: natural, colour: colour,
      roadsAround: roadsAround, nearestRoad: nearestRoad, cellRoads: cellRoads, nodeRoads: nodeRoads, nodeAt: nodeAt,
      town: town, townNear: townNear, scatter: scatter, hash: H, fbm: fbm
    };
  }
  root.CoiloverWorld = { create: create, seedOf: seedOf };
})(typeof window !== 'undefined' ? window : this);
