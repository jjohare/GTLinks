import {
  Group, Vector3, Quaternion, Raycaster, Vector2, Box3, Mesh, CircleGeometry, MeshBasicNodeMaterial, PerspectiveCamera, Object3D, MathUtils, AdditiveBlending,
} from 'three/webgpu';
import { instantiate, normaliseHeight, CARS } from '../render/assets';
import { CarView } from './carView';
import { SteinLoad, MAX_STEINS } from '../core/steins';
import { disposeTree } from './dispose';
import { bakeStatic } from './bake';
import type { Particles } from '../render/particles';
import type { Course, Game } from '../sim/types';

const STEIN_H = 0.3;
const PILE_SCALE = 1.6;
const PILE_SPREAD = 1.35;

type Mode = 'table' | 'drag' | 'return' | 'tip' | 'pile' | 'shed';
interface St {
  id: number; obj: Group; mode: Mode; t: number; home: Vector3; from: Vector3; fromQ: Quaternion;
  vel: Vector3; spin: Vector3; side: number; seed: number; bounced: boolean; life: number; base: number;
}

export interface LodgeHooks {
  onCount(count: number, canGo: boolean): void;
  onSelect(index: number): void;
  onClink(strength: number): void;
  onTip(): void;
  onFull(): void;
}

/** Pile slots in roof-anchor space (anchor at roof centre, +Z forward). Fills in layers of 6, 5 and 4. */
export function pileSlot(k: number): Vector3 {
  const L0 = [[-0.3, -0.5], [0.3, -0.5], [-0.3, 0], [0.3, 0], [-0.3, 0.5], [0.3, 0.5]];
  const L1 = [[-0.15, -0.25], [0.15, -0.25], [-0.15, 0.25], [0.15, 0.25], [0, 0.72]];
  const L2 = [[-0.12, -0.05], [0.12, -0.05], [-0.12, 0.4], [0.12, 0.4]];
  const h = STEIN_H * PILE_SCALE;
  const P = PILE_SPREAD;
  if (k < 6) return new Vector3(L0[k][0] * P, 0, L0[k][1] * P);
  if (k < 11) return new Vector3(L1[k - 6][0] * P, h * 0.96, L1[k - 6][1] * P);
  return new Vector3(L2[Math.min(3, k - 11)][0] * P, h * 1.92, L2[Math.min(3, k - 11)][1] * P);
}

/** Lodge terrace, table, steins and the four cars: owns selection and all drag-and-drop. */
export class Lodge {
  readonly group = new Group();
  readonly load = new SteinLoad();
  readonly cars: CarView[] = [];
  readonly slotPos: Vector3[] = [];
  readonly slotQuat: Quaternion[] = [];
  selected = 0;
  enabled = true;
  readonly camHome = new Vector3();
  readonly tablePos = new Vector3();

  private steins: St[] = [];
  private ring: Mesh;
  private ringMat = new MeshBasicNodeMaterial({ color: 0xffd36a, transparent: true, opacity: 0.55, blending: AdditiveBlending, depthWrite: false });
  private raycaster = new Raycaster();
  private ndc = new Vector2();
  private dragging: { st: St; plane: { normal: Vector3; point: Vector3 }; target: Vector3; last: Vector3; offset: Vector3 } | null = null;
  private down: { x: number; y: number; id: number; t: number } | null = null;
  private hover: St | null = null;
  private time = 0;
  private lodgeModel!: Group;
  private tableModel!: Group;
  private bboxTmp = new Box3();
  private pointerFns: Array<[string, (e: PointerEvent) => void]> = [];
  private tmpV = new Vector3();
  private tmpV2 = new Vector3();
  private tmpQ = new Quaternion();

  static async create(course: Course, game: Game, camera: PerspectiveCamera, canvas: HTMLCanvasElement, fx: Particles, hooks: LodgeHooks): Promise<Lodge> {
    const l = new Lodge(course, game, camera, canvas, fx, hooks);
    await l.build();
    return l;
  }

