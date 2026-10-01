# Coilover asset audit

Read only audit of `src/game.html` (three.js r128). Line numbers refer to that file as of the 2a32342 commit.

## Ground rules the remaster follows

- No model loader exists. Only `three.min.js` r128 is loaded (line 5). The game must stay offline-capable.
- Collision almost never reads geometry. The ground is the analytic `height(x, z)` (line 1184), which also holds the ramps, mesa, whoops, rock spine, basin wall, causeways and lakebeds. The only prop colliders are axis-aligned `BLD` boxes, and `hitWalls` runs on the city map only (line 4136).
- The look is a shader patch: `styleMat()` (lines 579 to 760) string-replaces the Phong fragment shader's `outgoingLight` line. glTF materials must be converted to `MeshPhongMaterial` before `styleMat` will do anything.
- Surface grain is projected (world XZ for static things, object space for moving things), so UVs only matter on painted canvas faces.
- Units are metres, +Y up, vehicles face +Z, +X is the vehicle's left.

## Palette (`PAL`, lines 767 to 774)

low b8683a, mid dc9a4e, high f2c877, playa d8d0bd, rock 9c5350, peak 7a5c82, fog b98498, scrub 5e6b4a, sun ffb870, skyFill 8e7aa8, groundFill b0603a, bounce 7a6aa0, body 2f7a86, spring e85a2c, tyre 241f2a, wheel 8a8070, dust e8c79a.

## Vehicles (lines 2570 to 3285)

| Vehicle | Track | Wheelbase | Wheel R | Tyre W | Rest | bodyY | W x L | Paint / second |
|---|---|---|---|---|---|---|---|---|
| Bracken | 2.06 | 3.10 | .55 | .62 | .60 | -.18 | 1.78 x 4.30 | 3f9dab / f0ece0 |
| Marisol T4 | 2.32 | 3.24 | .60 | .68 | .72 | -.10 | 2.36 x 4.55 | e0683a / f2e8d4 |
| Kestrel RS | 1.94 | 2.62 | .49 | .52 | .50 | -.24 | 1.96 x 4.05 | d8c352 / 3a3f52 |
| Serrano SV | 2.14 | 2.72 | .47 | .56 | .46 | -.26 | 2.06 x 4.12 | 66c04a / 241f2a |
| Veloce GT | 2.02 | 2.98 | .55 | .66 | .46 | -.30 | 2.10 x 4.30 | 2f5fd0 / e8e2d4 |

- `truck` origin is the centre of gravity; `bodyG` sits at `V.bodyY` and is emptied and refilled by `SHELLS[id](V)` (lines 3276 to 3283). This is the swap point.
- Strut mounts at x = +/- track/2, y = -0.06, z = +wb*rb front and -wb*(1-rb) rear. The same numbers feed `corners[k].mount`.
- Per frame (`sync`, lines 4241 to 4256): shock and spring `scale.y = len`, shock `position.y = -len/2`, hub `position.y = -len` with steer on the fronts, `wheel.rotation.x` and `rim.rotation.x` spin.
- Wheel contact uses `WHEEL_R`, not the mesh. The old lugs reached 1.105R.
- Headlight spotlights sit at fixed offsets (+/-0.62, 0.22, 2.30) for every vehicle (lines 3289 to 3292).

## Desert, city and shield props

| Asset | Lines | Notes |
|---|---|---|
| Terrain | 1217 to 1360 | 560 m square, 5 m grid with jitter, per-face vertex colour, `surfW` blend weights |
| Ramps, mesa, whoops, spine, lakebed, rim | 960, 1073 to 1106 | Terrain only, in `baseH` |
| Sky | 1365 to 1414 | 5-stop gradient shader sphere, 420 stars |
| Peaks | 1434 to 1444 | 22 five-sided cones |
| Rocks, scrub | 1556 to 1588 | Instanced dodecahedra (220) and icosahedra (300), no collision |
| Circuit gates x12 | 1591 to 1626 | Trigger box \|x\|<4, \|z\|<3.4, \|y\|<6 in the gate frame |
| Landmarks x8 | 1744 to 1891 | Gas station (-138,-58), motel sign (96,142), drive in (-92,158), water tower (158,-92), wreck (-58,-168), camp (176,86), windmill (-172,52), stone ring (-40,120) |
| Billboards x6 | 1934 to 1988 | 11.5 x 5.8 panel at y 9.2, canvas faces |
| Stone stacks x3 | 3332 to 3357 | Added to `scene`, not `G_DESERT` |
| City buildings | 2052 to 2099, 2474 to 2568 | `BLD` record drives mesh and collider; windows come from the facade shader |
| Street lights | 2545 to 2567 | Lit head feeds the point light pool |
| Shield props | 2118 to 2464 | Spruce, birch, erratics, bridges, camps, docks and canoes, store, pickup, fire tower, hydro poles |

## Bugs and oddities found (not fixed, the original is untouched)

1. Shield props have no working collision: their `BLD` boxes are never tested because walls only run on the city map.
2. Stone stacks are added to `scene`, so a placed stack probably shows on the other maps (inferred from code).
3. `setMap(0)` does not clear `BLD`. Harmless only while walls are city-only.
4. `applyTime` sets the smooth `paint` emissive from `PAL.body` (2f7a86), not the selected car's paint (line 1529), so every shell except Marisol gets a teal glow.
5. The eight hidden landmark flags are registered as lit, so they compete for point light slots before they are found.
6. Shield windows glow but never cast light: `rebuildLightPts` does not walk `G_SHIELD`.
7. Only the tyre and rim spin; the lug bands, shoulder and disc stay still.
8. `flares()` and `archT()` are defined but never called; `buildCityBuildings` declares an unused `WALLS`.
