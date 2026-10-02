# -*- coding: utf-8 -*-
"""Work order step 8b: the desert circuit's set dressing, and the bridges.

TWO THINGS THE PACK HAD PLACED AND THE GAME HAD NEVER DRAWN.

THE CIRCUIT'S DRESSING. `set_dressing_desert.json` holds 59 placements: 12
numbered boards round the lap and 47 tyre stacks round the pit and the three
ramps. The models for those were written in step 8's prep, so this is only the
placing. The tyre stacks are identical and go in as two instanced meshes; the
boards each carry a different number and so each need their own material, but
there are twelve of them, so twelve objects is the right answer and instancing
would be a false economy. The number is painted with `paintedFace()` rather
than extruded, which means it inherits the paper grain and the sun bleaching
every other painted face in the game gets.

THE PIKE NARROWS BRIDGES, which exist because Robert said the map was not
drivable: "the lakes need bridges across them". The pack ships nine, already
placed in world coordinates, so drawing them is a load and an add.

DRAWING THEM IS NOT THE POINT, THOUGH. A bridge you fall through is worse
than no bridge, and the physics reads the analytic `height()` functions, which
know nothing about a deck. Worse, `surfaceAt` would call the lake underneath
it water, with a friction of 0.58 and a rolling drag of 96, so a truck on a
bridge would feel like a truck in a lake.

So the bridges get a deck mask. `bridges.json` gives each crossing's
centreline as a polyline, not a straight span, so the footprint is rasterised
from those points into a 561 by 561 grid at one metre, the same grid the
painted terrain maps use. That is 315 KB and an O(1) lookup, where testing
distance to nine polylines of fifty segments each would be 450 segment tests
per height query, and `envHeight` asks five times per wheel per substep.

The mask is then read in exactly three places, and deliberately NOT in
`height()` itself:

    envHeight    the ground the tyres stand on, so max(terrain, deck)
    normalAt     flat on a deck, whatever the lake bed below is doing
    surfaceAt    gravel, not water

`height()` is what `buildTerrain` reads to make the ground mesh, so putting
the deck in there would ramp the terrain itself up out of the lake and the
bridge would sit on a causeway of its own making. Keeping the deck out of
`height()` and in the three physics readers is the whole trick.

Driving on and off needs no special case: the centreline polylines run up onto
the shore at both ends, where the terrain is already above the deck, so
`max(terrain, deck)` fairs into the bank by itself.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ------------------------------------------------------------- the deck mask
# Declared immediately before height(), not with its loader: buildTerrain runs
# during boot, and a `var` hoisted from a thousand lines below is undefined
# when the first wheel asks for it. That exact mistake cost an afternoon with
# TMAP in step 7.
sub("""function height(x,z){""",
r"""/* ---- step 8: the bridge decks ----
   The drivable top of each crossing, rasterised at one metre from the
   centreline polylines in bridges.json. Read by envHeight, normalAt and
   surfaceAt, and NOT by height(), which is what the terrain mesh is built
   from. See src/dressing.py. */
var DECK=null, DECK_N=561, DECK_HALF=280.5;
function deckAt(x,z){
  if(!DECK) return -1e9;
  var cx=Math.round(x+DECK_HALF), cy=Math.round(z+DECK_HALF);
  if(cx<0||cy<0||cx>=DECK_N||cy>=DECK_N) return -1e9;
  return DECK[cy*DECK_N+cx];
}
function buildDeckMask(list){
  var D=new Float32Array(DECK_N*DECK_N);
  D.fill(-1e9);
  for(var b=0;b<list.length;b++){
    var B=list[b], pts=B.pts||[], hw=(B.width||6)*0.5;
    /* the planks sit a little above the quoted deck line */
    var y=(B.deck_y||0)+0.15;
    for(var i=0;i+1<pts.length;i++){
      var x0=pts[i][0], z0=pts[i][1], x1=pts[i+1][0], z1=pts[i+1][1];
      var dx=x1-x0, dz=z1-z0, L=Math.sqrt(dx*dx+dz*dz);
      if(L<1e-6) continue;
      var ux=dx/L, uz=dz/L, nx=-uz, nz=ux;
      var ns=Math.ceil(L/0.5), nu=Math.ceil(hw/0.5);
      for(var a=0;a<=ns;a++){
        var t=a/ns, px=x0+dx*t, pz=z0+dz*t;
        for(var u=-nu;u<=nu;u++){
          var w=u*0.5, qx=px+nx*w, qz=pz+nz*w;
          var cx=Math.round(qx+DECK_HALF), cy=Math.round(qz+DECK_HALF);
          if(cx<0||cy<0||cx>=DECK_N||cy>=DECK_N) continue;
          var k=cy*DECK_N+cx;
          if(y>D[k]) D[k]=y;
        }
      }
    }
  }
  DECK=D;
}

function height(x,z){""")

# ---- the three readers
sub("""  var mx=Math.max(h0,Math.max(Math.max(a,b),Math.max(c,d)));
  var mean=(h0+a+b+c+d)*0.2;
  return mx*0.68+mean*0.32;""",
"""  var mx=Math.max(h0,Math.max(Math.max(a,b),Math.max(c,d)));
  var mean=(h0+a+b+c+d)*0.2;
  var h=mx*0.68+mean*0.32;
  /* a deck is flat and above whatever it crosses, so one sample settles it */
  var dk=deckAt(px,pz);
  return dk>h? dk : h;""")

sub("""function normalAt(x,z,out){
  var e=0.85;
  out.set(height(x-e,z)-height(x+e,z), 2*e, height(x,z-e)-height(x,z+e));
  return out.normalize();
}""",
"""function normalAt(x,z,out){
  var e=0.85;
  /* on a deck the lake bed below is irrelevant, and sampling it would tip the
     truck sideways over open water */
  if(deckAt(x,z)>height(x,z)) return out.set(0,1,0);
  out.set(height(x-e,z)-height(x+e,z), 2*e, height(x,z-e)-height(x,z+e));
  return out.normalize();
}""")

sub("""function surfaceAt(x,z,slope){
  if(MAP===2){
    if(shLakeD(x,z)<1.00) return 11;                  /* in the water */""",
"""function surfaceAt(x,z,slope){
  if(MAP===2){
    /* a bridge over a lake is gravel, not lake: without this the truck feels
       like it is wading the whole way across */
    if(deckAt(x,z)>height(x,z)) return 10;
    if(shLakeD(x,z)<1.00) return 11;                  /* in the water */""")

# ------------------------------------------------------------- the bridges
sub("/* ---- step 8: flora ---",
r"""/* ---- step 8: the Pike Narrows bridges ----
   Already placed in world coordinates by the pack, so this is a load, an add
   and the deck mask the physics reads. */
var BRIDGE_FILE={2:{glb:'bridges/bridges_pike_narrows.glb',
                    list:'terrain/shield/bridges.json'}};
var BRIDGE_GROUP={};
function addBridges(i){
  if(typeof MDL==='undefined' || !MDL.ready()) return;
  var F=BRIDGE_FILE[i];
  if(!F){ DECK=null; return; }
  if(BRIDGE_GROUP[i]){
    /* standing already; the mask belongs to this map, so put it back */
    if(BRIDGE_GROUP[i].userData.deck) DECK=BRIDGE_GROUP[i].userData.deck;
    return;
  }
  var key='bridges/'+i;
  BRIDGE_GROUP[i]='loading';
  MDL.loadOne(key, F.glb, function(ok){
    if(!ok){ BRIDGE_GROUP[i]=null; return; }
    var r=MDL.get(key,{tex:'rock'});
    if(!r){ BRIDGE_GROUP[i]=null; return; }
    r.traverse(function(o){
      if(!o.isMesh) return;
      o.castShadow=true; o.receiveShadow=true;
    });
    mapGroup(i).add(r);
    BRIDGE_GROUP[i]=r;
    fetch('assets/'+F.list).then(function(x){ return x.json(); }).then(function(list){
      buildDeckMask(list);
      r.userData.deck=DECK;
      if(MAP!==i) DECK=null;         /* the player moved on while this loaded */
    }).catch(function(e){ if(DEBUG && window.console) console.error('bridges', e); });
  });
}

/* ---- step 8: the desert circuit's set dressing ----
   12 numbered boards and 47 tyre stacks, from set_dressing_desert.json. */
var DRESS_GROUP={}, DRESS_SNOW=[];
var DRESS_FILE={0:'terrain/desert/set_dressing_desert.json'};
function addDressing(i){
  if(typeof MDL==='undefined' || !MDL.ready()) return;
  var file=DRESS_FILE[i]; if(!file || DRESS_GROUP[i]) return;
  if(!MDL.has('props/desert/tyre_stack') || !MDL.has('props/desert/gate_board')) return;
  DRESS_GROUP[i]='loading';
  fetch('assets/'+file).then(function(r){ return r.json(); }).then(function(list){
    /* `height()` branches on MAP, and this arrived asynchronously, so if the
       player has moved on every stack would be set to the wrong map's ground.
       Drop it and build again when this map next comes round. */
    if(MAP!==i){ DRESS_GROUP[i]=null; return; }
    var grp=new THREE.Group(), q, e;

    /* the tyre stacks: all the same, so two instanced meshes and done */
    var stacks=[];
    for(q=0;q<list.length;q++) if(list[q].kind==='tyre_stack') stacks.push(list[q]);
    if(stacks.length){
      var proto=MDL.get('props/desert/tyre_stack',{tex:'rock'});
      proto.updateMatrixWorld(true);
      var d5=new THREE.Object3D();
      proto.traverse(function(o){
        if(!o.isMesh) return;
        var snowy=/_snow/.test(o.name) || (o.parent && /_snow$/.test(o.parent.name));
        var g=o.geometry.clone(); g.applyMatrix4(o.matrixWorld);
        var im=new THREE.InstancedMesh(g, o.material, stacks.length);
        im.castShadow=true; im.receiveShadow=true;
        for(var k=0;k<stacks.length;k++){
          var t=stacks[k];
          d5.position.set(t.x, height(t.x,t.z), t.z);
          d5.rotation.set(0, t.yaw||0, 0);
          d5.scale.setScalar(1);
          d5.updateMatrix();
          im.setMatrixAt(k, d5.matrix);
        }
        im.instanceMatrix.needsUpdate=true;
        g.computeBoundingSphere();
        im.frustumCulled=false;      /* 47 stacks, 512 tris each: not worth it */
        if(snowy){ im.visible=!!FLORA.snow; DRESS_SNOW.push(im); }
        grp.add(im);
      });
    }

    /* the boards: each carries its own number, so each needs its own
       material, and twelve objects is cheaper than the machinery to avoid
       them */
    for(q=0;q<list.length;q++){
      e=list[q];
      if(e.kind!=='gate_board') continue;
      var b=MDL.get('props/desert/gate_board',{tex:'rock'});
      if(!b) break;
      b.position.set(e.x, height(e.x,e.z), e.z);
      b.rotation.y=e.yaw||0;
      (function(num){
        b.traverse(function(o){
          if(!o.isMesh) return;
          o.castShadow=true; o.receiveShadow=true;
          if(/_snow$/.test(o.name) || (o.parent && /_snow$/.test(o.parent.name))){
            o.visible=!!FLORA.snow; DRESS_SNOW.push(o);
          }
          if(o.material && o.material.name==='gateboard'){
            var m=o.material.clone();
            m.map=paintedFace(192,128,function(x,W,H){
              x.fillStyle='#efe4cf'; x.fillRect(0,0,W,H);
              x.strokeStyle='#b8360f'; x.lineWidth=7;
              x.strokeRect(10,10,W-20,H-20);
              x.fillStyle='#2b2320';
              x.font='bold 86px Helvetica, Arial, sans-serif';
              x.textAlign='center'; x.textBaseline='middle';
              x.fillText(String(num), W/2, H/2+4);
            });
            m.color.setRGB(1,1,1);     /* the paint carries the colour now */
            o.material=m;
          }
        });
      })(e.n);
      grp.add(b);
    }

    mapGroup(i).add(grp);
    DRESS_GROUP[i]=grp;
  }).catch(function(e){
    DRESS_GROUP[i]=null;
    if(DEBUG && window.console) console.error('dressing', e);
  });
}

/* ---- step 8: flora ---""")

# snow on the dressing rides along with the flora's
sub("""  FLORA.snow=on; updateFlora(true);""",
"""  FLORA.snow=on; updateFlora(true);
  for(var d=0;d<DRESS_SNOW.length;d++) DRESS_SNOW[d].visible=on;""")

# ------------------------------------------------------------- hook them in
sub("""  if(typeof buildFlora==='function') buildFlora(i);
  loadTerrainMaps(i, function(){ buildTerrain(); });""",
"""  if(typeof buildFlora==='function') buildFlora(i);
  if(typeof addBridges==='function') addBridges(i);
  if(typeof addDressing==='function') addDressing(i);
  loadTerrainMaps(i, function(){ buildTerrain(); });""")

sub("""    if(typeof buildFlora==='function') buildFlora(MAP);
    /* the painted ground, then one rebuild to use it */""",
"""    if(typeof buildFlora==='function') buildFlora(MAP);
    if(typeof addBridges==='function') addBridges(MAP);
    if(typeof addDressing==='function') addDressing(MAP);
    /* the painted ground, then one rebuild to use it */""")

# the harness needs to be able to ask where the decks are
sub("""  window.coilover={MDL:MDL,S:S,corners:corners,camera:camera,height:height,GATES:GATES,""",
"""  window.coilover={MDL:MDL,S:S,corners:corners,camera:camera,height:height,GATES:GATES,
    deckAt:deckAt,envHeight:envHeight,surfaceAt:surfaceAt,""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
