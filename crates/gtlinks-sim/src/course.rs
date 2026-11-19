//! Procedural course: a mountainside carrying nine linked golf holes and a finale arena.

use serde::Serialize;

use crate::math::{atan2, cos, lerp, sin, smoothstep, sqrt};
use crate::rng::Rng;
use crate::terrain::{
    Bunker, CORRIDOR_MARGIN, Heightfield, Pond, Ramp, Rect, TABLE_LEN, TABLE_Z0, Table, TeeBox,
    TerrainModel, node_x, node_z, normal_from_gradient,
};
use crate::{CELL, NX, NZ, X_MIN, Z_MAX};

/// Height of the summit plateau, m.
const SUMMIT_H: f32 = 560.0;
/// Total drop from the lodge (z = 40) to the bottom of the world (z = 2560), m.
const TOTAL_DROP: f32 = 520.0;
/// Start pose position on the lodge apron.
const START_X: f32 = 4.0;
/// Start pose z.
const START_Z: f32 = 40.0;
/// Lodge terrace centre.
const LODGE_X: f32 = -26.0;
/// Lodge terrace centre z.
const LODGE_Z: f32 = 32.0;
/// First tee z.
const FIRST_TEE_Z: f32 = 110.0;
/// Last green z.
const LAST_GREEN_Z: f32 = 2360.0;
/// Finale arena centre z.
const ARENA_Z: f32 = 2470.0;
/// Finale arena radius, m.
pub(crate) const ARENA_R: f32 = 70.0;
/// Fairway half-width used on the links between holes, m.
const LINK_HALF_WIDTH: f32 = 9.0;

/// Surface ids from the contract.
pub mod surface {
    /// Rough grass.
    pub const ROUGH: u8 = 0;
    /// Fairway.
    pub const FAIRWAY: u8 = 1;
    /// Putting green.
    pub const GREEN: u8 = 2;
    /// Sand bunker.
    pub const BUNKER: u8 = 3;
    /// Tee box.
    pub const TEE: u8 = 4;
    /// Cart path (also the paved lodge apron).
    pub const CART_PATH: u8 = 5;
    /// Exposed rock.
    pub const ROCK: u8 = 6;
    /// Water.
    pub const WATER: u8 = 7;
}

/// Prop kinds from the contract.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum PropKind {
    /// Pine tree, solid.
    Pine = 0,
    /// Broadleaf tree, solid.
    Broadleaf = 1,
    /// Spectator: never collides, dodges, emits `NearMiss`.
    Spectator = 2,
    /// Flag pin, knocked over (`PropHit`).
    Flag = 3,
    /// Tee marker, knocked over.
    TeeMarker = 4,
    /// Golf cart, solid but light.
    Cart = 5,
    /// Sign, knocked over.
    Sign = 6,
    /// Rock, solid.
    Rock = 7,
}

impl PropKind {
    /// How the car interacts with this kind.
    pub fn interaction(self) -> Interaction {
        match self {
            PropKind::Pine | PropKind::Broadleaf | PropKind::Cart | PropKind::Rock => {
                Interaction::Solid
            }
            PropKind::Flag | PropKind::TeeMarker | PropKind::Sign => Interaction::Knocked,
            PropKind::Spectator => Interaction::Dodges,
        }
    }

    /// Collision radius for unit scale, m.
    pub(crate) fn radius(self) -> f32 {
        match self {
            PropKind::Pine => 0.45,
            PropKind::Broadleaf => 0.55,
            PropKind::Cart => 1.3,
            PropKind::Rock => 1.1,
            PropKind::Flag | PropKind::TeeMarker | PropKind::Sign => 0.35,
            PropKind::Spectator => 0.4,
        }
    }

    /// Collider height for unit scale, m.
    pub(crate) fn height(self) -> f32 {
        match self {
            PropKind::Pine | PropKind::Broadleaf => 12.0,
            PropKind::Cart => 1.9,
            PropKind::Rock => 1.2,
            PropKind::Flag => 2.3,
            PropKind::TeeMarker => 0.4,
            PropKind::Sign => 1.6,
            PropKind::Spectator => 1.8,
        }
    }
}

/// How a prop responds to the car.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Interaction {
    /// Blocks the car with a bounce and adds damage.
    Solid,
    /// Falls over without impeding the car.
    Knocked,
    /// Gets out of the way; never touched.
    Dodges,
}

/// A placed prop.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Prop {
    /// Prop kind id (see [`PropKind`]).
    pub kind: u8,
    /// Base position, world metres.
    pub pos: [f32; 3],
    /// Rotation about +Y.
    pub yaw: f32,
    /// Uniform scale.
    pub scale: f32,
}

impl Prop {
    /// Typed kind.
    pub fn prop_kind(&self) -> PropKind {
        match self.kind {
            0 => PropKind::Pine,
            1 => PropKind::Broadleaf,
            2 => PropKind::Spectator,
            3 => PropKind::Flag,
            4 => PropKind::TeeMarker,
            5 => PropKind::Cart,
            6 => PropKind::Sign,
            _ => PropKind::Rock,
        }
    }
}

