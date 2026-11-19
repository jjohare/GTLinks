import {
  Group, Matrix4, Quaternion, Vector3, Color, Mesh, PlaneGeometry, MeshBasicNodeMaterial, CanvasTexture, SRGBColorSpace, BoxGeometry, MeshStandardNodeMaterial,
} from 'three/webgpu';
import { InstancedGroup, extractParts } from './instanced';
import { loadTemplate } from '../render/assets';
import { PropKind } from '../sim/types';
import type { Course, CourseProp, Game, SimEvent } from '../sim/types';

const Y = new Vector3(0, 1, 0);
const KIND_FILE: Record<number, string> = {
  [PropKind.Pine]: 'tree_pine', [PropKind.Broadleaf]: 'tree_broadleaf', [PropKind.Spectator]: 'spectator',
  [PropKind.Flag]: 'flag', [PropKind.TeeMarker]: 'tee_marker', [PropKind.Cart]: 'golf_cart', [PropKind.Sign]: 'sign', [PropKind.Rock]: 'rock',
};
const SHIRTS = [0xd14b3a, 0x2f6fb5, 0xe2b13a, 0x3f9a63, 0xb556a8, 0xf0efe8, 0xe07a2a];

interface Dyn {
  kind: 'dive' | 'tumble';
  t: number;
  pos: Vector3; vel: Vector3; q: Quaternion; spin: Vector3; dir: number; rest: boolean;
}

/** All static and animated scenery for one course, drawn with instancing. */
export class Props {
  readonly group = new Group();
  private groups = new Map<PropKind, InstancedGroup>();
  private slot = new Map<number, { kind: PropKind; i: number }>();
  private base: Matrix4[] = [];
  private dyn = new Map<number, Dyn>();
  private spectators: number[] = [];
  private phase: number[] = [];
  private rampGroup: InstancedGroup | null = null;
  private extra: InstancedGroup[] = [];
  private disposables: { dispose(): void }[] = [];
  private tmp = new Matrix4();
  private scaleV = new Vector3();
  private t = 0;
  private kicker: { group: InstancedGroup; pos: Vector3; yaw: number; t: number } | null = null;

  static async create(course: Course, game: Game): Promise<Props> {
    const p = new Props(course, game);
    await p.build();
    return p;
  }

  private constructor(private course: Course, private game: Game) {}

  /** Swap the height source when the preview game is replaced by the real run. */
  setGame(g: Game): void { this.game = g; }

  private async build(): Promise<void> {
    const { course } = this;
    const byKind = new Map<PropKind, number[]>();
    course.props.forEach((p, i) => {
      const l = byKind.get(p.kind) ?? [];
      l.push(i);
      byKind.set(p.kind, l);
      this.base[i] = compose(p);
    });
    for (const [kind, list] of byKind) {
      const parts = extractParts(await loadTemplate(`props/${KIND_FILE[kind]}.glb`));
      const dynamic = kind === PropKind.Spectator || kind === PropKind.Flag || kind === PropKind.TeeMarker || kind === PropKind.Sign || kind === PropKind.Rock;
      const ig = new InstancedGroup(parts, list.length, { cull: !dynamic, colourPart: kind === PropKind.Spectator ? 'shirt' : undefined, shadows: kind !== PropKind.Rock });
      list.forEach((pi, i) => {
        this.slot.set(pi, { kind, i });
        ig.set(i, this.base[pi]);
        if (kind === PropKind.Spectator) {
          ig.setColour(i, new Color(SHIRTS[(pi * 7 + 3) % SHIRTS.length]));
          this.spectators.push(pi);
          this.phase[pi] = (pi * 1.618) % 6.28;
        }
      });
      ig.commit();
      ig.addTo(this.group);
      this.groups.set(kind, ig);
    }
    // Ramps: the unit wedge scaled to (width, height, length).
    if (course.ramps.length) {
      const parts = extractParts(await loadTemplate('props/ramp.glb'));
      const rg = new InstancedGroup(parts, course.ramps.length, { cull: true });
      course.ramps.forEach((r, i) => {
        const q = new Quaternion().setFromAxisAngle(Y, r.yaw);
        rg.set(i, new Matrix4().compose(new Vector3(...r.pos), q, new Vector3(r.width, r.height, r.length)));
      });
      rg.commit();
      rg.addTo(this.group);
      this.rampGroup = rg;
    }
    await this.buildHoleDecor();
  }

