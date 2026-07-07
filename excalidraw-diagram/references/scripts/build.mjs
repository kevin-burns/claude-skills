// esbuild config that produces vendor/excalidraw.mjs — a single, self-contained,
// fully-offline ESM bundle exporting Excalidraw's exportToSvg.
//
// Run via scripts/vendor.sh, which installs the pinned package first.
import { build } from "esbuild";

// Drop the Xiaolai CJK fallback font (~12 MB of woff2 subset chunks). Technical
// / English diagrams never use it; the Latin fonts stay resolvable at runtime.
// To keep CJK support, delete this plugin and re-run vendor.sh (the bundle and
// vendored fonts get ~12 MB larger).
const dropCjkFonts = {
  name: "drop-cjk-fonts",
  setup(b) {
    b.onResolve({ filter: /Xiaolai/ }, (args) => ({
      path: args.path,
      namespace: "empty-font",
    }));
    b.onLoad({ filter: /.*/, namespace: "empty-font" }, () => ({
      contents: 'export default "data:font/woff2;base64,";',
      loader: "js",
    }));
  },
};

await build({
  entryPoints: ["entry.mjs"],
  bundle: true,
  format: "esm",
  minify: true,
  outfile: "excalidraw.mjs",
  define: { "process.env.NODE_ENV": '"production"' },
  loader: {
    ".css": "empty",
    ".woff": "dataurl",
    ".woff2": "dataurl",
    ".ttf": "dataurl",
    ".otf": "dataurl",
    ".svg": "dataurl",
    ".png": "dataurl",
  },
  plugins: [dropCjkFonts],
  logLevel: "warning",
});

console.log("built excalidraw.mjs");
