/**
 * Index buffer for a block of the contract heightfield. Node (ix, iz) has index iz*stride + ix.
 * Each cell is split along the diagonal (ix,iz)-(ix+1,iz+1), matching the simulation exactly.
 * Triangles wind so that, with +X right and +Z down the page, the normal points to +Y.
 */
export function buildChunkIndices(ix0: number, iz0: number, cellsX: number, cellsZ: number, stride: number): Uint32Array {
  const out = new Uint32Array(cellsX * cellsZ * 6);
  let o = 0;
  for (let cz = 0; cz < cellsZ; cz++) {
    for (let cx = 0; cx < cellsX; cx++) {
      const a = (iz0 + cz) * stride + ix0 + cx; // (ix, iz)
      const b = a + 1; // (ix+1, iz)
      const c = a + stride; // (ix, iz+1)
      const d = c + 1; // (ix+1, iz+1)
      out[o++] = a; out[o++] = c; out[o++] = d;
      out[o++] = a; out[o++] = d; out[o++] = b;
    }
  }
  return out;
}
