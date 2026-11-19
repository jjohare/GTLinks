import { WebGPURenderer, PCFShadowMap, SRGBColorSpace, ACESFilmicToneMapping } from 'three/webgpu';

export type Backend = 'webgpu' | 'webgl2';

export interface GpuContext {
  renderer: WebGPURenderer;
  backend: Backend;
}

export const DPR_CAP = 1.75;

export class NoGpuError extends Error {}

/** Create and initialise the renderer. The backend is read from the renderer after init, never assumed. */
export async function createRenderer(canvas: HTMLCanvasElement): Promise<GpuContext> {
  const forceWebGL = new URLSearchParams(location.search).get('renderer') === 'webgl';
  let renderer: WebGPURenderer;
  try {
    renderer = new WebGPURenderer({ canvas, antialias: true, forceWebGL, powerPreference: 'high-performance' });
    await renderer.init();
  } catch (e) {
    throw new NoGpuError(`Neither WebGPU nor WebGL2 could be started (${(e as Error).message}).`);
  }
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  const be = renderer.backend as unknown as { isWebGPUBackend?: boolean };
  const backend: Backend = be.isWebGPUBackend ? 'webgpu' : 'webgl2';
  return { renderer, backend };
}

export function fitRenderer(r: WebGPURenderer, width: number, height: number): void {
  r.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP));
  r.setSize(width, height, false);
}
