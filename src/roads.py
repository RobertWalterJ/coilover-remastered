# -*- coding: utf-8 -*-
"""Work order step 6: the roads.

LOADED PER MAP, NOT AT BOOT. `roads_city.glb` is 13 MB on its own, six times
everything else put together. Pulling it down at startup would delay the first
drive on every map including the two that never use it, so roads load the
first time their map is shown and are cached from then on. They are not in
`manifest.json`, so MDL gains a small on-demand path for files that are known
by name rather than listed.

POLYGON OFFSET, AND WHY NOT ON THE SHARED MATERIAL. The game's terrain is a
coarse 5 m grid, so between samples the mesh bows above the true surface the
roads were built against, and a road laid 2 to 10 cm proud still disappears
into it in places. The fix the pack asks for is `polygonOffset` with factor -1
and units -4.

That cannot go on the shared material by name, because `asphalt` and
`concrete` are used by things that are not roads, and a depth bias on a
building would be wrong. So road materials are cloned per road model and
biased there. The exception is anything named `glow_*`: those are matched by
IDENTITY in the light pool, so cloning one would quietly drop a traffic signal
out of the lighting. Those stay shared and unbiased, which is right anyway as
they are lenses and panels standing above the surface, not lying on it.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ---- MDL gains an on-demand path for files that are not in the manifest
sub("""    has:function(k){ return !!cache[k]; },""",
"""    has:function(k){ return !!cache[k]; },
    /* Fetch and parse one file that is not in the manifest, once. Used for
       the roads, which are per map and far too big to pull in at boot. */
    loadOne:function(k,file,cb){
      if(cache[k]){ cb && cb(true); return; }
      if(pending[k]){ pending[k].push(cb); return; }
      pending[k]=[cb];
      var loader=new THREE.GLTFLoader();
      fetch(ROOT+file).then(function(r){
        if(!r.ok) throw new Error(r.status);
        return r.arrayBuffer();
      }).then(function(buf){
        loader.parse(buf,'',function(g){
          cache[k]=g.scene;
          var q=pending[k]; pending[k]=null;
          q.forEach(function(f){ f && f(true); });
        }, function(){ var q=pending[k]; pending[k]=null; q.forEach(function(f){ f && f(false); }); });
      }).catch(function(){
        var q=pending[k]; pending[k]=null; q.forEach(function(f){ f && f(false); });
      });
    },""")

sub("  var ROOT='assets/', manifest=null, cache={}, mats={}, given={}, ready=false;",
    "  var ROOT='assets/', manifest=null, cache={}, mats={}, given={}, pending={}, ready=false;")

# ---- the roads themselves
sub("function rebuildAssetProps(){",
r"""/* ---- step 6: the roads ----
   One GLB per map, laid on the same height functions the physics reads, so
   nothing needs to change about how the ground feels. */
var ROAD_FILE={0:'roads/roads_desert.glb', 1:'roads/roads_city.glb', 2:'roads/roads_shield.glb'};
var ROAD_GROUP={};
function mapGroup(i){ return i===1? G_CITY : (i===2? G_SHIELD : G_DESERT); }

function addRoads(i){
  if(typeof MDL==='undefined' || !MDL.ready()) return;
  if(ROAD_GROUP[i]) return;                       /* already standing */
  var file=ROAD_FILE[i]; if(!file) return;
  var key='roads/'+i;
  ROAD_GROUP[i]='loading';
  MDL.loadOne(key, file, function(ok){
    if(!ok){ ROAD_GROUP[i]=null; return; }
    var r=MDL.get(key,{tex:'rock'});
    if(!r){ ROAD_GROUP[i]=null; return; }
    /* The terrain is a 5 m grid and bows above the true surface between
       samples, so a road lying 2 to 10 cm proud still sinks into it. Bias the
       depth test rather than lifting the road, which would float at the
       crests instead. Clone to bias, but never clone a glow material: the
       light pool matches those by identity. */
    var biased={};
    r.traverse(function(o){
      if(!o.isMesh || !o.material) return;
      var m=o.material;
      if(m.name && m.name.indexOf('glow_')===0) return;
      if(!biased[m.uuid]){
        var c=m.clone();
        c.polygonOffset=true; c.polygonOffsetFactor=-1; c.polygonOffsetUnits=-4;
        c.userData=m.userData;                     /* keep the weather role */
        biased[m.uuid]=c;
      }
      o.material=biased[m.uuid];
      o.receiveShadow=true; o.castShadow=false;    /* a road casts nothing */
    });
    mapGroup(i).add(r);
    ROAD_GROUP[i]=r;
    if(typeof rebuildLightPts==='function') rebuildLightPts();
  });
}

function rebuildAssetProps(){""")

sub("""  /* the props for this map have just been built, so swap in their models */
  if(typeof rebuildAssetProps==='function') rebuildAssetProps();""",
"""  /* the props for this map have just been built, so swap in their models */
  if(typeof rebuildAssetProps==='function') rebuildAssetProps();
  if(typeof addRoads==='function') addRoads(i);""")

# and on the map we are already standing on when the models arrive
sub("""    if(MAP===1 && typeof buildCityProps==='function'){ buildCityProps(); rebuildLightPts(); }""",
"""    if(MAP===1 && typeof buildCityProps==='function'){ buildCityProps(); rebuildLightPts(); }
    if(typeof addRoads==='function') addRoads(MAP);""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
