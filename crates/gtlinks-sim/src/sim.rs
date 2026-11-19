//! The run: fixed-step loop, finale director, events, tricks, damage and render state.

use crate::cars::{car_spec, car_tuning};
use crate::course::{Course, Interaction, PropKind, surface};
use crate::math::{Quat, Vec3, acos, asin, atan2, cos, exp, floor, lerp, ln, sin};
use crate::rng::Rng;
use crate::steins::{SteinFilter, SteinParams};
use crate::terrain::Ramp;
use crate::vehicle::{Controls, GRAVITY, Ground, StepReport, Vehicle};
use crate::{DT, MAX_FRAME_DT, STATE_LEN};

/// Run time at which the finale arms regardless of progress, s.
const ARM_TIME: f32 = 100.0;
/// Time without downhill progress that arms the finale, s.
const STALL_TIME: f32 = 12.0;
/// Fall-line progress that counts as downhill progress, m.
const STALL_PROGRESS: f32 = 1.0;
/// Speed the director aims for at the launch, m/s.
const LAUNCH_SPEED: f32 = 26.0;
/// FinaleArmed time after which the director gives up on a launch and settles, s.
const ARMED_TIMEOUT: f32 = 9.0;
/// Minimum time in FinaleAirborne before a contact counts as the touchdown, s.
const MIN_FINALE_FLIGHT: f32 = 0.3;
/// FinaleArmed time after which a car that has not moved 4 m is treated as wedged, s.
const WEDGED_AFTER: f32 = 5.0;
/// Settling time after which the last-resort righting torque engages, s.
const RIGHTING_AFTER: f32 = 4.0;
/// Settling time after which strong rest damping engages, s.
const DAMPING_AFTER: f32 = 8.0;
/// Settling time after which the car is placed inverted kinematically, s.
const KINEMATIC_AFTER: f32 = 11.0;
/// Settling roll tolerance from fully inverted, rad (20 degrees).
const SETTLE_TOLERANCE: f32 = 0.349;
/// Strength of the roll-tolerance clamp in Settling, as a multiple of the tipping moment.
const SETTLE_CLAMP: f32 = 1.6;
/// Roll error beyond the tolerance at which the clamp reaches full strength, rad.
const SETTLE_RAMP: f32 = 0.3;
/// Up-vector y below which the car counts as inverted.
const WRECK_UP: f32 = -0.9;
/// Linear speed below which the car counts as at rest, m/s.
const WRECK_SPEED: f32 = 0.1;
/// Time inverted and at rest before the phase becomes Wrecked, s.
const WRECK_DWELL: f32 = 1.0;
/// Airborne time before a JumpStart is announced, s.
const JUMP_MIN_AIR: f32 = 0.2;
/// Shortest run-up the director accepts before a kicker, m.
const MIN_RUN_UP: f32 = 16.0;
/// Clear ground wanted beyond the kicker for the flight and the roof slide, m.
const LANDING_CLEAR: f32 = 30.0;
/// How long the director backs out when the nose is against something, s.
const REVERSE_OUT: f32 = 1.5;
/// Finale roll controller: proportional gain, 1/s².
const ROLL_KP: f32 = 60.0;
/// Finale roll controller: derivative gain, 1/s.
const ROLL_KD: f32 = 13.0;
/// Finale roll controller: angular acceleration limit, rad/s².
const ROLL_MAX: f32 = 45.0;
/// Director kicker dimensions: length, width, height.
const KICKER: (f32, f32, f32) = (11.5, 8.0, 2.4);
/// Distance at which a spectator gets a NearMiss, m.
const NEAR_MISS_DIST: f32 = 4.0;
/// Below this speed nobody needs to dodge, m/s.
const NEAR_MISS_MIN_SPEED: f32 = 0.3;
/// Damage thresholds at which successive parts detach.
const PART_THRESHOLDS: [f32; 5] = [0.18, 0.32, 0.5, 0.7, 0.85];
/// Prop-kind offset in `Impact.b` so props and surfaces never share a code.
pub(crate) const IMPACT_PROP_BASE: f32 = 100.0;

/// Player intent for one call to [`Sim::step`].
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Input {
    /// Steering, -1..1, +1 = left (towards +X).
    pub steer: f32,
    /// Throttle, 0..1.
    pub throttle: f32,
    /// Brake, 0..1. Held near standstill (forward speed below 1 m/s, no throttle, no
    /// handbrake) it engages reverse.
    pub brake: f32,
    /// Handbrake: locks the rear wheels; in the air it turns steering into yaw.
    pub handbrake: bool,
}

/// Run phase, as in `state()[25]`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
#[repr(u8)]
pub enum Phase {
    /// The player is driving.
    Driving = 0,
    /// The director has taken over and is driving to a launch.
    FinaleArmed = 1,
    /// Airborne off the launch; a roll controller turns the car over.
    FinaleAirborne = 2,
    /// Ordinary contact physics bringing the car to rest on its roof.
    Settling = 3,
    /// Inverted and at rest. Terminal.
    Wrecked = 4,
}

/// Event kinds from the contract.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum EventKind {
    /// `a` = speed.
    JumpStart = 1,
    /// `a` = impact speed, `b` = airtime.
    Landing = 2,
    /// `a` = impulse 0..1, `b` = surface id (0..7), or 100 + prop kind, or 108 for the lodge.
    Impact = 3,
    /// `a` = prop index, `b` = prop kind.
    PropHit = 4,
    /// `a` = hole index.
    HoleEntered = 5,
    /// `a` = trick id, `b` = points.
    Trick = 6,
    /// `a` = prop index of the spectator who dodged.
    NearMiss = 7,
    /// `a` = launch yaw, `b` = [`LaunchKind`] code; position = launch ramp leading edge.
    FinaleStart = 8,
    /// The car is inverted and at rest.
    Wrecked = 9,
    /// `a` = part id (0 bumper_front, 1 bumper_rear, 2 bonnet, 3 mirror_l, 4 mirror_r).
    PartDetached = 10,
    /// `a` = strength 0..1.
    Hiccup = 11,
}

/// One event, emitted on the substep where it happened.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Event {
    /// Kind.
    pub kind: EventKind,
    /// First payload value.
    pub a: f32,
    /// Second payload value.
    pub b: f32,
    /// World position.
    pub pos: [f32; 3],
}

