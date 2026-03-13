# MetaHuman Eye Fix for Unity

## Problem

When importing a MetaHuman FBX from Unreal Engine into Unity (URP), the eyes appear completely white. This happens because MetaHuman uses a complex layered eye shader in Unreal that composites multiple textures (sclera, iris, cornea) at runtime. Unity's standard Lit shader can't do this — it expects a single combined texture.

## What was wrong

1. **Separate textures not composited**: The FBX export includes separate sclera (white) and iris (pattern) textures per eye, but the Unity materials only referenced the sclera textures, leaving the iris/pupil invisible.

2. **Iris texture is dark/untinted**: MetaHuman's iris base color texture is a dark grayscale pattern — the actual eye color is applied by Unreal's shader parameters at runtime. Without tinting and brightening, the iris looks nearly black.

3. **Iris texture has no alpha**: The iris PNG has a flat gray background with no transparency, so naive alpha-based compositing doesn't work. A content-based mask is needed.

4. **Material slot order was wrong**: Submesh 4 (the left eyeball sphere, identical geometry to the right eye) was assigned the EyeShell material, while submesh 5 (a flat strip — eyelid inner surface) was getting the left eye material. This caused the left eye to render on distorted geometry.

## Solution

### Editor Scripts

#### `BakeEyeTextures.cs` (Assets/Editor/)
Menu: **Aivatar > Bake Eye Textures**

1. **Content-based masking**: Samples edge pixels of the iris texture to detect the flat gray background color, then marks any pixel that differs as "iris content". This preserves the natural iris boundary, fiber detail, and pupil shape.

2. **Pupil shrinking**: Scans outward from center to find the pupil radius, then replaces outer pupil pixels with iris color sampled from further out at the same angle. Controlled by `PupilShrinkRadius`.

3. **Brightening + tinting**: Applies `IrisBrightness` (1.8x) and `IrisTint` (gray-blue) to the dark UE iris pattern while preserving per-channel detail. A limbal ring darkening is added at the iris edge.

4. **Normal map compositing**: Same mask-based approach for normal maps (no tinting).

5. **Material assignment**: Sets smoothness (0.85), enables specular highlights and environment reflections on eye materials.

6. **EyeShell setup**: Configures the corneal overlay material as transparent with high smoothness (0.98) for wet-look specular highlights.

#### Tunable parameters (top of BakeEyeTextures.cs)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `IrisBrightness` | 1.8 | Multiplier for the dark UE iris texture |
| `IrisTint` | (0.55, 0.62, 0.72) | RGB tint — change for different eye colors |
| `MaskThreshold` | 0.03 | Min color difference from background to count as iris |
| `PupilThreshold` | 0.04 | Grayscale below this is forced to black (pupil) |
| `PupilShrinkRadius` | 0.06 | How much to shrink pupil (fraction of texture width) |

#### `FixFaceMaterials.cs` (Assets/Editor/)
Menu: **Aivatar > Restore Face Materials**

Fixed submesh-to-material mapping:
| Slot | Submesh | Material |
|------|---------|----------|
| 0 | Face skin | MI_Face_Skin_Baked_LOD1_VT |
| 1 | Hidden geometry | M_Hide |
| 2 | Lacrimal fluid | MI_Face_LacrimalFluid |
| 3 | Right eyeball | MI_EyeR_Baked |
| 4 | Left eyeball | MI_EyeL_Baked |
| 5 | Corneal shell | MI_Face_EyeShell |
| 6 | Hidden geometry | M_Hide_6 |
| 7 | Teeth | MI_Teeth_Baked |
| 8 | Eyelashes | MI_Face_EyelashesHiLODs |

### Debug Scripts

#### `DebugEyeUVs.cs` (Assets/Editor/)
Menu: **Aivatar > Debug Eye UVs**

Dumps all submesh info: material name, vertex count, triangle count, world-space center/size, UV range, and tangent-space aspect ratio. This was used to discover the material slot misassignment.

## How to re-bake

1. Run **Aivatar > Restore Face Materials** (if material slots need resetting)
2. Run **Aivatar > Bake Eye Textures**
3. Adjust parameters at top of `BakeEyeTextures.cs` if needed and re-run

## Output files

- `Assets/Models/Avatar/Textures/BakedEyeR_BC.png` — right eye combined color
- `Assets/Models/Avatar/Textures/BakedEyeL_BC.png` — left eye combined color
- `Assets/Models/Avatar/Textures/BakedEyeR_N.png` — right eye combined normal
- `Assets/Models/Avatar/Textures/BakedEyeL_N.png` — left eye combined normal