  private constructor(private course: Course, private game: Game, private camera: PerspectiveCamera, private canvas: HTMLCanvasElement, private fx: Particles, private hooks: LodgeHooks) {
    const g = new CircleGeometry(3.6, 40);
    g.rotateX(-Math.PI / 2);
    this.ring = new Mesh(g, this.ringMat);
    this.ring.renderOrder = 5;
    this.group.add(this.ring);
  }

  private async build(): Promise<void> {
    const { course, game } = this;
    const L = new Vector3(...course.lodge.pos);
    this.lodgeModel = bakeStatic(await instantiate('props/lodge.glb'));
    this.lodgeModel.position.copy(L);
    this.lodgeModel.rotation.y = course.lodge.yaw;
    this.group.add(this.lodgeModel);

    this.tableModel = bakeStatic(await instantiate('props/table.glb'));
    this.tablePos.set(L.x, L.y, L.z + 6.4);
    this.tableModel.position.copy(this.tablePos);
    this.group.add(this.tableModel);
    this.tableModel.updateMatrixWorld(true);
    const tb = new Box3().setFromObject(this.tableModel);
    const topY = tb.max.y;
    const tw = tb.max.x - tb.min.x, td = tb.max.z - tb.min.z;

    this.camHome.set(L.x, L.y + 3.1, L.z + 2.2);

    // steins on the table in three rows of five
    for (let i = 0; i < MAX_STEINS; i++) {
      const obj = await instantiate('props/stein.glb');
      normaliseHeight(obj, STEIN_H);
      const col = i % 5, row = Math.floor(i / 5);
      const home = new Vector3(L.x + (col - 2) * Math.min(0.6, tw / 6), topY, this.tablePos.z + (row - 1) * Math.min(0.42, td / 4));
      obj.position.copy(home);
      obj.rotation.y = (i * 1.7) % 6.28;
      this.group.add(obj);
      this.steins.push({ id: i, obj, mode: 'table', t: 0, home, from: new Vector3(), fromQ: new Quaternion(), vel: new Vector3(), spin: new Vector3(), side: 1, seed: i * 12.9898, bounced: false, life: 0, base: obj.scale.x });
    }

    // four cars on the apron, turned to face the terrace
    const S = new Vector3(...course.start.pos);
    for (let i = 0; i < CARS.length; i++) {
      const cv = await CarView.create(CARS[i]);
      // the row sits just uphill of the spawn point so the car that drives off never meets its neighbours
      const x = S.x - (i - 1.5) * 5.4, z = S.z - 6 + (i % 2 === 0 ? 0 : 1.2);
      const y = game.height_at(x, z);
      const yaw = Math.atan2(this.camHome.x - x, this.camHome.z - z) + (i % 2 === 0 ? 0.55 : -0.55);
      cv.root.position.set(x, y, z);
      cv.root.rotation.y = yaw;
      cv.restWheels();
      cv.root.traverse((o) => { (o as Mesh).castShadow = i === this.selected; });
      this.group.add(cv.root);
      this.cars.push(cv);
      this.slotPos.push(cv.root.position.clone());
      this.slotQuat.push(cv.root.quaternion.clone());
    }
    this.moveRing();
    this.bind();
    this.hooks.onSelect(this.selected);
    this.hooks.onCount(this.load.count, this.load.canGo);
  }

  setGame(g: Game): void { this.game = g; }

  /** Put `n` steins on the selected car at once (automated starts). */
  fillInstant(n: number): void {
    this.load.clear();
    for (const s of this.steins) { this.group.attach(s.obj); s.mode = 'table'; s.obj.visible = true; }
    for (let i = 0; i < n; i++) {
      const s = this.steins[i];
      this.load.add(s.id);
      this.car.anchor.attach(s.obj);
      s.mode = 'pile';
      s.obj.position.copy(pileSlot(i));
      s.obj.scale.setScalar(s.base * PILE_SCALE);
    }
    this.hooks.onCount(this.load.count, this.load.canGo);
  }

  /** The selected car's view. */
  get car(): CarView { return this.cars[this.selected]; }

