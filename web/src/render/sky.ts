import {
  Mesh, SphereGeometry, BackSide, MeshBasicNodeMaterial, Group, BufferGeometry, BufferAttribute, Vector3, Color, DirectionalLight, HemisphereLight, Scene, FogExp2, Camera,
} from 'three/webgpu';
import {
  Fn, float, vec3, mix, smoothstep, positionLocal, normalize, dot, pow, max, mx_fractal_noise_float, uniform, clamp, vec2,
} from 'three/tsl';

export const SUN_DIR = new Vector3(0.45, 0.62, 0.35).normalize();
export const HAZE = new Color(0xbcd0dc);

/** Sky dome (gradient, sun, soft clouds), distant peaks, fog and lighting. Follows the camera. */
export class Sky {
  readonly group = new Group();
  readonly sun: DirectionalLight;
  readonly hemi: HemisphereLight;
  private dome: Mesh;
  private peaks: Mesh;
  private sunTarget = new Group();
  private time = uniform(0);
  private sunU = uniform(SUN_DIR.clone());
  private zenithU = uniform(new Color(0.16, 0.38, 0.76));
  private horizonU = uniform(HAZE.clone());
  private scene: Scene;
  private sunDir = SUN_DIR.clone();

  constructor(scene: Scene) {
    this.scene = scene;
    const sd = this.sunU;
    const time = this.time;
    const dome = new MeshBasicNodeMaterial({ side: BackSide, depthWrite: false, fog: false });
    dome.colorNode = Fn(() => {
      const d = normalize(positionLocal);
      const h = clamp(d.y, 0, 1);
      const zenith = this.zenithU;
      const horizon = this.horizonU;
      let col = mix(horizon, zenith, pow(h, 0.55));
      const s = max(dot(d, sd), 0);
      col = col.add(vec3(1.0, 0.86, 0.6).mul(pow(s, 24).mul(0.25)));
      col = col.add(vec3(1.0, 0.95, 0.85).mul(smoothstep(0.9993, 0.9997, s).mul(6)));
      // soft clouds from fractal noise on the dome, drifting slowly
      const uv = vec2(d.x, d.z).div(d.y.add(0.35)).mul(1.6).add(vec2(time.mul(0.004), 0));
      const n = mx_fractal_noise_float(vec3(uv.x, uv.y, 0.0), 4, 2.0, 0.5).mul(0.5).add(0.5);
      const cloud = smoothstep(0.52, 0.8, n).mul(smoothstep(0.02, 0.3, d.y)).mul(0.85);
      col = mix(col, vec3(1.0, 0.99, 0.96), cloud);
      return col;
    })();
    const dm = new Mesh(new SphereGeometry(1, 32, 16), dome);
    dm.scale.setScalar(2800);
    dm.renderOrder = -10;
    dm.frustumCulled = false;
    this.dome = dm;
    this.peaks = this.makePeaks();
    this.group.add(dm, this.peaks);

    scene.fog = new FogExp2(HAZE.getHex(), 0.00055);
    scene.background = HAZE.clone();

    this.hemi = new HemisphereLight(0xcfe3ff, 0x6a7a4a, 1.0);
    scene.add(this.hemi);
    this.sun = new DirectionalLight(0xfff0d8, 3.2);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    const c = this.sun.shadow.camera;
    c.left = -48; c.right = 48; c.top = 48; c.bottom = -48; c.near = 1; c.far = 220;
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.05;
    scene.add(this.sun, this.sunTarget);
    this.sun.target = this.sunTarget;
    scene.add(this.group);
  }

  private makePeaks(): Mesh {
    // ring of jagged ridges, built from a displaced cylinder wall with layered haze
    const seg = 160;
    const pos: number[] = [];
    const idx: number[] = [];
    const R = 2300;
    for (let i = 0; i <= seg; i++) {
      const a = (i / seg) * Math.PI * 2;
      const n = Math.sin(a * 3.1) * 0.5 + Math.sin(a * 7.7 + 1) * 0.3 + Math.sin(a * 17.3 + 2) * 0.15 + Math.sin(a * 41) * 0.05;
      const h = 160 + 380 * Math.max(0, n * 0.5 + 0.55);
      pos.push(Math.cos(a) * R, -400, Math.sin(a) * R, Math.cos(a) * R, h, Math.sin(a) * R);
    }
    for (let i = 0; i < seg; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    const g = new BufferGeometry();
    g.setAttribute('position', new BufferAttribute(new Float32Array(pos), 3));
    g.setIndex(idx);
    const m = new MeshBasicNodeMaterial({ side: 2, fog: false, depthWrite: false });
    m.colorNode = Fn(() => {
      const t = smoothstep(-400, 560, positionLocal.y);
      const base = vec3(0.45, 0.55, 0.68);
      const snow = vec3(0.93, 0.95, 0.98);
      const rock = mix(vec3(0.55, 0.62, 0.72), base, float(1).sub(t));
      return mix(rock, snow, smoothstep(0.62, 0.8, t));
    })();
    const mesh = new Mesh(g, m);
    mesh.frustumCulled = false;
    mesh.renderOrder = -9;
    return mesh;
  }

  /**
   * Time of day, 0 = late afternoon at the lodge, 1 = dusk at the finale (contract 6c): sun elevation about 28 degrees
   * falling to about 4, with sky, fog, light colour and intensity following. Returns the tone-mapping exposure to use.
   */
  setTimeOfDay(u: number): number {
    u = Math.max(0, Math.min(1, u));
    const el = (28 + (4 - 28) * u) * Math.PI / 180, az = 0.78;
    this.sunDir.set(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
    this.sunU.value.copy(this.sunDir);
    this.zenithU.value.setRGB(0.16 - 0.07 * u, 0.38 - 0.24 * u, 0.76 - 0.4 * u);
    this.horizonU.value.setRGB(HAZE.r + (0.9 - HAZE.r) * u, HAZE.g + (0.55 - HAZE.g) * u, HAZE.b + (0.45 - HAZE.b) * u);
    (this.scene.fog as FogExp2).color.copy(this.horizonU.value);
    (this.scene.background as Color).copy(this.horizonU.value);
    this.sun.color.setRGB(1, 0.94 - 0.42 * u, 0.85 - 0.62 * u);
    this.sun.intensity = 3.2 - 1.9 * u;
    this.hemi.intensity = 1 - 0.55 * u;
    return 0.95 - 0.12 * u;
  }

  /** Keep dome and shadow frustum attached to the action. */
  update(camera: Camera, focus: Vector3, dt: number): void {
    this.time.value += dt;
    this.dome.position.copy(camera.position);
    this.peaks.position.set(camera.position.x, camera.position.y - 330, camera.position.z);
    this.sunTarget.position.copy(focus);
    this.sun.position.copy(focus).addScaledVector(this.sunDir, 120);
  }
}
