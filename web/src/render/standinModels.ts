/**
 * STAND-IN MODELS. Delete this file at integration.
 *
 * Returns simple primitive stand-ins, named per the contract's GLB layout, for any GLB that
 * has not been produced yet. The asset loader calls this only when the file is absent from the
 * build-time manifest (or fails to parse).
 */
import {
  BoxGeometry, CylinderGeometry, Group, Mesh, MeshStandardNodeMaterial, ConeGeometry, SphereGeometry,
  TorusGeometry, IcosahedronGeometry, BufferGeometry, BufferAttribute,
} from 'three/webgpu';
import type { Object3D } from 'three/webgpu';
import type { CarSpec } from '../sim/types';

const mat = (name: string, color: number, rough = 0.7, metal = 0, emissive = 0x000000, ei = 0) => {
  const m = new MeshStandardNodeMaterial({ color, roughness: rough, metalness: metal });
  m.name = name;
  if (ei > 0) { m.emissive.setHex(emissive); m.emissiveIntensity = ei; }
  return m;
};
const box = (w: number, h: number, d: number, m: MeshStandardNodeMaterial, x = 0, y = 0, z = 0, name = '') => {
  const o = new Mesh(new BoxGeometry(w, h, d), m);
  o.position.set(x, y, z);
  if (name) o.name = name;
  return o;
};
const named = <T extends Object3D>(o: T, n: string): T => { o.name = n; return o; };

