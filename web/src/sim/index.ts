import type { Game, GameFactory } from './types';
import { StandInGame } from './standin';

/** Shape of the wasm-pack `web` target module. */
interface WasmModule {
  default: (input?: unknown) => Promise<unknown>;
  Game: new (seed: number, carId: number, steins: number) => Game;
  contract_version?: () => number;
}

export interface SimBackend {
  kind: 'wasm' | 'stand-in';
  create: GameFactory;
}

// Resolves to {} until web/src/wasm/pkg exists, so the build passes before and after it lands
// and no request is ever made for a missing file.
const pkgs = import.meta.glob('../wasm/pkg/*.js');

export async function loadSim(): Promise<SimBackend> {
  const key = Object.keys(pkgs).find((k) => !k.endsWith('_bg.js') && !k.includes('/snippets/'));
  if (key) {
    const mod = (await pkgs[key]()) as WasmModule;
    await mod.default();
    if (mod.contract_version && mod.contract_version() !== 1) throw new Error(`unsupported contract version ${mod.contract_version()}`);
    return { kind: 'wasm', create: (s, c, n) => new mod.Game(s, c, n) };
  }
  return { kind: 'stand-in', create: (s, c, n) => new StandInGame(s, c, n) };
}
