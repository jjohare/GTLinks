//! Analytic mountain terrain, its triangulated grid and ramp shapes.
//!
//! The generator evaluates [`TerrainModel::node_height`] only at grid nodes. Physics and
//! rendering then share the same triangulated surface: [`Heightfield::height`] interpolates
//! linearly inside the two triangles of each cell (split along the diagonal from `(ix, iz)` to
//! `(ix + 1, iz + 1)`). Outside the world extent the same analytic node function is evaluated
//! on the continuation of the lattice, so there is no seam at the edge.

use serde::Serialize;

use crate::math::{Vec3, cos, floor, lerp, sin, smoothstep, sqrt};
use crate::{CELL, NX, NZ, X_MIN};

/// First z covered by the precomputed per-metre tables.
pub(crate) const TABLE_Z0: f32 = -400.0;
/// Number of one-metre table entries (covers z up to 3000 m).
pub(crate) const TABLE_LEN: usize = 3401;

/// Lateral rise of the valley sides far from the course (dimensionless slope).
const VALLEY_SLOPE: f32 = 0.12;
/// Width over which the valley rise reaches its asymptotic slope, m.
const VALLEY_WIDTH: f32 = 80.0;
/// Amplitude of the off-course ridges, m.
const RIDGE_AMP: f32 = 3.0;
/// Wavelength of the off-course ridges, m.
const RIDGE_WAVELENGTH: f32 = 180.0;
/// Amplitude of the small rolling bumps, m.
const BUMP_AMP: f32 = 1.2;
/// Wavelength of the small rolling bumps, m.
const BUMP_WAVELENGTH: f32 = 42.0;
/// Fraction of the bumps that survives inside the carved corridor.
const CORRIDOR_BUMP: f32 = 0.25;
/// Extra half-width of the smooth carved corridor beyond the fairway, m.
pub(crate) const CORRIDOR_MARGIN: f32 = 6.0;
/// Blend distance from the carved corridor back to raw terrain, m.
const CORRIDOR_BLEND: f32 = 40.0;
/// Blend distance from the flat lodge and apron pads back to natural terrain, m.
const PAD_BLEND: f32 = 26.0;
/// Ramp side chamfer width, m (inside the drawn footprint).
const RAMP_CHAMFER: f32 = 1.0;
/// Length of the steep fall behind a ramp lip, m (behind the drawn wedge).
const RAMP_BACK: f32 = 0.7;

/// A function of z sampled every metre and linearly interpolated.
#[derive(Clone, Debug)]
pub(crate) struct Table {
    v: Vec<f32>,
}

impl Table {
    pub(crate) fn from_fn(mut f: impl FnMut(f32) -> f32) -> Self {
        let v = (0..TABLE_LEN).map(|i| f(TABLE_Z0 + i as f32)).collect();
        Self { v }
    }

    pub(crate) fn from_vec(v: Vec<f32>) -> Self {
        debug_assert_eq!(v.len(), TABLE_LEN, "table length");
        Self { v }
    }

    pub(crate) fn values(&self) -> &[f32] {
        &self.v
    }

    pub(crate) fn at(&self, z: f32) -> f32 {
        let g = (z - TABLE_Z0).clamp(0.0, (TABLE_LEN - 1) as f32);
        let i = (floor(g) as usize).min(TABLE_LEN - 2);
        let t = g - i as f32;
        lerp(self.v[i], self.v[i + 1], t)
    }
}

/// Elliptical sand bunker.
#[derive(Clone, Debug)]
pub(crate) struct Bunker {
    pub(crate) cx: f32,
    pub(crate) cz: f32,
    pub(crate) ax: f32,
    pub(crate) az: f32,
    pub(crate) cs: f32,
    pub(crate) sn: f32,
    pub(crate) depth: f32,
}

impl Bunker {
    /// Normalised elliptical radius (1 on the rim).
    pub(crate) fn radius(&self, x: f32, z: f32) -> f32 {
        let dx = x - self.cx;
        let dz = z - self.cz;
        let u = (dx * self.cs + dz * self.sn) / self.ax;
        let v = (-dx * self.sn + dz * self.cs) / self.az;
        sqrt(u * u + v * v)
    }
}

/// Round shallow pond.
#[derive(Clone, Debug)]
pub(crate) struct Pond {
    pub(crate) cx: f32,
    pub(crate) cz: f32,
    pub(crate) r: f32,
    pub(crate) depth: f32,
}