/// Flattens events to `[kind, a, b, x, y, z] * n` as the wasm API returns them.
pub fn flatten_events(events: &[Event]) -> Vec<f32> {
    let mut out = Vec::with_capacity(events.len() * 6);
    for e in events {
        out.extend_from_slice(&[
            f32::from(e.kind as u8),
            e.a,
            e.b,
            e.pos[0],
            e.pos[1],
            e.pos[2],
        ]);
    }
    out
}

/// Why the finale armed.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum ArmReason {
    /// The car reached the finale arena.
    Arena,
    /// Run time reached 100 s.
    Timer,
    /// No downhill progress for 12 s.
    Stall,
}

/// How the director launched the car (the `b` value of `FinaleStart`).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum LaunchKind {
    /// The final ramp in the arena (b = 0).
    FinalRamp = 0,
    /// A kicker raised ahead of the car (b = 1).
    Kicker = 1,
    /// The car was already off its wheels; straight to Settling (b = 2).
    AlreadyOver = 2,
    /// The car was already airborne; straight to FinaleAirborne (b = 3).
    AlreadyAirborne = 3,
}

/// How often each guarantee backstop fired in a run.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Fallbacks {
    /// The launch was abandoned after the FinaleArmed timeout.
    pub armed_timeout: u32,
    /// The last-resort righting torque engaged in Settling.
    pub righting_torque: u32,
    /// Strong rest damping engaged in Settling.
    pub rest_damping: u32,
    /// The car was placed inverted kinematically.
    pub kinematic: u32,
}

/// Summary statistics for a run.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct RunStats {
    /// Distance travelled, m.
    pub distance: f32,
    /// Highest speed, m/s.
    pub top_speed: f32,
    /// Total time airborne in announced jumps, s.
    pub airtime_total: f32,
    /// Number of tricks scored.
    pub tricks: u32,
    /// Phase changes with their run times.
    pub transitions: Vec<(Phase, f32)>,
    /// Furthest fall-line z reached before the finale armed.
    pub progress_z: f32,
    /// Why the finale armed, if it did.
    pub arm_reason: Option<ArmReason>,
    /// How the director launched, if it did.
    pub launch: Option<LaunchKind>,
    /// Guarantee backstops used.
    pub fallbacks: Fallbacks,
    /// Parts detached.
    pub parts_detached: u32,
    /// Run time at which every wheel had stopped after Wrecked.
    pub wheels_stopped_at: Option<f32>,
    /// Number of hiccups.
    pub hiccups: u32,
    /// Number of solid prop impacts.
    pub prop_impacts: u32,
    /// Body up-vector y at the finale touchdown (after FinaleAirborne).
    pub touchdown_up_y: Option<f32>,
}

#[derive(Clone, Copy, Debug, Default)]
struct Snapshot {
    origin: Vec3,
    q: Quat,
    v: Vec3,
    w: Vec3,
    comp: [f32; 4],
    spin: [f32; 4],
    steer: [f32; 4],
    time: f32,
}

#[derive(Clone, Copy, Debug)]
struct Launch {
    start: Vec3,
    dir: Vec3,
    length: f32,
}

/// One run of the game for a seed, car and stein count.
#[derive(Clone, Debug)]
pub struct Sim {
    course: Course,
    params: SteinParams,
    filter: SteinFilter,
    veh: Vehicle,
    phase: Phase,
    time: f32,
    acc: f32,
    prev: Snapshot,
    curr: Snapshot,
    events: Vec<Event>,
    report: StepReport,
    kicker: Option<Ramp>,
    launch: Option<Launch>,
    phase_since: f32,
    air_contactless: f32,
    roll_sign: f32,
    best_z: f32,
    best_z_time: f32,
    inverted_rest: f32,
    wrecked_at: Option<f32>,
    air_time: f32,
    jump_announced: bool,
    takeoff: Vec3,
    air_rot: Vec3,
    last_air_v: Vec3,
    damage: f32,
    parts: [bool; 5],
    last_terrain_impact: f32,
    knocked: Vec<bool>,
    contact_prev: Vec<u32>,
    contact_now: Vec<u32>,
    near_cooldown: Vec<f32>,
    near_buf: Vec<u32>,
    entered_hole: i32,
    hiccup_rng: Rng,
    next_hiccup: f32,
    score: f32,
    bunker_time: f32,
    skid_time: f32,
    skid_awarded: bool,
    applied_steer: f32,
    stats: RunStats,
    kinematic: bool,
    reverse_until: f32,
    reverse_count: u32,
    armed_at: Vec3,
    stuck_time: f32,
}

impl Sim {
    /// Generates the course for `seed` and places the car at the start.
    ///
    /// `car_id` is clamped to the available cars and `steins` to 10..=15.
    pub fn new(seed: u32, car_id: u32, steins: u32) -> Sim {
        Sim::from_course(Course::generate(seed), car_id, steins)
    }

    /// Starts a run on an existing course (cheaper than regenerating it).
    pub fn from_course(course: Course, car_id: u32, steins: u32) -> Sim {
        let spec = car_spec(car_id);
        let tuning = car_tuning(spec.id);
        let params = SteinParams::new(steins);
        let seed = course.seed();
        let filter = SteinFilter::new(params, seed);
        let mut veh = Vehicle::new(spec, &tuning, params.roof_mass);
        let start = course.start();
        veh.place(
            Vec3::new(start.pos[0], start.pos[1], start.pos[2]),
            start.yaw,
        );
        let n_props = course.props().len();
        let mut hiccup_rng = Rng::new(u64::from(seed), 0x0041_CC0F + u64::from(spec.id));
        let first = sample_interval(&mut hiccup_rng, params.hiccup_interval);
        let best_z = start.pos[2];
        let roll_sign = if seed & 1 == 0 { 1.0 } else { -1.0 };
        let mut sim = Sim {
            course,
            params,
            filter,
            veh,
            phase: Phase::Driving,
            time: 0.0,
            acc: 0.0,
            prev: Snapshot::default(),
            curr: Snapshot::default(),
            events: Vec::new(),
            report: StepReport::default(),
            kicker: None,
            launch: None,
            phase_since: 0.0,
            air_contactless: 0.0,
            roll_sign,
            best_z,
            best_z_time: 0.0,
            inverted_rest: 0.0,
            wrecked_at: None,
            air_time: 0.0,
            jump_announced: false,
            takeoff: Vec3::ZERO,
            air_rot: Vec3::ZERO,
            last_air_v: Vec3::ZERO,
            damage: 0.0,
            parts: [false; 5],
            last_terrain_impact: -10.0,
            knocked: vec![false; n_props],
            contact_prev: Vec::new(),
            contact_now: Vec::new(),
            near_cooldown: vec![0.0; n_props],
            near_buf: Vec::new(),
            entered_hole: -1,
            hiccup_rng,
            next_hiccup: first,
            score: 0.0,
            bunker_time: 0.0,
            skid_time: 0.0,
            skid_awarded: false,
            applied_steer: 0.0,
            stats: RunStats {
                progress_z: best_z,
                transitions: vec![(Phase::Driving, 0.0)],
                ..RunStats::default()
            },
            kinematic: false,
            reverse_until: -1.0,
            reverse_count: 0,
            armed_at: Vec3::ZERO,
            stuck_time: 0.0,
        };
        sim.curr = sim.snapshot();
        sim.prev = sim.curr;
        sim
    }

