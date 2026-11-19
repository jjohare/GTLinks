import {
  BufferGeometry, BufferAttribute, Mesh, Group, MeshStandardNodeMaterial, Sphere, Vector3,
} from 'three/webgpu';
import {
  Fn, attribute, vec3, float, mix, smoothstep, positionWorld, normalWorld, fract, mx_noise_float, clamp, step,
} from 'three/tsl';
import { NX, NZ, CELL, X0 } from '../sim/types';
import { buildChunkIndices } from './terrainIndex';

const CH = 32; // cells per chunk edge

/** Sample a height with clamped indices (the grid is analytic beyond, but edge normals only need local slope). */
const hAt = (h: Float32Array, ix: number, iz: number) =>
  h[Math.max(0, Math.min(NZ - 1, iz)) * NX + Math.max(0, Math.min(NX - 1, ix))];

/**
 * Blur surface ids into 8 per-vertex weights (3x3 box), packed as two vec4 attributes.
 * Vertex attributes avoid sampler limits entirely, so the WebGL2 fallback behaves identically.
 */
export function surfaceWeights(surf: Uint8Array, ix: number, iz: number, out: Float32Array, o: number): void {
  for (let k = 0; k < 8; k++) out[o + k] = 0;
  let n = 0;
  for (let dz = -1; dz <= 1; dz++) {
    for (let dx = -1; dx <= 1; dx++) {
      const x = Math.max(0, Math.min(NX - 1, ix + dx)), z = Math.max(0, Math.min(NZ - 1, iz + dz));
      const w = dx === 0 && dz === 0 ? 2 : 1;
      out[o + surf[z * NX + x]] += w;
      n += w;
    }
  }
  for (let k = 0; k < 8; k++) out[o + k] /= n;
}

function buildMaterial(): MeshStandardNodeMaterial {
  const m = new MeshStandardNodeMaterial({ roughness: 0.95, metalness: 0 });
  m.colorNode = Fn(() => {
    const wA = attribute('wA', 'vec4'); // rough, fairway, green, bunker
    const wB = attribute('wB', 'vec4'); // tee, cart path, rock, water
    const p = positionWorld;
    const n1 = mx_noise_float(vec3(p.x.mul(0.35), p.z.mul(0.35), 0.0)).mul(0.5).add(0.5);
    const n2 = mx_noise_float(vec3(p.x.mul(2.1), p.z.mul(2.1), 1.7)).mul(0.5).add(0.5);
    const n3 = mx_noise_float(vec3(p.x.mul(9.0), p.z.mul(9.0), 3.1)).mul(0.5).add(0.5);

    // rough: darker, tufted
    const roughCol = mix(vec3(0.18, 0.30, 0.10), vec3(0.28, 0.40, 0.14), n1).mul(mix(0.78, 1.12, n3));
    // fairway: mown stripes, skewed a little so they read as cut across the fall line
    const stripeCoord = p.z.mul(0.19).add(p.x.mul(0.035));
    const stripe = step(0.5, fract(stripeCoord));
    const fairCol = mix(vec3(0.30, 0.50, 0.16), vec3(0.37, 0.58, 0.20), stripe).mul(mix(0.94, 1.06, n2));
    // green: finer, lighter cut
    const gStripe = step(0.5, fract(p.z.mul(0.9).add(p.x.mul(0.2))));
    const greenCol = mix(vec3(0.40, 0.66, 0.26), vec3(0.46, 0.73, 0.30), gStripe).mul(mix(0.96, 1.04, n3));
    // bunker: pale sand with grain, darker lip where the weight rolls off
    const sand = mix(vec3(0.86, 0.78, 0.58), vec3(0.93, 0.87, 0.69), n3);
    const lip = smoothstep(0.08, 0.35, wA.w).mul(float(1).sub(smoothstep(0.45, 0.85, wA.w)));
    const sandCol = mix(sand, vec3(0.62, 0.52, 0.34), lip.mul(0.6));
    const teeCol = mix(vec3(0.42, 0.66, 0.24), vec3(0.50, 0.74, 0.28), step(0.5, fract(p.x.mul(0.8).add(p.z.mul(0.8))))).mul(mix(0.97, 1.03, n3));
    const pathCol = mix(vec3(0.62, 0.58, 0.50), vec3(0.70, 0.66, 0.58), n2);
    const rockCol = mix(vec3(0.42, 0.40, 0.38), vec3(0.58, 0.56, 0.52), n2.mul(0.6).add(n3.mul(0.4)));
    const waterCol = vec3(0.16, 0.36, 0.5);

    let col = roughCol.mul(wA.x)
      .add(fairCol.mul(wA.y))
      .add(greenCol.mul(wA.z))
      .add(sandCol.mul(wA.w))
      .add(teeCol.mul(wB.x))
      .add(pathCol.mul(wB.y))
      .add(rockCol.mul(wB.z))
      .add(waterCol.mul(wB.w));
    // slope-based rock on steep ground, with a snowless alpine meadow above
    const slope = float(1).sub(clamp(normalWorld.y, 0, 1));
    const steep = smoothstep(0.16, 0.34, slope.add(n1.sub(0.5).mul(0.06)));
    col = mix(col, rockCol, steep);
    // altitude: thinner, drier grass high up near the summit
    const alt = smoothstep(420, 560, p.y);
    col = mix(col, col.mul(vec3(1.15, 1.08, 0.92)), alt.mul(0.5));
    return col;
  })();
  return m;
}

