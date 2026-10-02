# Performance debt, and where it gets paid

## Paid in step 8: the city no longer submits every triangle

**What it was.** `buildCityModels()` draws 206 buildings as instanced meshes,
about 108 draw calls and roughly 402,000 triangles, every one of them
submitted on every frame whichever way the camera pointed, because the meshes
had `frustumCulled = false`. An `InstancedMesh` in three.js r128 is culled
against its *geometry's* bounding sphere placed at the object's origin, not
against the spread of its instances, so with culling left on the whole city
vanished the moment the origin left frame.

**What did not work, and why it is worth recording.** The obvious repair is to
give each mesh a bounding sphere that actually covers its own instances, and
that was written first. Measured, it saved exactly nothing: the city groups
its buildings BY MODEL, and each of the six models is used right across the
map, so every corrected sphere came out the size of the city and intersected
the frustum from anywhere inside it. A correct sphere is not the same as a
useful one.

**What worked.** The instance buffers are refilled with the buildings roughly
in front of the camera, 75 degrees either side with everything inside 40 m
kept regardless, and the sphere is then drawn round where those instances
actually went. The refill runs when the truck has moved 25 m or turned about
12 degrees, so it costs one pass over 206 records a few times a second.

    submitted triangles   455,000  ->  140,000       (69 percent less)
    draw calls            unchanged

It adds no draw calls, which the planned 192 m tile split would have. Flora
uses the same refill, which is why the two live together in `src/flora.py`.

**How it was measured.** `renderer.info.render.triangles` is reset by the
post-processing chain, so it is useless read at the end of a frame. Instead:
walk the scene, sum `count * triangles-per-instance` over every visible
`InstancedMesh`, and separately sum only those whose bounding sphere passes a
frustum built from the camera. The first number is what the buffers hold, the
second is what survives culling.

## Flora, sized in step 8

A flat 250 m radius puts 1.29 M triangles a frame into the shield and 2.09 M
into the desert. Two budgets bring that down, both measured rather than
guessed, and neither of them costs a draw call:

    radius graded by height   r = min(250, 60 + 28 * height), x0.7 on phones
    the same view cone        75 degrees either side, everything inside 40 m

    shield   1.29 M  ->  0.95 M graded  ->  about 0.30 M measured in play
    desert   2.09 M  ->  0.75 M graded  ->  about 0.17 M measured in play

Draw calls are the other half of the story, and they were the part that nearly
went wrong. One `InstancedMesh` per glTF primitive would be 205 calls for the
shield in fair weather, because the generator gave every tree its own needle
colour and so its own material. Merging primitives by weather role and baking
the hue into vertex colours takes that to 129 and 72, with nothing lost: the
colours are still per material, they are just carried on the vertices.

## Watch list, not yet a problem

- **Roads.** `roads_city.glb` is 13 MB on its own. Loaded per map rather than
  at boot, so it costs nothing on the other two maps.
- **Shadow casters.** Step 8 holds the handoff's rule: only flora over 4 m
  casts, which is 32 of 76 shield variants and 16 of 51 desert ones. Every
  caster is a second pass over that geometry.
- **The cone and shadows.** Something behind the camera can still cast into
  view, and the cone does not fill it. The margin is wide enough that this has
  not shown up, but it is the first place to look if a shadow goes missing
  when the camera swings.
