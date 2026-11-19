//! Determinism, terrain, stein model, course sanity, hiccup and render-state tests.

use gtlinks_sim::{
    CELL, Course, DT, Driver, EventKind, Input, Interaction, NX, NZ, Phase, Policy, STATE_LEN, Sim,
    SteinFilter, SteinParams, X_MIN, Z_MAX, car_specs, car_specs_json, flatten_events,
};

fn seeds() -> impl Iterator<Item = u32> {
    [1u32, 7, 42, 1234, 99_991, 4_000_000_007].into_iter()
}

// ---------------------------------------------------------------- determinism

fn record(
    seed: u32,
    car: u32,
    steins: u32,
    policy: Policy,
    varying_dt: bool,
) -> (Vec<u32>, Vec<u32>) {
    let mut sim = Sim::new(seed, car, steins);
    let mut driver = Driver::new(policy, seed);
    let mut states = Vec::new();
    let mut events = Vec::new();
    for k in 0..(30.0 / DT) as u32 {
        let input = driver.input(&sim, DT);
        if varying_dt {
            // A fixed but irregular frame-time pattern, as a browser would produce.
            let dt = [0.016, 0.007, 0.033, 0.0167, 0.05][(k % 5) as usize];
            sim.step(dt, input);
        } else {
            sim.substep(input);
        }
        states.extend(sim.state().iter().map(|v| v.to_bits()));
        events.extend(
            flatten_events(&sim.drain_events())
                .iter()
                .map(|v| v.to_bits()),
        );
    }
    (states, events)
}

#[test]
fn same_seed_and_inputs_give_bit_identical_state() {
    for (seed, car, policy) in [
        (3u32, 0u32, Policy::ThrottleRandomSteer),
        (77, 1, Policy::FollowCentreline),
        (5150, 3, Policy::Alternating),
    ] {
        for varying in [false, true] {
            let a = record(seed, car, 13, policy, varying);
            let b = record(seed, car, 13, policy, varying);
            assert!(
                a.0 == b.0,
                "state diverged for seed {seed} car {car} {policy:?}"
            );
            assert!(
                a.1 == b.1,
                "events diverged for seed {seed} car {car} {policy:?}"
            );
        }
    }
}

#[test]
fn different_seeds_give_different_courses() {
    let a = Course::generate(1);
    let b = Course::generate(2);
    assert_ne!(a.heightfield(), b.heightfield());
    assert_eq!(
        Course::generate(1).to_json(),
        a.to_json(),
        "course JSON is constant for a seed"
    );
}

// ---------------------------------------------------------------- terrain

#[test]
fn height_at_matches_grid_nodes_and_triangles() {
    for seed in seeds() {
        let c = Course::generate(seed);
        let hf = c.heightfield();
        assert_eq!(hf.len(), NX * NZ);
        assert!(
            hf.iter().all(|h| h.is_finite()),
            "non-finite height for seed {seed}"
        );
        // Exactly the stored value at every 7th node.
        for iz in (0..NZ).step_by(7) {
            for ix in (0..NX).step_by(7) {
                let x = X_MIN + CELL * ix as f32;
                let z = CELL * iz as f32;
                assert_eq!(
                    c.terrain_height(x, z),
                    hf[iz * NX + ix],
                    "node ({ix}, {iz}) seed {seed}"
                );
            }
        }
        // Linear interpolation inside the two triangles of a cell, split (ix,iz)-(ix+1,iz+1).
        let mut k = 0u32;
        for iz in (3..NZ - 1).step_by(37) {
            for ix in (2..NX - 1).step_by(13) {
                k += 1;
                let fx = ((k * 37) % 100) as f32 / 100.0;
                let fz = ((k * 61) % 100) as f32 / 100.0;
                let h = |i: usize, j: usize| hf[j * NX + i];
                let (h00, h10, h01, h11) =
                    (h(ix, iz), h(ix + 1, iz), h(ix, iz + 1), h(ix + 1, iz + 1));
                let want = if fx >= fz {
                    h00 + (h10 - h00) * fx + (h11 - h10) * fz
                } else {
                    h00 + (h11 - h01) * fx + (h01 - h00) * fz
                };
                let x = X_MIN + CELL * (ix as f32 + fx);
                let z = CELL * (iz as f32 + fz);
                let got = c.terrain_height(x, z);
                assert!(
                    (got - want).abs() < 2e-3,
                    "triangle interp at ({x}, {z}): {got} vs {want}"
                );
                // height_at adds ramps on top and nothing else.
                let on_ramp = c.ramps().iter().any(|r| {
                    let (dx, dz) = (libm::sinf(r.yaw), libm::cosf(r.yaw));
                    let u = (x - r.pos[0]) * dx + (z - r.pos[2]) * dz;
                    let v = (x - r.pos[0]) * dz - (z - r.pos[2]) * dx;
                    u > -0.1 && u < r.length + 1.0 && v.abs() < r.width * 0.5 + 0.1
                });
                if !on_ramp {
                    assert_eq!(c.height_at(x, z), got, "height_at off-ramp equals terrain");
                }
            }
        }
    }
}

