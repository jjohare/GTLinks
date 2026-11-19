import { InstancedMesh, Matrix4, Color } from 'three/webgpu';
import type { BufferGeometry, Material, Mesh, Object3D, Group } from 'three/webgpu';

export interface Part { geometry: BufferGeometry; material: Material; matrix: Matrix4; name: string }

/** Flatten a template into mesh parts with transforms relative to the template root. */
export function extractParts(root: Object3D): Part[] {
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert();
  const parts: Part[] = [];
  root.traverse((o) => {
    const m = o as Mesh;
    if (!m.isMesh) return;
    const mat = Array.isArray(m.material) ? m.material[0] : m.material;
    parts.push({ geometry: m.geometry, material: mat, matrix: inv.clone().multiply(m.matrixWorld), name: mat.name });
  });
  return parts;
}

/** One InstancedMesh per template part, driven together. Geometry and materials stay owned by the asset cache. */
export class InstancedGroup {
  readonly meshes: InstancedMesh[] = [];
  private tmp = new Matrix4();
  private colourPart: string | null;

  constructor(parts: Part[], readonly capacity: number, opts: { shadows?: boolean; cull?: boolean; colourPart?: string } = {}) {
    this.colourPart = opts.colourPart ?? null;
    for (const p of parts) {
      const im = new InstancedMesh(p.geometry, p.material, Math.max(1, capacity));
      im.count = capacity;
      im.castShadow = opts.shadows ?? true;
      im.receiveShadow = true;
      im.frustumCulled = opts.cull ?? true;
      this.meshes.push(im);
    }
    this.parts = parts;
  }
  private parts: Part[];

  set(i: number, world: Matrix4): void {
    for (let k = 0; k < this.meshes.length; k++) {
      this.tmp.multiplyMatrices(world, this.parts[k].matrix);
      this.meshes[k].setMatrixAt(i, this.tmp);
    }
  }
  setColour(i: number, c: Color): void {
    if (!this.colourPart) return;
    for (let k = 0; k < this.meshes.length; k++) if (this.parts[k].name === this.colourPart) this.meshes[k].setColorAt(i, c);
  }
  commit(): void {
    for (const m of this.meshes) {
      m.instanceMatrix.needsUpdate = true;
      if (m.instanceColor) m.instanceColor.needsUpdate = true;
    }
  }
  addTo(g: Group): void { for (const m of this.meshes) g.add(m); }
  dispose(): void { for (const m of this.meshes) { m.removeFromParent(); m.dispose(); } }
}
