//! Rigid-body vehicle: four raycast suspensions, tyre forces, aerodynamic drag, and an
//! impulse contact solver for the body against terrain, ramps and solid props.

use crate::cars::{CarSpec, CarTuning};
use crate::course::{Course, Interaction, PropKind, surface};
use crate::math::{Quat, Vec3, atan2, cos, exp, sin, smoothstep, sqrt};
use crate::terrain::{Ramp, normal_from_gradient};

/// Gravitational acceleration, m/s².
pub(crate) const GRAVITY: f32 = 9.81;
/// Air density, kg/m³.
const AIR_DENSITY: f32 = 1.225;
/// Effective drag area, m². Exaggerated well beyond a real SUV so downhill speed stays in
/// the 25 to 45 m/s band on fairway slopes; the biggest single lever on run pace.
pub(crate) const DRAG_AREA: f32 = 3.6;
/// Peak slip angle of the tyre curve, rad.
const SLIP_PEAK: f32 = 0.14;
/// Speed below which slip angles are regularised, m/s.
const SLIP_REGULARISE: f32 = 2.5;
/// Front share of drive torque (all four are driven).
const FRONT_DRIVE: f32 = 0.4;
/// Maximum steering lock at standstill, rad.
const MAX_LOCK: f32 = 0.6;
/// Speed at which steering lock has halved, m/s.
const LOCK_HALF_SPEED: f32 = 9.0;
/// Mid-air pitch and roll authority, rad/s².
const AIR_AUTHORITY: f32 = 3.5;
/// Fraction of full input ignored by mid-air control.
const AIR_DEADZONE: f32 = 0.5;
/// Passive mid-air roll and pitch damping without input, 1/s.
const AIR_DAMPING: f32 = 1.2;
/// Mid-air yaw authority (handbrake held), rad/s².
const AIR_YAW_AUTHORITY: f32 = 3.0;
/// Yaw damping of the sober car, 1/s (scaled by the stein model's assist).
const YAW_DAMPING: f32 = 2.5;
/// Anti-roll stiffness as a fraction of the corner spring rate.
const ANTI_ROLL: f32 = 0.5;
/// Roof sliding friction: low enough for a long slide, high enough to hold on any slope.
const ROOF_FRICTION: f32 = 0.5;
/// Contact solver iterations.
const SOLVER_ITERATIONS: usize = 8;
/// Baumgarte position-correction factor.
const BAUMGARTE: f32 = 0.1;
/// Largest separation speed the position correction may add, m/s.
const MAX_CORRECTION: f32 = 0.8;
/// Allowed penetration before correction, m.
const SLOP: f32 = 0.01;
/// Wheel spin decay time constant while inverted, before the wreck, s.
const INVERTED_SPIN_TAU: f32 = 3.0;
/// Time over which the wheels spin down to a stop after Wrecked, s.
pub(crate) const WRECK_SPIN_DOWN: f32 = 6.0;
/// Free spin rate of the driven wheels in the air at full throttle, rad/s.
const AIR_SPIN_RATE: f32 = 70.0;

/// Grip and rolling resistance of a surface id.
pub(crate) fn surface_friction(id: u8) -> (f32, f32) {
    match id {
        surface::FAIRWAY | surface::TEE => (1.0, 0.015),
        surface::GREEN => (0.6, 0.006),
        surface::BUNKER => (0.7, 0.32),
        surface::CART_PATH => (1.05, 0.012),
        surface::ROCK => (0.9, 0.04),
        surface::WATER => (0.45, 0.5),
        _ => (0.85, 0.09),
    }
}

/// The terrain, course ramps and the director's kicker as seen by the car.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Ground<'a> {
    pub(crate) course: &'a Course,
    pub(crate) kicker: Option<&'a Ramp>,
}

impl Ground<'_> {
    pub(crate) fn height(&self, x: f32, z: f32) -> f32 {
        self.course.sample(x, z, self.kicker).0
    }

    pub(crate) fn sample(&self, x: f32, z: f32) -> (f32, Vec3) {
        let (h, gx, gz) = self.course.sample(x, z, self.kicker);
        (h, normal_from_gradient(gx, gz))
    }

    pub(crate) fn surface(&self, x: f32, z: f32) -> u8 {
        if self.course.on_ramp(x, z, self.kicker) {
            surface::FAIRWAY
        } else {
            self.course.surface_at(x, z)
        }
    }
}