#[test]
fn ramps_raise_height_at_and_tilt_the_normal() {
    let c = Course::generate(42);
    for r in c.ramps() {
        let (dx, dz) = (libm::sinf(r.yaw), libm::cosf(r.yaw));
        let u = r.length * 0.75;
        let (x, z) = (r.pos[0] + dx * u, r.pos[2] + dz * u);
        let rise = c.height_at(x, z) - c.terrain_height(x, z);
        assert!(
            (rise - r.height * 0.75).abs() < 1e-3,
            "ramp rise {rise} vs {}",
            r.height * 0.75
        );
        let n = c.normal_at(x, z);
        let n_terrain_up = c.normal_at(x + 60.0 * dz, z - 60.0 * dx)[1];
        assert!(n[1] < 1.0 && n[1].is_finite() && n_terrain_up.is_finite());
    }
}

#[test]
fn terrain_continues_beyond_the_world_without_a_seam() {
    let c = Course::generate(9);
    for z in [100.0f32, 900.0, 2000.0] {
        let inside = c.terrain_height(-X_MIN - 0.01, z);
        let outside = c.terrain_height(-X_MIN + 0.01, z);
        assert!((inside - outside).abs() < 0.05, "seam at +x edge, z={z}");
        let left_in = c.terrain_height(X_MIN + 0.01, z);
        let left_out = c.terrain_height(X_MIN - 0.01, z);
        assert!((left_in - left_out).abs() < 0.05, "seam at -x edge, z={z}");
    }
    let end_in = c.terrain_height(0.0, Z_MAX - 0.01);
    let end_out = c.terrain_height(0.0, Z_MAX + 0.01);
    assert!((end_in - end_out).abs() < 0.05, "seam at the bottom edge");
    assert!(c.terrain_height(0.0, -50.0).is_finite());
}

// ---------------------------------------------------------------- stein model

/// Time for the steering output to first reach 63 % of its final value after a full step.
fn response_time(steins: u32) -> f32 {
    let mut p = SteinParams::new(steins);
    p.wander = 0.0;
    let target = p.steer_gain * 0.63;
    let mut f = SteinFilter::new(p, 1);
    let mut t = 0.0;
    loop {
        let out = f.update(DT, 1.0, 0.0, 0.0);
        t += DT;
        if out.steer >= target || t > 5.0 {
            return t;
        }
    }
}

/// Peak and overshoot of the steering step response, as fractions of the steady value.
fn overshoot(steins: u32) -> f32 {
    let mut p = SteinParams::new(steins);
    p.wander = 0.0;
    let mut f = SteinFilter::new(p, 1);
    let mut peak = 0.0f32;
    for _ in 0..(4.0 / DT) as u32 {
        peak = peak.max(f.update(DT, 1.0, 0.0, 0.0).steer);
    }
    peak / p.steer_gain - 1.0
}

/// Largest applied steering with the wheel held straight for two minutes.
fn wander_amplitude(steins: u32, seed: u32) -> f32 {
    let mut f = SteinFilter::new(SteinParams::new(steins), seed);
    let mut peak = 0.0f32;
    for _ in 0..(120.0 / DT) as u32 {
        peak = peak.max(f.update(DT, 0.0, 0.0, 0.0).steer.abs());
    }
    peak
}

