import { PerspectiveCamera, Vector3, Quaternion, MathUtils } from 'three/webgpu';
import type { Game, RenderState } from '../sim/types';

const damp = (a: number, b: number, lambda: number, dt: number) => a + (b - a) * (1 - Math.exp(-lambda * dt));

export type CamMode = 'lodge' | 'chase' | 'drone';

/** Camera director: lodge glide, speed-aware chase, and the broadcast drone. All smoothing lives here. */
export class CameraRig {
  readonly camera = new PerspectiveCamera(48, 1, 0.3, 3600);
  mode: CamMode = 'lodge';
  private look = new Vector3();
  private pos = new Vector3();
  private heading = new Vector3(0, 0, 1);
  private fov = 48;
  private shake = 0;
  private t = 0;
  private roll = 0;
  private tmp = new Vector3();
  private tmp2 = new Vector3();
  private q = new Quaternion();
  private snap = true;
  private droneAngle = 0;
  private droneBase = new Vector3();
  /** Test hook: pins the camera to a fixed pose (null releases it). */
  pinned: { pos: Vector3; look: Vector3; fov: number } | null = null;

  constructor() {
    this.camera.position.set(0, 600, 0);
  }

  resize(w: number, h: number): void {
    this.camera.aspect = w / h;
    // keep the framing readable on portrait screens
    this.camera.updateProjectionMatrix();
  }

  /** Apply the test pin after any mode update. */
  applyPin(): void {
    if (!this.pinned) return;
    this.camera.position.copy(this.pinned.pos);
    this.camera.lookAt(this.pinned.look);
    if (this.camera.fov !== this.pinned.fov) { this.camera.fov = this.pinned.fov; this.camera.updateProjectionMatrix(); }
  }

  /** Hard cut: the next update snaps instead of gliding. */
  cut(mode: CamMode): void { this.mode = mode; this.snap = true; }

  kick(amount: number): void { this.shake = Math.min(1.2, this.shake + amount); }

  private apply(dt: number, goalPos: Vector3, goalLook: Vector3, goalFov: number, posRate: number, lookRate: number, groundY: number | null): void {
    if (this.snap) { this.pos.copy(goalPos); this.look.copy(goalLook); this.fov = goalFov; this.snap = false; }
    else {
      this.pos.x = damp(this.pos.x, goalPos.x, posRate, dt);
      this.pos.y = damp(this.pos.y, goalPos.y, posRate, dt);
      this.pos.z = damp(this.pos.z, goalPos.z, posRate, dt);
      this.look.x = damp(this.look.x, goalLook.x, lookRate, dt);
      this.look.y = damp(this.look.y, goalLook.y, lookRate, dt);
      this.look.z = damp(this.look.z, goalLook.z, lookRate, dt);
      this.fov = damp(this.fov, goalFov, 3, dt);
    }
    if (groundY !== null && this.pos.y < groundY) this.pos.y = groundY;
    this.camera.position.copy(this.pos);
    this.camera.lookAt(this.look);
    if (this.roll !== 0) this.camera.rotateZ(this.roll);
    if (Math.abs(this.camera.fov - this.fov) > 0.01) { this.camera.fov = this.fov; this.camera.updateProjectionMatrix(); }
  }

  /** Lodge: sit on the terrace, glide the aim towards the selected car while keeping the table in frame. */
  updateLodge(dt: number, home: Vector3, carPos: Vector3, table: Vector3, rowCentre: Vector3, game: Game): void {
    this.t += dt;
    // aim half way between the middle of the row and the chosen car, so the car glides into focus
    // while the table (straight ahead, low in frame) stays visible for dragging
    const goalLook = this.tmp.copy(rowCentre).lerp(carPos, 0.3).add(this.tmp2.set(0, -0.6, 0)).lerp(table, 0.24);
    const goalPos = this.tmp2.copy(home);
    goalPos.x += (carPos.x - home.x) * 0.04; goalPos.z += (carPos.z - home.z) * 0.06;
    goalPos.z += 0.5 + Math.sin(this.t * 0.35) * 0.08;
    goalPos.y += Math.sin(this.t * 0.5) * 0.03;
    this.roll = 0;
    this.shake = 0;
    this.apply(dt, goalPos, goalLook, this.camera.aspect < 1 ? 62 : 47, 2.4, 3.2, game.height_at(home.x, home.z) + 1.0);
  }

