import {
  Group, Object3D, Mesh, Vector3, Quaternion, Box3, MeshStandardNodeMaterial, MeshBasicNodeMaterial, BoxGeometry, CylinderGeometry, Color,
} from 'three/webgpu';
import { instantiate } from '../render/assets';
import type { CarSpec, Game, RenderState } from '../sim/types';
import { PART_NAMES } from '../sim/types';


interface Eye { node: Object3D; side: 1 | -1; pupil: Mesh; cross: Group; w: number; h: number; front: number; rest: Vector3 }
interface LoosePart { obj: Object3D; vel: Vector3; spin: Vector3; rest: boolean }

/** One car's visual: GLB nodes, sprung body, wheels, eyes, damage. Pure presentation; poses come from state(). */
export class CarView {
  readonly root = new Group();
  readonly sprung = new Group();
  readonly anchor: Object3D;
  readonly wheels: Object3D[] = [];
  private eyes: Eye[] = [];
  private paint: MeshStandardNodeMaterial[] = [];
  private headMat: MeshStandardNodeMaterial[] = [];
  private bonnet: Object3D | null;
  private mirrors: Object3D[] = [];
  private restY: number[] = [];
  private loose: LoosePart[] = [];
  private partRest = new Map<string, { parent: Object3D; pos: Vector3; quat: Quaternion }>();
  private springY = 0; private springV = 0;
  private springR = 0; private springRV = 0;
  private disposables: { dispose(): void }[] = [];
  private t = Math.random() * 10;

  static async create(spec: CarSpec): Promise<CarView> {
    const v = new CarView(spec, await instantiate(`cars/${spec.key}.glb`));
    return v;
  }

  private constructor(readonly spec: CarSpec, model: Group) {
    const car = model.getObjectByName('car') ?? model;
    this.root.add(car);
    car.updateMatrixWorld(true);
    this.anchor = car.getObjectByName('roof_anchor') ?? (() => {
      const a = new Object3D();
      a.position.set(0, spec.roof_y, 0);
      car.add(a);
      return a;
    })();
    // gather wheels, then re-parent everything sprung under one pivot so the body can sway on its springs
    for (const n of ['wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr']) {
      const w = car.getObjectByName(n);
      if (!w) throw new Error(`car model ${spec.key} lacks node ${n}`);
      this.wheels.push(w);
      this.restY.push(w.position.y);
      w.rotation.order = 'YXZ';
    }
    const keep = new Set(this.wheels);
    for (const c of [...car.children]) if (!keep.has(c)) this.sprung.add(c);
    car.add(this.sprung);
    this.bonnet = car.getObjectByName('bonnet') ?? null;
    for (const n of ['mirror_l', 'mirror_r']) { const m = car.getObjectByName(n); if (m) this.mirrors.push(m); }
    for (const n of PART_NAMES) {
      const o = car.getObjectByName(n);
      if (o?.parent) this.partRest.set(n, { parent: o.parent, pos: o.position.clone(), quat: o.quaternion.clone() });
    }
    const colour = new Color(spec.paint);
    car.traverse((o) => {
      const m = (o as Mesh).material as MeshStandardNodeMaterial | undefined;
      if (!m) return;
      if (m.name === 'paint') { m.color.copy(colour); this.paint.push(m); }
      if (m.name === 'headlight' && !this.headMat.includes(m)) this.headMat.push(m);
    });
    this.buildEyes(car);
  }

  private buildEyes(car: Object3D): void {
    const pupilMat = new MeshBasicNodeMaterial({ color: 0x0b0b0e });
    const xMat = new MeshBasicNodeMaterial({ color: 0x0b0b0e });
    this.disposables.push(pupilMat, xMat);
    for (const [name, side] of [['headlight_l', 1], ['headlight_r', -1]] as const) {
      const node = car.getObjectByName(name);
      if (!node) continue;
      const inv = car.matrixWorld.clone().invert();
      const box = new Box3().setFromObject(node).applyMatrix4(inv);
      const size = box.getSize(new Vector3());
      const front = Math.max(0.02, box.max.z - node.position.z) + 0.012;
      const r = Math.max(0.03, Math.min(size.x, size.y) * 0.32);
      const geo = new CylinderGeometry(r, r, 0.02, 14);
      geo.rotateX(Math.PI / 2);
      this.disposables.push(geo);
      const pupil = new Mesh(geo, pupilMat);
      pupil.position.set(0, 0, front);
      node.add(pupil);
      const cross = new Group();
      const bar = new BoxGeometry(Math.max(0.05, size.x * 0.9), Math.max(0.012, size.y * 0.12), 0.012);
      this.disposables.push(bar);
      const a = new Mesh(bar, xMat), b = new Mesh(bar, xMat);
      a.rotation.z = Math.PI / 4; b.rotation.z = -Math.PI / 4;
      cross.add(a, b);
      cross.position.set(0, 0, front + 0.012);
      cross.visible = false;
      node.add(cross);
      this.eyes.push({ node, side, pupil, cross, w: size.x, h: size.y, front, rest: node.position.clone() });
    }
  }

