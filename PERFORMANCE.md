# Performance debt, and where it gets paid

One open item, recorded here so it is not lost between sessions. It is
deliberately deferred, not forgotten.

## Open: the city submits every triangle, every frame

**What.** `buildCityModels()` draws 206 buildings as instanced meshes, about
108 draw calls and roughly 402,000 triangles. Every one of those triangles is
submitted on every frame, whichever way the camera is pointing, because the
instanced meshes have `frustumCulled = false`.

**Why it is like that.** An `InstancedMesh` in three.js r128 is culled against
its *geometry's* bounding sphere placed at the object's origin, not against the
spread of its instances. All 206 buildings share one object at the world
origin, so with culling left on the whole city vanishes the moment the origin
leaves frame. Switching it off is correct, and expensive.

**What the original did.** `buildCityBuildings()` merges its boxes into one
mesh per 192 m tile (`BTILE`), so three.js culls whole tiles properly. The
model version is a regression against that and should not stay one.

**The fix.** Chunk instances by the same 192 m tile key, one set of instanced
meshes per tile, each with a bounding sphere covering its own tile so culling
works again. Typically one to four tiles are in view, so this should cut
submitted triangles by roughly three quarters at the cost of more draw calls.

**Where it gets paid: step 8.** Flora needs exactly the same machinery, with a
250 m radius around the truck, and the handoff says so explicitly under
"Budget for phones". Building one chunked instancing helper for buildings,
flora and rocks together is better than building it twice.

**How to tell it worked.** Count triangles actually submitted, not triangles
that exist. `renderer.info.render.triangles` is reset by the post-processing
chain, so read it immediately after the main scene pass rather than at the end
of the frame.

## Watch list, not yet a problem

- **Roads.** `roads_city.glb` is 13 MB on its own. Loaded per map rather than
  at boot, so it costs nothing on the other two maps.
- **Flora.** 76 shield variants and 51 desert variants, with about 8,000 and
  11,800 instances in the dress lists. One `InstancedMesh` per variant part is
  the plan from the handoff; the 250 m radius is what keeps it affordable.
- **Shadow casters.** Step 8 says shadows from trees and big rocks only. Worth
  holding to: every caster is a second pass over that geometry.