  /** Chase camera behind the direction of travel; robust through jumps, flips and tumbles. */
  updateChase(dt: number, st: RenderState, game: Game, steinCount: number): void {
    this.t += dt;
    const p = this.tmp.set(st.pos[0], st.pos[1], st.pos[2]);
    const spd = Math.abs(st.speed);
    // heading from velocity when moving (flips do not spin the camera), else from the body
    const hv = this.tmp2.set(st.vel[0], 0, st.vel[2]);
    if (hv.length() > 3) hv.normalize();
    else { this.q.set(st.quat[0], st.quat[1], st.quat[2], st.quat[3]); hv.set(0, 0, 1).applyQuaternion(this.q).setY(0).normalize(); if (hv.lengthSq() < 0.1) hv.copy(this.heading); }
    this.heading.lerp(hv, 1 - Math.exp(-2.6 * dt)).normalize();

    const dist = 7.6 + spd * 0.05 + (st.airtime > 0 ? 1.6 : 0);
    const h = 2.7 + spd * 0.012;
    const goalPos = new Vector3(p.x - this.heading.x * dist, p.y + h, p.z - this.heading.z * dist);
    // while airborne hold the camera near the launch altitude so the car arcs through the frame
    const ground = game.height_at(p.x, p.z);
    if (st.airtime > 0) goalPos.y = Math.max(goalPos.y - Math.min(3, st.airtime * 2.2), ground + 3.2);
    const goalLook = new Vector3(p.x + this.heading.x * (4 + spd * 0.12), p.y + 1.2, p.z + this.heading.z * (4 + spd * 0.12));
    const fov = 58 + MathUtils.clamp(spd * 0.55, 0, 24);

    this.shake = damp(this.shake, 0, 4, dt);
    const sh = (0.02 + Math.min(1, spd / 45) * 0.04 + this.shake * 0.35 + (st.wheelsOnGround < 4 ? 0 : 0.01));
    this.roll = Math.sin(this.t * 1.7) * 0.05 * st.wobble * (0.4 + steinCount / 15) + Math.sin(this.t * 31) * sh * 0.05;
    this.apply(dt, goalPos, goalLook, fov, 6.0, 9, null);

    // never under the terrain: test several points along the segment from the car to the camera
    for (let i = 1; i <= 6; i++) {
      const u = i / 6;
      const x = MathUtils.lerp(p.x, this.pos.x, u), z = MathUtils.lerp(p.z, this.pos.z, u);
      const gy = game.height_at(x, z) + 1.0;
      const yy = MathUtils.lerp(p.y + 1, this.pos.y, u);
      if (yy < gy) this.pos.y += (gy - yy) / Math.max(0.3, u);
    }
    this.camera.position.copy(this.pos);
    this.camera.position.x += Math.sin(this.t * 53) * sh * 0.5;
    this.camera.position.y += Math.cos(this.t * 47) * sh * 0.5;
    this.camera.lookAt(this.look);
    if (this.roll) this.camera.rotateZ(this.roll);
  }

  /**
   * Wreck-cam drone: a slow panoramic orbit, then a pull-up and away.
   * `t` is the contract's time-since-Wrecked; `orbit` and `pull` are durations in seconds.
   */
  updateDrone(dt: number, t: number, car: Vector3, game: Game, orbit: number, pull: number, solids: { x: number; z: number; r: number; h: number }[] = []): void {
    this.t += dt;
    if (this.snap) {
      // start the arc from the side the car faces away from the previous chase heading
      this.droneAngle = Math.atan2(-this.heading.x, -this.heading.z) + 0.9;
      this.droneBase.copy(car);
    }
    const o = Math.min(1, t / orbit);
    const pu = MathUtils.clamp((t - orbit) / pull, 0, 1);
    const e = pu * pu * (3 - 2 * pu);
    const ang = this.droneAngle + t * 0.3;
    const radius = MathUtils.lerp(MathUtils.lerp(18, 12, Math.sin(o * Math.PI * 0.5)), 150, e);
    const alt = MathUtils.lerp(2.0 + Math.sin(o * Math.PI) * 2.4 + Math.sin(t * 0.9) * 0.25, 95, e);
    const centre = this.tmp.copy(car).add(this.tmp2.set(0, 0.8, 0));
    const goalPos = new Vector3(centre.x + Math.sin(ang) * radius, centre.y + alt, centre.z + Math.cos(ang) * radius);
    const gy = game.height_at(goalPos.x, goalPos.z) + 2.0;
    if (goalPos.y < gy) goalPos.y = gy;
    // keep the lens out of foliage: rise over any tree the orbit would pass through
    for (const o of solids) if (Math.hypot(goalPos.x - o.x, goalPos.z - o.z) < o.r + 4.5 && goalPos.y < o.h + 1.5) goalPos.y = o.h + 1.5;
    // during the pull-out the aim eases from the car to a point further down the mountain
    const aim = new Vector3(centre.x, centre.y - e * 6, centre.z + e * 30);
    const fov = MathUtils.lerp(38, 48, e);
    this.roll = Math.sin(t * 0.6) * 0.012;
    this.shake = 0;
    this.apply(dt, goalPos, aim, fov, this.snap ? 100 : 5, 6, null);
    this.camera.position.x += Math.sin(this.t * 1.3) * 0.04;
    this.camera.position.y += Math.sin(this.t * 1.9) * 0.05;
  }

  /** Forward vector of the last chase heading (used to seed the drone). */
  get lastHeading(): Vector3 { return this.heading; }
  setHeading(x: number, z: number): void { this.heading.set(x, 0, z).normalize(); }
}

