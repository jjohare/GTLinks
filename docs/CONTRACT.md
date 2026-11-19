# GTLinks — shared contract (v3, frozen)

Every agent codes against this file. If something here is wrong or missing, report it to the
coordinator instead of diverging; a silent deviation breaks the other two workstreams.

## 1. Game flow

1. **Lodge** — camera on the terrace of a summer ski lodge near the summit. Four cars are parked
   on a turntable; the player cycles them (arrows, click, swipe). A table holds 15 steins.
2. **Loading** — the player drags steins from the table and drops them on the selected car.
   `GO` unlocks at 10 steins; 15 is the maximum. Steins can be dragged back off before `GO`.
3. **Descent** — the car is driven down the mountain through 9 linked golf holes with ramps.
   Handling is governed by the stein count (section 5).
4. **Finale** — the run always ends with the car inverted and at rest (section 6).
   **The car is the drinker.** No driver is shown or implied. Steins are tipped onto the car,
   which has a character of its own: headlights act as eyes (they droop and cross as steins go
   on), it sways on its springs at the lodge, and it hiccups. The simulation emits `Hiccup`
   events, more often with more steins, each a small jolt to the body and the steering.
5. **Wreck cam** — wheels spin down, light damage shows, a drone camera orbits, pulls out, the
   screen fades to black, and the game returns to the lodge with a new seed.

## 2. World conventions

- Units: metres, seconds, kilograms, radians. Right-handed, **+Y up** (three.js native).
- The course descends along **+Z**. **+X is the car's left** when it faces downhill.
- Car body frame: **+Z forward, +Y up, +X left** (this is what a Blender glTF export produces
  for a car modelled facing Blender −Y). Body origin is on the ground plane, centred between
  the axles, at rest ride height.
- World extent: `x ∈ [-320, 320]`, `z ∈ [0, 2560]`. Summit and lodge at `z ≈ 40`. Total drop
  roughly 520 m. Outside the extent the terrain continues analytically (no hole in the world).
- Heightfield grid: cell size **4 m**, `NX = 161`, `NZ = 641`, row-major with
  `index = iz * NX + ix`, `x = -320 + 4*ix`, `z = 4*iz`. Each cell is split into two triangles
  along the diagonal from `(ix, iz)` to `(ix+1, iz+1)`. **Physics and rendering use the same
  triangulated grid**: the generator evaluates its analytic terrain only at grid nodes, and
  `height_at` interpolates linearly within those triangles, so wheels sit exactly on the drawn
  surface. Anything finer than the grid (ramps) is a prop with its own collision shape, added on
  top by `height_at`.
- Quaternions are `(x, y, z, w)`.

## 3. Cars

**`assets/cars.json` is the single source of truth** for the numbers below (plus wheel width,
ground clearance, centre-of-gravity height and paint colour). The simulation embeds it with
`include_str!`, the Blender scripts read it, and the web build copies it. Do not retype these
numbers anywhere. Models carry no badges, logos or script; the names appear only as UI text.

| id | key | UI name | L | W | H | wheelbase | track | wheel r | mass | character |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `escapade_2009` | Cadillax Escapade (2009) | 5.14 | 2.01 | 1.89 | 2.95 | 1.71 | 0.40 | 2600 | heavy, soft, rolls easily |
| 1 | `glug_2017` | Mercy-Bends GLUG (2017) | 5.13 | 1.93 | 1.85 | 3.08 | 1.66 | 0.39 | 2450 | big, composed, then not |
| 2 | `genesips_2021` | Genesips GV-Ale (2021) | 4.95 | 1.98 | 1.72 | 2.96 | 1.68 | 0.39 | 2250 | balanced |
| 3 | `rangeroller_2026` | Range Roller (2026) | 5.05 | 2.05 | 1.87 | 3.00 | 1.70 | 0.40 | 2500 | long travel, best off-fairway |

All four are large SUVs. The names are parodies: no real marque name, badge, logo or script
appears anywhere in the repository, the models or the UI. Each model is an original stylised
design with a generic silhouette of its class and era, not a replica of a production vehicle.

