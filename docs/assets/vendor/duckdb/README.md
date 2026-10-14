# Vendored DuckDB-Wasm runtime

These files power the in-browser **live query console** (`docs/assets/duckdb-console.html`). They are vendored
(committed to the repo) rather than loaded from a CDN so the docs site is self-contained and offline-capable —
there is no runtime dependency on jsdelivr.

**Version:** `@duckdb/duckdb-wasm@1.29.0` · **Bundle:** `eh` only (WebAssembly exception handling).

| File | Size | What it is | Source |
| --- | --- | --- | --- |
| `duckdb-eh.wasm` | ~34 MB | DuckDB engine compiled to WASM (`eh` build; includes `httpfs`, `parquet`, `json`) | `dist/duckdb-eh.wasm` from the npm package, verbatim |
| `duckdb-browser-eh.worker.js` | ~760 KB | Web Worker that drives the engine (classic worker, self-contained) | `dist/duckdb-browser-eh.worker.js` from the npm package, verbatim |
| `duckdb-browser.bundled.js` | ~220 KB | The browser API (`AsyncDuckDB`, `selectBundle`, …) with its `apache-arrow` dependency inlined | built locally with esbuild (see below) |

## Why only the `eh` bundle

DuckDB-Wasm ships three bundles: `mvp`, `eh`, and `coi`. `coi` needs cross-origin isolation (COOP/COEP
headers) that GitHub Pages cannot set, so it is unusable here. `eh` (exception handling) is supported by every
modern browser, so the `mvp` fallback buys almost nothing for +38 MB. We vendor `eh` only.

## Why `duckdb-browser.bundled.mjs` is a local build

The package's own `dist/duckdb-browser.mjs` has a **bare import** — `import * as … from "apache-arrow"` — which a
browser cannot resolve without an import map or a bundler. So we bundle it into one self-contained ESM:

```bash
mkdir ddw-build && cd ddw-build
npm init -y
npm i @duckdb/duckdb-wasm@1.29.0
printf 'export * from "@duckdb/duckdb-wasm";\n' > entry.mjs
npx esbuild entry.mjs --bundle --format=esm --platform=browser --minify \
  --legal-comments=none --outfile=duckdb-browser.bundled.js
# then copy duckdb-browser.bundled.js here; copy the .wasm + .worker.js verbatim from node_modules/@duckdb/duckdb-wasm/dist/
```

The bundle is named `.js` (not `.mjs`) on purpose: GitHub Pages has served `.mjs` with a non-JavaScript MIME
type, which breaks the ESM `import`. A `.js` module imported with `import …` works and is served as
`text/javascript` reliably.

The `.wasm` and `.worker.js` are copied **verbatim** from the same package version — do not re-minify them.

## Upgrading

Bump the version in the commands above, rebuild all three files together (they must come from the **same**
version), and smoke-test the console in a browser (counts, DESCRIBE, a remote query, an error) before committing.
Git LFS is **not** an option — GitHub Pages serves the LFS pointer, not the file, so these stay as plain
committed blobs.