    /// The course this run is on.
    pub fn course(&self) -> &Course {
        &self.course
    }

    /// The stein handling parameters in use.
    pub fn stein_params(&self) -> &SteinParams {
        &self.params
    }

    /// Current phase.
    pub fn phase(&self) -> Phase {
        self.phase
    }

    /// Run time, s (advances in fixed substeps).
    pub fn run_time(&self) -> f32 {
        self.time
    }

    /// Body origin, world.
    pub fn position(&self) -> [f32; 3] {
        self.veh.origin().to_array()
    }

    /// Body forward axis, world.
    pub fn forward(&self) -> [f32; 3] {
        self.veh.forward().to_array()
    }

    /// Body up axis, world.
    pub fn up(&self) -> [f32; 3] {
        self.veh.up().to_array()
    }

    /// Linear velocity, world.
    pub fn velocity(&self) -> [f32; 3] {
        self.veh.v.to_array()
    }

    /// Linear speed, m/s.
    pub fn speed(&self) -> f32 {
        self.veh.v.length()
    }

    /// Accumulated damage, 0..1.
    pub fn damage(&self) -> f32 {
        self.damage
    }

    /// Run statistics so far.
    pub fn stats(&self) -> &RunStats {
        &self.stats
    }

    /// Terrain height including course ramps and any kicker the director has raised.
    pub fn height_at(&self, x: f32, z: f32) -> f32 {
        self.course.sample(x, z, self.kicker.as_ref()).0
    }

    /// The kicker raised by the director, if any.
    pub fn kicker(&self) -> Option<&Ramp> {
        self.kicker.as_ref()
    }

    /// Advances by wall-clock `dt` (clamped to 0.1 s) in fixed 1/120 s substeps.
    pub fn step(&mut self, dt: f32, input: Input) {
        let dt = if dt.is_finite() {
            dt.clamp(0.0, MAX_FRAME_DT)
        } else {
            0.0
        };
        self.acc += dt;
        while self.acc >= DT {
            self.acc -= DT;
            self.substep(input);
        }
    }

    /// Runs exactly one fixed substep.
    pub fn substep(&mut self, input: Input) {
        self.prev = self.curr;
        if self.phase == Phase::Wrecked {
            self.veh.spin_down(DT);
            self.time += DT;
            if self.stats.wheels_stopped_at.is_none() && self.veh.wheels_stopped() {
                self.stats.wheels_stopped_at = Some(self.time);
            }
            self.curr = self.snapshot();
            return;
        }
        let input = sanitise(input);
        let applied = self
            .filter
            .update(DT, input.steer, input.throttle, input.brake);
        let controls = if self.phase == Phase::Driving {
            self.applied_steer = applied.steer;
            Controls {
                steer: applied.steer,
                throttle: applied.throttle,
                brake: applied.brake,
                handbrake: input.handbrake,
                allow_reverse: true,
                air_control: true,
                assist: self.params.assist,
            }
        } else {
            let c = self.director_controls();
            self.applied_steer = c.steer;
            c
        };
        if self.phase == Phase::Driving {
            self.maybe_hiccup();
        }
        let torque = self.director_torque();

        if self.kinematic {
            self.kinematic_settle();
        } else {
            let ground = Ground {
                course: &self.course,
                kicker: self.kicker.as_ref(),
            };
            self.veh
                .step(&ground, &controls, torque, DT, &mut self.report);
        }
        if !self.veh.is_finite() {
            // Never expected; recover to a safe resting pose rather than propagate NaN.
            let p = self.curr.origin;
            let yaw = 0.0;
            self.veh
                .place(Vec3::new(p.x, self.height_at(p.x, p.z), p.z), yaw);
        }
        self.time += DT;
        self.post_step();
        self.curr = self.snapshot();
    }

    /// Applies a hiccup of `strength` (0..1) immediately, as the scheduler would.
    pub fn force_hiccup(&mut self, strength: f32) {
        self.hiccup(strength.clamp(0.0, 1.0));
    }

    /// Takes every event emitted since the last call.
    pub fn drain_events(&mut self) -> Vec<Event> {
        std::mem::take(&mut self.events)
    }

    /// The render state, interpolated between the last two substeps.
    pub fn state(&self) -> [f32; STATE_LEN] {
        let a = (self.acc / DT).clamp(0.0, 1.0);
        let (p, c) = (&self.prev, &self.curr);
        let mut s = [0.0f32; STATE_LEN];
        let o = p.origin.lerp(c.origin, a);
        let q = p.q.nlerp(c.q, a);
        let v = p.v.lerp(c.v, a);
        let w = p.w.lerp(c.w, a);
        s[0..3].copy_from_slice(&o.to_array());
        s[3..7].copy_from_slice(&q.to_array());
        s[7..10].copy_from_slice(&v.to_array());
        s[10..13].copy_from_slice(&w.to_array());
        for i in 0..4 {
            s[13 + i * 3] = lerp(p.comp[i], c.comp[i], a);
            s[14 + i * 3] = lerp(p.spin[i], c.spin[i], a);
            s[15 + i * 3] = lerp(p.steer[i], c.steer[i], a);
        }
        s[25] = f32::from(self.phase as u8);
        s[26] = self.damage;
        s[27] = lerp(p.time, c.time, a);
        s[28] = self.course.hole_at(self.veh.origin().z) as f32;
        s[29] = self.veh.v.dot(self.veh.forward());
        s[30] = self.report.wheels_on_ground as f32;
        s[31] = if self.grounded() { 0.0 } else { self.air_time };
        s[32] = self.applied_steer;
        s[33] = self.wobble();
        s[34] = self.score;
        s[35] = self.wrecked_at.map_or(0.0, |t| self.time - t);
        s
    }

