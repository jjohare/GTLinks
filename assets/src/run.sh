#!/usr/bin/env bash
# Stage sources + cars.json into the sidecar share, run a headless job, wait, copy results back.
# usage: assets/src/run.sh build <what>      (what = cars | props | all | <key>,<name>,...)
#        assets/src/run.sh render <targets>  (renders previews of the exported GLBs)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
J=/opt/agentbox/skills/blender/tools/blender-job.js
SHARE_L=/home/devuser/gui-tools/gtl
SHARE_R=/home/devuser/exchange/gtl
mode="${1:?build|render}"; what="${2:-all}"
node $J stage "$HERE" gtl/src >/dev/null
node $J stage "$REPO/assets/cars.json" gtl/cars.json >/dev/null
name="gtl-$mode-$(date +%s)"
if [ "$mode" = build ]; then
  mkdir -p "$SHARE_L/out"
  node $J submit "$HERE/build.py" --name "$name" -- --src $SHARE_R/src --cars $SHARE_R/cars.json --out $SHARE_R/out --what "$what"
  node $J wait "$name" --timeout 900 || { node $J tail "$name" 60; exit 1; }
  node $J tail "$name" 30
  mkdir -p "$REPO/web/public/assets/cars" "$REPO/web/public/assets/props"
  cp -f "$SHARE_L"/out/cars/*.glb "$REPO/web/public/assets/cars/" 2>/dev/null || true
  cp -f "$SHARE_L"/out/props/*.glb "$REPO/web/public/assets/props/" 2>/dev/null || true
else
  rm -rf "$SHARE_L/png"; mkdir -p "$SHARE_L/glb" "$SHARE_L/png"
  cp -f "$REPO"/web/public/assets/cars/*.glb "$SHARE_L/glb/" 2>/dev/null || true
  cp -f "$REPO"/web/public/assets/props/*.glb "$SHARE_L/glb/" 2>/dev/null || true
  node $J submit "$HERE/render.py" --name "$name" -- --src $SHARE_R/src --glb $SHARE_R/glb --out $SHARE_R/png --what "$what"
  node $J wait "$name" --timeout 1500 || { node $J tail "$name" 60; exit 1; }
  node $J tail "$name" 12
  mkdir -p "$REPO/docs/evidence/assets"
  cp -f "$SHARE_L"/png/*.png "$REPO/docs/evidence/assets/"
fi
