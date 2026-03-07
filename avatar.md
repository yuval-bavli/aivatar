# avatar.html — Technical Reference

Single-file HTML prototype of a 3D talking-head avatar with morph-target lip sync.
No build tools. Runs in Chrome via a local HTTP server or `file://`.

---

## Quick Start

```bash
# Option A — any local server (avoids CORS on CDN fetch)
npx serve .
# then open http://localhost:3000/avatar.html

# Option B — direct file open
start avatar.html
```

Three.js r152.2 is loaded from jsDelivr CDN, so network access is required on first load.

---

## Architecture

```
body (flex column, 100vh)
├── #viewport          ← Three.js canvas fills this
└── #panel             ← viseme control sliders (max-height 38vh, scrollable)
```

All logic lives in a single `<script>` block. No modules, no bundler.

---

## Scene

| Item | Value |
|---|---|
| Renderer | `WebGLRenderer`, antialias, sRGB output, ACES filmic tone mapping (exposure 1.1) |
| Shadow map | PCFSoft, 1024 × 1024 |
| Camera | PerspectiveCamera, FOV 38°, position (0, 0.08, 2.4) |
| Background | `#0d1117`, exponential fog density 0.18 |

### Lights

| Name | Type | Color | Intensity | Notes |
|---|---|---|---|---|
| `ambLight` | AmbientLight | blue-grey | 0.9 | base fill |
| `keyLight` | DirectionalLight | warm white | 1.4 | from upper-right-front, casts shadows |
| `fillLight` | DirectionalLight | cool blue | 0.35 | from left |
| `rimLight` | DirectionalLight | white | 0.5 | from behind (hair rim) |
| `bounceLight` | HemisphereLight | — | 0.4 | sky/ground bounce |

---

## Head Model

All meshes belong to a single `headGroup` (`THREE.Group`) so idle animation moves the whole head together.

| Part | Geometry | Material color |
|---|---|---|
| Head | `SphereGeometry(0.5, 40, 30)`, scaled (1, 1.18, 0.92) | `#f0b888` skin |
| Neck | `CylinderGeometry(0.19, 0.23, 0.38)` | skin |
| Shoulders | `CapsuleGeometry`, rotated 90° Z | `#1a2030` dark cloth |
| Eyes | Sphere (white) + Circle (iris) + Circle (pupil) + Box (eyelid) per side | white / `#3d6b99` blue / dark |
| Eyebrows | `BoxGeometry(0.13, 0.016, 0.025)` per side | `#1a1008` dark |
| Nose | Box (bridge) + Sphere (tip) + 2× Sphere (nostrils) | `#e8a878` slightly darker skin |
| Ears | Partial Torus (arc) + Sphere (lobe) per side | `#e8a070` |
| Hair | `SphereGeometry` with φ clipped to upper 55%, scaled (1, 1.19, 0.93) | `#100808` near-black |
| Teeth (upper) | `BoxGeometry(0.16, 0.022, 0.018)` | `#f0ece0` off-white |
| Teeth (lower) | `BoxGeometry(0.145, 0.020, 0.016)` | same |
| Mouth cavity | `CircleGeometry(0.065)` | `#1a0808` dark red |

Teeth and cavity are static — they sit behind the morph-target lip mesh and become visible as the mouth opens.

---

## Mouth Geometry & Morph Targets

### Vertex Layout

The lip mesh (`mouthMesh`) is a flat `BufferGeometry` with **17 vertices** and **24 triangles**, placed at world position (0, −0.23, 0.454) in head-local space.

```
Indices 0–7   outer lip ring   (8 verts, ellipse, CCW from bottom when seen from +z)
Indices 8–15  inner lip ring   (8 verts, smaller ellipse)
Index 16      center / throat  (1 vert)
```