  /** Eyes: droop and cross with stein count. `n` is the loaded count (0..15). */
  setEyes(n: number, time: number, wrecked: boolean): void {
    const s = Math.min(1, n / 15);
    for (const e of this.eyes) {
      const droop = s * 0.55;
      e.node.scale.y = 1 - droop * 0.9;
      e.node.position.y = e.rest.y - droop * e.h * 0.35;
      e.node.rotation.z = -e.side * droop * 0.5;
      const cross = Math.max(0, (n - 4) / 11);
      const drift = Math.sin(time * (1.3 + s) + e.side * 1.7) * 0.18 * s;
      e.pupil.position.x = (-e.side * (0.28 * cross) + drift * 0.4) * e.w;
      e.pupil.position.y = Math.sin(time * 0.9 + e.side) * 0.08 * s * e.h;
      e.pupil.visible = !wrecked;
      e.cross.visible = wrecked;
    }
    for (const m of this.headMat) m.emissiveIntensity = wrecked ? 0.1 : 1.2 * (1 - 0.25 * s) * (0.92 + 0.08 * Math.sin(time * 9 * (0.3 + s)));
  }

  /** Small vertical and roll kick from a hiccup. */
  hiccup(strength: number): void {
    this.springV += 1.4 * (0.5 + strength);
    this.springRV += (Math.random() < 0.5 ? -1 : 1) * 0.6 * strength;
  }

  /** Idle sway on the springs at the lodge, scaled by loaded steins; plus hiccup spring dynamics. */
  tickSprings(dt: number, n: number, wobble: number): void {
    this.t += dt;
    const s = n / 15;
    const k = 140, c = 9;
    this.springV += (-k * this.springY - c * this.springV) * dt;
    this.springY += this.springV * dt;
    this.springRV += (-k * 0.6 * this.springR - c * 0.7 * this.springRV) * dt;
    this.springR += this.springRV * dt;
    const swayAmp = 0.006 + 0.03 * s + 0.05 * wobble;
    this.sprung.rotation.z = Math.sin(this.t * (1.5 + s)) * swayAmp + this.springR;
    this.sprung.rotation.x = Math.sin(this.t * (1.1 + s * 0.7) + 1) * swayAmp * 0.6;
    this.sprung.position.y = this.springY * 0.04;
  }

  /** Apply render state: the caller positions `root`; this animates the wheels and damage. */
  applyState(st: RenderState): void {
    for (let i = 0; i < 4; i++) {
      const w = st.wheels[i];
      const node = this.wheels[i];
      node.position.y = this.restY[i] + w.compression;
      node.rotation.set(w.spin, w.steer, 0);
    }
    if (this.bonnet) this.bonnet.rotation.x = -st.damage * 0.45;
    if (this.mirrors[1]) this.mirrors[1].rotation.y = st.damage * 0.6;
  }

  /** Idle wheel pose at the lodge. */
  restWheels(): void {
    for (let i = 0; i < 4; i++) { this.wheels[i].position.y = this.restY[i]; this.wheels[i].rotation.set(0, 0, 0); }
  }

  /** Throw a detached part clear; it tumbles and lies on the ground. */
  detach(partId: number, scene: Object3D, carVel: Vector3): void {
    const name = PART_NAMES[partId];
    const o = name ? this.root.getObjectByName(name) : null;
    if (!o || this.loose.some((l) => l.obj === o)) return;
    scene.attach(o);
    this.loose.push({ obj: o, vel: new Vector3(carVel.x * 0.3 + (Math.random() - 0.5) * 4, 3 + Math.random() * 2, carVel.z * 0.3 + (Math.random() - 0.3) * 4), spin: new Vector3(Math.random() * 6, Math.random() * 6, Math.random() * 6), rest: false });
  }

  tickLoose(dt: number, game: Game): void {
    for (const l of this.loose) {
      if (l.rest) continue;
      l.vel.y -= 9.8 * dt;
      l.obj.position.addScaledVector(l.vel, dt);
      l.obj.rotateX(l.spin.x * dt); l.obj.rotateY(l.spin.y * dt); l.obj.rotateZ(l.spin.z * dt);
      const g = game.height_at(l.obj.position.x, l.obj.position.z) + 0.12;
      if (l.obj.position.y < g) {
        l.obj.position.y = g;
        l.vel.y *= -0.3; l.vel.x *= 0.6; l.vel.z *= 0.6; l.spin.multiplyScalar(0.55);
        if (l.vel.length() < 0.8) l.rest = true;
      }
    }
  }

  /** Reattach parts and clear transient state for a fresh run. */
  reset(): void {
    for (const l of this.loose) {
      const r = this.partRest.get(l.obj.name);
      if (r) { r.parent.add(l.obj); l.obj.position.copy(r.pos); l.obj.quaternion.copy(r.quat); l.obj.scale.set(1, 1, 1); }
    }
    this.loose = [];
    if (this.bonnet) this.bonnet.rotation.x = 0;
    if (this.mirrors[1]) this.mirrors[1].rotation.y = 0;
    this.springY = this.springV = this.springR = this.springRV = 0;
  }

  dispose(): void {
    this.reset();
    for (const d of this.disposables) d.dispose();
    this.root.removeFromParent();
  }
}