  /** Decorative pin at each green (if the course did not already place one) and a hole number board at each tee. */
  private async buildHoleDecor(): Promise<void> {
    const { course } = this;
    const flags = course.props.filter((p) => p.kind === PropKind.Flag);
    const pins = course.holes.filter((h) => !flags.some((f) => Math.hypot(f.pos[0] - h.green[0], f.pos[2] - h.green[2]) < 4));
    if (pins.length) {
      const parts = extractParts(await loadTemplate('props/flag.glb'));
      const ig = new InstancedGroup(parts, pins.length, { cull: false });
      pins.forEach((h, i) => ig.set(i, new Matrix4().makeTranslation(h.green[0], h.green[1], h.green[2])));
      ig.commit();
      ig.addTo(this.group);
      this.extra.push(ig);
    }
    const post = new MeshStandardNodeMaterial({ color: 0x6b4a2b, roughness: 0.9 });
    const postGeo = new BoxGeometry(0.1, 1.3, 0.1);
    const boardGeo = new PlaneGeometry(1.7, 0.85);
    this.disposables.push(post, postGeo, boardGeo);
    for (const h of course.holes) {
      const c = document.createElement('canvas');
      c.width = 256; c.height = 128;
      const g = c.getContext('2d')!;
      g.fillStyle = '#f4efe0'; g.fillRect(0, 0, 256, 128);
      g.strokeStyle = '#27473a'; g.lineWidth = 8; g.strokeRect(6, 6, 244, 116);
      g.fillStyle = '#27473a'; g.textAlign = 'center';
      g.font = '700 74px system-ui, sans-serif'; g.fillText(String(h.index + 1), 96, 90);
      g.font = '600 30px system-ui, sans-serif'; g.fillText('PAR', 188, 56); g.font = '700 46px system-ui, sans-serif'; g.fillText(String(h.par), 188, 102);
      const tex = new CanvasTexture(c);
      tex.colorSpace = SRGBColorSpace;
      const m = new MeshBasicNodeMaterial({ map: tex });
      this.disposables.push(tex, m);
      const board = new Mesh(boardGeo, m);
      board.position.set(h.tee[0] - 11, h.tee[1] + 1.35, h.tee[2] - 3);
      board.rotation.y = Math.PI; // faces back up the course towards the approaching car
      const pole = new Mesh(postGeo, post);
      pole.position.set(h.tee[0] - 11, h.tee[1] + 0.65, h.tee[2] - 3.05);
      board.castShadow = false;
      this.group.add(board, pole);
    }
  }

  /**
   * The finale kicker: a ramp wedge (11.5 m long, 8 m wide, 2.4 m high, per docs/FINALE.md) that the simulation
   * raises ahead of the car. It is not in course_json, so it grows out of the ground here over about a second.
   */
  async spawnKicker(x: number, y: number, z: number, yaw: number): Promise<void> {
    if (this.kicker) return;
    const parts = extractParts(await loadTemplate('props/ramp.glb'));
    const group = new InstancedGroup(parts, 1, { cull: false });
    group.addTo(this.group);
    this.kicker = { group, pos: new Vector3(x, y, z), yaw, t: 0 };
    this.placeKicker(0);
  }

  private placeKicker(u: number): void {
    const k = this.kicker;
    if (!k) return;
    const e = u * u * (3 - 2 * u);
    k.group.set(0, new Matrix4().compose(k.pos, new Quaternion().setFromAxisAngle(Y, k.yaw), new Vector3(8.0, Math.max(0.02, 2.4 * e), 11.5)));
    k.group.commit();
  }

  /** Number of props currently animating (diving spectators and tumbling knocked props). */
  get animating(): number { return this.dyn.size; }

  /** Solid obstacles (trees, carts, rocks) within `range` of a point, for camera avoidance. */
  solidsNear(x: number, z: number, range: number): { x: number; z: number; r: number; h: number }[] {
    const out: { x: number; z: number; r: number; h: number }[] = [];
    for (const p of this.course.props) {
      if (p.kind !== PropKind.Pine && p.kind !== PropKind.Broadleaf && p.kind !== PropKind.Cart && p.kind !== PropKind.Rock) continue;
      if (Math.hypot(p.pos[0] - x, p.pos[2] - z) > range) continue;
      const tall = p.kind === PropKind.Pine ? 11 : p.kind === PropKind.Broadleaf ? 8 : 2.5;
      out.push({ x: p.pos[0], z: p.pos[2], r: (p.kind === PropKind.Pine ? 2.2 : 3) * p.scale, h: p.pos[1] + tall * p.scale });
    }
    return out;
  }

  /** React to a simulation event that concerns scenery. */
  onEvent(e: SimEvent, carPos: Vector3, carVel: Vector3): void {
    if (e.kind === 7) this.dive(e.a, carPos);
    else if (e.kind === 4) this.knock(e.a, carVel);
  }

  private dive(pi: number, carPos: Vector3): void {
    const s = this.slot.get(pi);
    if (!s || s.kind !== PropKind.Spectator || this.dyn.has(pi)) return;
    const p = this.course.props[pi];
    const dir = p.pos[0] >= carPos.x ? 1 : -1;
    this.dyn.set(pi, { kind: 'dive', t: 0, pos: new Vector3(...p.pos), vel: new Vector3(), q: new Quaternion(), spin: new Vector3(), dir, rest: false });
  }