/// A position and heading.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Pose {
    /// Position, world metres.
    pub pos: [f32; 3],
    /// Heading: yaw 0 faces +Z, positive yaw turns towards +X.
    pub yaw: f32,
}

/// One golf hole.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Hole {
    /// Index 0 to 8.
    pub index: u32,
    /// Par 3, 4 or 5.
    pub par: u32,
    /// Tee box centre.
    pub tee: [f32; 3],
    /// Green centre.
    pub green: [f32; 3],
    /// Green radius, m.
    pub green_radius: f32,
    /// Centreline from tee to green, about 10 m spacing.
    pub centreline: Vec<[f32; 3]>,
    /// Fairway half-width, m.
    pub fairway_half_width: f32,
}

/// The finale arena.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Finale {
    /// Arena centre on the ground.
    pub pos: [f32; 3],
    /// Arena radius, m.
    pub radius: f32,
    /// Index of the final ramp in the course's ramp list (additive field).
    pub ramp_index: usize,
}

/// Uniform bucket grid over the props for collision queries.
#[derive(Clone, Debug)]
struct PropGrid {
    cells: Vec<Vec<u32>>,
}

/// Prop grid cell size, m.
const PROP_CELL: f32 = 16.0;
const PROP_GX: usize = 41;
const PROP_GZ: usize = 161;

impl PropGrid {
    fn build(props: &[Prop]) -> Self {
        let mut cells = vec![Vec::new(); PROP_GX * PROP_GZ];
        for (i, p) in props.iter().enumerate() {
            if let Some(c) = Self::cell(p.pos[0], p.pos[2]) {
                cells[c].push(u32::try_from(i).unwrap_or(u32::MAX));
            }
        }
        Self { cells }
    }

    fn cell(x: f32, z: f32) -> Option<usize> {
        let gx = ((x - X_MIN) / PROP_CELL) as i32;
        let gz = (z / PROP_CELL) as i32;
        if x < X_MIN || z < 0.0 || gx >= PROP_GX as i32 || gz >= PROP_GZ as i32 {
            return None;
        }
        Some(gz as usize * PROP_GX + gx as usize)
    }

    fn query(&self, x: f32, z: f32, r: f32, out: &mut Vec<u32>) {
        out.clear();
        let gx0 = (((x - r - X_MIN) / PROP_CELL) as i32).max(0);
        let gx1 = (((x + r - X_MIN) / PROP_CELL) as i32).min(PROP_GX as i32 - 1);
        let gz0 = (((z - r) / PROP_CELL) as i32).max(0);
        let gz1 = (((z + r) / PROP_CELL) as i32).min(PROP_GZ as i32 - 1);
        if x + r < X_MIN || z + r < 0.0 {
            return;
        }
        for gz in gz0..=gz1 {
            for gx in gx0..=gx1 {
                out.extend_from_slice(&self.cells[gz as usize * PROP_GX + gx as usize]);
            }
        }
    }
}

/// Per-hole layout used by the simulation (tee position along the fall line).
#[derive(Clone, Copy, Debug)]
pub(crate) struct HoleSpan {
    pub(crate) tee_z: f32,
}

/// A generated course: terrain grid, surfaces, holes, props, ramps and finale arena.
///
/// Constant for a given seed. Cheap to clone (a few hundred kilobytes), so property tests
/// generate each seed once and clone it per run.
#[derive(Clone, Debug)]
pub struct Course {
    seed: u32,
    pub(crate) model: TerrainModel,
    field: Heightfield,
    surfaces: Vec<u8>,
    holes: Vec<Hole>,
    pub(crate) spans: Vec<HoleSpan>,
    props: Vec<Prop>,
    ramps: Vec<Ramp>,
    start: Pose,
    lodge: Pose,
    finale: Finale,
    grid: PropGrid,
    /// Static obstacles that are not props (the lodge building): (x, z, radius).
    pub(crate) blockers: Vec<(f32, f32, f32)>,
}

#[derive(Serialize)]
struct CourseJson<'a> {
    seed: u32,
    start: &'a Pose,
    lodge: &'a Pose,
    holes: &'a [Hole],
    props: &'a [Prop],
    ramps: &'a [Ramp],
    finale: &'a Finale,
}

impl Course {
    /// Generates the course for `seed`. Deterministic.
    pub fn generate(seed: u32) -> Course {
        generate(seed)
    }

    /// The seed this course was generated from.
    pub fn seed(&self) -> u32 {
        self.seed
    }

    /// The course as the contract's JSON document.
    pub fn to_json(&self) -> String {
        let doc = CourseJson {
            seed: self.seed,
            start: &self.start,
            lodge: &self.lodge,
            holes: &self.holes,
            props: &self.props,
            ramps: &self.ramps,
            finale: &self.finale,
        };
        serde_json::to_string(&doc).unwrap_or_else(|_| String::from("{}"))
    }

    /// Node heights, `NX * NZ`, row-major `iz * NX + ix`.
    pub fn heightfield(&self) -> &[f32] {
        &self.field.heights
    }

