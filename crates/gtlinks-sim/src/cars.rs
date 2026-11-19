//! Car dimensions from the embedded `assets/cars.json`, plus simulation tuning.
//!
//! The JSON file is the single source of truth for every dimension and mass. The tuning
//! values here (spring rate, travel, power) belong to the simulation and are keyed by car id.

use std::sync::OnceLock;

use serde::{Deserialize, Serialize};

/// The embedded car table, shared verbatim with the Blender scripts and the web build.
const CARS_JSON: &str = include_str!("../../../assets/cars.json");

/// One row of `assets/cars.json`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct CarSpec {
    /// Car id, 0 to 3.
    pub id: u32,
    /// Asset key (GLB file stem).
    pub key: String,
    /// Display name for the UI.
    pub name: String,
    /// Body length, m.
    pub length: f32,
    /// Body width, m.
    pub width: f32,
    /// Body height, m.
    pub height: f32,
    /// Axle separation, m.
    pub wheelbase: f32,
    /// Wheel centre separation across the car, m.
    pub track: f32,
    /// Wheel radius, m.
    pub wheel_radius: f32,
    /// Tyre width, m.
    pub wheel_width: f32,
    /// Underbody clearance at rest, m.
    pub ground_clearance: f32,
    /// Kerb mass, kg.
    pub mass: f32,
    /// Centre-of-gravity height above the ground at rest, m.
    pub cog_height: f32,
    /// Roof height above the ground at rest, m.
    pub roof_y: f32,
    /// Paint colour as a CSS hex string.
    pub paint: String,
    /// One-line description for the UI.
    pub character: String,
}

#[derive(Deserialize)]
struct CarsFile {
    cars: Vec<CarSpec>,
}

/// Simulation tuning for one car, not part of `cars.json`.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct CarTuning {
    /// Suspension natural frequency, Hz.
    pub ride_hz: f32,
    /// Suspension damping ratio.
    pub damping_ratio: f32,
    /// Maximum suspension compression, m.
    pub travel: f32,
    /// Peak engine power, W per kg of kerb mass.
    pub power_per_kg: f32,
    /// Electronically limited top speed, m/s.
    pub top_speed: f32,
    /// Peak tyre friction multiplier.
    pub grip: f32,
    /// Height of lateral tyre forces as a fraction from CoG (0) to contact patch (1);
    /// higher values roll the body more readily.
    pub roll_lever: f32,
}

/// Every car row from the embedded JSON, parsed once.
///
/// # Panics
///
/// Panics if the embedded `assets/cars.json` does not parse; it is checked by the test suite.
pub fn car_specs() -> &'static [CarSpec] {
    static SPECS: OnceLock<Vec<CarSpec>> = OnceLock::new();
    SPECS.get_or_init(|| {
        let file: CarsFile = serde_json::from_str(CARS_JSON)
            .expect("assets/cars.json embedded at build time parses");
        file.cars
    })
}

/// The spec for `car_id`, clamped to the available cars.
pub fn car_spec(car_id: u32) -> &'static CarSpec {
    let specs = car_specs();
    let i = usize::try_from(car_id).unwrap_or(0).min(specs.len() - 1);
    &specs[i]
}

/// Simulation tuning for `car_id`.
pub fn car_tuning(car_id: u32) -> CarTuning {
    match car_id {
        // Heavy, soft and tall: rolls easily.
        0 => CarTuning {
            ride_hz: 1.20,
            damping_ratio: 0.32,
            travel: 0.28,
            power_per_kg: 92.0,
            top_speed: 46.0,
            grip: 0.97,
            roll_lever: 0.8,
        },
        // Big and composed.
        1 => CarTuning {
            ride_hz: 1.45,
            damping_ratio: 0.42,
            travel: 0.26,
            power_per_kg: 98.0,
            top_speed: 47.0,
            grip: 1.02,
            roll_lever: 0.6,
        },
        // Balanced.
        2 => CarTuning {
            ride_hz: 1.40,
            damping_ratio: 0.40,
            travel: 0.26,
            power_per_kg: 100.0,
            top_speed: 47.0,
            grip: 1.0,
            roll_lever: 0.62,
        },
        // Long travel, happiest off the fairway.
        _ => CarTuning {
            ride_hz: 1.25,
            damping_ratio: 0.38,
            travel: 0.36,
            power_per_kg: 95.0,
            top_speed: 46.0,
            grip: 1.0,
            roll_lever: 0.66,
        },
    }
}

#[derive(Serialize)]
struct SpecWithTuning<'a> {
    #[serde(flatten)]
    spec: &'a CarSpec,
    tuning: CarTuning,
}

/// JSON array of every car row plus the tuning the UI may display.
pub fn car_specs_json() -> String {
    let rows: Vec<SpecWithTuning<'_>> = car_specs()
        .iter()
        .map(|spec| SpecWithTuning {
            spec,
            tuning: car_tuning(spec.id),
        })
        .collect();
    serde_json::to_string(&rows).unwrap_or_else(|_| String::from("[]"))
}