  private moveRing(): void {
    const p = this.slotPos[this.selected];
    this.ring.position.set(p.x, p.y + 0.06, p.z);
  }

  select(i: number): void {
    const n = this.cars.length;
    i = ((i % n) + n) % n;
    if (i === this.selected) return;
    this.selected = i;
    this.cars.forEach((c, k) => c.root.traverse((o) => { (o as Mesh).castShadow = k === i; }));
    this.moveRing();
    // any pile moves to the newly chosen car
    for (const s of this.steins) if (s.mode === 'pile') { this.car.anchor.attach(s.obj); }
    this.hooks.onSelect(i);
    this.hooks.onClink(0.3);
  }
  next(): void { this.select(this.selected + 1); }
  prev(): void { this.select(this.selected - 1); }

  // ---------------------------------------------------------------- pointer handling

  private bind(): void {
    const add = (type: string, fn: (e: PointerEvent) => void) => { this.canvas.addEventListener(type, fn as EventListener); this.pointerFns.push([type, fn]); };
    add('pointerdown', (e) => this.onDown(e));
    add('pointermove', (e) => this.onMove(e));
    add('pointerup', (e) => this.onUp(e));
    add('pointercancel', (e) => this.onCancel(e));
  }

  private setRay(e: PointerEvent): void {
    const r = this.canvas.getBoundingClientRect();
    this.ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(this.ndc, this.camera);
  }

  private pick(e: PointerEvent): St | null {
    this.setRay(e);
    const targets = this.steins.filter((s) => s.mode === 'table' || s.mode === 'pile' || s.mode === 'return').map((s) => s.obj);
    const hits = this.raycaster.intersectObjects(targets, true);
    if (!hits.length) return null;
    let o: Object3D | null = hits[0].object;
    while (o && !targets.includes(o as Group)) o = o.parent;
    return this.steins.find((s) => s.obj === o) ?? null;
  }

  private pickCar(e: PointerEvent): number {
    this.setRay(e);
    let best = -1, bd = Infinity;
    for (let i = 0; i < this.cars.length; i++) {
      this.bboxTmp.setFromObject(this.cars[i].root);
      const hit = this.raycaster.ray.intersectBox(this.bboxTmp, this.tmpV);
      if (hit) { const d = hit.distanceTo(this.raycaster.ray.origin); if (d < bd) { bd = d; best = i; } }
    }
    return best;
  }

  private onDown(e: PointerEvent): void {
    if (!this.enabled) return;
    const st = this.pick(e);
    if (st) {
      this.canvas.setPointerCapture(e.pointerId);
      if (st.mode === 'pile') {
        this.load.remove(st.id);
        this.group.attach(st.obj);
        this.hooks.onCount(this.load.count, this.load.canGo);
      }
      st.mode = 'drag';
      const wp = st.obj.getWorldPosition(new Vector3());
      const normal = this.camera.getWorldDirection(new Vector3()).negate();
      this.setRay(e);
      const plane = { normal, point: wp.clone() };
      const hit = this.rayPlane(plane);
      const offset = hit ? wp.clone().sub(hit) : new Vector3();
      this.dragging = { st, plane, target: wp.clone(), last: wp.clone(), offset };
      this.hooks.onClink(0.5);
      e.preventDefault();
      return;
    }
    this.down = { x: e.clientX, y: e.clientY, id: e.pointerId, t: performance.now() };
  }

  private rayPlane(plane: { normal: Vector3; point: Vector3 }): Vector3 | null {
    const o = this.raycaster.ray.origin, d = this.raycaster.ray.direction;
    const denom = plane.normal.dot(d);
    if (Math.abs(denom) < 1e-5) return null;
    const t = plane.point.clone().sub(o).dot(plane.normal) / denom;
    return t > 0 ? o.clone().addScaledVector(d, t) : null;
  }