export function standInModel(path: string, cars: CarSpec[]): Group {
  const file = path.split('/').pop()!.replace('.glb', '');
  const car = cars.find((c) => c.key === file);
  if (car) return standInCar(car);
  const g = new Group();
  switch (file) {
    case 'stein': {
      const glass = mat('glass', 0xcfe6ee, 0.1, 0);
      glass.transparent = true; glass.opacity = 0.35;
      const cup = new Mesh(new CylinderGeometry(0.075, 0.065, 0.2, 14), glass);
      cup.position.y = 0.1;
      const lager = new Mesh(new CylinderGeometry(0.066, 0.058, 0.16, 14), mat('lager', 0xe8a317, 0.3));
      lager.position.y = 0.09;
      const foam = new Mesh(new CylinderGeometry(0.07, 0.066, 0.04, 14), mat('foam', 0xfff7e0, 0.9));
      foam.position.y = 0.19;
      const handle = new Mesh(new TorusGeometry(0.05, 0.012, 6, 12), glass);
      handle.position.set(0.09, 0.1, 0); 
      g.add(cup, lager, foam, handle);
      break;
    }
    case 'table': {
      const wood = mat('wood', 0x8a5a33, 0.8);
      g.add(box(3, 0.08, 1.3, wood, 0, 0.9, 0));
      for (const sx of [-1.3, 1.3]) for (const sz of [-0.5, 0.5]) g.add(box(0.1, 0.9, 0.1, wood, sx, 0.45, sz));
      break;
    }
    case 'lodge': {
      const wood = mat('wood', 0x7a4f2e, 0.85), roof = mat('roof', 0x3b3a3c, 0.8), deck = mat('deck', 0xa07a52, 0.9);
      g.add(box(24, 0.3, 14, deck, 0, -0.15, 0));
      g.add(box(22, 6, 10, wood, 0, 3, -12));
      const r = new Mesh(new ConeGeometry(9, 4.5, 4), roof);
      r.position.set(0, 8.2, -12); r.rotation.y = Math.PI / 4; r.scale.set(1.35, 1, 1.0);
      g.add(r);
      const pylon = new Group();
      pylon.add(box(0.5, 9, 0.5, mat('steel', 0x777c80, 0.5, 0.6), 0, 4.5, 0), box(3, 0.3, 0.3, mat('steel', 0x777c80, 0.5, 0.6), 0, 9, 0));
      pylon.position.set(16, 0, -2);
      g.add(pylon);
      break;
    }
    case 'tree_pine': {
      g.add(new Mesh(new CylinderGeometry(0.15, 0.22, 2, 6), mat('bark', 0x4d3623, 0.9)).translateY(1));
      const leaf = mat('needles', 0x24512f, 0.9);
      for (let i = 0; i < 3; i++) g.add(new Mesh(new ConeGeometry(1.5 - i * 0.35, 3 - i * 0.4, 7), leaf).translateY(3 + i * 1.5));
      break;
    }
    case 'tree_broadleaf': {
      g.add(new Mesh(new CylinderGeometry(0.2, 0.28, 2.6, 6), mat('bark', 0x5b4330, 0.9)).translateY(1.3));
      g.add(new Mesh(new IcosahedronGeometry(2, 1), mat('leaves', 0x4a7f33, 0.85)).translateY(4.2));
      break;
    }
    case 'spectator': {
      g.add(box(0.5, 0.75, 0.3, mat('shirt', 0xd14b3a, 0.8), 0, 1.1, 0));
      g.add(box(0.4, 0.8, 0.26, mat('trousers', 0x3a3f55, 0.8), 0, 0.4, 0));
      g.add(new Mesh(new SphereGeometry(0.16, 8, 6), mat('skin', 0xe3b894, 0.8)).translateY(1.65));
      break;
    }
    case 'flag': {
      g.add(new Mesh(new CylinderGeometry(0.025, 0.025, 2.4, 6), mat('pole', 0xf2f2f2, 0.5)).translateY(1.2));
      g.add(box(0.6, 0.38, 0.02, mat('cloth', 0xe0382c, 0.8), 0.3, 2.15, 0));
      break;
    }
    case 'tee_marker': {
      g.add(new Mesh(new SphereGeometry(0.16, 10, 8), mat('marker', 0xf2f2f2, 0.5)).translateY(0.16));
      break;
    }
    case 'golf_cart': {
      const body = mat('cartbody', 0xf0f0e8, 0.6);
      g.add(box(1.2, 0.5, 2.3, body, 0, 0.55, 0), box(1.3, 0.05, 1.2, mat('canopy', 0x2f6d4d), 0, 1.75, -0.2));
      for (const x of [-0.55, 0.55]) for (const z of [-0.8, 0.8]) g.add(box(0.14, 0.45, 0.45, mat('tyre', 0x1b1b1b, 0.9), x, 0.25, z));
      for (const x of [-0.6, 0.6]) g.add(box(0.04, 1.2, 0.04, body, x, 1.15, -0.8));
      break;
    }
    case 'ramp': {
      // unit wedge: 1 m long in +Z, 1 m wide, 1 m high at the far end, flush with the ground at the near end
      const v = new Float32Array([
        -0.5, 0, 0, 0.5, 0, 0, -0.5, 0, 1, 0.5, 0, 1, -0.5, 1, 1, 0.5, 1, 1,
      ]);
      const idx = [0, 2, 3, 0, 3, 1, 2, 4, 5, 2, 5, 3, 0, 4, 2, 1, 3, 5, 0, 1, 5, 0, 5, 4];
      const geo = new BufferGeometry();
      geo.setAttribute('position', new BufferAttribute(v, 3));
      geo.setIndex(idx);
      geo.computeVertexNormals();
      g.add(new Mesh(geo, mat('ramp', 0x9b7b53, 0.85)));
      break;
    }
    case 'rock': {
      const geo = new IcosahedronGeometry(1, 1);
      const p = geo.attributes.position;
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
        const n = 0.82 + 0.28 * Math.abs(Math.sin(x * 3.1 + z * 2.3) * Math.cos(y * 2.7 + x * 1.3));
        p.setXYZ(i, x * n * 1.15, y * n * 0.7, z * n);
      }
      geo.computeVertexNormals();
      const rm = mat('rock', 0x77736c, 0.95);
      rm.flatShading = true;
      g.add(new Mesh(geo, rm).translateY(0.45));
      break;
    }
    case 'sign': {
      const wood = mat('wood', 0x7a5535, 0.85);
      g.add(new Mesh(new CylinderGeometry(0.05, 0.05, 1.5, 6), wood).translateY(0.75), box(1.0, 0.5, 0.05, mat('board', 0xf1e8cf, 0.8), 0, 1.35, 0));
      break;
    }
    case 'drone': {
      g.add(box(0.5, 0.12, 0.5, mat('drone', 0x2a2d33, 0.5)));
      break;
    }
    default:
      g.add(box(1, 1, 1, mat('missing', 0xff00ff)));
  }
  g.name = file;
  return g;
}

