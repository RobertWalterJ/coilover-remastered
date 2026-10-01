# Coilover remastered assets

This folder is a companion to `Documents\Coilover`. Nothing in the original game was changed. Everything here is new: Blender models, terrain maps and textures, plus the Python generators that made them. Start a Claude Code session in this folder or in the game folder and point it at this file.

## What is in here

| Folder | Contents |
|---|---|
| `assets/vehicles/` | `<id>_body.glb` for bracken, marisol, kestrel, serrano and veloce. `<id>_wheels.glb` holds four nodes per vehicle: `wheel`, `rim`, `disc`, `caliper`. `strut.glb` holds `spring`, `shock`, `capT`, `capB`, `arm`, `link`. |
| `assets/props/desert/` | The eight landmarks (gas station, motel sign, drive in, water tower, aircraft wreck, camp, windmill, stone ring), circuit gate, billboard, stone stack, 4 rocks, 3 scrub, 2 peaks. |
| `assets/props/city/` | Six buildings matching the game's parcel sizes, and the street light. |
| `assets/props/shield/` | 3 spruce, 2 birch, 3 erratics, cottage, outhouse, dock, canoe, general store, derelict pickup, fire tower, hydro pole, bridge bay. |
| `assets/terrain/<map>/` | `height_1m.png` (16 bit), `colour_1m.png`, `surf_1m.png`, `terrain.json`, and `terrain_<map>_5m.glb`. Maps: desert (Ochre Basin), city (Vantage Hill), shield (Pike Narrows). |
| `assets/textures/` | Tileable ground sets at 512 px (albedo, OpenGL normal, ORH = AO/rough/height, 16 bit height), plus `grain/<name>_128.png` greyscale grain in the format the game's `tex` slots already use. |
| `assets/manifest.json` | Every model: file, node names, triangle count, size, every material with its hex colour, and the emissive colour for each lit part. |
| `sheets/` | Contact sheets and map previews (JPG). |
| `generators/` | The Blender and numpy scripts. Re-run them to change anything (see the end of this file). |
| `AUDIT.md` | The asset audit of the original game, with line numbers, and the bugs found along the way. |

## Conventions

- Metres. glTF is +Y up. Props face +Z in game space (Blender -Y). Origins are at the base centre, on the ground.
- Vehicle bodies are authored in the game's `bodyG` frame: +Y up, +Z forward, +X is the vehicle's left. That is the same frame the shell functions draw into, so a loaded body lines up with the struts with no offsets.
- Material names match the game's variables: `paint`, `second`, `trim`, `flare`, `carbon`, `disc`, `caliper`, `shoulder`, `tyre`, `lug`, `rim`, `chrome`, `spring`, `glass`, `canvas`, `accent`, `rubber`. Lit parts are named `glow_*` and the manifest carries their emissive colour.
- The look is the game's: flat shaded, chamfered hard edges, smooth shading only on the lofted car panels (the game does the same).

## Integrating into the game (for Claude Code)

The game is one HTML file on three.js r128 with no model loader, and it must stay offline-capable. Suggested order:

1. **Loader.** Vendor `examples/js/loaders/GLTFLoader.js` from three r128 into `app/vendor/` (and `docs/` through `build.py`), add it to `sw.js` so it caches, and load GLBs with `fetch` plus `loader.parse`. Alternatively embed each GLB as base64 in the HTML to keep the single file.
2. **Materials.** glTF arrives as `MeshStandardMaterial`, and `styleMat()` patches the Phong shader, so convert every material on load: `new THREE.MeshPhongMaterial({color: sc(hex), specular: 0, shininess: 0, flatShading: true})`, then `styleMat(m, {obj: true, tex: ...})` for anything that moves. Keep `flatShading: false` for the `paint` material on lofted bodies.
3. **Glow.** For each `glow_*` material, register the converted material in `LGLOW` (props) or `GLOW` (vehicles) with the manifest's emissive colour. Matching is by material identity, so reuse one material instance per glow type.
4. **Vehicles.** In `__setVehicle`, empty `bodyG` and add the loaded body instead of calling `SHELLS[id](V)`. Replace the wheel meshes in each corner's `hubg` with the `wheel`, `rim` and `disc` nodes, and spin all three (today only the tyre and rim spin; the lug bands and disc do not, which is a small existing bug). Use `caliper` in place of the current caliper box. Swap `springGeo` and the shock for the `strut.glb` nodes; they keep the 1.0 m length and origins the code scales.
5. **Wheel size.** The new tread's outer radius is `wheelR * 1.06`, down from the old lugs at `1.105R`, so the drawn tyre is closer to the physics tyre. No physics change is needed.
6. **Props.** Replace the box builds in `place()` (landmarks), the gates, billboards, stone stacks, `buildCityProps`, and `buildShieldProps` with loaded models at the same positions. City buildings: keep the `BLD` record for collision and pick the closest model by `w` and `h`, scaling Y to the record's height. The windmill rotor is its own node; keep spinning it about Z.
7. **Painted faces.** The billboard panel, drive in screen and general store sign carry a 0 to 1 UV on their front face only, so the existing canvas textures drop straight on. The aircraft fuselage has a cylindrical UV for the livery strip.
8. **Terrain.** Physics should keep reading the analytic `height()` functions. The terrain files here were sampled from a numpy port of those same functions, so they agree with what the truck feels. Easiest win: use `colour_1m.png` as a lookup in place of the per-face colour rules, and `surf_1m.png` for the playa/rock/road texture blend. The 5 m GLBs are there for previews and other tools.
9. **Textures.** `grain/*_128.png` are drop-in replacements or additions for the game's `PHOTO_SAND`, `PHOTO_ROCK` and `PHOTO_PLAYA` style grain slots (greyscale, high passed, mean 0.5). New ones: gravel_track (fixed: it read as wet tar before), asphalt, muskeg, granite.

Constraints to respect (from `REQUIREMENTS.md`): no em dashes in any UI text, no timers or countdowns, invented names only with no badges or real trade dress, minimal HUD.

## Regenerating

Blender 4.2 headless, run from `generators/`:

```
blender -b --python export_coilover.py          # every vehicle and prop GLB plus manifest.json
python3 cv_terrain.py                           # height, colour and surf maps for all three maps
MAP=desert blender -b --python cv_terrain_blend.py   # terrain GLB and a dressed preview render
python3 texgen.py 512 desert_ripples cracked_earth gravel_track asphalt muskeg rock_granite rock_strata
```

`cv_vehicles.py` holds the five shells (ported from the game's shell functions, then remastered), the wheel set and the strut. `cv_props.py` holds everything else, with a `registry()` listing every asset. Vehicle colours, sizes and wheel data are in `VEH` at the top of `cv_vehicles.py` and come from the game's `VEHICLES` table.
