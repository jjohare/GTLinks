#!/usr/bin/env bash
# Builds the GTLinks simulation to WebAssembly for the web target, into web/src/wasm/pkg.
#
# Uses wasm-pack with the workspace's `wasm-release` profile (opt-level z, fat LTO,
# panic = abort). wasm-pack's own wasm-opt step is skipped because it does not enable the
# features rustc now emits; binaryen's wasm-opt -Oz runs here instead, if installed.
# Run from anywhere; paths are resolved from the repository root.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/web/src/wasm/pkg"
cd "$root"

wasm-pack build crates/gtlinks-wasm \
  --target web \
  --profile wasm-release \
  --out-dir "$out" \
  --out-name gtlinks \
  --no-pack \
  --no-opt

wasm="$out/gtlinks_bg.wasm"
if command -v wasm-opt >/dev/null 2>&1; then
  # The feature set rustc's wasm32-unknown-unknown target emits by default.
  wasm-opt -Oz --enable-bulk-memory --enable-nontrapping-float-to-int --enable-sign-ext \
    --enable-mutable-globals --enable-multivalue --enable-reference-types \
    "$wasm" -o "$wasm.opt"
  mv "$wasm.opt" "$wasm"
else
  echo "wasm-opt not found; skipping the size pass" >&2
fi
rm -f "$out/.gitignore"
bytes=$(wc -c < "$wasm")
echo "built $wasm (${bytes} bytes)"
