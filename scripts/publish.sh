#!/usr/bin/env bash
# Builds the site locally and publishes it straight to GitHub Pages.
#
# No CI: the wasm package and the Vite bundle are built on this machine, and web/dist is
# force-pushed as a single commit to the `gh-pages` branch, which Pages serves as-is.
# Usage: scripts/publish.sh ["commit message"]
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
msg="${1:-Publish $(date -u +%Y-%m-%dT%H:%MZ)}"
remote="$(git remote get-url origin)"

./scripts/build-wasm.sh
(cd web && npm run build)

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
cp -r web/dist/. "$stage/"
touch "$stage/.nojekyll"
cd "$stage"
git init -q -b gh-pages
git config user.name "$(git -C "$root" config user.name)"
git config user.email "$(git -C "$root" config user.email)"
git add -A
git commit -q -m "$msg"
git push -q --force "$remote" gh-pages
echo "published $(git rev-parse --short HEAD) to gh-pages"