/// Flat raised tee box aligned with the course.
#[derive(Clone, Debug)]
pub(crate) struct TeeBox {
    pub(crate) cx: f32,
    pub(crate) cz: f32,
    /// Unit heading (x, z) down the hole.
    pub(crate) dx: f32,
    pub(crate) dz: f32,
    pub(crate) half_len: f32,
    pub(crate) half_w: f32,
    /// Height of the raise above the surrounding ground, m.
    pub(crate) h: f32,
}

impl TeeBox {
    /// Local (along, lateral) coordinates.
    pub(crate) fn local(&self, x: f32, z: f32) -> (f32, f32) {
        let rx = x - self.cx;
        let rz = z - self.cz;
        (rx * self.dx + rz * self.dz, rx * self.dz - rz * self.dx)
    }
}

/// Axis-aligned rectangle in the XZ plane.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Rect {
    pub(crate) x0: f32,
    pub(crate) x1: f32,
    pub(crate) z0: f32,
    pub(crate) z1: f32,
}

impl Rect {
    /// Distance outside the rectangle (0 inside).
    pub(crate) fn outside(&self, x: f32, z: f32) -> f32 {
        let dx = (self.x0 - x).max(x - self.x1).max(0.0);
        let dz = (self.z0 - z).max(z - self.z1).max(0.0);
        sqrt(dx * dx + dz * dz)
    }
}

/// Every parameter of the analytic terrain.
#[derive(Clone, Debug)]
pub(crate) struct TerrainModel {
    pub(crate) noise_seed: u32,
    /// Base height along the fall line.
    pub(crate) profile: Table,
    /// Course centreline x as a function of z.
    pub(crate) path_x: Table,
    /// dx/dz of the centreline.
    pub(crate) path_dx: Table,
    /// Bank slope of the carved corridor (positive lowers the +X side).
    pub(crate) bank: Table,
    /// Fairway half-width along the course.
    pub(crate) half_width: Table,
    pub(crate) bunkers: Vec<Bunker>,
    pub(crate) ponds: Vec<Pond>,
    pub(crate) tees: Vec<TeeBox>,
    pub(crate) pads: Vec<Rect>,
    pub(crate) pad_h: f32,
    pub(crate) arena_x: f32,
    pub(crate) arena_z: f32,
    pub(crate) arena_r: f32,
}

fn hash2(seed: u32, ix: i32, iz: i32) -> f32 {
    let mut h =
        seed ^ (ix as u32).wrapping_mul(0x27D4_EB2D) ^ (iz as u32).wrapping_mul(0x1656_67B1);
    h = (h ^ (h >> 15)).wrapping_mul(0x85EB_CA6B);
    h = (h ^ (h >> 13)).wrapping_mul(0xC2B2_AE35);
    h ^= h >> 16;
    ((h & 0x00FF_FFFF) as f32) * (2.0 / 16_777_215.0) - 1.0
}

/// Smooth value noise in [-1, 1] with unit lattice spacing.
fn value_noise(seed: u32, x: f32, z: f32) -> f32 {
    let fx = floor(x);
    let fz = floor(z);
    let ix = fx as i32;
    let iz = fz as i32;
    let tx = x - fx;
    let tz = z - fz;
    let qx = tx * tx * tx * (tx * (tx * 6.0 - 15.0) + 10.0);
    let qz = tz * tz * tz * (tz * (tz * 6.0 - 15.0) + 10.0);
    let a = hash2(seed, ix, iz);
    let b = hash2(seed, ix + 1, iz);
    let c = hash2(seed, ix, iz + 1);
    let d = hash2(seed, ix + 1, iz + 1);
    lerp(lerp(a, b, qx), lerp(c, d, qx), qz)
}

impl TerrainModel {
    /// Lateral distance from the centreline (positive towards +X), perpendicular to it.
    pub(crate) fn lateral(&self, x: f32, z: f32) -> f32 {
        let d = self.path_dx.at(z);
        (x - self.path_x.at(z)) / sqrt(1.0 + d * d)
    }

    fn bumps(&self, x: f32, z: f32) -> f32 {
        let s = 1.0 / BUMP_WAVELENGTH;
        value_noise(self.noise_seed ^ 0x5bd1, x * s, z * s) * 0.7
            + value_noise(self.noise_seed ^ 0x1b87, x * s * 2.1, z * s * 2.1) * 0.3
    }

