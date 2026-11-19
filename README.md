# GTLinks

A slapstick downhill driving game for the browser. Pick a large SUV at a summer ski lodge, tip
ten to fifteen steins of lager over it, and try to steer it down a mountainside that happens to
be nine linked golf holes. The car is the one drinking, and it shows. However the run goes, it
finishes the same way: on its roof, wheels spinning, with a drone circling overhead.

**Play:** https://jjohare.github.io/GTLinks/

Renders with WebGPU where the browser has it and falls back to WebGL2 where it does not. Add
`?renderer=webgl` to the address to force the fallback.

## Controls

| | Keyboard | Gamepad | Touch |
|---|---|---|---|
| Steer | A / D or ← / → | left stick | on-screen stick |
| Accelerate, brake | W / S or ↑ / ↓ | triggers | pedals |
| Handbrake | Space | A | — |
| Restart | R | Start | — |

At the lodge, choose a car, then drag steins from the table onto it. Ten unlocks the run;
fifteen is the limit. More steins mean slower, sloppier steering.

## How it is built

```
crates/gtlinks-sim     Rust. Course generation, vehicle dynamics, the stein handling model and
                       the finale director. Deterministic, fixed 120 Hz step, no browser code.
crates/gtlinks-wasm    wasm-bindgen wrapper around the simulation.
web/                   TypeScript and three.js (WebGPURenderer, TSL materials). View only: it
                       draws what the simulation reports and passes it the player's input.
assets/src/            Blender Python scripts that generate every model procedurally.
assets/cars.json       Car dimensions, shared by the simulation, the models and the UI.
docs/CONTRACT.md       The interface between the three parts.
```

The simulation is separate from the renderer so that "every run ends upside down" can be
tested rather than hoped for. A property suite drives hundreds of seeds, every car, every stein
count and a range of input policies (including none at all) and requires each run to end
inverted and at rest.

## Build

Requires Rust with the `wasm32-unknown-unknown` target, `wasm-pack`, and Node 22.

```sh
cargo test --release -p gtlinks-sim   # simulation tests, including the property suite
./scripts/build-wasm.sh               # builds the wasm package into web/src/wasm/pkg
cd web && npm ci && npm run dev       # local development server
cd web && npm run build               # static site in web/dist
```

Pushing to `main` builds and deploys to GitHub Pages.

## Notes

The cars are original stylised designs with parody names. No real manufacturer's name, badge or
design is used, and none is affiliated with or endorses this project. Spectators always get out
of the way. Cars cannot drink; people who have should not drive.

Licensed under the [MIT Licence](LICENSE).
