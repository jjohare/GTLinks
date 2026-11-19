import { Scene, Vector3, Quaternion, Object3D } from 'three/webgpu';
import { createRenderer, fitRenderer, NoGpuError } from '../render/renderer';
import type { GpuContext } from '../render/renderer';
import { Sky } from '../render/sky';
import { CameraRig } from '../render/cameras';
import { Particles } from '../render/particles';
import { preloadAll, CARS } from '../render/assets';
import { Terrain } from '../world/terrain';
import { Props } from '../world/props';
import { PursuitView } from '../world/pursuit';
import type { PursuitInfo } from '../world/pursuit';
import { Lodge, derivedStats } from '../world/lodge';
import { Hud } from '../ui/hud';
import { AudioEngine } from '../audio/audio';
import { InputManager } from '../input/input';
import type { Intent } from '../input/mapping';
import { loadSim } from '../sim';
import type { SimBackend } from '../sim';
import { decodeEvents, decodeState, EventKind, Phase, TRICK_NAMES, NX, NZ, CELL, X0, STATE_LEN } from '../sim/types';
import type { Course, Game, RenderState, SimEvent } from '../sim/types';
import { nextScreen, WRECK } from './flow';
import type { Screen } from './flow';

/** One lodge-to-wreck cycle's worth of world objects. Everything here is disposed on restart. */
interface Run {
  seed: number;
  preview: Game;
  game: Game | null;
  course: Course;
  surf: Uint8Array;
  terrain: Terrain;
  props: Props;
  pursuit: PursuitView;
  lodge: Lodge;
  parkedAt: number | null;
  shedCount: number;
  blend: number;
  blendFrom: { p: Vector3; q: Quaternion };
  lastPhase: Phase;
  state: RenderState | null;
  raw: Float32Array | null;
  hiccupAt: number;
  wreckHandled: boolean;
  fadeStarted: boolean;
  restartAt: number;
  steam: number;
  surface: number;
  solids: { x: number; z: number; r: number; h: number }[];
}

/** Top-level controller: screen flow, per-frame orchestration, lifecycle and disposal. */
export class App {
  private canvas = document.getElementById('view') as HTMLCanvasElement;
  private ghost = document.createElement('canvas');
  private gctx = this.ghost.getContext('2d');
  private gpu!: GpuContext;
  private scene = new Scene();
  private rig = new CameraRig();
  private sky!: Sky;
  private fx = new Particles();
  private hud!: Hud;
  private audio = new AudioEngine();
  private input!: InputManager;
  private sim!: SimBackend;
  private run: Run | null = null;
  private screen: Screen = 'loading';
  private building = false;
  private last = 0;
  private paused = false;
  private ghostOff = false;
  private eventCounts: Record<string, number> = {};
  private overrideIntent: Intent | null = null;
  private lastIntent: Intent = { steer: 0, throttle: 0, brake: 0, handbrake: false };
  private frameTimes: number[] = [];
  private seedCounter = (Date.now() >>> 0) % 100000;
  private tmpV = new Vector3();
  private tmpV2 = new Vector3();
  private tmpQ = new Quaternion();
  private t = 0;
  private resizeObs: ResizeObserver | null = null;
  private rawDt = 0.016;
  private tod = 0;
  private pursuitInfo: PursuitInfo | null = null;

