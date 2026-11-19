import {
  Group, Object3D, Mesh, Vector3, Quaternion, PointLight, SpotLight, ConeGeometry, CircleGeometry, MeshBasicNodeMaterial, AdditiveBlending, DoubleSide, Box3, MeshStandardNodeMaterial,
} from 'three/webgpu';
import { Fn, vec3, uv, smoothstep, pow, normalView, abs, length, vec2 } from 'three/tsl';
import { instantiate } from '../render/assets';
import { disposeTree } from './dispose';
import { decodeHeli, decodePolice, HeliMode, PoliceMode, POLICE_COUNT } from '../sim/types';
import type { Game, HeliState, PoliceUnit } from '../sim/types';
import type { Particles } from '../render/particles';

const WHEELS = ['wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr'] as const;

/** One patrol car: posed from the police buffer, with alternating beacons and a coloured light spill. */
class PatrolView {
  readonly root = new Group();
  private wheels: Object3D[] = [];
  private restY: number[] = [];
  private beaconMats: { m: MeshStandardNodeMaterial; side: number }[] = [];
  private light = new PointLight(0x2a5cff, 0, 24, 2);
  private q = new Quaternion();
  private roll = new Quaternion();
  prev = new Vector3();
  vel = new Vector3();
  active = false;

  constructor(model: Group, private index: number) {
    const car = model.getObjectByName('car') ?? model;
    this.root.add(car);
    for (const n of WHEELS) { const w = car.getObjectByName(n); if (w) { w.rotation.order = 'YXZ'; this.wheels.push(w); this.restY.push(w.position.y); } }
    for (const [n, side] of [['beacon_l', 0], ['beacon_r', 1]] as const) {
      car.getObjectByName(n)?.traverse((o) => { const m = (o as Mesh).material as MeshStandardNodeMaterial | undefined; if (m && !this.beaconMats.some((b) => b.m === m)) this.beaconMats.push({ m, side }); });
    }
    this.light.position.set(0, 2.4, 0);
    this.root.add(this.light);
    this.root.visible = false;
  }

  pose(u: PoliceUnit, t: number): void {
    this.active = u.mode !== PoliceMode.Absent;
    this.root.visible = this.active;
    if (!this.active) { this.light.intensity = 0; return; }
    this.vel.set(u.pos[0], u.pos[1], u.pos[2]).sub(this.prev);
    this.prev.set(u.pos[0], u.pos[1], u.pos[2]);
    this.root.position.set(u.pos[0], u.pos[1], u.pos[2]);
    this.q.set(u.quat[0], u.quat[1], u.quat[2], u.quat[3]);
    this.root.quaternion.copy(this.q).multiply(this.roll.setFromAxisAngle(new Vector3(0, 0, 1), u.roll));
    this.wheels.forEach((w, i) => { w.position.y = this.restY[i]; w.rotation.set(u.spin, i < 2 ? u.steer : 0, 0); });
    // alternating pulses: left and right beacons in antiphase, each with its own fast flicker
    const ph = (t * 5 + this.index * 0.37) % 1;
    const left = ph < 0.5 ? 1 : 0.05, right = ph < 0.5 ? 0.05 : 1;
    for (const b of this.beaconMats) b.m.emissiveIntensity = (b.side === 0 ? left : right) * (u.lights ? 6 : 0.2);
    const blue = ph < 0.5;
    this.light.color.setHex(blue ? 0x2a5cff : 0xff2a2a);
    this.light.intensity = u.lights ? 320 : 0;
  }

  dispose(): void { disposeTree(this.root); this.light.dispose(); }
}

/** The helicopter: spinning rotors, nav lights, strobe, a real spot light plus additive beam cone and ground pool. */
class HeliView {
  readonly root = new Group();
  readonly spot = new SpotLight(0xfff1d0, 0, 190, 0.11, 0.55, 2);
  readonly beam: Mesh;
  readonly pool: Mesh;
  private rotor: Object3D | null = null;
  private tail: Object3D | null = null;
  private spotNode: Object3D | null = null;
  private navMats: { m: MeshStandardNodeMaterial; kind: string }[] = [];
  private disc: Mesh | null = null;
  private mats: { dispose(): void }[] = [];
  private tmp = new Vector3();
  private dirV = new Vector3();
  private qa = new Quaternion();
  prev = new Vector3();
  vel = new Vector3();

