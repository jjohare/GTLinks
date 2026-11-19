/**
 * Front-end stand-in for the police and helicopter simulation (contract 6b and 6c).
 *
 * It is used only for the parts the loaded simulation does not provide (feature-detected per method), so every
 * intermediate deploy works. It reads the car's state() and emits the same events and buffers the real
 * simulation will: units trail the car's actual path, then circle and park around the wreck; the helicopter flies
 * in, tracks with a lagging spotlight, then orbits the wreck the other way. Delete once the simulation owns both.
 */
import { decodeState, EventKind, HELI_LEN, HeliMode, Phase, POLICE_COUNT, POLICE_STRIDE, PoliceMode } from './types';
import type { BaseGame } from './types';

interface Unit { joined: boolean; pos: [number, number, number]; yaw: number; speed: number; spin: number; mode: PoliceMode; steer: number; ang: number; stopped: boolean }

const JOIN_AT = [15, 16.5, 18];
const TRAIL_BACK = [20, 30, 40];

export class FallbackPursuit {
  private units: Unit[] = Array.from({ length: POLICE_COUNT }, () => ({ joined: false, pos: [0, 0, 0], yaw: 0, speed: 0, spin: 0, mode: PoliceMode.Absent, steer: 0, ang: 0, stopped: false }));
  private trail: { t: number; x: number; y: number; z: number; yaw: number }[] = [];
  private events: number[] = [];
  private heli = { joined: false, pos: [0, 0, 0] as [number, number, number], aim: [0, 0, 0] as [number, number, number], rotor: 0, yaw: 0, mode: HeliMode.Absent, lock: 0, orbit: 0, speed: 0, vel: [0, 0, 0] as [number, number, number] };
  private wreckT = 0;
  private circling = false;
  private parked = false;
  private last = { x: 0, z: 0, has: false };

  constructor(private inner: BaseGame, private wantPolice: boolean, private wantHeli: boolean) {}

  private emit(kind: EventKind, a: number, x: number, y: number, z: number): void { this.events.push(kind, a, 0, x, y, z); }
  drain(): number[] { const e = this.events; this.events = []; return e; }

  tick(dt: number): void {
    const s = decodeState(this.inner.state());

    const car = s.pos;
    const yaw = Math.atan2(s.vel[0], s.vel[2]);
    const wrecked = s.phase === Phase.Wrecked;
    const hAt = (x: number, z: number) => this.inner.height_at(x, z);
    if (!wrecked && (!this.last.has || Math.hypot(car[0] - this.last.x, car[2] - this.last.z) > 1.2)) {
      this.trail.push({ t: s.runTime, x: car[0], y: car[1], z: car[2], yaw: Math.hypot(s.vel[0], s.vel[2]) > 2 ? yaw : (this.trail.at(-1)?.yaw ?? 0) });
      this.last = { x: car[0], z: car[2], has: true };
      if (this.trail.length > 600) this.trail.shift();
    }
    if (wrecked) this.wreckT = s.wreckedFor;
    const holes = s.hole;
    if (this.wantPolice) this.tickPolice(dt, s.runTime, holes, car, wrecked, hAt);
    if (this.wantHeli) this.tickHeli(dt, car, wrecked, hAt, s.runTime);
  }