  async start(): Promise<void> {
    const ui = document.getElementById('ui') as HTMLElement;
    this.hud = new Hud(ui, {
      prev: () => this.lodgeAction((l) => l.prev()), next: () => this.lodgeAction((l) => l.next()),
      add: () => this.lodgeAction((l) => l.addOne()), remove: () => this.lodgeAction((l) => l.removeOne()),
      go: () => this.go(), mute: () => this.toggleMute(),
    });
    this.hud.setMuted(this.audio.muted);
    this.input = new InputManager(this.hud.isTouch ? this.hud.touchEls : null);
    try {
      this.hud.loadProgress(0.05, 'Starting renderer');
      this.gpu = await createRenderer(this.canvas);
    } catch (e) {
      this.hud.fail(e instanceof NoGpuError ? e.message : `Renderer failed: ${(e as Error).message}`);
      return;
    }
    this.hud.setBackend(this.gpu.backend === 'webgpu' ? 'WebGPU' : 'WebGL2');
    this.hud.loadProgress(0.2, 'Loading simulation');
    try { this.sim = await loadSim(); } catch (e) { this.hud.fail(`Simulation failed to load: ${(e as Error).message}`); return; }
    this.sky = new Sky(this.scene);
    this.scene.add(this.fx.mesh);
    this.hud.loadProgress(0.4, 'Loading models');
    await preloadAll();
    this.hud.loadProgress(0.7, 'Building the mountain');
    this.ghost.id = 'ghost';
    this.canvas.after(this.ghost);
    this.onResize();
    this.resizeObs = new ResizeObserver(() => this.onResize());
    this.resizeObs.observe(document.body);
    window.addEventListener('resize', () => this.onResize());
    document.addEventListener('visibilitychange', () => this.onVisibility());
    const unlock = () => this.audio.unlock();
    window.addEventListener('pointerdown', unlock, { passive: true });
    window.addEventListener('keydown', unlock);
    this.installDebug();
    await this.newRun(this.nextSeed());
    this.hud.loadProgress(1, 'Ready');
    this.screen = nextScreen(this.screen, { t: 'ready' });
    this.hud.hideLoading();
    this.showLodge();
    this.hud.fade(false);
    // render once explicitly so `renderer.info` is populated before the loop is scheduled
    this.gpu.renderer.setAnimationLoop((time) => this.frame(time));
  }

  private nextSeed(): number { this.seedCounter = (this.seedCounter * 1664525 + 1013904223) >>> 0; return this.seedCounter % 1000000; }

  // ------------------------------------------------------------------ lifecycle

  /** Dispose the current run and build a fresh one for `seed`. */
  private async newRun(seed: number): Promise<void> {
    if (this.building) return;
    this.building = true;
    try {
      this.disposeRun();
      const preview = this.sim.create(seed, 0, 10);
      const course = JSON.parse(preview.course_json()) as Course;
      const heights = preview.heightfield();
      const surf = preview.surface_map();
      if (heights.length !== NX * NZ || surf.length !== NX * NZ) throw new Error('heightfield size does not match the contract grid');
      const terrain = new Terrain(heights, surf, (x, z) => preview.height_at(x, z));
      this.scene.add(terrain.group);
      const props = await Props.create(course, preview);
      this.scene.add(props.group);
      const pursuit = await PursuitView.create();
      this.scene.add(pursuit.group);
      const lodge = await Lodge.create(course, preview, this.rig.camera, this.canvas, this.fx, {
        onCount: (n, can) => this.hud.setCount(n, can, this.run?.lodge.load.severity ?? 0),
        onSelect: (i) => this.hud.setCar(CARS[i], derivedStats(CARS[i], CARS), i, CARS.length),
        onClink: (s) => this.audio.clink(s),
        onTip: () => { this.audio.splash(); this.audio.clink(0.7); },
        onFull: () => { this.hud.toast('The car is full. That is quite enough.'); },
      });
      this.scene.add(lodge.group);
      this.run = {
        seed, preview, game: null, course, surf, terrain, props, pursuit, lodge, parkedAt: null, shedCount: 0, blend: 1,
        blendFrom: { p: new Vector3(), q: new Quaternion() }, lastPhase: Phase.Driving, state: null, raw: null,
        hiccupAt: 0, wreckHandled: false, fadeStarted: false, restartAt: 0, steam: 0, surface: 1, solids: [],
      };
      // the lodge hooks fire during construction before `run` exists; refresh the readouts now
      this.hud.setCount(0, false, 0);
      this.hud.setCar(CARS[lodge.selected], derivedStats(CARS[lodge.selected], CARS), lodge.selected, CARS.length);
      this.rig.cut('lodge');
      this.rig.startIntro(lodge.introPos, lodge.introLook);
      this.fx.clear();
    } finally {
      this.building = false;
    }
  }

  private disposeRun(): void {
    const r = this.run;
    if (!r) return;
    r.lodge.dispose();
    r.props.dispose();
    r.pursuit.dispose();
    r.terrain.dispose();
    this.scene.remove(r.terrain.group, r.props.group, r.lodge.group);
    r.game?.free?.();
    r.preview.free?.();
    this.run = null;
  }

  private showLodge(): void {
    this.screen = 'lodge';
    this.hud.screen('lodge');
    if (this.run) this.run.lodge.enabled = true;
    this.audio.silence();
    this.audio.silencePursuit();
    this.hud.pursuit(0);
  }