  constructor(model: Group, scene: Group) {
    this.root.add(model.getObjectByName('heli') ?? model);
    this.rotor = this.root.getObjectByName('rotor_main') ?? null;
    this.tail = this.root.getObjectByName('rotor_tail') ?? null;
    this.spotNode = this.root.getObjectByName('spotlight') ?? null;
    this.root.traverse((o) => {
      const m = (o as Mesh).material as MeshStandardNodeMaterial | undefined;
      if (m && ['nav_red', 'nav_green', 'strobe', 'spot_lens'].includes(m.name) && !this.navMats.some((n) => n.m === m)) this.navMats.push({ m, kind: m.name });
    });
    if (this.rotor) {
      const b = new Box3().setFromObject(this.rotor); const r = Math.max(b.max.x - b.min.x, b.max.z - b.min.z) / 2;
      const dm = new MeshBasicNodeMaterial({ color: 0x20262c, transparent: true, opacity: 0.16, side: DoubleSide, depthWrite: false });
      const dg = new CircleGeometry(Math.max(2, r), 32); dg.rotateX(-Math.PI / 2);
      this.disc = new Mesh(dg, dm); this.rotor.add(this.disc); this.mats.push(dm, dg);
    }
    // beam: open cone, apex at the lamp, additive, bright at the lamp and fading towards the ground, soft at the rim
    const bm = new MeshBasicNodeMaterial({ transparent: true, blending: AdditiveBlending, depthWrite: false, side: DoubleSide, fog: false });
    bm.colorNode = vec3(1.0, 0.93, 0.78);
    bm.opacityNode = Fn(() => {
      const along = uv().y; // 1 at the apex, 0 at the base
      const rim = smoothstep(0.0, 0.55, abs(normalView.z));
      return pow(along, 0.7).mul(0.17).mul(rim).add(0.0);
    })();
    const bg = new ConeGeometry(1, 1, 28, 1, true);
    this.beam = new Mesh(bg, bm); this.beam.frustumCulled = false; this.beam.renderOrder = 6;
    // ground pool: soft-edged additive disc
    const pm = new MeshBasicNodeMaterial({ transparent: true, blending: AdditiveBlending, depthWrite: false, fog: false });
    pm.colorNode = vec3(1.0, 0.92, 0.72);
    pm.opacityNode = Fn(() => { const d = length(uv().sub(vec2(0.5, 0.5))).mul(2); return smoothstep(1.0, 0.25, d).mul(0.55); })();
    const pg = new CircleGeometry(1, 40); pg.rotateX(-Math.PI / 2);
    this.pool = new Mesh(pg, pm); this.pool.renderOrder = 5; this.pool.frustumCulled = false;
    this.mats.push(bm, bg, pm, pg);
    scene.add(this.root, this.spot, this.spot.target, this.beam, this.pool);
    this.root.visible = this.beam.visible = this.pool.visible = false;
    this.spot.visible = false;
  }

  pose(h: HeliState, t: number): void {
    const on = h.mode !== HeliMode.Absent;
    this.root.visible = on;
    const lit = on && h.light && h.mode !== HeliMode.Departing;
    this.beam.visible = this.pool.visible = this.spot.visible = lit;
    if (!on) return;
    this.vel.set(h.pos[0], h.pos[1], h.pos[2]).sub(this.prev);
    this.prev.set(h.pos[0], h.pos[1], h.pos[2]);
    this.root.position.set(h.pos[0], h.pos[1], h.pos[2]);
    this.root.quaternion.set(h.quat[0], h.quat[1], h.quat[2], h.quat[3]);
    if (this.rotor) this.rotor.rotation.y = h.rotor;
    if (this.tail) this.tail.rotation.x = h.rotor * 4.6;
    if (this.disc) (this.disc.material as MeshBasicNodeMaterial).opacity = Math.min(0.2, 0.04 + h.speed * 0.004 + 0.1);
    for (const n of this.navMats) {
      const f = n.kind === 'strobe' ? ((t * 1.6) % 1 < 0.08 ? 8 : 0.05) : n.kind === 'spot_lens' ? (lit ? 7 : 0.1) : ((t * 0.9) % 1 < 0.5 ? 3 : 0.4);
      n.m.emissiveIntensity = f;
    }
    if (!lit) return;
    const origin = this.spotNode ? this.spotNode.getWorldPosition(this.tmp) : this.tmp.set(h.pos[0], h.pos[1] - 1, h.pos[2]);
    const aim = new Vector3(h.aim[0], h.aim[1], h.aim[2]);
    this.spot.position.copy(origin);
    this.spot.target.position.copy(aim);
    this.spot.target.updateMatrixWorld();
    this.spot.intensity = 9000 * (0.35 + 0.65 * Math.max(0.3, h.lock));
    const dir = this.dirV.copy(aim).sub(origin);
    const len = dir.length();
    if (len < 1) return;
    dir.divideScalar(len);
    const r = Math.tan(0.11) * len;
    this.beam.scale.set(r, len, r);
    this.beam.position.copy(origin).addScaledVector(dir, len / 2);
    // cone local -Y points from apex to base; rotate it to the beam direction
    this.beam.quaternion.copy(this.qa.setFromUnitVectors(new Vector3(0, -1, 0), dir));
    this.pool.position.set(aim.x, aim.y + 0.12, aim.z);
    const pr = Math.max(3, r * 1.15);
    this.pool.scale.set(pr, 1, pr);
  }