    /// Node surface ids, same layout as [`Course::heightfield`].
    pub fn surface_map(&self) -> &[u8] {
        &self.surfaces
    }

    /// Height of the triangulated terrain alone (no ramps).
    pub fn terrain_height(&self, x: f32, z: f32) -> f32 {
        self.field.sample(&self.model, x, z).0
    }

    /// Terrain height plus the course's ramps.
    pub fn height_at(&self, x: f32, z: f32) -> f32 {
        self.sample(x, z, None).0
    }

    /// Unit surface normal including ramps, as `[x, y, z]`.
    pub fn normal_at(&self, x: f32, z: f32) -> [f32; 3] {
        let (_, gx, gz) = self.sample(x, z, None);
        normal_from_gradient(gx, gz).to_array()
    }

    /// Height and gradient including the course ramps and an optional extra ramp.
    pub(crate) fn sample(&self, x: f32, z: f32, extra: Option<&Ramp>) -> (f32, f32, f32) {
        let (h, gx, gz) = self.field.sample(&self.model, x, z);
        let mut best: Option<(f32, f32, f32)> = None;
        for r in self.ramps.iter().chain(extra) {
            if let Some(c) = r.contribution(x, z)
                && best.is_none_or(|b| c.0 > b.0)
            {
                best = Some(c);
            }
        }
        match best {
            Some((rh, rgx, rgz)) => (h + rh, gx + rgx, gz + rgz),
            None => (h, gx, gz),
        }
    }

    /// True if the point is on one of the course ramps or the extra ramp.
    pub(crate) fn on_ramp(&self, x: f32, z: f32, extra: Option<&Ramp>) -> bool {
        self.ramps
            .iter()
            .chain(extra)
            .any(|r| r.contribution(x, z).is_some())
    }

    /// Surface id at the nearest grid node (rough outside the world).
    pub fn surface_at(&self, x: f32, z: f32) -> u8 {
        let ix = ((x - X_MIN) / CELL + 0.5) as i32;
        let iz = (z / CELL + 0.5) as i32;
        if x < X_MIN - 2.0 || z < -2.0 || ix >= NX as i32 || iz >= NZ as i32 {
            return surface::ROUGH;
        }
        self.surfaces[iz.max(0) as usize * NX + ix.max(0) as usize]
    }

    /// The nine holes.
    pub fn holes(&self) -> &[Hole] {
        &self.holes
    }

    /// Every prop; event prop indices refer to this order.
    pub fn props(&self) -> &[Prop] {
        &self.props
    }

    /// Every ramp; the last is the final ramp in the arena.
    pub fn ramps(&self) -> &[Ramp] {
        &self.ramps
    }

    /// Car spawn pose on the lodge apron.
    pub fn start(&self) -> Pose {
        self.start
    }

    /// Lodge terrace pose.
    pub fn lodge(&self) -> Pose {
        self.lodge
    }

    /// Finale arena.
    pub fn finale(&self) -> Finale {
        self.finale
    }

    /// Course centreline x at fall-line position `z` (continuous from apron to arena).
    pub fn path_x(&self, z: f32) -> f32 {
        self.model.path_x.at(z)
    }

    /// Slope dx/dz of the centreline at `z`.
    pub fn path_dx(&self, z: f32) -> f32 {
        self.model.path_dx.at(z)
    }

    /// Lateral distance from the centreline, positive towards +X.
    pub fn lateral_offset(&self, x: f32, z: f32) -> f32 {
        self.model.lateral(x, z)
    }

    /// Index of the hole whose stretch contains `z` (0 before the first tee).
    pub fn hole_at(&self, z: f32) -> usize {
        self.spans
            .iter()
            .rposition(|s| z >= s.tee_z - 2.0)
            .unwrap_or(0)
    }

    /// Indices of props within `r` of `(x, z)` (a superset; caller filters).
    pub(crate) fn props_near(&self, x: f32, z: f32, r: f32, out: &mut Vec<u32>) {
        self.grid.query(x, z, r, out);
    }

    /// True if `(x, z)` is on the lodge terrace or the start apron (with `margin`).
    pub fn on_pad(&self, x: f32, z: f32, margin: f32) -> bool {
        self.model.on_pad(x, z, margin)
    }

    /// True if `(x, z)` lies within `margin` of the lodge terrace footprint.
    pub fn in_lodge_footprint(&self, x: f32, z: f32, margin: f32) -> bool {
        (x - self.lodge.pos[0]).abs() <= 12.0 + margin
            && (z - self.lodge.pos[2]).abs() <= 7.0 + margin
    }

    /// True if `(x, z)` lies within `margin` of the start apron (the car's spawn area).
    pub fn on_start_apron(&self, x: f32, z: f32, margin: f32) -> bool {
        (x - self.start.pos[0]).abs() <= 6.0 + margin
            && (z - self.start.pos[2]).abs() <= 10.0 + margin
    }
}

