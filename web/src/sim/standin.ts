/**
 * STAND-IN SIMULATION. Delete this file at integration.
 *
 * A deliberately minimal implementation of the contract's Game interface so every screen,
 * camera and effect can be exercised before the Rust wasm package lands: a tilted plane with
 * bumps, a kinematic car, and phases that advance on a timer to Wrecked with the car inverted.
 * It performs no real physics. It is only selected when web/src/wasm/pkg is absent.
 */
import { Matrix4, Quaternion, Vector3 } from 'three/webgpu';
import { CELL, NX, NZ, STATE_LEN, S, X0, EventKind, Phase, Surface, PropKind } from './types';
import type { Course, CourseProp, CourseRamp, Game } from './types';

function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const node = (x: number, z: number) =>
  520 - 0.2 * z + 3.2 * Math.sin(x * 0.045 + z * 0.01) * Math.cos(z * 0.031) + 0.0008 * x * x * 0.5;

const HOLE_LEN = 260;
const hole0Z = 150;

export class StandInGame implements Game {
  private course: Course;
  private heights = new Float32Array(NX * NZ);
  private surfaces = new Uint8Array(NX * NZ);
  private t = 0;
  private pos = new Vector3();
  private yaw = 0;
  private speed = 0;
  private steerApplied = 0;
  private spin = 0;
  private events: number[] = [];
  private rand: () => number;
  private phase = Phase.Driving;
  private wreckedAt = -1;
  private roll = 0;
  private lastHole = -1;
  private nextHiccup = 4;
  private trick = 0;
  private lastTrick = 0;
  private lastNear = 0;
  private hitProps = new Set<number>();
  private readonly steins: number;

  constructor(seed: number, _carId: number, steins: number) {
    this.rand = rng(seed ^ 0x9e3779b9);
    this.steins = Math.max(10, Math.min(15, steins));
    for (let iz = 0; iz < NZ; iz++) for (let ix = 0; ix < NX; ix++) this.heights[iz * NX + ix] = node(X0 + ix * CELL, iz * CELL);
    this.course = this.buildCourse(seed);
    this.paintSurfaces();
    const sp = this.course.start.pos;
    this.pos.set(sp[0], this.height_at(sp[0], sp[2]), sp[2]);
    this.yaw = 0;
  }

  private buildCourse(seed: number): Course {
    const r = rng(seed);
    const holes: Course['holes'] = [];
    for (let i = 0; i < 9; i++) {
      const z0 = hole0Z + i * HOLE_LEN;
      const sway = (r() - 0.5) * 60;
      const cl: [number, number, number][] = [];
      for (let k = 0; k <= 23; k++) {
        const z = z0 + k * 10;
        const x = sway * Math.sin((k / 23) * Math.PI);
        cl.push([x, node(x, z) + 0, z]);
      }
      const g = cl[cl.length - 1];
      holes.push({ index: i, par: 3 + Math.floor(r() * 3), tee: [cl[0][0], cl[0][1], cl[0][2]], green: [g[0], g[1], g[2]], green_radius: 14, centreline: cl, fairway_half_width: 22 });
    }
    const props: CourseProp[] = [];
    const ramps: CourseRamp[] = [];
    for (const h of holes) {
      props.push({ kind: PropKind.Flag, pos: [...h.green], yaw: 0, scale: 1 });
      props.push({ kind: PropKind.TeeMarker, pos: [h.tee[0] - 4, h.tee[1], h.tee[2]], yaw: 0, scale: 1 });
      props.push({ kind: PropKind.TeeMarker, pos: [h.tee[0] + 4, h.tee[1], h.tee[2]], yaw: 0, scale: 1 });
      props.push({ kind: PropKind.Sign, pos: [h.tee[0] + 9, h.tee[1], h.tee[2] + 4], yaw: -0.4, scale: 1 });
      for (let k = 0; k < 26; k++) {
        const c = h.centreline[Math.floor(r() * h.centreline.length)];
        const side = r() < 0.5 ? -1 : 1;
        const x = c[0] + side * (h.fairway_half_width + 4 + r() * 40);
        const z = c[2] + (r() - 0.5) * 20;
        props.push({ kind: r() < 0.6 ? PropKind.Pine : PropKind.Broadleaf, pos: [x, node(x, z), z], yaw: r() * 6, scale: 0.8 + r() * 0.7 });
      }
      for (let k = 0; k < 6; k++) {
        const x = h.green[0] + (r() - 0.5) * 40;
        const z = h.green[2] - 10 - r() * 14;
        props.push({ kind: PropKind.Spectator, pos: [x, node(x, z), z], yaw: r() * 6, scale: 1 });
      }
      for (let k = 0; k < 3; k++) {
        const x = h.green[0] + (r() < 0.5 ? -1 : 1) * (28 + r() * 20);
        const z = h.green[2] - r() * 90;
        props.push({ kind: k === 0 ? PropKind.Cart : PropKind.Rock, pos: [x, node(x, z), z], yaw: r() * 6, scale: 0.8 + r() });
      }
      const rc = h.centreline[10];
      ramps.push({ pos: [rc[0], rc[1], rc[2]], yaw: 0, length: 9, width: 6, height: 2.2 });
    }
    const lg = holes[8].green;
    return {
      seed,
      start: { pos: [-10, node(-10, 62), 62], yaw: 0 },
      lodge: { pos: [0, node(0, 40), 40], yaw: 0 },
      holes, props, ramps,
      finale: { pos: [lg[0], lg[1], lg[2] + 120], radius: 60 },
    };
  }

