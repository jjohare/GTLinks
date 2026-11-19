#!/usr/bin/env bash
# usage: run_shots.sh "<shot spec>;<shot spec>"   (props2 close-up helper; see render_props2.py)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
J=/opt/agentbox/skills/blender/tools/blender-job.js
SL=/home/devuser/gui-tools/gtl; SR=/home/devuser/exchange/gtl
node $J stage "$HERE" gtl/src >/dev/null
name="gtl-shot-$$-$(date +%s)"
P_L="$SL/png_$name"; P_R="$SR/png_$name"; G_L="$SL/glb_$name"; G_R="$SR/glb_$name"
mkdir -p "$P_L" "$G_L"; cp -f "$REPO"/web/public/assets/props/*.glb "$G_L/"
node $J submit "$HERE/render_props2.py" --name "$name" -- --src $SR/src --glb $G_R --out $P_R --what "$1" >/dev/null
node $J wait "$name" --timeout 900 >/dev/null || { node $J tail "$name" 60; exit 1; }
mkdir -p "$REPO/docs/evidence/assets"; cp -f "$P_L"/*.png "$REPO/docs/evidence/assets/"; rm -rf "$P_L" "$G_L"
