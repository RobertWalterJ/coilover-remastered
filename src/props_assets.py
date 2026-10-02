# -*- coding: utf-8 -*-
"""Work order step 5, first pass: the desert landmarks and the circuit gates.

HOW THE SWAP WORKS, and why it is not a rewrite. Every landmark already lives
in its own group at the right place, with the right yaw, holding its discovery
orb and its flag. `place()` put it there and the game's logic holds a reference
to that group. So rather than rewriting eight builder functions, this walks the
existing groups and replaces only the geometry inside them, keeping the group,
the orb, the flag and every reference the game already has.

That means the swap is reversible by doing nothing: if a model is missing, the
boxes stay and the landmark still works.

THREE THINGS THE OLD BOXES DID THAT THE MODELS MUST KEEP DOING:

  - The windmill's rotor spins. It is lifted out of the group by `place` into
    `WINDMILL` and turned every frame, so the loaded `windmill_rotor` node has
    to take its place rather than being swallowed by the body.
  - The flag and the orb are the discovery state. They are added by `place`
    AFTER the build, so clearing has to spare them.
  - A gate's beam is the next-gate indicator, and `checkGates` recolours every
    OTHER child of the gate group to teal when you pass through. So the beam is
    spared and the model's parts become the things that recolour.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

sub("/* Replace the procedural wheel and strut meshes with the modelled ones.",
r"""/* ---- step 5: the built world, swapped for the modelled one ----
   Each entry keeps the group the game already holds a reference to and
   replaces only what is inside it, so positions, yaw, collision records,
   discovery state and every existing reference survive untouched. */
var PROP_FOR={
  'Gas station':'props/desert/gas_station',
  'Motel sign' :'props/desert/motel_sign',
  'Drive in'   :'props/desert/drive_in',
  'Water tower':'props/desert/water_tower',
  'Old wreck'  :'props/desert/aircraft_wreck',
  'The camp'   :'props/desert/camp',
  'Windmill'   :'props/desert/windmill',
  'Stone ring' :'props/desert/stone_ring'
};

/* Empty a group of its built geometry while sparing the things the game holds
   on to by reference. */
function clearBuilt(g, spare){
  for(var i=g.children.length-1;i>=0;i--){
    var c=g.children[i];
    if(spare && spare.indexOf(c)>=0) continue;
    g.remove(c);
  }
}

function rebuildAssetProps(){
  if(typeof MDL==='undefined' || !MDL.ready()) return;
  var opts={tex:'rock'};

  /* ---- the eight landmarks ---- */
  for(var i=0;i<LANDMARKS.length;i++){
    var L=LANDMARKS[i];
    if(!L.g || L.assetDone) continue;
    var key=PROP_FOR[L.name];
    if(!key || !MDL.has(key)) continue;
    var m=MDL.get(key,opts);
    if(!m) continue;
    clearBuilt(L.g,[L.orb,L.flag]);
    L.g.add(m);
    L.assetDone=true;
  }

  /* ---- the windmill rotor, which turns every frame ---- */
  if(typeof WINDMILL!=='undefined' && WINDMILL && !WINDMILL.assetDone
     && MDL.has('props/desert/windmill')){
    var rot=MDL.node('props/desert/windmill','windmill_rotor',opts);
    if(rot){
      clearBuilt(WINDMILL,[]);
      rot.position.set(0,0,0); rot.rotation.set(0,0,0);
      WINDMILL.add(rot);
      WINDMILL.assetDone=true;
    }
  }

  /* ---- the twelve circuit gates ----
     checkGates recolours every child except the beam to teal on a pass, so
     the model's meshes have to BE those children. */
  for(var gi=0;gi<GATES.length;gi++){
    var G=GATES[gi];
    if(!G.g || G.assetDone || !MDL.has('props/desert/circuit_gate')) continue;
    var gm=MDL.get('props/desert/circuit_gate',{tex:'metal'});
    if(!gm) continue;
    clearBuilt(G.g,[G.beam]);
    /* lift the meshes up to be direct children, so the recolour walk reaches
       them: it only looks at g.children, not the whole subtree */
    var kids=[];
    gm.traverse(function(o){ if(o.isMesh) kids.push(o); });
    kids.forEach(function(o){
      if(o.parent) o.parent.remove(o);
      o.material=o.material.clone();   /* a gate recolours on its own */
      G.g.add(o);
    });
    G.assetDone=true;
  }
}

/* Replace the procedural wheel and strut meshes with the modelled ones.""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