  private tickPolice(dt: number, runTime: number, hole: number, car: [number, number, number], wrecked: boolean, hAt: (x: number, z: number) => number): void {
    this.units.forEach((u, i) => {
      if (!u.joined && (wrecked || runTime >= JOIN_AT[i] || (i === 0 && hole >= 2))) {
        u.joined = true; u.mode = PoliceMode.Pursuing;
        const back = this.trail.at(0) ?? { x: car[0], z: car[2] - 30, y: car[1], yaw: 0, t: 0 };
        if (wrecked) { u.ang = (i / POLICE_COUNT) * Math.PI * 2; u.pos = [car[0] + Math.cos(u.ang) * 90, 0, car[2] + Math.sin(u.ang) * 90]; }
        else u.pos = [back.x, 0, back.z];
        this.emit(EventKind.PoliceJoined, i, u.pos[0], u.pos[1], u.pos[2]);
      }
      if (!u.joined) return;
      const prev: [number, number, number] = [u.pos[0], u.pos[1], u.pos[2]];
      if (!wrecked) {
        // follow the recorded trail 20, 30 and 40 m back along the path the car actually drove, fanned sideways
        let acc = 0, p = this.trail[0];
        let prevPt = { x: car[0], z: car[2] };
        for (let k = this.trail.length - 1; k >= 0; k--) {
          const q = this.trail[k];
          acc += Math.hypot(q.x - prevPt.x, q.z - prevPt.z);
          prevPt = q; p = q;
          if (acc >= TRAIL_BACK[i]) break;
        }
        if (p) {
          const side = (i - 1) * 3;
          const tx = p.x + Math.cos(p.yaw) * side, tz = p.z - Math.sin(p.yaw) * side;
          u.pos[0] += (tx - u.pos[0]) * Math.min(1, dt * 4); u.pos[2] += (tz - u.pos[2]) * Math.min(1, dt * 4); u.yaw = p.yaw;
        }
      } else {
        if (!this.circling) { this.circling = true; this.emit(EventKind.PoliceCircling, 0, car[0], car[1], car[2]); }
        const k = Math.min(1, this.wreckT / 3);
        const radius = 14 + (1 - k) * 70;
        if (this.wreckT < 8) { u.mode = PoliceMode.Circling; u.ang += (22 / 14) * dt; }
        else if (!u.stopped) { u.stopped = true; u.mode = PoliceMode.Parked; }
        const tx = car[0] + Math.cos(u.ang) * radius, tz = car[2] + Math.sin(u.ang) * radius;
        u.pos[0] += (tx - u.pos[0]) * Math.min(1, dt * 6); u.pos[2] += (tz - u.pos[2]) * Math.min(1, dt * 6);
        u.yaw = u.mode === PoliceMode.Parked ? Math.atan2(car[0] - u.pos[0], car[2] - u.pos[2]) : Math.atan2(-Math.sin(u.ang), Math.cos(u.ang)) ;
      }
      u.pos[1] = hAt(u.pos[0], u.pos[2]);
      const mv = Math.hypot(u.pos[0] - prev[0], u.pos[2] - prev[2]);
      u.speed = dt > 0 ? mv / dt : 0;
      u.spin += (u.speed / 0.36) * dt;
      u.steer = u.mode === PoliceMode.Circling ? 0.25 : 0;
    });
    if (wrecked && !this.parked && this.units.every((u) => u.mode === PoliceMode.Parked)) {
      this.parked = true;
      this.emit(EventKind.PoliceParked, 0, car[0], car[1], car[2]);
    }
  }