Wheel centres in the body frame: `x = ±track/2`, `y = wheel r`, `z = ±wheelbase/2`.
Wheel order everywhere: **FL, FR, RL, RR** (FL is +X, +Z).

### GLB layout (`web/public/assets/cars/<key>.glb`)

Named nodes, all parented to a root named `car`:

- `body` — shell, paint material named `paint` (the front end recolours it).
- `glass` — windows, material `glass`.
- `wheel_fl`, `wheel_fr`, `wheel_rl`, `wheel_rr` — origin at the wheel centre, axle along X.
- `headlight_l`, `headlight_r` — separate nodes with emissive material `headlight`, origin at
  the lamp centre (the front end animates them as eyes).
- Detachable, each its own node with origin at its hinge or mount: `bumper_front`,
  `bumper_rear`, `bonnet`, `mirror_l`, `mirror_r`.
- `roof_anchor` — an empty at the centre of the roof (steins stack here).
- No morph targets, no animations, no textures above 1024 px. Target 25k to 40k
  triangles per car, including a modelled underside (`underside` node: floor pan, exhaust,
  axles, differentials, sump, spare wheel well) and a simple interior (`interior` node: seats,
  dashboard, steering wheel) visible through the glass. Wheels have tyres with tread, spoked
  rims and brake discs. Materials are plain PBR factors (base colour, metallic, roughness) so they translate to
  node materials on both backends.

### Other models (`web/public/assets/props/`)

`stein.glb` (glass mug, material `lager` for the liquid, `foam` for the head, origin at base),
`lodge.glb` (timber chalet with terrace, chairlift pylon, origin at terrace centre, terrace
about 24 × 14 m), `table.glb`, `tree_pine.glb`, `tree_broadleaf.glb` (each under 300 triangles,
origin at trunk base), `spectator.glb` (under 250 triangles, material `shirt` recolourable, origin
at feet), `flag.glb` (pin with flag, origin at base), `tee_marker.glb`, `golf_cart.glb`,
`ramp.glb` (unit wedge: 1 m long in +Z, 1 m wide, 1 m high at the far end, scaled by the front
end), `drone.glb` (optional).

## 4. WASM API (`gtlinks-wasm`, consumed from `web/src/wasm/pkg`)

```ts
// static
function car_specs_json(): string;         // array of section-3 rows plus tuning the UI may show
function contract_version(): number;        // 3

class Game {
  constructor(seed: number, car_id: number, steins: number); // steins clamped to 10..=15
  course_json(): string;                    // see below; constant for a given seed
  heightfield(): Float32Array;              // NX*NZ heights, section 2 layout
  surface_map(): Uint8Array;                // NX*NZ surface ids, same layout
  height_at(x: number, z: number): number;  // analytic terrain incl. ramps
  step(dt: number, steer: number, throttle: number, brake: number, handbrake: boolean): void;
  state(): Float32Array;                    // STATE_LEN floats, layout below (copy, not a view)
  police_state(): Float32Array;             // POLICE_COUNT * POLICE_STRIDE floats, section 6b
  drain_events(): Float32Array;             // flat [kind, a, b, x, y, z] * n since last drain
}
```

`seed` is a `u32` (a `u64` would surface in JavaScript as a BigInt).

`step` takes raw player intent: `steer ∈ [-1, 1]` (+1 = left, towards +X), `throttle` and
`brake` in `[0, 1]`. The simulation applies the stein model itself. `dt` is wall-clock seconds;
the simulation accumulates it and runs fixed 1/120 s substeps (clamped to 0.1 s per call, which
also covers a backgrounded tab). `state()` returns the **render state, already interpolated**
between the last two substeps, so the front end never interpolates. Events carry no
interpolation and are emitted on the substep where they happen.

All transcendental maths in the simulation goes through the `libm` crate, so a native
`cargo test` run exercises the same arithmetic as the shipped wasm.

The steins are a count as far as the simulation is concerned. The front end shows them stacked
on the roof and throws them off as its own cosmetic effect on `Landing`, `Impact` and
`FinaleStart` events; that has no effect on handling.