  private paintSurfaces(): void {
    for (let iz = 0; iz < NZ; iz++) {
      for (let ix = 0; ix < NX; ix++) {
        const x = X0 + ix * CELL, z = iz * CELL;
        let s: Surface = Surface.Rough;
        for (const h of this.course.holes) {
          const dg = Math.hypot(x - h.green[0], z - h.green[2]);
          const dt = Math.hypot(x - h.tee[0], z - h.tee[2]);
          if (dg < h.green_radius) { s = Surface.Green; break; }
          if (Math.hypot(x - h.green[0] - 22, z - h.green[2] + 6) < 7) { s = Surface.Bunker; break; }
          if (dt < 8) { s = Surface.Tee; break; }
          if (z >= h.tee[2] && z <= h.green[2]) {
            const c = h.centreline[Math.min(h.centreline.length - 1, Math.round((z - h.tee[2]) / 10))];
            if (Math.abs(x - c[0]) < h.fairway_half_width) { s = Surface.Fairway; break; }
            if (Math.abs(x - c[0] - h.fairway_half_width - 4) < 1.2) { s = Surface.CartPath; break; }
          }
        }
        const dx = this.heights[iz * NX + Math.min(NX - 1, ix + 1)] - this.heights[iz * NX + ix];
        if (Math.abs(dx) / CELL > 0.7) s = Surface.Rock;
        this.surfaces[iz * NX + ix] = s;
      }
    }
  }

  course_json(): string { return JSON.stringify(this.course); }
  heightfield(): Float32Array { return this.heights; }
  surface_map(): Uint8Array { return this.surfaces; }

  height_at(x: number, z: number): number {
    const fx = (x - X0) / CELL, fz = z / CELL;
    const ix = Math.max(0, Math.min(NX - 2, Math.floor(fx))), iz = Math.max(0, Math.min(NZ - 2, Math.floor(fz)));
    const u = Math.max(0, Math.min(1, fx - ix)), v = Math.max(0, Math.min(1, fz - iz));
    const h = (a: number, b: number) => this.heights[(iz + b) * NX + ix + a];
    const base = u >= v ? h(0, 0) + (h(1, 0) - h(0, 0)) * u + (h(1, 1) - h(1, 0)) * v : h(0, 0) + (h(1, 1) - h(0, 1)) * u + (h(0, 1) - h(0, 0)) * v;
    let ramp = 0;
    for (const rp of this.course.ramps) {
      const dx = Math.abs(x - rp.pos[0]), dz = z - rp.pos[2];
      if (dx < rp.width / 2 && dz > 0 && dz < rp.length) ramp = Math.max(ramp, rp.height * (dz / rp.length));
    }
    return base + ramp;
  }