#[test]
fn steering_response_and_wander_worsen_monotonically_with_steins() {
    let times: Vec<f32> = (10..=15).map(response_time).collect();
    let overshoots: Vec<f32> = (10..=15).map(overshoot).collect();
    println!("response time 10..15 steins: {times:?}");
    println!("overshoot 10..15 steins: {overshoots:?}");
    for w in times.windows(2) {
        assert!(w[1] > w[0], "response time not increasing: {times:?}");
    }
    for w in overshoots.windows(2) {
        assert!(w[1] > w[0], "overshoot not increasing: {overshoots:?}");
    }
    for seed in [1u32, 2, 3, 99] {
        let amps: Vec<f32> = (10..=15).map(|s| wander_amplitude(s, seed)).collect();
        println!("wander amplitude seed {seed}: {amps:?}");
        for w in amps.windows(2) {
            assert!(
                w[1] > w[0],
                "wander not increasing for seed {seed}: {amps:?}"
            );
        }
        assert!(
            amps[0] <= 0.06 + 1e-4 && amps[5] <= 0.28 + 1e-4,
            "wander exceeds the table"
        );
    }
}

#[test]
fn stein_table_endpoints_match_the_contract() {
    let lo = SteinParams::new(10);
    let hi = SteinParams::new(15);
    let close = |a: f32, b: f32| (a - b).abs() < 1e-5;
    assert!(close(lo.steer_lag, 0.12) && close(hi.steer_lag, 0.45));
    assert!(close(lo.steer_gain, 0.95) && close(hi.steer_gain, 0.70));
    assert!(close(lo.wander, 0.06) && close(hi.wander, 0.28));
    assert!(close(lo.pedal_lag, 0.10) && close(hi.pedal_lag, 0.35));
    assert!(close(lo.assist, 0.60) && close(hi.assist, 0.10));
    assert!(close(lo.roof_mass, 13.0) && close(hi.roof_mass, 19.5));
    assert_eq!(SteinParams::new(3).steins, 10);
    assert_eq!(SteinParams::new(40).steins, 15);
}

// ---------------------------------------------------------------- course sanity

#[test]
fn course_layout_is_sane() {
    for seed in seeds() {
        let c = Course::generate(seed);
        let holes = c.holes();
        assert_eq!(holes.len(), 9, "seed {seed}");
        let inside =
            |p: [f32; 3]| (X_MIN..=-X_MIN).contains(&p[0]) && (0.0..=Z_MAX).contains(&p[2]);
        let mut last = f32::INFINITY;
        for h in holes {
            assert!(
                inside(h.tee) && inside(h.green),
                "hole {} outside the world, seed {seed}",
                h.index
            );
            assert!((3..=5).contains(&h.par));
            assert!(
                h.green[1] < h.tee[1],
                "hole {} green above tee, seed {seed}",
                h.index
            );
            assert!(
                h.tee[1] < last,
                "hole {} tee above previous green, seed {seed}",
                h.index
            );
            last = h.green[1];
            assert!(h.centreline.len() >= 10);
            for w in h.centreline.windows(2) {
                let d = ((w[1][0] - w[0][0]).powi(2) + (w[1][2] - w[0][2]).powi(2)).sqrt();
                assert!(d <= 10.5, "centreline spacing {d}");
            }
        }
        // Links: the next tee sits just beyond the previous green.
        for w in holes.windows(2) {
            let gap = w[1].tee[2] - w[0].green[2];
            assert!(
                gap > w[0].green_radius && gap < 60.0,
                "gap {gap} seed {seed}"
            );
        }
        let fin = c.finale();
        assert!(
            fin.pos[2] - fin.radius > holes[8].green[2],
            "arena after the ninth green"
        );
        let start = c.start();
        assert!((start.pos[2] - 40.0).abs() < 1.0 && start.yaw == 0.0);
        // Ramps: two to four per hole, none on the lodge or the start apron.
        let ramps = c.ramps();
        assert!(
            (2 * 9 + 1..=4 * 9 + 1).contains(&ramps.len()),
            "{} ramps",
            ramps.len()
        );
        assert_eq!(fin.ramp_index, ramps.len() - 1);
        for r in ramps {
            for k in 0..=4 {
                let u = r.length * k as f32 / 4.0;
                let (x, z) = (
                    r.pos[0] + libm::sinf(r.yaw) * u,
                    r.pos[2] + libm::cosf(r.yaw) * u,
                );
                assert!(
                    !c.in_lodge_footprint(x, z, 2.0) && !c.on_start_apron(x, z, 2.0),
                    "ramp on the lodge"
                );
            }
        }
        for p in c.props() {
            let solid = p.prop_kind().interaction() == Interaction::Solid;
            if solid {
                assert!(
                    !c.in_lodge_footprint(p.pos[0], p.pos[2], 2.0)
                        && !c.on_start_apron(p.pos[0], p.pos[2], 4.0),
                    "solid prop on the lodge or apron, seed {seed}"
                );
            }
            assert!(p.pos.iter().all(|v| v.is_finite()));
        }
        // Lodge terrace flat.
        let l = c.lodge();
        let h0 = c.terrain_height(l.pos[0], l.pos[2]);
        for (dx, dz) in [(-12.0, -7.0), (12.0, -7.0), (-12.0, 7.0), (12.0, 7.0)] {
            assert!(
                (c.terrain_height(l.pos[0] + dx, l.pos[2] + dz) - h0).abs() < 1e-3,
                "lodge not flat"
            );
        }
        // Monotone descent along the course centreline, sampled every 100 m of fall line.
        let mut prev = f32::INFINITY;
        for z in (100..=2500).step_by(100) {
            let z = z as f32;
            let h = c.terrain_height(c.path_x(z), z);
            assert!(h < prev + 0.5, "course climbs at z={z}, seed {seed}");
            prev = h;
        }
        let drop = c.terrain_height(start.pos[0], start.pos[2])
            - c.terrain_height(c.path_x(2550.0), 2550.0);
        assert!((440.0..=600.0).contains(&drop), "total drop {drop}");
        // Surfaces are valid ids, with every kind of golf ground present.
        let s = c.surface_map();
        assert_eq!(s.len(), NX * NZ);
        assert!(s.iter().all(|&v| v <= 7));
        for id in [0u8, 1, 2, 3, 4, 5] {
            assert!(s.contains(&id), "surface {id} missing, seed {seed}");
        }
        // JSON round trip carries every contract key.
        let v: serde_json::Value = serde_json::from_str(&c.to_json()).expect("course JSON parses");
        for key in [
            "seed", "start", "lodge", "holes", "props", "ramps", "finale",
        ] {
            assert!(v.get(key).is_some(), "missing {key}");
        }
        assert_eq!(v["holes"].as_array().map(Vec::len), Some(9));
    }
}

