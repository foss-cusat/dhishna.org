# Dhishna 2027

Responsive CUSAT landing page with the detailed campus model, university gate, central statue, dense rooted foliage, raised clay roof tiles, weathered plaster and festival preparations.

## Run and validate

Requires Node.js 22.12 or newer.

```sh
npm install
npm run dev
npm run build
npm test
```

The tests launch the production build with Playwright on a temporary local port. Build before testing. Set `BROWSER_PATH` if Chromium is installed elsewhere. Screenshots and browser reports are in `artifacts/`.

## Model pipeline

The complete editable artwork is `assets/dhishna-campus-detailed.blend`, scene `Dhishna_Campus_Detailed`. The original model is preserved in `assets/dhishna-campus.blend`. Model-generation steps and reference renders are documented in `assets/MODEL-REVIEW.md`.

After editing the detailed scene, run `scripts/export_detailed.py` in Blender to create `assets/cusat-detailed.glb`. Then:

```sh
npm run optimize:model
npm run build
npm test
```

The optimizer produces separate desktop and mobile GLBs. It rebuilds folded grass blades, uses fewer blades on mobile, conservatively simplifies static geometry, removes unused texture coordinates, joins compatible materials, compresses geometry with Meshopt, and resizes textures to WebP. The gate, enlarged central statue, roof tiles and all four weathered plaster materials are retained.

The authoring wind clip stays in Blender. Website assets replace morph targets with zero-weight roots and a lightweight vertex wind shader. This reduces upload size and per-frame CPU work while keeping stems anchored. Model transforms and phase constants are computed once, not separately for every vertex.

Current measured assets:

| Asset | Download | Triangles | Draw calls |
|---|---:|---:|---:|
| Detailed authoring export | 57.86 MB | 724,287 | 269 before browser batching |
| Desktop | 10.65 MB | 534,097 | 65 |
| Mobile | 8.01 MB | 403,325 | 65 |

Sizes use decimal MB. `public/models/scene-info*.json` and `artifacts/optimization-report.json` record exact counts. The mobile asset is about 86% smaller than the detailed export; texture payload is 28 KB mobile / 72 KB desktop. Desktop maps are at most 1024 pixels; mobile maps at most 512 pixels.

After visual changes, keep the dev server on port 5173 and run `node scripts/capture-colour.mjs --poster`. This captures the current web lighting and camera into `public/campus-poster.png`; the build generates its WebP fallback.

The exporter refreshes packed texture bytes from the authored PNGs before exporting. Regression checks compare the optimized base-colour maps against these PNGs to detect stale or incorrectly encoded colours. The website uses ACES daylight grading, a restrained hemisphere fill and a deeper green meadow tint to match the vivid illustrated reference. Its orthographic framing is about 22% closer than the original hero.

## Browser behavior

- Phone/touch layouts request only the mobile asset. Phone layouts fit one dynamic viewport with no page scrolling, including browser toolbar changes. Copy spacing scales with screen height, the scene fills the remaining space, and landscape phones use a side-by-side composition. The mobile camera is another ~15% closer; the footer and lower fade remain hidden.
- Phone tilt gently shifts the camera around a calibrated resting position. It respects reduced motion and stops listening while hidden/offscreen. Safari shows an Enable tilt button when permission is required. Sensor access requires HTTPS (localhost is allowed); unavailable or denied sensors leave the scene usable.
- Rendering is on demand, with wind updates capped at 45 FPS desktop / 30 FPS mobile.
- Reduced motion renders a still scene; the hero has no visible motion control.
- Hidden or offscreen scenes stop continuous rendering.
- Slow renderers lower resolution after a short sample.
- Data saver skips the 3D chunk and model and displays the campus poster.
- Model-load failure, unavailable WebGL or context loss displays the poster.
- The 3D code loads separately from the initial landing content.

Headless software WebGL tests verify functionality and rendering counters, not physical phone performance. A real Android/iOS check is still needed before publishing.

The page remains the January 2027 coming-soon hero. It does not invent dates, registration links or event schedules.

## Deployment

`npm run build` creates the static site in `dist/`. Serve it at the domain root. Enable gzip/Brotli for JS/CSS/JSON, cache hashed assets, and revalidate model/poster files on releases. No backend or environment variables are needed.

Technical references: [glTF Transform](https://gltf-transform.dev/), [Meshopt compression](https://gltf-transform.dev/modules/extensions/classes/EXTMeshoptCompression), [Three.js GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html).