  private tickHeli(dt: number, car: [number, number, number], wrecked: boolean, hAt: (x: number, z: number) => number, runTime: number): void {
    const h = this.heli;
    if (!h.joined && (this.units[0].joined || runTime >= JOIN_AT[0])) {
      h.joined = true; h.mode = HeliMode.Inbound;
      h.pos = [car[0] + 60, car[1] + 80, car[2] + 450]; h.aim = [car[0], car[1], car[2]];
      this.emit(EventKind.HeliJoined, 0, h.pos[0], h.pos[1], h.pos[2]);
    }
    if (!h.joined) return;
    const prev = [...h.pos] as [number, number, number];
    let target: [number, number, number];
    if (wrecked) {
      h.mode = HeliMode.Orbiting; h.orbit -= (0.35) * dt;
      // low hover round the wreck so the drone camera (which sits low and looks down) can see it
      target = [car[0] + Math.cos(h.orbit) * 21, car[1] + 15, car[2] + Math.sin(h.orbit) * 21];
      h.aim = [car[0], hAt(car[0], car[2]), car[2]]; h.lock = 1;
    } else {
      h.mode = Math.hypot(car[0] - h.pos[0], car[2] - h.pos[2]) > 120 ? HeliMode.Inbound : HeliMode.Tracking;
      const cy = this.trail.at(-1)?.yaw ?? 0;
      target = [car[0] - Math.sin(cy) * 25, car[1] + 45, car[2] - Math.cos(cy) * 25];
      h.aim[0] += (car[0] - h.aim[0]) * Math.min(1, dt * 1.6); h.aim[2] += (car[2] - h.aim[2]) * Math.min(1, dt * 1.6);
      h.aim[1] = hAt(h.aim[0], h.aim[2]);
      h.lock = Math.max(0, 1 - Math.hypot(h.aim[0] - car[0], h.aim[2] - car[2]) / 22);
      h.orbit = Math.atan2(h.pos[2] - car[2], h.pos[0] - car[0]);
    }
    const k = Math.min(1, dt * (wrecked ? 1.5 : 0.8));
    h.pos[0] += (target[0] - h.pos[0]) * k; h.pos[1] += (Math.max(target[1], hAt(h.pos[0], h.pos[2]) + (wrecked ? 11 : 30)) - h.pos[1]) * k; h.pos[2] += (target[2] - h.pos[2]) * k;
    h.vel = [(h.pos[0] - prev[0]) / Math.max(dt, 1e-3), (h.pos[1] - prev[1]) / Math.max(dt, 1e-3), (h.pos[2] - prev[2]) / Math.max(dt, 1e-3)];
    h.speed = Math.hypot(h.vel[0], h.vel[2]);
    if (h.speed > 1) h.yaw = Math.atan2(h.vel[0], h.vel[2]);
    h.rotor += 38 * dt;
  }

  policeState(): Float32Array {
    const f = new Float32Array(POLICE_COUNT * POLICE_STRIDE);
    const car = decodeState(this.inner.state()).pos;
    this.units.forEach((u, i) => {
      const o = i * POLICE_STRIDE;
      const half = u.yaw * 0.5;
      f[o] = u.pos[0]; f[o + 1] = u.pos[1]; f[o + 2] = u.pos[2];
      f[o + 3] = 0; f[o + 4] = Math.sin(half); f[o + 5] = 0; f[o + 6] = Math.cos(half);
      f[o + 7] = u.speed; f[o + 8] = u.steer; f[o + 9] = u.spin; f[o + 10] = u.mode; f[o + 11] = u.joined ? 1 : 0;
      f[o + 12] = u.mode === PoliceMode.Circling ? 0.05 : 0; f[o + 13] = Math.hypot(u.pos[0] - car[0], u.pos[2] - car[2]);
    });
    return f;
  }

  heliState(): Float32Array {
    const f = new Float32Array(HELI_LEN);
    const h = this.heli;
    const bank = Math.max(-0.35, Math.min(0.35, h.mode === HeliMode.Orbiting ? -0.25 : 0.08));
    const qy = { x: 0, y: Math.sin(h.yaw / 2), z: 0, w: Math.cos(h.yaw / 2) };
    const qz = { x: 0, y: 0, z: Math.sin(bank / 2), w: Math.cos(bank / 2) };
    // quaternion product qy * qz
    const q = { x: qy.w * qz.x + qy.x * qz.w + qy.y * qz.z - qy.z * qz.y, y: qy.w * qz.y - qy.x * qz.z + qy.y * qz.w + qy.z * qz.x, z: qy.w * qz.z + qy.x * qz.y - qy.y * qz.x + qy.z * qz.w, w: qy.w * qz.w - qy.x * qz.x - qy.y * qz.y - qy.z * qz.z };
    f[0] = h.pos[0]; f[1] = h.pos[1]; f[2] = h.pos[2]; f[3] = q.x; f[4] = q.y; f[5] = q.z; f[6] = q.w;
    f[7] = h.aim[0]; f[8] = h.aim[1]; f[9] = h.aim[2]; f[10] = h.mode; f[11] = h.joined ? 1 : 0; f[12] = h.rotor; f[13] = h.lock; f[14] = h.speed;
    return f;
  }
}