#[test]
fn slopes_stay_shallow_enough_to_rest_inverted() {
    // A car flat on its roof on a slope steeper than about 25 degrees cannot reach up.y < -0.9,
    // so such ground must stay rare (bunker lips and the odd ridge flank).
    let mut worst = 0.0f32;
    let mut steep = 0usize;
    let mut total = 0usize;
    for seed in seeds() {
        let c = Course::generate(seed);
        let h = c.heightfield();
        for iz in 0..NZ - 1 {
            for ix in 0..NX - 1 {
                let a = h[iz * NX + ix];
                let gx = (h[iz * NX + ix + 1] - a) / CELL;
                let gz = (h[(iz + 1) * NX + ix] - a) / CELL;
                let g = (gx * gx + gz * gz).sqrt();
                worst = worst.max(g);
                total += 1;
                if g > 0.42 {
                    steep += 1;
                }
            }
        }
    }
    println!(
        "steepest grid slope: {worst:.3} ({:.1} deg); cells steeper than 0.42: {:.3}%",
        libm::atanf(worst).to_degrees(),
        100.0 * steep as f32 / total as f32
    );
    assert!(worst < 0.62, "steepest slope {worst}");
    assert!(
        (steep as f32) < 0.01 * total as f32,
        "too much ground steeper than 23 degrees"
    );
}

#[test]
fn car_left_at_the_start_rests_stably() {
    for seed in seeds() {
        for car in 0..4 {
            let mut sim = Sim::new(seed, car, 15);
            let start = sim.course().start();
            for _ in 0..(3.0 / DT) as u32 {
                sim.substep(Input::default());
                assert_eq!(sim.phase(), Phase::Driving);
            }
            // Fifteen steins: hiccups may bounce it on its springs, but it must stay put.
            let p = sim.position();
            let up = sim.up();
            assert!(up[1] > 0.97, "car {car} seed {seed} tipped: up.y {}", up[1]);
            assert!(
                (p[1] - start.pos[1]).abs() < 0.3,
                "car {car} seed {seed} sank or rose: {}",
                p[1] - start.pos[1]
            );
            let drift = ((p[0] - start.pos[0]).powi(2) + (p[2] - start.pos[2]).powi(2)).sqrt();
            assert!(drift < 0.5, "car {car} seed {seed} drifted {drift} m");
        }
    }
}

