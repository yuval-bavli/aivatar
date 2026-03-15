using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;

/// MetaHumanFixer1 — comprehensive material fix via Unity Material API
public static class MetaHumanFixer1
{
    [MenuItem("Aivatar/MetaHuman Fixer V1")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ── 1. Fix Eyelash Material ──────────────────────────────
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null)
        {
            // Force URP Lit shader
            var urpLit = Shader.Find("Universal Render Pipeline/Lit");
            if (urpLit != null && lashMat.shader != urpLit)
            {
                lashMat.shader = urpLit;
                log.AppendLine("Eyelash: switched to URP/Lit shader");
            }

            // Enable alpha clipping (the KEY fix — was disabled!)
            lashMat.SetFloat("_AlphaClip", 1f);
            lashMat.SetFloat("_Cutoff", 0.45f);

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
            lashMat.SetColor("_BaseColor", new Color(0.12f, 0.08f, 0.06f, 0.35f));
            lashMat.SetColor("_Color", new Color(0.12f, 0.08f, 0.06f, 0.35f));

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
            log.AppendLine($"Eyelash: AlphaClip=ON, Cutoff=0.45, Keywords fixed, RQ=2450");
        }
        else log.AppendLine("WARNING: MI_Face_EyelashesHiLODs.mat not found");

        // Also fix AvatarEyelashes if it exists (backup eyelash mat)
        var lashMat2 = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/AvatarEyelashes.mat");
        if (lashMat2 != null)
        {
            var urpLit = Shader.Find("Universal Render Pipeline/Lit");
            if (urpLit != null) lashMat2.shader = urpLit;
            lashMat2.SetFloat("_AlphaClip", 1f);
            lashMat2.SetFloat("_Cutoff", 0.45f);
            lashMat2.SetFloat("_Surface", 0f);
            lashMat2.SetFloat("_Cull", (float)CullMode.Off);
            lashMat2.SetFloat("_ZWrite", 1f);
            lashMat2.SetFloat("_AlphaToMask", 1f);
            lashMat2.SetColor("_BaseColor", new Color(0.12f, 0.08f, 0.06f, 0.35f));
            lashMat2.EnableKeyword("_ALPHATEST_ON");
            lashMat2.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
            lashMat2.renderQueue = (int)RenderQueue.AlphaTest;
            lashMat2.SetOverrideTag("RenderType", "TransparentCutout");
            EditorUtility.SetDirty(lashMat2);
            log.AppendLine("AvatarEyelashes: fixed (same as above)");
        }

        // ── 2. Fix Hair Material ─────────────────────────────────
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            // Ensure URP Lit shader
            var urpLit = Shader.Find("Universal Render Pipeline/Lit");
            if (urpLit != null && hairMat.shader != urpLit)
            {
                hairMat.shader = urpLit;
                log.AppendLine("Hair: switched to URP/Lit shader");
            }

            // Alpha clipping for hair cards
            hairMat.SetFloat("_AlphaClip", 1f);
            hairMat.SetFloat("_Cutoff", 0.15f);
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
            hairMat.SetFloat("_Smoothness", 0.45f);
            hairMat.SetFloat("_Metallic", 0f);

            // Hair color — warm dark brown matching reference
            hairMat.SetColor("_BaseColor", new Color(0.22f, 0.16f, 0.11f, 1f));
            hairMat.SetColor("_Color", new Color(0.22f, 0.16f, 0.11f, 1f));

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
            log.AppendLine($"Hair: Smoothness=0.45, Cutoff=0.15, color=(0.22,0.16,0.11)");
        }
        else log.AppendLine("WARNING: haircut.mat not found");

        // ── 3. Fix Eyebrow Mesh ──────────────────────────────────

        // Try to find and re-enable the eyebrow mesh renderer
        var allRenderers = Object.FindObjectsOfType<SkinnedMeshRenderer>(true);
        foreach (var smr in allRenderers)
        {
            string goName = smr.gameObject.name.ToLower();
            if (goName.Contains("brow") || goName.Contains("eyebrow"))
            {
                // Re-enable the eyebrow renderer
                smr.enabled = true;
                smr.gameObject.SetActive(true);
                log.AppendLine($"Eyebrow mesh re-enabled: {smr.gameObject.name}");

                // Fix its material
                var browMat = smr.sharedMaterial;
                if (browMat != null)
                {
                    browMat.SetFloat("_AlphaClip", 1f);
                    browMat.SetFloat("_Cutoff", 0.3f);
                    browMat.SetFloat("_Cull", (float)CullMode.Off);
                    browMat.SetFloat("_ZWrite", 1f);
                    browMat.SetFloat("_Surface", 0f);
                    browMat.SetFloat("_Smoothness", 0.15f);
                    browMat.EnableKeyword("_ALPHATEST_ON");
                    browMat.renderQueue = (int)RenderQueue.AlphaTest + 1;  // Render after face
                    browMat.SetOverrideTag("RenderType", "TransparentCutout");
                    EditorUtility.SetDirty(browMat);
                    log.AppendLine($"Eyebrow material fixed: {browMat.name}");
                }
            }
        }


        // ── 4. Ensure eyelash texture has proper import settings ─
        string[] lashTexPaths = {
            "Assets/Models/Avatar/Textures/EyelashThin.png",
            "Assets/Models/Avatar/Textures/T_Head_BC_VT_Eyelash.png"
        };
        foreach (var texPath in lashTexPaths)
        {
            var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
            if (importer != null)
            {
                importer.sRGBTexture = true;
                importer.alphaSource = TextureImporterAlphaSource.FromInput;
                importer.alphaIsTransparency = true;
                importer.SaveAndReimport();
                log.AppendLine($"Texture import fixed: {texPath}");
            }
        }

        // ── 5. Fix scalp backing materials ───────────────────────
        string[] hideMats = { "M_Hide", "M_Hide_6" };
        foreach (var hideName in hideMats)
        {
            var hideMat = AssetDatabase.LoadAssetAtPath<Material>(
                $"Assets/Models/Avatar/Materials/{hideName}.mat");
            if (hideMat != null)
            {
                // Make scalp dark to minimize visibility through hair cards
                hideMat.SetColor("_BaseColor", new Color(0.08f, 0.06f, 0.04f, 1f));
                hideMat.SetColor("_Color", new Color(0.08f, 0.06f, 0.04f, 1f));
                hideMat.SetFloat("_Smoothness", 0.1f);
                EditorUtility.SetDirty(hideMat);
                log.AppendLine($"Scalp {hideName}: darkened");
            }
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log("[MetaHumanFixer] " + result);
        return result;
    }
}