/// Controls fed to the vehicle for one substep.
#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct Controls {
    pub(crate) steer: f32,
    pub(crate) throttle: f32,
    pub(crate) brake: f32,
    pub(crate) handbrake: bool,
    /// Brake held near standstill engages reverse.
    pub(crate) allow_reverse: bool,
    /// Steer and pedals rotate the car while airborne.
    pub(crate) air_control: bool,
    /// Stability assist fraction (0..1).
    pub(crate) assist: f32,
}

/// Per-wheel state.
#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct Wheel {
    pub(crate) anchor: Vec3,
    pub(crate) compression: f32,
    pub(crate) spin: f32,
    pub(crate) spin_rate: f32,
    pub(crate) steer: f32,
    pub(crate) grounded: bool,
    pub(crate) surface: u8,
    pub(crate) lateral_speed: f32,
    /// Linear spin-down rate after the wreck, rad/s².
    pub(crate) spin_down_rate: f32,
}

/// A solid contact found this substep.
#[derive(Clone, Copy, Debug)]
pub(crate) struct PropContact {
    /// Prop index, or `None` for the lodge building.
    pub(crate) prop: Option<u32>,
    pub(crate) closing_speed: f32,
    /// Contact direction in the body frame (from car towards obstacle).
    pub(crate) dir_body: Vec3,
    pub(crate) point: Vec3,
}

/// What happened during a substep, for the event logic.
#[derive(Clone, Debug, Default)]
pub(crate) struct StepReport {
    pub(crate) wheels_on_ground: u32,
    pub(crate) body_contacts: u32,
    /// Hardest terrain contact: (closing speed, surface, contact point, body-frame direction).
    pub(crate) terrain_impact: Option<(f32, u8, Vec3, Vec3)>,
    pub(crate) props: Vec<PropContact>,
    pub(crate) knocked: Vec<u32>,
}

#[derive(Clone, Copy, Debug)]
struct Contact {
    r: Vec3,
    n: Vec3,
    t1: Vec3,
    t2: Vec3,
    kn: f32,
    kt1: f32,
    kt2: f32,
    target: f32,
    mu: f32,
    ln: f32,
    lt1: f32,
    lt2: f32,
}

/// The car as a rigid body.
#[derive(Clone, Debug)]
pub(crate) struct Vehicle {
    pub(crate) mass: f32,
    inv_mass: f32,
    inertia: Vec3,
    /// Centre of gravity above the body origin, m.
    pub(crate) cog_y: f32,
    /// Roof height above the body origin, m.
    pub(crate) roof_y: f32,
    wheel_r: f32,
    travel: f32,
    spring: f32,
    damper: f32,
    power: f32,
    max_drive: f32,
    top_speed: f32,
    grip: f32,
    roll_lever: f32,
    wheelbase: f32,
    pub(crate) length: f32,
    pub(crate) width: f32,
    /// Body sample points relative to the CoG (body frame) with friction coefficient.
    points: Vec<(Vec3, f32)>,
    /// Centre of gravity, world.
    pub(crate) pos: Vec3,
    pub(crate) q: Quat,
    pub(crate) v: Vec3,
    pub(crate) w: Vec3,
    pub(crate) wheels: [Wheel; 4],
    contacts: Vec<Contact>,
    near: Vec<u32>,
}

