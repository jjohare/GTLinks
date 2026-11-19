/** Raw input mapping: keyboard, gamepad and touch to contract intent (steer +1 = left). */
export interface Intent { steer: number; throttle: number; brake: number; handbrake: boolean }
export const NEUTRAL: Intent = { steer: 0, throttle: 0, brake: 0, handbrake: false };

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

export function keyboardIntent(down: ReadonlySet<string>): Intent {
  const left = down.has('KeyA') || down.has('ArrowLeft');
  const right = down.has('KeyD') || down.has('ArrowRight');
  const up = down.has('KeyW') || down.has('ArrowUp');
  const back = down.has('KeyS') || down.has('ArrowDown');
  return {
    steer: (left ? 1 : 0) - (right ? 1 : 0),
    throttle: up ? 1 : 0,
    brake: back ? 1 : 0,
    handbrake: down.has('Space'),
  };
}

export function applyDeadzone(v: number, dz = 0.12): number {
  const a = Math.abs(v);
  if (a <= dz) return 0;
  return Math.sign(v) * (a - dz) / (1 - dz);
}

/** Standard-mapping gamepad: left stick X steers (stick left = -1 = steer left = +1). */
export function gamepadIntent(axes: ArrayLike<number>, buttons: ArrayLike<{ value: number; pressed: boolean }>): Intent {
  const rt = buttons[7]?.value ?? 0;
  const lt = buttons[6]?.value ?? 0;
  const a = buttons[0]?.pressed ?? false; // A: throttle fallback
  const x = buttons[2]?.pressed ?? false; // X / square: handbrake
  return {
    steer: clamp(0 - applyDeadzone(axes[0] ?? 0), -1, 1),
    throttle: clamp(Math.max(rt, a ? 1 : 0), 0, 1),
    brake: clamp(lt, 0, 1),
    handbrake: x || (buttons[1]?.pressed ?? false),
  };
}

/** Combine sources: largest magnitude wins per channel. */
export function mergeIntents(list: Intent[]): Intent {
  const out: Intent = { steer: 0, throttle: 0, brake: 0, handbrake: false };
  for (const i of list) {
    if (Math.abs(i.steer) > Math.abs(out.steer)) out.steer = i.steer;
    out.throttle = Math.max(out.throttle, i.throttle);
    out.brake = Math.max(out.brake, i.brake);
    out.handbrake = out.handbrake || i.handbrake;
  }
  return out;
}
