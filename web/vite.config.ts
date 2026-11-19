import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  resolve: {
    // One copy of three: addons import the bare specifier, which must land on the webgpu build.
    alias: [{ find: /^three$/, replacement: 'three/webgpu' }],
  },
  build: { target: 'es2022', chunkSizeWarningLimit: 2500, sourcemap: false },
  server: { host: true },
  test: { environment: 'node', include: ['tests/**/*.test.ts'] },
});
