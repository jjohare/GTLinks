//! Minimal f32 vector and quaternion maths.
//!
//! Every transcendental function goes through `libm` so native builds and the shipped
//! WebAssembly perform bit-identical arithmetic.

use std::ops::{Add, AddAssign, Mul, Neg, Sub, SubAssign};

/// Sine via `libm`.
#[inline]
pub(crate) fn sin(x: f32) -> f32 {
    libm::sinf(x)
}

/// Cosine via `libm`.
#[inline]
pub(crate) fn cos(x: f32) -> f32 {
    libm::cosf(x)
}

/// Two-argument arctangent via `libm`.
#[inline]
pub(crate) fn atan2(y: f32, x: f32) -> f32 {
    libm::atan2f(y, x)
}

/// Natural exponential via `libm`.
#[inline]
pub(crate) fn exp(x: f32) -> f32 {
    libm::expf(x)
}

/// Natural logarithm via `libm`.
#[inline]
pub(crate) fn ln(x: f32) -> f32 {
    libm::logf(x)
}

/// Arc cosine via `libm`, with the argument clamped into the domain.
#[inline]
pub(crate) fn acos(x: f32) -> f32 {
    libm::acosf(x.clamp(-1.0, 1.0))
}

/// Arc sine via `libm`, with the argument clamped into the domain.
#[inline]
pub(crate) fn asin(x: f32) -> f32 {
    libm::asinf(x.clamp(-1.0, 1.0))
}

/// Square root via `libm` (correctly rounded, identical everywhere).
#[inline]
pub(crate) fn sqrt(x: f32) -> f32 {
    libm::sqrtf(x)
}

/// Floor via `libm`.
#[inline]
pub(crate) fn floor(x: f32) -> f32 {
    libm::floorf(x)
}

/// Hermite smoothstep from `e0` to `e1` (works for `e0 > e1` too).
#[inline]
pub(crate) fn smoothstep(e0: f32, e1: f32, x: f32) -> f32 {
    let t = ((x - e0) / (e1 - e0)).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

/// Linear interpolation.
#[inline]
pub(crate) fn lerp(a: f32, b: f32, t: f32) -> f32 {
    a + (b - a) * t
}

/// Three-component vector.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct Vec3 {
    pub(crate) x: f32,
    pub(crate) y: f32,
    pub(crate) z: f32,
}

impl Vec3 {
    pub(crate) const ZERO: Vec3 = Vec3::new(0.0, 0.0, 0.0);
    pub(crate) const X: Vec3 = Vec3::new(1.0, 0.0, 0.0);
    pub(crate) const Y: Vec3 = Vec3::new(0.0, 1.0, 0.0);
    pub(crate) const Z: Vec3 = Vec3::new(0.0, 0.0, 1.0);

    pub(crate) const fn new(x: f32, y: f32, z: f32) -> Self {
        Self { x, y, z }
    }

    pub(crate) fn dot(self, o: Vec3) -> f32 {
        self.x * o.x + self.y * o.y + self.z * o.z
    }

    pub(crate) fn cross(self, o: Vec3) -> Vec3 {
        Vec3::new(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )
    }

    pub(crate) fn length_sq(self) -> f32 {
        self.dot(self)
    }

    pub(crate) fn length(self) -> f32 {
        sqrt(self.length_sq())
    }

    /// Unit vector, or `fallback` when the length is negligible.
    pub(crate) fn normalize_or(self, fallback: Vec3) -> Vec3 {
        let l = self.length();
        if l > 1e-6 { self * (1.0 / l) } else { fallback }
    }

    pub(crate) fn lerp(self, o: Vec3, t: f32) -> Vec3 {
        self + (o - self) * t
    }

    /// Component-wise product.
    pub(crate) fn mul_elem(self, o: Vec3) -> Vec3 {
        Vec3::new(self.x * o.x, self.y * o.y, self.z * o.z)
    }

    /// Component-wise quotient.
    pub(crate) fn div_elem(self, o: Vec3) -> Vec3 {
        Vec3::new(self.x / o.x, self.y / o.y, self.z / o.z)
    }

    pub(crate) fn is_finite(self) -> bool {
        self.x.is_finite() && self.y.is_finite() && self.z.is_finite()
    }

    pub(crate) fn to_array(self) -> [f32; 3] {
        [self.x, self.y, self.z]
    }
}

impl Add for Vec3 {
    type Output = Vec3;
    fn add(self, o: Vec3) -> Vec3 {
        Vec3::new(self.x + o.x, self.y + o.y, self.z + o.z)
    }
}

impl Sub for Vec3 {
    type Output = Vec3;
    fn sub(self, o: Vec3) -> Vec3 {
        Vec3::new(self.x - o.x, self.y - o.y, self.z - o.z)
    }
}

impl Mul<f32> for Vec3 {
    type Output = Vec3;
    fn mul(self, s: f32) -> Vec3 {
        Vec3::new(self.x * s, self.y * s, self.z * s)
    }
}

