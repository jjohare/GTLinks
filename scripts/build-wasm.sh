#!/usr/bin/env bash
# Builds the GTLinks simulation to WebAssembly for the web target, into web/src/wasm/pkg.
#
# Uses cargo and the wasm-bindgen CLI directly (not wasm-pack, whose flags differ between
# versions) with the workspace's `wasm-release` profile (opt-level z, fat LTO, panic = abort).
# The wasm-bindgen CLI version must match the crate pinned in Cargo.toml (0.2.129).
# binaryen's wasm-opt -Oz runs afterwards, if installed.
# Run from anywhere; paths are resolved from the repository root.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/web/src/wasm/pkg"
cd "$root"

cargo build -p gtlinks-wasm --lib --target wasm32-unknown-unknown --profile wasm-release

target_dir="${CARGO_TARGET_DIR:-$root/target}"
mkdir -p "$out"
wasm-bindgen --target web --out-dir "$out" --out-name gtlinks \
  "$target_dir/wasm32-unknown-unknown/wasm-release/gtlinks_wasm.wasm"

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
