import { defineConfig, type Plugin } from 'vite';
import { readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

/**
 * Virtual module `virtual:asset-manifest`: the list of files that actually exist under
 * public/assets at build time. The runtime consults it so a GLB that has not been built yet
 * is substituted without issuing a request that would 404 and pollute the console.
 */
function assetManifest(): Plugin {
  const id = 'virtual:asset-manifest';
  const resolved = '\0' + id;
  const root = resolve(__dirname, 'public/assets');
  const walk = (dir: string, out: string[]): string[] => {
    if (!existsSync(dir)) return out;
    for (const name of readdirSync(dir)) {
      const p = join(dir, name);
      if (statSync(p).isDirectory()) walk(p, out);
      else out.push(relative(resolve(__dirname, 'public'), p).split('\\').join('/'));
    }
    return out;
  };
  return {
    name: 'gtlinks-asset-manifest',
    resolveId: (s) => (s === id ? resolved : null),
    load: (s) => (s === resolved ? `export default ${JSON.stringify(walk(root, []).sort())};` : null),
  };
}

export default defineConfig({
  base: './',
  plugins: [assetManifest()],
  resolve: {
    // One copy of three: addons import the bare specifier, which must land on the webgpu build.
    alias: [{ find: /^three$/, replacement: 'three/webgpu' }],
  },
  build: { target: 'es2022', chunkSizeWarningLimit: 2500, sourcemap: false },
  server: { host: true },
  test: { environment: 'node', include: ['tests/**/*.test.ts'] },
});