  private knock(pi: number, carVel: Vector3): void {
    const s = this.slot.get(pi);
    const p = this.course.props[pi];
    if (!s || !p || this.dyn.has(pi)) return;
    const sp = Math.max(8, carVel.length());
    const vel = new Vector3(carVel.x * 0.5 + (Math.random() - 0.5) * 6, 5 + sp * 0.25, carVel.z * 0.6 + 2);
    this.dyn.set(pi, {
      kind: 'tumble', t: 0, pos: new Vector3(...p.pos), vel, q: new Quaternion().setFromAxisAngle(Y, p.yaw),
      spin: new Vector3((Math.random() - 0.5) * 12, (Math.random() - 0.5) * 6, (Math.random() - 0.5) * 12), dir: 1, rest: false,
    });
  }

  update(dt: number): void {
    this.t += dt;
    if (this.kicker && this.kicker.t < 1) { this.kicker.t = Math.min(1, this.kicker.t + dt); this.placeKicker(this.kicker.t); }
    const spectGroup = this.groups.get(PropKind.Spectator);
    if (spectGroup) {
      for (const pi of this.spectators) {
        const p = this.course.props[pi];
        const d = this.dyn.get(pi);
        const s = this.slot.get(pi)!;
        if (d && d.kind === 'dive') {
          d.t += dt;
          const u = d.t;
          // 0..0.5 leap aside, 0.5..3.5 lie flat, 3.5..4.6 get up
          const leap = Math.min(1, u / 0.5);
          const up = Math.max(0, Math.min(1, (u - 3.5) / 1.1));
          const ease = leap * leap * (3 - 2 * leap) * (1 - up * up * (3 - 2 * up));
          const arc = Math.sin(Math.min(1, u / 0.5) * Math.PI) * 0.9 * (u < 0.5 ? 1 : 0);
          const x = p.pos[0] + d.dir * 3.2 * Math.min(1, leap) * (1 - up);
          const y = this.game.height_at(x, p.pos[2]) + arc;
          const q = new Quaternion().setFromAxisAngle(Y, p.yaw)
            .multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), -d.dir * 1.45 * ease))
            .multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), 0.25 * ease));
          this.scaleV.setScalar(p.scale);
          this.tmp.compose(new Vector3(x, y + 0.15 * ease, p.pos[2]), q, this.scaleV);
          if (u > 4.6) { this.dyn.delete(pi); }
        } else {
          // idle: shifting weight, the odd cheer
          const w = this.t * 1.6 + this.phase[pi];
          const q = new Quaternion().setFromAxisAngle(Y, p.yaw + Math.sin(w * 0.5) * 0.12)
            .multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.sin(w) * 0.035));
          this.scaleV.setScalar(p.scale);
          this.tmp.compose(new Vector3(p.pos[0], p.pos[1] + Math.max(0, Math.sin(w * 1.3 + 2)) * 0.03, p.pos[2]), q, this.scaleV);
        }
        spectGroup.set(s.i, this.tmp);
      }
      spectGroup.commit();
    }
    // knocked props tumble
    const touched = new Set<InstancedGroup>();
    for (const [pi, d] of this.dyn) {
      if (d.kind !== 'tumble' || d.rest) continue;
      d.t += dt;
      d.vel.y -= 9.8 * dt;
      d.pos.addScaledVector(d.vel, dt);
      const g = this.game.height_at(d.pos.x, d.pos.z);
      if (d.pos.y < g) { d.pos.y = g; d.vel.y *= -0.35; d.vel.x *= 0.7; d.vel.z *= 0.7; d.spin.multiplyScalar(0.6); if (d.vel.length() < 1.2) d.rest = true; }
      const dq = new Quaternion().setFromAxisAngle(d.spin.clone().normalize(), d.spin.length() * dt);
      d.q.premultiply(dq);
      const p = this.course.props[pi];
      this.scaleV.setScalar(p.scale);
      this.tmp.compose(d.pos, d.q, this.scaleV);
      const s = this.slot.get(pi)!;
      const ig = this.groups.get(s.kind)!;
      ig.set(s.i, this.tmp);
      touched.add(ig);
    }
    for (const ig of touched) ig.commit();
  }

  dispose(): void {
    for (const g of this.groups.values()) g.dispose();
    this.rampGroup?.dispose();
    this.kicker?.group.dispose();
    this.kicker = null;
    for (const g of this.extra) g.dispose();
    for (const d of this.disposables) d.dispose();
    this.group.clear();
  }
}

function compose(p: CourseProp): Matrix4 {
  return new Matrix4().compose(new Vector3(...p.pos), new Quaternion().setFromAxisAngle(Y, p.yaw), new Vector3(p.scale, p.scale, p.scale));
}