    fn snapshot(&self) -> Snapshot {
        let mut comp = [0.0; 4];
        let mut spin = [0.0; 4];
        let mut steer = [0.0; 4];
        for (i, w) in self.veh.wheels.iter().enumerate() {
            comp[i] = w.compression;
            spin[i] = w.spin;
            steer[i] = w.steer;
        }
        Snapshot {
            origin: self.veh.origin(),
            q: self.veh.q,
            v: self.veh.v,
            w: self.veh.w,
            comp,
            spin,
            steer,
            time: self.time,
        }
    }

    fn wobble(&self) -> f32 {
        let wander = self.filter.wander().abs() / 0.28;
        (0.25 * self.params.s + 0.6 * wander + 2.0 * self.filter.jolt_level().abs()).clamp(0.0, 1.0)
    }

    fn grounded(&self) -> bool {
        self.report.wheels_on_ground > 0 || self.report.body_contacts > 0
    }

    fn emit(&mut self, kind: EventKind, a: f32, b: f32, pos: Vec3) {
        self.events.push(Event {
            kind,
            a,
            b,
            pos: pos.to_array(),
        });
    }

    fn set_phase(&mut self, phase: Phase) {
        self.phase = phase;
        self.phase_since = self.time;
        self.stats.transitions.push((phase, self.time));
    }

    fn maybe_hiccup(&mut self) {
        if self.time < self.next_hiccup || !self.grounded() {
            return;
        }
        let strength = 0.35 + 0.65 * self.hiccup_rng.f32();
        self.hiccup(strength);
        self.next_hiccup =
            self.time + sample_interval(&mut self.hiccup_rng, self.params.hiccup_interval);
    }

    fn hiccup(&mut self, strength: f32) {
        let up = self.veh.up();
        let left = self.veh.left();
        let sign = self.hiccup_rng.sign();
        self.veh.v += up * (0.9 * strength);
        self.veh.w += left * (0.25 * strength * sign);
        self.filter.jolt(0.18 * strength * self.hiccup_rng.sign());
        self.stats.hiccups += 1;
        let p = self.veh.origin();
        self.emit(EventKind::Hiccup, strength, 0.0, p);
    }

    /// Director controls for the finale phases: the car ignores the player.
    fn director_controls(&mut self) -> Controls {
        let mut c = Controls {
            assist: 0.6,
            ..Controls::default()
        };
        if self.phase == Phase::FinaleAirborne {
            // Foot still down: the wheels whirr in the air.
            c.throttle = 1.0;
            return c;
        }
        if self.phase != Phase::FinaleArmed {
            return c;
        }
        let Some(l) = self.launch else {
            return c;
        };
        let p = self.veh.pos;
        let fwd = self.veh.forward();
        let v_fwd = self.veh.v.dot(fwd);
        let rel = Vec3::new(p.x - l.start.x, 0.0, p.z - l.start.z);
        let along = rel.dot(l.dir);
        let look = 8.0 + 0.35 * v_fwd.abs();
        let target_along = (along + look).min(l.length + 4.0);
        let target = l.start + l.dir * target_along;
        let want = Vec3::new(target.x - p.x, 0.0, target.z - p.z).normalize_or(l.dir);
        let f = Vec3::new(fwd.x, 0.0, fwd.z).normalize_or(l.dir);
        let cross = f.z * want.x - f.x * want.z;
        let ang = atan2(cross, f.dot(want));
        c.steer = (2.2 * ang).clamp(-1.0, 1.0);
        // Pushing against something and getting nowhere: back out and try again.
        if self.time >= self.reverse_until {
            if v_fwd.abs() < 0.8 && self.time - self.phase_since > 1.0 {
                self.stuck_time += DT;
            } else {
                self.stuck_time = 0.0;
            }
            if self.stuck_time > 1.2 && self.reverse_count < 3 {
                self.stuck_time = 0.0;
                self.reverse_count += 1;
                self.reverse_until = self.time + REVERSE_OUT;
            }
        }
        if self.time < self.reverse_until {
            // Reverse with opposite lock so the nose swings towards the launch line.
            c.steer = -ang.signum();
            c.brake = 1.0;
            c.allow_reverse = true;
            return c;
        }
        if v_fwd < -0.5 {
            // Still rolling backwards: brake before driving off.
            c.brake = 1.0;
            return c;
        }
        if v_fwd < LAUNCH_SPEED - 2.0 {
            c.throttle = 1.0;
        } else if v_fwd > LAUNCH_SPEED + 3.0 {
            c.brake = 0.4;
        } else {
            c.throttle = 0.4;
        }
        c
    }

    /// Torques the director applies in the finale phases.
    fn director_torque(&mut self) -> Vec3 {
        match self.phase {
            Phase::FinaleAirborne if !self.grounded() => self.roll_controller(),
            Phase::Settling => self.settle_torque(),
            _ => Vec3::ZERO,
        }
    }

    /// PD controller rolling the airborne car towards inverted while keeping it level.
    fn roll_controller(&mut self) -> Vec3 {
        let f = self.veh.forward();
        let u = self.veh.up();
        let w = self.veh.w;
        let down = Vec3::new(0.0, -1.0, 0.0);
        let mut torque = Vec3::ZERO;
        let target = (down - f * f.dot(down)).normalize_or(down);
        let mut theta = atan2(f.dot(u.cross(target)), u.dot(target));
        if theta.abs() > 2.6 {
            theta = self.roll_sign * theta.abs();
        } else {
            self.roll_sign = theta.signum();
        }
        let ir = self.veh.inertia_about(f);
        let tr = (ir * (ROLL_KP * theta - ROLL_KD * w.dot(f))).clamp(-ROLL_MAX * ir, ROLL_MAX * ir);
        torque += f * tr;
        // Keep the nose level so the roof meets the ground flat.
        let axis = f.cross(Vec3::Y);
        if axis.length() > 0.2 {
            let a = axis.normalize_or(Vec3::X);
            let ip = self.veh.inertia_about(a);
            let pitch = asin(f.y);
            torque += a * ((ip * (-20.0 * pitch - 7.0 * w.dot(a))).clamp(-15.0 * ip, 15.0 * ip));
        }
        let iy = self.veh.inertia_about(Vec3::Y);
        torque += Vec3::Y * (-3.0 * iy * w.y);
        torque
    }

