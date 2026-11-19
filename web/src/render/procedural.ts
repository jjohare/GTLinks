import { Group, Mesh, IcosahedronGeometry, BoxGeometry, MeshStandardNodeMaterial, CylinderGeometry } from 'three/webgpu';

/** Props the contract does not ship as GLBs (rock, sign) and the small fx meshes: built in code, permanently. */
export function proceduralModel(name: string): Group | null {
  const g = new Group();
  g.name = name;
  if (name === 'rock') {
    const geo = new IcosahedronGeometry(1, 1);
    const p = geo.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
      const n = 0.82 + 0.28 * Math.abs(Math.sin(x * 3.1 + z * 2.3) * Math.cos(y * 2.7 + x * 1.3));
      p.setXYZ(i, x * n * 1.15, y * n * 0.7, z * n);
    }
    geo.computeVertexNormals();
    const m = new MeshStandardNodeMaterial({ color: 0x77736c, roughness: 0.95, flatShading: true });
    m.name = 'rock';
    const mesh = new Mesh(geo, m);
    mesh.position.y = 0.45;
    g.add(mesh);
    return g;
  }
  if (name === 'sign') {
    const wood = new MeshStandardNodeMaterial({ color: 0x7a5535, roughness: 0.85 });
    wood.name = 'wood';
    const board = new MeshStandardNodeMaterial({ color: 0xf1e8cf, roughness: 0.8 });
    board.name = 'board';
    const post = new Mesh(new CylinderGeometry(0.05, 0.05, 1.5, 6), wood);
    post.position.y = 0.75;
    const b = new Mesh(new BoxGeometry(1.0, 0.5, 0.05), board);
    b.position.y = 1.35;
    g.add(post, b);
    return g;
  }
  return null;
}
