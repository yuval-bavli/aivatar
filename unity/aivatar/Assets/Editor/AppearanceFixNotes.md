# MetaHuman Appearance Fix Notes (Unity URP)

## Starting State (Problems)
- Hair: white/red streaks — wrong material assigned to hair mesh
- Outfit: completely black — no textures, black base color
- Eyebrows: completely invisible — positioned 0.86 world units ABOVE the head
- Eyelashes: too dark, too bold

## Target
Original MetaHuman from Unreal Engine — dark brown messy bob, natural eyebrows, white T-shirt, thin natural eyelashes.

---

## Fixes That Worked

### 1. Hair Material — CRITICAL FIX
**Problem**: `Hair_M_BobMessy_CardsMesh_Group0_LOD0` (MeshRenderer, 1 submesh) had 9 materials assigned — the same face materials as `SKM_model4_FaceMesh`. Only Mat[0] (`MI_Face_Skin_Baked_LOD1_VT`) was used, making the hair render with the face skin texture.

**Fix**: Assign `Assets/Models/Avatar/Materials/haircut.mat` as the **only** material on this mesh.

**Material settings for `haircut.mat`:**
- Shader: URP/Lit, Opaque, alpha cutout enabled
- `_BaseColor`: (0.22, 0.15, 0.10) — warm dark brown
- `_Cutoff`: 0.15 — moderate for good coverage
- `_Smoothness`: 0.20 — low to avoid shiny flat-plane look
- `_Cull`: 0 (double-sided)
- Disable `_SPECULARHIGHLIGHTS_ON` and `_ENVIRONMENTREFLECTIONS_ON` — prevents blue skybox tint on hair

**Note**: Alpha blending (transparent mode) was tried but made hair look washed out/grey. Alpha cutout is correct.

---

### 2. Outfit Fix
**Problem**: `MID_M_DG_bodyShapeB_Shirt_70` and `..._Short_71` had black `_BaseColor` and no textures.

**Fix**: Set `_BaseColor` to (0.85, 0.85, 0.85) — light gray to match original white T-shirt.

---

### 3. M_Hide / M_Hide_6 Materials (Scalp Backing)
**Problem**: These were using `HairCard0_Color_1K.png` with hair texture, showing visible hair card artifacts in scalp area.

**Fix**: Set to dark opaque:
- `_BaseColor`: (0.10, 0.07, 0.05) — very dark brown scalp
- `_Surface`: 0 (opaque), no texture, no alpha
- Acts as a dark cap under the hair to reduce scalp visibility

---

### 4. Eyelashes (`MI_Face_EyelashesHiLODs.mat`)
**Problem**: Very dark (0.12, 0.08, 0.06) and bold, looking like heavy mascara.

**Fix**:
- `_BaseColor`: (0.35, 0.25, 0.20) — much lighter, nearly skin-toned
- `_Cutoff`: 0.7 — very high for thin, wispy lashes
- `_BaseMap`: `HairCard0_Color_1K.png` (has proper alpha for strand shapes)
- Disable `_SPECULARHIGHLIGHTS_ON` and `_ENVIRONMENTREFLECTIONS_ON`

---

### 5. Eye Shell (`MI_Face_EyeShell.mat`)
**Problem**: Was using `HairCard0_Color_1K.png` as texture — wrong, showed hair pattern.

**Fix**: Clear `_BaseMap` and `_BumpMap`, set `_BaseColor` to (1,1,1,0.02) nearly invisible, `_Smoothness`: 0.98 for wet-look cornea specular.

---

### 6. Eyebrows — COMPLEX PROBLEM

#### Root Cause of Invisibility
The eyebrow mesh `Eyebrows_M_Natural_CardsMesh_Group0_LOD0`:
- Has mesh vertices in local space at Y=-4.83 to -2.96, Z=62.67 to 63.54
- Parent `SKM_model4_BodyMesh` has rotation (270°, 183.62°, 0°) which rotates local Z→world Y
- The mesh was rendering at world Y≈2.35, but the face is at world Y≈1.49
- **The eyebrows were floating 0.86m above the head!**

#### Position Fix
Required local position adjustment: `(-0.01, -0.04, -0.757)` to achieve world Y≈1.55.
- Local Z maps approximately to world Y (due to 270° X rotation on parent)
- Local -Y maps approximately to world -Z (toward camera)
- Forward push needed: local Y ≈ -0.04 to clear z-fighting with brow ridge
- Camera near clip reduced to 0.1 (from 0.3) to allow close rendering

