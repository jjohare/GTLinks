//! The inverted-rest guarantee, checked by brute force.
//!
//! For every seed (a 6-seed subset by default, `GTLINKS_SEEDS` to change, 200 in the ignored
//! full test), every car, every stein count
//! from 10 to 15 and seven input policies, the run must reach `Wrecked` within 150 s of run
//! time with `up.y < -0.9` and speed `< 0.1`, then hold that pose for a further 10 s. State
//! and events must never contain a non-finite value, hiccups must stop once the finale arms,
//! and at least two parts must have detached by the wreck.
//!
//! A report (pass count, time-to-wreck distribution, phase timings, backstop usage and the
//! centreline driver's progress) is printed and written to `target/property-report.txt`.

use std::fmt::Write as _;
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};

use gtlinks_sim::{
    ArmReason, Course, DT, Driver, EventKind, LaunchKind, Phase, Policy, STATE_LEN, Sim,
};

const RUN_LIMIT: f32 = 150.0;
const HOLD: f32 = 10.0;

#[derive(Clone, Debug)]
struct Outcome {
    seed: u32,
    car: u32,
    steins: u32,
    policy: Policy,
    failure: Option<String>,
    wreck_time: f32,
    phase_times: Vec<(Phase, f32)>,
    arm: Option<ArmReason>,
    launch: Option<LaunchKind>,
    fallbacks: [u32; 4],
    progress: f32,
    finale_z: f32,
    start_z: f32,
    wheels_stop_after: Option<f32>,
    parts: u32,
    reached_arena: bool,
    touchdown: Option<f32>,
}

fn run_one(course: &Course, car: u32, steins: u32, policy: Policy) -> Outcome {
    let seed = course.seed();
    let mut sim = Sim::from_course(course.clone(), car, steins);
    let mut driver = Driver::new(policy, seed ^ (car << 8) ^ (steins << 12));
    let mut failure: Option<String> = None;
    let mut wreck_time = f32::NAN;
    let mut armed = false;
    let mut wrecked_events = 0;
    let mut parts_at_wreck = 0;
    let mut parts = 0;
    let mut frozen: Option<[f32; STATE_LEN]> = None;
    let steps_limit = ((RUN_LIMIT + HOLD + 1.0) / DT) as u32;
    for _ in 0..steps_limit {
        let input = driver.input(&sim, DT);
        sim.substep(input);
        let s = sim.state();
        if failure.is_none() && s.iter().any(|v| !v.is_finite()) {
            failure = Some(format!("non-finite state at t={:.2}", sim.run_time()));
        }
        for e in sim.drain_events() {
            if failure.is_none()
                && !(e.a.is_finite() && e.b.is_finite() && e.pos.iter().all(|v| v.is_finite()))
            {
                failure = Some(format!(
                    "non-finite event {:?} at t={:.2}",
                    e.kind,
                    sim.run_time()
                ));
            }
            match e.kind {
                EventKind::FinaleStart => armed = true,
                EventKind::Hiccup if armed && failure.is_none() => {
                    failure = Some(format!(
                        "hiccup after finale armed at t={:.2}",
                        sim.run_time()
                    ));
                }
                EventKind::PartDetached => parts += 1,
                EventKind::Wrecked => {
                    wrecked_events += 1;
                    parts_at_wreck = parts;
                }
                _ => {}
            }
        }
        if sim.phase() == Phase::Wrecked && wreck_time.is_nan() {
            wreck_time = sim.run_time();
            let up = sim.up();
            if up[1] >= -0.9 || sim.speed() >= 0.1 {
                failure.get_or_insert_with(|| {
                    format!("wrecked but up.y={:.3} speed={:.3}", up[1], sim.speed())
                });
            }
            frozen = Some(sim.state());
        }
        if !wreck_time.is_nan() {
            let up = sim.up();
            if sim.phase() != Phase::Wrecked || up[1] >= -0.9 || sim.speed() >= 0.1 {
                failure.get_or_insert_with(|| {
                    format!("left the wrecked pose at t={:.2}", sim.run_time())
                });
            }
            if let Some(f) = frozen {
                let s = sim.state();
                let moved = (0..7).any(|i| s[i].to_bits() != f[i].to_bits());
                if moved {
                    failure.get_or_insert_with(|| {
                        format!("pose drifted after wreck at t={:.2}", sim.run_time())
                    });
                }
            }
            if sim.run_time() >= wreck_time + HOLD {
                break;
            }
        }
        if wreck_time.is_nan() && sim.run_time() > RUN_LIMIT {
            let up = sim.up();
            failure.get_or_insert_with(|| {
                format!(
                    "not wrecked by {RUN_LIMIT}s: phase {:?} up.y={:.3} speed={:.3} pos={:?}",
                    sim.phase(),
                    up[1],
                    sim.speed(),
                    sim.position()
                )
            });
            break;
        }
    }
    if failure.is_none() && wrecked_events != 1 {
        failure = Some(format!("{wrecked_events} Wrecked events"));
    }
    if failure.is_none() && parts_at_wreck < 2 {
        failure = Some(format!("only {parts_at_wreck} parts detached at wreck"));
    }
    let st = sim.stats();
    let fin = course.finale();
    Outcome {
        seed,
        car,
        steins,
        policy,
        failure,
        wreck_time,
        phase_times: st.transitions.clone(),
        arm: st.arm_reason,
        launch: st.launch,
        fallbacks: [
            st.fallbacks.armed_timeout,
            st.fallbacks.righting_torque,
            st.fallbacks.rest_damping,
            st.fallbacks.kinematic,
        ],
        progress: st.progress_z,
        finale_z: fin.pos[2] - fin.radius,
        start_z: course.start().pos[2],
        wheels_stop_after: st.wheels_stopped_at.map(|t| t - wreck_time),
        parts: st.parts_detached,
        reached_arena: st.arm_reason == Some(ArmReason::Arena),
        touchdown: st.touchdown_up_y,
    }
}