    /// Clamped tolerance torque in Settling, escalating to the righting torque.
    fn settle_torque(&mut self) -> Vec3 {
        let t = self.time - self.phase_since;
        let u = self.veh.up();
        let err = acos(-u.y);
        if err <= SETTLE_TOLERANCE {
            return Vec3::ZERO;
        }
        let fwd = self.veh.forward();
        let axis = u
            .cross(Vec3::new(0.0, -1.0, 0.0))
            .normalize_or(fwd * self.roll_sign);
        let i = self.veh.inertia_about(axis);
        let wa = self.veh.w.dot(axis);
        // Scale by the moment needed to tip the car over its roof edge or its wheels.
        let arm = (self.veh.width * 0.5).max(self.veh.roof_y - self.veh.cog_y);
        let lever = self.veh.mass * GRAVITY * arm;
        if t < RIGHTING_AFTER {
            if !self.grounded() {
                return Vec3::ZERO;
            }
            let over = (err - SETTLE_TOLERANCE) / SETTLE_RAMP;
            let m = (over * SETTLE_CLAMP * lever - 4.0 * i * wa)
                .clamp(-SETTLE_CLAMP * lever, SETTLE_CLAMP * lever);
            axis * m
        } else {
            if self.stats.fallbacks.righting_torque == 0 {
                self.stats.fallbacks.righting_torque = 1;
            }
            let m = (err / SETTLE_RAMP * lever - 8.0 * i * wa).clamp(-3.0 * lever, 3.0 * lever);
            axis * m
        }
    }

    /// Last resort: rotate to inverted on the spot and hold still.
    fn kinematic_settle(&mut self) {
        let f = self.veh.forward();
        let heading = atan2(f.x, f.z);
        let target =
            Quat::from_yaw(heading).mul(Quat::from_axis_angle(Vec3::Z, std::f32::consts::PI));
        self.veh.q = self.veh.q.nlerp(target, 0.08);
        self.veh.v = Vec3::ZERO;
        self.veh.w = Vec3::ZERO;
        let o = self.veh.origin();
        let ground = self.height_at(o.x, o.z);
        // Rest the roof on the ground: the CoG sits (roof - cog) above it when inverted.
        let lift = self.veh.roof_y - self.veh.cog_y;
        self.veh.pos = Vec3::new(self.veh.pos.x, ground + lift + 0.02, self.veh.pos.z);
        self.report.wheels_on_ground = 0;
        self.report.body_contacts = 1;
    }

