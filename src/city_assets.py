# -*- coding: utf-8 -*-
"""Step 5 continued: the city, built from models instead of merged boxes.

WHY THIS ONE NEEDS INSTANCING. The other props are a handful of objects each,
so swapping a group's contents is enough. The city is 206 buildings, and the
original does not build them as 206 objects: `buildCityBuildings` pushes six
boxes per record into a few merged tile meshes, which is why the city runs at
all on a phone. Dropping 206 loaded models in as separate objects would undo
that and cost hundreds of draw calls.

So each building model is taken apart once into its component meshes, and each
of those becomes one `InstancedMesh` carrying every building that uses it. Six
models of about nine meshes each is roughly fifty draw calls for the whole
city, which is the same order as the merged version it replaces.

THE RECORDS DRIVE IT, NOT THE LAYOUT FILE. The pack ships
`terrain/city/city_layout.json`, and it is tempting to place from that. I
compared it against the running game: 145 of its 188 parcels sit within 6 m of
a `BLD` record and 43 do not, by up to 30 m, because the layout deliberately
turns some blocks into parks and surface lots. Placing from it would put
buildings where the game has none and, worse, leave collision boxes standing in
open ground. Since the thing that broke the city before was the truck being
walled in, the records win: every model goes exactly where a collider already
is, and is scaled to that collider's own width, depth and height.

The facade shader stays off these. It draws windows procedurally onto the
merged boxes; the models bring their own, including lit shopfronts, which
register in the light pool through the usual glow path.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

sub("function buildCityBuildings(){",
r"""/* ---- the city, from models ----
   One InstancedMesh per component mesh per model, so 206 buildings cost about
   fifty draw calls rather than several hundred. Returns null if the models are
   not available, and the caller falls back to the merged boxes. */
var CITY_MODELS=['props/city/building_0','props/city/building_1','props/city/building_2',
                 'props/city/building_3','props/city/building_4','props/city/building_5'];
function buildCityModels(){
  if(typeof MDL==='undefined' || !MDL.ready()) return null;

  /* take each model apart once: geometry baked into the model's own frame,
     plus its material and its authored size */
  var parts=[], sizes=[];
  for(var mi=0;mi<CITY_MODELS.length;mi++){
    var key=CITY_MODELS[mi];
    if(!MDL.has(key)) return null;
    var root=MDL.get(key,{tex:'metal'});
    if(!root) return null;
    root.updateMatrixWorld(true);
    var box=new THREE.Box3().setFromObject(root);
    var sz=box.getSize(new THREE.Vector3());
    sizes.push({w:sz.x||1, d:sz.z||1, h:sz.y||1, base:box.min.y});
    var list=[];
    root.traverse(function(o){
      if(!o.isMesh) return;
      var g=o.geometry.clone();
      g.applyMatrix4(o.matrixWorld);          /* bake the local transform in */
      list.push({geo:g, mat:o.material});
    });
    parts.push(list);
  }

  /* choose a model per record: closest footprint, then closest height */
  var use=[]; for(var u=0;u<CITY_MODELS.length;u++) use.push([]);
  for(var i=0;i<BLD.length;i++){
    var B=BLD[i];
    if(B.h===undefined) continue;
    var best=0, bestScore=1e9;
    for(var m2=0;m2<sizes.length;m2++){
      var S=sizes[m2];
      var sc1=Math.abs(S.w-B.w)/Math.max(1,B.w) + Math.abs(S.d-B.d)/Math.max(1,B.d)
            + Math.abs(S.h-B.h)/Math.max(1,B.h)*0.6;
      if(sc1<bestScore){ bestScore=sc1; best=m2; }
    }
    use[best].push(B);
  }

  var grp=new THREE.Group(), d4=new THREE.Object3D(), made=0;
  for(var mi2=0;mi2<parts.length;mi2++){
    var recs=use[mi2]; if(!recs.length) continue;
    var S2=sizes[mi2];
    for(var pi=0;pi<parts[mi2].length;pi++){
      var P=parts[mi2][pi];
      var im=new THREE.InstancedMesh(P.geo, P.mat, recs.length);
      im.castShadow=true; im.receiveShadow=true;
      /* the bounding sphere of an InstancedMesh is the geometry's, at the
         group origin, so it culls away the moment the origin leaves frame */
      im.frustumCulled=false;
      for(var r=0;r<recs.length;r++){
        var R=recs[r];
        d4.position.set(R.x, R.y - S2.base*(R.h/S2.h), R.z);
        d4.scale.set(R.w/S2.w, R.h/S2.h, R.d/S2.d);
        d4.rotation.set(0,0,0);
        d4.updateMatrix();
        im.setMatrixAt(r, d4.matrix);
      }
      im.instanceMatrix.needsUpdate=true;
      grp.add(im); made++;
    }
  }
  grp.userData.drawCalls=made;
  return grp;
}

function buildCityBuildings(){""")

# and the caller prefers models, falling back to the merged boxes
sub("  G_CITY.add(buildCityBuildings());",
"""  /* Models if they are loaded, the merged boxes if not. Either way the BLD
     records are untouched, so collision matches whatever is drawn. */
  var cityMdl=buildCityModels();
  G_CITY.add(cityMdl || buildCityBuildings());""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
