//! Deterministic simulation core for GTLinks.
//!
//! A car carrying 10 to 15 steins of lager descends a procedurally generated mountainside of
//! nine linked golf holes, and every run ends with the car upside down and at rest. The car is
//! the drinker: the stein count changes how it answers the player's intent, never the tyre
//! physics. This crate holds the whole game state; the browser only draws it.
//!
//! - [`Course`] generates the terrain grid, surfaces, holes, props and ramps from a seed.
//! - [`Sim`] runs the vehicle at a fixed 1/120 s step, applies the stein model, emits
//!   [`Event`]s, and directs the finale so the inverted-rest guarantee always holds.
//! - [`Driver`] is a scripted stand-in for the player (input policies for tests and the
//!   `run_summary` example). Nobody sits in the car; the name refers to the remote player.
//!
//! Arithmetic is `f32` throughout and every transcendental function goes through `libm`, so a
//! native test run and the shipped WebAssembly produce bit-identical state for the same seed
//! and inputs.
//!
//! # Examples
//!
//! ```
//! use gtlinks_sim::{Input, Phase, Sim};
//!
//! let mut sim = Sim::new(7, 2, 12);
//! let input = Input { throttle: 1.0, ..Input::default() };
//! for _ in 0..120 {
//!     sim.step(1.0 / 60.0, input);
//! }
//! assert_eq!(sim.phase(), Phase::Driving);
//! let state = sim.state();
//! assert_eq!(state.len(), gtlinks_sim::STATE_LEN);
//! ```

mod cars;
mod course;
mod driver;
mod math;
mod rng;
mod sim;
mod steins;
mod terrain;
mod vehicle;

pub use cars::{CarSpec, CarTuning, car_spec, car_specs, car_specs_json, car_tuning};
pub use course::{Course, Finale, Hole, Interaction, Pose, Prop, PropKind, surface};
pub use driver::{Driver, Policy};
pub use sim::{
    ArmReason, Event, EventKind, Fallbacks, Input, LaunchKind, Phase, RunStats, Sim, flatten_events,
};
pub use steins::{AppliedControls, MAX_STEINS, MIN_STEINS, STEIN_MASS, SteinFilter, SteinParams};
pub use terrain::Ramp;

/// Contract version reported to the front end.
pub const CONTRACT_VERSION: u32 = 1;
/// Heightfield columns (x).
pub const NX: usize = 161;
/// Heightfield rows (z).
pub const NZ: usize = 641;
/// Heightfield cell size, m.
pub const CELL: f32 = 4.0;
/// World x of grid column 0.
pub const X_MIN: f32 = -320.0;
/// World z of the last grid row.
pub const Z_MAX: f32 = 2560.0;
/// Fixed simulation step, s.
pub const DT: f32 = 1.0 / 120.0;
/// Largest wall-clock `dt` accepted by one [`Sim::step`] call, s.
pub const MAX_FRAME_DT: f32 = 0.1;
/// Floats in the render state returned by [`Sim::state`].
pub const STATE_LEN: usize = 36;