/// Integrates the fall-line slope into the base height profile.
fn build_profile(rng: &mut Rng) -> Table {
    let la = rng.range(500.0, 800.0);
    let lb = rng.range(170.0, 260.0);
    let pa = rng.range(0.0, std::f32::consts::TAU);
    let pb = rng.range(0.0, std::f32::consts::TAU);
    let arena_in = ARENA_Z - ARENA_R;
    let slope = |z: f32| -> f32 {
        let m = 1.0
            + 0.28 * sin(std::f32::consts::TAU * z / la + pa)
            + 0.12 * sin(std::f32::consts::TAU * z / lb + pb);
        let ramp_in = smoothstep(50.0, 150.0, z);
        let arena = 1.0
            - 0.9
                * smoothstep(arena_in - 60.0, arena_in, z)
                * (1.0 - smoothstep(ARENA_Z + ARENA_R, ARENA_Z + ARENA_R + 60.0, z));
        m * ramp_in * arena
    };
    let mut cum = vec![0.0f32; TABLE_LEN];
    let mut acc = 0.0f32;
    for (i, c) in cum.iter_mut().enumerate().skip(1) {
        let z = TABLE_Z0 + i as f32;
        acc += 0.5 * (slope(z - 1.0) + slope(z));
        *c = acc;
    }
    let idx = |z: f32| ((z - TABLE_Z0) as usize).min(TABLE_LEN - 1);
    let span = cum[idx(Z_MAX)] - cum[idx(START_Z)];
    let k = TOTAL_DROP / span;
    let c0 = cum[idx(START_Z)];
    Table::from_vec(
        cum.iter()
            .map(|c| SUMMIT_H - k * (c - c0).max(0.0))
            .collect(),
    )
}

struct Layout {
    pars: Vec<u32>,
    tee_z: Vec<f32>,
    green_z: Vec<f32>,
    green_r: Vec<f32>,
    half_w: Vec<f32>,
}

fn layout_holes(rng: &mut Rng) -> Layout {
    let mut pars: Vec<u32> = (0..9)
        .map(|_| {
            let r = rng.f32();
            if r < 0.22 {
                3
            } else if r < 0.78 {
                4
            } else {
                5
            }
        })
        .collect();
    if !pars.contains(&3) {
        let i = rng.below(9) as usize;
        pars[i] = 3;
    }
    if !pars.contains(&5) {
        let i = loop {
            let i = rng.below(9) as usize;
            if pars[i] != 3 {
                break i;
            }
        };
        pars[i] = 5;
    }
    let weights: Vec<f32> = pars
        .iter()
        .map(|p| {
            let w = match p {
                3 => 0.6,
                4 => 1.0,
                _ => 1.4,
            };
            w * rng.range(0.9, 1.1)
        })
        .collect();
    let green_r: Vec<f32> = (0..9).map(|_| rng.range(12.0, 16.0)).collect();
    let gaps: Vec<f32> = (0..8).map(|i| green_r[i] + rng.range(14.0, 22.0)).collect();
    let total = LAST_GREEN_Z - FIRST_TEE_Z - gaps.iter().sum::<f32>();
    let wsum: f32 = weights.iter().sum();
    let mut tee_z = Vec::with_capacity(9);
    let mut green_z = Vec::with_capacity(9);
    let mut z = FIRST_TEE_Z;
    for i in 0..9 {
        tee_z.push(z);
        z += weights[i] / wsum * total;
        green_z.push(z);
        if i < 8 {
            z += gaps[i];
        }
    }
    let half_w = (0..9).map(|_| rng.range(18.0, 26.0)).collect();
    Layout {
        pars,
        tee_z,
        green_z,
        green_r,
        half_w,
    }
}

