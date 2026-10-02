/* weather.js v2: apply Coilover / Squall Cove weather states to procedural models.
   Works with three.js r128 (Coilover) and r160 (Squall Cove). No modules, no build step.

   Usage
     CoiloverWeather.init(THREE, profilesJson, { biome: 'shield' })   // weather_profiles.json; biome picks the overrides
     CoiloverWeather.register(object3d)       // every loaded model root (call once per model)
     CoiloverWeather.set('rain', 2.0)         // target state, seconds to blend the look
     CoiloverWeather.set('snow', 2.0, { settled: true })   // skip accumulation: snow already lying, ponds already full
     CoiloverWeather.setBiome('desert')       // when the map changes
     CoiloverWeather.update(dt)               // every frame
     CoiloverWeather.light                    // blended hints: sun, ambient, fog, sky, wind, rain, snowfall,
                                              //   snowDepth (metres lying now), ponding (0..1 how full the ponds are)

   What it does to a material with userData.role (GLTFLoader puts glTF material extras in material.userData):
     colour     mul, tint/tintAmt, autumn palette
     wet        darker albedo, glossier (rough < 1)
     pond       standing water on flat ground: low-frequency patches that grow with the amount, mirror dark and glossy
     moss       green growth on up and north facing surfaces of rock, bark, wood and concrete
     dew        cool sheen and fine glints on up facing foliage, grass and metal
     snow       coverage on up facing surfaces
     ice        freezing rain: a clear glaze that darkens and glints, black ice on asphalt; light.ice reports how thick
   Freezing states (freezing_rain) keep lying snow from melting, so snow on the ground with rain falling gives a crust and
   black ice. snow_fog is snow falling in fog with hoar frost on the needles.
   Depth: meshes with role 'snow' (snow caps on every model, the snow blanket on each map) sit lower while snow is still
   accumulating and rise to full depth; meshes with role 'puddle' (desert ponds) fill the same way while it rains.
   Layer nodes: *_snow shown while snow is lying, *_puddles while ponds hold water, *_leaves hidden when leafless.
   Existing onBeforeCompile patches (Coilover's styleMat) are kept: this one chains after them. */