impl Vehicle {
    pub(crate) fn new(spec: &CarSpec, tuning: &CarTuning, roof_mass: f32) -> Self {
        let mass = spec.mass + roof_mass;
        let cog_y = (spec.mass * spec.cog_height + roof_mass * spec.roof_y) / mass;
        let h = spec.height * 0.85;
        let (l, wd) = (spec.length, spec.width);
        let roof_arm = (spec.roof_y - cog_y) * (spec.roof_y - cog_y);
        let inertia = Vec3::new(
            spec.mass / 12.0 * (h * h + l * l) + roof_mass * roof_arm,
            spec.mass / 12.0 * (wd * wd + l * l),
            spec.mass / 12.0 * (wd * wd + h * h) + roof_mass * roof_arm,
        );
        let omega = std::f32::consts::TAU * tuning.ride_hz;
        let corner = mass * 0.25;
        let spring = corner * omega * omega;
        let damper = 2.0 * tuning.damping_ratio * sqrt(spring * corner);
        let rest = corner * GRAVITY / spring;
        let anchor_y = spec.wheel_radius + tuning.travel - rest - cog_y;
        let (ht, hb) = (spec.track * 0.5, spec.wheelbase * 0.5);
        let wheels = [
            Vec3::new(ht, anchor_y, hb),
            Vec3::new(-ht, anchor_y, hb),
            Vec3::new(ht, anchor_y, -hb),
            Vec3::new(-ht, anchor_y, -hb),
        ]
        .map(|anchor| Wheel {
            anchor,
            compression: rest,
            grounded: true,
            ..Wheel::default()
        });
        let (hw, hl) = (spec.width * 0.5, spec.length * 0.5);
        let gc = spec.ground_clearance;
        let mut points = Vec::new();
        for sx in [-1.0f32, 1.0] {
            for sz in [-1.0f32, 1.0] {
                points.push((Vec3::new(sx * hw * 0.95, gc + 0.08, sz * hl * 0.95), 0.3));
                points.push((Vec3::new(sx * hw, spec.height * 0.55, sz * hl), 0.55));
                points.push((
                    Vec3::new(sx * hw * 0.96, spec.height * 0.82, sz * hl * 0.3),
                    0.6,
                ));
                points.push((
                    Vec3::new(sx * spec.width * 0.42, spec.roof_y, sz * hl * 0.56),
                    ROOF_FRICTION,
                ));
            }
            points.push((Vec3::new(sx * hw * 0.95, gc, 0.0), 0.5));
            points.push((
                Vec3::new(sx * spec.width * 0.42, spec.roof_y, 0.0),
                ROOF_FRICTION,
            ));
        }
        let points = points
            .into_iter()
            .map(|(p, mu)| (p - Vec3::new(0.0, cog_y, 0.0), mu))
            .collect();
        Self {
            mass,
            inv_mass: 1.0 / mass,
            inertia,
            cog_y,
            roof_y: spec.roof_y,
            wheel_r: spec.wheel_radius,
            travel: tuning.travel,
            spring,
            damper,
            power: tuning.power_per_kg * spec.mass,
            max_drive: mass * 5.5,
            top_speed: tuning.top_speed,
            grip: tuning.grip,
            roll_lever: tuning.roll_lever,
            wheelbase: spec.wheelbase,
            length: spec.length,
            width: spec.width,
            points,
            pos: Vec3::ZERO,
            q: Quat::IDENTITY,
            v: Vec3::ZERO,
            w: Vec3::ZERO,
            wheels,
            contacts: Vec::with_capacity(32),
            near: Vec::with_capacity(64),
        }
    }

    /// Places the car at rest with its body origin at `origin`, heading `yaw`.
    pub(crate) fn place(&mut self, origin: Vec3, yaw: f32) {
        self.q = Quat::from_yaw(yaw);
        self.pos = origin + self.q.rotate(Vec3::new(0.0, self.cog_y, 0.0));
        self.v = Vec3::ZERO;
        self.w = Vec3::ZERO;
    }

    pub(crate) fn up(&self) -> Vec3 {
        self.q.rotate(Vec3::Y)
    }

    pub(crate) fn forward(&self) -> Vec3 {
        self.q.rotate(Vec3::Z)
    }

    pub(crate) fn left(&self) -> Vec3 {
        self.q.rotate(Vec3::X)
    }

    /// Body origin (on the ground plane between the axles at rest ride height).
    pub(crate) fn origin(&self) -> Vec3 {
        self.pos - self.q.rotate(Vec3::new(0.0, self.cog_y, 0.0))
    }

    /// Applies the world inverse inertia tensor to `t`.
    fn inv_inertia(&self, t: Vec3) -> Vec3 {
        self.q.rotate(self.q.inv_rotate(t).div_elem(self.inertia))
    }

    /// Effective inertia about a world unit axis.
    pub(crate) fn inertia_about(&self, axis: Vec3) -> f32 {
        let b = self.q.inv_rotate(axis);
        b.x * b.x * self.inertia.x + b.y * b.y * self.inertia.y + b.z * b.z * self.inertia.z
    }

    /// Steering lock for the current speed.
    fn lock(speed: f32) -> f32 {
        MAX_LOCK / (1.0 + speed.abs() / LOCK_HALF_SPEED)
    }

