//! Small seeded pseudo-random generator (SplitMix64).
//!
//! Gameplay randomness only; this is not, and must never be used as, a cryptographic source.

/// Deterministic SplitMix64 stream.
#[derive(Clone, Debug)]
pub(crate) struct Rng {
    state: u64,
}

impl Rng {
    /// A stream derived from `seed` and a `stream` tag, so independent consumers (course,
    /// wander, hiccups) do not reshuffle each other when one of them draws more numbers.
    pub(crate) fn new(seed: u64, stream: u64) -> Self {
        let mut r = Self {
            state: seed ^ stream.wrapping_mul(0xD1B5_4A32_D192_ED03),
        };
        r.next_u64();
        r
    }

    pub(crate) fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Uniform in `[0, 1)` with 24 bits of precision.
    pub(crate) fn f32(&mut self) -> f32 {
        let bits = u32::try_from(self.next_u64() >> 40).unwrap_or(0);
        // 24-bit integers are exactly representable in f32.
        let v = bits as f32;
        v * (1.0 / 16_777_216.0)
    }

    /// Uniform in `[a, b)`.
    pub(crate) fn range(&mut self, a: f32, b: f32) -> f32 {
        a + (b - a) * self.f32()
    }

    /// Uniform integer in `[0, n)`; `n` must be non-zero.
    pub(crate) fn below(&mut self, n: u32) -> u32 {
        u32::try_from(self.next_u64() % u64::from(n.max(1))).unwrap_or(0)
    }

    /// `+1.0` or `-1.0` with equal probability.
    pub(crate) fn sign(&mut self) -> f32 {
        if self.next_u64() & 1 == 0 { 1.0 } else { -1.0 }
    }
}