(function (root) {
  var T = null, P = null, biome = 'shield', cur = 'sunny', target = 'sunny', blend = 1, dur = 1, mats = [], layers = [];
  var acc = { snow: 0, pond: 0, ice: 0 };
  var U = { uSnowCol: { value: null }, uMossCol: { value: null }, uPondCol: { value: null } };
  var light = {};
  function hex(h) { return new T.Color(h); }
  function st(state) { return P.states[state]; }
  function rolesFor(state) {
    var s = st(state), base = s.roles || {}, ov = ((s.biomes || {})[biome] || {}).roles || {}, out = {}, k, j;
    for (k in base) { out[k] = {}; for (j in base[k]) out[k][j] = base[k][j]; }
    for (k in ov) { out[k] = out[k] || {}; for (j in ov[k]) out[k][j] = ov[k][j]; }
    return out;
  }
  function lightFor(state) {
    var s = st(state), out = {}, k, ov = ((s.biomes || {})[biome] || {}).light || {};
    for (k in s.light) out[k] = s.light[k];
    for (k in ov) out[k] = ov[k];
    return out;
  }
  function flag(state, f) { var s = st(state), ov = (s.biomes || {})[biome] || {}; return ov[f] !== undefined ? ov[f] : s[f]; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  var NOISE = 'float wxHash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }\n' +
    'float wxNoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);\n' +
    '  return mix(mix(wxHash(i), wxHash(i + vec2(1.0, 0.0)), f.x), mix(wxHash(i + vec2(0.0, 1.0)), wxHash(i + vec2(1.0, 1.0)), f.x), f.y); }\n';
  function patch(m) {
    var prev = m.onBeforeCompile, ud = m.userData;
    ['wxSnow', 'wxWet', 'wxPond', 'wxMoss', 'wxDew', 'wxSink', 'wxIce'].forEach(function (k) { ud[k] = { value: 0 }; });
    m.onBeforeCompile = function (sh, r) {
      if (prev) prev.call(this, sh, r);
      sh.uniforms.uWxSnow = ud.wxSnow; sh.uniforms.uWxWet = ud.wxWet; sh.uniforms.uWxPond = ud.wxPond;
      sh.uniforms.uWxMoss = ud.wxMoss; sh.uniforms.uWxDew = ud.wxDew; sh.uniforms.uWxSink = ud.wxSink; sh.uniforms.uWxIce = ud.wxIce;
      sh.uniforms.uSnowCol = U.uSnowCol; sh.uniforms.uMossCol = U.uMossCol; sh.uniforms.uPondCol = U.uPondCol;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uWxSink; varying vec3 vWxN; varying vec3 vWxP;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed.y -= uWxSink;\nvWxN = normalize(mat3(modelMatrix) * objectNormal);\n#ifdef USE_INSTANCING\nvWxN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * objectNormal);\nvWxP = (modelMatrix * instanceMatrix * vec4(transformed, 1.0)).xyz;\n#else\nvWxP = (modelMatrix * vec4(transformed, 1.0)).xyz;\n#endif');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uWxSnow; uniform float uWxWet; uniform float uWxPond; uniform float uWxMoss; uniform float uWxDew; uniform float uWxIce;\n' +
          'uniform vec3 uSnowCol; uniform vec3 uMossCol; uniform vec3 uPondCol; varying vec3 vWxN; varying vec3 vWxP;\n' + NOISE)
        .replace('#include <color_fragment>', '#include <color_fragment>\n' +
          'float wxUp = vWxN.y;\n' +
          'float wxN1 = wxNoise(vWxP.xz * 0.16) * 0.65 + wxNoise(vWxP.xz * 0.6) * 0.35;\n' +
          'float wxN2 = wxNoise(vWxP.xz * 0.11 + 17.3) * 0.7 + wxNoise(vWxP.xz * 0.45 + 3.1) * 0.3;\n' +
          // moss: up and north (game -z) facing, patchy
          'float wxMossM = smoothstep(0.36, 0.54, wxN1 + 0.24 * wxUp - 0.18 * vWxN.z) * uWxMoss;\n' +
          'diffuseColor.rgb = mix(diffuseColor.rgb, uMossCol * (0.75 + 0.5 * wxHash(floor(vWxP.xz * 5.0 + vWxP.y * 3.0))), clamp(wxMossM, 0.0, 1.0));\n' +
          'diffuseColor.rgb *= 1.0 - 0.38 * uWxWet;\n' +
          // glaze: a clear coat of ice that darkens and catches fine glints
          'diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * 0.82 + vec3(0.02, 0.03, 0.04), uWxIce);\n' +
          'diffuseColor.rgb += vec3(0.35) * uWxIce * step(0.992, wxHash(floor(vWxP.xz * 30.0) + floor(vWxP.y * 30.0)));\n' +
          // ponds: flat ground only, patches that spread as the amount rises
          'float wxPondM = smoothstep(0.93, 0.985, wxUp) * smoothstep(1.0 - 0.42 * uWxPond, 1.05 - 0.42 * uWxPond, wxN2) * step(0.001, uWxPond);\n' +
          'diffuseColor.rgb = mix(diffuseColor.rgb, uPondCol, wxPondM * 0.88);\n' +
          // dew: cool sheen plus fine glints on up facing surfaces
          'float wxDewM = uWxDew * (0.45 + 0.55 * max(wxUp, 0.0));\n' +
          'diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * 1.06 + vec3(0.05, 0.06, 0.075), wxDewM * 0.55);\n' +
          'diffuseColor.rgb += vec3(0.55) * wxDewM * step(0.986, wxHash(floor(vWxP.xz * 22.0) + floor(vWxP.y * 22.0)));\n' +
          '{ float n = wxHash(floor(vWxP.xz * 1.7)) * 0.25;\n' +
          '  float s = smoothstep(0.35, 0.75, wxUp + n - 0.12) * uWxSnow;\n' +
          '  diffuseColor.rgb = mix(diffuseColor.rgb, uSnowCol, clamp(s, 0.0, 1.0)); }');
      if (sh.fragmentShader.indexOf('#include <roughnessmap_fragment>') >= 0)
        sh.fragmentShader = sh.fragmentShader.replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n' +
          'roughnessFactor *= 1.0 - 0.65 * uWxWet;\nroughnessFactor *= 1.0 - 0.4 * wxDewM;\nroughnessFactor = mix(roughnessFactor, 0.04, wxPondM);\nroughnessFactor = mix(roughnessFactor, 0.03, uWxIce);');
    };
    m.needsUpdate = true;
    ud.wxBase = m.color ? m.color.clone() : null;
    ud.wxAutumn = Math.random();
    mats.push(m);
  }
  function stateValues(state, m) {
    var md = rolesFor(state)[m.userData.role] || {}, c = m.userData.wxBase ? m.userData.wxBase.clone() : null;
    if (c) {
      if (md.tint) c.lerp(hex(md.tint), md.tintAmt || 0);
      if (md.autumn) c.lerp(hex(md.autumn[Math.floor(m.userData.wxAutumn * md.autumn.length)]), 0.85);
      if (md.mul) c.multiplyScalar(md.mul);
    }
    return { color: c, snow: md.snow || 0, wet: md.rough !== undefined && md.rough < 1 ? (1 - md.rough) : 0,
             pond: md.pond || 0, moss: md.moss || 0, dew: md.dew || 0, ice: md.ice || 0 };
  }
  var api = {
    init: function (THREE, profiles, opts) {
      T = THREE; P = profiles; biome = (opts && opts.biome) || biome;
      U.uSnowCol.value = new T.Color(P.snowColor); U.uMossCol.value = new T.Color(P.mossColor || '#4d6a2c');
      U.uPondCol.value = new T.Color(P.pondColor || '#3d4a55');
      return api;
    },
    register: function (obj) {
      obj.traverse(function (o) {
        if (/_snow$/.test(o.name) || /_leaves$/.test(o.name) || /_puddles$/.test(o.name)) layers.push(o);
        if (!o.isMesh) return;
        (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) {
          if (m && m.userData && m.userData.role && !m.userData.wxSnow) patch(m);
        });
      });
      api.apply(blend); return obj;
    },
    set: function (state, seconds, opts) {
      if (!P.states[state]) return;
      cur = target; target = state; dur = Math.max(0.001, seconds || 0); blend = 0;
      if (opts && opts.settled) { var L = lightFor(state); acc.snow = L.snowfall ? 1 : (flag(state, 'freezing') ? Math.max(acc.snow, opts.snow || 0) : 0); acc.pond = flag(state, 'puddles') ? 1 : 0; acc.ice = flag(state, 'freezing') && L.rain ? 1 : 0; }
    },
    setBiome: function (b) { biome = b; api.apply(blend); },
    update: function (dt) {
      var A = P.accumulate || {}, L = lightFor(target);
      // snow builds while it falls and melts after; ponds fill while it rains and drain after
      var frz = !!flag(target, 'freezing');
      // snow builds while it falls; below freezing it stays put, otherwise it melts
      acc.snow = L.snowfall ? Math.min(1, acc.snow + dt * L.snowfall / (A.snowBuild || 25)) : frz ? acc.snow : Math.max(0, acc.snow - dt / (A.snowMelt || 40));
      // freezing rain glazes everything over; a thaw takes it off again
      acc.ice = frz && L.rain ? Math.min(1, acc.ice + dt * L.rain / (A.iceBuild || 20)) : frz ? acc.ice : Math.max(0, acc.ice - dt / (A.iceMelt || 50));
      acc.pond = flag(target, 'puddles') ? Math.min(1, acc.pond + dt * (L.rain || 0.5) / (A.pondFill || 18)) : Math.max(0, acc.pond - dt / (A.pondDrain || 45));
      if (blend < 1) blend = Math.min(1, blend + dt / dur);
      api.apply(blend);
    },
    apply: function (t) {
      var A = lightFor(cur), B = lightFor(target);
      ['sun', 'ambient', 'fog', 'wind', 'rain', 'snowfall'].forEach(function (k) { light[k] = lerp(A[k] || 0, B[k] || 0, t); });
      light.sky = hex(A.sky).lerp(hex(B.sky), t);
      var depth = Math.max(A.snowDepth || 0, B.snowDepth || 0);
      if (!depth && acc.snow > 0) depth = lightFor('snow').snowDepth || 0.4;
      light.snowDepth = acc.snow * depth; light.ponding = acc.pond; light.ice = acc.ice;
      U.uPondCol.value.copy(hex(P.pondColor || '#3d4a55')).lerp(light.sky, 0.35);
      var cover = Math.min(1, acc.snow * 2.5);
      mats.forEach(function (m) {
        var a = stateValues(cur, m), b = stateValues(target, m), ud = m.userData;
        if (m.color && a.color) m.color.copy(a.color).lerp(b.color, t);
        var lying = (rolesFor('snow')[ud.role] || {}).snow || 0;      // lying snow keeps the snow look whatever is falling now
        ud.wxSnow.value = Math.max(b.snow || a.snow, lying) * cover;
        ud.wxIce.value = Math.max(a.ice, b.ice) * acc.ice;
        ud.wxWet.value = lerp(a.wet, b.wet, t);
        ud.wxPond.value = Math.max(a.pond, b.pond) * acc.pond;
        ud.wxMoss.value = lerp(a.moss, b.moss, t);
        ud.wxDew.value = lerp(a.dew, b.dew, t);
        var role = ud.role;
        ud.wxSink.value = role === 'snow' ? (1 - acc.snow) * (depth || 0.4) * 1.2 : role === 'puddle' ? (1 - acc.pond) * 0.25 : 0;
      });
      var s = st(target), s0 = st(cur);
      layers.forEach(function (o) {
        if (/_snow$/.test(o.name)) o.visible = acc.snow > 0.01;
        if (/_leaves$/.test(o.name)) o.visible = !(s.leafless ? t > 0.5 : (s0.leafless && t < 0.5));
        if (/_puddles$/.test(o.name)) o.visible = acc.pond > 0.01;
      });
    },
    get light() { return light; },
    get state() { return target; },
    get biome() { return biome; },
    get accumulation() { return { snow: acc.snow, pond: acc.pond, ice: acc.ice }; }
  };
  root.CoiloverWeather = api;
})(typeof window !== 'undefined' ? window : this);