Angle convention: `a = (i/8) * 2π − π/2`
- `i=0` → bottom (6 o'clock)
- `i=2` → right (3 o'clock)
- `i=4` → top (12 o'clock)
- `i=6` → left (9 o'clock)

### Triangulation

```
Outer → Inner strip : 8 quads  → 16 triangles   (CCW-wound from +z)
Inner → Center fan  : 8 tris
Total : 24 triangles, 72 indices
```

Strip winding for quad (outer[i], outer[i+1], inner[i+1], inner[i]):
```js
indices.push(o0, o1, i1);  // tri 1
indices.push(o0, i1, i0);  // tri 2
```

Fan winding:
```js
indices.push(inner[i], inner[i+1], center);
```

### Shape Parameters (`buildMouthVerts`)

Each viseme shape is described by a plain parameter object:

| Parameter | Effect |
|---|---|
| `outerRx / outerRy` | x/y radii of the outer lip ellipse |
| `innerRx / innerRy` | x/y radii of the inner (opening) ellipse |
| `jawDrop` | lower-half vertices drop by `jawDrop × |sinA|` |
| `pucker` | z-offset (positive = lips forward toward camera) |
| `cornerX` | x-scale applied to corner vertices (`cosA > 0.65`); `>1` = smile, `<1` = pucker |
| `upperLift` | upper-half vertices rise by `upperLift × sinA` |

`buildMouthVerts(params)` returns a `Float32Array` of length 51 (17 verts × 3 floats).

### Morph Target Mode

```js
mouthGeo.morphTargetsRelative = false;   // absolute positions
```

Three.js interpolation formula:
```
final = base × (1 − ΣweightᵢB) + morph₀ × w₀ + morph₁ × w₁ + …
```

When all weights are 0 the mesh shows the base (= sil) shape.
When one weight is 1.0 the mesh snaps fully to that viseme shape.
Intermediate values blend smoothly.

---

## Viseme Table

| ID | Name | Phoneme class | Key shape characteristics |
|---|---|---|---|
| 0 | `viseme_sil` | silence | closed, neutral — identical to base mesh |
| 1 | `viseme_PP` | p, b, m | lips pressed, slight forward pucker, corners pulled in |
| 2 | `viseme_FF` | f, v | narrow horizontal opening, lips flat |
| 3 | `viseme_TH` | th | very flat wide opening, minimal jaw drop |
| 4 | `viseme_DD` | t, d | small opening, teeth close |
| 5 | `viseme_kk` | k, g | slightly larger opening, lips slightly retracted |
| 6 | `viseme_CH` | ch, sh | lips forward and rounded, medium-small opening |
| 7 | `viseme_SS` | s, z | widest smile, teeth nearly touching |
| 8 | `viseme_nn` | n | tiny opening, lips nearly touching |
| 9 | `viseme_RR` | r | rounded, medium-small open |
| 10 | `viseme_aa` | ah | widest jaw drop, open vowel |
| 11 | `viseme_E` | eh | wide smile, medium jaw drop |
| 12 | `viseme_ih` | ih | slight smile, small opening |
| 13 | `viseme_oh` | oh | tall O shape, rounded corners, medium open |
| 14 | `viseme_ou` | oo | smallest rounded pucker |

These IDs match the Azure Cognitive Services Speech SDK viseme event stream exactly.

---

## Global JavaScript API

```js
// Drive a single viseme. Call this from your speech event handler.
setViseme(visemeId, weight)
// visemeId : integer 0–14
// weight   : float 0.0–1.0 (clamped internally)
// Side-effect: syncs the corresponding UI slider.

// Zero out all 15 morph target influences.
resetVisemes()
// Side-effect: resets all UI sliders to 0.
```

### Connecting Azure Speech SDK

```js
synthesizer.visemeReceived = (s, e) => {
  resetVisemes();
  setViseme(e.visemeId, 1.0);
};
```

For smoother animation, lerp the influence over the audio offset window rather than snapping to 1.0.

---

## Idle Animation

Runs inside `requestAnimationFrame`. Uses a manually incremented `clock` (+=0.016 per frame, approximately 60 fps).

| Axis | Formula | Effect |
|---|---|---|
| position.y | `sin(clock × 0.48) × 0.011` | breathing bob |
| rotation.y | `sin(clock × 0.22) × 0.028` | slow look-around |
| rotation.x | `sin(clock × 0.31) × 0.012` | slight nod |
| rotation.z | `sin(clock × 0.17) × 0.008` | gentle tilt |

**Blinking:** a random interval (2.0–5.5 s) triggers a 0.12 s blink. The eyelid `BoxGeometry` meshes are identified by their height parameter (0.018) via `headGroup.traverse` and their `scale.y` is driven by `sin(blinkPhase × π)`.

---

## Control Panel

Built entirely in JS at startup. Each of the 15 rows contains:

```
[id]  [viseme_name]  [────────────slider────────────]  [0.00]
```

- Slider `id="s-{visemeId}"`, value `"v-{visemeId}"`
- Moving a slider directly writes to `mouthMesh.morphTargetInfluences[id]`
- Calling `setViseme()` / `resetVisemes()` from code also updates sliders
- **Reset All** button calls `window.resetVisemes()`

---

## Planned Next Steps

1. **Speech integration** — connect Azure Speech SDK; feed `visemeReceived` events to `setViseme()`
2. **Lerp smoothing** — instead of snapping weights, animate them toward target values each frame (e.g. exponential decay)
3. **Unity migration** — replace this mesh with a proper rigged glTF head; the 15 blendshape names and the `setViseme` / `resetVisemes` API contract carry over unchanged
4. **Morph normals** — add `morphAttributes.normal` to fix lighting artefacts on extreme morph shapes
5. **Eye tracking** — drive iris/pupil position toward a target point for more lifelike gaze