  dispose(): void {
    disposeTree(this.root);
    this.beam.removeFromParent(); this.pool.removeFromParent(); this.spot.removeFromParent(); this.spot.target.removeFromParent();
    this.spot.dispose();
    for (const d of this.mats) d.dispose();
  }
}

export interface PursuitInfo {
  units: { pos: Vector3; vel: Vector3; on: boolean; mode: PoliceMode }[];
  heli: { pos: Vector3; vel: Vector3; on: boolean; mode: HeliMode; lock: number; low: boolean };
  /** Number of patrol cars currently pursuing, and the nearest one's distance to the player. */
  pursuing: number;
  nearest: number;
}

/** Owns the three patrol cars and the helicopter for one run; reads the simulation buffers and poses them. */
export class PursuitView {
  readonly group = new Group();
  private patrols: PatrolView[] = [];
  private heli!: HeliView;
  private t = 0;
  private info: PursuitInfo = {
    units: Array.from({ length: POLICE_COUNT }, () => ({ pos: new Vector3(), vel: new Vector3(), on: false, mode: PoliceMode.Absent })),
    heli: { pos: new Vector3(), vel: new Vector3(), on: false, mode: HeliMode.Absent, lock: 0, low: false },
    pursuing: 0, nearest: 1e9,
  };

  static async create(): Promise<PursuitView> {
    const v = new PursuitView();
    for (let i = 0; i < POLICE_COUNT; i++) {
      const p = new PatrolView(await instantiate('cars/patrol.glb'), i);
      v.patrols.push(p); v.group.add(p.root);
    }
    v.heli = new HeliView(await instantiate('props/helicopter.glb'), v.group);
    return v;
  }

  update(dt: number, game: Game, fx: Particles | null): PursuitInfo {
    this.t += dt;
    const units = decodePolice(game.police_state());
    const info = this.info;
    info.pursuing = 0; info.nearest = 1e9;
    units.forEach((u, i) => {
      const p = this.patrols[i];
      p.pose(u, this.t);
      const iu = info.units[i];
      iu.on = p.active; iu.mode = u.mode; iu.pos.copy(p.root.position); iu.vel.copy(p.vel).divideScalar(Math.max(dt, 1e-3));
      if (p.active && u.mode === PoliceMode.Pursuing) { info.pursuing++; info.nearest = Math.min(info.nearest, u.distance); }
      if (p.active && fx && u.speed > 8 && Math.random() < dt * 9) fx.emit('dust', p.root.position.clone().add(new Vector3(0, 0.2, 0)), 1, new Vector3(), 0.8, 0.5);
    });
    const h = decodeHeli(game.heli_state());
    this.heli.pose(h, this.t);
    const ih = info.heli;
    ih.on = h.mode !== HeliMode.Absent; ih.mode = h.mode; ih.lock = h.lock; ih.pos.set(h.pos[0], h.pos[1], h.pos[2]); ih.vel.copy(this.heli.vel).divideScalar(Math.max(dt, 1e-3));
    ih.low = ih.on && h.pos[1] - h.aim[1] < 60;
    if (fx && ih.on && h.light && Math.random() < dt * 12) fx.emit('dust', new Vector3(h.aim[0], h.aim[1] + 0.2, h.aim[2]), 1, new Vector3(0, 0, 0), 3, 0.4);
    return info;
  }

  dispose(): void {
    for (const p of this.patrols) p.dispose();
    this.heli.dispose();
    this.group.removeFromParent();
  }
}
