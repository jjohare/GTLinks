# GTLinks finale timeline

What the simulation emits from the moment the finale arms until the wreck has settled. It is
written for the front end. All numbers come from the 200-seed property run in
`crates/gtlinks-sim/tests/property.rs`: 33,600 runs covering 4 cars, stein counts 10 to 15 and
7 input policies. The report is written to `target/property-report.txt`. Times are run time in
seconds.

## Arming

The finale arms on the first substep where any of these holds. Shares are over all 33,600 runs.

| trigger | share | note |
|---|---|---|
| no downhill progress (z) for 12 s | 79.9 % (26,846) | Includes the no-input, brake and reverse policies, which arm at exactly 12.0 s. |
| run time reaches 100 s | 6.4 % (2,145) | |
| the car enters the arena circle, or passes the arena's uphill edge in z | 5.3 % (1,786) | |

Runs that roll over and come to rest before any of these triggers fire take the early path
below, and the finale never arms (2,823 of 33,600).

## Order of phases and events

Phase values are `state()[25]`. "Same substep" means the events share one `drain_events()`
batch.

1. **`FinaleStart` (8)** and **phase 1 FinaleArmed** begin on the same substep. Player input is
   ignored from then on. No `Hiccup` (11) is ever emitted after this point (asserted in the
   property test). The payload says what the director chose:

   | `b` | meaning | position (`x, y, z`) | `a` | phase sequence |
   |---|---|---|---|---|
   | 0 | final ramp in the arena | leading-edge centre of the final ramp (`ramps[finale.ramp_index]`) | ramp yaw | 1 → 2 → 3 → 4 |
   | 1 | kicker raised ahead of the car | leading-edge centre of the kicker | kicker yaw | 1 → 2 → 3 → 4 |
   | 2 | car already off its wheels (`up.y < 0.5`) | car | 0 | 1 → 3 on the same substep, then 4 |
   | 3 | car already airborne | car | 0 | 1 → 2 on the same substep, then 3 → 4 |

   Shares: of the 30,777 runs that armed, `b=1` 91.0 % (27,994), `b=2` 6.8 % (2,105), `b=0` 1.6 % (504), `b=3` 0.6 % (174).

   **The kicker** is a wedge exactly like `ramp.glb`, scaled to length 11.5 m, width 8.0 m and
   height 2.4 m. Its origin is the leading-edge centre on the ground, and it rises along `a`
   (yaw 0 faces +Z). It exists in the physics from the `FinaleStart` substep onwards, and
   `height_at()` includes it, but it is not in `course_json()`. The front end should spawn it at
   that position, ideally rising from the ground over about 1 s. The director places it at
   least 16 m ahead, usually 26 to 55 m, so the car is never on it when it appears.

2. **Phase 1, FinaleArmed.** The director drives towards the launch at about 26 m/s. If the
   nose is against an obstacle, or the car stalls under throttle, it backs out for 1.5 s with
   the brake held, at most 3 times. Expect `Impact` (3), `PropHit` (4) and `NearMiss` (7)
   along the way. Duration from arming to take-off: min 0.00 s (the `b = 3` path), median 4.00 s, p95 6.64 s, max 9.01 s.
   - **Give-up path:** if the car is not airborne after 9 s, or has moved less than 4 m after
     5 s, the phase goes straight to 3 (7,424; 7,167 of them in the full-throttle, random-steer and alternating policies, which wedge the car in the trees; 257 in the centreline policy and none in the no-input, brake or reverse policies runs).
   - If the car tips past `up.y < 0.3` on the way, the phase also goes straight to 3.

3. **Phase 2, FinaleAirborne.** This begins once the car has left the ground at or beyond the
   middle of the ramp. A `JumpStart` (1) arrives within 0.2 s of the phase change. A roll
   controller turns the car over, but only while nothing touches the ground. The wheels run up
   towards 70 rad/s in the air. Duration: min 0.30 s, median 0.94 s, p95 1.43 s, max 2.43 s. Touchdown was roof-first (`up.y < -0.5`)
   in 18,136 of 21,111 flights (85.9 %).

4. **Touchdown: phase 3 Settling** begins with, in order:
   - `Landing` (2), with `b` = airtime;
   - `Impact` (3), terrain;
   - `PartDetached` (10), one or two of them, bringing the total to at least two. On a roof
     landing these are `mirror_l` (3) and then `mirror_r` (4) unless they have already gone.

   During Settling the car slides on its roof with ordinary contact physics. If the roll drifts
   more than 20° from fully inverted, a clamped torque holds it back. More `Landing` and
   `Impact` events can follow as it bounces. Wheel spin decays with a 3 s time constant while
   inverted. Settling backstops, in order:
   - from 4 s, a stronger righting torque (5,127 runs);
   - from 8 s, rest damping (2,378 runs);
   - from 11 s, the car is placed inverted kinematically (70 runs).

   Duration from touchdown to Wrecked: min 0.10 s, median 5.26 s, p95 8.63 s, max 12.19 s.

5. **`Wrecked` (9) and phase 4 Wrecked** begin on the same substep, 1.0 s after the car first
   satisfies `up.y < -0.9` and speed `< 0.1 m/s`. If fewer than two parts have detached by then
   (early path only), the missing `PartDetached` events come first in the same batch. From this
   substep:
   - the pose is frozen bit for bit, and `state()[0..7]` never changes again;
   - linear and angular velocity are exactly zero;
   - `state()[35]` counts up from 0;
   - no further events are emitted.

6. **After Wrecked.** Each wheel spins down linearly from its speed at the wreck and reaches
   exactly zero **6.0 s** later (`state()[14 + 3i]` stops changing). Wheels that had already
   stopped stay at 0. Measured spin-down: 6.0 s in every run whose wheels were still turning; the median is 6.01 s, including one substep.

## Durations, arming to Wrecked

| span | min | median | p95 | max |
|---|---|---|---|---|
| FinaleArmed → FinaleAirborne | 0.00 | 4.00 | 6.64 | 9.01 |
| FinaleAirborne → Settling | 0.30 | 0.94 | 1.43 | 2.43 |
| Settling → Wrecked | 0.10 | 5.26 | 8.63 | 12.19 |
| FinaleArmed → Wrecked | 0.10 | 11.16 | 16.29 | 21.14 |

Overall time to Wrecked from the start of the run: min 11.4 s, median 32.1 s, p95 108.9 s, max 121.0 s. All 33,600 runs reached Wrecked
within 150 s and held the pose for 10 s.

## Early rollover path

At any time, in any phase, a car that has been inverted (`up.y < -0.9`) and slow
(`< 0.1 m/s`) for 1.0 s becomes Wrecked. From Driving the sequence is the tumble's own
`Impact`/`Landing` events, then top-up `PartDetached` events if fewer than two parts have gone,
then `Wrecked`, with no `FinaleStart` and no phases 1 to 3. This happened in 2,823 of 33,600
runs. A car that comes to rest on its side or wheels instead waits for the 12 s stall rule,
then arms with `b = 2` and is turned onto its roof in Settling.

## Parts and damage during the run

Damage (`state()[26]`) builds from prop impacts (0.03 + 0.12 × impulse), hard terrain hits
(0.08 × impulse) and heavy landings (+0.03). The finale touchdown adds 0.12. Parts detach as
damage crosses 0.18, 0.32, 0.50, 0.70 and 0.85. Each detachment emits `PartDetached`, choosing
the part that faces the hit: front gives `bumper_front` or `bonnet`, rear gives `bumper_rear`,
and the sides give the mirrors. Every run ends with at least two parts detached. Parts by the
end of the run: min 2, median 2, mean 2.67, max 5.
