using UnityEngine;
using UnityEditor;
using System.IO;

public static class FixAppearanceFresh
{
    [MenuItem("Aivatar/Fix Appearance Fresh")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ============================================================
        // 1. EYEBROWS: Disable the displaced mesh - it looks wrong
        //    The face texture should have some brow shading baked in
        // ============================================================
        foreach (var r in Object.FindObjectsOfType<Renderer>(true))
        {
            if (r.gameObject.name == "Eyebrows_M_Natural_CardsMesh_Group0_LOD0")
            {
                r.enabled = false;
                log.AppendLine("Disabled eyebrow mesh (displaced version looks wrong)");
            }
        }

        // ============================================================
        // 2. HAIR: Switch to alpha blending for softer, less polygonal look
        // ============================================================
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            // Switch to transparent surface type for soft blending
            hairMat.SetFloat("_Surface", 1f); // Transparent
            hairMat.SetFloat("_Blend", 0f); // Alpha blend
            hairMat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            hairMat.EnableKeyword("_ALPHAPREMULTIPLY_ON");
            // Disable alpha clipping - use smooth alpha blending instead
            hairMat.SetFloat("_AlphaClip", 0f);
            hairMat.DisableKeyword("_ALPHATEST_ON");
            // Blend modes for proper transparency
            hairMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.One);
            hairMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            hairMat.SetFloat("_ZWrite", 0f);
            hairMat.renderQueue = 3000; // Transparent queue
            // Dark warm brown
            hairMat.SetColor("_BaseColor", new Color(0.22f, 0.15f, 0.10f, 1f));
            hairMat.SetFloat("_Smoothness", 0.35f);
            hairMat.SetFloat("_Metallic", 0f);
            hairMat.SetFloat("_Cull", 0f); // Double-sided
            // Disable specular/env reflections to avoid blue tint
            hairMat.DisableKeyword("_SPECULARHIGHLIGHTS_ON");
            hairMat.DisableKeyword("_ENVIRONMENTREFLECTIONS_ON");
            EditorUtility.SetDirty(hairMat);
            log.AppendLine("Hair: switched to alpha blend (transparent) for softer edges");
        }

        // ============================================================
        // 3. EYELASHES: Use actual eyelash opacity texture, much lighter
        // ============================================================
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        // Try to use the embedded eyelash opacity mask as the base map
        var lashOpacity = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/MI_Face_EyelashesHiLODs_OpacityMask_8.png");
        var lashBaseColor = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/MI_Face_EyelashesHiLODs_BaseColor_8.png");

        if (lashMat != null)
        {
            // Use the eyelash-specific textures if available
            if (lashBaseColor != null)
            {
                lashMat.SetTexture("_BaseMap", lashBaseColor);
                log.AppendLine($"Eyelashes: using dedicated base color texture");
            }

            // Much lighter and thinner
            lashMat.SetColor("_BaseColor", new Color(0.30f, 0.22f, 0.18f, 1f));
            lashMat.SetFloat("_Cutoff", 0.6f); // Very high for thin lashes
            lashMat.SetFloat("_AlphaClip", 1f);
            lashMat.EnableKeyword("_ALPHATEST_ON");
            lashMat.SetFloat("_Smoothness", 0.2f);
            lashMat.SetFloat("_Cull", 0f);
            lashMat.DisableKeyword("_SPECULARHIGHLIGHTS_ON");
            lashMat.DisableKeyword("_ENVIRONMENTREFLECTIONS_ON");
            EditorUtility.SetDirty(lashMat);
            log.AppendLine("Eyelashes: lighter color, higher cutoff for thin natural look");

            // Log eyelash texture info
            log.AppendLine($"  lashOpacity found: {lashOpacity != null}");
            log.AppendLine($"  lashBaseColor found: {lashBaseColor != null}");
        }

        // ============================================================
        // 4. M_HIDE: Dark scalp backing (keep as-is from earlier fix)
        // ============================================================

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
