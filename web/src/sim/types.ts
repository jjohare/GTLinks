/** Contract v1 types and pure decoders. Mirrors docs/CONTRACT.md sections 2, 4 and 6. */

export const NX = 161;
export const NZ = 641;
export const CELL = 4;
export const X0 = -320;
export const STATE_LEN = 36;

/** Named indices into the state() buffer. */
export const S = {
  px: 0, py: 1, pz: 2,
  qx: 3, qy: 4, qz: 5, qw: 6,
  vx: 7, vy: 8, vz: 9,
  wx: 10, wy: 11, wz: 12,
  wheel0: 13, // 4 wheels x (compression, spin, steer)
  phase: 25, damage: 26, runTime: 27, hole: 28, speed: 29,
  wheelsOnGround: 30, airtime: 31, appliedSteer: 32, wobble: 33, trick: 34, wreckedFor: 35,
} as const;

export enum Phase { Driving = 0, FinaleArmed = 1, FinaleAirborne = 2, Settling = 3, Wrecked = 4 }
export enum Surface { Rough = 0, Fairway = 1, Green = 2, Bunker = 3, Tee = 4, CartPath = 5, Rock = 6, Water = 7 }
export enum PropKind { Pine = 0, Broadleaf = 1, Spectator = 2, Flag = 3, TeeMarker = 4, Cart = 5, Sign = 6, Rock = 7 }
export enum EventKind {
  JumpStart = 1, Landing = 2, Impact = 3, PropHit = 4, HoleEntered = 5, Trick = 6,
  NearMiss = 7, FinaleStart = 8, Wrecked = 9, PartDetached = 10, Hiccup = 11,
}
export const TRICK_NAMES = ['Airtime', 'Barrel roll', 'Front flip', 'Back flip', 'Flat spin', 'Bunker blast', 'Green skid'];
export const PART_NAMES = ['bumper_front', 'bumper_rear', 'bonnet', 'mirror_l', 'mirror_r'];

export interface SimEvent { kind: EventKind; a: number; b: number; x: number; y: number; z: number }

export interface WheelState { compression: number; spin: number; steer: number }

export interface RenderState {
  pos: [number, number, number];
  quat: [number, number, number, number];
  vel: [number, number, number];
  angVel: [number, number, number];
  wheels: WheelState[];
  phase: Phase;
  damage: number;
  runTime: number;
  hole: number;
  speed: number;
  wheelsOnGround: number;
  airtime: number;
  appliedSteer: number;
  wobble: number;
  trick: number;
  wreckedFor: number;
}

/** Decode a state() buffer. Throws on a wrong length so a contract drift is loud. */
export function decodeState(f: ArrayLike<number>): RenderState {
  if (f.length !== STATE_LEN) throw new Error(`state() length ${f.length}, expected ${STATE_LEN}`);
  const wheels: WheelState[] = [];
  for (let i = 0; i < 4; i++) {
    const o = S.wheel0 + i * 3;
    wheels.push({ compression: f[o], spin: f[o + 1], steer: f[o + 2] });
  }
  return {
    pos: [f[S.px], f[S.py], f[S.pz]],
    quat: [f[S.qx], f[S.qy], f[S.qz], f[S.qw]],
    vel: [f[S.vx], f[S.vy], f[S.vz]],
    angVel: [f[S.wx], f[S.wy], f[S.wz]],
    wheels,
    phase: f[S.phase] as Phase,
    damage: f[S.damage], runTime: f[S.runTime], hole: f[S.hole], speed: f[S.speed],
    wheelsOnGround: f[S.wheelsOnGround], airtime: f[S.airtime], appliedSteer: f[S.appliedSteer],
    wobble: f[S.wobble], trick: f[S.trick], wreckedFor: f[S.wreckedFor],
  };
}

/** Decode a flat drain_events() buffer: [kind, a, b, x, y, z] * n. */
export function decodeEvents(f: ArrayLike<number>): SimEvent[] {
  const out: SimEvent[] = [];
  for (let i = 0; i + 5 < f.length; i += 6) {
    out.push({ kind: f[i] as EventKind, a: f[i + 1], b: f[i + 2], x: f[i + 3], y: f[i + 4], z: f[i + 5] });
  }
  return out;
}

export interface CourseHole {
  index: number; par: number; tee: [number, number, number]; green: [number, number, number];
  green_radius: number; centreline: [number, number, number][]; fairway_half_width: number;
}
export interface CourseProp { kind: PropKind; pos: [number, number, number]; yaw: number; scale: number }
export interface CourseRamp { pos: [number, number, number]; yaw: number; length: number; width: number; height: number }
export interface Course {
  seed: number;
  start: { pos: [number, number, number]; yaw: number };
  lodge: { pos: [number, number, number]; yaw: number };
  holes: CourseHole[];
  props: CourseProp[];
  ramps: CourseRamp[];
  finale: { pos: [number, number, number]; radius: number };
}

/** The wasm Game class, as the front end consumes it. */
export interface Game {
  course_json(): string;
  heightfield(): Float32Array;
  surface_map(): Uint8Array;
  height_at(x: number, z: number): number;
  step(dt: number, steer: number, throttle: number, brake: number, handbrake: boolean): void;
  state(): Float32Array;
  drain_events(): Float32Array;
  free?(): void;
}
export type GameFactory = (seed: number, carId: number, steins: number) => Game;

export interface CarSpec {
  id: number; key: string; name: string; length: number; width: number; height: number;
  wheelbase: number; track: number; wheel_radius: number; wheel_width: number;
  ground_clearance: number; mass: number; cog_height: number; roof_y: number; paint: string; character: string;
}
