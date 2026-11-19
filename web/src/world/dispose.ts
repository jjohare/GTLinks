import type { Material, Mesh, Object3D } from 'three/webgpu';

/** Dispose materials (and optionally geometry) beneath `root`. Template geometry is shared and must be kept. */
export function disposeTree(root: Object3D, geometry = false): void {
  root.traverse((o) => {
    const m = o as Mesh;
    if (!m.isMesh) return;
    if (geometry) m.geometry.dispose();
    const mats: Material[] = Array.isArray(m.material) ? m.material : [m.material];
    for (const x of mats) x.dispose();
  });
  root.removeFromParent();
}
