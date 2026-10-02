/* weather.js: apply Coilover / Squall Cove weather states to procedural models.
   Works with three.js r128 (Coilover) and r160 (Squall Cove). No modules, no build step.

   Usage
     CoiloverWeather.init(THREE, profilesJson)          // the contents of weather_profiles.json
     CoiloverWeather.register(object3d)                  // every loaded model root (call once per model)
     CoiloverWeather.set('rain', 2.0)                    // target state, seconds to blend
     CoiloverWeather.update(dt)                          // every frame
     CoiloverWeather.light                               // blended light hints: sun, ambient, fog, sky, wind, rain, snowfall
   Materials need userData.role (GLTFLoader puts glTF material extras in material.userData). Existing onBeforeCompile
   patches (Coilover's styleMat) are kept: this one chains after them. */
(function (root) {
  var T = null, P = null, cur = 'sunny', target = 'sunny', blend = 1, dur = 1, mats = [], layers = [];
  var U = { uSnow: { value: 0 }, uWet: { value: 0 }, uSnowCol: { value: null } };
  var light = {};
  function hex(h) { return new T.Color(h); }
  function mod(state, role) { var s = P.states[state]; var r = s.roles || {}; return r[role] || {}; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function patch(m) {
    var prev = m.onBeforeCompile;
    var role = m.userData.role;
    m.userData.wxSnow = { value: 0 }; m.userData.wxWet = { value: 0 };
    m.onBeforeCompile = function (sh, r) {
      if (prev) prev.call(this, sh, r);
      sh.uniforms.uWxSnow = m.userData.wxSnow; sh.uniforms.uWxWet = m.userData.wxWet; sh.uniforms.uSnowCol = U.uSnowCol;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWxN; varying vec3 vWxP;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWxN = normalize(mat3(modelMatrix) * objectNormal);\n#ifdef USE_INSTANCING\nvWxN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * objectNormal);\nvWxP = (modelMatrix * instanceMatrix * vec4(transformed, 1.0)).xyz;\n#else\nvWxP = (modelMatrix * vec4(transformed, 1.0)).xyz;\n#endif');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uWxSnow; uniform float uWxWet; uniform vec3 uSnowCol; varying vec3 vWxN; varying vec3 vWxP;\nfloat wxHash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }')
        .replace('#include <color_fragment>', '#include <color_fragment>\n' +
          '{ float n = wxHash(floor(vWxP.xz * 1.7)) * 0.25;\n' +
          '  float s = smoothstep(0.35, 0.75, vWxN.y + n - 0.12) * uWxSnow;\n' +
          '  diffuseColor.rgb *= 1.0 - 0.38 * uWxWet;\n' +
          '  diffuseColor.rgb = mix(diffuseColor.rgb, uSnowCol, clamp(s, 0.0, 1.0)); }');
      if (sh.fragmentShader.indexOf('#include <roughnessmap_fragment>') >= 0)
        sh.fragmentShader = sh.fragmentShader.replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor *= 1.0 - 0.65 * uWxWet;');
    };
    m.needsUpdate = true;
    m.userData.wxBase = m.color ? m.color.clone() : null;
    m.userData.wxAutumn = Math.random();
    mats.push(m);
  }
  function stateValues(state, m) {
    var md = mod(state, m.userData.role), c = m.userData.wxBase ? m.userData.wxBase.clone() : null;
    if (c) {
      if (md.tint) c.lerp(hex(md.tint), md.tintAmt || 0);
      if (md.autumn) c.lerp(hex(md.autumn[Math.floor(m.userData.wxAutumn * md.autumn.length)]), 0.85);
      if (md.mul) c.multiplyScalar(md.mul);
    }
    return { color: c, snow: md.snow || 0, wet: md.rough !== undefined && md.rough < 1 ? (1 - md.rough) : 0 };
  }
  var api = {
    init: function (THREE, profiles) { T = THREE; P = profiles; U.uSnowCol.value = new T.Color(P.snowColor); return api; },
    register: function (obj) {
      obj.traverse(function (o) {
        if (/_snow$/.test(o.name) || /_leaves$/.test(o.name) || /_puddles$/.test(o.name)) layers.push(o);
        if (!o.isMesh) return;
        (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) {
          if (m && m.userData && m.userData.role && !m.userData.wxSnow) patch(m);
        });
      });
      api.apply(1); return obj;
    },
    set: function (state, seconds) { if (!P.states[state]) return; cur = target; target = state; dur = Math.max(0.001, seconds || 0); blend = 0; },
    update: function (dt) { if (blend < 1) { blend = Math.min(1, blend + dt / dur); api.apply(blend); } },
    apply: function (t) {
      var A = P.states[cur].light, B = P.states[target].light;
      ['sun', 'ambient', 'fog', 'wind', 'rain', 'snowfall'].forEach(function (k) { light[k] = lerp(A[k] || 0, B[k] || 0, t); });
      light.sky = hex(A.sky).lerp(hex(B.sky), t);
      mats.forEach(function (m) {
        var a = stateValues(cur, m), b = stateValues(target, m);
        if (m.color && a.color) m.color.copy(a.color).lerp(b.color, t);
        m.userData.wxSnow.value = lerp(a.snow, b.snow, t);
        m.userData.wxWet.value = lerp(a.wet, b.wet, t);
      });
      var s = P.states[target], s0 = P.states[cur];
      layers.forEach(function (o) {
        if (/_snow$/.test(o.name)) o.visible = (target === 'snow' ? t > 0.4 : (cur === 'snow' && t < 0.6));
        if (/_leaves$/.test(o.name)) o.visible = !(s.leafless ? t > 0.5 : (s0.leafless && t < 0.5));
        if (/_puddles$/.test(o.name)) o.visible = !!(s.puddles ? t > 0.3 : (s0.puddles && t < 0.7));
      });
    },
    get light() { return light; },
    get state() { return target; }
  };
  root.CoiloverWeather = api;
})(typeof window !== 'undefined' ? window : this);
