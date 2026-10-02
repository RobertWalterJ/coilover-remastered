# -*- coding: utf-8 -*-
"""Step 5, last part: the Pike Narrows structures.

Same method as the landmarks. Each structure already builds into its own
group, at a position the placement code worked out from the terrain (camps
walk out from the lake until the ground is flat, the fire tower finds the
highest dome). Those decisions are worth keeping, so the groups stay where
they are and only their contents are replaced.

Each group is tagged as it is built, which is cheaper and far less fragile
than trying to recognise a cottage by its shape afterwards.

The trees, erratics and the bridge bays are NOT done here. Spruce, birch and
boulders belong to step 8 with the proper flora library and its instance
lists, and the bridges belong to the same step with `bridges.json`, which
places real trusses and trestles rather than the single bay the old code
repeated. Doing them twice would be wasted work.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ---- tag each structure as it is built, so the swap can find it ----
sub("""  function camp(cx,cz,ang){
    var g=new THREE.Group();
    var gy=height(cx,cz);
    g.position.set(cx,gy,cz); g.rotation.y=ang; G_SHIELD.add(g);""",
"""  function camp(cx,cz,ang){
    var g=new THREE.Group();
    var gy=height(cx,cz);
    g.position.set(cx,gy,cz); g.rotation.y=ang; G_SHIELD.add(g);
    g.userData.asset='props/shield/cottage';""")

sub("""  function dock(sx,sz,dirX,dirZ){
    var g=new THREE.Group(); G_SHIELD.add(g);""",
"""  function dock(sx,sz,dirX,dirZ){
    var g=new THREE.Group(); G_SHIELD.add(g);
    /* the dock walks its own length out over the water, so it keeps its
       built planks; only the canoe on it becomes a model */
    g.userData.assetCanoe=true;""")

sub("""    var g=new THREE.Group(); g.position.set(sx,gy,sz); G_SHIELD.add(g);
    put(g,11.0,4.0,7.0, woodM, 0,2.00,0);""",
"""    var g=new THREE.Group(); g.position.set(sx,gy,sz); G_SHIELD.add(g);
    g.userData.asset='props/shield/general_store';
    put(g,11.0,4.0,7.0, woodM, 0,2.00,0);""")

sub("""    var g=new THREE.Group(); g.position.set(px,gy,pz); g.rotation.y=0.8; G_SHIELD.add(g);
    put(g,1.9,0.9,4.4, rustM, 0,0.85,0);""",
"""    var g=new THREE.Group(); g.position.set(px,gy,pz); g.rotation.y=0.8; G_SHIELD.add(g);
    g.userData.asset='props/shield/derelict_pickup';
    put(g,1.9,0.9,4.4, rustM, 0,0.85,0);""")

sub("""    var g=new THREE.Group(); g.position.set(bx,gy,bz); G_SHIELD.add(g);
    var H=17;""",
"""    var g=new THREE.Group(); g.position.set(bx,gy,bz); G_SHIELD.add(g);
    g.userData.asset='props/shield/fire_tower';
    var H=17;""")

sub("""      var g=new THREE.Group(); g.position.set(px2,gy,pz2); G_SHIELD.add(g);
      put(g,0.24,9.4,0.24, poleM, 0,4.70,0);""",
"""      var g=new THREE.Group(); g.position.set(px2,gy,pz2); G_SHIELD.add(g);
      g.userData.asset='props/shield/hydro_pole';
      put(g,0.24,9.4,0.24, poleM, 0,4.70,0);""")

# ---- and swap them when the models are in ----
sub("""  /* ---- the twelve circuit gates ----""",
"""  /* ---- Pike Narrows structures ----
     Each was tagged with its model as it was built, so the placement work
     (camps on flat shore, the tower on the highest dome) is kept and only
     the geometry changes. */
  if(typeof G_SHIELD!=='undefined') G_SHIELD.traverse(function(o){
    if(!o.isGroup || o.userData.assetDone) return;
    if(o.userData.asset && MDL.has(o.userData.asset)){
      var mm=MDL.get(o.userData.asset,{tex:'rock'});
      if(mm){ clearBuilt(o,[]); o.add(mm); o.userData.assetDone=true; }
    }
    /* the camps carry an outhouse of their own */
    if(o.userData.asset==='props/shield/cottage' && o.userData.assetDone
       && MDL.has('props/shield/outhouse')){
      var oh=MDL.get('props/shield/outhouse',{tex:'rock'});
      if(oh){ oh.position.set(5.0,0,2.6); o.add(oh); }
    }
  });

  /* ---- the twelve circuit gates ----""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