fn build_path(rng: &mut Rng, lay: &Layout) -> (Table, Table, Table, Table) {
    let a1 = rng.range(45.0, 85.0) * rng.sign();
    let l1 = rng.range(950.0, 1350.0);
    let p1 = rng.range(0.0, std::f32::consts::TAU);
    let a2 = rng.range(8.0, 16.0);
    let l2 = rng.range(380.0, 520.0);
    let p2 = rng.range(0.0, std::f32::consts::TAU);
    let dogs: Vec<f32> = (0..9)
        .map(|i| {
            let len = lay.green_z[i] - lay.tee_z[i];
            if rng.f32() < 0.6 {
                rng.sign() * rng.range(0.02, 0.06) * len
            } else {
                0.0
            }
        })
        .collect();
    let meander = |z: f32| -> f32 {
        let mut x = a1 * sin(std::f32::consts::TAU * z / l1 + p1)
            + a2 * sin(std::f32::consts::TAU * z / l2 + p2);
        for ((&t0, &t1), &dog) in lay.tee_z.iter().zip(&lay.green_z).zip(&dogs) {
            if z > t0 && z < t1 {
                let s = sin(std::f32::consts::PI * (z - t0) / (t1 - t0));
                x += dog * s * s;
            }
        }
        x
    };
    let arena_in = ARENA_Z - ARENA_R;
    let raw = |z: f32| lerp(START_X, meander(z), smoothstep(45.0, 190.0, z));
    let x_final = raw(arena_in - 40.0);
    let path = Table::from_fn(|z| {
        lerp(
            raw(z),
            x_final,
            smoothstep(arena_in - 90.0, arena_in - 20.0, z),
        )
    });
    let xs = path.values();
    let n = xs.len();
    let dx: Vec<f32> = (0..n)
        .map(|i| {
            let a = xs[i.saturating_sub(1)];
            let b = xs[(i + 1).min(n - 1)];
            let span = ((i + 1).min(n - 1) - i.saturating_sub(1)) as f32;
            (b - a) / span
        })
        .collect();
    // Curvature from a wide stencil keeps the bank smooth.
    let bank: Vec<f32> = (0..n)
        .map(|i| {
            let s = 12usize;
            let a = xs[i.saturating_sub(s)];
            let b = xs[(i + s).min(n - 1)];
            let c = xs[i];
            let k = (a + b - 2.0 * c) / (s * s) as f32;
            (k * 15.0).clamp(-0.06, 0.06)
        })
        .collect();
    // Smooth the bank so it never flips abruptly where the curvature changes sign.
    let bank: Vec<f32> = (0..n)
        .map(|i| {
            let lo = i.saturating_sub(40);
            let hi = (i + 40).min(n - 1);
            bank[lo..=hi].iter().sum::<f32>() / (hi - lo + 1) as f32
        })
        .collect();
    let hw_raw = |z: f32| -> f32 {
        if (ARENA_Z - z).abs() < ARENA_R + 10.0 {
            return 30.0;
        }
        for i in 0..9 {
            if z >= lay.tee_z[i] - 6.0 && z <= lay.green_z[i] + lay.green_r[i] {
                return lay.half_w[i];
            }
        }
        LINK_HALF_WIDTH
    };
    let raw_hw: Vec<f32> = (0..n).map(|i| hw_raw(TABLE_Z0 + i as f32)).collect();
    let hw: Vec<f32> = (0..n)
        .map(|i| {
            let lo = i.saturating_sub(15);
            let hi = (i + 15).min(n - 1);
            raw_hw[lo..=hi].iter().sum::<f32>() / (hi - lo + 1) as f32
        })
        .collect();
    (
        path,
        Table::from_vec(dx),
        Table::from_vec(bank),
        Table::from_vec(hw),
    )
}