impl Neg for Vec3 {
    type Output = Vec3;
    fn neg(self) -> Vec3 {
        Vec3::new(-self.x, -self.y, -self.z)
    }
}

impl AddAssign for Vec3 {
    fn add_assign(&mut self, o: Vec3) {
        *self = *self + o;
    }
}

impl SubAssign for Vec3 {
    fn sub_assign(&mut self, o: Vec3) {
        *self = *self - o;
    }
}

/// Unit quaternion `(x, y, z, w)`.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Quat {
    pub(crate) x: f32,
    pub(crate) y: f32,
    pub(crate) z: f32,
    pub(crate) w: f32,
}

impl Default for Quat {
    fn default() -> Self {
        Self::IDENTITY
    }
}

impl Quat {
    pub(crate) const IDENTITY: Quat = Quat {
        x: 0.0,
        y: 0.0,
        z: 0.0,
        w: 1.0,
    };

    /// Rotation by `angle` about the unit `axis`.
    pub(crate) fn from_axis_angle(axis: Vec3, angle: f32) -> Quat {
        let h = angle * 0.5;
        let s = sin(h);
        Quat {
            x: axis.x * s,
            y: axis.y * s,
            z: axis.z * s,
            w: cos(h),
        }
    }

    /// Heading rotation: yaw 0 faces +Z, positive yaw turns towards +X.
    pub(crate) fn from_yaw(yaw: f32) -> Quat {
        Quat::from_axis_angle(Vec3::Y, yaw)
    }

    pub(crate) fn mul(self, o: Quat) -> Quat {
        Quat {
            w: self.w * o.w - self.x * o.x - self.y * o.y - self.z * o.z,
            x: self.w * o.x + self.x * o.w + self.y * o.z - self.z * o.y,
            y: self.w * o.y - self.x * o.z + self.y * o.w + self.z * o.x,
            z: self.w * o.z + self.x * o.y - self.y * o.x + self.z * o.w,
        }
    }

    pub(crate) fn conj(self) -> Quat {
        Quat {
            x: -self.x,
            y: -self.y,
            z: -self.z,
            w: self.w,
        }
    }

    /// Rotates `v` from body to world frame.
    pub(crate) fn rotate(self, v: Vec3) -> Vec3 {
        let u = Vec3::new(self.x, self.y, self.z);
        let t = u.cross(v) * 2.0;
        v + t * self.w + u.cross(t)
    }

    /// Rotates `v` from world to body frame.
    pub(crate) fn inv_rotate(self, v: Vec3) -> Vec3 {
        self.conj().rotate(v)
    }

    pub(crate) fn normalize(self) -> Quat {
        let l = sqrt(self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w);
        if l < 1e-9 {
            return Quat::IDENTITY;
        }
        let s = 1.0 / l;
        Quat {
            x: self.x * s,
            y: self.y * s,
            z: self.z * s,
            w: self.w * s,
        }
    }

    /// Integrates a world angular velocity over `dt` (first order, renormalised).
    pub(crate) fn integrate(self, w: Vec3, dt: f32) -> Quat {
        let dq = Quat {
            x: w.x,
            y: w.y,
            z: w.z,
            w: 0.0,
        }
        .mul(self);
        Quat {
            x: self.x + 0.5 * dt * dq.x,
            y: self.y + 0.5 * dt * dq.y,
            z: self.z + 0.5 * dt * dq.z,
            w: self.w + 0.5 * dt * dq.w,
        }
        .normalize()
    }

    /// Normalised linear interpolation along the shorter arc.
    pub(crate) fn nlerp(self, o: Quat, t: f32) -> Quat {
        let d = self.x * o.x + self.y * o.y + self.z * o.z + self.w * o.w;
        let o = if d < 0.0 {
            Quat {
                x: -o.x,
                y: -o.y,
                z: -o.z,
                w: -o.w,
            }
        } else {
            o
        };
        Quat {
            x: lerp(self.x, o.x, t),
            y: lerp(self.y, o.y, t),
            z: lerp(self.z, o.z, t),
            w: lerp(self.w, o.w, t),
        }
        .normalize()
    }

    pub(crate) fn is_finite(self) -> bool {
        self.x.is_finite() && self.y.is_finite() && self.z.is_finite() && self.w.is_finite()
    }

    pub(crate) fn to_array(self) -> [f32; 4] {
        [self.x, self.y, self.z, self.w]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn yaw_turns_forward_towards_left() {
        let q = Quat::from_yaw(std::f32::consts::FRAC_PI_2);
        let f = q.rotate(Vec3::Z);
        assert!((f.x - 1.0).abs() < 1e-5 && f.z.abs() < 1e-5, "{f:?}");
    }

    #[test]
    fn rotate_roundtrip() {
        let q = Quat::from_axis_angle(Vec3::new(0.3, 0.8, -0.2).normalize_or(Vec3::Y), 1.3);
        let v = Vec3::new(1.0, -2.0, 0.5);
        let back = q.inv_rotate(q.rotate(v));
        assert!((back - v).length() < 1e-5);
    }
}
