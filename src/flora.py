# -*- coding: utf-8 -*-
"""Work order step 8a: 19,258 plants and rocks, and the culling the city owed.

THE NUMBER THAT DECIDES THE DESIGN. The two dress lists hold 8,038 shield and
11,220 desert instances across 127 variants. If every one drew, that is 5.6
million triangles, and the cost is not concentrated anywhere convenient: grass
is the most numerous thing by far and only 2 percent of the triangles, while
white pines at 1,150 each and desert scree at 884 carry most of it. So there
is no cheap win available by special casing one variant. Two budgets apply
instead, and they are the ones the handoff asks for: nothing draws beyond
250 m, and only things over 4 m cast a shadow.

DRAW CALLS WERE THE REAL PROBLEM, not triangles. The obvious build is one
InstancedMesh per glTF primitive, and the libraries hold 340 and 281 of them,
because the generator gave every tree its own needle colour: `needles_#2a4232`
and `needles_#2f4a35` are separate materials, so they are separate primitives,
so they would be separate draw calls. In fair weather that is 205 calls for
the shield before anything else in the world has drawn, which is most of a
phone's budget spent on telling trees apart by hue.

So the primitives are merged by ROLE and the hue is baked into vertex colours:
one call for all the bark in a tree, one for all its needles. Role is the unit
because `weather.js` keys entirely off `userData.role`, so bark, foliage, rock
and grass have to stay separable or the wet, the moss and the ice have nothing
to attach to. That takes the shield to 129 calls and the desert to 72, and
loses nothing visible: the colours are still per material, they are just
carried on the vertices now.

  shield   340 primitives  ->  205 fair weather calls  ->  129 merged by role
  desert   281 primitives  ->  150 fair weather calls  ->   72 merged by role

THE 250 M RADIUS, by refilling rather than by chunking. Each mesh is allocated
for every instance of its variant and its `count` is set to however many are
in range. Writing a matrix is cheap, the filter is one pass over the list, and
it only runs when the truck has moved 25 m, so it costs nothing per frame.
That implements the radius exactly instead of approximating it with tiles, and
the same pass hands us the bounds for a correct bounding sphere.

AND THE CITY'S DEBT, PAID HERE, THOUGH NOT THE WAY IT LOOKED.
`PERFORMANCE.md` recorded that the city submits 402k triangles every frame
because an InstancedMesh is culled against its geometry's bounding sphere at
the object ORIGIN, not against where its instances actually are, so culling
had to be off or the city vanished as soon as the origin left frame. The
obvious repair is to give each mesh a sphere that covers its own instances,
and that was tried first. Measured, it saved exactly nothing: the city groups
its buildings BY MODEL, and each of the six models is used right across the
map, so every corrected sphere came out the size of the city and every one of
them intersects the frustum from anywhere inside it.

So the city gets the same treatment as the flora, for the same reason. The
instance buffers are refilled with what is roughly in front of the camera, the
sphere is taken from where those instances actually went, and the whole thing
costs one pass over 206 records when the truck has moved or turned. That is
what takes the city's submitted triangles down, and it adds no draw calls,
which a spatial split into tiles would have.

ONE COLOUR BUG FIXED ON THE WAY. `convert()` reads a material colour back out
of the glTF as a hex string and hands it to `sc()`, which converts sRGB to
linear. That is right for the manifest, whose colours are authored sRGB hexes,
and wrong for anything loaded by `loadOne`, whose colours came from glTF and
are already linear: they were being converted a second time and rendering
markedly dark. That has been true of the roads since step 6. Fixed by marking
such a spec linear so `matFor` leaves it alone.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# --------------------------------------------- the double conversion
sub("""    var o={ color:sc(spec.color||'#888888'), specular:0x000000, shininess:0,
            flatShading:true };""",
"""    /* `spec.color` off the manifest is an authored sRGB hex and wants
       converting; a colour read back out of a glTF is already linear and must
       not be converted twice, or it renders dark. See `convert`. */
    var o={ color:(spec.linear? new THREE.Color(spec.color||'#888888')
                              : sc(spec.color||'#888888')),
            specular:0x000000, shininess:0, flatShading:true };""")

sub("""      var spec=(MDL.specOf(nm)) || {color:'#'+(src&&src.color? src.color.getHexString():'888888')};""",
"""      var spec=(MDL.specOf(nm)) ||
               {color:'#'+(src&&src.color? src.color.getHexString():'888888'), linear:true};""")

# --------------------------------------------- the flora itself
sub("/* ---- step 6: the roads ----",
r"""/* ---- step 8: flora ----------------------------------------------------
   One InstancedMesh per variant, per layer, per weather role, filled from the
   dress list with whatever is inside the radius. See src/flora.py. */