/// Builds the whole course.
fn generate(seed: u32) -> Course {
    let seed64 = u64::from(seed);
    let mut rng = Rng::new(seed64, 0xC0_0125E);
    let profile = build_profile(&mut rng);
    let lay = layout_holes(&mut rng);
    let (path_x, path_dx, bank, half_width) = build_path(&mut rng, &lay);

    let arena_x = path_x.at(ARENA_Z);
    let pads = vec![
        // Lodge building and terrace.
        Rect {
            x0: LODGE_X - 22.0,
            x1: LODGE_X + 22.0,
            z0: 8.0,
            z1: LODGE_Z + 12.0,
        },
        // Start apron.
        Rect {
            x0: START_X - 10.0,
            x1: START_X + 10.0,
            z0: 24.0,
            z1: 62.0,
        },
    ];
    let mut model = TerrainModel {
        noise_seed: seed.wrapping_mul(0x9E37_79B9) ^ 0x2545_F491,
        profile,
        path_x,
        path_dx,
        bank,
        half_width,
        bunkers: Vec::new(),
        ponds: Vec::new(),
        tees: Vec::new(),
        pads,
        pad_h: 0.0,
        arena_x,
        arena_z: ARENA_Z,
        arena_r: ARENA_R,
    };

    // Tees: flat boxes slightly above the carved corridor.
    for i in 0..9 {
        let z = lay.tee_z[i];
        let x = model.path_x.at(z);
        let d = model.path_dx.at(z);
        let inv = 1.0 / sqrt(1.0 + d * d);
        let h = 0.2;
        model.tees.push(TeeBox {
            cx: x,
            cz: z,
            dx: d * inv,
            dz: inv,
            half_len: 7.0,
            half_w: 5.0,
            h,
        });
    }

    // Bunkers and ponds.
    for i in 0..9 {
        let (t0, t1) = (lay.tee_z[i], lay.green_z[i]);
        let hw = lay.half_w[i];
        let n = 2 + rng.below(4);
        for _ in 0..n {
            let ang = rng.range(0.0, std::f32::consts::PI);
            let (cx, cz) = if rng.f32() < 0.6 {
                let z = lerp(t0, t1, rng.range(0.3, 0.85));
                let lat = rng.sign() * rng.range(0.35, 0.95) * hw;
                (model.path_x.at(z) + lat, z)
            } else {
                let gx = model.path_x.at(t1);
                let r = lay.green_r[i] + rng.range(3.0, 6.0);
                let a = rng.range(-0.4, std::f32::consts::PI + 0.4);
                (gx + r * cos(a), t1 + r * sin(a) * 0.9)
            };
            model.bunkers.push(Bunker {
                cx,
                cz,
                ax: rng.range(4.0, 8.0),
                az: rng.range(2.5, 5.0),
                cs: cos(ang),
                sn: sin(ang),
                depth: 0.55,
            });
        }
        if rng.f32() < 0.3 {
            let z = lerp(t0, t1, rng.range(0.3, 0.7));
            let lat = rng.sign() * (hw + rng.range(16.0, 28.0));
            model.ponds.push(Pond {
                cx: model.path_x.at(z) + lat,
                cz: z,
                r: rng.range(8.0, 13.0),
                depth: 0.7,
            });
        }
    }

    model.pad_h = model.natural_height(START_X, START_Z);
    let field = Heightfield::build(&model);

    // Surfaces.
    let mut surfaces = vec![surface::ROUGH; NX * NZ];
    for iz in 0..NZ {
        for ix in 0..NX {
            let x = node_x(ix as i32);
            let z = node_z(iz as i32);
            let i = iz * NX + ix;
            surfaces[i] = classify(&model, &lay, &field, x, z, ix, iz);
        }
    }

    let ground = |x: f32, z: f32| field.sample(&model, x, z).0;

    // Ramps on or near the centreline.
    let mut ramps: Vec<Ramp> = Vec::new();
    for i in 0..9 {
        let (t0, t1) = (lay.tee_z[i], lay.green_z[i]);
        let n = 2 + rng.below(3);
        let mut placed = 0;
        let mut tries = 0;
        let mut last_z: Vec<f32> = Vec::new();
        while placed < n && tries < 40 {
            tries += 1;
            let z = lerp(t0, t1, rng.range(0.12, 0.88));
            if z < t0 + 30.0 || z > t1 - lay.green_r[i] - 25.0 {
                continue;
            }
            if last_z.iter().any(|&q| (q - z).abs() < 40.0) {
                continue;
            }
            let d = model.path_dx.at(z);
            let yaw = atan2(d, 1.0);
            let off = rng.range(-1.5, 1.5);
            let x = model.path_x.at(z) + off * cos(yaw);
            let zz = z - off * sin(yaw);
            if model
                .bunkers
                .iter()
                .any(|b| (b.cx - x).abs() < 14.0 && (b.cz - zz).abs() < 22.0)
            {
                continue;
            }
            ramps.push(Ramp {
                pos: [x, ground(x, zz), zz],
                yaw,
                length: rng.range(10.0, 12.5),
                width: rng.range(8.0, 10.0),
                height: rng.range(1.4, 2.0),
            });
            last_z.push(z);
            placed += 1;
        }
    }
    // The final ramp in the arena.
    let fz = ARENA_Z - 28.0;
    let fx = model.path_x.at(fz);
    let final_ramp = Ramp {
        pos: [fx, ground(fx, fz), fz],
        yaw: atan2(model.path_dx.at(fz), 1.0),
        length: 14.0,
        width: 10.0,
        height: 3.0,
    };
    ramps.push(final_ramp);
    let ramp_index = ramps.len() - 1;

    let props = place_props(&mut rng, &model, &lay, &ramps, &ground);

    let holes = (0..9)
        .map(|i| {
            let tee = [model.path_x.at(lay.tee_z[i]), 0.0, lay.tee_z[i]];
            let green = [model.path_x.at(lay.green_z[i]), 0.0, lay.green_z[i]];
            let mut centreline = Vec::new();
            let mut z = lay.tee_z[i];
            while z < lay.green_z[i] {
                let x = model.path_x.at(z);
                centreline.push([x, ground(x, z), z]);
                let d = model.path_dx.at(z);
                z += 10.0 / sqrt(1.0 + d * d);
            }
            centreline.push([green[0], ground(green[0], green[2]), green[2]]);
            Hole {
                index: u32::try_from(i).unwrap_or(0),
                par: lay.pars[i],
                tee: [tee[0], ground(tee[0], tee[2]), tee[2]],
                green: [green[0], ground(green[0], green[2]), green[2]],
                green_radius: lay.green_r[i],
                centreline,
                fairway_half_width: lay.half_w[i],
            }
        })
        .collect();
    let spans = (0..9)
        .map(|i| HoleSpan {
            tee_z: lay.tee_z[i],
        })
        .collect();

    let grid = PropGrid::build(&props);
    let blockers = vec![
        (LODGE_X - 10.0, LODGE_Z - 12.0, 6.5),
        (LODGE_X, LODGE_Z - 12.0, 6.5),
        (LODGE_X + 10.0, LODGE_Z - 12.0, 6.5),
    ];
    Course {
        seed,
        start: Pose {
            pos: [START_X, ground(START_X, START_Z), START_Z],
            yaw: 0.0,
        },
        lodge: Pose {
            pos: [LODGE_X, ground(LODGE_X, LODGE_Z), LODGE_Z],
            yaw: 0.0,
        },
        finale: Finale {
            pos: [arena_x, ground(arena_x, ARENA_Z), ARENA_Z],
            radius: ARENA_R,
            ramp_index,
        },
        model,
        field,
        surfaces,
        holes,
        spans,
        props,
        ramps,
        grid,
        blockers,
    }
}