    #[expect(
        clippy::too_many_lines,
        reason = "the per-substep rules, in contract order"
    )]
    fn post_step(&mut self) {
        let origin = self.veh.origin();
        let speed = self.veh.v.length();
        self.stats.distance += speed * DT;
        self.stats.top_speed = self.stats.top_speed.max(speed);

        self.track_air(origin);
        self.track_impacts();
        self.track_props(origin, speed);
        self.track_surface_tricks(speed);

        // Holes.
        let h = i32::try_from(self.course.hole_at(origin.z)).unwrap_or(0);
        let tee_z = self.course.spans[usize::try_from(h).unwrap_or(0)].tee_z;
        if h > self.entered_hole && origin.z >= tee_z - 2.0 {
            for k in (self.entered_hole + 1)..=h {
                let hole = &self.course.holes()[usize::try_from(k).unwrap_or(0)];
                let p = Vec3::new(hole.tee[0], hole.tee[1], hole.tee[2]);
                self.emit(EventKind::HoleEntered, k as f32, 0.0, p);
            }
            self.entered_hole = h;
        }

        let up = self.veh.up();
        match self.phase {
            Phase::Driving => {
                if origin.z > self.best_z + STALL_PROGRESS {
                    self.best_z = origin.z;
                    self.best_z_time = self.time;
                    self.stats.progress_z = origin.z;
                }
                let fin = self.course.finale();
                let dx = origin.x - fin.pos[0];
                let dz = origin.z - fin.pos[2];
                let in_arena = dx * dx + dz * dz < fin.radius * fin.radius;
                let reason = if in_arena || origin.z >= fin.pos[2] - fin.radius {
                    Some(ArmReason::Arena)
                } else if self.time >= ARM_TIME {
                    Some(ArmReason::Timer)
                } else if self.time - self.best_z_time >= STALL_TIME {
                    Some(ArmReason::Stall)
                } else {
                    None
                };
                if let Some(r) = reason {
                    self.arm(r, in_arena);
                }
            }
            Phase::FinaleArmed => {
                if self.grounded() {
                    self.air_contactless = 0.0;
                } else {
                    self.air_contactless += DT;
                }
                let t = self.time - self.phase_since;
                // Airborne off the launch, not merely skipping over a bump on the way to it.
                let reached = self.launch.is_some_and(|l| {
                    let p = self.veh.pos;
                    Vec3::new(p.x - l.start.x, 0.0, p.z - l.start.z).dot(l.dir) > 0.5 * l.length
                });
                if self.air_contactless >= 0.05 && (reached || self.air_contactless >= 0.3) {
                    self.set_phase(Phase::FinaleAirborne);
                } else if up.y < 0.3 {
                    self.set_phase(Phase::Settling);
                } else if t >= ARMED_TIMEOUT
                    || (t >= WEDGED_AFTER
                        && Vec3::new(origin.x - self.armed_at.x, 0.0, origin.z - self.armed_at.z)
                            .length()
                            < 4.0)
                {
                    self.stats.fallbacks.armed_timeout += 1;
                    self.set_phase(Phase::Settling);
                }
            }
            Phase::FinaleAirborne => {
                // A wheel brushing the lip on the way off is not a touchdown.
                if self.grounded() && self.time - self.phase_since >= MIN_FINALE_FLIGHT {
                    self.stats.touchdown_up_y = Some(up.y);
                    self.finale_landing();
                    self.set_phase(Phase::Settling);
                }
            }
            Phase::Settling => {
                let t = self.time - self.phase_since;
                if t >= DAMPING_AFTER {
                    if self.stats.fallbacks.rest_damping == 0 {
                        self.stats.fallbacks.rest_damping = 1;
                    }
                    let k = exp(-3.0 * DT);
                    self.veh.v = self.veh.v * k;
                    self.veh.w = self.veh.w * k;
                } else if acos(-up.y) <= SETTLE_TOLERANCE && self.grounded() {
                    // Within tolerance: scrub off the rocking.
                    self.veh.w = self.veh.w * exp(-2.0 * DT);
                }
                if t >= KINEMATIC_AFTER && !self.kinematic {
                    self.stats.fallbacks.kinematic += 1;
                    self.kinematic = true;
                }
            }
            Phase::Wrecked => {}
        }

        // Wrecked is a state: inverted and at rest for long enough, in any phase.
        let up = self.veh.up();
        if up.y < WRECK_UP && self.veh.v.length() < WRECK_SPEED {
            self.inverted_rest += DT;
        } else {
            self.inverted_rest = 0.0;
        }
        if self.inverted_rest >= WRECK_DWELL && self.phase != Phase::Wrecked {
            self.wreck();
        }
    }

    fn arm(&mut self, reason: ArmReason, in_arena: bool) {
        self.stats.arm_reason = Some(reason);
        self.stats.progress_z = self.best_z.max(self.veh.origin().z);
        self.set_phase(Phase::FinaleArmed);
        self.air_contactless = 0.0;
        let origin = self.veh.origin();
        self.armed_at = origin;
        let up = self.veh.up();
        if up.y < 0.5 {
            self.stats.launch = Some(LaunchKind::AlreadyOver);
            self.emit(
                EventKind::FinaleStart,
                0.0,
                f32::from(LaunchKind::AlreadyOver as u8),
                origin,
            );
            self.set_phase(Phase::Settling);
            return;
        }
        if !self.grounded() && self.air_time >= JUMP_MIN_AIR {
            self.stats.launch = Some(LaunchKind::AlreadyAirborne);
            self.emit(
                EventKind::FinaleStart,
                0.0,
                f32::from(LaunchKind::AlreadyAirborne as u8),
                origin,
            );
            self.set_phase(Phase::FinaleAirborne);
            return;
        }
        let (launch, kind, yaw, pos) = self.plan_launch(in_arena);
        self.launch = Some(launch);
        self.stats.launch = Some(kind);
        self.emit(EventKind::FinaleStart, yaw, f32::from(kind as u8), pos);
    }

    /// Chooses the final ramp if it is reachable, otherwise raises a kicker on a clear line.
    fn plan_launch(&mut self, in_arena: bool) -> (Launch, LaunchKind, f32, Vec3) {
        let p = self.veh.pos;
        let fwd = self.veh.forward();
        let course = &self.course;
        if in_arena {
            let fin = course.finale();
            let r = course.ramps()[fin.ramp_index];
            let (dx, dz) = r.dir();
            let dir = Vec3::new(dx, 0.0, dz);
            let start = Vec3::new(r.pos[0], r.pos[1], r.pos[2]);
            let rel = Vec3::new(start.x - p.x, 0.0, start.z - p.z);
            let along = rel.dot(dir);
            let lateral = (rel - dir * along).length();
            let f = Vec3::new(fwd.x, 0.0, fwd.z).normalize_or(dir);
            if along > 18.0 && lateral < 0.6 * along && f.dot(dir) > 0.5 {
                let l = Launch {
                    start,
                    dir,
                    length: r.length,
                };
                return (l, LaunchKind::FinalRamp, r.yaw, start);
            }
        }
        let f = Vec3::new(fwd.x, 0.0, fwd.z).normalize_or(Vec3::Z);
        let base_yaw = atan2(f.x, f.z);
        let speed = Vec3::new(self.veh.v.x, 0.0, self.veh.v.z).length();
        let (kl, kw, kh) = KICKER;
        let wanted = (26.0 + 0.8 * speed).min(55.0);
        let obstacles = self.obstacles_near(p, 140.0);
        let mut best = (f32::NEG_INFINITY, base_yaw, wanted);
        let mut off = 0.0f32;
        for k in 0..17 {
            // 0, +0.3, -0.3, +0.6, -0.6, ... up to +-2.4 rad.
            if k > 0 {
                let step = ((k + 1) / 2) as f32 * 0.3;
                off = if k % 2 == 1 { step } else { -step };
            }
            let yaw = base_yaw + off;
            let d = Vec3::new(sin(yaw), 0.0, cos(yaw));
            let clear = path_clearance(
                &obstacles,
                p,
                base_yaw,
                yaw,
                self.veh.width * 0.5 + 1.0,
                130.0,
            );
            let dist = wanted.min(clear - kl - LANDING_CLEAR).max(MIN_RUN_UP);
            let landing = clear - dist - kl;
            let mut score = 4.0 * d.z - 1.5 * off.abs() + 0.3 * dist + 0.3 * landing.min(40.0);
            if clear < MIN_RUN_UP + kl + 2.0 {
                score -= 100.0;
            }
            let (e, _) = path_point(p, base_yaw, yaw, dist + kl);
            let h0 = course.terrain_height(p.x, p.z);
            let h1 = course.terrain_height(e.x, e.z);
            if (h1 - h0) / (dist + kl) > 0.08 {
                score -= 20.0;
            }
            for k in 1..=6 {
                let (s, _) = path_point(p, base_yaw, yaw, (dist + kl) * k as f32 / 6.0);
                if course.surface_at(s.x, s.z) == surface::WATER
                    || course.in_lodge_footprint(s.x, s.z, 3.0)
                {
                    score -= 15.0;
                }
            }
            if score > best.0 {
                best = (score, yaw, dist);
            }
        }
        let (_, yaw, dist) = best;
        let d = Vec3::new(sin(yaw), 0.0, cos(yaw));
        // Nose against something solid: back out before going for the kicker.
        if path_clearance(&obstacles, p, base_yaw, base_yaw, self.veh.width * 0.5, 6.0)
            < self.veh.length * 0.5 + 1.5
        {
            self.reverse_until = self.time + REVERSE_OUT;
        }
        let (s, _) = path_point(p, base_yaw, yaw, dist);
        let start = Vec3::new(s.x, course.terrain_height(s.x, s.z), s.z);
        self.kicker = Some(Ramp {
            pos: start.to_array(),
            yaw,
            length: kl,
            width: kw,
            height: kh,
        });
        let l = Launch {
            start,
            dir: d,
            length: kl,
        };
        (l, LaunchKind::Kicker, yaw, start)
    }

    /// Solid obstacles `(x, z, radius)` within `r` of `p`.
    fn obstacles_near(&self, p: Vec3, r: f32) -> Vec<(f32, f32, f32)> {
        let mut near = Vec::new();
        self.course.props_near(p.x, p.z, r, &mut near);
        let props = self.course.props();
        let mut out: Vec<(f32, f32, f32)> = near
            .iter()
            .map(|&i| props[i as usize])
            .filter(|pr| pr.prop_kind().interaction() == Interaction::Solid)
            .map(|pr| (pr.pos[0], pr.pos[2], pr.prop_kind().radius() * pr.scale))
            .collect();
        out.extend_from_slice(&self.course.blockers);
        out
    }

    fn finale_landing(&mut self) {
        self.add_damage(0.12, Vec3::new(0.0, 1.0, 0.0));
        self.top_up_parts(2);
    }

    fn wreck(&mut self) {
        self.top_up_parts(2);
        self.veh.v = Vec3::ZERO;
        self.veh.w = Vec3::ZERO;
        self.set_phase(Phase::Wrecked);
        self.veh.begin_spin_down();
        self.wrecked_at = Some(self.time);
        let p = self.veh.origin();
        self.emit(EventKind::Wrecked, 0.0, 0.0, p);
        // Freeze interpolation on the resting pose.
        self.curr = self.snapshot();
        self.prev = self.curr;
    }

    fn track_air(&mut self, origin: Vec3) {
        if self.grounded() {
            if self.jump_announced {
                let n = self.course.normal_at(origin.x, origin.z);
                let impact = (-self.last_air_v.dot(Vec3::new(n[0], n[1], n[2]))).max(0.0);
                self.emit(EventKind::Landing, impact, self.air_time, origin);
                self.stats.airtime_total += self.air_time;
                if self.phase == Phase::Driving {
                    self.score_air_tricks(origin);
                }
                if impact > 9.0 {
                    self.add_damage(0.03, Vec3::new(0.0, -1.0, 0.0));
                }
            }
            self.air_time = 0.0;
            self.jump_announced = false;
            self.air_rot = Vec3::ZERO;
        } else {
            if self.air_time == 0.0 {
                self.takeoff = origin;
            }
            self.air_time += DT;
            self.last_air_v = self.veh.v;
            let w = self.veh.w;
            self.air_rot += Vec3::new(
                w.dot(self.veh.left()),
                w.dot(self.veh.up()),
                w.dot(self.veh.forward()),
            ) * DT;
            if !self.jump_announced && self.air_time >= JUMP_MIN_AIR {
                self.jump_announced = true;
                let speed = self.veh.v.length();
                let p = self.takeoff;
                self.emit(EventKind::JumpStart, speed, 0.0, p);
            }
        }
    }

    fn score_air_tricks(&mut self, origin: Vec3) {
        let full = std::f32::consts::TAU;
        let count = |a: f32| floor((a.abs() + 0.6) / full) as u32;
        let rot = self.air_rot;
        let mut tricks: Vec<(f32, f32)> = Vec::new();
        for _ in 0..count(rot.z) {
            tricks.push((1.0, 500.0));
        }
        let flip = if rot.x > 0.0 { 2.0 } else { 3.0 };
        for _ in 0..count(rot.x) {
            tricks.push((flip, 600.0));
        }
        for _ in 0..count(rot.y) {
            tricks.push((4.0, 400.0));
        }
        if self.air_time >= 1.2 {
            tricks.push((0.0, (100.0 * self.air_time).round()));
        }
        for (id, pts) in tricks {
            self.award(id, pts, origin);
        }
    }

    fn award(&mut self, id: f32, points: f32, pos: Vec3) {
        self.score += points;
        self.stats.tricks += 1;
        self.emit(EventKind::Trick, id, points, pos);
    }

    fn track_surface_tricks(&mut self, speed: f32) {
        if self.phase != Phase::Driving {
            return;
        }
        let origin = self.veh.origin();
        let wheels = self.veh.wheels;
        let in_bunker = wheels
            .iter()
            .any(|w| w.grounded && w.surface == surface::BUNKER);
        if in_bunker && speed > 12.0 {
            self.bunker_time += DT;
        } else if !in_bunker {
            if self.bunker_time > 0.3 && speed > 8.0 {
                self.award(5.0, 250.0, origin);
            }
            self.bunker_time = 0.0;
        }
        let on_green = wheels
            .iter()
            .any(|w| w.grounded && w.surface == surface::GREEN);
        let skidding = wheels
            .iter()
            .any(|w| w.grounded && w.surface == surface::GREEN && w.lateral_speed.abs() > 4.0);
        if on_green {
            if skidding {
                self.skid_time += DT;
            }
            if self.skid_time > 0.5 && !self.skid_awarded {
                self.skid_awarded = true;
                self.award(6.0, 300.0, origin);
            }
        } else {
            self.skid_time = 0.0;
            self.skid_awarded = false;
        }
    }

    fn track_impacts(&mut self) {
        if let Some((closing, surf, point, dir_body)) = self.report.terrain_impact
            && closing > 3.0
            && self.time - self.last_terrain_impact > 0.3
        {
            self.last_terrain_impact = self.time;
            let a = (closing / 15.0).min(1.0);
            self.emit(EventKind::Impact, a, f32::from(surf), point);
            if closing > 4.0 {
                self.add_damage(0.08 * a, dir_body);
            }
        }
        self.contact_now.clear();
        let contacts = std::mem::take(&mut self.report.props);
        for c in &contacts {
            let key = c.prop.unwrap_or(u32::MAX);
            self.contact_now.push(key);
            if self.contact_prev.contains(&key) || c.closing_speed < 1.0 {
                continue;
            }
            let a = (c.closing_speed / 20.0).min(1.0);
            let b = match c.prop {
                Some(i) => IMPACT_PROP_BASE + f32::from(self.course.props()[i as usize].kind),
                None => IMPACT_PROP_BASE + 8.0,
            };
            self.stats.prop_impacts += 1;
            self.emit(EventKind::Impact, a, b, c.point);
            if c.closing_speed > 2.0 {
                self.add_damage(0.03 + 0.12 * a, c.dir_body);
            }
        }
        self.report.props = contacts;
        std::mem::swap(&mut self.contact_prev, &mut self.contact_now);
    }

    fn track_props(&mut self, origin: Vec3, speed: f32) {
        let knocked = std::mem::take(&mut self.report.knocked);
        for &i in &knocked {
            let iu = i as usize;
            if !self.knocked[iu] {
                self.knocked[iu] = true;
                let pr = self.course.props()[iu];
                let p = Vec3::new(pr.pos[0], pr.pos[1], pr.pos[2]);
                self.emit(EventKind::PropHit, i as f32, f32::from(pr.kind), p);
            }
        }
        self.report.knocked = knocked;
        // Even a crawling car makes the spectators step aside (the cooldown stops repeats).
        if speed < NEAR_MISS_MIN_SPEED {
            return;
        }
        let v = Vec3::new(self.veh.v.x, 0.0, self.veh.v.z);
        let v2 = v.length_sq().max(1e-3);
        let mut near = std::mem::take(&mut self.near_buf);
        self.course.props_near(
            origin.x,
            origin.z,
            NEAR_MISS_DIST + 0.8 * speed + 2.0,
            &mut near,
        );
        for &i in &near {
            let iu = i as usize;
            let pr = self.course.props()[iu];
            if pr.prop_kind() != PropKind::Spectator || self.time < self.near_cooldown[iu] {
                continue;
            }
            let rel = Vec3::new(pr.pos[0] - origin.x, 0.0, pr.pos[2] - origin.z);
            let t = (rel.dot(v) / v2).clamp(0.0, 0.8);
            let closest = (rel - v * t).length();
            if closest < NEAR_MISS_DIST && (pr.pos[1] - origin.y).abs() < 6.0 {
                self.near_cooldown[iu] = self.time + 4.0;
                let p = Vec3::new(pr.pos[0], pr.pos[1], pr.pos[2]);
                self.emit(EventKind::NearMiss, i as f32, 0.0, p);
            }
        }
        self.near_buf = near;
    }

    fn add_damage(&mut self, amount: f32, dir_body: Vec3) {
        self.damage = (self.damage + amount).min(1.0);
        loop {
            let n = self.parts.iter().filter(|&&p| p).count();
            if n >= PART_THRESHOLDS.len() || self.damage < PART_THRESHOLDS[n] {
                break;
            }
            self.detach(preferred_part(dir_body));
        }
    }

    fn top_up_parts(&mut self, min: usize) {
        while self.parts.iter().filter(|&&p| p).count() < min {
            // Landing on the roof takes the mirrors first.
            self.detach(3);
        }
        let n = self.parts.iter().filter(|&&p| p).count();
        self.damage = self.damage.max(PART_THRESHOLDS[n.saturating_sub(1).min(4)]);
    }

    fn detach(&mut self, preferred: usize) {
        let order: [usize; 5] = match preferred {
            0 => [0, 2, 3, 4, 1],
            1 => [1, 3, 4, 0, 2],
            2 => [2, 0, 3, 4, 1],
            3 => [3, 4, 0, 1, 2],
            _ => [4, 3, 0, 1, 2],
        };
        let Some(part) = order.into_iter().find(|&p| !self.parts[p]) else {
            return;
        };
        self.parts[part] = true;
        self.stats.parts_detached += 1;
        let (l, w) = (self.veh.length, self.veh.width);
        let local = match part {
            0 => Vec3::new(0.0, 0.5, l * 0.5),
            1 => Vec3::new(0.0, 0.5, -l * 0.5),
            2 => Vec3::new(0.0, 1.0, l * 0.3),
            3 => Vec3::new(w * 0.5, 1.1, l * 0.15),
            _ => Vec3::new(-w * 0.5, 1.1, l * 0.15),
        };
        let p = self.veh.origin() + self.veh.q.rotate(local);
        self.emit(EventKind::PartDetached, part as f32, 0.0, p);
    }
}

