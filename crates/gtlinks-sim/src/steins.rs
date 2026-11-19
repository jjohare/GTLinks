//! The stein handling model: how the lager changes the link between intent and car.
//!
//! Everything here acts on the input signal path (plus the roof mass, which the vehicle
//! reads). Tyre physics never sees the stein count. Parameters follow the contract's
//! table, interpolated linearly on `s = (steins - 10) / 5`.

use crate::math::{exp, lerp, sin};
use crate::rng::Rng;

/// Fewest steins a run can carry.
pub const MIN_STEINS: u32 = 10;
/// Most steins a run can carry.
pub const MAX_STEINS: u32 = 15;
/// Rise-time factor of the discretised second-order step response: the time to reach 63 % of
/// the final value is about `(RISE_A + RISE_B * zeta) / omega` (fitted at 120 Hz).
const RISE_A: f32 = 1.11;
/// See [`RISE_A`].
const RISE_B: f32 = 0.89;
/// Mass of one full stein on the roof, kg.
pub const STEIN_MASS: f32 = 1.3;

/// Handling parameters derived from the stein count.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct SteinParams {
    /// Number of steins, clamped to 10..=15.
    pub steins: u32,
    /// Impairment `s = (steins - 10) / 5`, 0..=1.
    pub s: f32,
    /// Steering lag time constant, s (0.12 to 0.45): the 63 % rise time of the steering
    /// response.
    pub steer_lag: f32,
    /// Steering gain (0.95 to 0.70).
    pub steer_gain: f32,
    /// Damping ratio of the steering response: 0.8 (about 1.5 % overshoot) to 0.3 (about 37 %).
    pub steer_zeta: f32,
    /// Natural frequency of the steering response, rad/s, set so the 63 % rise time equals
    /// `steer_lag`.
    pub steer_omega: f32,
    /// Wander amplitude, fraction of full lock (0.06 to 0.28).
    pub wander: f32,
    /// Throttle and brake lag time constant, s (0.10 to 0.35).
    pub pedal_lag: f32,
    /// Fraction of the sober car's yaw damping still available (0.6 to 0.1).
    pub assist: f32,
    /// Added roof mass, kg.
    pub roof_mass: f32,
    /// Mean interval between hiccups, s (about 9 at 10 steins, 3 at 15).
    pub hiccup_interval: f32,
}

impl SteinParams {
    /// Parameters for a stein count (clamped to 10..=15).
    pub fn new(steins: u32) -> Self {
        let steins = steins.clamp(MIN_STEINS, MAX_STEINS);
        let s = (steins - MIN_STEINS) as f32 / (MAX_STEINS - MIN_STEINS) as f32;
        Self {
            steins,
            s,
            steer_lag: lerp(0.12, 0.45, s),
            steer_gain: lerp(0.95, 0.70, s),
            steer_zeta: lerp(0.80, 0.30, s),
            steer_omega: (RISE_A + RISE_B * lerp(0.80, 0.30, s)) / lerp(0.12, 0.45, s),
            wander: lerp(0.06, 0.28, s),
            pedal_lag: lerp(0.10, 0.35, s),
            assist: lerp(0.60, 0.10, s),
            roof_mass: steins as f32 * STEIN_MASS,
            hiccup_interval: lerp(9.0, 3.0, s),
        }
    }
}

/// Controls after the stein model.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct AppliedControls {
    /// Steering, -1..1 (+1 = left).
    pub steer: f32,
    /// Throttle, 0..1.
    pub throttle: f32,
    /// Brake, 0..1.
    pub brake: f32,
}

/// The stateful input filter for one run.
#[derive(Clone, Debug)]
pub struct SteinFilter {
    params: SteinParams,
    y: f32,
    ydot: f32,
    throttle: f32,
    brake: f32,
    time: f32,
    freqs: [f32; 3],
    phases: [f32; 3],
    jolt: f32,
}

/// Relative weights of the three wander components; they sum to 1 so |wander| <= amplitude.
const WANDER_WEIGHTS: [f32; 3] = [0.5, 0.3, 0.2];

impl SteinFilter {
    /// A filter for `params`, with wander phases drawn from `seed`.
    ///
    /// The wander shape depends only on the seed; its amplitude scales with the stein
    /// count, so for one seed more steins always means more wander.
    pub fn new(params: SteinParams, seed: u32) -> Self {
        let mut rng = Rng::new(u64::from(seed), 0x0057_E14A);
        let freqs = [
            rng.range(0.05, 0.08),
            rng.range(0.11, 0.17),
            rng.range(0.23, 0.31),
        ];
        let tau = std::f32::consts::TAU;
        let phases = [
            rng.range(0.0, tau),
            rng.range(0.0, tau),
            rng.range(0.0, tau),
        ];
        Self {
            params,
            y: 0.0,
            ydot: 0.0,
            throttle: 0.0,
            brake: 0.0,
            time: 0.0,
            freqs,
            phases,
            jolt: 0.0,
        }
    }

    /// The parameters in use.
    pub fn params(&self) -> &SteinParams {
        &self.params
    }

    /// Current wander bias (signed fraction of full lock).
    pub fn wander(&self) -> f32 {
        let tau = std::f32::consts::TAU;
        let w: f32 = WANDER_WEIGHTS
            .iter()
            .zip(self.freqs.iter().zip(&self.phases))
            .map(|(wt, (f, ph))| wt * sin(tau * f * self.time + ph))
            .sum();
        w * self.params.wander
    }

    /// Adds a decaying steering jolt (a hiccup).
    pub fn jolt(&mut self, amount: f32) {
        self.jolt += amount;
    }

    /// Current hiccup jolt still decaying.
    pub fn jolt_level(&self) -> f32 {
        self.jolt
    }

    /// Advances the filter by `dt` with raw intent and returns the applied controls.
    pub fn update(&mut self, dt: f32, steer: f32, throttle: f32, brake: f32) -> AppliedControls {
        let p = &self.params;
        self.time += dt;
        let target = steer.clamp(-1.0, 1.0) * p.steer_gain;
        // One under-damped second-order response carries both the lag (its rise time) and the
        // overshoot (its damping ratio). Semi-implicit Euler is stable here at 120 Hz.
        let w = p.steer_omega;
        let acc = w * w * (target - self.y) - 2.0 * p.steer_zeta * w * self.ydot;
        self.ydot += acc * dt;
        self.y += self.ydot * dt;
        self.jolt *= exp(-dt / 0.15);
        let ap = 1.0 - exp(-dt / p.pedal_lag);
        self.throttle += (throttle.clamp(0.0, 1.0) - self.throttle) * ap;
        self.brake += (brake.clamp(0.0, 1.0) - self.brake) * ap;
        AppliedControls {
            // The wander is a bias on top of the response, so it never exceeds its amplitude.
            steer: (self.y + self.wander() + self.jolt).clamp(-1.0, 1.0),
            throttle: self.throttle,
            brake: self.brake,
        }
    }
}