  private emit(kind: EventKind, a: number, b: number, x = this.pos.x, y = this.pos.y, z = this.pos.z): void {
    this.events.push(kind, a, b, x, y, z);
  }

  step(dt: number, steer: number, throttle: number, brake: number, handbrake: boolean): void {
    dt = Math.min(0.1, Math.max(0, dt));
    this.t += dt;
    const sev = (this.steins - 10) / 5;
    const autopilot = this.phase !== Phase.Driving;
    if (autopilot) { steer = 0; throttle = 0.5; brake = 0; }
    const lag = 0.12 + sev * 0.33;
    this.steerApplied += (steer * (0.95 - sev * 0.25) - this.steerApplied) * Math.min(1, dt / lag);
    if (this.phase < Phase.Settling) {
      this.speed += (throttle * 32 - brake * 24 - (handbrake ? 14 : 0) - this.speed * 0.05) * dt * (throttle > 0 ? 0.5 : 1);
      this.speed = Math.max(0, Math.min(36, this.speed));
    } else {
      this.speed *= Math.exp(-dt * 1.6);
    }
    this.yaw += this.steerApplied * this.speed * 0.03 * dt * 6;
    this.pos.x += Math.sin(this.yaw) * this.speed * dt;
    this.pos.z += Math.cos(this.yaw) * this.speed * dt;
    this.pos.x = Math.max(-300, Math.min(300, this.pos.x));
    this.spin += (this.speed / 0.4) * dt * (this.phase === Phase.Wrecked ? Math.max(0, 1 - (this.t - this.wreckedAt) / 6) : 1);
    const ground = this.height_at(this.pos.x, this.pos.z);
    this.pos.y = ground;

    // timed phases (stand-in only)
    const T = this.t;
    if (this.phase === Phase.Driving && T > 24) { this.phase = Phase.FinaleArmed; this.emit(EventKind.FinaleStart, 0, 0); }
    else if (this.phase === Phase.FinaleArmed && T > 27) this.phase = Phase.FinaleAirborne;
    else if (this.phase === Phase.FinaleAirborne && T > 29) { this.phase = Phase.Settling; this.emit(EventKind.Landing, 18, 1.4); this.emit(EventKind.Impact, 0.9, 0); }
    else if (this.phase === Phase.Settling && T > 31) {
      this.phase = Phase.Wrecked; this.wreckedAt = T; this.speed = 0;
      this.emit(EventKind.Wrecked, 0, 0);
      this.emit(EventKind.PartDetached, 0, 0);
      this.emit(EventKind.PartDetached, 3, 0);
    }
    if (this.phase === Phase.FinaleAirborne) this.roll = Math.min(Math.PI, this.roll + dt * Math.PI * 0.7);
    if (this.phase >= Phase.Settling) this.roll = Math.PI;
    if (this.phase === Phase.FinaleAirborne) this.pos.y += Math.sin(((T - 27) / 2) * Math.PI) * 4;
    if (this.phase >= Phase.Settling) this.pos.y = ground + 0.9;

    const hole = Math.max(0, Math.min(8, Math.floor((this.pos.z - hole0Z) / HOLE_LEN)));
    if (hole !== this.lastHole && this.pos.z > hole0Z) { this.lastHole = hole; this.emit(EventKind.HoleEntered, hole, 0); }
    // knock flags, tee markers and signs the car passes close to
    if (this.phase < Phase.Settling) {
      this.course.props.forEach((p, i) => {
        if ((p.kind === PropKind.Flag || p.kind === PropKind.TeeMarker || p.kind === PropKind.Sign) && !this.hitProps.has(i)
          && Math.abs(p.pos[2] - this.pos.z) < 5 && Math.abs(p.pos[0] - this.pos.x) < 8) {
          this.hitProps.add(i);
          this.emit(EventKind.PropHit, i, p.kind, p.pos[0], p.pos[1], p.pos[2]);
        }
      });
    }
    if (this.phase === Phase.Driving) {
      if (T > this.nextHiccup) { this.emit(EventKind.Hiccup, 0.5, 0); this.nextHiccup = T + 3 + this.rand() * 6; }
      if (this.speed > 18 && T - this.lastTrick > 6) { this.lastTrick = T; this.trick += 150; this.emit(EventKind.Trick, 1, 150); }
      if (this.speed > 10 && T - this.lastNear > 5) {
        const sp = this.course.props.findIndex((p, i) => p.kind === PropKind.Spectator && p.pos[2] > this.pos.z && p.pos[2] < this.pos.z + 80 && i >= 0);
        if (sp >= 0) { this.lastNear = T; this.emit(EventKind.NearMiss, sp, 0, ...this.course.props[sp].pos); }
      }
    }
  }