/// Turning radius the director plans with, m.
const PLAN_TURN_RADIUS: f32 = 10.0;

/// Point and heading after travelling `s` metres from `p`: turn from `yaw0` towards `yaw1` at
/// the planning radius, then straight on.
fn path_point(p: Vec3, yaw0: f32, yaw1: f32, s: f32) -> (Vec3, f32) {
    let turn = yaw1 - yaw0;
    let arc = turn.abs() * PLAN_TURN_RADIUS;
    let mut pos = p;
    let mut yaw = yaw0;
    let mut travelled = 0.0;
    while travelled + 1.0 <= s.min(arc) {
        yaw += turn.signum() / PLAN_TURN_RADIUS;
        pos += Vec3::new(sin(yaw), 0.0, cos(yaw));
        travelled += 1.0;
    }
    if travelled < s {
        yaw = if arc <= s { yaw1 } else { yaw };
        pos += Vec3::new(sin(yaw), 0.0, cos(yaw)) * (s - travelled);
    }
    (pos, yaw)
}

/// Distance along the planned path to the first obstacle closer than `half_width`.
fn path_clearance(
    obstacles: &[(f32, f32, f32)],
    p: Vec3,
    yaw0: f32,
    yaw1: f32,
    half_width: f32,
    max: f32,
) -> f32 {
    let mut s = 1.0;
    while s <= max {
        let (q, _) = path_point(p, yaw0, yaw1, s);
        if obstacles.iter().any(|&(x, z, r)| {
            (x - q.x) * (x - q.x) + (z - q.z) * (z - q.z) < (half_width + r) * (half_width + r)
        }) {
            return s;
        }
        s += 1.0;
    }
    max
}