    fn ridges(&self, x: f32, z: f32) -> f32 {
        let s = 1.0 / RIDGE_WAVELENGTH;
        let n = value_noise(self.noise_seed ^ 0x9e37, x * s, z * s * 0.6);
        let r = 1.0 - n.abs();
        r * r * 2.0 - 0.6
    }

    /// The carved corridor surface (smooth and banked) at a point.
    fn fair_height(&self, x: f32, z: f32) -> f32 {
        let dl = self.lateral(x, z);
        // The bank tilts the fairway only; beyond its edge the tilt stops growing.
        let hw = self.half_width.at(z);
        self.profile.at(z) - self.bank.at(z) * dl.clamp(-hw, hw)
            + CORRIDOR_BUMP * BUMP_AMP * self.bumps(x, z)
    }

    /// Terrain height before pads (used to choose the pad level).
    pub(crate) fn natural_height(&self, x: f32, z: f32) -> f32 {
        let base = self.profile.at(z);
        let dl = self.lateral(x, z);
        let valley = VALLEY_SLOPE * (sqrt(VALLEY_WIDTH * VALLEY_WIDTH + dl * dl) - VALLEY_WIDTH);
        let raw = base + valley + RIDGE_AMP * self.ridges(x, z) + BUMP_AMP * self.bumps(x, z);
        let hw = self.half_width.at(z) + CORRIDOR_MARGIN;
        let wc = smoothstep(hw + CORRIDOR_BLEND, hw, dl.abs());
        let mut h = lerp(raw, self.fair_height(x, z), wc);

        let dax = x - self.arena_x;
        let daz = z - self.arena_z;
        let da = sqrt(dax * dax + daz * daz);
        let wa = smoothstep(self.arena_r + 40.0, self.arena_r, da);
        if wa > 0.0 {
            h = lerp(h, base, wa);
        }

        for t in &self.tees {
            let (u, v) = t.local(x, z);
            let ou = (u.abs() - t.half_len).max(0.0);
            let ov = (v.abs() - t.half_w).max(0.0);
            let d = sqrt(ou * ou + ov * ov);
            if d < 4.0 {
                // A gentle raise that follows the slope; a level box would leave a lip.
                h += t.h * smoothstep(4.0, 0.0, d);
            }
        }
        for b in &self.bunkers {
            if (x - b.cx).abs() > b.ax.max(b.az) + 1.0 || (z - b.cz).abs() > b.ax.max(b.az) + 1.0 {
                continue;
            }
            let r = b.radius(x, z);
            if r < 1.15 {
                h -= b.depth * smoothstep(1.15, 0.55, r);
            }
        }
        for p in &self.ponds {
            let dx = x - p.cx;
            let dz = z - p.cz;
            let d = sqrt(dx * dx + dz * dz);
            if d < p.r + 4.0 {
                h -= p.depth * smoothstep(p.r + 4.0, p.r * 0.7, d);
            }
        }
        h
    }

    /// The analytic terrain height, the only function the grid ever samples.
    pub(crate) fn node_height(&self, x: f32, z: f32) -> f32 {
        let h = self.natural_height(x, z);
        let d = self
            .pads
            .iter()
            .map(|p| p.outside(x, z))
            .fold(f32::INFINITY, f32::min);
        if d < PAD_BLEND {
            lerp(h, self.pad_h, smoothstep(PAD_BLEND, 0.0, d))
        } else {
            h
        }
    }

    /// True when the point lies on a flattened pad (lodge terrace or start apron).
    pub(crate) fn on_pad(&self, x: f32, z: f32, margin: f32) -> bool {
        self.pads.iter().any(|p| p.outside(x, z) <= margin)
    }
}

/// The triangulated grid over the world extent, continued analytically beyond it.
#[derive(Clone, Debug)]
pub(crate) struct Heightfield {
    pub(crate) heights: Vec<f32>,
}

impl Heightfield {
    pub(crate) fn build(model: &TerrainModel) -> Self {
        let mut heights = Vec::with_capacity(NX * NZ);
        for iz in 0..NZ {
            for ix in 0..NX {
                heights.push(model.node_height(node_x(ix as i32), node_z(iz as i32)));
            }
        }
        Self { heights }
    }

    fn node(&self, model: &TerrainModel, ix: i32, iz: i32) -> f32 {
        if (0..NX as i32).contains(&ix) && (0..NZ as i32).contains(&iz) {
            self.heights[iz as usize * NX + ix as usize]
        } else {
            model.node_height(node_x(ix), node_z(iz))
        }
    }