#[test]
fn car_specs_come_from_the_embedded_table() {
    let specs = car_specs();
    assert_eq!(specs.len(), 4);
    let keys: Vec<&str> = specs.iter().map(|s| s.key.as_str()).collect();
    assert_eq!(
        keys,
        [
            "escapade_2009",
            "glug_2017",
            "genesips_2021",
            "rangeroller_2026"
        ]
    );
    let v: serde_json::Value =
        serde_json::from_str(&car_specs_json()).expect("car specs JSON parses");
    assert_eq!(v.as_array().map(Vec::len), Some(4));
    assert!(v[1]["tuning"]["travel"].is_number() && v[1]["mass"].is_number());
}

// ---------------------------------------------------------------- hiccups

#[test]
fn strongest_hiccups_cannot_flip_the_car() {
    for car in 0..4 {
        // Parked on the apron: a full-strength hiccup every 0.4 s for 12 s.
        let mut sim = Sim::new(5, car, 15);
        let mut min_up = 1.0f32;
        for k in 0..(10.0 / DT) as u32 {
            if k % 48 == 0 {
                sim.force_hiccup(1.0);
            }
            sim.substep(Input::default());
            min_up = min_up.min(sim.up()[1]);
        }
        assert!(
            min_up > 0.9,
            "car {car} rocked to up.y {min_up} while parked"
        );
        // Rolling down the apron at speed with the wheel straight.
        let mut sim = Sim::new(5, car, 15);
        let mut min_up = 1.0f32;
        for k in 0..(4.5 / DT) as u32 {
            if k % 48 == 0 {
                sim.force_hiccup(1.0);
            }
            sim.substep(Input {
                throttle: 1.0,
                ..Input::default()
            });
            min_up = min_up.min(sim.up()[1]);
        }
        assert!(
            min_up > 0.8,
            "car {car} rocked to up.y {min_up} while driving"
        );
    }
}

#[test]
fn hiccups_come_more_often_with_more_steins_and_stop_at_the_finale() {
    let count = |steins: u32| -> (u32, u32) {
        let mut before = 0;
        let mut after = 0;
        for seed in 0..60u32 {
            let mut sim = Sim::new(seed, 2, steins);
            let mut armed = false;
            for _ in 0..(40.0 / DT) as u32 {
                sim.substep(Input::default());
                for e in sim.drain_events() {
                    match e.kind {
                        EventKind::FinaleStart => armed = true,
                        EventKind::Hiccup if armed => after += 1,
                        EventKind::Hiccup => {
                            assert!((0.0..=1.0).contains(&e.a));
                            before += 1;
                        }
                        _ => {}
                    }
                }
            }
        }
        (before, after)
    };
    let (lo, lo_after) = count(10);
    let (hi, hi_after) = count(15);
    println!("hiccups in 60 runs x 12 s before the finale: 10 steins {lo}, 15 steins {hi}");
    // Expected about 60 * 12 / 9 = 80 and 60 * 12 / 3 = 240.
    assert!(
        hi as f32 > lo as f32 * 2.2,
        "15 steins should hiccup about three times as often ({lo} vs {hi})"
    );
    assert_eq!(lo_after + hi_after, 0, "no hiccups after the finale arms");
}

// ---------------------------------------------------------------- render state

#[test]
fn render_state_interpolates_between_substeps() {
    let mut sim = Sim::new(11, 2, 10);
    for _ in 0..240 {
        sim.step(
            DT,
            Input {
                throttle: 1.0,
                ..Input::default()
            },
        );
    }
    let before = sim.state();
    sim.step(
        DT * 0.5,
        Input {
            throttle: 1.0,
            ..Input::default()
        },
    );
    let half = sim.state();
    sim.step(
        DT * 0.5,
        Input {
            throttle: 1.0,
            ..Input::default()
        },
    );
    let after = sim.state();
    assert_eq!(before.len(), STATE_LEN);
    for i in 0..3 {
        let (lo, hi) = (before[i].min(after[i]), before[i].max(after[i]));
        assert!(
            half[i] >= lo - 1e-4 && half[i] <= hi + 1e-4,
            "component {i} not between substeps"
        );
    }
    let q = &half[3..7];
    let n = (q.iter().map(|v| v * v).sum::<f32>()).sqrt();
    assert!((n - 1.0).abs() < 1e-4, "quaternion not unit: {n}");
}

#[test]
fn step_clamps_large_frames() {
    let mut a = Sim::new(3, 0, 10);
    a.step(5.0, Input::default());
    let t = a.state()[27];
    assert!(t <= 0.1 + 1e-4, "one call advanced {t}s");
    a.step(
        f32::NAN,
        Input {
            steer: f32::NAN,
            ..Input::default()
        },
    );
    assert!(a.state().iter().all(|v| v.is_finite()));
}