fn percentile(sorted: &[f32], p: f32) -> f32 {
    if sorted.is_empty() {
        return f32::NAN;
    }
    let i = ((sorted.len() - 1) as f32 * p).round() as usize;
    sorted[i]
}

fn dist_line(name: &str, mut v: Vec<f32>) -> String {
    v.retain(|x| x.is_finite());
    v.sort_by(f32::total_cmp);
    if v.is_empty() {
        return format!("{name:<34} (none)\n");
    }
    let mean = v.iter().sum::<f32>() / v.len() as f32;
    format!(
        "{name:<34} n={:<6} min {:6.2}  p50 {:6.2}  mean {:6.2}  p95 {:6.2}  max {:6.2}\n",
        v.len(),
        v[0],
        percentile(&v, 0.5),
        mean,
        percentile(&v, 0.95),
        v[v.len() - 1]
    )
}

/// Duration between the first entry into phase `a` and the first entry into phase `b`.
fn span(o: &Outcome, a: Phase, b: Phase) -> f32 {
    let ta = o.phase_times.iter().find(|(p, _)| *p == a).map(|x| x.1);
    let tb = o.phase_times.iter().find(|(p, _)| *p == b).map(|x| x.1);
    match (ta, tb) {
        (Some(x), Some(y)) => y - x,
        _ => f32::NAN,
    }
}

/// Seeds in the default (CI) subset; `GTLINKS_SEEDS` overrides it.
const DEFAULT_SEEDS: u32 = 6;
/// Seeds in the full matrix run by the ignored test.
const FULL_SEEDS: u32 = 200;