Surface ids: `0 rough, 1 fairway, 2 green, 3 bunker, 4 tee, 5 cart path, 6 rock, 7 water`.

### `state()` layout (`STATE_LEN = 46`)

| index | field |
|---|---|
| 0–2 | position x, y, z (body origin) |
| 3–6 | orientation quaternion x, y, z, w |
| 7–9 | linear velocity |
| 10–12 | angular velocity (world) |
| 13–24 | per wheel FL, FR, RL, RR: suspension compression (m), spin angle (rad, accumulated), steer angle (rad) |
| 25 | phase: `0 Driving, 1 FinaleArmed, 2 FinaleAirborne, 3 Settling, 4 Wrecked` |
| 26 | damage, 0..1 |
| 27 | run time (s) |
| 28 | current hole index, 0..8 |
| 29 | speed along the body forward axis (m/s) |
| 30 | wheels on ground (0..4) |
| 31 | airtime of the current jump (s), 0 when grounded |
| 32 | applied steer after the stein model, −1..1 (for the HUD wheel) |
| 33 | wobble, 0..1 (drives screen sway) |
| 34 | trick score total |
| 35 | time since Wrecked began (s), 0 before |
| 36 | engine speed (rev/min) |
| 37 | gear: −1 reverse, 0 neutral, 1..8 |
| 38–41 | per wheel FL, FR, RL, RR: combined slip magnitude 0..1 (drives skid marks, smoke, tyre audio) |
| 42–45 | per wheel: surface id under the contact patch, −1 when airborne |

### Events (`kind`, then `a`, `b`, then world position)

`1 JumpStart(a = speed)`, `2 Landing(a = impact speed, b = airtime)`,
`3 Impact(a = impulse 0..1, b = surface or prop kind)`, `4 PropHit(a = prop index, b = prop kind)`,
`5 HoleEntered(a = hole index)`, `6 Trick(a = trick id, b = points)`,
`7 NearMiss(a = prop index)` (spectators always get out of the way; nobody is ever struck),
`8 FinaleStart`, `9 Wrecked`, `10 PartDetached(a = part id: 0 bumper_front, 1 bumper_rear,
2 bonnet, 3 mirror_l, 4 mirror_r)`, `11 Hiccup(a = strength 0..1)` (a small vertical and
steering jolt applied by the simulation; mean interval about 9 s at 10 steins, 3 s at 15; none
after the finale arms).

Trick ids: `0 airtime, 1 barrel roll, 2 front flip, 3 back flip, 4 flat spin, 5 bunker blast,
6 green skid`.

### `course_json()`

```jsonc
{
  "seed": 123,
  "start": { "pos": [x, y, z], "yaw": 0.0 },            // car spawn on the lodge apron
  "lodge": { "pos": [x, y, z], "yaw": 0.0 },
  "holes": [{
    "index": 0, "par": 4,
    "tee": [x, y, z], "green": [x, y, z], "green_radius": 14.0,
    "centreline": [[x, y, z], ...],                      // polyline, ~10 m spacing
    "fairway_half_width": 22.0
  }],
  "props": [{ "kind": 0, "pos": [x, y, z], "yaw": 0.0, "scale": 1.0 }],
  "ramps": [{ "pos": [x, y, z], "yaw": 0.0, "length": 9.0, "width": 6.0, "height": 2.2 }],
  "finale": { "pos": [x, y, z], "radius": 60.0 }         // arena after the 9th green
}
```

Prop kinds (v2 adds 8 onwards): `0 pine (solid), 1 broadleaf (solid), 2 spectator (dodges,
NearMiss), 3 flag (knocked, PropHit), 4 tee marker (knocked), 5 golf cart (solid, light,
shunted), 6 sign (knocked), 7 rock (solid), 8 grandstand (solid), 9 leaderboard (solid),
10 bench (knocked), 11 sprinkler (knocked, sprays), 12 yardage post (knocked), 13 out-of-bounds
stake (knocked), 14 ball washer (knocked), 15 halfway hut (solid), 16 golfer mid-swing (dodges),
17 golf bag (knocked, scatters clubs), 18 chairlift pylon (solid), 19 cow with bell (dodges),
20 bunker rake (knocked), 21 parasol (knocked), 22 larch (solid), 23 footbridge (drivable deck)`.
`holes[]` also carries `"dogleg": -1|0|1`, `"bunkers": [{"pos":[x,y,z],"radius":r}]`,
`"water": [{"pos":[x,y,z],"radius":r,"level":y}]` and `"cart_path": [[x,y,z], ...]`. Prop indices in events refer to the `props` array order.

