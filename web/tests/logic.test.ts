import { describe, expect, it } from 'vitest';
import { decodeEvents, decodeState, EventKind, Phase, S, STATE_LEN } from '../src/sim/types';
import { SteinLoad, MAX_STEINS, MIN_STEINS } from '../src/core/steins';
import { nextScreen } from '../src/core/flow';
import { gamepadIntent, keyboardIntent, mergeIntents, applyDeadzone } from '../src/input/mapping';
import { buildChunkIndices } from '../src/world/terrainIndex';

describe('state decoding', () => {
  it('maps every contract index', () => {
    const f = new Float32Array(STATE_LEN);
    for (let i = 0; i < STATE_LEN; i++) f[i] = i + 0.5;
    f[S.phase] = 4;
    const s = decodeState(f);
    expect(s.pos).toEqual([0.5, 1.5, 2.5]);
    expect(s.quat).toEqual([3.5, 4.5, 5.5, 6.5]);
    expect(s.vel).toEqual([7.5, 8.5, 9.5]);
    expect(s.angVel).toEqual([10.5, 11.5, 12.5]);
    expect(s.wheels[0]).toEqual({ compression: 13.5, spin: 14.5, steer: 15.5 });
    expect(s.wheels[3]).toEqual({ compression: 22.5, spin: 23.5, steer: 24.5 });
    expect(s.phase).toBe(Phase.Wrecked);
    expect(s.damage).toBe(26.5);
    expect(s.runTime).toBe(27.5);
    expect(s.hole).toBe(28.5);
    expect(s.speed).toBe(29.5);
    expect(s.wheelsOnGround).toBe(30.5);
    expect(s.airtime).toBe(31.5);
    expect(s.appliedSteer).toBe(32.5);
    expect(s.wobble).toBe(33.5);
    expect(s.trick).toBe(34.5);
    expect(s.wreckedFor).toBe(35.5);
  });
  it('rejects a wrong length', () => {
    expect(() => decodeState(new Float32Array(35))).toThrow();
  });
});

describe('event decoding', () => {
  it('splits the flat buffer', () => {
    const ev = decodeEvents(new Float32Array([6, 2, 150, 1, 2, 3, 11, 0.5, 0, 4, 5, 6]));
    expect(ev).toHaveLength(2);
    expect(ev[0]).toEqual({ kind: EventKind.Trick, a: 2, b: 150, x: 1, y: 2, z: 3 });
    expect(ev[1].kind).toBe(EventKind.Hiccup);
  });
  it('ignores a trailing partial record and empty input', () => {
    expect(decodeEvents(new Float32Array([1, 2, 3]))).toHaveLength(0);
    expect(decodeEvents(new Float32Array(0))).toHaveLength(0);
  });
});

describe('stein loading', () => {
  it('locks GO below 10 and unlocks at 10', () => {
    const l = new SteinLoad();
    for (let i = 0; i < MIN_STEINS - 1; i++) l.addNext();
    expect(l.canGo).toBe(false);
    l.addNext();
    expect(l.canGo).toBe(true);
  });
  it('caps at 15', () => {
    const l = new SteinLoad();
    for (let i = 0; i < 20; i++) l.addNext();
    expect(l.count).toBe(MAX_STEINS);
    expect(l.add(3)).toBe(false);
    expect(l.addNext()).toBeNull();
  });
  it('removes and re-locks, rejects duplicates', () => {
    const l = new SteinLoad();
    for (let i = 0; i < 10; i++) l.addNext();
    expect(l.add(2)).toBe(false);
    expect(l.remove(4)).toBe(true);
    expect(l.remove(4)).toBe(false);
    expect(l.canGo).toBe(false);
    expect(l.addNext()).toBe(4);
    expect(l.removeLast()).toBe(4);
    expect(l.severity).toBe(0);
  });
  it('severity spans 0..1', () => {
    const l = new SteinLoad();
    for (let i = 0; i < 15; i++) l.addNext();
    expect(l.severity).toBe(1);
  });
});

describe('input mapping', () => {
  it('steers left as +1', () => {
    expect(keyboardIntent(new Set(['KeyA'])).steer).toBe(1);
    expect(keyboardIntent(new Set(['ArrowRight'])).steer).toBe(-1);
    expect(keyboardIntent(new Set(['KeyA', 'KeyD'])).steer).toBe(0);
    const i = keyboardIntent(new Set(['KeyW', 'Space']));
    expect(i.throttle).toBe(1);
    expect(i.handbrake).toBe(true);
  });
  it('gamepad stick left steers +1 with deadzone', () => {
    const b = Array.from({ length: 16 }, () => ({ value: 0, pressed: false }));
    expect(gamepadIntent([-1, 0], b).steer).toBeCloseTo(1);
    expect(gamepadIntent([0.05, 0], b).steer).toBe(0);
    b[7] = { value: 0.6, pressed: true };
    expect(gamepadIntent([0, 0], b).throttle).toBeCloseTo(0.6);
    expect(applyDeadzone(1)).toBe(1);
  });
  it('merges by magnitude', () => {
    const m = mergeIntents([
      { steer: 0.3, throttle: 0, brake: 0, handbrake: false },
      { steer: -0.8, throttle: 1, brake: 0, handbrake: true },
    ]);
    expect(m).toEqual({ steer: -0.8, throttle: 1, brake: 0, handbrake: true });
  });
});

describe('screen flow', () => {
  it('walks the loop', () => {
    let s = nextScreen('loading', { t: 'ready' });
    expect(s).toBe('lodge');
    s = nextScreen(s, { t: 'go' });
    expect(s).toBe('descent');
    s = nextScreen(s, { t: 'phase', phase: Phase.FinaleArmed });
    expect(s).toBe('descent');
    s = nextScreen(s, { t: 'phase', phase: Phase.Wrecked });
    expect(s).toBe('wreck');
    s = nextScreen(s, { t: 'wreckDone' });
    expect(s).toBe('fade');
    s = nextScreen(s, { t: 'faded' });
    expect(s).toBe('lodge');
  });
  it('ignores out-of-order events and restarts from anywhere but loading', () => {
    expect(nextScreen('lodge', { t: 'phase', phase: Phase.Wrecked })).toBe('lodge');
    expect(nextScreen('descent', { t: 'restart' })).toBe('lodge');
    expect(nextScreen('loading', { t: 'restart' })).toBe('loading');
  });
});

describe('terrain triangulation', () => {
  it('splits each cell along (ix,iz)->(ix+1,iz+1) with upward winding', () => {
    const w = 3; // 3x3 nodes, flat
    const idx = buildChunkIndices(0, 0, 2, 2, w);
    expect(idx).toHaveLength(2 * 2 * 6);
    const pos = (i: number) => [i % w, 0, Math.floor(i / w)];
    for (let t = 0; t < idx.length; t += 3) {
      const a = pos(idx[t]), b = pos(idx[t + 1]), c = pos(idx[t + 2]);
      const e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
      const e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
      const ny = e1[2] * e2[0] - e1[0] * e2[2];
      expect(ny).toBeGreaterThan(0);
    }
    // first cell: both triangles share the (0,0)-(1,1) diagonal = nodes 0 and 4
    const first = [...idx.slice(0, 6)];
    expect(first.filter((i) => i === 0).length).toBe(2);
    expect(first.filter((i) => i === 4).length).toBe(2);
  });
});
