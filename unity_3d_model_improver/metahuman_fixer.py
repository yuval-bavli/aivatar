"""
metahuman_fixer.py — Deterministic C# script generator for MetaHuman material fixes.

Approach 1: Instead of tweaking YAML float values, generates a C# Editor script
that uses Unity's Material API to programmatically set ALL material properties:
- Shader keywords (m_ValidKeywords / m_InvalidKeywords)
- Render queues
- Surface types
- Alpha clipping enable/disable
- Blend modes
- Cull modes

These are things the YAML mat_editor cannot do because they require
Material.EnableKeyword(), Material.renderQueue, etc.

Usage:
    python metahuman_fixer.py [--dry-run]
"""

from __future__ import annotations

import pathlib
import sys
import textwrap

import unity_bridge

_REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
_EDITOR_DIR = _REPO_ROOT / "unity" / "aivatar" / "Assets" / "Editor"

# Counter file to generate unique class names (avoids Unity compile conflicts)
_COUNTER_FILE = pathlib.Path(__file__).parent / ".fixer_counter"


def _next_version() -> int:
    """Get and increment the version counter."""
    n = 1
    if _COUNTER_FILE.exists():
        try:
            n = int(_COUNTER_FILE.read_text().strip()) + 1
        except ValueError:
            pass
    _COUNTER_FILE.write_text(str(n))
    return n