    /// Advances one fixed substep. `extra_torque` is a world torque from the director.
    #[expect(
        clippy::too_many_lines,
        reason = "one physics substep, kept linear for clarity"
    )]
    pub(crate) fn step(
        &mut self,
        g: &Ground<'_>,
        c: &Controls,
        extra_torque: Vec3,
        dt: f32,
        report: &mut StepReport,
    ) {
        report.wheels_on_ground = 0;
        report.body_contacts = 0;
        report.terrain_impact = None;
        report.props.clear();
        report.knocked.clear();

        let up = self.up();
        let fwd = self.forward();
        let left = self.left();
        let v_fwd = self.v.dot(fwd);
        let mut force = Vec3::new(0.0, -GRAVITY * self.mass, 0.0);
        let mut torque = extra_torque;

        let reverse =
            c.allow_reverse && c.brake > 0.05 && c.throttle < 0.05 && v_fwd < 1.0 && !c.handbrake;
        let (drive_total, brake_total) = if reverse {
            let f = -c.brake * self.mass * 5.0 * (1.0 - smoothstep(8.0, 11.0, -v_fwd));
            (f, 0.0)
        } else {
            let fade = 1.0 - smoothstep(0.92 * self.top_speed, self.top_speed, v_fwd);
            let f = c.throttle * self.max_drive.min(self.power / v_fwd.max(1.0)) * fade;
            (f, c.brake * self.mass * 9.0)
        };
        let steer_angle = c.steer.clamp(-1.0, 1.0) * Self::lock(v_fwd);
        let mut comps = [0.0f32; 4];

        for (i, (wheel, comp_out)) in self.wheels.iter_mut().zip(comps.iter_mut()).enumerate() {
            let front = i < 2;
            wheel.steer = if front { steer_angle } else { 0.0 };
            wheel.lateral_speed = 0.0;
            if up.y < 0.1 {
                wheel.grounded = false;
                wheel.compression = 0.0;
                continue;
            }
            let anchor = self.pos + self.q.rotate(wheel.anchor);
            let d = -up;
            let mut t = (anchor.y - g.height(anchor.x, anchor.z)) / up.y;
            for _ in 0..2 {
                let p = anchor + d * t;
                t += (p.y - g.height(p.x, p.z)) / up.y;
            }
            let max_len = self.travel + self.wheel_r;
            let comp = max_len - t;
            if comp <= 0.0 || t < -0.5 {
                wheel.grounded = false;
                wheel.compression = 0.0;
                continue;
            }
            wheel.grounded = true;
            report.wheels_on_ground += 1;
            let contact = anchor + d * t;
            let (_, n) = g.sample(contact.x, contact.z);
            let v_anchor = self.v + self.w.cross(anchor - self.pos);
            let comp_rate = v_anchor.dot(d);
            let c_eff = comp.min(self.travel);
            let extra = (comp - self.travel).max(0.0);
            wheel.compression = c_eff;
            *comp_out = c_eff;
            let fs = (self.spring * c_eff + self.damper * comp_rate + self.spring * 8.0 * extra)
                .clamp(0.0, 5.0 * self.mass * GRAVITY);
            let centre = contact - d * self.wheel_r;
            force += up * fs;
            torque += (centre - self.pos).cross(up * fs);

            // Tyre forces in the ground plane.
            let load = fs.min(0.9 * self.mass * GRAVITY);
            let surf = g.surface(contact.x, contact.z);
            wheel.surface = surf;
            let (mu_s, crr) = surface_friction(surf);
            let mu = mu_s * self.grip;
            let heading = fwd * cos(wheel.steer) + left * sin(wheel.steer);
            let f_dir = (heading - n * heading.dot(n)).normalize_or(fwd);
            let s_dir = n.cross(f_dir);
            let vp = self.v + self.w.cross(contact - self.pos);
            let vl = vp.dot(f_dir);
            let vs = vp.dot(s_dir);
            wheel.lateral_speed = vs;
            let share = if front {
                FRONT_DRIVE * 0.5
            } else {
                (1.0 - FRONT_DRIVE) * 0.5
            };
            let brake_share = if front { 0.3 } else { 0.2 };
            let sat = (vl / 0.3).clamp(-1.0, 1.0);
            let mut fx = drive_total * share
                - brake_total * brake_share * sat
                - crr * load * (vl / 0.5).clamp(-1.0, 1.0);
            let mut lat_grip = 1.0;
            let rear_locked = c.handbrake && !front;
            if rear_locked {
                fx -= 0.6 * mu * load * sat;
                lat_grip = 0.45;
            }
            let alpha = atan2(vs, vl.abs().max(SLIP_REGULARISE));
            let x = alpha / SLIP_PEAK;
            let curve = if x.abs() <= 1.0 {
                x
            } else {
                x.signum() * (1.0 - 0.15 * (x.abs() - 1.0).min(1.0))
            };
            let mut fy = -mu * lat_grip * load * curve;
            let limit = mu * load;
            let total = sqrt(fx * fx + fy * fy);
            if total > limit && total > 0.0 {
                let k = limit / total;
                fx *= k;
                fy *= k;
            }
            let lever = (self.pos - contact).dot(up) * (1.0 - self.roll_lever);
            let apply = contact + up * lever;
            let tf = f_dir * fx + s_dir * fy;
            force += tf;
            torque += (apply - self.pos).cross(tf);

            wheel.spin_rate = if rear_locked { 0.0 } else { vl / self.wheel_r };
        }

        // Anti-roll bars.
        for (a, b) in [(0usize, 1usize), (2, 3)] {
            if self.wheels[a].grounded && self.wheels[b].grounded {
                let f = ANTI_ROLL * self.spring * (comps[a] - comps[b]);
                let pa = self.pos + self.q.rotate(self.wheels[a].anchor);
                let pb = self.pos + self.q.rotate(self.wheels[b].anchor);
                torque += (pa - self.pos).cross(up * f) + (pb - self.pos).cross(up * -f);
            }
        }

        // Aerodynamic drag.
        let speed = self.v.length();
        force += self.v * (-0.5 * AIR_DENSITY * DRAG_AREA * speed);

        // Stability assist: the yaw damping a sober car would get, scaled by the stein model.
        if report.wheels_on_ground >= 2 {
            let iy = self.inertia_about(up);
            let yaw_rate = self.w.dot(up);
            let kin = v_fwd * sin(steer_angle) / self.wheelbase;
            torque += up * (-c.assist * YAW_DAMPING * iy * (yaw_rate - kin));
        }

        // Mid-air authority for tricks.
        if c.air_control && report.wheels_on_ground == 0 {
            let ir = self.inertia_about(fwd);
            let ip = self.inertia_about(left);
            let iy = self.inertia_about(up);
            // Small corrections do nothing; only a deliberate input rotates the car.
            let dz = |x: f32| (x.abs() - AIR_DEADZONE).max(0.0) / (1.0 - AIR_DEADZONE) * x.signum();
            let steer = dz(c.steer);
            let pitch = dz(c.brake) - dz(c.throttle);
            if c.handbrake {
                torque += up * (steer * AIR_YAW_AUTHORITY * iy);
            } else {
                torque += fwd * (-steer * AIR_AUTHORITY * ir);
            }
            torque += left * (pitch * AIR_AUTHORITY * ip);
            // Without input the body keeps its attitude better than a free brick would.
            let wr = self.w.dot(fwd);
            let wp = self.w.dot(left);
            if steer == 0.0 || c.handbrake {
                torque += fwd * (-AIR_DAMPING * ir * wr);
            }
            if pitch == 0.0 {
                torque += left * (-AIR_DAMPING * ip * wp);
            }
        }

        // Integrate velocities.
        self.v += force * (self.inv_mass * dt);
        let wb = self.q.inv_rotate(self.w);
        let gyro = wb.cross(wb.mul_elem(self.inertia));
        let tb = self.q.inv_rotate(torque) - gyro;
        self.w += self.q.rotate(tb.div_elem(self.inertia)) * dt;

        self.collect_contacts(g, report);
        self.solve_contacts(dt);

        // Integrate positions.
        self.pos += self.v * dt;
        self.q = self.q.integrate(self.w, dt);

        for wheel in &mut self.wheels {
            if !wheel.grounded {
                if up.y < 0.0 {
                    // Inverted: nothing on the ground drives the wheels any more.
                    wheel.spin_rate = decay_spin(wheel.spin_rate, INVERTED_SPIN_TAU, dt);
                } else if c.throttle > 0.05 {
                    // Off the ground with throttle held, the driven wheels run up.
                    let target = c.throttle * AIR_SPIN_RATE;
                    wheel.spin_rate += (target - wheel.spin_rate) * (1.5 * dt);
                } else {
                    wheel.spin_rate = decay_spin(wheel.spin_rate, 4.0, dt);
                }
            }
            wheel.spin += wheel.spin_rate * dt;
        }
    }

    fn collect_contacts(&mut self, g: &Ground<'_>, report: &mut StepReport) {
        self.contacts.clear();
        let mut hardest: Option<(f32, u8, Vec3, Vec3)> = None;
        for k in 0..self.points.len() {
            let (pb, mu) = self.points[k];
            let r = self.q.rotate(pb);
            let p = self.pos + r;
            let (h, n) = g.sample(p.x, p.z);
            let depth = h - p.y;
            if depth <= 0.0 {
                continue;
            }
            report.body_contacts += 1;
            let pen = (depth * n.y).min(0.3);
            let vp = self.v + self.w.cross(r);
            let vn = vp.dot(n);
            if vn < 0.0 && hardest.is_none_or(|hh| -vn > hh.0) {
                hardest = Some((-vn, g.surface(p.x, p.z), p, pb));
            }
            self.push_contact(r, n, pen, mu, 0.05);
        }
        report.terrain_impact = hardest;

        // Solid props and the lodge building against a capsule along the body axis.
        let fwd = self.forward();
        let half = (self.length - self.width) * 0.5;
        let a = self.pos + fwd * half;
        let b = self.pos - fwd * half;
        let rc = self.width * 0.5;
        let course = g.course;
        let mut near = std::mem::take(&mut self.near);
        course.props_near(self.pos.x, self.pos.z, self.length * 0.5 + 3.0, &mut near);
        let props = course.props();
        for &idx in &near {
            let prop = props[idx as usize];
            let kind = prop.prop_kind();
            let inter = kind.interaction();
            if inter == Interaction::Dodges {
                continue;
            }
            let rp = kind.radius() * prop.scale;
            let base = prop.pos[1];
            let top = base + kind.height() * prop.scale;
            let centre = Vec3::new(prop.pos[0], 0.0, prop.pos[2]);
            let (q, dist) = closest_xz(a, b, centre);
            if dist >= rp + rc || q.y < base - 0.6 || q.y > top + 0.4 {
                continue;
            }
            match inter {
                Interaction::Knocked => report.knocked.push(idx),
                _ => {
                    let e = if kind == PropKind::Cart { 0.15 } else { 0.3 };
                    self.solid_contact(q, centre, dist, rp, rc, e, Some(idx), report);
                }
            }
        }
        self.near = near;
        for &(bx, bz, br) in &course.blockers {
            let centre = Vec3::new(bx, 0.0, bz);
            let (q, dist) = closest_xz(a, b, centre);
            if dist < br + rc {
                self.solid_contact(q, centre, dist, br, rc, 0.2, None, report);
            }
        }
    }

    #[expect(
        clippy::too_many_arguments,
        reason = "internal helper with one call pattern"
    )]
    fn solid_contact(
        &mut self,
        q: Vec3,
        centre: Vec3,
        dist: f32,
        rp: f32,
        rc: f32,
        restitution: f32,
        prop: Option<u32>,
        report: &mut StepReport,
    ) {
        let f = self.forward();
        let fallback = Vec3::new(-f.x, 0.0, -f.z).normalize_or(Vec3::X);
        let n = Vec3::new(q.x - centre.x, 0.0, q.z - centre.z).normalize_or(fallback);
        let pen = (rp + rc - dist).min(0.5);
        let point = Vec3::new(q.x, q.y, q.z) - n * rc;
        let r = point - self.pos;
        let vp = self.v + self.w.cross(r);
        let closing = -vp.dot(n);
        report.props.push(PropContact {
            prop,
            closing_speed: closing,
            dir_body: self.q.inv_rotate(-n),
            point,
        });
        self.push_contact(r, n, pen, 0.25, restitution);
    }

    fn push_contact(&mut self, r: Vec3, n: Vec3, pen: f32, mu: f32, restitution: f32) {
        let t1 = if n.y.abs() < 0.9 {
            n.cross(Vec3::Y).normalize_or(Vec3::X)
        } else {
            n.cross(Vec3::X).normalize_or(Vec3::Z)
        };
        let t2 = n.cross(t1);
        let k = |dir: Vec3| -> f32 {
            let rn = r.cross(dir);
            self.inv_mass + self.inv_inertia(rn).cross(r).dot(dir)
        };
        let vn = (self.v + self.w.cross(r)).dot(n);
        let bounce = if vn < -1.5 { -vn * restitution } else { 0.0 };
        let bias = (BAUMGARTE * 120.0 * (pen - SLOP).max(0.0)).min(MAX_CORRECTION);
        self.contacts.push(Contact {
            r,
            n,
            t1,
            t2,
            kn: k(n),
            kt1: k(t1),
            kt2: k(t2),
            target: bounce.max(bias),
            mu,
            ln: 0.0,
            lt1: 0.0,
            lt2: 0.0,
        });
    }

    fn solve_contacts(&mut self, _dt: f32) {
        if self.contacts.is_empty() {
            return;
        }
        let mut contacts = std::mem::take(&mut self.contacts);
        for _ in 0..SOLVER_ITERATIONS {
            for c in &mut contacts {
                let vp = self.v + self.w.cross(c.r);
                let vn = vp.dot(c.n);
                let d = (c.target - vn) / c.kn;
                let ln = (c.ln + d).max(0.0);
                let dl = ln - c.ln;
                c.ln = ln;
                self.apply_rel(c.n * dl, c.r);

                let max_f = c.mu * c.ln;
                let vp = self.v + self.w.cross(c.r);
                let d1 = -vp.dot(c.t1) / c.kt1;
                let l1 = (c.lt1 + d1).clamp(-max_f, max_f);
                let dl1 = l1 - c.lt1;
                c.lt1 = l1;
                let vp = self.v + self.w.cross(c.r);
                let d2 = -vp.dot(c.t2) / c.kt2;
                let l2 = (c.lt2 + d2).clamp(-max_f, max_f);
                let dl2 = l2 - c.lt2;
                c.lt2 = l2;
                self.apply_rel(c.t1 * dl1 + c.t2 * dl2, c.r);
            }
        }
        contacts.clear();
        self.contacts = contacts;
    }

    fn apply_rel(&mut self, j: Vec3, r: Vec3) {
        self.v += j * self.inv_mass;
        self.w += self.inv_inertia(r.cross(j));
    }

    /// Records each wheel's spin rate as the start of the post-wreck spin-down.
    pub(crate) fn begin_spin_down(&mut self) {
        for wheel in &mut self.wheels {
            wheel.spin_down_rate = wheel.spin_rate.abs() / WRECK_SPIN_DOWN;
        }
    }

    /// Spins every wheel down linearly so it stops `WRECK_SPIN_DOWN` after the wreck.
    pub(crate) fn spin_down(&mut self, dt: f32) {
        for wheel in &mut self.wheels {
            let r = wheel.spin_rate;
            let step = wheel.spin_down_rate * dt;
            wheel.spin_rate = if r.abs() <= step {
                0.0
            } else {
                r - step * r.signum()
            };
            wheel.spin += wheel.spin_rate * dt;
        }
    }

    /// True when every wheel has stopped.
    pub(crate) fn wheels_stopped(&self) -> bool {
        self.wheels.iter().all(|w| w.spin_rate == 0.0)
    }

    pub(crate) fn is_finite(&self) -> bool {
        self.pos.is_finite() && self.q.is_finite() && self.v.is_finite() && self.w.is_finite()
    }
}

/// Exponential spin decay with a small linear floor so it reaches exactly zero.
fn decay_spin(rate: f32, tau: f32, dt: f32) -> f32 {
    let r = rate * exp(-dt / tau);
    let floor = 0.4 * dt;
    if r.abs() <= floor {
        0.0
    } else {
        r - floor * r.signum()
    }
}

/// Closest point on segment `a..b` to `p` in the XZ plane, and the horizontal distance.
fn closest_xz(a: Vec3, b: Vec3, p: Vec3) -> (Vec3, f32) {
    let ab = Vec3::new(b.x - a.x, 0.0, b.z - a.z);
    let ap = Vec3::new(p.x - a.x, 0.0, p.z - a.z);
    let l2 = ab.length_sq();
    let t = if l2 > 1e-6 {
        (ap.dot(ab) / l2).clamp(0.0, 1.0)
    } else {
        0.0
    };
    let q = a + (b - a) * t;
    let dx = q.x - p.x;
    let dz = q.z - p.z;
    (q, sqrt(dx * dx + dz * dz))
}
