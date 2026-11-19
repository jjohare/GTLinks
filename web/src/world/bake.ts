import { BufferAttribute, BufferGeometry, Group, Mesh, Matrix4 } from 'three/webgpu';
import type { Material, MeshStandardNodeMaterial, Object3D } from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const keyOf = (m: Material): string => {
  const s = m as MeshStandardNodeMaterial;
  return [m.name, s.color?.getHex(), s.roughness, s.metalness, s.emissive?.getHex(), s.emissiveIntensity, m.opacity, m.transparent, m.side, s.map?.uuid ?? ''].join('|');
};

/**
 * Merge a static model's meshes by material so it costs a handful of draw calls instead of
 * hundreds. The returned group owns its geometry (dispose with `disposeTree(group, true)`).
 * Falls back to the original model if the attribute layouts cannot be merged.
 */
export function bakeStatic(model: Object3D): Group {
  model.updateMatrixWorld(true);
  const inv = model.matrixWorld.clone().invert();
  const buckets = new Map<string, { mat: Material; geos: BufferGeometry[]; shadow: boolean }>();
  const rel = new Matrix4();
  model.traverse((o) => {
    const m = o as Mesh;
    if (!m.isMesh || Array.isArray(m.material)) return;
    const g = m.geometry.clone();
    rel.multiplyMatrices(inv, m.matrixWorld);
    g.applyMatrix4(rel);
    for (const name of Object.keys(g.attributes)) if (name !== 'position' && name !== 'normal' && name !== 'uv') g.deleteAttribute(name);
    if (!g.attributes.normal) g.computeVertexNormals();
    if (!g.attributes.uv) g.setAttribute('uv', new BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    if (!g.index) { const n = g.attributes.position.count; const idx = new Uint32Array(n); for (let i = 0; i < n; i++) idx[i] = i; g.setIndex(new BufferAttribute(idx, 1)); }
    const k = keyOf(m.material);
    const b = buckets.get(k) ?? { mat: m.material, geos: [], shadow: m.castShadow };
    b.geos.push(g);
    buckets.set(k, b);
  });
  const out = new Group();
  out.name = model.name;
  for (const b of buckets.values()) {
    const merged = mergeGeometries(b.geos, false);
    for (const g of b.geos) g.dispose();
    if (!merged) {
      // cannot merge: keep the model but give it geometry of its own so the caller may dispose it safely
      model.traverse((o) => { const m = o as Mesh; if (m.isMesh) m.geometry = m.geometry.clone(); });
      for (const x of buckets.values()) for (const g of x.geos) g.dispose();
      return model as Group;
    }
    const mesh = new Mesh(merged, b.mat);
    mesh.castShadow = b.shadow;
    mesh.receiveShadow = true;
    out.add(mesh);
  }
  // the unmerged clones' materials are no longer referenced
  model.traverse((o) => { const m = o as Mesh; if (m.isMesh && !Array.isArray(m.material) && ![...buckets.values()].some((b) => b.mat === m.material)) m.material.dispose(); });
  return out;
}