  /** Restart from the lodge with a new seed; `quick` shortens the fade (the R key). */
  async restart(quick: boolean): Promise<void> {
    if (this.screen === 'loading' || this.building) return;
    this.screen = nextScreen(this.screen, { t: 'restart' });
    this.hud.fade(true, quick);
    await new Promise((r) => setTimeout(r, quick ? 380 : 120));
    this.hud.hideLower();
    this.hud.clearTransient();
    await this.newRun(this.nextSeed());
    this.showLodge();
    await new Promise((r) => setTimeout(r, 150));
    this.hud.fade(false, quick);
  }

  private lodgeAction(fn: (l: Lodge) => unknown): void {
    if (this.screen !== 'lodge' || !this.run) return;
    fn(this.run.lodge);
  }

  private toggleMute(): void { this.audio.unlock(); this.hud.setMuted(this.audio.toggleMute()); }

  /** Begin the descent with whatever is on the car. */
  private go(): void {
    const r = this.run;
    if (!r || this.screen !== 'lodge' || !r.lodge.load.canGo) return;
    this.startGame(r, r.lodge.selected, r.lodge.load.count);
  }

  private startGame(r: Run, carId: number, steins: number): void {
    r.game = this.sim.create(r.seed, carId, steins);
    r.props.setGame(r.game);
    r.lodge.setGame(r.game);
    r.state = null;
    const car = r.lodge.car;
    r.blend = 0;
    r.blendFrom.p.copy(car.root.position);
    r.blendFrom.q.copy(car.root.quaternion);
    r.lastPhase = Phase.Driving;
    r.wreckHandled = false; r.fadeStarted = false;
    r.lodge.enabled = false;
    this.screen = nextScreen(this.screen, { t: 'go' });
    this.hud.screen('drive');
    this.rig.cut('chase');
    this.rig.setHeading(0, 1);
    this.audio.unlock();
    this.audio.chime();
  }

  // ------------------------------------------------------------------ per frame

  private frame(time: number): void {
    if (this.paused || !this.run) return;
    const now = time / 1000;
    const raw = this.last ? Math.max(0, now - this.last) : 0.016;
    const dt = Math.min(0.1, raw);
    this.rawDt = Math.min(0.3, raw);
    this.last = now;
    this.t += dt;
    this.recordFrame(dt);
    const r = this.run;

    for (const code of this.input.takePressed()) this.onKey(code);
    if (this.input.padStart() && this.screen === 'lodge') this.go();

    switch (this.screen) {
      case 'lodge': this.tickLodge(r, dt); break;
      case 'descent': this.tickDrive(r, dt); break;
      case 'wreck': this.tickWreck(r, dt); break;
      default: break;
    }
    r.props.update(dt);
    this.fx.update(dt);
    const focus = this.screen === 'lodge' ? r.lodge.slotPos[r.lodge.selected] : this.tmpV.set(r.state?.pos[0] ?? 0, r.state?.pos[1] ?? 0, r.state?.pos[2] ?? 0);
    if (this.screen === 'lodge') this.timeOfDay(dt, 0);
    this.sky.update(this.rig.camera, focus, dt);
    this.rig.applyPin();
    this.gpu.renderer.render(this.scene, this.rig.camera);
    this.drawGhost(r);
  }

  private onKey(code: string): void {
    if (code === 'KeyM') { this.toggleMute(); return; }
    if (code === 'KeyR') { void this.restart(true); return; }
    if (this.screen !== 'lodge' || !this.run) return;
    const l = this.run.lodge;
    switch (code) {
      case 'ArrowLeft': case 'KeyA': l.prev(); break;
      case 'ArrowRight': case 'KeyD': l.next(); break;
      case 'ArrowUp': case 'Equal': case 'NumpadAdd': case 'KeyW': l.addOne(); break;
      case 'ArrowDown': case 'Minus': case 'NumpadSubtract': case 'KeyS': l.removeOne(); break;
      case 'Enter': this.go(); break;
      default: break;
    }
  }

  /** Advance the simulation by the real frame time in slices of at most 0.05 s, so a slow frame does not slow the game. */
  private stepSim(game: Game, steer: number, throttle: number, brake: number, handbrake: boolean): void {
    let rem = this.rawDt;
    for (let i = 0; i < 6 && rem > 1e-4; i++) { const h = Math.min(0.05, rem); game.step(h, steer, throttle, brake, handbrake); rem -= h; }
  }