/// Picks the part most exposed to a hit from direction `d` (body frame).
fn preferred_part(d: Vec3) -> usize {
    if d.z > 0.5 {
        if d.y > 0.3 { 2 } else { 0 }
    } else if d.z < -0.5 {
        1
    } else if d.x >= 0.0 {
        3
    } else {
        4
    }
}

/// Exponentially distributed hiccup interval with the given mean, clamped to a sane range.
fn sample_interval(rng: &mut Rng, mean: f32) -> f32 {
    let u = rng.f32().clamp(1e-4, 0.9999);
    (-mean * ln(1.0 - u)).clamp(0.6, 5.0 * mean)
}

fn sanitise(i: Input) -> Input {
    let f = |v: f32, lo: f32, hi: f32| if v.is_finite() { v.clamp(lo, hi) } else { 0.0 };
    Input {
        steer: f(i.steer, -1.0, 1.0),
        throttle: f(i.throttle, 0.0, 1.0),
        brake: f(i.brake, 0.0, 1.0),
        handbrake: i.handbrake,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hiccup_intervals_have_the_contract_means() {
        let mut rng = Rng::new(1, 2);
        for mean in [9.0f32, 3.0] {
            let n = 20_000;
            let total: f32 = (0..n).map(|_| sample_interval(&mut rng, mean)).sum();
            let got = total / n as f32;
            assert!(
                (got - mean).abs() < 0.08 * mean,
                "mean interval {got} for {mean}"
            );
        }
    }

    #[test]
    fn parts_detach_towards_the_hit() {
        assert_eq!(preferred_part(Vec3::new(0.0, 0.0, 1.0)), 0);
        assert_eq!(preferred_part(Vec3::new(0.0, 0.0, -1.0)), 1);
        assert_eq!(preferred_part(Vec3::new(1.0, 0.0, 0.0)), 3);
        assert_eq!(preferred_part(Vec3::new(-1.0, 0.0, 0.0)), 4);
    }

    #[test]
    fn planned_path_turns_then_runs_straight() {
        let (p, yaw) = path_point(Vec3::ZERO, 0.0, 1.0, 60.0);
        assert!((yaw - 1.0).abs() < 1e-5);
        assert!(p.x > 0.0 && p.z > 0.0);
    }
}