export class Terrain {
  readonly group = new Group();
  private geoms: BufferGeometry[] = [];
  private material = buildMaterial();

  constructor(heights: Float32Array, surf: Uint8Array, heightAt: (x: number, z: number) => number) {
    const stride = CH + 1;
    const index = buildChunkIndices(0, 0, CH, CH, stride);
    const indexAttr = new BufferAttribute(index, 1);
    const cxN = (NX - 1) / CH, czN = (NZ - 1) / CH;
    for (let cz = 0; cz < czN; cz++) {
      for (let cx = 0; cx < cxN; cx++) {
        const nv = stride * stride;
        const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3);
        const wA = new Float32Array(nv * 4), wB = new Float32Array(nv * 4);
        const w8 = new Float32Array(8);
        let k = 0;
        for (let j = 0; j < stride; j++) {
          for (let i = 0; i < stride; i++, k++) {
            const ix = cx * CH + i, iz = cz * CH + j;
            const y = hAt(heights, ix, iz);
            pos[k * 3] = X0 + ix * CELL; pos[k * 3 + 1] = y; pos[k * 3 + 2] = iz * CELL;
            const dx = (hAt(heights, ix + 1, iz) - hAt(heights, ix - 1, iz)) / (2 * CELL);
            const dz = (hAt(heights, ix, iz + 1) - hAt(heights, ix, iz - 1)) / (2 * CELL);
            const l = Math.hypot(dx, 1, dz);
            nor[k * 3] = -dx / l; nor[k * 3 + 1] = 1 / l; nor[k * 3 + 2] = -dz / l;
            surfaceWeights(surf, ix, iz, w8, 0);
            wA.set(w8.subarray(0, 4), k * 4); wB.set(w8.subarray(4, 8), k * 4);
          }
        }
        const g = new BufferGeometry();
        g.setAttribute('position', new BufferAttribute(pos, 3));
        g.setAttribute('normal', new BufferAttribute(nor, 3));
        g.setAttribute('wA', new BufferAttribute(wA, 4));
        g.setAttribute('wB', new BufferAttribute(wB, 4));
        g.setIndex(indexAttr);
        // bounding sphere from the actual extent
        let lo = Infinity, hi = -Infinity;
        for (let q = 0; q < nv; q++) { const y = pos[q * 3 + 1]; if (y < lo) lo = y; if (y > hi) hi = y; }
        const cxm = X0 + (cx * CH + CH / 2) * CELL, czm = (cz * CH + CH / 2) * CELL;
        g.boundingSphere = new Sphere(new Vector3(cxm, (lo + hi) / 2, czm), Math.hypot(CH * CELL / 2 * 1.4143, (hi - lo) / 2) + 1);
        const mesh = new Mesh(g, this.material);
        mesh.receiveShadow = true;
        mesh.matrixAutoUpdate = false;
        this.geoms.push(g);
        this.group.add(mesh);
      }
    }
    this.buildSkirt(heightAt);
  }

  /**
   * Coarse apron beyond the contract grid so the world never ends in a void. Heights come from the
   * simulation's analytic height_at; it sits a few metres below the fine mesh and overlaps its border by one cell so no seam shows sky.
   */
  private buildSkirt(heightAt: (x: number, z: number) => number): void {
    const step = 80, x0 = -3600, x1 = 3600, z0 = -2000, z1 = 4800;
    const cols = (x1 - x0) / step + 1, rows = (z1 - z0) / step + 1;
    const pos = new Float32Array(cols * rows * 3), nor = new Float32Array(cols * rows * 3);
    const wA = new Float32Array(cols * rows * 4), wB = new Float32Array(cols * rows * 4);
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const k = j * cols + i, x = x0 + i * step, z = z0 + j * step;
        pos[k * 3] = x; pos[k * 3 + 1] = heightAt(x, z) - 3; pos[k * 3 + 2] = z;
        const dx = (heightAt(x + 20, z) - heightAt(x - 20, z)) / 40, dz = (heightAt(x, z + 20) - heightAt(x, z - 20)) / 40;
        const l = Math.hypot(dx, 1, dz);
        nor[k * 3] = -dx / l; nor[k * 3 + 1] = 1 / l; nor[k * 3 + 2] = -dz / l;
        wA[k * 4] = 1;
      }
    }
    const inner = (x: number, z: number) => x > X0 + step && x < -X0 - step && z > step && z < (NZ - 1) * CELL - step;
    const idx: number[] = [];
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cols - 1; i++) {
        if (inner(x0 + (i + 0.5) * step, z0 + (j + 0.5) * step)) continue;
        const a = j * cols + i, b = a + 1, c = a + cols, d = c + 1;
        idx.push(a, c, d, a, d, b);
      }
    }
    const g = new BufferGeometry();
    g.setAttribute('position', new BufferAttribute(pos, 3));
    g.setAttribute('normal', new BufferAttribute(nor, 3));
    g.setAttribute('wA', new BufferAttribute(wA, 4));
    g.setAttribute('wB', new BufferAttribute(wB, 4));
    g.setIndex(idx);
    g.boundingSphere = new Sphere(new Vector3(0, 300, 1400), 6000);
    const m = new Mesh(g, this.material);
    m.receiveShadow = false;
    m.frustumCulled = false;
    this.geoms.push(g);
    this.group.add(m);
  }

  dispose(): void {
    // the shared index attribute is released with the first geometry; the rest only hold references
    for (const g of this.geoms) g.dispose();
    this.material.dispose();
    this.group.clear();
    this.geoms = [];
  }
}
