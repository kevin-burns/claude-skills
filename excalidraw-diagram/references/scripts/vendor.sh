#!/usr/bin/env bash
#
# Regenerate references/vendor/ — the offline Excalidraw render engine.
#
# You only need this to BUMP the pinned Excalidraw version. Normal use of the
# skill never runs it: the vendored files are committed and shipped as-is.
#
# Requires: node + npm (Node 18+). Produces a single self-contained ESM bundle
# plus the Latin font files, all under references/vendor/.
#
# Usage:
#   scripts/vendor.sh                # re-vendor the currently pinned version
#   scripts/vendor.sh 0.18.1         # vendor a specific version
#
# After running, render a test diagram and eyeball it before committing — a new
# Excalidraw version can change export behavior. Update vendor/VERSION too.
set -euo pipefail

VERSION="${1:-0.18.1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REF_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENDOR_DIR="$REF_DIR/vendor"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Latin font families to vendor. Xiaolai (CJK, ~12 MB) is intentionally omitted;
# see build.mjs and vendor/VERSION.
FONT_FAMILIES=(Excalifont Nunito Cascadia ComicShanns Virgil Liberation Assistant Lilita)

echo ">> vendoring @excalidraw/excalidraw@$VERSION into $VENDOR_DIR"

cd "$WORK"
npm init -y >/dev/null 2>&1
echo ">> installing @excalidraw/excalidraw@$VERSION + esbuild ..."
npm install "@excalidraw/excalidraw@$VERSION" esbuild >/dev/null 2>&1

echo 'export { exportToSvg } from "@excalidraw/excalidraw";' > entry.mjs
cp "$SCRIPT_DIR/build.mjs" build.mjs

echo ">> bundling ..."
node build.mjs

FONTS_SRC="$WORK/node_modules/@excalidraw/excalidraw/dist/prod/fonts"

echo ">> installing artifacts ..."
rm -rf "$VENDOR_DIR/excalidraw.mjs" "$VENDOR_DIR/fonts"
mkdir -p "$VENDOR_DIR/fonts"
cp "$WORK/excalidraw.mjs" "$VENDOR_DIR/excalidraw.mjs"
for fam in "${FONT_FAMILIES[@]}"; do
  [ -d "$FONTS_SRC/$fam" ] && cp -R "$FONTS_SRC/$fam" "$VENDOR_DIR/fonts/$fam"
done

echo ">> done."
echo "   bundle: $(du -h "$VENDOR_DIR/excalidraw.mjs" | cut -f1)"
echo "   fonts:  $(du -sh "$VENDOR_DIR/fonts" | cut -f1)  ($(ls "$VENDOR_DIR/fonts" | tr '\n' ' '))"

# Update the integrity pin the render script reads.
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}
BUNDLE_SHA="$(sha256_of "$VENDOR_DIR/excalidraw.mjs")"
BUNDLE_BYTES="$(wc -c < "$VENDOR_DIR/excalidraw.mjs" | tr -d ' ')"
TAG="excalidraw-vendor-v$VERSION"
REPO="kevin-burns/claude-skills"
URL="https://github.com/$REPO/releases/download/$TAG/excalidraw.mjs"

cat > "$VENDOR_DIR/bundle.lock.json" <<JSON
{
  "file": "excalidraw.mjs",
  "excalidraw_version": "$VERSION",
  "url": "$URL",
  "sha256": "$BUNDLE_SHA",
  "bytes": $BUNDLE_BYTES
}
JSON
echo "   lock:   updated vendor/bundle.lock.json (sha256 $BUNDLE_SHA)"

echo ""
echo "Next: publish the bundle as the pinned release asset, then commit the lock:"
echo "  gh release create $TAG \"$VENDOR_DIR/excalidraw.mjs\" \\"
echo "     --repo $REPO --title \"Excalidraw render engine $VERSION\" \\"
echo "     --notes \"Vendored @excalidraw/excalidraw@$VERSION exportToSvg bundle for excalidraw-diagram.\""
echo "  # (if the tag already exists: gh release upload $TAG \"$VENDOR_DIR/excalidraw.mjs\" --repo $REPO --clobber)"
echo "  git add vendor/bundle.lock.json && git commit -m \"excalidraw-diagram: bump render engine to $VERSION\""
echo ""
echo "Then render a test diagram and eyeball it before pushing."
