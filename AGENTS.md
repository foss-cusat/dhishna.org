# Dhishna 2027 — agent guide

## Scope and working approach

These instructions apply to this project and its subdirectories. Follow the user's latest direction when changing the design; the decisions below describe the current baseline.

- Work in this checkout and keep the active preview in sync with it.
- Inspect current files and the Git diff before editing. Preserve unrelated changes, including manual Blender edits.
- Make focused changes. Copy and layout adjustments do not require rebuilding the model.
- Complete authorized work without repeatedly asking for confirmation. Ask when missing information materially affects the result.
- Do not publish, deploy, or expose a public preview unless the user requests it.

## Product and visual direction

This is the landing page for Dhishna, CUSAT's tech fest in January 2027. It presents an illustrated campus scene, not a playable game. Do not invent exact event dates, registration links, or schedules.

- Preserve the recognizable pink and cream administration building, twin towers, detailed terracotta roofs, and ornamental university gate.
- Keep the enlarged Kathakali statue in the central oval garden. The separate statue island and old entrance banner were removed.
- Retain weathered facade textures, palms, faceted trees, dense grass, and festival preparation props.
- Aim for rich tropical greens, warm terracotta, and readable shadows. Earlier versions were overly dark/red or washed out; avoid restoring those looks.
- Foliage should move gently from anchored roots, with subtle camera parallax.

Current copy and layout:

- Brand: `dhishna /27`; top-right location: `KOCHI`.
- Headline: `Something's brewing`, retaining the existing italic treatment on `brewing`.
- Retain the tech-fest eyebrow and January 2027 date.
- The curiosity line, explanatory paragraph, coming-soon badge, university address, and “Back where it all begins” have been removed.
- Do not restore “See you on campus”, “A campus full of possibilities”, or the pause-motion control without a request.
- On phones, compact copy sits above a close-up campus scene that fills the remaining screen to the bottom edge. There must be no footer strip or page scrolling.
- Preserve the landscape layout, safe-area handling, and browser zoom accessibility.

## Stack and commands

React 19, TypeScript, Vite, Three.js, and React Three Fiber. Use Node.js 22.12 or newer; the test runner imports TypeScript with Node's experimental type stripping.

Run commands from the project root:

```sh
npm install
npm run dev
npm run build
npm test
```

- `npm run build` prepares the poster, checks TypeScript, and builds `dist/`.
- `npm test` runs scene/asset checks and Playwright checks against a production preview. Build first to avoid testing stale output.
- `npm run test:browser` runs only the browser checks against the existing production build.
- `npm run optimize:model` regenerates optimized web models and their generated metadata from the source export.
- The browser checker uses port 4177 and supports `BROWSER_PATH` for the Chromium executable. Screenshots and reports are written to `artifacts/`.

## Code map

- `src/App.tsx`: copy, layout markup, loading/fallback state, pointer input, and tilt controls.
- `src/styles.css`: typography, responsive layout, scene masks, and fixed mobile viewport.
- `src/Campus.tsx`: GLB loading, lighting, tone mapping, camera framing, GPU wind, and rendering lifecycle.
- `src/scene-policy.ts`: camera defaults, responsive spans, bounded pointer motion, tilt mapping, and motion policy.
- `src/usePhoneTilt.ts`: orientation availability, permissions, listeners, and calibration.
- `src/hooks.ts`: media queries, page visibility, and scene visibility.
- `src/model-assets.ts`: generated, versioned model URLs; regenerate through the asset pipeline rather than inventing cache hashes.
- `scripts/browser-check.mjs`: browser, viewport, fallback, and simulated sensor checks.
- `tests/scene.test.mjs`: camera/motion policy, model budgets, landmarks, texture fidelity, and rooted wind checks.

Read `README.md` and `assets/MODEL-REVIEW.md` for additional setup and model context. Historical framing measurements in those documents may lag behind the current source and recent user requests.

## Camera, colour, and rendering