    /// Height and gradient `(h, dh/dx, dh/dz)` of the triangulated surface.
    pub(crate) fn sample(&self, model: &TerrainModel, x: f32, z: f32) -> (f32, f32, f32) {
        let gx = (x - X_MIN) / CELL;
        let gz = z / CELL;
        let fx0 = floor(gx);
        let fz0 = floor(gz);
        let ix = fx0 as i32;
        let iz = fz0 as i32;
        let fx = gx - fx0;
        let fz = gz - fz0;
        let h00 = self.node(model, ix, iz);
        let h11 = self.node(model, ix + 1, iz + 1);
        if fx >= fz {
            // Triangle (0,0) (1,0) (1,1).
            let h10 = self.node(model, ix + 1, iz);
            let ax = h10 - h00;
            let az = h11 - h10;
            (h00 + ax * fx + az * fz, ax / CELL, az / CELL)
        } else {
            // Triangle (0,0) (0,1) (1,1).
            let h01 = self.node(model, ix, iz + 1);
            let ax = h11 - h01;
            let az = h01 - h00;
            (h00 + ax * fx + az * fz, ax / CELL, az / CELL)
        }
    }
}

/// World x of grid column `ix`.
pub(crate) fn node_x(ix: i32) -> f32 {
    X_MIN + CELL * ix as f32
}

/// World z of grid row `iz`.
pub(crate) fn node_z(iz: i32) -> f32 {
    CELL * iz as f32
}

/// A wedge ramp. `pos` is the centre of the low leading edge on the ground; the ramp rises
/// along its heading to `height` at `length`, matching the unit `ramp.glb` scaled by
/// `(width, height, length)` and rotated by `yaw` about +Y.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Ramp {
    /// Leading-edge centre, world metres.
    pub pos: [f32; 3],
    /// Heading: yaw 0 faces +Z, positive yaw turns towards +X.
    pub yaw: f32,
    /// Run length along the heading, m.
    pub length: f32,
    /// Width across the heading, m.
    pub width: f32,
    /// Height of the lip at the far end, m.
    pub height: f32,
}

impl Ramp {
    /// Unit heading in the XZ plane.
    pub(crate) fn dir(&self) -> (f32, f32) {
        (sin(self.yaw), cos(self.yaw))
    }

    /// Ramp height above the terrain and its gradient, if the point is on the ramp.
    pub(crate) fn contribution(&self, x: f32, z: f32) -> Option<(f32, f32, f32)> {
        let (dx, dz) = self.dir();
        let (lx, lz) = (dz, -dx);
        let rx = x - self.pos[0];
        let rz = z - self.pos[2];
        let u = rx * dx + rz * dz;
        let v = rx * lx + rz * lz;
        let hw = self.width * 0.5;
        if u <= 0.0 || u >= self.length + RAMP_BACK || v.abs() >= hw {
            return None;
        }
        let (top, dtop) = if u <= self.length {
            (self.height * u / self.length, self.height / self.length)
        } else {
            let k = (u - self.length) / RAMP_BACK;
            (self.height * (1.0 - k), -self.height / RAMP_BACK)
        };
        let sf_raw = (hw - v.abs()) / RAMP_CHAMFER;
        let (sf, dsf) = if sf_raw >= 1.0 {
            (1.0, 0.0)
        } else {
            (sf_raw, -v.signum() / RAMP_CHAMFER)
        };
        let h = top * sf;
        let dhdu = dtop * sf;
        let dhdv = top * dsf;
        Some((h, dhdu * dx + dhdv * lx, dhdu * dz + dhdv * lz))
    }

    /// True if `(x, z)` lies within `margin` of the ramp footprint.
    pub(crate) fn near(&self, x: f32, z: f32, margin: f32) -> bool {
        let (dx, dz) = self.dir();
        let rx = x - self.pos[0];
        let rz = z - self.pos[2];
        let u = rx * dx + rz * dz;
        let v = rx * dz - rz * dx;
        u > -margin && u < self.length + RAMP_BACK + margin && v.abs() < self.width * 0.5 + margin
    }
}

/// Surface normal from a height gradient.
pub(crate) fn normal_from_gradient(gx: f32, gz: f32) -> Vec3 {
    Vec3::new(-gx, 1.0, -gz).normalize_or(Vec3::Y)
}
