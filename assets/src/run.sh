#!/usr/bin/env bash
# Stage sources + cars.json into the sidecar share, run a headless job, wait, copy results back.
# Concurrency-safe: every invocation uses its own out/png directory in the share.
# usage: assets/src/run.sh build <what>      (what = cars | props | all | <key>,<name>,...)
#        assets/src/run.sh render <targets>  (see render.py: cars, <car key>, lodge, view:<prop>[,<prop>], ...)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
J=/opt/agentbox/skills/blender/tools/blender-job.js
SHARE_L=/home/devuser/gui-tools/gtl
SHARE_R=/home/devuser/exchange/gtl
mode="${1:?build|render}"; what="${2:-all}"
node $J stage "$HERE" gtl/src >/dev/null
node $J stage "$REPO/assets/cars.json" gtl/cars.json >/dev/null
name="gtl-$mode-$$-$(date +%s)"
if [ "$mode" = build ]; then
  OUT_L="$SHARE_L/out_$name"; OUT_R="$SHARE_R/out_$name"; mkdir -p "$OUT_L"
  [ "${GTL_BUILD_CARS:-}" = 1 ] || echo "run.sh: cars skipped (set GTL_BUILD_CARS=1 to build/copy car GLBs)"
  node $J submit "$HERE/build.py" --name "$name" -- --src $SHARE_R/src --cars $SHARE_R/cars.json --out $OUT_R --what "$what" $([ "${GTL_BUILD_CARS:-}" = 1 ] && echo --build-cars) >/dev/null
  node $J wait "$name" --timeout 1700 >/dev/null || { node $J tail "$name" 80; exit 1; }
  node $J tail "$name" 400 | grep -E "BUILT|Traceback|Error|error" || true
  mkdir -p "$REPO/web/public/assets/cars" "$REPO/web/public/assets/props"
  [ "${GTL_BUILD_CARS:-}" = 1 ] && cp -f "$OUT_L"/cars/*.glb "$REPO/web/public/assets/cars/" 2>/dev/null || true
  cp -f "$OUT_L"/props/*.glb "$REPO/web/public/assets/props/" 2>/dev/null || true
  rm -rf "$OUT_L"
else
  PNG_L="$SHARE_L/png_$name"; PNG_R="$SHARE_R/png_$name"; GLB_L="$SHARE_L/glb_$name"; GLB_R="$SHARE_R/glb_$name"
  mkdir -p "$PNG_L" "$GLB_L"
  cp -f "$REPO"/web/public/assets/cars/*.glb "$GLB_L/" 2>/dev/null || true
  cp -f "$REPO"/web/public/assets/props/*.glb "$GLB_L/" 2>/dev/null || true
  node $J submit "$HERE/render.py" --name "$name" -- --src $SHARE_R/src --glb $GLB_R --out $PNG_R --what "$what" >/dev/null
  node $J wait "$name" --timeout 1700 >/dev/null || { node $J tail "$name" 80; exit 1; }
  node $J tail "$name" 200 | grep -E "RENDERED|Traceback|Error" || true
  mkdir -p "$REPO/docs/evidence/assets"
  if [ "${GTL_BUILD_CARS:-}" = 1 ]; then cp -f "$PNG_L"/*.png "$REPO/docs/evidence/assets/"
  else find "$PNG_L" -name '*.png' ! -name 'escapade_2009_*' ! -name 'glug_2017_*' ! -name 'genesips_2021_*' ! -name 'rangeroller_2026_*' -exec cp -f {} "$REPO/docs/evidence/assets/" \; ; fi
  rm -rf "$PNG_L" "$GLB_L"
fi
