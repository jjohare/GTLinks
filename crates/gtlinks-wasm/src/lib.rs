//! wasm-bindgen wrapper exposing the GTLinks simulation to the browser.
//!
//! This crate is the contract's section 4 API and nothing else: every method forwards to
//! [`gtlinks_sim::Sim`]. Arrays are returned as copies (`Float32Array` / `Uint8Array`).

use gtlinks_sim::{CONTRACT_VERSION, Input, MAX_STEINS, MIN_STEINS, Sim, flatten_events};
use wasm_bindgen::prelude::wasm_bindgen;

/// JSON array of the car table rows plus the tuning the UI may show.
#[wasm_bindgen]
pub fn car_specs_json() -> String {
    gtlinks_sim::car_specs_json()
}

/// The contract version this build implements.
#[wasm_bindgen]
pub fn contract_version() -> u32 {
    CONTRACT_VERSION
}

/// One run of the game.
#[wasm_bindgen]
#[derive(Debug)]
pub struct Game {
    sim: Sim,
}

#[wasm_bindgen]
impl Game {
    /// Generates the course for `seed` and places the car; `steins` is clamped to 10..=15.
    #[wasm_bindgen(constructor)]
    pub fn new(seed: u32, car_id: u32, steins: u32) -> Game {
        Game {
            sim: Sim::new(seed, car_id, steins.clamp(MIN_STEINS, MAX_STEINS)),
        }
    }

    /// The course document; constant for a given seed.
    pub fn course_json(&self) -> String {
        self.sim.course().to_json()
    }

    /// Node heights, `NX * NZ`, row-major `iz * NX + ix`.
    pub fn heightfield(&self) -> Vec<f32> {
        self.sim.course().heightfield().to_vec()
    }

    /// Node surface ids, same layout as `heightfield`.
    pub fn surface_map(&self) -> Vec<u8> {
        self.sim.course().surface_map().to_vec()
    }

    /// Terrain height including ramps (and the finale kicker once raised).
    pub fn height_at(&self, x: f32, z: f32) -> f32 {
        self.sim.height_at(x, z)
    }

    /// Advances by wall-clock `dt` seconds with the player's raw intent.
    pub fn step(&mut self, dt: f32, steer: f32, throttle: f32, brake: f32, handbrake: bool) {
        self.sim.step(
            dt,
            Input {
                steer,
                throttle,
                brake,
                handbrake,
            },
        );
    }

    /// The interpolated render state (`STATE_LEN` floats).
    pub fn state(&self) -> Vec<f32> {
        self.sim.state().to_vec()
    }

    /// Events since the last drain, flat `[kind, a, b, x, y, z] * n`.
    pub fn drain_events(&mut self) -> Vec<f32> {
        flatten_events(&self.sim.drain_events())
    }
}