def generate_fixer_script(
    eyelash_cutoff: float = 0.45,
    eyelash_alpha: float = 0.35,
    eyelash_color: tuple = (0.12, 0.08, 0.06),
    hair_smoothness: float = 0.45,
    hair_cutoff: float = 0.15,
    hair_color: tuple = (0.22, 0.16, 0.11),
    enable_eyebrow_mesh: bool = True,
    eyebrow_cutoff: float = 0.3,
) -> tuple[str, str]:
    """
    Generate a C# Editor script that fixes MetaHuman materials using Unity's API.

    Returns (class_name, cs_code).
    """
    ver = _next_version()
    class_name = f"MetaHumanFixer{ver}"

    cs_code = textwrap.dedent(f"""\
        using UnityEngine;
        using UnityEditor;
        using UnityEngine.Rendering;

        /// MetaHumanFixer{ver} — comprehensive material fix via Unity Material API
        public static class {class_name}
        {{
            [MenuItem("Aivatar/MetaHuman Fixer V{ver}")]
            public static string Run()
            {{
                var log = new System.Text.StringBuilder();

                // ── 1. Fix Eyelash Material ──────────────────────────────
                var lashMat = AssetDatabase.LoadAssetAtPath<Material>(
                    "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
                if (lashMat != null)
                {{
                    // Force URP Lit shader
                    var urpLit = Shader.Find("Universal Render Pipeline/Lit");
                    if (urpLit != null && lashMat.shader != urpLit)
                    {{
                        lashMat.shader = urpLit;
                        log.AppendLine("Eyelash: switched to URP/Lit shader");
                    }}

                    // Enable alpha clipping (the KEY fix — was disabled!)
                    lashMat.SetFloat("_AlphaClip", 1f);
                    lashMat.SetFloat("_Cutoff", {eyelash_cutoff}f);

                    // Surface type: Opaque with alpha test (not transparent)
                    lashMat.SetFloat("_Surface", 0f);  // 0 = Opaque
                    lashMat.SetFloat("_Blend", 0f);
                    lashMat.SetFloat("_SrcBlend", 1f);  // One
                    lashMat.SetFloat("_DstBlend", 0f);  // Zero
                    lashMat.SetFloat("_SrcBlendAlpha", 1f);
                    lashMat.SetFloat("_DstBlendAlpha", 0f);
                    lashMat.SetFloat("_ZWrite", 1f);

                    // Double-sided rendering (eyelash cards are single-sided geometry)
                    lashMat.SetFloat("_Cull", (float)CullMode.Off);
                    lashMat.doubleSidedGI = true;

                    // Alpha-to-coverage for smoother edges
                    lashMat.SetFloat("_AlphaToMask", 1f);

                    // Color: dark brown, semi-transparent alpha for softness
                    lashMat.SetColor("_BaseColor", new Color({eyelash_color[0]}f, {eyelash_color[1]}f, {eyelash_color[2]}f, {eyelash_alpha}f));
                    lashMat.SetColor("_Color", new Color({eyelash_color[0]}f, {eyelash_color[1]}f, {eyelash_color[2]}f, {eyelash_alpha}f));

                    // Low smoothness (hair isn't glossy)
                    lashMat.SetFloat("_Smoothness", 0.1f);
                    lashMat.SetFloat("_Metallic", 0f);

                    // Shader keywords — the CRITICAL part YAML editing can't do
                    lashMat.EnableKeyword("_ALPHATEST_ON");
                    lashMat.EnableKeyword("_NORMALMAP");
                    lashMat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    lashMat.DisableKeyword("_ALPHAPREMULTIPLY_ON");

                    // Render queue: AlphaTest (2450)
                    lashMat.renderQueue = (int)RenderQueue.AlphaTest;

                    // Set render type tag
                    lashMat.SetOverrideTag("RenderType", "TransparentCutout");

                    // Re-enable shadow casting and depth pass
                    lashMat.SetShaderPassEnabled("DepthOnly", true);
                    lashMat.SetShaderPassEnabled("SHADOWCASTER", true);

                    EditorUtility.SetDirty(lashMat);
                    log.AppendLine($"Eyelash: AlphaClip=ON, Cutoff={eyelash_cutoff}, Keywords fixed, RQ=2450");
                }}
                else log.AppendLine("WARNING: MI_Face_EyelashesHiLODs.mat not found");

                // Also fix AvatarEyelashes if it exists (backup eyelash mat)
                var lashMat2 = AssetDatabase.LoadAssetAtPath<Material>(
                    "Assets/Models/Avatar/Materials/AvatarEyelashes.mat");
                if (lashMat2 != null)
                {{
                    var urpLit = Shader.Find("Universal Render Pipeline/Lit");
                    if (urpLit != null) lashMat2.shader = urpLit;
                    lashMat2.SetFloat("_AlphaClip", 1f);
                    lashMat2.SetFloat("_Cutoff", {eyelash_cutoff}f);
                    lashMat2.SetFloat("_Surface", 0f);
                    lashMat2.SetFloat("_Cull", (float)CullMode.Off);
                    lashMat2.SetFloat("_ZWrite", 1f);
                    lashMat2.SetFloat("_AlphaToMask", 1f);
                    lashMat2.SetColor("_BaseColor", new Color({eyelash_color[0]}f, {eyelash_color[1]}f, {eyelash_color[2]}f, {eyelash_alpha}f));
                    lashMat2.EnableKeyword("_ALPHATEST_ON");
                    lashMat2.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    lashMat2.renderQueue = (int)RenderQueue.AlphaTest;
                    lashMat2.SetOverrideTag("RenderType", "TransparentCutout");
                    EditorUtility.SetDirty(lashMat2);
                    log.AppendLine("AvatarEyelashes: fixed (same as above)");
                }}

                // ── 2. Fix Hair Material ─────────────────────────────────
                var hairMat = AssetDatabase.LoadAssetAtPath<Material>(
                    "Assets/Models/Avatar/Materials/haircut.mat");
                if (hairMat != null)
                {{
                    // Ensure URP Lit shader
                    var urpLit = Shader.Find("Universal Render Pipeline/Lit");
                    if (urpLit != null && hairMat.shader != urpLit)
                    {{
                        hairMat.shader = urpLit;
                        log.AppendLine("Hair: switched to URP/Lit shader");
                    }}

                    // Alpha clipping for hair cards
                    hairMat.SetFloat("_AlphaClip", 1f);
                    hairMat.SetFloat("_Cutoff", {hair_cutoff}f);
                    hairMat.SetFloat("_AlphaToMask", 1f);

                    // Opaque surface with alpha test
                    hairMat.SetFloat("_Surface", 0f);
                    hairMat.SetFloat("_Blend", 0f);
                    hairMat.SetFloat("_SrcBlend", 1f);
                    hairMat.SetFloat("_DstBlend", 0f);
                    hairMat.SetFloat("_ZWrite", 1f);

                    // Double-sided
                    hairMat.SetFloat("_Cull", (float)CullMode.Off);
                    hairMat.doubleSidedGI = true;

                    // CRITICAL: Reduce smoothness (was 0.95 = glass-like!)
                    hairMat.SetFloat("_Smoothness", {hair_smoothness}f);
                    hairMat.SetFloat("_Metallic", 0f);

                    // Hair color — warm dark brown matching reference
                    hairMat.SetColor("_BaseColor", new Color({hair_color[0]}f, {hair_color[1]}f, {hair_color[2]}f, 1f));
                    hairMat.SetColor("_Color", new Color({hair_color[0]}f, {hair_color[1]}f, {hair_color[2]}f, 1f));

                    // Normal map strength
                    hairMat.SetFloat("_BumpScale", 0.8f);

                    // Disable environment reflections (hair shouldn't reflect skybox)
                    hairMat.SetFloat("_EnvironmentReflections", 0f);

                    // Keywords
                    hairMat.EnableKeyword("_ALPHATEST_ON");
                    hairMat.EnableKeyword("_NORMALMAP");
                    hairMat.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
                    hairMat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");

                    // Render queue
                    hairMat.renderQueue = (int)RenderQueue.AlphaTest;
                    hairMat.SetOverrideTag("RenderType", "TransparentCutout");

                    EditorUtility.SetDirty(hairMat);
                    log.AppendLine($"Hair: Smoothness={hair_smoothness}, Cutoff={hair_cutoff}, color=({hair_color[0]},{hair_color[1]},{hair_color[2]})");
                }}
                else log.AppendLine("WARNING: haircut.mat not found");

                // ── 3. Fix Eyebrow Mesh ──────────────────────────────────
                {"" if not enable_eyebrow_mesh else f'''
                // Try to find and re-enable the eyebrow mesh renderer
                var allRenderers = Object.FindObjectsOfType<SkinnedMeshRenderer>(true);
                foreach (var smr in allRenderers)
                {{
                    string goName = smr.gameObject.name.ToLower();
                    if (goName.Contains("brow") || goName.Contains("eyebrow"))
                    {{
                        // Re-enable the eyebrow renderer
                        smr.enabled = true;
                        smr.gameObject.SetActive(true);
                        log.AppendLine($"Eyebrow mesh re-enabled: {{smr.gameObject.name}}");

                        // Fix its material
                        var browMat = smr.sharedMaterial;
                        if (browMat != null)
                        {{
                            browMat.SetFloat("_AlphaClip", 1f);
                            browMat.SetFloat("_Cutoff", {eyebrow_cutoff}f);
                            browMat.SetFloat("_Cull", (float)CullMode.Off);
                            browMat.SetFloat("_ZWrite", 1f);
                            browMat.SetFloat("_Surface", 0f);
                            browMat.SetFloat("_Smoothness", 0.15f);
                            browMat.EnableKeyword("_ALPHATEST_ON");
                            browMat.renderQueue = (int)RenderQueue.AlphaTest + 1;  // Render after face
                            browMat.SetOverrideTag("RenderType", "TransparentCutout");
                            EditorUtility.SetDirty(browMat);
                            log.AppendLine($"Eyebrow material fixed: {{browMat.name}}");
                        }}
                    }}
                }}
                '''}

                // ── 4. Ensure eyelash texture has proper import settings ─
                string[] lashTexPaths = {{
                    "Assets/Models/Avatar/Textures/EyelashThin.png",
                    "Assets/Models/Avatar/Textures/T_Head_BC_VT_Eyelash.png"
                }};
                foreach (var texPath in lashTexPaths)
                {{
                    var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
                    if (importer != null)
                    {{
                        importer.sRGBTexture = true;
                        importer.alphaSource = TextureImporterAlphaSource.FromInput;
                        importer.alphaIsTransparency = true;
                        importer.SaveAndReimport();
                        log.AppendLine($"Texture import fixed: {{texPath}}");
                    }}
                }}

                // ── 5. Fix scalp backing materials ───────────────────────
                string[] hideMats = {{ "M_Hide", "M_Hide_6" }};
                foreach (var hideName in hideMats)
                {{
                    var hideMat = AssetDatabase.LoadAssetAtPath<Material>(
                        $"Assets/Models/Avatar/Materials/{{hideName}}.mat");
                    if (hideMat != null)
                    {{
                        // Make scalp dark to minimize visibility through hair cards
                        hideMat.SetColor("_BaseColor", new Color(0.08f, 0.06f, 0.04f, 1f));
                        hideMat.SetColor("_Color", new Color(0.08f, 0.06f, 0.04f, 1f));
                        hideMat.SetFloat("_Smoothness", 0.1f);
                        EditorUtility.SetDirty(hideMat);
                        log.AppendLine($"Scalp {{hideName}}: darkened");
                    }}
                }}

                AssetDatabase.SaveAssets();
                string result = log.ToString();
                Debug.Log("[MetaHumanFixer] " + result);
                return result;
            }}
        }}
    """)

    return class_name, cs_code