var FLORA={group:null, meshes:[], at:null, map:-1, snow:false};
var FLORA_FILE={0:{lib:'flora/flora_desert.glb', list:'terrain/desert/dress_desert.json',
                   man:'flora/flora_desert.json', tex:'sand'},
                2:{lib:'flora/flora_shield.glb', list:'terrain/shield/dress_shield.json',
                   man:'flora/flora_shield.json', tex:'rock'}};
/* Two budgets, both measured rather than guessed. A flat 250 m radius puts
   1.29 M triangles a frame into the shield and 2.09 M into the desert, which
   is a laptop number, not a phone one. Grading the radius by how tall a thing
   is costs nothing and is simply true to how the world reads: grass at 250 m
   is a pixel. Then only the instances roughly in front of the camera are
   written, with a wide margin so nothing appears inside the visible frame.

     shield   1.29 M  ->  0.95 M graded  ->  about 0.43 M with the cone
     desert   2.09 M  ->  0.75 M graded  ->  about 0.34 M with the cone

   The cone is the one that needs a margin: 75 degrees either side against a
   camera that sees about 40, and everything inside 40 m kept regardless, so a
   tree is already in the buffer long before it could be seen arriving. */
var FLORA_MOVE=25, FLORA_TURN=0.20, FLORA_SHADOW_H=4.0;
var FLORA_NEAR=40, FLORA_COS=Math.cos(1.31);     /* 75 degrees either side */
function floraRadius(tall){
  var r=60+tall*28; if(r>250) r=250;
  return mobile? r*0.7 : r;
}

/* Merge a set of flat shaded geometries into one, carrying each source
   material's colour onto its own vertices. r128's BufferGeometryUtils is not
   bundled and the game is one offline file, so this is the three attributes
   the shader actually reads and nothing else. */
function mergeTinted(parts){
  var nv=0, i, j;
  for(i=0;i<parts.length;i++){
    if(parts[i].geo.index) parts[i].geo=parts[i].geo.toNonIndexed();
    nv+=parts[i].geo.attributes.position.count;
  }
  var P=new Float32Array(nv*3), N=new Float32Array(nv*3), C=new Float32Array(nv*3), o=0;
  for(i=0;i<parts.length;i++){
    var g=parts[i].geo, pa=g.attributes.position.array, na=g.attributes.normal, c=parts[i].col;
    var cnt=g.attributes.position.count;
    P.set(pa, o*3);
    if(na) N.set(na.array, o*3);
    for(j=0;j<cnt;j++){ C[(o+j)*3]=c.r; C[(o+j)*3+1]=c.g; C[(o+j)*3+2]=c.b; }
    o+=cnt;
  }
  var out=new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(P,3));
  out.setAttribute('normal',   new THREE.BufferAttribute(N,3));
  out.setAttribute('color',    new THREE.BufferAttribute(C,3));
  out.computeBoundingSphere();
  return out;
}

/* One material per role, white, with the hue coming off the vertices. */
var FLORA_MAT={};
function floraMat(role, tex){
  var k=role+'|'+tex;
  if(FLORA_MAT[k]) return FLORA_MAT[k];
  var m=new THREE.MeshPhongMaterial({color:0xffffff, specular:0x000000, shininess:0,
                                     flatShading:true, vertexColors:true});
  m.name='flora_'+role;
  m.userData.role=role;                 /* weather.js keys entirely off this */
  FLORA_MAT[k]=styleMat(m, {tex:tex});
  return FLORA_MAT[k];
}

function clearFlora(){
  if(FLORA.group && FLORA.group.parent) FLORA.group.parent.remove(FLORA.group);
  FLORA.group=null; FLORA.meshes=[]; FLORA.at=null; FLORA.map=-1;
}