- The scene uses an orthographic camera. Keep `manual: true` on the R3F camera: automatic projection updates previously broke initial mobile framing after layout sizing.
- Calculate framing from the actual scene container. Mobile has a closer view than desktop and anchors the composition at the lower edge as the available height changes.
- The current mobile span is `Math.max(34, 36 / Math.max(aspect, .65))`. Its minimum retains vertical context on short viewports. Adjust the framing policy deliberately rather than scaling the canvas with CSS.
- Keep mobile-layout media queries consistent between `App.tsx` and `styles.css`. Preserve the dynamic viewport sizing.
- The web renderer uses ACES filmic tone mapping, exposure 1, and sRGB output. Blender and browser rendering are not automatically colour-identical.
- If colours drift, inspect authored files, packed images, exported textures, material multipliers, lighting, tone mapping, and CSS blends before changing exposure globally.
- Preserve demand rendering, mobile DPR limits, and visibility/reduced-motion handling. Hidden and offscreen scenes should stop continuous rendering.
- Wind runs in vertex shaders using rooted weights. Avoid per-frame CPU geometry updates or shadow passes for every grass blade.

## Blender and asset workflow

- Main editable model: `assets/dhishna-campus-detailed.blend`, scene `Dhishna_Campus_Detailed`.
- Original model: `assets/dhishna-campus.blend`; preserve it.
- Detailed source export: `assets/cusat-detailed.glb`.
- Authored textures: `assets/textures/`.
- Web assets: `public/models/cusat.glb` and `public/models/cusat-mobile.glb`.
- Loading/fallback images: `public/campus-poster.png` and `public/campus-poster.webp`.

For model changes:

1. Inspect the current Blender scene, using the connected Blender MCP when available. Do not assume procedural scripts contain every later manual edit.
2. Modify the intended scene and save the editable model. Check the effects of scene-generation scripts before running them over existing work.
3. Run `scripts/export_detailed.py` in Blender with the detailed scene loaded. It refreshes packed textures, validates rooted wind, exports the source GLB, and saves the detailed Blender file.
4. Run `npm run optimize:model` to regenerate desktop/mobile assets, metadata, and versioned URLs together.
5. Refresh the fallback poster when the visible composition changes materially. With the development preview on port 5173, `node scripts/capture-colour.mjs --poster` captures the web scene into the PNG; the build generates WebP. Inspect that helper's Chromium path if running elsewhere.
6. Build, verify asset budgets, and inspect desktop and phone rendering.

An earlier export used stale packed texture bytes even though Blender displayed updated files from disk, causing dark roads and red roofs on the website. Preserve the exporter's refresh step and source-versus-export texture checks.

The optimized GLBs use Meshopt compression, quantized geometry, and WebP textures. Keep the bundled decoder and separate mobile model. Current tests enforce desktop/mobile limits of 12/8 MiB, 650,000/480,000 triangles, fewer than 130 draw calls, and maximum texture sizes of 1024/512 respectively. Optimize changes to fit these budgets rather than raising limits silently.

## Phone motion and fallbacks

- Orientation access requires a secure context. Ordinary LAN HTTP will not provide phone sensor data; localhost tests do not prove that LAN HTTP works.
- Use trusted HTTPS for physical-device testing. Browsers requiring explicit permission must request it from a user gesture.
- Calibrate to the first valid reading, account for screen rotation, ignore invalid readings/noise, and keep camera travel bounded.
- Respect reduced motion and tie listeners/rendering to page and scene visibility.
- Preserve poster fallback for failed model loading, unavailable WebGL, context loss, and data saver mode.
- Playwright dispatches synthetic orientation events and mocks permissions. Report these as simulated checks, not verification of physical phone sensors.

## Verification and handoff

- For app changes, run the production build and relevant existing checks. Do not add tests that merely repeat trivial copy or CSS edits.
- For layout/camera changes, inspect screenshots as well as DOM metrics. Cover a tall phone such as 412×915, a standard phone such as 390×844, a small phone such as 320×568, landscape, and desktop.
- Verify readable copy, the scene reaching the viewport bottom, and no mobile scrolling on either axis. Browser bars can change the available height.
- For model/renderer changes, also verify texture colours, retained landmarks, draw calls, mobile asset selection, motion, and fallbacks.
- Documentation-only changes need content/path review and a clean diff, not a model rebuild or rendering test.
- Summarize what changed and which checks actually ran. Do not claim physical-device testing or deployment that did not happen.