fn classify(
    model: &TerrainModel,
    lay: &Layout,
    field: &Heightfield,
    x: f32,
    z: f32,
    ix: usize,
    iz: usize,
) -> u8 {
    if model.on_pad(x, z, 0.0) {
        return surface::CART_PATH;
    }
    if model
        .ponds
        .iter()
        .any(|p| (x - p.cx) * (x - p.cx) + (z - p.cz) * (z - p.cz) < p.r * p.r)
    {
        return surface::WATER;
    }
    if model.bunkers.iter().any(|b| b.radius(x, z) < 0.95) {
        return surface::BUNKER;
    }
    for t in &model.tees {
        let (u, v) = t.local(x, z);
        if u.abs() <= t.half_len && v.abs() <= t.half_w {
            return surface::TEE;
        }
    }
    for i in 0..9 {
        let gx = model.path_x.at(lay.green_z[i]);
        let d2 = (x - gx) * (x - gx) + (z - lay.green_z[i]) * (z - lay.green_z[i]);
        if d2 < lay.green_r[i] * lay.green_r[i] {
            return surface::GREEN;
        }
        if d2 < (lay.green_r[i] + 3.0) * (lay.green_r[i] + 3.0) {
            return surface::FAIRWAY;
        }
    }
    let da2 = (x - model.arena_x) * (x - model.arena_x) + (z - model.arena_z) * (z - model.arena_z);
    if da2 < model.arena_r * model.arena_r {
        return surface::FAIRWAY;
    }
    let dl = model.lateral(x, z);
    for i in 0..9 {
        let (t0, t1) = (lay.tee_z[i], lay.green_z[i]);
        if z >= t0 + 18.0 && z <= t1 {
            let t = (z - t0) / (t1 - t0);
            let shape = 0.75 + 0.25 * sin(std::f32::consts::PI * t);
            if dl.abs() < lay.half_w[i] * shape {
                return surface::FAIRWAY;
            }
        }
    }
    let in_link = (z > 55.0 && z < lay.tee_z[0])
        || (0..8).any(|i| z > lay.green_z[i] && z < lay.tee_z[i + 1])
        || (z > lay.green_z[8] && z < model.arena_z - model.arena_r);
    if in_link && dl.abs() < 2.6 {
        return surface::CART_PATH;
    }
    // Steep, off-corridor ground shows as rock.
    let h = field.heights[iz * NX + ix];
    let hx = field.heights[iz * NX + (ix + 1).min(NX - 1)];
    let hz = field.heights[(iz + 1).min(NZ - 1) * NX + ix];
    let slope = sqrt((hx - h) * (hx - h) + (hz - h) * (hz - h)) / CELL;
    if slope > 0.38 && dl.abs() > model.half_width.at(z) + CORRIDOR_MARGIN {
        return surface::ROCK;
    }
    surface::ROUGH
}

