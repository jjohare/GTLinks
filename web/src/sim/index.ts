import { StandInGame } from './standin';
import { FallbackPursuit } from './pursuit';
import type { BaseGame, Game, GameFactory } from './types';

/** Shape of the wasm-pack `web` target module. */
interface WasmModule {
  default: (input?: unknown) => Promise<unknown>;
  Game: new (seed: number, carId: number, steins: number) => BaseGame;
  contract_version: () => number;
}

export interface SimBackend {
  kind: 'wasm' | 'stand-in';
  create: GameFactory;
}

// Resolves to {} until web/src/wasm/pkg exists, so the build never depends on it.
const pkgs = import.meta.glob('../wasm/pkg/*.js');

/**
 * Give any backend the full Game surface. Police and helicopter buffers come from the simulation when it exposes
 * them, otherwise from the front-end fallback; each is detected independently so staged simulation releases work.
 */
function withPursuit(inner: BaseGame): Game {
  const hasPolice = typeof inner.police_state === 'function';
  const hasHeli = typeof inner.heli_state === 'function';
  if (hasPolice && hasHeli) return inner as Game;
  const fb = new FallbackPursuit(inner, !hasPolice, !hasHeli);
  const g: Game = {
    course_json: () => inner.course_json(),
    heightfield: () => inner.heightfield(),
    surface_map: () => inner.surface_map(),
    height_at: (x, z) => inner.height_at(x, z),
    step: (dt, a, b, c, d) => { inner.step(dt, a, b, c, d); fb.tick(dt); },
    state: () => inner.state(),
    drain_events: () => {
      const e = inner.drain_events();
      const extra = fb.drain();
      if (!extra.length) return e;
      const out = new Float32Array(e.length + extra.length);
      out.set(e); out.set(extra, e.length);
      return out;
    },
    police_state: () => (hasPolice ? inner.police_state!() : fb.policeState()),
    heli_state: () => (hasHeli ? inner.heli_state!() : fb.heliState()),
    free: () => inner.free?.(),
  };
  return g;
}

/** Load the wasm simulation, or fall back to the stand-in when the package has not been built. */
export async function loadSim(): Promise<SimBackend> {
  const key = Object.keys(pkgs).find((k) => !k.endsWith('_bg.js') && !k.includes('/snippets/'));
  if (key) {
    const mod = (await pkgs[key]()) as WasmModule;
    await mod.default();
    if (mod.contract_version() < 1) throw new Error(`unsupported contract version ${mod.contract_version()}`);
    return { kind: 'wasm', create: (s, c, n) => withPursuit(new mod.Game(s, c, n)) };
  }
  return { kind: 'stand-in', create: (s, c, n) => withPursuit(new StandInGame(s, c, n)) };
}