/// Default subset: every car, stein count and policy over a few seeds. Fast enough for CI.
#[test]
fn inverted_rest_guarantee() {
    let seeds = std::env::var("GTLINKS_SEEDS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(DEFAULT_SEEDS);
    run_matrix(seeds);
}

/// Full matrix over 200 seeds: `cargo test --release -p gtlinks-sim --test property -- --ignored`.
#[test]
#[ignore = "full 200-seed matrix; about 15 minutes on 56 cores"]
fn inverted_rest_guarantee_full() {
    run_matrix(FULL_SEEDS);
}

fn run_matrix(seeds: u32) {
    let threads = std::thread::available_parallelism().map_or(4, |n| n.get());
    let next = AtomicUsize::new(0);
    let results: Mutex<Vec<Outcome>> = Mutex::new(Vec::new());
    let t0 = std::time::Instant::now();
    std::thread::scope(|scope| {
        for _ in 0..threads {
            scope.spawn(|| {
                loop {
                    let i = next.fetch_add(1, Ordering::Relaxed);
                    if i >= seeds as usize {
                        break;
                    }
                    let seed = u32::try_from(i).expect("seed fits") * 7919 + 13;
                    let course = Course::generate(seed);
                    let mut local = Vec::new();
                    for car in 0..4 {
                        for steins in 10..=15 {
                            for policy in Policy::ALL {
                                local.push(run_one(&course, car, steins, policy));
                            }
                        }
                    }
                    results.lock().expect("results lock").extend(local);
                }
            });
        }
    });
    let mut all = results.into_inner().expect("results lock");
    all.sort_by_key(|o| (o.seed, o.car, o.steins, o.policy.name()));
    let failures: Vec<&Outcome> = all.iter().filter(|o| o.failure.is_some()).collect();

    let mut r = String::new();
    let _ = writeln!(
        r,
        "inverted-rest property: {} seeds x 4 cars x 6 stein counts x {} policies = {} runs in {:.1}s on {threads} threads",
        seeds,
        Policy::ALL.len(),
        all.len(),
        t0.elapsed().as_secs_f32()
    );
    let _ = writeln!(r, "passed {} / {}", all.len() - failures.len(), all.len());
    r.push_str(&dist_line(
        "time to Wrecked (s), all",
        all.iter().map(|o| o.wreck_time).collect(),
    ));
    for p in Policy::ALL {
        r.push_str(&dist_line(
            &format!("  policy {}", p.name()),
            all.iter()
                .filter(|o| o.policy == p)
                .map(|o| o.wreck_time)
                .collect(),
        ));
    }
    let mut hist = [0usize; 16];
    for o in &all {
        if o.wreck_time.is_finite() {
            hist[((o.wreck_time / 10.0) as usize).min(15)] += 1;
        }
    }
    r.push_str("histogram of time to Wrecked (10 s bins):\n");
    for (i, n) in hist.iter().enumerate() {
        if *n > 0 {
            let _ = writeln!(r, "  {:3}-{:3}s {:6}", i * 10, i * 10 + 10, n);
        }
    }
    let early = all
        .iter()
        .filter(|o| !o.phase_times.iter().any(|(p, _)| *p == Phase::FinaleArmed))
        .count();
    let _ = writeln!(r, "early wrecks (no finale): {early}");
    for (name, reason) in [
        ("arena", ArmReason::Arena),
        ("timer", ArmReason::Timer),
        ("stall", ArmReason::Stall),
    ] {
        let _ = writeln!(
            r,
            "armed by {name}: {}",
            all.iter().filter(|o| o.arm == Some(reason)).count()
        );
    }
    for (name, kind) in [
        ("final ramp", LaunchKind::FinalRamp),
        ("kicker", LaunchKind::Kicker),
        ("already over", LaunchKind::AlreadyOver),
        ("already airborne", LaunchKind::AlreadyAirborne),
    ] {
        let _ = writeln!(
            r,
            "launch {name}: {}",
            all.iter().filter(|o| o.launch == Some(kind)).count()
        );
    }
    let fb: Vec<usize> = (0..4)
        .map(|k| all.iter().filter(|o| o.fallbacks[k] > 0).count())
        .collect();
    let _ = writeln!(
        r,
        "backstops: armed-timeout {}  righting-torque {}  rest-damping {}  kinematic {}",
        fb[0], fb[1], fb[2], fb[3]
    );
    for p in Policy::ALL {
        let runs: Vec<&Outcome> = all.iter().filter(|o| o.policy == p).collect();
        let c = |k: usize| runs.iter().filter(|o| o.fallbacks[k] > 0).count();
        let _ = writeln!(
            r,
            "  {:<13} armed-timeout {:4}  righting {:4}  damping {:4}  kinematic {:4}",
            p.name(),
            c(0),
            c(1),
            c(2),
            c(3)
        );
    }
    r.push_str("finale phase timings (s):\n");
    r.push_str(&dist_line(
        "  FinaleArmed -> FinaleAirborne",
        all.iter()
            .map(|o| span(o, Phase::FinaleArmed, Phase::FinaleAirborne))
            .collect(),
    ));
    r.push_str(&dist_line(
        "  FinaleAirborne -> Settling",
        all.iter()
            .map(|o| span(o, Phase::FinaleAirborne, Phase::Settling))
            .collect(),
    ));
    r.push_str(&dist_line(
        "  Settling -> Wrecked",
        all.iter()
            .map(|o| span(o, Phase::Settling, Phase::Wrecked))
            .collect(),
    ));
    r.push_str(&dist_line(
        "  FinaleArmed -> Wrecked",
        all.iter()
            .map(|o| span(o, Phase::FinaleArmed, Phase::Wrecked))
            .collect(),
    ));
    r.push_str(&dist_line(
        "  wheel spin-down after Wrecked",
        all.iter()
            .map(|o| o.wheels_stop_after.unwrap_or(f32::NAN))
            .collect(),
    ));
    r.push_str(&dist_line(
        "  up.y at finale touchdown",
        all.iter()
            .map(|o| o.touchdown.unwrap_or(f32::NAN))
            .collect(),
    ));
    let inverted_touch = all
        .iter()
        .filter(|o| o.touchdown.is_some_and(|u| u < -0.5))
        .count();
    let touches = all.iter().filter(|o| o.touchdown.is_some()).count();
    let _ = writeln!(
        r,
        "  finale touchdowns roof-first (up.y < -0.5): {inverted_touch} / {touches}"
    );
    r.push_str(&dist_line(
        "  parts detached by the end",
        all.iter().map(|o| o.parts as f32).collect(),
    ));

    r.push_str(
        "follow-the-centreline driver, progress down the course (0 = start, 1 = arena edge):\n",
    );
    for steins in 10..=15 {
        let runs: Vec<&Outcome> = all
            .iter()
            .filter(|o| o.policy == Policy::FollowCentreline && o.steins == steins)
            .collect();
        let frac: Vec<f32> = runs
            .iter()
            .map(|o| ((o.progress - o.start_z) / (o.finale_z - o.start_z)).clamp(0.0, 1.0))
            .collect();
        let arena = runs.iter().filter(|o| o.reached_arena).count();
        let mean = frac.iter().sum::<f32>() / frac.len().max(1) as f32;
        let mut sorted = frac.clone();
        sorted.sort_by(f32::total_cmp);
        let _ = writeln!(
            r,
            "  {steins} steins: mean {:.2}  median {:.2}  reached arena {}/{}",
            mean,
            percentile(&sorted, 0.5),
            arena,
            runs.len()
        );
    }
    if !failures.is_empty() {
        r.push_str("FAILURES:\n");
        for o in failures.iter().take(40) {
            let _ = writeln!(
                r,
                "  seed {} car {} steins {} policy {}: {}",
                o.seed,
                o.car,
                o.steins,
                o.policy.name(),
                o.failure.as_deref().unwrap_or("")
            );
        }
    }
    println!("{r}");
    let target =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../target/property-report.txt");
    let _ = std::fs::write(target, &r);
    assert!(
        failures.is_empty(),
        "{} of {} runs failed the inverted-rest guarantee",
        failures.len(),
        all.len()
    );
}