#[expect(
    clippy::too_many_lines,
    reason = "one linear placement pass per prop family"
)]
fn place_props(
    rng: &mut Rng,
    model: &TerrainModel,
    lay: &Layout,
    ramps: &[Ramp],
    ground: &dyn Fn(f32, f32) -> f32,
) -> Vec<Prop> {
    let mut props: Vec<Prop> = Vec::new();
    let in_world = |x: f32, z: f32| {
        (X_MIN + 2.0..=-X_MIN - 2.0).contains(&x) && (2.0..=Z_MAX - 2.0).contains(&z)
    };
    let arena_d = |x: f32, z: f32| {
        let dx = x - model.arena_x;
        let dz = z - model.arena_z;
        sqrt(dx * dx + dz * dz)
    };
    let near_feature = |x: f32, z: f32, m: f32| -> bool {
        ramps.iter().any(|r| r.near(x, z, m))
            || model.bunkers.iter().any(|b| b.radius(x, z) < 1.3)
            || model
                .ponds
                .iter()
                .any(|p| sqrt((x - p.cx) * (x - p.cx) + (z - p.cz) * (z - p.cz)) < p.r + 3.0)
            || model.tees.iter().any(|t| {
                let (u, v) = t.local(x, z);
                u.abs() < t.half_len + 4.0 && v.abs() < t.half_w + 4.0
            })
            || (0..9).any(|i| {
                let gx = model.path_x.at(lay.green_z[i]);
                sqrt((x - gx) * (x - gx) + (z - lay.green_z[i]) * (z - lay.green_z[i]))
                    < lay.green_r[i] + 6.0
            })
    };
    // Solid props keep clear of the drivable corridor, the pads and the features.
    let solid_ok = |x: f32, z: f32| -> bool {
        in_world(x, z)
            && !model.on_pad(x, z, 12.0)
            && model.lateral(x, z).abs() > model.half_width.at(z) + CORRIDOR_MARGIN + 3.0
            && arena_d(x, z) > ARENA_R + 8.0
            && !near_feature(x, z, 12.0)
    };
    let push = |props: &mut Vec<Prop>, kind: PropKind, x: f32, z: f32, yaw: f32, scale: f32| {
        props.push(Prop {
            kind: kind as u8,
            pos: [x, ground(x, z), z],
            yaw,
            scale,
        });
    };

    // Tree lines along the rough, plus scattered forest further out.
    let mut z = 70.0;
    while z < Z_MAX - 6.0 {
        let d = model.path_dx.at(z);
        let stretch = sqrt(1.0 + d * d);
        let hwc = model.half_width.at(z) + CORRIDOR_MARGIN;
        for side in [-1.0f32, 1.0] {
            let rows = [
                (0.85, hwc + rng.range(5.0, 14.0)),
                (0.75, hwc + rng.range(16.0, 32.0)),
                (0.5, hwc + rng.range(34.0, 120.0)),
            ];
            for (p, dl) in rows {
                if rng.f32() >= p {
                    continue;
                }
                let zz = z + rng.range(-3.0, 3.0);
                let x = model.path_x.at(zz) + side * dl * stretch;
                if !solid_ok(x, zz) {
                    continue;
                }
                let kind = if rng.f32() < 0.6 {
                    PropKind::Pine
                } else {
                    PropKind::Broadleaf
                };
                let yaw = rng.range(0.0, std::f32::consts::TAU);
                let scale = rng.range(0.8, 1.35);
                push(&mut props, kind, x, zz, yaw, scale);
            }
        }
        z += rng.range(7.0, 12.0);
    }

    for i in 0..9 {
        let t = &model.tees[i];
        let (lx, lz) = (t.dz, -t.dx);
        let hw = lay.half_w[i];
        // Tee markers at the front of the tee box, a sign beside it.
        for s in [-1.0f32, 1.0] {
            let x = t.cx + t.dx * (t.half_len - 1.0) + lx * 3.5 * s;
            let z = t.cz + t.dz * (t.half_len - 1.0) + lz * 3.5 * s;
            push(&mut props, PropKind::TeeMarker, x, z, 0.0, 1.0);
        }
        let side = rng.sign();
        let x = t.cx + lx * 9.0 * side - t.dx * 2.0;
        let z = t.cz + lz * 9.0 * side - t.dz * 2.0;
        push(&mut props, PropKind::Sign, x, z, rng.range(-0.5, 0.5), 1.0);

        // Flag on the green.
        let gz = lay.green_z[i];
        let gx = model.path_x.at(gz);
        let gr = lay.green_r[i];
        let a = rng.range(0.0, std::f32::consts::TAU);
        let rr = rng.range(0.0, 0.4) * gr;
        push(
            &mut props,
            PropKind::Flag,
            gx + rr * cos(a),
            gz + rr * sin(a),
            0.0,
            1.0,
        );

        // Spectators near the tee and near the green, always off the line.
        let groups = [(t.cx, t.cz, 14.0f32, 4.0f32), (gx, gz, gr + 9.0, 8.0)];
        for (cx, cz, lat, along) in groups {
            for _ in 0..1 + rng.below(2) {
                let s = rng.sign();
                let gxp =
                    cx + lx * s * (lat + rng.range(0.0, 4.0)) + t.dx * rng.range(-along, along);
                let gzp =
                    cz + lz * s * (lat + rng.range(0.0, 4.0)) + t.dz * rng.range(-along, along);
                let n = 3 + rng.below(4);
                for _ in 0..n {
                    let x = gxp + rng.range(-2.5, 2.5);
                    let z = gzp + rng.range(-2.5, 2.5);
                    if in_world(x, z) && model.lateral(x, z).abs() > hw * 0.5 + 4.0 {
                        push(
                            &mut props,
                            PropKind::Spectator,
                            x,
                            z,
                            rng.range(0.0, std::f32::consts::TAU),
                            1.0,
                        );
                    }
                }
            }
        }

        // The odd golf cart, parked by the green.
        if rng.f32() < 0.5 {
            let s = rng.sign();
            let x = gx + lx * s * (gr + 14.0);
            let z = gz + lz * s * (gr + 14.0) - rng.range(0.0, 10.0);
            if solid_ok(x, z) {
                push(
                    &mut props,
                    PropKind::Cart,
                    x,
                    z,
                    rng.range(0.0, std::f32::consts::TAU),
                    1.0,
                );
            }
        }
        // Rocks in the rough.
        for _ in 0..2 + rng.below(3) {
            let z = lerp(lay.tee_z[i], gz, rng.f32());
            let d = model.path_dx.at(z);
            let dl = model.half_width.at(z) + CORRIDOR_MARGIN + rng.range(6.0, 40.0);
            let x = model.path_x.at(z) + rng.sign() * dl * sqrt(1.0 + d * d);
            if solid_ok(x, z) {
                push(
                    &mut props,
                    PropKind::Rock,
                    x,
                    z,
                    rng.range(0.0, std::f32::consts::TAU),
                    rng.range(0.7, 1.6),
                );
            }
        }
    }

    // Spectators at the arena edge, beside the run-out.
    for s in [-1.0f32, 1.0] {
        let cx = model.arena_x + s * (ARENA_R + 6.0);
        for _ in 0..5 {
            let x = cx + rng.range(-2.5, 2.5);
            let z = model.arena_z + rng.range(-10.0, 10.0);
            push(
                &mut props,
                PropKind::Spectator,
                x,
                z,
                rng.range(0.0, std::f32::consts::TAU),
                1.0,
            );
        }
    }
    props
}