  state(): Float32Array {
    const f = new Float32Array(STATE_LEN);
    const fwd = new Vector3(Math.sin(this.yaw), 0, Math.cos(this.yaw));
    const e = 1.5;
    const gz1 = this.height_at(this.pos.x + fwd.x * e, this.pos.z + fwd.z * e);
    const gz0 = this.height_at(this.pos.x - fwd.x * e, this.pos.z - fwd.z * e);
    const left = new Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw));
    const gl = this.height_at(this.pos.x + left.x * e, this.pos.z + left.z * e);
    const gr = this.height_at(this.pos.x - left.x * e, this.pos.z - left.z * e);
    const f3 = fwd.clone().setY((gz1 - gz0) / (2 * e)).normalize();
    const l3 = left.clone().setY((gl - gr) / (2 * e)).normalize();
    const up = new Vector3().crossVectors(f3, l3).normalize();
    const l4 = new Vector3().crossVectors(up, f3).normalize();
    const q = new Quaternion().setFromRotationMatrix(new Matrix4().makeBasis(l4, up, f3));
    if (this.roll !== 0) q.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), this.roll));
    f[S.px] = this.pos.x; f[S.py] = this.pos.y + 0.0; f[S.pz] = this.pos.z;
    f[S.qx] = q.x; f[S.qy] = q.y; f[S.qz] = q.z; f[S.qw] = q.w;
    f[S.vx] = fwd.x * this.speed; f[S.vy] = 0; f[S.vz] = fwd.z * this.speed;
    for (let i = 0; i < 4; i++) {
      const o = S.wheel0 + i * 3;
      f[o] = 0.05 + 0.03 * Math.sin(this.t * 3 + i);
      f[o + 1] = this.spin;
      f[o + 2] = i < 2 ? this.steerApplied * 0.45 : 0;
    }
    f[S.phase] = this.phase;
    f[S.damage] = this.phase === Phase.Wrecked ? 0.35 : 0;
    f[S.runTime] = this.t;
    f[S.hole] = Math.max(0, this.lastHole);
    f[S.speed] = this.speed;
    f[S.wheelsOnGround] = this.phase === Phase.FinaleAirborne ? 0 : 4;
    f[S.airtime] = this.phase === Phase.FinaleAirborne ? this.t - 27 : 0;
    f[S.appliedSteer] = this.steerApplied;
    f[S.wobble] = this.phase === Phase.Driving ? Math.min(1, ((this.steins - 10) / 5) * 0.6 + 0.2) * Math.abs(Math.sin(this.t * 2)) : 0.1;
    f[S.trick] = this.trick;
    f[S.wreckedFor] = this.phase === Phase.Wrecked ? this.t - this.wreckedAt : 0;
    return f;
  }

  drain_events(): Float32Array {
    const out = new Float32Array(this.events);
    this.events = [];
    return out;
  }
}