  private onMove(e: PointerEvent): void {
    if (this.dragging) {
      this.setRay(e);
      const hit = this.rayPlane(this.dragging.plane);
      if (hit) this.dragging.target.copy(hit.add(this.dragging.offset));
      return;
    }
    if (!this.enabled || e.pointerType === 'touch') return;
    const s = this.pick(e);
    this.hover = s;
    this.canvas.style.cursor = s ? 'grab' : this.pickCar(e) >= 0 ? 'pointer' : 'default';
  }

  /** True when the pointer ray passes through the selected car's (generous) bounding box. */
  private overCar(e: PointerEvent): boolean {
    this.setRay(e);
    this.bboxTmp.setFromObject(this.car.root).expandByVector(this.tmpV2.set(0.6, 1.4, 0.6));
    return this.raycaster.ray.intersectsBox(this.bboxTmp);
  }

  private onUp(e: PointerEvent): void {
    if (this.dragging) {
      const { st } = this.dragging;
      this.dragging = null;
      if (this.canvas.hasPointerCapture(e.pointerId)) this.canvas.releasePointerCapture(e.pointerId);
      if (this.overCar(e) && !this.load.full) this.tip(st);
      else {
        if (this.load.full && this.overCar(e)) this.hooks.onFull();
        this.giveBack(st);
      }
      return;
    }
    const d = this.down;
    this.down = null;
    if (!d || !this.enabled) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.6) { if (dx < 0) this.next(); else this.prev(); return; }
    if (Math.hypot(dx, dy) < 12) { const c = this.pickCar(e); if (c >= 0) this.select(c); }
  }

  private onCancel(e: PointerEvent): void {
    this.down = null;
    if (this.dragging) { const st = this.dragging.st; this.dragging = null; this.giveBack(st); }
    if (this.canvas.hasPointerCapture(e.pointerId)) this.canvas.releasePointerCapture(e.pointerId);
  }

  // ---------------------------------------------------------------- stein state changes

  private giveBack(st: St): void {
    st.mode = 'return'; st.t = 0;
    st.from.copy(st.obj.position);
    st.fromQ.copy(st.obj.quaternion);
    this.hooks.onClink(0.4);
  }

  private tip(st: St): void {
    if (!this.load.add(st.id)) { this.giveBack(st); return; }
    st.mode = 'tip'; st.t = 0;
    st.from.copy(st.obj.position);
    st.fromQ.copy(st.obj.quaternion);
    st.side = Math.random() < 0.5 ? -1 : 1;
    this.hooks.onCount(this.load.count, this.load.canGo);
  }

  /** Keyboard / button route: add the next stein from the table. */
  addOne(): boolean {
    if (this.load.full) { this.hooks.onFull(); return false; }
    const next = this.steins.find((s) => s.mode === 'table');
    if (!next) return false;
    this.tip(next);
    return true;
  }
  /** Keyboard / button route: take the most recent stein back to the table. */
  removeOne(): boolean {
    const id = this.load.removeLast();
    if (id === null) return false;
    const st = this.steins[id];
    this.group.attach(st.obj);
    this.giveBack(st);
    this.hooks.onCount(this.load.count, this.load.canGo);
    return true;
  }

  /** Visible pile size (what is physically still on the roof). */
  get pileCount(): number { return this.steins.filter((s) => s.mode === 'pile').length; }

  /** Throw `n` steins off the roof (cosmetic only). Returns world positions for foam. */
  shed(n: number, carVel: Vector3, power = 1): void {
    const pile = this.steins.filter((s) => s.mode === 'pile').sort((a, b) => this.load.ids.indexOf(b.id) - this.load.ids.indexOf(a.id));
    for (const s of pile.slice(0, n)) {
      this.group.attach(s.obj);
      s.mode = 'shed'; s.t = 0; s.life = 0; s.bounced = false;
      s.vel.set(carVel.x * 0.55 + (Math.random() - 0.5) * 7 * power, 4 + Math.random() * 6 * power, carVel.z * 0.55 + (Math.random() - 0.3) * 5 * power);
      s.spin.set((Math.random() - 0.5) * 14, (Math.random() - 0.5) * 8, (Math.random() - 0.5) * 14);
    }
  }

  /** After a descent begins the pile belongs to the sim car; detach visuals from the lodge selection only. */
  get steinObjects(): readonly St[] { return this.steins; }

  // ---------------------------------------------------------------- per-frame

  update(dt: number, wobble: number, driving: boolean): void {
    this.time += dt;
    for (const c of this.cars) c.tickSprings(dt, c === this.car ? this.load.count : 0, c === this.car && driving ? wobble : 0);
    this.ringMat.opacity = driving ? 0 : 0.35 + 0.15 * Math.sin(this.time * 2.4);
    this.ring.rotation.y += dt * 0.2;
    const anchor = this.car.anchor;
    anchor.updateWorldMatrix(true, false);
    const ids = this.load.ids;

    for (const s of this.steins) {
      const o = s.obj;
      switch (s.mode) {
        case 'table': {
          const hov = this.hover === s ? 0.03 : 0;
          o.position.y += (s.home.y + hov - o.position.y) * Math.min(1, dt * 12);
          break;
        }
        case 'drag': {
          const d = this.dragging;
          if (d && d.st === s) {
            const prev = o.position.clone();
            o.position.lerp(d.target, Math.min(1, dt * 20));
            const v = o.position.clone().sub(prev).divideScalar(Math.max(dt, 1e-3));
            // a little swing: tilt with horizontal velocity, lag behind
            const tz = MathUtils.clamp(-v.x * 0.07, -0.7, 0.7), tx = MathUtils.clamp(v.z * 0.07 + v.y * 0.03, -0.5, 0.5);
            o.rotation.z += (tz - o.rotation.z) * Math.min(1, dt * 10);
            o.rotation.x += (tx - o.rotation.x) * Math.min(1, dt * 10);
          }
          break;
        }
        case 'return': {
          s.t += dt / 0.38;
          const u = Math.min(1, s.t), e = u * u * (3 - 2 * u);
          o.position.lerpVectors(s.from, s.home, e);
          o.position.y += Math.sin(u * Math.PI) * 0.25;
          o.quaternion.slerp(this.tmpQ.identity(), e);
          o.scale.setScalar(o.scale.x + (s.base - o.scale.x) * e);
          if (u >= 1) { s.mode = 'table'; o.position.copy(s.home); o.rotation.set(0, (s.id * 1.7) % 6.28, 0); o.scale.setScalar(s.base); this.hooks.onClink(0.35); }
          break;
        }
        case 'tip': {
          s.t += dt / 0.95;
          const u = Math.min(1, s.t);
          const top = anchor.localToWorld(this.tmpV2.set(0, 1.0, 0.1));
          const slot = anchor.localToWorld(pileSlot(Math.max(0, ids.indexOf(s.id))));
          if (u < 0.45) {
            const k = u / 0.45, e = k * k * (3 - 2 * k);
            o.position.lerpVectors(s.from, top, e);
            o.position.y += Math.sin(k * Math.PI) * 0.4;
            o.rotation.z = s.side * 1.85 * e;
            o.rotation.x *= 1 - e;
          } else if (u < 0.6) {
            o.position.copy(top);
            o.rotation.z = s.side * (1.85 + Math.sin((u - 0.45) * 40) * 0.1);
          } else {
            const k = (u - 0.6) / 0.4, e = k * k * (3 - 2 * k);
            o.position.lerpVectors(top, slot, e);
            o.rotation.z = s.side * 1.85 * (1 - e);
          }
          if (!s.bounced && u >= 0.5) {
            s.bounced = true;
            this.tmpV2.copy(top).add(new Vector3(0, -0.15, 0));
            this.fx.emit('foam', this.tmpV2, 16, new Vector3(0, 1.2, 0), 1.6);
            this.fx.emit('lager', this.tmpV2, 10, new Vector3(0, 0.6, 0), 1.4);
            this.hooks.onTip();
            this.car.hiccup(0.35);
          }
          if (u >= 1) {
            anchor.attach(o);
            o.rotation.set(0, (s.id * 2.3) % 6.28, 0);
            s.mode = 'pile'; s.bounced = false;
          }
          break;
        }
        case 'pile': {
          const k = ids.indexOf(s.id);
          if (k < 0) { s.mode = 'return'; this.group.attach(o); s.t = 0; s.from.copy(o.position); s.fromQ.copy(o.quaternion); break; }
          const slot = pileSlot(k);
          const wob = 1 + wobble * 5;
          const tx = slot.x + Math.sin(this.time * 2.1 + s.seed) * 0.012 * wob;
          const tz = slot.z + Math.cos(this.time * 1.7 + s.seed) * 0.012 * wob;
          const f = Math.min(1, dt * 9);
          o.position.x += (tx - o.position.x) * f;
          o.position.y += (slot.y - o.position.y) * f;
          o.position.z += (tz - o.position.z) * f;
          o.scale.setScalar(o.scale.x + (s.base * PILE_SCALE - o.scale.x) * f);
          o.rotation.x = Math.sin(this.time * 2.6 + s.seed) * 0.05 * (1 + wobble * 6) + Math.sin(s.seed) * 0.05;
          o.rotation.z = Math.cos(this.time * 2.2 + s.seed * 1.3) * 0.05 * (1 + wobble * 6) + Math.cos(s.seed) * 0.05;
          break;
        }
        case 'shed': {
          s.life += dt;
          s.vel.y -= 9.8 * dt;
          o.position.addScaledVector(s.vel, dt);
          o.rotateX(s.spin.x * dt); o.rotateY(s.spin.y * dt); o.rotateZ(s.spin.z * dt);
          const g = this.game.height_at(o.position.x, o.position.z) + 0.1;
          if (o.position.y < g) {
            o.position.y = g;
            if (!s.bounced) { s.bounced = true; this.fx.emit('foam', o.position, 10, new Vector3(0, 1.5, 0), 1.8); this.fx.emit('lager', o.position, 6, new Vector3(0, 1, 0), 1.6); }
            s.vel.y *= -0.35; s.vel.x *= 0.65; s.vel.z *= 0.65; s.spin.multiplyScalar(0.6);
          }
          if (s.life > 9) o.visible = false;
          break;
        }
      }
    }
  }

  /** Put every stein back on the table and empty the car (a new run). */
  resetSteins(): void {
    this.load.clear();
    for (const s of this.steins) { this.group.attach(s.obj); s.obj.visible = true; s.mode = 'table'; s.obj.position.copy(s.home); s.obj.rotation.set(0, (s.id * 1.7) % 6.28, 0); s.obj.scale.setScalar(s.base); }
    this.hooks.onCount(0, false);
  }

  dispose(): void {
    for (const [t, f] of this.pointerFns) this.canvas.removeEventListener(t, f as EventListener);
    this.pointerFns = [];
    for (const c of this.cars) c.dispose();
    for (const s of this.steins) disposeTree(s.obj);
    disposeTree(this.lodgeModel, true);
    disposeTree(this.tableModel, true);
    this.ring.geometry.dispose();
    this.ringMat.dispose();
    this.group.removeFromParent();
  }
}

/** Stats shown on the car card, derived from the spec (no retyped numbers). */
export function derivedStats(spec: { track: number; cog_height: number; mass: number; wheelbase: number; length: number }, all: { track: number; cog_height: number; mass: number; wheelbase: number; length: number }[]): { stability: number; agility: number; presence: number } {
  const norm = (v: number, list: number[]) => { const lo = Math.min(...list), hi = Math.max(...list); return hi === lo ? 0.5 : (v - lo) / (hi - lo); };
  const stab = (c: typeof spec) => c.track / c.cog_height;
  const agi = (c: typeof spec) => 1 / (c.mass * c.wheelbase);
  return {
    stability: 0.25 + 0.7 * norm(stab(spec), all.map(stab)),
    agility: 0.25 + 0.7 * norm(agi(spec), all.map(agi)),
    presence: 0.25 + 0.7 * norm(spec.length * spec.mass, all.map((c) => c.length * c.mass)),
  };
}
