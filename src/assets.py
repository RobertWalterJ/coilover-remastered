# -*- coding: utf-8 -*-
"""The asset layer: load the Blender models, and make them look like the game.

THE PROBLEM. The game has no model loader and never had one, because the whole
thing was one HTML file with nothing beside it. The remaster has 55 GLBs, and
three things have to be true at once:

  1. The game is SYNCHRONOUS at boot. `SHELLS[V.id](V)` builds a body the
     instant the vehicle changes, and `buildCityProps` runs inside `setMap`.
     Loading is asynchronous. So everything is preloaded behind the title
     screen, which already exists and already waits for a tap, and the game
     only starts once the models are in memory. Nothing downstream has to
     learn about promises.
  2. glTF arrives as `MeshStandardMaterial`. `styleMat()` patches the PHONG
     fragment shader, so a standard material gets none of the posterising, the
     grain, the rim light or the band tinting -- the model would render as a
     flat grey blob next to a stylised world. Every material is rebuilt as
     Phong and run through `styleMat` on load.
  3. Materials must be SHARED, not cloned per mesh. The glow system matches by
     material identity (`LGLOW` holds the material object), and the shader
     uniform patching is per material. One instance per name, reused across
     every model that mentions it.

HOW A MODEL IS NAMED. `assets/manifest.json` carries, for every file, its node
names, its triangle count, and every material with its hex colour and (for the
lit parts, named `glow_*`) its emissive colour. The material names are the
game's own variable names -- paint, second, trim, flare, carbon, disc, caliper,
tyre, rim, chrome, spring, glass, canvas -- which is what makes this a swap
rather than a translation.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ------------------------------------------------------------------ the loader
sub('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>',
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>')

# The asset layer goes in just before the truck is built, so MDL exists by the
# time any shell function or prop builder wants it.
sub("/* ================= the truck ================= */",
r"""/* ================= assets =================
   Blender models, loaded once at boot and converted into the game's own
   materials. `MDL.get(key)` returns a fresh clone of a loaded model; the
   materials inside it are shared instances, which is what the glow system and
   the shader patching both require. */
var MDL=(function(){
  var ROOT='assets/', manifest=null, cache={}, mats={}, ready=false;

  /* One material per NAME, not per mesh. LGLOW and GLOW match by identity, and
     styleMat patches uniforms per material, so cloning would break both. */
  function matFor(name, spec, opts){
    if(mats[name]) return mats[name];
    var o={ color:sc(spec.color||'#888888'), specular:0x000000, shininess:0,
            flatShading:true };
    /* the lofted car panels are the one thing authored smooth, and the
       generator keeps that, so honour it here too */
    if(name==='paint') o.flatShading=false;
    if(spec.opacity!==undefined && spec.opacity<1){
      o.transparent=true; o.opacity=spec.opacity;
    }
    var m=new THREE.MeshPhongMaterial(o);
    /* A lit part glows rather than being painted bright: register it so the
       time of day drives it, exactly as the hand built props do. */
    if(name.indexOf('glow_')===0){
      m.emissive=new THREE.Color(0x000000);
      LGLOW.push({m:m, c:new THREE.Color(spec.emissive||spec.color), s:0.95, asset:true});
    }
    mats[name]=styleMat(m, opts||{});
    return mats[name];
  }

  /* glTF hands us MeshStandardMaterial, which styleMat cannot touch because it
     patches the Phong shader. Rebuild every one by name. */
  function convert(root, opts){
    root.traverse(function(o){
      if(!o.isMesh) return;
      o.castShadow=true; o.receiveShadow=true;
      var src=o.material, nm=(src && src.name) || 'trim';
      var spec=(MDL.specOf(nm)) || {color:'#'+(src&&src.color? src.color.getHexString():'888888')};
      o.material=matFor(nm, spec, opts);
    });
    return root;
  }

  var allSpecs={};
  function indexSpecs(){
    for(var k in manifest){
      var ms=manifest[k].materials||{};
      for(var nm in ms) if(!allSpecs[nm]) allSpecs[nm]=ms[nm];
    }
  }

  return {
    specOf:function(nm){ return allSpecs[nm]; },
    ready:function(){ return ready; },
    /* Preload everything behind the title screen. 2.1 MB of GLB, which is one
       beat on a phone and nothing at all on a laptop. */
    load:function(onDone,onProgress){
      var loader=new THREE.GLTFLoader();
      fetch(ROOT+'manifest.json').then(function(r){ return r.json(); }).then(function(j){
        manifest=j; indexSpecs();
        var keys=Object.keys(manifest), done=0;
        if(!keys.length){ ready=true; onDone&&onDone(); return; }
        keys.forEach(function(k){
          fetch(ROOT+manifest[k].file).then(function(r){ return r.arrayBuffer(); })
            .then(function(buf){
              loader.parse(buf, '', function(g){
                cache[k]=g.scene;
                if(++done===keys.length){ ready=true; onDone&&onDone(); }
                onProgress&&onProgress(done,keys.length);
              }, function(){ if(++done===keys.length){ ready=true; onDone&&onDone(); } });
            })
            .catch(function(){ if(++done===keys.length){ ready=true; onDone&&onDone(); } });
        });
      }).catch(function(){ ready=true; onDone&&onDone(); });   /* no assets: fall back to the built in shells */
    },
    has:function(k){ return !!cache[k]; },
    info:function(k){ return manifest && manifest[k]; },
    /* A clone per use, with the shared materials carried across. */
    get:function(k,opts){
      if(!cache[k]) return null;
      var c=cache[k].clone(true);
      return convert(c, opts);
    },
    /* One named node out of a model, lifted out of its parent transform. */
    node:function(k,name,opts){
      var m=this.get(k,opts); if(!m) return null;
      var found=null;
      m.traverse(function(o){ if(!found && o.name===name) found=o; });
      if(found && found.parent) found.parent.remove(found);
      return found;
    }
  };
})();

/* ================= the truck ================= */""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
