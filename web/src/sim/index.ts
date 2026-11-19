import type { Game, GameFactory } from './types';

/** Shape of the wasm-pack `web` target module. */
interface WasmModule {
  default: (input?: unknown) => Promise<unknown>;
  Game: new (seed: number, carId: number, steins: number) => Game;
  contract_version: () => number;
}

export interface SimBackend {
  create: GameFactory;
}

// The wasm-pack package is generated into src/wasm/pkg by scripts/build-wasm.sh. A glob keeps the
// type-check and bundling independent of whether it has been built yet; loadSim reports a clear error.
const pkgs = import.meta.glob('../wasm/pkg/*.js');

/** Load and initialise the simulation. The wasm file is resolved relative to the module by wasm-bindgen. */
export async function loadSim(): Promise<SimBackend> {
  const key = Object.keys(pkgs).find((k) => !k.endsWith('_bg.js') && !k.includes('/snippets/'));
  if (!key) throw new Error('the simulation package is missing: run scripts/build-wasm.sh to create web/src/wasm/pkg');
  const mod = (await pkgs[key]()) as WasmModule;
  await mod.default();
  if (mod.contract_version() !== 1) throw new Error(`unsupported contract version ${mod.contract_version()}`);
  return { create: (s, c, n) => new mod.Game(s, c, n) };
}
