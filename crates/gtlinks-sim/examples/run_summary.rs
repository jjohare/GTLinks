//! Prints a run summary for a seed, car and stein count without a browser.
//!
//! ```text
//! cargo run --release -p gtlinks-sim --example run_summary -- <seed> <car 0-3> <steins 10-15> [policy] [--events] [--trace]
//! ```
//!
//! Policies: none, throttle, random-steer, brake, reverse, centreline (default), alternating.

use gtlinks_sim::{DT, Driver, EventKind, Phase, Policy, Sim, car_spec};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let num = |i: usize, default: u32| args.get(i).and_then(|s| s.parse().ok()).unwrap_or(default);
    let seed = num(0, 1);
    let car = num(1, 2);
    let steins = num(2, 10);
    let policy = args
        .get(3)
        .and_then(|s| Policy::from_name(s))
        .unwrap_or(Policy::FollowCentreline);
    let show_events = args.iter().any(|a| a == "--events");
    let trace = args.iter().any(|a| a == "--trace");

    let mut sim = Sim::new(seed, car, steins);
    let mut driver = Driver::new(policy, seed);
    let mut wrecked_at = None;
    let mut log: Vec<String> = Vec::new();
    while sim.run_time() < 170.0 {
        let input = driver.input(&sim, DT);
        sim.substep(input);
        let step = (sim.run_time() / DT).round() as u64;
        if trace && step.is_multiple_of(30) {
            let p = sim.position();
            let st = sim.state();
            log.push(format!(
                "  {:7.2}s trace pos ({:.0}, {:.1}, {:.0}) lat {:.1} speed {:.1} up.y {:.2} wheels {} steer {:.2} in {:.2}/{:.2}/{:.2} surf {}",
                sim.run_time(),
                p[0],
                p[1],
                p[2],
                sim.course().lateral_offset(p[0], p[2]),
                sim.speed(),
                sim.up()[1],
                st[30],
                st[32],
                input.steer,
                input.throttle,
                input.brake,
                sim.course().surface_at(p[0], p[2])
            ));
        }
        for e in sim.drain_events() {
            if show_events || !matches!(e.kind, EventKind::NearMiss | EventKind::Hiccup) {
                log.push(format!(
                    "  {:7.2}s {:?} a={:.2} b={:.2} at ({:.0}, {:.0}, {:.0})",
                    sim.run_time(),
                    e.kind,
                    e.a,
                    e.b,
                    e.pos[0],
                    e.pos[1],
                    e.pos[2]
                ));
            }
        }
        if sim.phase() == Phase::Wrecked && wrecked_at.is_none() {
            wrecked_at = Some(sim.run_time());
        }
        if wrecked_at.is_some_and(|t| sim.run_time() > t + 8.0) {
            break;
        }
    }

    let st = sim.stats();
    let up = sim.up();
    println!(
        "seed {seed}  car {car} ({})  steins {steins}  policy {}",
        car_spec(car).name,
        policy.name()
    );
    println!("time            {:.2} s", sim.run_time());
    println!("distance        {:.0} m", st.distance);
    println!("top speed       {:.1} m/s", st.top_speed);
    println!("airtime total   {:.2} s", st.airtime_total);
    println!(
        "tricks          {}  score {:.0}",
        st.tricks,
        sim.state()[34]
    );
    println!(
        "progress        z {:.0} of arena {:.0}",
        st.progress_z,
        sim.course().finale().pos[2]
    );
    println!("hiccups         {}", st.hiccups);
    println!("prop impacts    {}", st.prop_impacts);
    println!(
        "parts detached  {}  damage {:.2}",
        st.parts_detached,
        sim.damage()
    );
    println!(
        "armed by        {:?}  launch {:?}",
        st.arm_reason, st.launch
    );
    println!("fallbacks       {:?}", st.fallbacks);
    println!("touchdown up.y  {:?}", st.touchdown_up_y);
    println!(
        "final           up.y {:.3}  speed {:.3}  wheels stopped at {:?}",
        up[1],
        sim.speed(),
        st.wheels_stopped_at
    );
    println!("phases:");
    for (phase, t) in &st.transitions {
        println!("  {t:7.2}s {phase:?}");
    }
    println!("events:");
    for line in &log {
        println!("{line}");
    }
}