function buildFlora(i){
  if(typeof MDL==='undefined' || !MDL.ready()) return;
  if(FLORA.map===i) return;
  var F=FLORA_FILE[i];
  clearFlora();
  if(!F) return;
  FLORA.map=i;

  var key='flora/'+i;
  MDL.loadOne(key, F.lib, function(ok){
    if(!ok || FLORA.map!==i) return;
    Promise.all([fetch('assets/'+F.man).then(function(r){ return r.json(); }),
                 fetch('assets/'+F.list).then(function(r){ return r.json(); })])
      .then(function(both){
        if(FLORA.map!==i) return;
        var man=both[0], list=both[1];
        var root=MDL.get(key,{tex:F.tex});
        if(!root) return;
        root.updateMatrixWorld(true);

        /* Every mesh in the library, filed under its LAYER node. GLTFLoader
           names a mesh after its node only when that node holds a single
           primitive; a node with several becomes a Group named for the node
           with children called `spruce_0_main_1` and so on. Keying on the
           mesh's own name therefore found the bare snags and the birch leaves
           and silently dropped every spruce, pine, fir and boulder, which is
           why the first build was a forest of bare poles. Climb to the layer
           node instead. */
        var byNode={};
        root.traverse(function(o){
          if(!o.isMesh) return;
          var p=o, nm=o.name;
          while(p && !/_(main|snow|leaves)$/.test(nm)){ p=p.parent; nm=p? p.name : ''; }
          if(!nm) return;
          var g=o.geometry.clone(); g.applyMatrix4(o.matrixWorld);
          (byNode[nm]=byNode[nm]||[]).push({geo:g, mat:o.material});
        });

        /* and which placements belong to which variant */
        var per={};
        for(var q=0;q<list.length;q++) (per[list[q].model]=per[list[q].model]||[]).push(list[q]);

        var grp=new THREE.Group(), v, li, pi;
        FLORA.meshes=[];
        for(v in per){
          var info=man[v]; if(!info) continue;
          var sz=info.size_m_xyz_blender||[0,0,0];
          var tall=sz[2]||0;                       /* Blender is Z up */
          var layers=info.layers||['main'];
          for(li=0;li<layers.length;li++){
            var layer=layers[li], parts=byNode[v+'_'+layer];
            if(!parts || !parts.length) continue;
            /* split by weather role, merge everything else together */
            var byRole={};
            for(pi=0;pi<parts.length;pi++){
              var mt=parts[pi].mat;
              var role=(mt.userData && mt.userData.role) || 'wood';
              (byRole[role]=byRole[role]||[]).push({geo:parts[pi].geo, col:mt.color});
            }
            for(var role2 in byRole){
              var geo=mergeTinted(byRole[role2]);
              var im=new THREE.InstancedMesh(geo, floraMat(role2, F.tex), per[v].length);
              im.count=0;
              im.castShadow=(layer!=='snow' && tall>=FLORA_SHADOW_H);
              im.receiveShadow=true;
              im.userData.layer=layer;
              /* the sphere is rewritten with the instances' own bounds on
                 every refill, so culling is a real test and stays on */
              im.frustumCulled=true;
              grp.add(im);
              FLORA.meshes.push({im:im, items:per[v], layer:layer, rad:floraRadius(tall),
                                 r0:geo.boundingSphere.radius+geo.boundingSphere.center.length()});
            }
          }
        }
        mapGroup(i).add(grp);
        FLORA.group=grp;
        FLORA.at=null;
        updateFlora(true);
      }).catch(function(e){
        /* a bare catch here hid a real failure once already, so say so */
        if(DEBUG && window.console) console.error('flora', e);
      });
  });
}

/* ---- the same refill, for the city ----
   Registered by buildCityModels. A building is never out of sight for being
   far away, only for being behind you, so this is the cone without the
   radius. See the note at the top of src/flora.py. */