## 5. Stein handling model

`s = (steins − 10) / 5`, so `s ∈ [0, 1]`. Ten steins is already impaired; fifteen is barely
controllable but never uncontrollable. The model changes the *link between input and car*, not
the physics of the car:

| effect | at 10 steins | at 15 steins |
|---|---|---|
| steering input lag (first-order time constant) | 0.12 s | 0.45 s |
| steering gain | 0.95 | 0.70 |
| overshoot (under-damped second-order response) | slight | pronounced |
| wander (slow random steering bias, never zero mean for long) | ±0.06 | ±0.28 |
| throttle and brake lag | 0.10 s | 0.35 s |
| stability assist (yaw damping the sober car would get) | 60 % | 10 % |
| added mass on the roof (raises the centre of gravity) | 10 × 1.3 kg | 15 × 1.3 kg |

## 6. The inverted-rest guarantee

Required outcome for every seed, car, stein count and input sequence, including no input at
all: the simulation reaches phase `4 Wrecked` with the body up-vector `y < -0.9`, linear speed
`< 0.1 m/s`, within **150 s** of run time, and stays there.

**Wrecked is a state, not the end of a sequence.** At any time, in any phase, if the car has
been inverted (`up.y < -0.9`) and slow (`< 0.1 m/s`) for 1 s, the phase becomes `4 Wrecked`. A
player who rolls it on the second hole has simply reached the ending early.

**Otherwise the finale is a scripted hand-off.** It arms when the car enters the finale arena,
or at 100 s of run time, or when the car has made no downhill progress for 12 s (stopped,
reversing, wedged against a tree, or off the course). From `1 FinaleArmed` the simulation
ignores player input and drives: the car "gets away" from the driver, accelerates along a line
the director has chosen to a launch point it can reach from where the car actually is (the
final ramp if in the arena, otherwise a kicker it raises under the car's path), and leaves the
ground. During `2 FinaleAirborne`, and only while airborne, a PD torque steers the roll so the
car arrives inverted. `3 Settling` is ordinary contact physics within a clamped roll tolerance,
with a last-resort righting torque towards inverted if the car is still not within tolerance
after 4 s. Wheel spin has its own slow decay once inverted (about 6 s), since nothing on the
ground is driving it.

The front end only reads the phase. On `1` it shows that control is lost; on `4` it cuts to the
drone camera.

## 6a. Fidelity (v2)

The operator has asked for a lot of technical detail and no corner-cutting. Where a simple
version and a thorough version are both possible, build the thorough one, provided it stays
deterministic, holds 60 fps on a mid-range GPU and works on the WebGL2 fallback.

- **Vehicle:** load-sensitive tyre model with combined slip (Pacejka-style curves per surface),
  longitudinal and lateral load transfer, anti-roll bars, bump stops, per-car spring and damper
  rates, an engine torque curve with an automatic gearbox and all-wheel drive with a centre
  split, aerodynamic drag and lift, gyroscopic and inertial behaviour in the air, per-surface
  rolling resistance and sinkage in sand, water drag in ponds.
- **Course:** real golf architecture: par 3, 4 and 5 holes with doglegs, tiered tee boxes,
  fairway bunkers and greenside bunkers with lips, contoured greens with fringe, water hazards,
  cart paths with a footbridge or two, first cut and deep rough, out-of-bounds lines, tree-lined
  corridors of mixed species, grandstands and a leaderboard at the last green, a halfway hut,
  chairlift pylons marching down from the lodge, cows on the high pasture.
- **Models:** enough geometry to hold up in the close drone orbit, including a modelled
  underside for each car (it spends the finale on its roof) and a simple interior.
- **Rendering:** physically based materials, cascaded sun shadows, atmospheric scattering and
  height fog, animated cloud shadows, wind in trees, flags and grass, near-field instanced grass,
  water with fresnel and ripples, tyre marks, sand and turf deformation trails, a
  post-processing chain (tone mapping, bloom, motion blur at speed, depth of field for the drone
  shots) built with TSL so it runs on both backends.

## 6b. Police pursuit (v3)

Three patrol cars (`POLICE_COUNT = 3`) chase the car as it loses control, then circle the wreck
before the camera pulls back. The simulation owns them, deterministically, like everything else.

`police_state()` returns `POLICE_COUNT * POLICE_STRIDE` floats (`POLICE_STRIDE = 16`),
interpolated like `state()`. Per unit:

| offset | field |
|---|---|
| 0–2 | position (body origin, on the terrain) |
| 3–6 | orientation quaternion x, y, z, w |
| 7 | speed (m/s) |
| 8 | steer angle of the front wheels (rad) |
| 9 | wheel spin angle (rad, accumulated) |
| 10 | mode: `0 Absent, 1 Pursuing, 2 Circling, 3 Parked` |
| 11 | lights and siren on (0 or 1) |
| 12 | body roll (rad, cosmetic lean in corners) |
| 13 | distance to the player car (m) |
| 14–15 | reserved, 0 |

Behaviour:

- **Joining.** Unit 0 joins at about 20 s of run time or when the car reaches the third hole,
  whichever is first; units 1 and 2 join over the following holes. All three are in pursuit no
  later than the moment the finale arms. A unit enters from out of the player's view (behind,
  or from a cart path or side track), emitting `12 PoliceJoined(a = unit)`.