def apply_fix(
    eyelash_cutoff: float = 0.45,
    eyelash_alpha: float = 0.35,
    eyelash_color: tuple = (0.12, 0.08, 0.06),
    hair_smoothness: float = 0.45,
    hair_cutoff: float = 0.15,
    hair_color: tuple = (0.22, 0.16, 0.11),
    enable_eyebrow_mesh: bool = True,
    eyebrow_cutoff: float = 0.3,
    dry_run: bool = False,
) -> str:
    """
    Generate a C# fixer script, write it to the Unity Editor folder,
    compile it via refresh, and execute it.

    Returns the execution result string.
    """
    class_name, cs_code = generate_fixer_script(
        eyelash_cutoff=eyelash_cutoff,
        eyelash_alpha=eyelash_alpha,
        eyelash_color=eyelash_color,
        hair_smoothness=hair_smoothness,
        hair_cutoff=hair_cutoff,
        hair_color=hair_color,
        enable_eyebrow_mesh=enable_eyebrow_mesh,
        eyebrow_cutoff=eyebrow_cutoff,
    )

    script_path = _EDITOR_DIR / f"{class_name}.cs"

    if dry_run:
        print(f"[metahuman_fixer] DRY RUN — would write {script_path}")
        print(cs_code)
        return "DRY RUN"

    # Write script
    script_path.write_text(cs_code, encoding="utf-8")
    print(f"[metahuman_fixer] Wrote {script_path}", file=sys.stderr)

    # Compile
    print("[metahuman_fixer] Refreshing Unity (compiling) …", file=sys.stderr)
    unity_bridge.refresh()

    # Execute
    print(f"[metahuman_fixer] Executing {class_name}.Run() …", file=sys.stderr)
    result = unity_bridge.execute(f"{class_name}.Run")
    print(f"[metahuman_fixer] Result:\n{result}")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MetaHuman material fixer")
    parser.add_argument("--dry-run", action="store_true", help="Print C# script without executing")
    parser.add_argument("--eyelash-cutoff", type=float, default=0.45)
    parser.add_argument("--eyelash-alpha", type=float, default=0.35)
    parser.add_argument("--hair-smoothness", type=float, default=0.45)
    parser.add_argument("--hair-cutoff", type=float, default=0.15)
    parser.add_argument("--eyebrow-cutoff", type=float, default=0.3)
    args = parser.parse_args()

    apply_fix(
        eyelash_cutoff=args.eyelash_cutoff,
        eyelash_alpha=args.eyelash_alpha,
        hair_smoothness=args.hair_smoothness,
        hair_cutoff=args.hair_cutoff,
        eyebrow_cutoff=args.eyebrow_cutoff,
        dry_run=args.dry_run,
    )