  /** Pose the patrol cars and helicopter, drive their audio and the chase glow. */
  private tickPursuit(r: Run, dt: number, game: Game): void {
    const info = r.pursuit.update(dt, game, this.fx);
    this.pursuitInfo = info;
    const cam = this.rig.camera;
    const right = this.tmpV2.set(1, 0, 0).applyQuaternion(cam.quaternion);
    this.audio.spatial(
      { x: cam.position.x, y: cam.position.y, z: cam.position.z, rx: right.x, rz: right.z }, dt,
      info.units.map((u) => ({ x: u.pos.x, y: u.pos.y, z: u.pos.z, vx: u.vel.x, vy: u.vel.y, vz: u.vel.z, on: u.on })),
      { x: info.heli.pos.x, y: info.heli.pos.y, z: info.heli.pos.z, vx: info.heli.vel.x, vy: info.heli.vel.y, vz: info.heli.vel.z, on: info.heli.on },
    );
    this.hud.pursuit(info.pursuing > 0 && this.screen === 'descent' ? Math.max(0.3, Math.min(1, 1 - info.nearest / 70)) : 0);
  }

  private tickLodge(r: Run, dt: number): void {
    r.lodge.update(dt, 0, false);
    const car = r.lodge.car;
    this.rig.updateLodge(dt, r.lodge.camHome, r.lodge.slotPos[r.lodge.selected], r.lodge.tablePos, r.lodge.rowCentre, r.preview);
    car.setEyes(r.lodge.load.count, this.t, false);
    for (const c of r.lodge.cars) if (c !== car) c.setEyes(0, this.t + 3, false);
  }

  private tickDrive(r: Run, dt: number): void {
    const game = r.game!;
    const intent = this.overrideIntent ?? this.input.intent();
    this.lastIntent = intent;
    this.stepSim(game, intent.steer, intent.throttle, intent.brake, intent.handbrake);
    const raw = game.state();
    if (raw.length < STATE_LEN) throw new Error('state() length mismatch');
    r.raw = raw;
    const st = decodeState(raw);
    r.state = st;
    const events = decodeEvents(game.drain_events());
    const car = r.lodge.car;
    const pos = this.tmpV.set(st.pos[0], st.pos[1], st.pos[2]);
    const vel = this.tmpV2.set(st.vel[0], st.vel[1], st.vel[2]);
    this.posePlayerCar(r, car.root, st, dt);
    car.applyState(st);
    car.tickLoose(dt, game);
    const n = r.lodge.load.count;
    car.tickSprings(dt, n, st.wobble);
    car.setEyes(n, this.t, st.phase === Phase.Wrecked);
    r.lodge.update(dt, st.wobble, true);
    // the parked cars are ~35k triangles each: stop drawing them once the player is well clear of the apron
    const away = Math.hypot(st.pos[0] - r.course.start.pos[0], st.pos[2] - r.course.start.pos[2]);
    for (const c of r.lodge.cars) if (c !== car) { c.root.visible = away < 60; if (c.root.visible) c.tickSprings(dt, 0, 0); }
    for (const e of events) this.onEvent(r, e, pos, vel);

    if (st.phase !== r.lastPhase) {
      if (st.phase === Phase.FinaleArmed) {
        this.hud.notice('The car has got away', 'You are no longer in charge');
        this.audio.alarm();
      }
      r.lastPhase = st.phase;
    }
    this.groundFx(r, st, car, dt);
    this.tickPursuit(r, dt, game);
    this.timeOfDay(dt, st.hole / 8);
    this.hud.drive({
      kph: st.speed * 3.6, hole: Math.min(8, Math.max(0, Math.round(st.hole))),
      par: r.course.holes[Math.min(8, Math.max(0, Math.round(st.hole)))]?.par ?? 4, steins: n,
      applied: st.appliedSteer, input: st.phase === Phase.Driving ? intent.steer : 0,
    });
    r.surface = this.surfaceAt(r.surf, st.pos[0], st.pos[2]);
    this.audio.setSurface(r.surface);
    this.audio.drive(true, st.speed, st.phase === Phase.Driving ? intent.throttle : 0.5, st.wheelsOnGround, Math.abs(st.appliedSteer) * Math.min(1, Math.abs(st.speed) / 30));
    this.rig.updateChase(dt, st, game, n);

    if (st.phase === Phase.Wrecked) this.enterWreck(r, st);
  }