var CITYV=[];
function updateCity(px,pz,fx,fz){
  if(!CITYV.length) return;
  var N2=FLORA_NEAR*FLORA_NEAR;
  for(var m=0;m<CITYV.length;m++){
    var E=CITYV[m], im=E.im, mats=E.mats, k=0;
    var lx=1e9,hx=-1e9,ly=1e9,hy=-1e9,lz=1e9,hz=-1e9;
    for(var r=0;r<mats.length;r++){
      var e=mats[r].elements, dx=e[12]-px, dz=e[14]-pz, d2=dx*dx+dz*dz;
      if(d2>N2 && (dx*fx+dz*fz) < FLORA_COS*Math.sqrt(d2)) continue;
      im.setMatrixAt(k++, mats[r]);
      if(e[12]<lx)lx=e[12]; if(e[12]>hx)hx=e[12];
      if(e[13]<ly)ly=e[13]; if(e[13]>hy)hy=e[13];
      if(e[14]<lz)lz=e[14]; if(e[14]>hz)hz=e[14];
    }
    im.count=k;
    if(!k){ im.visible=false; continue; }
    im.visible=true;
    im.instanceMatrix.needsUpdate=true;
    var bs=im.geometry.boundingSphere;
    bs.center.set((lx+hx)*0.5, (ly+hy)*0.5, (lz+hz)*0.5);
    /* the records carry a scale, and a tower scaled up reaches well past its
       own origin, so be generous rather than clip a skyline */
    bs.radius=0.5*Math.sqrt((hx-lx)*(hx-lx)+(hy-ly)*(hy-ly)+(hz-lz)*(hz-lz))+E.r0*4;
  }
}

/* Step 9 will drive this; until then it is fair weather everywhere. */
function floraSnow(on){
  on=!!on;
  if(on===FLORA.snow) return;
  FLORA.snow=on; updateFlora(true);
}

var _fd=new THREE.Object3D(), _fv=new THREE.Vector3();
function updateFlora(force){
  var px=S.p.x, pz=S.p.z;
  camera.getWorldDirection(_fv);
  var fx=_fv.x, fz=_fv.z, fl=Math.sqrt(fx*fx+fz*fz)||1;
  fx/=fl; fz/=fl;
  if(!force && FLORA.at &&
     (px-FLORA.at.x)*(px-FLORA.at.x)+(pz-FLORA.at.z)*(pz-FLORA.at.z) < FLORA_MOVE*FLORA_MOVE &&
     (fx*FLORA.at.fx+fz*FLORA.at.fz) > Math.cos(FLORA_TURN)) return;
  FLORA.at={x:px, z:pz, fx:fx, fz:fz};
  updateCity(px, pz, fx, fz);
  if(!FLORA.group || !FLORA.meshes.length) return;
  var N2=FLORA_NEAR*FLORA_NEAR;
  for(var m=0;m<FLORA.meshes.length;m++){
    var E=FLORA.meshes[m], im=E.im, items=E.items, k=0, R2=E.rad*E.rad;
    if(E.layer==='snow' && !FLORA.snow){ im.count=0; im.visible=false; continue; }
    im.visible=true;
    var lx=1e9,hx=-1e9,ly=1e9,hy=-1e9,lz=1e9,hz=-1e9, ms=0;
    for(var q=0;q<items.length;q++){
      var e=items[q], dx=e.x-px, dz=e.z-pz, d2=dx*dx+dz*dz;
      if(d2>R2) continue;
      /* anything close stays in whatever way the camera is pointed */
      if(d2>N2 && (dx*fx+dz*fz) < FLORA_COS*Math.sqrt(d2)) continue;
      _fd.position.set(e.x, e.y, e.z);
      _fd.rotation.set(0, e.yaw, 0);
      _fd.scale.setScalar(e.s);
      _fd.updateMatrix();
      im.setMatrixAt(k++, _fd.matrix);
      if(e.x<lx)lx=e.x; if(e.x>hx)hx=e.x;
      if(e.y<ly)ly=e.y; if(e.y>hy)hy=e.y;
      if(e.z<lz)lz=e.z; if(e.z>hz)hz=e.z;
      if(e.s>ms) ms=e.s;
    }
    im.count=k;
    if(!k){ im.visible=false; continue; }
    im.instanceMatrix.needsUpdate=true;
    /* an InstancedMesh culls on its GEOMETRY's sphere, so give it one that
       covers where the instances actually are */
    var bs=im.geometry.boundingSphere;
    bs.center.set((lx+hx)*0.5, (ly+hy)*0.5, (lz+hz)*0.5);
    bs.radius=0.5*Math.sqrt((hx-lx)*(hx-lx)+(hy-ly)*(hy-ly)+(hz-lz)*(hz-lz))+E.r0*ms;
  }
}

