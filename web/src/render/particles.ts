import { InstancedMesh, IcosahedronGeometry, MeshBasicNodeMaterial, Matrix4, Color, Vector3, Quaternion, Object3D } from 'three/webgpu';

export type FxKind = 'dust' | 'sand' | 'grass' | 'foam' | 'steam' | 'lager' | 'spark';

interface Spec { colours: number[]; life: [number, number]; size: [number, number]; grow: number; gravity: number; drag: number }
const SPECS: Record<FxKind, Spec> = {
  dust: { colours: [0xcbbd9c, 0xb8aa8a, 0xd9cdb0], life: [0.45, 0.9], size: [0.07, 0.14], grow: 2.0, gravity: -0.3, drag: 1.8 },
  sand: { colours: [0xe8d9a8, 0xf0e2b4, 0xd8c68e], life: [0.6, 1.2], size: [0.12, 0.26], grow: 0.4, gravity: 7, drag: 0.6 },
  grass: { colours: [0x4d8a2a, 0x62a031, 0x3b6f21, 0x6b4a2b], life: [0.7, 1.3], size: [0.07, 0.14], grow: 0, gravity: 9, drag: 0.4 },
  foam: { colours: [0xfffdf2, 0xfff3c8, 0xffffff], life: [0.6, 1.1], size: [0.1, 0.22], grow: 0.8, gravity: 3.5, drag: 1.2 },
  lager: { colours: [0xe8a317, 0xf2b52a, 0xd18f0f], life: [0.6, 1.0], size: [0.05, 0.1], grow: 0, gravity: 9.8, drag: 0.3 },
  steam: { colours: [0xe9eef0, 0xdfe6e9], life: [1.2, 2.0], size: [0.06, 0.12], grow: 2.2, gravity: -1.4, drag: 0.9 },
  spark: { colours: [0xfff0a0, 0xffd060], life: [0.2, 0.45], size: [0.04, 0.08], grow: -0.6, gravity: 6, drag: 0.5 },
};

/** Pooled, instanced particles. Dead slots are collapsed to zero scale. */
export class Particles {
  readonly mesh: InstancedMesh;
  private readonly cap: number;
  private px: Float32Array; private py: Float32Array; private pz: Float32Array;
  private vx: Float32Array; private vy: Float32Array; private vz: Float32Array;
  private life: Float32Array; private maxLife: Float32Array; private size: Float32Array; private grow: Float32Array;
  private grav: Float32Array; private drag: Float32Array;
  private head = 0;
  private m = new Matrix4(); private q = new Quaternion(); private s = new Vector3(); private p = new Vector3();
  private col = new Color();
  private geo = new IcosahedronGeometry(1, 1);
  private mat = new MeshBasicNodeMaterial();
  private zero = new Matrix4().makeScale(0, 0, 0);

  constructor(cap = 900) {
    this.cap = cap;
    this.mesh = new InstancedMesh(this.geo, this.mat, cap);
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = false;
    const mk = () => new Float32Array(cap);
    this.px = mk(); this.py = mk(); this.pz = mk(); this.vx = mk(); this.vy = mk(); this.vz = mk();
    this.life = mk(); this.maxLife = mk(); this.size = mk(); this.grow = mk(); this.grav = mk(); this.drag = mk();
    for (let i = 0; i < cap; i++) { this.mesh.setMatrixAt(i, this.zero); this.mesh.setColorAt(i, this.col.set(0xffffff)); }
  }

  emit(kind: FxKind, pos: Vector3, n: number, vel: Vector3 = new Vector3(), spread = 1.5, upBias = 1): void {
    const sp = SPECS[kind];
    for (let k = 0; k < n; k++) {
      const i = this.head++ % this.cap;
      const r = () => Math.random() - 0.5;
      this.px[i] = pos.x + r() * 0.4; this.py[i] = pos.y + r() * 0.2; this.pz[i] = pos.z + r() * 0.4;
      this.vx[i] = vel.x + r() * spread * 2; this.vy[i] = vel.y + (Math.random() * upBias + 0.2) * spread; this.vz[i] = vel.z + r() * spread * 2;
      this.maxLife[i] = this.life[i] = sp.life[0] + Math.random() * (sp.life[1] - sp.life[0]);
      this.size[i] = (sp.size[0] + Math.random() * (sp.size[1] - sp.size[0])) * 0.55;
      this.grow[i] = sp.grow; this.grav[i] = sp.gravity; this.drag[i] = sp.drag;
      this.mesh.setColorAt(i, this.col.set(sp.colours[Math.floor(Math.random() * sp.colours.length)]));
    }
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
  }

  update(dt: number): void {
    for (let i = 0; i < this.cap; i++) {
      if (this.life[i] <= 0) continue;
      this.life[i] -= dt;
      if (this.life[i] <= 0) { this.mesh.setMatrixAt(i, this.zero); continue; }
      const d = Math.exp(-this.drag[i] * dt);
      this.vx[i] *= d; this.vz[i] *= d; this.vy[i] = this.vy[i] * d - this.grav[i] * dt;
      this.px[i] += this.vx[i] * dt; this.py[i] += this.vy[i] * dt; this.pz[i] += this.vz[i] * dt;
      const u = 1 - this.life[i] / this.maxLife[i];
      const sz = Math.max(0, this.size[i] * (1 + this.grow[i] * u) * (1 - u * u * 0.9));
      this.p.set(this.px[i], this.py[i], this.pz[i]);
      this.s.setScalar(sz);
      this.m.compose(this.p, this.q, this.s);
      this.mesh.setMatrixAt(i, this.m);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  clear(): void { this.life.fill(0); for (let i = 0; i < this.cap; i++) this.mesh.setMatrixAt(i, this.zero); this.mesh.instanceMatrix.needsUpdate = true; }

  dispose(): void { (this.mesh as Object3D).removeFromParent(); this.mesh.dispose(); this.geo.dispose(); this.mat.dispose(); }
}