  /** Place the player's car, blending from the lodge parking slot for the first moments. */
  private posePlayerCar(r: Run, root: Object3D, st: RenderState, dt: number): void {
    this.tmpQ.set(st.quat[0], st.quat[1], st.quat[2], st.quat[3]);
    if (r.blend < 1) {
      r.blend = Math.min(1, r.blend + dt / 0.9);
      const e = r.blend * r.blend * (3 - 2 * r.blend);
      root.position.set(st.pos[0], st.pos[1], st.pos[2]).lerp(r.blendFrom.p, 1 - e);
      root.position.y += Math.sin(r.blend * Math.PI) * 0.15;
      root.quaternion.copy(r.blendFrom.q).slerp(this.tmpQ, e);
    } else {
      root.position.set(st.pos[0], st.pos[1], st.pos[2]);
      root.quaternion.copy(this.tmpQ);
    }
  }

  private enterWreck(r: Run, st: RenderState): void {
    if (r.wreckHandled) return;
    r.wreckHandled = true;
    this.screen = nextScreen(this.screen, { t: 'phase', phase: st.phase });
    this.hud.screen('wreck');
    this.rig.cut('drone');
    this.audio.thump(0.6);
    // whatever is still on the roof (the early-rollover path never sees FinaleStart) spills off the upturned car
    r.lodge.shed(15, new Vector3(), 0.5);
    this.hud.clearTransient();
    r.restartAt = 0;
    r.solids = r.props.solidsNear(st.pos[0], st.pos[2], 220);
  }

  private tickWreck(r: Run, dt: number): void {
    const game = r.game!;
    this.stepSim(game, 0, 0, 0, false);
    r.raw = game.state();
    const st = decodeState(r.raw);
    r.state = st;
    const events = decodeEvents(game.drain_events());
    const car = r.lodge.car;
    const pos = this.tmpV.set(st.pos[0], st.pos[1], st.pos[2]);
    this.posePlayerCar(r, car.root, st, dt);
    car.applyState(st);
    car.tickLoose(dt, game);
    car.tickSprings(dt, 0, 0);
    car.setEyes(r.lodge.load.count, this.t, true);
    r.lodge.update(dt, 0, true);
    for (const e of events) this.onEvent(r, e, pos, this.tmpV2.set(0, 0, 0));
    const t = st.wreckedFor;
    // the pull-out waits for PoliceParked (or 16 s after Wrecked, whichever comes first)
    const orbit = r.parkedAt !== null ? Math.min(16, Math.max(6, r.parkedAt + 0.8)) : 16;
    const total = orbit + WRECK.pull;
    this.tickPursuit(r, dt, game);
    this.timeOfDay(dt, 1);
    if (t > 1.2 && t < orbit) this.hud.lowerThird(CARS[r.lodge.selected].name, r.lodge.load.count, st.trick);
    else if (t >= orbit) this.hud.hideLower();
    this.audio.drive(true, 0, 0, 4, 0);
    this.audio.silence();
    // wisp of steam from the bonnet area
    r.steam -= dt;
    if (r.steam <= 0 && st.damage > 0.01) {
      r.steam = 0.09;
      const b = car.root.getObjectByName('bonnet');
      const sp = b ? b.getWorldPosition(this.tmpV2) : this.tmpV2.copy(pos);
      this.fx.emit('steam', sp, 1, new Vector3(0, 0.6, 0), 0.5, 1);
    }
    this.rig.updateDrone(dt, t, pos, game, orbit, WRECK.pull, r.solids, (this.pursuitInfo?.units.some((u) => u.on) ?? false));
    if (t >= total - 0.4 && !r.fadeStarted) { r.fadeStarted = true; this.hud.fade(true); r.restartAt = this.t + WRECK.fade + WRECK.hold; }
    if (r.fadeStarted && this.t >= r.restartAt) {
      void this.finishWreck();
    }
  }

  private async finishWreck(): Promise<void> {
    this.screen = 'fade';
    this.hud.hideLower();
    await this.newRun(this.nextSeed());
    this.screen = nextScreen(this.screen, { t: 'faded' });
    this.showLodge();
    await new Promise((r) => setTimeout(r, 200));
    this.hud.fade(false);
  }

  // ------------------------------------------------------------------ events and effects

