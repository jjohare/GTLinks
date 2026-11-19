import { Box3, Group, Mesh, MeshStandardMaterial, MeshStandardNodeMaterial, Vector3 } from 'three';
import type { Material, Object3D } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import manifest from 'virtual:asset-manifest';
import { standInModel } from './standinModels';
import { proceduralModel } from './procedural';
import carsJson from '../../../assets/cars.json';
import type { CarSpec } from '../sim/types';

export const CARS: CarSpec[] = (carsJson as { cars: CarSpec[] }).cars;

const BASE = import.meta.env.BASE_URL;
const present = new Set(manifest);
const loader = new GLTFLoader();
const cache = new Map<string, Promise<Group>>();
/** Which paths fell back to primitives; surfaced for the report and debugging. */
export const standInsUsed = new Set<string>();

/** Convert any loaded standard material to its node-material equivalent (TSL-only rule). */
export function toNodeMaterial(m: Material): Material {
  if (m instanceof MeshStandardNodeMaterial) return m;
  if (m instanceof MeshStandardMaterial) {
    const n = new MeshStandardNodeMaterial();
    n.name = m.name;
    n.color.copy(m.color);
    n.roughness = m.roughness; n.metalness = m.metalness;
    n.emissive.copy(m.emissive); n.emissiveIntensity = m.emissiveIntensity;
    n.opacity = m.opacity; n.transparent = m.transparent;
    n.side = m.side;
    n.map = m.map; n.emissiveMap = m.emissiveMap;
    m.dispose();
    return n;
  }
  return m;
}

function fix(root: Object3D): void {
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(toNodeMaterial) : toNodeMaterial(mesh.material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
  });
}

/** Load a GLB by path under public/assets (e.g. "props/stein.glb"), or a stand-in if absent. Cached template. */
export function loadTemplate(rel: string): Promise<Group> {
  let p = cache.get(rel);
  if (!p) {
    p = (async () => {
      if (!present.has(`assets/${rel}`)) {
        const proc = proceduralModel(rel.split('/').pop()!.replace('.glb', ''));
        if (proc) { fix(proc); return proc; }
      }
      if (present.has(`assets/${rel}`)) {
        try {
          const gltf = await loader.loadAsync(`${BASE}assets/${rel}`);
          fix(gltf.scene);
          return gltf.scene;
        } catch (e) {
          console.info(`[assets] ${rel} failed to load (${(e as Error).message}); using stand-in`);
        }
      }
      standInsUsed.add(rel);
      const g = standInModel(rel, CARS);
      fix(g);
      return g;
    })();
    cache.set(rel, p);
  }
  return p;
}

/** An independent copy with its own materials, safe to recolour. */
export async function instantiate(rel: string): Promise<Group> {
  const t = await loadTemplate(rel);
  const c = t.clone(true);
  c.traverse((o) => {
    const m = o as Mesh;
    if (m.isMesh) m.material = Array.isArray(m.material) ? m.material.map((x) => x.clone()) : m.material.clone();
  });
  return c;
}

/** Scale a model so its bounding box height equals `h` (steins are gameplay-sized, not life-sized). */
export function normaliseHeight(o: Object3D, h: number): number {
  const b = new Box3().setFromObject(o);
  const s = h / Math.max(1e-6, b.max.y - b.min.y);
  o.scale.multiplyScalar(s);
  return s;
}
export function sizeOf(o: Object3D): Vector3 { return new Box3().setFromObject(o).getSize(new Vector3()); }

export async function preloadAll(): Promise<void> {
  const props = ['stein', 'lodge', 'table', 'tree_pine', 'tree_broadleaf', 'spectator', 'flag', 'tee_marker', 'golf_cart', 'ramp'];
  await Promise.all([
    ...props.map((n) => loadTemplate(`props/${n}.glb`)),
    ...CARS.map((c) => loadTemplate(`cars/${c.key}.glb`)),
  ]);
}