#### Z-Fighting Problem
Even at correct position, central eyebrow cards are occluded by face geometry (brow ridge sits at same depth). Only outer/temple portions render cleanly.

#### What Was Tried (Failed)
- `_ZTest = Always` on URP/Lit material — shader ignores material-level ZTest
- Custom HLSL shader with `ZTest Always` — didn't render (likely render pipeline tag issue)
- Pushing mesh 2m forward — geometry went past near clip plane (0.3 units)
- Standard Quad primitives facing wrong direction — Unity Quad faces +Z by default, camera looks from -Z side; need `Euler(0, 180, 0)` rotation

#### Best Partial Solution
Position: `(-0.01, -0.04, -0.757)` with material:
- `_Cutoff`: 0.5 (high, for subtle look)
- renderQueue: 2500
The sides of the eyebrows (temples) render; center is occluded. Acceptable for close-up shots.

#### Alternative: Bake onto Face Texture
Approach: Paint eyebrow arcs directly onto `T_Head_BC_VT.PNG` face texture.

UV mapping found (from mesh vertex sampling):
- Right eyebrow (viewer's left): pixels ≈ (654-737, 1291-1532)
- Left eyebrow (viewer's right): pixels ≈ (1328-1431, 1295-1589)

Paint settings that work:
- `PaintBrowArc()` with 5 overlapping passes for thickness
- `_thickness`: 12px, `strength`: 0.65-0.7
- Color: (0.20, 0.14, 0.10) dark warm brown
- Multiple passes with slight Y offsets for natural thickness
- Optional: hair-like individual strokes (40 random strokes per brow)

Save as `T_Head_BC_VT_Brows.png` and assign to `MI_Face_Skin_Baked_LOD1_VT._BaseMap`.

**Note**: Baked arcs are visible but require strong settings — thin/faint at render distance. The face texture is UV-mapped with face upside-down; UV V increases upward.

---

## Scene Hierarchy (Key Objects)
```
SKM_model4_BodyMesh (root, SkinnedMeshRenderer)
  ├── model4_Outfits (SkinnedMeshRenderer — clothing)
  └── SKM_model4_FaceMesh/ (transform parent, NOT a renderer)
       ├── Hair_M_BobMessy_CardsMesh_Group0_LOD0 (MeshRenderer — hair)
       ├── Eyebrows_M_Natural_CardsMesh_Group0_LOD0 (MeshRenderer — eyebrows)
       └── SKM_model4_FaceMesh (MeshRenderer — face, 9 submeshes)
```

## Face Mesh Submesh → Material Mapping (9 slots)
| Slot | Material |
|------|----------|
| 0 | MI_Face_Skin_Baked_LOD1_VT (face skin) |
| 1 | M_Hide (scalp/hidden) |
| 2 | MI_Face_LacrimalFluid (tear fluid) |
| 3 | MI_EyeR_Baked (right eye) |
| 4 | MI_EyeL_Baked (left eye) |
| 5 | MI_Face_EyeShell (cornea overlay) |
| 6 | M_Hide_6 (hidden) |
| 7 | MI_Teeth_Baked (teeth) |
| 8 | MI_Face_EyelashesHiLODs (eyelashes) |

## Camera Settings
- Position: (0.04, 1.53, -9.09), looking +Z
- Near clip: **0.1** (reduced from 0.3 to allow eyebrow rendering at close range)
- FOV: 60°

## Final Confirmed State (2026-03-14)

- `BakeEyebrows4.Run` executed successfully — eyebrow arcs painted onto `T_Head_BC_VT_Brows.png`, assigned to face material
- Eyebrow mesh renderer (`Eyebrows_M_Natural_CardsMesh_Group0_LOD0`) is **disabled** — mesh-based approach fully abandoned
- Screenshot confirmed: dark hair, subtle eyebrows above eyes, lightened eyelashes, white T-shirt visible

---

## Remaining Issues / Possible Next Improvements
1. **Hair polygon look**: Inherent to hair cards — no material fix can solve this. Would require replacing with SpeedTree/strand-based hair asset.
2. **Eyebrows too subtle**: Baked arcs are faint at render distance. Could increase `strength` (0.7→0.9) or `thickness` (12→18) in `BakeEyebrows4.cs` and re-run.
3. **Eyelashes still slightly bold**: `_Cutoff` 0.7 with BaseColor (0.35, 0.25, 0.20) is improved but not perfect. Try cutoff 0.75–0.8 or lighter color.
4. **Scalp gaps**: Normal for hair cards — dark M_Hide backing minimizes this.