  private onEvent(r: Run, e: SimEvent, pos: Vector3, vel: Vector3): void {
    const car = r.lodge.car;
    const at = new Vector3(e.x, e.y, e.z);
    const evName = EventKind[e.kind] ?? String(e.kind);
    this.eventCounts[evName] = (this.eventCounts[evName] ?? 0) + 1;
    switch (e.kind) {
      case EventKind.JumpStart:
        this.fx.emit('dust', at, 6, new Vector3(0, 1, 0), 1.2);
        break;
      case EventKind.Landing: {
        const s = Math.min(1, e.a / 22);
        this.audio.thump(s);
        this.rig.kick(0.25 + s * 0.6);
        this.fx.emit(r.surface === 3 ? 'sand' : 'dust', at, 12 + Math.round(s * 20), new Vector3(0, 1.5, 0), 3);
        if (r.surface !== 3) this.fx.emit('grass', at, 6 + Math.round(s * 10), new Vector3(0, 2, 0), 3);
        this.shedSome(r, e.a > 14 ? 1 : 0, vel, 1);
        this.fx.emit('foam', at.clone().setY(at.y + 2), 6, new Vector3(0, 1, 0), 2);
        break;
      }
      case EventKind.Impact: {
        this.audio.thump(0.4 + e.a * 0.6);
        this.rig.kick(0.3 + e.a * 0.8);
        this.fx.emit('dust', at, 10 + Math.round(e.a * 14), new Vector3(0, 1, 0), 3);
        this.fx.emit('spark', at, 4, new Vector3(0, 1, 0), 3);
        this.shedSome(r, e.a > 0.4 || e.b >= 100 ? Math.ceil(e.a * 2) : 0, vel, 1 + e.a);
        break;
      }
      case EventKind.PropHit:
        r.props.onEvent(e, pos, vel);
        this.audio.thump(0.25);
        this.fx.emit('grass', at, 6, new Vector3(0, 2, 0), 3);
        break;
      case EventKind.NearMiss:
        r.props.onEvent(e, pos, vel);
        this.audio.gasp();
        this.hud.callout('Fore!', 0);
        break;
      case EventKind.HoleEntered:
        if (e.a > 0) this.hud.callout(`Hole ${Math.round(e.a) + 1}`, 0);
        break;
      case EventKind.Trick: {
        const name = TRICK_NAMES[Math.round(e.a)] ?? 'Trick';
        this.hud.callout(name, e.b);
        this.audio.chime();
        if (Math.round(e.a) === 5) this.fx.emit('sand', at, 30, new Vector3(0, 3, 0), 4);
        break;
      }
      case EventKind.FinaleStart:
        r.lodge.shed(15, vel, 1.4);
        if (Math.round(e.b) === 1) void r.props.spawnKicker(e.x, e.y, e.z, e.a);
        break;
      case EventKind.Wrecked:
        break;
      case EventKind.PoliceJoined:
        this.hud.callout(`Patrol ${Math.round(e.a) + 1} is on your tail`, 0);
        this.audio.alarm();
        break;
      case EventKind.HeliJoined:
        this.hud.callout('Air unit overhead', 0);
        break;
      case EventKind.PoliceParked:
        r.parkedAt = r.state?.wreckedFor ?? 0;
        break;
      case EventKind.PartDetached:
        car.detach(Math.round(e.a), this.scene, vel);
        this.audio.thump(0.3);
        break;
      case EventKind.Hiccup: {
        car.hiccup(e.a);
        this.audio.hiccup();
        this.rig.kick(0.08 + e.a * 0.15);
        const p = this.tmpV.copy(pos).add(new Vector3(0, 2.4, 0)).project(this.rig.camera);
        this.hud.hiccup((p.x * 0.5 + 0.5) * innerWidth, (-p.y * 0.5 + 0.5) * innerHeight);
        break;
      }
      default: break;
    }
  }

  /** Shed a few steins, but keep at least half on the roof until the finale so the pile stays visible all the way down. */
  private shedSome(r: Run, n: number, vel: Vector3, power: number): void {
    const keep = Math.ceil(r.lodge.load.count / 2);
    const allowed = Math.max(0, r.lodge.pileCount - keep);
    const k = Math.min(n, allowed);
    if (k > 0) { r.lodge.shed(k, vel, power); r.shedCount += k; }
  }