function standInCar(c: CarSpec): Group {
  const root = new Group();
  root.name = 'car';
  const paint = mat('paint', parseInt(c.paint.slice(1), 16), 0.35, 0.4);
  const glass = mat('glass', 0x1d2a33, 0.1, 0.1);
  const L = c.length, W = c.width, H = c.height, wr = c.wheel_radius, wb = c.wheelbase, tr = c.track;
  const lowY = c.ground_clearance + 0.35;
  const body = new Group(); body.name = 'body';
  body.add(box(W, 0.8, L * 0.9, paint, 0, lowY + 0.1, 0));
  body.add(box(W * 0.94, H - lowY - 0.65, L * 0.55, paint, 0, (H + lowY + 0.5) / 2, -L * 0.05));
  root.add(body);
  const gl = new Group(); gl.name = 'glass';
  gl.add(box(W * 0.95, H - lowY - 0.75, L * 0.5, glass, 0, (H + lowY + 0.5) / 2 - 0.02, -L * 0.05));
  root.add(gl);
  const tyre = mat('tyre', 0x161616, 0.9);
  const names = ['wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr'];
  names.forEach((n, i) => {
    const w = new Group(); w.name = n;
    const m = new Mesh(new CylinderGeometry(wr, wr, c.wheel_width, 18), tyre);
    m.rotation.z = Math.PI / 2;
    const hub = new Mesh(new CylinderGeometry(wr * 0.55, wr * 0.55, c.wheel_width + 0.02, 10), mat('rim', 0xb8bcc0, 0.3, 0.8));
    hub.rotation.z = Math.PI / 2;
    const spoke = box(c.wheel_width + 0.03, wr * 0.2, wr * 1.1, mat('rim', 0xb8bcc0, 0.3, 0.8));
    w.add(m, hub, spoke);
    w.position.set((i % 2 === 0 ? 1 : -1) * tr / 2, wr, (i < 2 ? 1 : -1) * wb / 2);
    root.add(w);
  });
  const hl = mat('headlight', 0xfff2c8, 0.2, 0, 0xfff2c8, 1.2);
  for (const [n, s] of [['headlight_l', 1], ['headlight_r', -1]] as const) {
    const h = new Group(); h.name = n;
    h.add(box(0.46, 0.24, 0.08, hl));
    h.position.set(s * W * 0.34, lowY + 0.3, L * 0.45 + 0.02);
    root.add(h);
  }
  const part = (n: string, w: number, h: number, d: number, x: number, y: number, z: number, ox: number, oy: number, oz: number) => {
    const g = new Group(); g.name = n; g.position.set(x, y, z);
    g.add(box(w, h, d, paint, ox, oy, oz));
    root.add(g);
  };
  part('bumper_front', W * 0.98, 0.3, 0.3, 0, lowY - 0.1, L * 0.45, 0, 0, 0.05);
  part('bumper_rear', W * 0.98, 0.3, 0.3, 0, lowY - 0.1, -L * 0.45, 0, 0, -0.05);
  part('bonnet', W * 0.9, 0.08, L * 0.28, 0, lowY + 0.52, L * 0.2, 0, 0, L * 0.14);
  part('mirror_l', 0.2, 0.16, 0.12, W / 2 + 0.05, H * 0.62, L * 0.18, 0.08, 0, 0);
  part('mirror_r', 0.2, 0.16, 0.12, -W / 2 - 0.05, H * 0.62, L * 0.18, -0.08, 0, 0);
  const anchor = named(new Group(), 'roof_anchor');
  anchor.position.set(0, H, -L * 0.05);
  root.add(anchor);
  return root;
}
