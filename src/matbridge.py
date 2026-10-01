# -*- coding: utf-8 -*-
"""Every car came out the same colour. The materials have to be the game's own.

THE BUG. `MDL` created one material per NAME and shared it across every model,
which is right for `trim` or `chrome` and completely wrong for `paint`. Paint
is per vehicle: `__setVehicle` recolours the game's `paint` variable every time
you change car. The models were using a separate material that nobody was
recolouring, so all five cars rendered in whatever colour happened to be baked
into the first model that loaded, and switching car appeared to do nothing but
change the name on the card.

THE FIX, and it is better than patching the colour through. The model's
material names were deliberately chosen to be the game's own variable names.
So rather than MDL inventing materials, the truck registers its real ones:

    MDL.useMaterial('paint', paint); MDL.useMaterial('trim', trim); ...

and a loaded mesh called `paint` gets the actual `paint` object. That means the
per vehicle recolour, the glow registration, the time of day emissive, the rim
light settings and the grain projection all keep working on the models with no
further plumbing, because they were never about the geometry.

Only names the game has no material for -- `rubber`, `accent`, `post`, `vane`,
the prop-specific ones -- still get built from the manifest.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ---- MDL gains a registry that takes precedence over anything it would build
sub("""  function matFor(name, spec, opts){
    if(mats[name]) return mats[name];""",
"""  function matFor(name, spec, opts){
    /* The game's own material always wins. Its name is the model's name on
       purpose, and it is the one the rest of the game already drives. */
    if(given[name]) return given[name];
    if(mats[name]) return mats[name];""")

sub("""  var ROOT='assets/', manifest=null, cache={}, mats={}, ready=false;""",
"""  var ROOT='assets/', manifest=null, cache={}, mats={}, given={}, ready=false;""")

sub("""    specOf:function(nm){ return allSpecs[nm]; },
    ready:function(){ return ready; },""",
"""    specOf:function(nm){ return allSpecs[nm]; },
    /* Hand MDL a material the game already owns and drives. */
    useMaterial:function(nm,m){ given[nm]=m; return m; },
    ready:function(){ return ready; },""")

# ---- the truck hands over its materials, right after they are all defined
sub("""  var lampM=glowMat(0xfff3d0,0xfff0c0);
  var tailM=glowMat(0x8c2a22,0xff4530);""",
"""  var lampM=glowMat(0xfff3d0,0xfff0c0);
  var tailM=glowMat(0x8c2a22,0xff4530);

  /* ---- hand the real materials to the asset layer ----
     The Blender materials carry these exact names, so a loaded body picks up
     the same `paint` object that `__setVehicle` recolours, the same glow
     materials the time of day drives, and the same grain projection. Without
     this every car rendered in one colour. */
  if(typeof MDL!=='undefined'){
    MDL.useMaterial('paint',    paint);
    MDL.useMaterial('second',   second);
    MDL.useMaterial('trim',     trim);
    MDL.useMaterial('flare',    flare);
    MDL.useMaterial('carbon',   carbon);
    MDL.useMaterial('disc',     discM);
    MDL.useMaterial('caliper',  calM);
    MDL.useMaterial('shoulder', shoulder);
    MDL.useMaterial('tyre',     tyreM);
    MDL.useMaterial('lug',      lugM);
    MDL.useMaterial('rim',      rimM);
    MDL.useMaterial('chrome',   chrome);
    MDL.useMaterial('glass',    glass);
    MDL.useMaterial('canvas',   canvasM);
    MDL.useMaterial('spring',   spring);
    /* the lit parts, so they join the pool the sun already drives */
    MDL.useMaterial('glow_lamp', lampM);
    MDL.useMaterial('glow_tail', tailM);
  }""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