/* ---- step 6: the roads ----""")

# ---------------------------------------------------- hook it in
sub("""  if(typeof addRoads==='function') addRoads(i);
  loadTerrainMaps(i, function(){ buildTerrain(); });""",
"""  if(typeof addRoads==='function') addRoads(i);
  if(typeof buildFlora==='function') buildFlora(i);
  loadTerrainMaps(i, function(){ buildTerrain(); });""")

sub("""    if(typeof addRoads==='function') addRoads(MAP);
    /* the painted ground, then one rebuild to use it */""",
"""    if(typeof addRoads==='function') addRoads(MAP);
    if(typeof buildFlora==='function') buildFlora(MAP);
    /* the painted ground, then one rebuild to use it */""")

sub("""    stepDust(dt);""",
"""    stepDust(dt);
    if(typeof updateFlora==='function') updateFlora(false);""")

# ---------------------------------------------------- the city's debt
# one set of matrices per model, shared by that model's component meshes
sub("""  var grp=new THREE.Group(), d4=new THREE.Object3D(), made=0;
  for(var mi2=0;mi2<parts.length;mi2++){
    var recs=use[mi2]; if(!recs.length) continue;
    var S2=sizes[mi2];""",
"""  var grp=new THREE.Group(), d4=new THREE.Object3D(), made=0;
  CITYV=[];
  for(var mi2=0;mi2<parts.length;mi2++){
    var recs=use[mi2]; if(!recs.length) continue;
    var S2=sizes[mi2];
    /* A building's place never changes, so work its matrix out once here and
       let every component mesh of that model pick from the same list. */
    var mats=[];
    for(var r=0;r<recs.length;r++){
      var R=recs[r];
      d4.position.set(R.x, R.y, R.z);
      d4.scale.set(R.w/S2.w, R.h/S2.h, R.d/S2.d);
      d4.rotation.set(0,0,0);
      d4.updateMatrix();
      mats.push(d4.matrix.clone());
    }""")

sub("""      var im=new THREE.InstancedMesh(P.geo, P.mat, recs.length);
      im.castShadow=true; im.receiveShadow=true;
      /* the bounding sphere of an InstancedMesh is the geometry's, at the
         group origin, so it culls away the moment the origin leaves frame */
      im.frustumCulled=false;
      for(var r=0;r<recs.length;r++){
        var R=recs[r];
        d4.position.set(R.x, R.y, R.z);
        d4.scale.set(R.w/S2.w, R.h/S2.h, R.d/S2.d);
        d4.rotation.set(0,0,0);
        d4.updateMatrix();
        im.setMatrixAt(r, d4.matrix);
      }
      im.instanceMatrix.needsUpdate=true;""",
"""      var im=new THREE.InstancedMesh(P.geo, P.mat, recs.length);
      im.castShadow=true; im.receiveShadow=true;
      im.count=0;                      /* updateCity fills it */""")

sub("""  grp.userData.drawCalls=made;
  return grp;""",
"""  grp.userData.drawCalls=made;
  /* nothing is in the buffers yet, so fill them before the first frame */
  FLORA.at=null;
  if(typeof updateFlora==='function') updateFlora(true);
  return grp;""")

sub("""      grp.add(im); made++;""",
"""      /* PERFORMANCE.md's 402k a frame, paid here: the mesh is handed to the
         same refill the flora uses, so it carries only the buildings roughly
         in front of the camera and gets a bounding sphere drawn round them.
         See src/flora.py for why a corrected sphere alone saved nothing. */
      P.geo.computeBoundingSphere();
      im.frustumCulled=true;
      CITYV.push({im:im, mats:mats, r0:P.geo.boundingSphere.radius
                                      +P.geo.boundingSphere.center.length()});
      grp.add(im); made++;""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
