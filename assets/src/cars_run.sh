#!/usr/bin/env bash
# Car-only runner: stages the car scripts into a private folder of the sidecar share, builds or renders,
# and copies results back.  Uses its own share folder so it never collides with run.sh.
#   assets/src/cars_run.sh build  <keys|cars|all> [ao=1] [cars.json] [out dir]   -> web/public/assets/cars (default)
#   assets/src/cars_run.sh render <keys[,lineup]> [views] [glb dir] [png dir]     -> docs/evidence/assets (default)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
J=/opt/agentbox/skills/blender/tools/blender-job.js
L=/home/devuser/gui-tools/gtlcars; R=/home/devuser/exchange/gtlcars
mode="${1:?build|render}"; what="${2:?what}"
name="gtlcars-$mode-$$-$(date +%s)"
mkdir -p "$L/src"
cp -f "$HERE"/gtl.py "$HERE"/cars.py "$HERE"/carkit.py "$HERE"/carparts.py "$HERE"/cars_job.py "$HERE"/cars_render.py "$L/src/"
if [ "$mode" = build ]; then
  ao="${3:-1}"; json="${4:-$REPO/assets/cars.json}"; dest="${5:-$REPO/web/public/assets/cars}"
  cp -f "$json" "$L/cars_$name.json"; mkdir -p "$L/out_$name"
  node $J submit "$HERE/cars_job.py" --name "$name" -- --src $R/src --cars "$R/cars_$name.json" --out "$R/out_$name" --what "$what" --ao "$ao" >/dev/null
  node $J wait "$name" --timeout 1700 >/dev/null || { node $J tail "$name" 60; rm -rf "$L/out_$name" "$L/cars_$name.json"; exit 1; }
  node $J tail "$name" 400 | grep -E "^BUILT|FAILED|Traceback|Error" || true
  mkdir -p "$dest"; cp -f "$L/out_$name"/cars/*.glb "$dest/"; cp -f "$L/out_$name/cars_report.json" "$dest/../" 2>/dev/null || true
  rm -rf "$L/out_$name" "$L/cars_$name.json"
else
  views="${3:-front34,side,rear34,drone,under,underrear,nose}"; glb="${4:-$REPO/web/public/assets/cars}"; dest="${5:-$REPO/docs/evidence/assets}"
  mkdir -p "$L/glb_$name" "$L/png_$name"; cp -f "$glb"/*.glb "$L/glb_$name/"
  node $J submit "$HERE/cars_render.py" --name "$name" -- --glb "$R/glb_$name" --out "$R/png_$name" --what "$what" --views "$views" >/dev/null
  node $J wait "$name" --timeout 1700 >/dev/null || { node $J tail "$name" 60; rm -rf "$L/glb_$name" "$L/png_$name"; exit 1; }
  node $J tail "$name" 300 | grep -E "RENDERED|Traceback|Error" || true
  mkdir -p "$dest"; cp -f "$L/png_$name"/*.png "$dest/"
  rm -rf "$L/glb_$name" "$L/png_$name"
fi