  /** Late afternoon at the lodge to dusk at the finale (contract 6c), eased so it never jumps. */
  private timeOfDay(dt: number, target: number): void {
    this.tod += (Math.max(0, Math.min(1, target)) - this.tod) * Math.min(1, dt * 0.6);
    this.gpu.renderer.toneMappingExposure = this.sky.setTimeOfDay(this.tod);
  }

  private surfaceAt(surf: Uint8Array, x: number, z: number): number {
    const ix = Math.max(0, Math.min(NX - 1, Math.round((x - X0) / CELL)));
    const iz = Math.max(0, Math.min(NZ - 1, Math.round(z / CELL)));
    return surf[iz * NX + ix];
  }

  /** Dust, sand and divots from the wheels that are on the ground. */
  private groundFx(r: Run, st: RenderState, car: { wheels: Object3D[] }, dt: number): void {
    if (st.phase >= Phase.Settling || st.wheelsOnGround < 1) return;
    const spd = Math.abs(st.speed);
    if (spd < 4) return;
    const surf = r.surface;
    const rate = Math.min(1, spd / 40) * (surf === 3 ? 2.4 : surf === 0 ? 1.0 : surf === 5 ? 1.2 : 0.35);
    for (let i = 0; i < 4; i++) {
      if (Math.random() > rate * dt * 8) continue;
      const w = car.wheels[i].getWorldPosition(this.tmpV2);
      w.y -= 0.3;
      const back = new Vector3(-st.vel[0], 0.5, -st.vel[2]).multiplyScalar(0.1);
      if (surf === 3) this.fx.emit('sand', w, 3, back, 2.4);
      else this.fx.emit('dust', w, 1, back.multiplyScalar(0.3), 0.8);
      if (surf !== 3 && surf !== 5 && spd > 14 && Math.random() < 0.15) this.fx.emit('grass', w, 2, back, 2.2);
    }
  }

  // ------------------------------------------------------------------ housekeeping

  private onResize(): void {
    const w = Math.max(1, window.innerWidth), h = Math.max(1, window.innerHeight);
    fitRenderer(this.gpu.renderer, w, h);
    this.rig.resize(w, h);
    this.ghost.width = Math.round(w / 2); this.ghost.height = Math.round(h / 2);
  }

  private onVisibility(): void {
    this.paused = document.hidden;
    this.last = 0;
    if (document.hidden) this.audio.silence();
  }

  /** Slight double vision: a faded, offset copy of the frame, scaled by loaded steins and wobble. */
  private drawGhost(r: Run): void {
    const g = this.gctx;
    if (!g) return;
    const n = r.lodge.load.count;
    const st = r.state;
    const on = !this.ghostOff && this.screen === 'descent' && st && st.phase === Phase.Driving && n >= 10;
    if (!on) { if (this.ghost.style.opacity !== '0') { this.ghost.style.opacity = '0'; g.clearRect(0, 0, this.ghost.width, this.ghost.height); } return; }
    const strength = ((n - 8) / 7) * (0.3 + 0.7 * st.wobble) * 0.6;
    try {
      g.clearRect(0, 0, this.ghost.width, this.ghost.height);
      const off = (4 + 16 * st.wobble) * Math.sin(this.t * 1.3) * (n / 15);
      g.drawImage(this.canvas, off / 2, Math.sin(this.t * 0.9) * 2, this.ghost.width, this.ghost.height);
      this.ghost.style.opacity = String(Math.min(0.5, strength));
    } catch {
      this.gctx?.clearRect(0, 0, this.ghost.width, this.ghost.height);
    }
  }

  private recordFrame(dt: number): void {
    this.frameTimes.push(dt * 1000);
    if (this.frameTimes.length > 600) this.frameTimes.shift();
  }

  // ------------------------------------------------------------------ test hooks