- **Pursuing.** Units follow the trail the car has actually driven, fanned out in a loose
  formation 15 to 40 m behind, matching its speed, taking ramps and catching air. They stay on
  the terrain, steer around solid props, and close up when the finale arms. They **never touch
  the player's car and never touch a spectator, golfer or cow**: this is a chase for show.
- **Circling.** On `Wrecked` (including an early rollover, in which case absent units join at
  once and drive in from out of view) the units arrive and circle the wreck nose to tail at a
  radius of about 14 m, lights on, for at least one and a half laps each; `13 PoliceCircling`
  fires when the first unit starts its lap.
- **Parked.** Each unit then stops on the ring facing the wreck, lights still flashing;
  `14 PoliceParked` fires when the last one has stopped. This happens within 14 s of `Wrecked`
  in every run.

Front-end timeline after `Wrecked`: drone orbit throughout; the pull-out begins only after
`14 PoliceParked` (or 16 s, whichever is first), then fade to black and restart.

Model: `web/public/assets/cars/patrol.glb`, an original generic patrol SUV in a made-up livery
(high-visibility blocks and chevrons, no text, crest or real force markings), with the car node
conventions plus `lightbar` and separate emissive `beacon_l` (blue) and `beacon_r` (red or
blue) nodes. Dimensions in `assets/cars.json` under `"patrol"`.

## 7. Front end

- three.js r187, `three/webgpu` `WebGPURenderer` with its built-in WebGL2 fallback; node
  materials and TSL only, no `ShaderMaterial`, no `onBeforeCompile`. A `?renderer=webgl` query
  parameter forces the fallback (`forceWebGL: true`). The HUD shows which backend is active.
- Static site: Vite `base: './'`, every asset by relative URL, no server calls, no analytics.
- Keyboard (WASD or arrows, space handbrake, R restart), gamepad, and touch (on-screen stick
  and pedals). Drag and drop uses pointer events, so it works with mouse and touch.
- Exposes `window.__gtlinks = { phase, backend, state(), debugStart(carId, steins, seed) }` for
  automated checks.

## 8. Repository layout

```
crates/gtlinks-sim/     pure Rust simulation, no wasm dependencies, property tests
crates/gtlinks-wasm/    wasm-bindgen wrapper only
web/                    Vite + TypeScript front end; public/assets holds the GLBs
assets/src/             Blender build scripts (Python, kept because bpy is Python-only)
docs/                   this contract, evidence
.github/workflows/      Pages deployment
```
