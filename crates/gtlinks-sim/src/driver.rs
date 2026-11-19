//! Scripted input policies for tests and the `run_summary` example.
//!
//! These stand in for a player. They produce raw intent only; the stein model still sits
//! between them and the car.

use crate::math::{Vec3, atan2, sqrt};
use crate::rng::Rng;
use crate::sim::{Input, Sim};

/// An input policy.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Policy {
    /// Never touches anything.
    NoInput,
    /// Full throttle, wheel straight.
    FullThrottle,
    /// Full throttle with a random steering target changed every 0.5 to 2 s.
    ThrottleRandomSteer,
    /// Brake and handbrake held throughout (stays put).
    BrakeHeld,
    /// Brake held without the handbrake, which engages reverse once stopped.
    ReverseHeld,
    /// Follows the course centreline at a curvature-limited speed.
    FollowCentreline,
    /// Full throttle with hard left and right lock alternating every 1.5 s.
    Alternating,
}

impl Policy {
    /// Every policy, in a stable order.
    pub const ALL: [Policy; 7] = [
        Policy::NoInput,
        Policy::FullThrottle,
        Policy::ThrottleRandomSteer,
        Policy::BrakeHeld,
        Policy::ReverseHeld,
        Policy::FollowCentreline,
        Policy::Alternating,
    ];

    /// Short name for reports.
    pub fn name(self) -> &'static str {
        match self {
            Policy::NoInput => "none",
            Policy::FullThrottle => "throttle",
            Policy::ThrottleRandomSteer => "random-steer",
            Policy::BrakeHeld => "brake",
            Policy::ReverseHeld => "reverse",
            Policy::FollowCentreline => "centreline",
            Policy::Alternating => "alternating",
        }
    }

    /// Parses a name produced by [`Policy::name`].
    pub fn from_name(name: &str) -> Option<Policy> {
        Policy::ALL.into_iter().find(|p| p.name() == name)
    }
}

/// A scripted stand-in for the player, for one run.
#[derive(Clone, Debug)]
pub struct Driver {
    policy: Policy,
    rng: Rng,
    time: f32,
    steer: f32,
    next_change: f32,
}

impl Driver {
    /// A stand-in player following `policy`; `seed` feeds the random-steering policy.
    pub fn new(policy: Policy, seed: u32) -> Self {
        Self {
            policy,
            rng: Rng::new(u64::from(seed), 0xD21_7E5),
            time: 0.0,
            steer: 0.0,
            next_change: 0.0,
        }
    }

    /// The policy being driven.
    pub fn policy(&self) -> Policy {
        self.policy
    }

    /// Intent for the next `dt` seconds given the current run.
    pub fn input(&mut self, sim: &Sim, dt: f32) -> Input {
        self.time += dt;
        match self.policy {
            Policy::NoInput => Input::default(),
            Policy::FullThrottle => Input {
                throttle: 1.0,
                ..Input::default()
            },
            Policy::ThrottleRandomSteer => {
                if self.time >= self.next_change {
                    self.steer = self.rng.range(-1.0, 1.0);
                    self.next_change = self.time + self.rng.range(0.5, 2.0);
                }
                Input {
                    steer: self.steer,
                    throttle: 1.0,
                    ..Input::default()
                }
            }
            Policy::BrakeHeld => Input {
                brake: 1.0,
                handbrake: true,
                ..Input::default()
            },
            Policy::ReverseHeld => Input {
                brake: 1.0,
                ..Input::default()
            },
            Policy::FollowCentreline => follow(sim),
            Policy::Alternating => {
                let phase = (self.time / 1.5) as u32;
                Input {
                    steer: if phase.is_multiple_of(2) { 1.0 } else { -1.0 },
                    throttle: 1.0,
                    ..Input::default()
                }
            }
        }
    }
}

/// Pure-pursuit centreline follower with a curvature speed limit.
fn follow(sim: &Sim) -> Input {
    let course = sim.course();
    let p = sim.position();
    let f = sim.forward();
    let v = sim.velocity();
    let speed = sqrt(v[0] * v[0] + v[2] * v[2]);
    let look = 9.0 + 0.55 * speed;
    let tz = p[2] + look;
    let target = Vec3::new(course.path_x(tz), 0.0, tz);
    let want = Vec3::new(target.x - p[0], 0.0, target.z - p[2]).normalize_or(Vec3::Z);
    let fw = Vec3::new(f[0], 0.0, f[2]).normalize_or(Vec3::Z);
    let cross = fw.z * want.x - fw.x * want.z;
    let ang = atan2(cross, fw.dot(want));
    let steer = (2.4 * ang).clamp(-1.0, 1.0);
    // A sensible player lets go in the air rather than tumbling the car.
    if sim.state()[30] == 0.0 {
        return Input {
            throttle: 0.3,
            ..Input::default()
        };
    }

    // Speed limit from the tightest curvature in the next 90 m.
    let mut kmax = 1e-4f32;
    let mut z = p[2];
    while z < p[2] + 90.0 {
        let a = course.path_x(z - 6.0);
        let b = course.path_x(z);
        let c = course.path_x(z + 6.0);
        kmax = kmax.max(((a + c - 2.0 * b) / 36.0).abs());
        z += 6.0;
    }
    let vmax = sqrt(6.0 / kmax).min(36.0);
    let (throttle, brake) = if speed < vmax - 1.0 {
        (1.0, 0.0)
    } else if speed > vmax + 3.0 {
        (0.0, 0.6)
    } else {
        (0.3, 0.0)
    };
    Input {
        steer,
        throttle,
        brake,
        handbrake: false,
    }
}