  private installDebug(): void {
    const self = this;
    const api = {
      get phase(): number { return self.run?.state && self.screen !== 'lodge' ? self.run.state.phase : -1; },
      backend: this.gpu.backend as string,
      state(): Float32Array | null { return self.run?.raw ? new Float32Array(self.run.raw) : null; },
      async debugStart(carId: number, steins: number, seed: number): Promise<void> {
        await self.debugStart(carId, steins, seed);
      },
    };
    Object.defineProperty(window, '__gtlinks', { value: api, configurable: true });
    // Separate, richer hooks for the automated walkthrough (screen coordinates of draggable things, timing, leak counters).
    const dbg = {
      screen: () => self.screen,
      steins: () => self.run?.lodge.load.count ?? 0,
      steinScreen: (id: number) => self.run ? self.project(self.run.lodge.steinObjects[id].obj.getWorldPosition(new Vector3())) : null,
      carScreen: (i: number) => self.run ? self.project(self.run.lodge.cars[i].root.getWorldPosition(new Vector3()).add(new Vector3(0, 1.0, 0))) : null,
      selected: () => self.run?.lodge.selected ?? -1,
      roofScreen: () => self.run ? self.project(self.run.lodge.car.anchor.getWorldPosition(new Vector3()).add(new Vector3(0, 0.3, 0))) : null,
      info: () => { const i = self.gpu.renderer.info; return { geometries: i.memory.geometries, textures: i.memory.textures, programs: (i as unknown as { programs?: unknown[] }).programs?.length ?? null, calls: i.render.drawCalls, triangles: i.render.triangles }; },
      toggle: (name: string, on: boolean) => { if (name === 'shadow') self.sky.sun.castShadow = on; if (name === 'terrain' && self.run) self.run.terrain.group.visible = on; if (name === 'props' && self.run) self.run.props.group.visible = on; if (name === 'fx') self.fx.mesh.visible = on; if (name === 'lodge' && self.run) self.run.lodge.group.visible = on; if (name === 'ghost') self.ghostOff = !on; if (name === 'sky') self.sky.group.visible = on;  },
      recent: () => { const a = self.frameTimes.slice(-60); return a.reduce((p, c) => p + c, 0) / Math.max(1, a.length); },
      frameStats: () => { const a = [...self.frameTimes].sort((x, y) => x - y); return a.length ? { n: a.length, mean: a.reduce((p, c) => p + c, 0) / a.length, p50: a[Math.floor(a.length * 0.5)], p95: a[Math.floor(a.length * 0.95)], max: a[a.length - 1] } : null; },
      setIntent: (i: Intent | null) => { self.overrideIntent = i; },
      restart: () => self.restart(true),
      go: () => self.go(),
      seed: () => self.run?.seed ?? -1,
      eventCounts: () => ({ ...self.eventCounts }),
      course: () => { const c = self.run?.course; return c ? { start: c.start, lodge: c.lodge, finale: c.finale, hole0: { tee: c.holes[0].tee, green: c.holes[0].green, cl: c.holes[0].centreline.slice(0, 4) }, props: c.props.length, ramps: c.ramps.slice(0, 2) } : null; },
      animatingProps: () => self.run?.props.animating ?? 0,
      heightAt: (x: number, z: number) => (self.run?.game ?? self.run?.preview)?.height_at(x, z) ?? null,
      pin: (p: number[] | null, l?: number[], fov = 50) => { self.rig.pinned = p && l ? { pos: new Vector3(...p), look: new Vector3(...l), fov } : null; },
      camera: () => { const c = self.rig.camera; const d = c.getWorldDirection(new Vector3()); return { pos: c.position.toArray(), dir: d.toArray(), fov: c.fov, aspect: c.aspect, table: self.run?.lodge.tablePos.toArray(), home: self.run?.lodge.camHome.toArray(), lodge: self.run?.course.lodge.pos, start: self.run?.course.start.pos }; },
      events: () => self.lastIntent,
    };
    Object.defineProperty(window, '__gtlinksDebug', { value: dbg, configurable: true });
  }

  private project(p: Vector3): { x: number; y: number } {
    p.project(this.rig.camera);
    const r = this.canvas.getBoundingClientRect();
    return { x: r.left + (p.x * 0.5 + 0.5) * r.width, y: r.top + (-p.y * 0.5 + 0.5) * r.height };
  }

  private async debugStart(carId: number, steins: number, seed: number): Promise<void> {
    while (this.building || this.screen === 'loading') await new Promise((r) => setTimeout(r, 30));
    if (!this.run || this.run.seed !== seed || this.screen !== 'lodge' || this.run.game) {
      this.screen = 'fade';
      await this.newRun(seed);
      this.showLodge();
    }
    const r = this.run!;
    r.lodge.select(carId);
    r.lodge.fillInstant(Math.max(10, Math.min(15, steins)));
    this.hud.fade(false, true);
    this.startGame(r, carId, Math.max(10, Math.min(15, steins)));
  }
}
